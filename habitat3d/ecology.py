"""Neural-only actuation; artificial sensors and passive body/environment mechanics.

No target planner, behavioral arbitration, random exploration or semantic messages.
The environment module supplies passive world construction and serialization.
"""
import copy
import math
import numpy as np
from environment import Environment, DT, DAY, height, sector

SCHEMA = 'habitat3d/2'
SENSORS = ('hunger','thirst','fatigue','light','rain','heat','touch',
           'odor_left','odor_right','humidity_left','humidity_right','shade',
           'wind_forward','wind_side','speed','signal_a_left','signal_a_right',
           'signal_b_left','signal_b_right','energy','hydration','altitude','contact','vertical_speed')
MOTORS = ('left_thrust','right_thrust','lift','proboscis','pump','signal_a','signal_b','brake')

class Habitat(Environment):
    def __init__(self,seed=20260913,count=12,brain_mode='full'):
        super().__init__(seed,count,brain_mode)
        self.plasticity=False
        for f in self.flies:
            f.update(vx=0.,vz=0.,vy=0.,touch=0.,signal=[0.,0.],motors=[0.]*8,state='静止')
            f['y']=height(f['x'],f['z'])+.4
        self.events.clear();self.pending_events=[];self.event_id=0
        self.emit('system','神经自主世界初始化','动作仅来自神经输出；感觉与身体模型未生理校准。')

    # Explicitly reject all legacy behavioral entry points.
    def decide(self,*args):raise RuntimeError('Behavior planner removed')
    def send(self,*args,**kwargs):raise RuntimeError('Semantic broadcasting removed')
    def broadcast(self,*args):raise RuntimeError('Semantic broadcasting removed')
    def resolve(self,*args):raise RuntimeError('Semantic trust learning removed')
    def human_message(self,*args,**kwargs):raise ValueError('此模式没有预设词义或人类行为指令；请通过环境干预观察。')
    def perceive(self,f):return []  # no resource identity/coordinate memory

    def observation(self,f,seen=None):
        x=np.zeros(24,np.float32)
        floor=height(f['x'],f['z'])+.4
        x[:7]=[1-f['energy'],1-f['hydration'],f['fatigue'],self.weather['light'],
               self.weather['rain'],self.weather['heat'],f['touch']]
        # Two separated receptors sample scalar fields, not bearings or targets.
        for side,offset in enumerate((-.35,.35)):
            sx=f['x']+math.cos(f['heading'])*offset
            sz=f['z']-math.sin(f['heading'])*offset
            for r in self.resources:
                d2=(sx-r['x'])**2+(sz-r['z'])**2+(f['y']-height(sx,sz))**2
                if r['kind']=='food':x[7+side]+=r['amount']*r['ripeness']*math.exp(-d2/32)
                elif r['kind']=='water':x[9+side]+=r['amount']*math.exp(-d2/18)
                elif d2<r['radius']**2:x[11]=1.
            if self.communication:
                for g in self.flies:
                    if g is f or not g['alive']:continue
                    d2=(sx-g['x'])**2+(sz-g['z'])**2+(f['y']-g['y'])**2
                    attenuation=math.exp(-d2/32)
                    x[15+side]+=g['signal'][0]*attenuation
                    x[17+side]+=g['signal'][1]*attenuation
        wx,wz=self.weather['wind'];a=f['heading']
        x[12:15]=[wx*math.sin(a)+wz*math.cos(a),wx*math.cos(a)-wz*math.sin(a),f['speed']/3]
        x[19:]=[f['energy'],f['hydration'],max(0,f['y']-floor)/6,float(f['y']<=floor+1e-6),f['vy']/3]
        return np.clip(x,-1,1)

    def environment_step(self,dt):
        self.t+=dt;self.tick+=1;self.climate()
        for r in self.resources:
            if r['kind']=='food':
                phase=(self.t+r['phase'])%480
                r['ripeness']=float(np.clip(math.sin(phase/480*math.pi),.05,1))
                r['amount']=min(1,r['amount']+dt*.0015*r['ripeness'])
                if phase>430:r['amount']=max(0,r['amount']-dt*.001)
            elif r['kind']=='water':
                rate=.007*self.weather['rain']+.0009*(1-self.weather['light'])-.0007*self.weather['heat']*(.3 if r['protected'] else 1)
                r['amount']=float(np.clip(r['amount']+dt*rate,0,1)) if self.t>=r['suppressed_until'] else 0.

    def actuate(self,f,output,dt):
        """Fixed local transducer: no goal, resource location or need chooses action."""
        u=np.clip(np.asarray(output,dtype=float),-1,1)
        if u.shape!=(8,) or not np.isfinite(u).all():raise ValueError('Invalid motor output')
        if not f['alive']:u=np.zeros(8)
        f['motors']=u.tolist()
        left,right,lift,extend,pump,sa,sb,brake=np.maximum(u,0)
        f['signal']=[float(sa),float(sb)] if self.communication else [0.,0.]
        f['heading']=(f['heading']+3*(right-left)*dt+math.pi)%(2*math.pi)-math.pi
        thrust=4*(left+right)
        exposure=self.weather['rain']*(0. if f['sheltered'] else 1.)
        drag=2+4*brake+exposure
        f['vx']=(f['vx']+dt*thrust*math.sin(f['heading']))/(1+dt*drag)
        f['vz']=(f['vz']+dt*thrust*math.cos(f['heading']))/(1+dt*drag)
        f['vy']=(f['vy']+dt*(12*lift-3))/(1+dt)
        oldx,oldz=f['x'],f['z']
        f['x']+=dt*f['vx'];f['z']+=dt*f['vz'];f['y']+=dt*f['vy']
        f['touch']=0.
        norm=math.hypot(f['x']/27.5,f['z']/17.5)
        if norm>1:
            f['x']/=norm;f['z']/=norm;f['vx']=f['vz']=0.;f['touch']=1.
        floor=height(f['x'],f['z'])+.4
        # Solid vertical rock columns: collision stops penetration; never steers.
        for r in self.rocks:
            dx,dz=f['x']-r['x'],f['z']-r['z'];d=math.hypot(dx,dz)
            if d<r['r']+.25 and f['y']<floor+r['height']:
                f['x'],f['z']=oldx,oldz;f['vx']=f['vz']=0.;f['touch']=1.
        floor=height(f['x'],f['z'])+.4
        if f['y']<=floor:f['y']=floor;f['vy']=max(0.,f['vy'])
        if f['y']>6:f['y']=6.;f['vy']=min(0.,f['vy']);f['touch']=1.
        distance=math.hypot(f['x']-oldx,f['z']-oldz)
        f['speed']=distance/dt;f['travel']+=distance
        f['sheltered']=any(r['kind']=='shade' and math.hypot(f['x']-r['x'],f['z']-r['z'])<r['radius'] and f['y']<2 for r in self.resources)
        effort=float(left+right+lift+extend*pump+sa+sb)
        f['energy']=max(0.,f['energy']-dt*(.0007+.0004*effort+.0008*exposure))
        f['hydration']=max(0.,f['hydration']-dt*(.0007+.0005*self.weather['heat']+.0001*effort))
        f['fatigue']=float(np.clip(f['fatigue']+dt*(.002*effort-.001),0,1))
        f['age']+=dt/DAY
        f['state']='运动' if distance>1e-8 or abs(f['vy'])>1e-8 else '静止'
        consumed=None
        for r in self.resources:
            if r['kind'] not in ('food','water'):continue
            contact=math.hypot(f['x']-r['x'],f['z']-r['z'])<r['radius'] and f['y']<=floor+.15
            # Ingestion requires BOTH neural mouth actuators, even when starving.
            if not contact:continue
            key='energy' if r['kind']=='food' else 'hydration'
            amount=min(r['amount'],.007*dt*extend*pump,(1-f[key])/5)
            if amount<=0:continue
            r['amount']-=amount;f[key]+=5*amount;consumed=r['id']
            f['state']='进食' if key=='energy' else '饮水'
            if f.get('last_consumed')!=consumed:self.metrics['meals' if key=='energy' else 'drinks']+=1
        f['last_consumed']=consumed
        if f['energy']<=0 or f['hydration']<=0 or f['age']>40:
            if f['alive']:self.metrics['deaths']+=1;self.emit('death',f['id']+' 停止活动','没有自动救援或复活。')
            f.update(alive=False,state='死亡',signal=[0.,0.],speed=0.)
        if self.tick%4==0:f['trail']=(f['trail']+[[f['x'],f['y'],f['z']]])[-36:]

    def step(self,dt=DT):
        if abs(dt-DT)>1e-9:raise ValueError('Fixed step required')
        self.environment_step(dt)
        obs=np.stack([self.observation(f) if f['alive'] else np.zeros(24,np.float32) for f in self.flies])
        outputs=self.brains.forward(obs,dt,True)
        # Synchronous sensing: signals from this step are heard next step.
        for f,u in zip(self.flies,outputs):self.actuate(f,u,dt)
        if self.tick%8==0:
            alive=[f for f in self.flies if f['alive']]
            self.history.append({'t':self.t,'alive':len(alive),'energy':float(np.mean([f['energy'] for f in alive])) if alive else 0.,
                'hydration':float(np.mean([f['hydration'] for f in alive])) if alive else 0.,'sent':0,'verified':0,'gain':0.})

    def control(self,action,value=None):
        if action in ('plasticity','neural_enabled'):raise ValueError('神经自主模式不支持绕过神经核心或修改结构权重。')
        if action=='communication':
            if type(value) is not bool:raise ValueError('Expected boolean')
            self.communication=value
            if not value:
                for f in self.flies:f['signal']=[0.,0.]
            self.emit('control','无语义信号通道'+('开启' if value else '关闭'));return
        super().control(action,value)

    def public(self,selected='F01'):
        data=super().public(selected);data['schema']=SCHEMA
        text = ('真实 MaleCNS 98 节点左前胫节回路（生产端口+已发表 hook 身份）；被动 FeCO 式磁刺激协议；'
                '输出为观察投影；生态身体未生理校准' if self.brains.mode == 'real' else
                '完整结构图和假设神经动力学；感觉/动作端口与身体参数尚未生理校准')
        data['provenance'].update(controller='neural-only-actuation-v1',language='两路连续无语义信号；无预设词义、指令或语言能力证据',
            biology=text)
        data['brain']['outputs']=dict(zip(MOTORS,self.brains.last_output[int(data['selected'][1:])-1].tolist()))
        for row,f in zip(data['flies'],self.flies):row.update(motors=list(f['motors']),signal=list(f['signal']))
        return data

    def dump(self):
        data=super().dump();data['schema']=SCHEMA;data['controller']='neural-only-actuation-v1';return data

    @classmethod
    def restore(cls,data):
        if data.get('schema')!=SCHEMA or data.get('controller')!='neural-only-actuation-v1':
            raise ValueError('Legacy controller checkpoint: archive it and load the new init explicitly')
        for f in data['world']['flies']:
            if f['target'] or f['hint'] or f['directive'] or f['memory'] or f['trust']:raise ValueError('Scripted behavior state forbidden')
            for k in ('vx','vz','vy','touch','motors','signal'):
                if k not in f or not np.isfinite(f[k]).all():raise ValueError('Invalid body state')
        if data['world']['plasticity'] or not data['world']['neural_enabled']:raise ValueError('Invalid neural control flags')
        return super().restore(data)
