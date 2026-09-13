"""Deterministic multirate sensory-neural-muscle runtime.

Mappings and gains are explicit inputs. A software fixture is never promoted to
an anatomical model by this executor. Observers receive copies and cannot step it.
"""
import copy
from dataclasses import asdict, dataclass
from fractions import Fraction
import hashlib
import json
import time
import numpy as np
from physiology.homeostasis import Homeostasis


@dataclass(frozen=True)
class SensoryPort:
    neuron_id: str
    joint: str
    observable: str
    gain_pa_per_unit: float
    offset: float
    delay_ms: float
    evidence: str


@dataclass(frozen=True)
class MotorPort:
    neuron_id: str
    muscle: str
    threshold_mv: float
    slope_per_mv: float
    delay_ms: float
    evidence: str


class EmbodiedExperiment:
    def __init__(self, brain, body, neuron_ids, sensory, motor, exchange_ms=1.,
                 slow_ms=10., scope='software_fixture', condition=None, learning=None):
        if scope not in ['software_fixture','anatomical_hypothesis']:
            raise ValueError('Scientific acceptance is external to the executor')
        if brain.individuals != 1:
            raise ValueError('One body per independently instantiated brain required')
        self.brain, self.body = brain, body
        if not getattr(body,'fingerprint',None):
            raise ValueError('A versioned body fingerprint is required')
        self.learning = learning
        if learning is not None and learning.trace.shape != brain.g.shape:
            raise ValueError('Local learning state must match individual synapses')
        self.ids = tuple(neuron_ids)
        if len(self.ids) != brain.n or len(set(self.ids)) != brain.n:
            raise ValueError('Neuron identities must be unique and match the core')
        self.sensory, self.motor = tuple(sensory), tuple(motor)
        if not self.sensory or not self.motor:
            raise ValueError('Explicit sensory and motor interfaces required')
        self.exchange_ms, self.slow_ms, self.scope = exchange_ms, slow_ms, scope
        self.condition = copy.deepcopy(condition or {})
        periods = {'brain':brain.dt_ms,'body':float(body.model.opt.timestep)*1000,
                   'exchange':exchange_ms,'slow':slow_ms}
        fractions = [Fraction(str(x)).limit_denominator(1000000000) for x in periods.values()]
        from math import gcd,lcm
        denominator = lcm(*(x.denominator for x in fractions))
        numerator = gcd(*(x.numerator*(denominator//x.denominator) for x in fractions))
        self.base_ms = float(Fraction(numerator,denominator))
        if min(periods.values()) <= 0 or self.base_ms < 1e-6:
            raise ValueError('Invalid or impractically fine common clock')
        self.periods = {k:round(v/self.base_ms) for k,v in periods.items()}
        self.sensory_indices = [self.ids.index(p.neuron_id) for p in self.sensory]
        self.motor_indices = [self.ids.index(p.neuron_id) for p in self.motor]
        self.joint_indices = [body.joint_names.index(p.joint) for p in self.sensory]
        self.muscle_indices = [body.names.index(p.muscle) for p in self.motor]
        for p in self.sensory:
            if p.observable not in ('qpos_rad','qvel_rad_s') or not p.evidence:
                raise ValueError('Unsupported or undocumented proprioceptive channel')
            if not np.isfinite([p.gain_pa_per_unit,p.offset,p.delay_ms]).all():
                raise ValueError('Nonfinite sensory parameters')
        for p in self.motor:
            if not p.evidence or not np.isfinite([p.threshold_mv,p.slope_per_mv,p.delay_ms]).all() or p.slope_per_mv < 0:
                raise ValueError('Invalid recruitment parameters')
        self.sensory_delay = self._delays(self.sensory)
        self.motor_delay = self._delays(self.motor)
        maximum = max([*self.sensory_delay,*self.motor_delay],default=0)
        self.sensor_history = np.zeros((maximum+1,len(sensory)))
        self.motor_history = np.zeros((maximum+1,len(motor)))
        self.current = np.zeros((1,brain.n))
        self.action = np.zeros(len(body.names))
        self.internal = Homeostasis(0.,100.,100.)
        self.tick = 0
        self.exchanges = 0
        self.timings = {'brain':0.,'body':0.,'exchange':0.,'slow':0.}
        self.events = {name:0 for name in self.timings}
        payload = {'brain':brain.fingerprint,'ids':self.ids,'sensory':[asdict(p) for p in sensory],
            'motor':[asdict(p) for p in motor],'periods':periods,'scope':scope,'condition':self.condition,
            'body':getattr(body,'fingerprint',None)}
        payload['learning'] = None if learning is None else {'tau':learning.tau,'rate':learning.rate,
            'bounds':learning.bounds,'allowed':learning.allowed.tolist(),'evidence':learning.evidence}
        self.fingerprint = hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()

    def _delays(self, ports):
        result = []
        for p in ports:
            ticks = p.delay_ms/self.exchange_ms
            if ticks < 0 or not np.isclose(ticks,round(ticks),rtol=0,atol=1e-9):
                raise ValueError('Interface delay must be a nonnegative exchange-clock multiple')
            result.append(round(ticks))
        return np.array(result,dtype=int)

    def _exchange(self, proprioception):
        obs = self.body.observe()
        row = self.exchanges % len(self.sensor_history)
        self.sensor_history[row] = [p.gain_pa_per_unit*(obs[p.observable][j]-p.offset)
            for p,j in zip(self.sensory,self.joint_indices)]
        self.motor_history[row] = [np.clip((self.brain.v[0,i]-p.threshold_mv)*p.slope_per_mv,0,1)
            for p,i in zip(self.motor,self.motor_indices)]
        delayed_s = self.sensor_history[(self.exchanges-self.sensory_delay)%len(self.sensor_history),np.arange(len(self.sensory))]
        delayed_m = self.motor_history[(self.exchanges-self.motor_delay)%len(self.motor_history),np.arange(len(self.motor))]
        self.current.fill(0)
        if proprioception:
            np.add.at(self.current[0],self.sensory_indices,delayed_s)
        self.action.fill(0)
        np.add.at(self.action,self.muscle_indices,delayed_m)
        np.clip(self.action,0,1,out=self.action)
        self.exchanges += 1

    def run(self, duration_ms, *, proprioception=True, neural_clamp=False, current_pa=None, modulator=None):
        steps = duration_ms/self.base_ms
        if not np.isfinite(steps) or steps < 0 or not np.isclose(steps,round(steps),atol=1e-8,rtol=0):
            raise ValueError('Duration must be an integer number of base ticks')
        stimulus = np.zeros_like(self.current) if current_pa is None else np.asarray(current_pa,dtype=float)
        if stimulus.shape != self.current.shape or not np.isfinite(stimulus).all():
            raise ValueError('Explicit stimulus must be in pA, one value per neuron')
        modulation = np.zeros_like(self.brain.g) if modulator is None else np.asarray(modulator,dtype=float)
        if modulation.shape != self.brain.g.shape or not np.isfinite(modulation).all():
            raise ValueError('Local modulation must align with synapses')
        for _ in range(round(steps)):
            for name in ['exchange','brain','body','slow']:
                phase = self.tick if name == 'exchange' else self.tick+1
                if phase % self.periods[name]:
                    continue
                start = time.perf_counter()
                if name == 'exchange':
                    self._exchange(proprioception)
                elif name == 'brain':
                    self.brain.step(self.current+stimulus)
                    if self.learning is not None:
                        release=np.clip((self.brain.v-self.brain.parameters.resting_mv)/20.,0,1)
                        self.brain.efficacy=self.learning.step(self.brain.efficacy,
                            release[:,self.brain.pre],release[:,self.brain.post],modulation,self.brain.dt_ms)
                elif name == 'body':
                    self.body.step(np.zeros_like(self.action) if neural_clamp else self.action)
                else:
                    # Bookkeeping only, not a calibrated metabolic-to-circuit model.
                    self.internal.step(self.slow_ms/1000,False,0.,0.,1.,0.,0.)
                self.timings[name] += time.perf_counter()-start
                self.events[name] += 1
            self.tick += 1
        return self.observe()

    def observe(self):
        return {'time_ms':self.tick*self.base_ms,'voltage_mv':self.brain.v.copy(),
            'body':copy.deepcopy(self.body.observe()),'muscle_commands':self.action.copy(),
            'internal':asdict(self.internal),'scope':self.scope,'biological_acceptance':False}

    def snapshot(self):
        return copy.deepcopy({'fingerprint':self.fingerprint,'brain':self.brain.snapshot(),
            'body':self.body.snapshot(),'tick':self.tick,'exchanges':self.exchanges,
            'sensor_history':self.sensor_history,'motor_history':self.motor_history,
            'current':self.current,'action':self.action,'internal':asdict(self.internal),
            'learning_trace':None if self.learning is None else self.learning.trace})

    def restore(self, state):
        if state.get('fingerprint') != self.fingerprint:
            raise ValueError('Different experiment, interface, clock or body')
        for key in ['sensor_history','motor_history','current','action']:
            a = np.asarray(state[key])
            if a.shape != getattr(self,key).shape or not np.isfinite(a).all():
                raise ValueError('Invalid checkpoint '+key)
        if any(not isinstance(state[k],int) or state[k] < 0 for k in ['tick','exchanges']):
            raise ValueError('Invalid checkpoint clocks')
        if state['exchanges'] != (state['tick']+self.periods['exchange']-1)//self.periods['exchange']:
            raise ValueError('Inconsistent exchange clock')
        for key in ['motor_history','action']:
            if np.any((np.asarray(state[key])<0)|(np.asarray(state[key])>1)):
                raise ValueError('Invalid muscle command history')
        body_state=np.asarray(state['body'])
        if body_state.shape!=self.body.snapshot().shape or not np.isfinite(body_state).all():
            raise ValueError('Invalid physical checkpoint')
        if set(state['internal'])!=set(asdict(self.internal)) or any(not np.isfinite(x) or x<0 for x in state['internal'].values()):
            raise ValueError('Invalid slow state checkpoint')
        if self.learning is not None:
            trace=np.asarray(state['learning_trace'])
            if trace.shape!=self.learning.trace.shape or not np.isfinite(trace).all():
                raise ValueError('Invalid learning checkpoint')
        self.brain.restore(state['brain'])
        self.body.restore(state['body'])
        for key in ['sensor_history','motor_history','current','action']:
            setattr(self,key,np.array(state[key],copy=True))
        self.internal = Homeostasis(**state['internal'])
        self.tick,self.exchanges = state['tick'],state['exchanges']
        if self.learning is not None:self.learning.trace=trace.copy()
