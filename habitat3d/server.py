"""Loopback-only persistent observation server. No cloud service or LLM required."""
import argparse
import json
import mimetypes
import os
from pathlib import Path
import threading
import time
import traceback
import copy
import hashlib
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse,parse_qs,unquote
from ecology import Habitat,DT,SCHEMA

HERE=Path(__file__).resolve().parent


class Runtime:
    def __init__(self,path,seed,count,resume=True,brain_mode='mbon'):
        self.path=Path(path);self.path.mkdir(parents=True,exist_ok=True)
        self.lock=threading.RLock();self.stop=threading.Event()
        self.paused=False;self.speed=1;self.error=None;self.step_ms=0.
        self.saved_at=None;self.started=time.monotonic()
        save=self.path/'world_state.json'
        if resume and save.exists():
            data=json.loads(save.read_text(encoding='utf-8'))
            self.world=Habitat.restore(data['simulation'])
            if self.world.brains.mode!=brain_mode:raise ValueError('Saved brain mode differs from requested mode; archive explicitly before migration')
            self.paused=data['runtime']['paused'];self.speed=data['runtime']['speed']
            self.saved_at=data['saved_at']
            # Runtime resume must not mutate the simulation's event IDs or RNG.
            print('Resumed saved world without changing simulation state.',flush=True)
        elif brain_mode=='full' and (HERE.parent/'init/world_state.json').exists():
            initial=(HERE.parent/'init/world_state.json').read_bytes()
            manifest=json.loads((HERE.parent/'init/manifest.json').read_text(encoding='utf-8'))
            if hashlib.sha256(initial).hexdigest()!=manifest['world_sha256']:raise ValueError('Init checkpoint checksum mismatch')
            data=json.loads(initial)
            self.world=Habitat.restore(data['simulation']);self.paused=True
        else:self.world=Habitat(seed,count,brain_mode)
        if self.world.brains.mode!=brain_mode:raise ValueError('Requested brain mode does not match loaded world')
        self.publish()
        self.flush_events()

    def publish(self):
        state=self.world.public()
        brains={f['id']:self.world.brains.inspect(i) for i,f in enumerate(self.world.flies)}
        self.published=(state,brains)

    def flush_events(self):
        events=self.world.drain_events()
        if events:
            with (self.path/'events.jsonl').open('a',encoding='utf-8') as f:
                for event in events:f.write(json.dumps(dict(event,world_seed=self.world.seed),ensure_ascii=False,allow_nan=False)+'\n')

    def export(self):
        return {'application':'MaleCNS Micro Habitat','schema':SCHEMA,'saved_at':time.strftime('%Y-%m-%dT%H:%M:%S%z'),
                'runtime':{'paused':self.paused,'speed':self.speed},'simulation':self.world.dump(),
                'limitations':'Neural-only actuation with artificial sensory/motor ports and body physics; not physiological equivalence or language evidence.'}

    def save(self):
        data=self.export()
        temporary=self.path/'world_state.json.tmp'
        temporary.write_text(json.dumps(data,ensure_ascii=False,allow_nan=False,separators=(',',':')),encoding='utf-8')
        os.replace(temporary,self.path/'world_state.json')
        self.saved_at=data['saved_at']

    def loop(self):
        last_save=time.monotonic()
        while not self.stop.is_set():
            start=time.monotonic()
            try:
                with self.lock:
                    if not self.paused:
                        for _ in range(1 if self.world.brains.mode=='full' else self.speed):self.world.step()
                        self.publish()
                    self.flush_events()
                    if time.monotonic()-last_save>=(120 if self.world.brains.mode=='full' else 20):
                        self.save();last_save=time.monotonic()
                self.step_ms=(time.monotonic()-start)*1000
            except Exception:
                self.error=traceback.format_exc()
                self.paused=True
                print(self.error,flush=True)
                return
            period=DT/self.speed if self.world.brains.mode in ('full','real') else DT
            self.stop.wait(max(.001,period-(time.monotonic()-start)))

    def command(self,data):
        action=data.get('action');value=data.get('value')
        if self.error:raise RuntimeError('Simulation stopped after an internal error; inspect server.log')
        if action=='pause':
            if type(value) is not bool:raise ValueError('Expected boolean pause state')
            self.paused=value
        elif action=='speed':
            if type(value) is not int or value not in [1,2,4,8]:raise ValueError('Speed must be 1, 2, 4 or 8')
            self.speed=value
        elif action=='step':
            if not self.paused:raise ValueError('请先暂停，再单步观察。')
            self.world.step()
        elif action=='save':self.save()
        elif action=='message':
            return self.world.human_message(data.get('text'),data.get('recipient','all'))
        elif action=='reset':
            seed=data.get('seed',self.world.seed);count=data.get('count',self.world.count)
            if type(seed) is not int or type(count) is not int or not 0<=seed<2**32 or not 1<=count<=24:
                raise ValueError('Invalid seed or population')
            archived=self.path/f'archive-{time.time_ns()}.json'
            archived.write_text(json.dumps(self.export(),ensure_ascii=False,allow_nan=False),encoding='utf-8')
            old_world=self.world
            self.world=Habitat(seed,count,old_world.brains.mode)
            if old_world.brains.mode=='full':old_world.brains.close()
            self.paused=False;self.speed=1;self.save()
        else:self.world.control(action,value)
        self.flush_events()
        self.publish()
        return {'action':action,'t':self.world.t}


def make_handler(runtime):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass

        def reply(self,status,data,ctype='application/json; charset=utf-8',extra=None):
            body=json.dumps(data,ensure_ascii=False,allow_nan=False).encode('utf-8') if not isinstance(data,bytes) else data
            self.send_response(status)
            self.send_header('Content-Type',ctype)
            self.send_header('Content-Length',str(len(body)))
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Cache-Control','no-store' if ctype.startswith('application/json') else 'no-cache')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            if extra:
                for k,v in extra.items():self.send_header(k,v)
            self.end_headers()
            try:self.wfile.write(body)
            except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):pass

        def do_GET(self):
            try:
                parsed=urlparse(self.path)
                if parsed.path=='/api/health':
                    return self.reply(200,{'app':'malecns-habitat','ok':runtime.error is None,'schema':SCHEMA,'port':self.server.server_port,
                        'mode':runtime.world.brains.mode,'nodes':runtime.world.brains.n,'edges':getattr(runtime.world.brains,'edge_count',1606)})
                if parsed.path=='/api/state':
                    selected=parse_qs(parsed.query).get('selected',['F01'])[0]
                    published,brains=runtime.published
                    data=dict(published);selected=selected if selected in brains else next(iter(brains))
                    data['brain']=brains[selected];data['selected']=selected
                    data['runtime']={'paused':runtime.paused,'speed':runtime.speed,'step_ms':round(runtime.step_ms,2),
                        'saved_at':runtime.saved_at,'error':runtime.error,'uptime':time.monotonic()-runtime.started}
                    return self.reply(200,data)
                if parsed.path=='/api/export':
                    with runtime.lock:data=runtime.export()
                    return self.reply(200,data,extra={'Content-Disposition':'attachment; filename="micro-habitat-state.json"'})
                if parsed.path=='/api/topology':
                    b=runtime.world.brains
                    if b.mode=='full':
                        from brain import Brains
                        probe=Brains(1,runtime.world.seed)
                        return self.reply(200,{'ids':probe.ids.tolist(),'pre':probe.col.tolist(),'post':probe.row.tolist(),'sign':np_sign(probe.base),
                            'inputs':probe.input_map.tolist(),'outputs':probe.output_map.tolist(),'display_only':True,
                            'total_nodes':b.n,'total_edges':b.edge_count})
                    return self.reply(200,{'ids':b.ids.tolist(),'pre':b.col.tolist(),'post':b.row.tolist(),'sign':np_sign(b.base),
                        'inputs':b.input_map.tolist(),'outputs':b.output_map.tolist()})
                relative=unquote(parsed.path).lstrip('/') or 'index.html'
                path=(HERE/'ui'/relative).resolve()
                if not path.is_relative_to((HERE/'ui').resolve()) or not path.is_file():
                    return self.reply(404,{'error':'Not found'})
                ctype=mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
                if path.suffix=='.js':ctype='text/javascript; charset=utf-8'
                if path.suffix=='.html':ctype='text/html; charset=utf-8'
                return self.reply(200,path.read_bytes(),ctype)
            except Exception as exc:
                traceback.print_exc()
                self.reply(500,{'error':str(exc)})

        def do_POST(self):
            if self.path!='/api/control':return self.reply(404,{'error':'Not found'})
            origin=self.headers.get('Origin')
            allowed={f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'}
            if origin and origin not in allowed:return self.reply(403,{'error':'Cross-origin control is not allowed'})
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':
                return self.reply(415,{'error':'JSON required'})
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=4096:raise ValueError('Invalid request size')
                data=json.loads(self.rfile.read(length))
                if not isinstance(data,dict):raise ValueError('Expected object')
                if data.get('action')=='shutdown':
                    runtime.stop.set()
                    with runtime.lock:
                        runtime.flush_events();runtime.save()
                    self.reply(200,{'ok':True,'saved':True})
                    threading.Thread(target=self.server.shutdown,daemon=True).start()
                    return
                with runtime.lock:result=runtime.command(data)
                self.reply(200,{'ok':True,'result':result})
            except (ValueError,TypeError,KeyError) as exc:self.reply(400,{'error':str(exc)})
            except Exception as exc:
                traceback.print_exc();self.reply(500,{'error':str(exc)})
    return Handler


def np_sign(a):
    return [1 if float(x)>0 else -1 for x in a]


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--port',type=int,default=8765)
    p.add_argument('--seed',type=int,default=20260913)
    p.add_argument('--flies',type=int,default=12)
    p.add_argument('--data-dir',type=Path,default=HERE/'state')
    p.add_argument('--no-resume',action='store_true')
    p.add_argument('--brain-mode',choices=['full','real','mbon'],default='full')
    p.add_argument('--engineering-sandbox',action='store_true',help='Explicitly run the historical artificial-port/body controller')
    args=p.parse_args()
    if not args.engineering_sandbox:
        p.error('This server is an engineering sandbox. Use --engineering-sandbox explicitly; reviewed physiological I/O and a validated closed loop are not yet available. See REALISM_STATUS.md.')
    runtime=Runtime(args.data_dir,args.seed,args.flies,not args.no_resume,args.brain_mode)
    httpd=ThreadingHTTPServer(('127.0.0.1',args.port),make_handler(runtime))
    thread=threading.Thread(target=runtime.loop,daemon=True);thread.start()
    print(f'Micro Habitat ready: http://127.0.0.1:{args.port}',flush=True)
    try:httpd.serve_forever()
    except KeyboardInterrupt:pass
    finally:
        runtime.stop.set();thread.join(timeout=5)
        with runtime.lock:runtime.save()
        if runtime.world.brains.mode=='full':runtime.world.brains.close()
        httpd.server_close()
