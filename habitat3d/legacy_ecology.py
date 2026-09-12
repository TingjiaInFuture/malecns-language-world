"""Deterministic, partially observed 3D microhabitat. Artificial ecology and symbol protocol."""
from __future__ import annotations
import copy
import json
import math
import re
from collections import deque
import numpy as np
from brain import Brains,INPUTS

SCHEMA = 'habitat3d/1'
DT = .25
DAY = 360.
WORDS = {'food':'糖','water':'水','shade':'荫','danger':'险','empty':'空'}
SECTORS = ('西北','北侧','东北','西侧','中央','东侧','西南','南侧','东南')
PALETTE = ['#e4b66c','#7fc7b1','#92b7e6','#c79dd7','#d99685','#c6ce87',
           '#79bcc5','#c1a482','#e3c893','#89b992','#a5a2d8','#d6a7ba']


def height(x,z):
    return .16*math.sin(x*.18)*math.cos(z*.21)


def sector(x,z):
    return SECTORS[(0 if z < -5 else 2 if z > 5 else 1)*3+(0 if x < -9 else 2 if x > 9 else 1)]


def sector_position(name):
    i=SECTORS.index(name)
    return [(i%3-1)*17.,(i//3-1)*11.]


class Habitat:
    def __init__(self,seed=20260913,count=12,brain_mode='mbon'):
        if not 1 <= count <= 24 or not 0 <= seed < 2**32:
            raise ValueError('Population must be 1..24; seed must be a uint32')
        self.seed,self.count,self.t,self.tick = seed,count,0.,0
        self.rng = np.random.default_rng(np.random.SeedSequence([seed,1]))
        self.move_rng = [np.random.default_rng(np.random.SeedSequence([seed,2,i])) for i in range(count)]
        self.social_rng = [np.random.default_rng(np.random.SeedSequence([seed,3,i])) for i in range(count)]
        if brain_mode=='full':
            from full_brain import FullBrains
            self.brains=FullBrains(count,seed)
        elif brain_mode=='mbon':self.brains=Brains(count,seed)
        else:raise ValueError('Unknown brain mode')
        self.communication,self.plasticity,self.neural_enabled = True,True,True
        if brain_mode=='full':self.plasticity=False
        self.events = deque(maxlen=100)
        self.pending_events=[]
        self.history=deque(maxlen=360)
        self.messages=deque(maxlen=120)
        self.event_id=0
        self.metrics={'sent':0,'received':0,'followed':0,'verified':0,'failed':0,'meals':0,'drinks':0,'shelter_visits':0,'deaths':0}
        self.weather_override=None
        self.weather={'rain':0.,'light':.7,'heat':.65,'wind':[.3,.1],'label':'晴 · 微风'}
        self.last_weather=''
        self.resources=[]
        specs=[('food',-18.,-8.,3.0,False,'发酵无花果'),('water',16.,-7.,2.3,False,'石面露水'),
               ('shade',-12.,9.,4.4,True,'卷叶庇护'),('food',17.,10.,2.7,False,'熟落果'),
               ('water',-19.,3.,1.8,True,'叶下积水'),('shade',12.,-12.,4.,True,'蕨叶阴影')]
        for i,(kind,x,z,r,protected,label) in enumerate(specs):
            self.resources.append({'id':f'R{i+1}','kind':kind,'x':x,'z':z,'radius':r,'protected':protected,
                'label':label,'amount':1. if kind=='shade' else .85,'ripeness':.85,'phase':80.+i*37.,'suppressed_until':0.})
        self.rocks=[{'x':-2.,'z':-8.,'r':2.4,'height':2.2},{'x':4.,'z':8.,'r':2.,'height':1.8},
                    {'x':22.,'z':-1.,'r':1.8,'height':1.4},{'x':-22.,'z':-12.,'r':1.6,'height':1.2}]
        self.flies=[]
        for i in range(count):
            rng=self.move_rng[i]
            centers=[(-10.,-6.),(10.,-5.),(0.,7.)]
            x,z=np.asarray(centers[i%3])+rng.uniform(-3,3,2)
            self.flies.append({'id':f'F{i+1:02d}','color':PALETTE[i%12],'x':float(x),'z':float(z),'y':1.8,
                'heading':float(rng.uniform(-math.pi,math.pi)),'energy':float(rng.uniform(.5,.88)),
                'hydration':float(rng.uniform(.46,.85)),'fatigue':float(rng.uniform(.05,.3)),'age':float(rng.uniform(0,2)),
                'alive':True,'state':'探索','target':None,'memory':{},'hint':None,'directive':None,'trust':{},
                'next_decision':0.,'next_signal':float(3+i*1.7),'next_explore':0.,'trail':[],
                'experience':0,'helped':0,'last_word':None,'last_signal_t':-100.,'travel':0.,'sheltered':False,
                'speed':0.,'last_reward':0.,'failure_wait':0.})
        self.emit('system','微境开始运行','昼夜、资源与个体经验将持续变化。')

    def emit(self,kind,title,detail='',**extra):
        self.event_id+=1
        e={'id':self.event_id,'t':round(self.t,3),'kind':kind,'title':title,'detail':detail,**extra}
        self.events.append(e)
        self.pending_events.append(copy.deepcopy(e))
        return e

    def drain_events(self):
        result=self.pending_events
        self.pending_events=[]
        return result

    @staticmethod
    def available(r):
        return r['kind']=='shade' or (r['amount']>.025 and (r['kind']!='food' or r['ripeness']>.18))

    def climate(self):
        phase=(self.t%DAY)/DAY
        light=max(.04,.5+.5*math.sin(phase*2*math.pi))
        # Exogenous cycles do not consume agent random streams.
        rain=max(0.,math.sin((self.t-40)*2*math.pi/620)-.64)/.36
        if self.weather_override and self.t < self.weather_override['until']:
            rain=self.weather_override['rain']
        heat=.25+.65*light-.3*rain
        label='阵雨' if rain>.22 else '夜露' if light<.2 else '午后偏热' if heat>.83 else '晴 · 微风'
        wind=[.45*math.cos(self.t/85),.32*math.sin(self.t/110)]
        self.weather={'rain':float(rain),'light':float(light),'heat':float(heat),'wind':wind,'label':label}
        if label!=self.last_weather:
            self.last_weather=label
            self.emit('weather',label,'环境改变，个体仍需依照本地感知和记忆行动。')

    def perceive(self,f):
        seen=[]
        for r in self.resources:
            d=math.hypot(f['x']-r['x'],f['z']-r['z'])
            radius=10 if r['kind']=='food' else 8
            if d <= radius:
                seen.append(r)
                previous=f['memory'].get(r['id'])
                available=self.available(r)
                # Do not repeatedly pursue a nearly empty patch as tiny replenishment
                # crosses the consumption threshold each tick.
                if previous and not previous['available'] and r['kind']!='shade':
                    available=available and r['amount']>=.08
                f['memory'][r['id']]={'kind':r['kind'],'x':r['x'],'z':r['z'],'at':self.t,
                                     'available':available,'source':'local'}
        f['memory']={k:v for k,v in f['memory'].items() if self.t-v['at']<180}
        return seen

    def send(self,f,r=None,kind=None):
        if not self.communication or not f['alive']:
            return None
        if r is not None:
            limit=10 if r['kind']=='food' else 8
            if math.hypot(f['x']-r['x'],f['z']-r['z']) > limit:
                raise ValueError('Cannot broadcast an unobserved resource')
            kind=r['kind'] if self.available(r) else 'empty'
            place=sector(r['x'],r['z'])
        else:
            kind=kind or 'danger'
            place=sector(f['x'],f['z'])
        packet={'sender':f['id'],'kind':kind,'word':WORDS[kind],'sector':place,'t':self.t,
                'origin':[f['x'],f['y'],f['z']], 'human':False}
        return self.broadcast(packet)

    def broadcast(self,packet):
        if not self.communication:
            return None
        packet=dict(packet,id=self.event_id+1,recipients=[])
        for f in self.flies:
            if not f['alive'] or f['id']==packet['sender']:
                continue
            if not packet['human'] and math.hypot(f['x']-packet['origin'][0],f['z']-packet['origin'][2])>18:
                continue
            self.metrics['received']+=1
            packet['recipients'].append(f['id'])
            if packet['kind'] in ['food','water','shade']:
                trust=f['trust'].get(packet['sender'],[2.,1.])
                confidence=trust[0]/sum(trust)
                if self.social_rng[int(f['id'][1:])-1].random()<confidence:
                    # No sender resource ID or exact resource coordinates enter the receiver hint.
                    hint={k:packet[k] for k in ['id','sender','kind','word','sector','t']}
                    hint.update(used=False,confidence=confidence)
                    if not f['hint'] or not f['hint'].get('used'):
                        f['hint']=hint
            elif packet['kind']=='danger':
                f['directive']={'kind':'shade','until':self.t+40,'from':'signal'}
            elif packet['kind']=='empty':
                for m in f['memory'].values():
                    if sector(m['x'],m['z'])==packet['sector']:
                        m['available']=False
        self.metrics['sent']+=1
        self.messages.append(packet)
        sender=next((f for f in self.flies if f['id']==packet['sender']),None)
        if sender:
            sender['last_word']=packet['word']+' · '+packet['sector']
            sender['last_signal_t']=self.t
        self.emit('signal',f"{packet['sender']}  ·  {packet['word']}，{packet['sector']}",
                  f"{len(packet['recipients'])} 个体接收 · 有限词符协议",packet=packet)
        return packet

    def resolve(self,f,success):
        h=f['hint']
        if not h or not h['used']:
            return
        trust=f['trust'].setdefault(h['sender'],[2.,1.])
        trust[0 if success else 1]+=1
        self.metrics['verified' if success else 'failed']+=1
        f['experience']+=1
        sender=next((s for s in self.flies if s['id']==h['sender']),None)
        if success and sender:
            sender['helped']+=1
        self.emit('verified' if success else 'miss',f"{f['id']} {'验证了线索' if success else '未找到线索资源'}",
                  f"来自 {h['sender']}：{h['word']} · {h['sector']}，{'亲自接触后确认' if success else '线索可能已过期'}",
                  fly=f['id'],sender=h['sender'],message_id=h['id'])
        f['hint']=None

    def observation(self,f,seen):
        x=np.zeros(len(INPUTS),np.float32)
        x[:7]=[1-f['energy'],1-f['hydration'],f['fatigue'],self.weather['light'],self.weather['rain'],self.weather['heat'],
               sum(math.hypot(f['x']-g['x'],f['z']-g['z'])<3 for g in self.flies if g['alive'] and g['id']!=f['id'])/5]
        for r in seen:
            if not self.available(r):continue
            relative=math.atan2(r['x']-f['x'],r['z']-f['z'])-f['heading']
            side=0 if math.sin(relative)<0 else 1
            strength=1/(1+math.hypot(r['x']-f['x'],r['z']-f['z'])/3)
            if r['kind'] in ['food','water']:
                j=(7 if r['kind']=='food' else 9)+side
                x[j]=max(x[j],strength)
            elif r['kind']=='shade':x[11]=max(x[11],strength)
        x[12:15]=[*self.weather['wind'],f['speed']/3]
        if self.communication:
            h=f['hint']
            if h and self.t-h['t']<65:
                x[{'food':15,'water':16,'shade':17}[h['kind']]]=h['confidence']
            if f['directive'] and f['directive']['until']>self.t:
                x[{'food':15,'water':16,'shade':17}[f['directive']['kind']]]=1
        x[19:]=[f['energy'],f['hydration'],f['age']/30,1.,1/(1+len(f['memory']))]
        return x

    def decide(self,f,output):
        if self.t < f['next_decision']:
            return
        f['next_decision']=self.t+1.5
        drives=np.array([1-f['energy'],1-f['hydration'],.65*f['fatigue']+.65*self.weather['rain']+
                         .32*(1-self.weather['light']),.28])+.18*output[:4]
        shelter_needed=(self.weather['rain']>.22 or self.weather['light']<.2 or
                        f['fatigue']>.3 or (f.get('was_resting') and f['fatigue']>.08))
        if not shelter_needed:drives[2]=-.5
        if f['directive'] and self.t < f['directive']['until'] and self.communication:
            drives[['food','water','shade'].index(f['directive']['kind'])]+=.5
        kind=['food','water','shade','explore'][int(np.argmax(drives))]
        current=f['target']
        if current and current['kind'] in ['food','water','shade']:
            j=['food','water','shade'].index(current['kind'])
            valid=(current['source']=='local' and any(m['available'] and m['kind']==current['kind'] and
                   m['x']==current['x'] and m['z']==current['z'] for m in f['memory'].values())) or (
                   current['source']=='signal' and self.communication and f['hint'] and
                   self.t-f['hint']['t']<65)
            # Hysteresis prevents opposite destinations flipping every 1.5 seconds.
            # A sufficiently stronger need still interrupts the current intention.
            satisfied=(j==0 and f['energy']>=.9) or (j==1 and f['hydration']>=.9) or (j==2 and not shelter_needed)
            if valid and not satisfied and drives[j]+.18>=max(drives):kind=current['kind']
        candidates=[m for m in f['memory'].values() if m['kind']==kind and m['available']]
        best=min(candidates,key=lambda m:math.hypot(m['x']-f['x'],m['z']-f['z']),default=None)
        if best:
            f['target']={'kind':kind,'x':best['x'],'z':best['z'],'source':'local'}
        elif f['hint'] and self.communication and f['hint']['kind']==kind and self.t-f['hint']['t']<65:
            h=f['hint']
            if output[7] > -.8:
                x,z=sector_position(h['sector'])
                if not h['used']:
                    h['used']=True
                    h['used_at']=self.t
                    self.metrics['followed']+=1
                    self.emit('follow',f"{f['id']} 开始调查线索",f"{h['word']} · {h['sector']}，尚未验证",fly=f['id'])
                if not (f['target'] and f['target']['source']=='signal' and f['target'].get('message_id')==h['id']):
                    f['target']={'kind':kind,'x':x,'z':z,'source':'signal','message_id':h['id']}
        elif not f['target'] or f['target'].get('kind')!='explore' or self.t>=f['next_explore']:
            rng=self.move_rng[int(f['id'][1:])-1]
            angle=rng.uniform(-math.pi,math.pi)
            radius=rng.uniform(4,23)
            f['target']={'kind':'explore','x':float(math.sin(angle)*radius),'z':float(math.cos(angle)*radius*.63),'source':'explore'}
            f['next_explore']=self.t+10
        if f['hint'] and (self.t-f['hint']['t']>65 or (f['hint']['used'] and self.t-f['hint']['used_at']>35)):
            self.resolve(f,False)
            f['hint']=None
            if f['target'] and f['target']['source']=='signal': f['target']=None

    def step(self,dt=DT):
        if abs(dt-DT)>1e-9:
            raise ValueError('Simulation uses fixed 0.25 model-second steps')
        self.t+=dt
        self.tick+=1
        self.climate()
        for r in self.resources:
            if r['kind']=='food':
                phase=(self.t+r['phase'])%480
                r['ripeness']=float(np.clip(math.sin(phase/480*math.pi),.05,1))
                r['amount']=min(1,r['amount']+dt*.0015*r['ripeness'])
                if phase>430:r['amount']=max(0,r['amount']-dt*.001)
            elif r['kind']=='water':
                rate=.007*self.weather['rain']+.0009*(1-self.weather['light'])-.0007*self.weather['heat']*(.3 if r['protected'] else 1)
                r['amount']=float(np.clip(r['amount']+dt*rate,0,1)) if self.t>=r['suppressed_until'] else 0.
        seen=[self.perceive(f) if f['alive'] else [] for f in self.flies]
        obs=np.stack([self.observation(f,s) if f['alive'] else np.zeros(len(INPUTS),np.float32) for f,s in zip(self.flies,seen)])
        outputs=self.brains.forward(obs,dt,self.neural_enabled)
        rewards=np.zeros(self.count,np.float32)
        for i,f in enumerate(self.flies):
            if not f['alive']:continue
            self.decide(f,outputs[i])
            target=f['target']
            sheltered=any(r['kind']=='shade' and math.hypot(f['x']-r['x'],f['z']-r['z'])<r['radius'] for r in self.resources)
            f['sheltered']=sheltered
            resting=False
            consumed=False
            f['energy']-=dt*.0007
            f['hydration']-=dt*(.0007+.0005*self.weather['heat'])
            f['age']+=dt/DAY
            f['state']='探索'
            for r in seen[i]:
                close=math.hypot(f['x']-r['x'],f['z']-r['z'])<r['radius']
                if not close or not self.available(r):continue
                if r['kind']=='shade' and target and target['kind']=='shade' and (self.weather['rain']>.22 or f['fatigue']>.08 or self.weather['light']<.2):
                    if f['state'] not in ['避雨','休息'] and not f.get('was_resting'):
                        self.metrics['shelter_visits']+=1
                    resting=True
                    f['state']='避雨' if self.weather['rain']>.22 else '休息'
                    f['fatigue']=max(0,f['fatigue']-.014*dt)
                    rewards[i]+=.018*dt
                    if f['hint'] and f['hint']['used'] and f['hint']['kind']=='shade' and sector(r['x'],r['z'])==f['hint']['sector']:
                        self.resolve(f,True)
                if r['kind'] not in ['food','water']:continue
                need='energy' if r['kind']=='food' else 'hydration'
                if f[need]>.94:continue
                occupants=sum(g['alive'] and math.hypot(g['x']-r['x'],g['z']-r['z'])<r['radius'] for g in self.flies)
                amount=min(r['amount'],.007*dt/max(1,occupants/2))
                r['amount']-=amount
                f[need]=min(1,f[need]+amount*5)
                f['state']='进食' if r['kind']=='food' else '饮水'
                consumed=True
                rewards[i]+=amount*6
                if f.get('last_consumed')!=r['id']:
                    self.metrics['meals' if r['kind']=='food' else 'drinks']+=1
                    f['experience']+=1
                f['last_consumed']=r['id']
                if f['hint'] and f['hint']['used'] and f['hint']['kind']==r['kind'] and sector(r['x'],r['z'])==f['hint']['sector']:
                    self.resolve(f,True)
            f['was_resting']=resting
            if not consumed:f['last_consumed']=None
            speed=0. if (resting or consumed) else 1.7+.4*(1-f['fatigue'])
            if self.weather['rain']>.25 and not sheltered:
                speed*=.7
                f['energy']-=dt*.0008*self.weather['rain']
                rewards[i]-=.005*dt*self.weather['rain']
            if speed and target:
                dx,dz=target['x']-f['x'],target['z']-f['z']
                distance=math.hypot(dx,dz)
                if distance<1.:
                    if target['source']=='explore':
                        f['next_explore']=self.t;f['next_decision']=self.t
                    # Search within the reported sector rather than knowing the hidden resource coordinate.
                    if target['source']=='signal':
                        rng=self.move_rng[i]
                        target['x']=float(np.clip(target['x']+rng.uniform(-4,4),-26,26))
                        target['z']=float(np.clip(target['z']+rng.uniform(-3,3),-16,16))
                        dx,dz=target['x']-f['x'],target['z']-f['z']
                        distance=math.hypot(dx,dz)
                speed=min(speed,distance/dt)
                if target['source']=='local' and distance<.8:
                    speed=0.;f['next_decision']=self.t
                desired=math.atan2(dx,dz)+.1*float(outputs[i,5]-outputs[i,4])
                for rock in self.rocks:
                    rx,rz=f['x']-rock['x'],f['z']-rock['z']
                    d=math.hypot(rx,rz)
                    if d<rock['r']+1.7 and f['y']<rock['height']+1:
                        desired=math.atan2(dx+rx*6/(d+.1),dz+rz*6/(d+.1))
                turn=(desired-f['heading']+math.pi)%(2*math.pi)-math.pi
                f['heading']+=float(np.clip(turn,-dt*3,dt*3))
                f['x']+=math.sin(f['heading'])*speed*dt
                f['z']+=math.cos(f['heading'])*speed*dt
                norm=math.sqrt((f['x']/27.5)**2+(f['z']/17.5)**2)
                if norm>1:
                    f['x']/=norm; f['z']/=norm
                f['travel']+=speed*dt
                f['fatigue']=min(1,f['fatigue']+dt*.0011)
                f['energy']-=dt*.0003
                f['state']=('循声调查' if target['source']=='signal' else {'food':'觅食','water':'寻水','shade':'寻找庇护','explore':'探索'}[target['kind']])
            floor=height(f['x'],f['z'])+.4
            target_y=floor if not speed or self.weather['rain']>.55 else floor+1.6+.3*math.sin(self.t*.6+i)
            f['y']+=float(np.clip(target_y-f['y'],-dt*1.8,dt*1.8))
            f['speed']=speed
            f['last_reward']=float(rewards[i])
            if self.communication and self.t>=f['next_signal']:
                options=[r for r in seen[i] if self.available(r) and
                         math.hypot(f['x']-r['x'],f['z']-r['z']) <= (10 if r['kind']=='food' else 8)]
                if options and outputs[i,6]>-.9:
                    # A perceived item only; no access to distant resources in sender selection.
                    r=options[int(self.social_rng[i].integers(len(options)))]
                    self.send(f,r)
                elif self.weather['rain']>.4 and not sheltered:
                    self.send(f,kind='danger')
                f['next_signal']=self.t+22+float(self.social_rng[i].uniform(0,12))
            if f['energy']<=0 or f['hydration']<=0 or f['age']>40:
                f['alive']=False;f['state']='死亡';f['speed']=0.
                f['energy']=max(0,f['energy']);f['hydration']=max(0,f['hydration'])
                self.metrics['deaths']+=1
                self.emit('death',f"{f['id']} 停止活动",'个体不会自动复活。可保留存档后新建世界。',fly=f['id'])
            if self.tick%4==0:
                f['trail']=(f['trail']+[[round(f['x'],3),round(f['y'],3),round(f['z'],3)]])[-36:]
        self.brains.learn(rewards,self.plasticity and self.neural_enabled)
        if self.tick%8==0:
            alive=[f for f in self.flies if f['alive']]
            self.history.append({'t':self.t,'alive':len(alive),'energy':float(np.mean([f['energy'] for f in alive])) if alive else 0.,
                'hydration':float(np.mean([f['hydration'] for f in alive])) if alive else 0.,'sent':self.metrics['sent'],
                'verified':self.metrics['verified'],'gain':float(np.mean(np.abs(self.brains.theta)))})

    def control(self,action,value=None):
        if action in ['communication','plasticity','neural_enabled']:
            if type(value) is not bool:raise ValueError('Expected boolean')
            if self.brains.mode=='full' and ((action=='plasticity' and value) or (action=='neural_enabled' and not value)):
                raise ValueError('全量模式保持公开结构权重固定，不能跳过全图计算。')
            setattr(self,action,value)
            if action=='communication' and not value:
                for f in self.flies:
                    f['hint']=None;f['directive']=None
                    if f['target'] and f['target']['source']=='signal':f['target']=None
            self.emit('control',{'communication':'交流通道','plasticity':'连接可塑性','neural_enabled':'神经调节'}[action]+('已开启' if value else '已关闭'))
        elif action=='rain':
            self.weather_override={'rain':.9,'until':self.t+75}
            self.emit('control','观察者引入阵雨','持续 75 模型秒，个体通过本地环境感知作出反应。')
        elif action=='dry':
            for r in self.resources:
                if r['kind']=='water':r['amount']=0.;r['suppressed_until']=self.t+90
            self.emit('control','露水暂时蒸干','90 模型秒后恢复自然补水过程；已有线索可能失效。')
        elif action=='fruit':
            for r in self.resources:
                if r['kind']=='food':r['amount']=1.
            self.emit('control','观察者补充果实','只有接近补给点的个体能直接发现变化。')
        else:raise ValueError('Unsupported ecology action')

    def human_message(self,text,recipient='all'):
        if not self.communication:raise ValueError('交流通道已关闭，请先开启。')
        if not isinstance(text,str) or len(text)>80:raise ValueError('输入不超过 80 字的有限词符。')
        clean=text.strip().replace('，',' ').replace('。','').replace('！','')
        match=re.fullmatch(r'(找水|水|找糖|糖|食物|避雨|荫|阴影)(?:\s*在?\s*('+'|'.join(SECTORS)+r'))?',clean)
        if not match:raise ValueError('支持：找水、找糖、避雨，或 水在东侧 / 糖在西北 / 荫在南侧。')
        kind={'找水':'water','水':'water','找糖':'food','糖':'food','食物':'food','避雨':'shade','荫':'shade','阴影':'shade'}[match[1]]
        targets=self.flies if recipient=='all' else [f for f in self.flies if f['id']==recipient]
        if not targets:raise ValueError('个体不存在。')
        place=match[2]
        if place:
            if recipient!='all':raise ValueError('带方位的线索使用全体广播；个体提示可用“找水”。')
            packet={'sender':'观察者','kind':kind,'word':WORDS[kind],'sector':place,'t':self.t,'origin':[0,0,0],'human':True}
            self.broadcast(packet)
        else:
            for f in targets:
                if f['alive']:f['directive']={'kind':kind,'until':self.t+50,'from':'human'};f['next_decision']=self.t
            self.emit('human',f"观察者发送：{WORDS[kind]}",'暂时提高相应需求优先级；没有提供目标坐标。',recipient=recipient)
        return {'word':WORDS[kind],'sector':place,'recipient':recipient}

    def public(self,selected='F01'):
        flies=[]
        for f in self.flies:
            copy_fields=['id','color','x','y','z','heading','energy','hydration','fatigue','age','alive','state','speed','trail',
                         'experience','helped','last_word','last_signal_t','travel','sheltered','hint','target']
            row={k:copy.deepcopy(f[k]) for k in copy_fields}
            row['known']=len(f['memory'])
            row['gain_change']=float(np.mean(np.abs(self.brains.theta[int(f['id'][1:])-1])))
            row['neural_rms']=self.brains.rms(int(f['id'][1:])-1)
            flies.append(row)
        index=next((i for i,f in enumerate(self.flies) if f['id']==selected),0)
        return {'schema':SCHEMA,'seed':self.seed,'t':self.t,'tick':self.tick,'day':int(self.t//DAY)+1,'day_phase':(self.t%DAY)/DAY,
                'weather':copy.deepcopy(self.weather),'flies':flies,'resources':copy.deepcopy(self.resources),'rocks':self.rocks,
                'metrics':dict(self.metrics),'events':list(self.events)[-45:],'history':list(self.history),
                'messages':[copy.deepcopy(m) for m in self.messages if self.t-m['t']<8],
                'communication':self.communication,'plasticity':self.plasticity,'neural_enabled':self.neural_enabled,
                'brain':self.brains.inspect(index),'selected':self.flies[index]['id'],
                'provenance':{'dataset':'male-cns:v1.0','mode':self.brains.mode,'nodes':self.brains.n,'edges':getattr(self.brains,'edge_count',1606),'graph_sha256':self.brains.sha,
                    'controller':'homeostasis + engineered navigation + connectome recurrent modulation',
                    'language':'人工有限词符协议；经验与信任更新，不是人类语言涌现',
                    'biology':('全量公开分割连接图；结构计数不等于生理权重；混合工程控制器' if self.brains.mode=='full' else '真实连接数据子图；未生理校准的身体与生态模型；非完整果蝇仿真')}}

    def dump(self):
        attributes=['seed','count','t','tick','communication','plasticity','neural_enabled','event_id','metrics',
                    'weather_override','weather','last_weather','resources','rocks','flies']
        return {'schema':SCHEMA,'world':{k:copy.deepcopy(getattr(self,k)) for k in attributes},
                'events':list(self.events),'history':list(self.history),'messages':list(self.messages),
                'rng':self.rng.bit_generator.state,'move_rng':[r.bit_generator.state for r in self.move_rng],
                'social_rng':[r.bit_generator.state for r in self.social_rng],'brains':self.brains.dump()}

    @classmethod
    def restore(cls,data):
        if data.get('schema')!=SCHEMA:raise ValueError('Unsupported habitat save version')
        w=data['world'];obj=cls(w['seed'],w['count'],data['brains'].get('mode','mbon'))
        for k in ['seed','count','t','tick','communication','plasticity','neural_enabled','event_id','metrics',
                  'weather_override','weather','last_weather','resources','rocks','flies']:
            setattr(obj,k,copy.deepcopy(w[k]))
        obj.events=deque(data['events'],maxlen=100);obj.history=deque(data['history'],maxlen=360)
        obj.messages=deque(data['messages'],maxlen=120);obj.pending_events=[]
        obj.rng.bit_generator.state=data['rng']
        for rng,s in zip(obj.move_rng,data['move_rng']):rng.bit_generator.state=s
        for rng,s in zip(obj.social_rng,data['social_rng']):rng.bit_generator.state=s
        obj.brains.restore(data['brains'])
        if len(obj.flies)!=obj.count or not math.isfinite(obj.t):raise ValueError('Invalid habitat save')
        return obj
