"""Passive habitat construction, climate, intervention and checkpoint facilities."""
from __future__ import annotations
import copy
import json
import math
import re
from collections import deque
import numpy as np
from brain import Brains, INPUTS
SCHEMA = 'habitat3d/2'
DT = 0.25
DAY = 360.0
WORDS = {'food': '糖', 'water': '水', 'shade': '荫', 'danger': '险', 'empty': '空'}
SECTORS = ('西北', '北侧', '东北', '西侧', '中央', '东侧', '西南', '南侧', '东南')
PALETTE = ['#e4b66c', '#7fc7b1', '#92b7e6', '#c79dd7', '#d99685', '#c6ce87', '#79bcc5', '#c1a482', '#e3c893', '#89b992', '#a5a2d8', '#d6a7ba']

def height(x, z):
    return 0.16 * math.sin(x * 0.18) * math.cos(z * 0.21)

def sector(x, z):
    return SECTORS[(0 if z < -5 else 2 if z > 5 else 1) * 3 + (0 if x < -9 else 2 if x > 9 else 1)]

def sector_position(name):
    i = SECTORS.index(name)
    return [(i % 3 - 1) * 17.0, (i // 3 - 1) * 11.0]

class Environment:

    def __init__(self, seed=20260913, count=12, brain_mode='mbon'):
        if not 1 <= count <= 24 or not 0 <= seed < 2 ** 32:
            raise ValueError('Population must be 1..24; seed must be a uint32')
        self.seed, self.count, self.t, self.tick = (seed, count, 0.0, 0)
        self.rng = np.random.default_rng(np.random.SeedSequence([seed, 1]))
        self.move_rng = [np.random.default_rng(np.random.SeedSequence([seed, 2, i])) for i in range(count)]
        self.social_rng = [np.random.default_rng(np.random.SeedSequence([seed, 3, i])) for i in range(count)]
        if brain_mode == 'full':
            from full_brain import FullBrains
            self.brains = FullBrains(count, seed)
        elif brain_mode == 'real':
            from real_brain import RealCircuitBrains
            self.brains = RealCircuitBrains(count, seed)
        elif brain_mode == 'mbon':
            self.brains = Brains(count, seed)
        else:
            raise ValueError('Unknown brain mode')
        self.communication, self.plasticity, self.neural_enabled = (True, True, True)
        if brain_mode in ('full', 'real'):
            self.plasticity = False
        self.events = deque(maxlen=100)
        self.pending_events = []
        self.history = deque(maxlen=360)
        self.messages = deque(maxlen=120)
        self.event_id = 0
        self.metrics = {'sent': 0, 'received': 0, 'followed': 0, 'verified': 0, 'failed': 0, 'meals': 0, 'drinks': 0, 'shelter_visits': 0, 'deaths': 0}
        self.weather_override = None
        self.weather = {'rain': 0.0, 'light': 0.7, 'heat': 0.65, 'wind': [0.3, 0.1], 'label': '晴 · 微风'}
        self.last_weather = ''
        self.resources = []
        specs = [('food', -18.0, -8.0, 3.0, False, '发酵无花果'), ('water', 16.0, -7.0, 2.3, False, '石面露水'), ('shade', -12.0, 9.0, 4.4, True, '卷叶庇护'), ('food', 17.0, 10.0, 2.7, False, '熟落果'), ('water', -19.0, 3.0, 1.8, True, '叶下积水'), ('shade', 12.0, -12.0, 4.0, True, '蕨叶阴影')]
        for i, (kind, x, z, r, protected, label) in enumerate(specs):
            self.resources.append({'id': f'R{i + 1}', 'kind': kind, 'x': x, 'z': z, 'radius': r, 'protected': protected, 'label': label, 'amount': 1.0 if kind == 'shade' else 0.85, 'ripeness': 0.85, 'phase': 80.0 + i * 37.0, 'suppressed_until': 0.0})
        self.rocks = [{'x': -2.0, 'z': -8.0, 'r': 2.4, 'height': 2.2}, {'x': 4.0, 'z': 8.0, 'r': 2.0, 'height': 1.8}, {'x': 22.0, 'z': -1.0, 'r': 1.8, 'height': 1.4}, {'x': -22.0, 'z': -12.0, 'r': 1.6, 'height': 1.2}]
        self.flies = []
        for i in range(count):
            rng = self.move_rng[i]
            centers = [(-10.0, -6.0), (10.0, -5.0), (0.0, 7.0)]
            x, z = np.asarray(centers[i % 3]) + rng.uniform(-3, 3, 2)
            self.flies.append({'id': f'F{i + 1:02d}', 'color': PALETTE[i % 12], 'x': float(x), 'z': float(z), 'y': 1.8, 'heading': float(rng.uniform(-math.pi, math.pi)), 'energy': float(rng.uniform(0.5, 0.88)), 'hydration': float(rng.uniform(0.46, 0.85)), 'fatigue': float(rng.uniform(0.05, 0.3)), 'age': float(rng.uniform(0, 2)), 'alive': True, 'state': '探索', 'target': None, 'memory': {}, 'hint': None, 'directive': None, 'trust': {}, 'next_decision': 0.0, 'next_signal': float(3 + i * 1.7), 'next_explore': 0.0, 'trail': [], 'experience': 0, 'helped': 0, 'last_word': None, 'last_signal_t': -100.0, 'travel': 0.0, 'sheltered': False, 'speed': 0.0, 'last_reward': 0.0, 'failure_wait': 0.0})
        self.emit('system', '微境开始运行', '昼夜、资源与个体经验将持续变化。')

    def emit(self, kind, title, detail='', **extra):
        self.event_id += 1
        e = {'id': self.event_id, 't': round(self.t, 3), 'kind': kind, 'title': title, 'detail': detail, **extra}
        self.events.append(e)
        self.pending_events.append(copy.deepcopy(e))
        return e

    def drain_events(self):
        result = self.pending_events
        self.pending_events = []
        return result

    @staticmethod
    def available(r):
        return r['kind'] == 'shade' or (r['amount'] > 0.025 and (r['kind'] != 'food' or r['ripeness'] > 0.18))

    def climate(self):
        phase = self.t % DAY / DAY
        light = max(0.04, 0.5 + 0.5 * math.sin(phase * 2 * math.pi))
        rain = max(0.0, math.sin((self.t - 40) * 2 * math.pi / 620) - 0.64) / 0.36
        if self.weather_override and self.t < self.weather_override['until']:
            rain = self.weather_override['rain']
        heat = 0.25 + 0.65 * light - 0.3 * rain
        label = '阵雨' if rain > 0.22 else '夜露' if light < 0.2 else '午后偏热' if heat > 0.83 else '晴 · 微风'
        wind = [0.45 * math.cos(self.t / 85), 0.32 * math.sin(self.t / 110)]
        self.weather = {'rain': float(rain), 'light': float(light), 'heat': float(heat), 'wind': wind, 'label': label}
        if label != self.last_weather:
            self.last_weather = label
            self.emit('weather', label, '环境改变，通过感觉通道进入神经模型。')

    def control(self, action, value=None):
        if action == 'rain':
            self.weather_override = {'rain': 0.9, 'until': self.t + 75}
            self.emit('control', '观察者引入阵雨', '持续 75 模型秒，个体通过本地环境感知作出反应。')
        elif action == 'dry':
            for r in self.resources:
                if r['kind'] == 'water':
                    r['amount'] = 0.0
                    r['suppressed_until'] = self.t + 90
            self.emit('control', '露水暂时蒸干', '90 模型秒后恢复自然补水过程；已有线索可能失效。')
        elif action == 'fruit':
            for r in self.resources:
                if r['kind'] == 'food':
                    r['amount'] = 1.0
            self.emit('control', '观察者补充果实', '只有接近补给点的个体能直接发现变化。')
        else:
            raise ValueError('Unsupported ecology action')

    def public(self, selected='F01'):
        flies = []
        for f in self.flies:
            copy_fields = ['id', 'color', 'x', 'y', 'z', 'heading', 'energy', 'hydration', 'fatigue', 'age', 'alive', 'state', 'speed', 'trail', 'experience', 'helped', 'last_word', 'last_signal_t', 'travel', 'sheltered', 'hint', 'target']
            row = {k: copy.deepcopy(f[k]) for k in copy_fields}
            row['known'] = len(f['memory'])
            row['gain_change'] = float(np.mean(np.abs(self.brains.theta[int(f['id'][1:]) - 1]))) \
                if hasattr(self.brains, 'theta') else 0.0
            row['neural_rms'] = self.brains.rms(int(f['id'][1:]) - 1)
            flies.append(row)
        index = next((i for i, f in enumerate(self.flies) if f['id'] == selected), 0)
        return {'schema': SCHEMA, 'seed': self.seed, 't': self.t, 'tick': self.tick, 'day': int(self.t // DAY) + 1, 'day_phase': self.t % DAY / DAY, 'weather': copy.deepcopy(self.weather), 'flies': flies, 'resources': copy.deepcopy(self.resources), 'rocks': self.rocks, 'metrics': dict(self.metrics), 'events': list(self.events)[-45:], 'history': list(self.history), 'messages': [copy.deepcopy(m) for m in self.messages if self.t - m['t'] < 8], 'communication': self.communication, 'plasticity': self.plasticity, 'neural_enabled': self.neural_enabled, 'brain': self.brains.inspect(index), 'selected': self.flies[index]['id'], 'provenance': {'dataset': 'male-cns:v1.0', 'mode': self.brains.mode, 'nodes': self.brains.n, 'edges': getattr(self.brains, 'edge_count', 1606), 'graph_sha256': self.brains.sha, 'controller': 'neural-only-actuation-v1', 'language': '连续无语义信号，未验证语言能力', 'biology': '全量公开分割连接图；结构计数不等于生理权重' if self.brains.mode == 'full' else
               ('真实 MaleCNS 98 节点左前胫节回路（生产端口+已发表 hook 身份）；被动 FeCO 式磁刺激协议；'
                '输出为观察投影；未生理校准的生态身体' if self.brains.mode == 'real' else
                '真实连接数据子图；未生理校准的身体与生态模型；非完整果蝇仿真')}}

    def dump(self):
        attributes = ['seed', 'count', 't', 'tick', 'communication', 'plasticity', 'neural_enabled', 'event_id', 'metrics', 'weather_override', 'weather', 'last_weather', 'resources', 'rocks', 'flies']
        return {'schema': SCHEMA, 'world': {k: copy.deepcopy(getattr(self, k)) for k in attributes}, 'events': list(self.events), 'history': list(self.history), 'messages': list(self.messages), 'rng': self.rng.bit_generator.state, 'move_rng': [r.bit_generator.state for r in self.move_rng], 'social_rng': [r.bit_generator.state for r in self.social_rng], 'brains': self.brains.dump()}

    @classmethod
    def restore(cls, data):
        if data.get('schema') != SCHEMA:
            raise ValueError('Unsupported habitat save version')
        w = data['world']
        obj = cls(w['seed'], w['count'], data['brains'].get('mode', 'mbon'))
        for k in ['seed', 'count', 't', 'tick', 'communication', 'plasticity', 'neural_enabled', 'event_id', 'metrics', 'weather_override', 'weather', 'last_weather', 'resources', 'rocks', 'flies']:
            setattr(obj, k, copy.deepcopy(w[k]))
        obj.events = deque(data['events'], maxlen=100)
        obj.history = deque(data['history'], maxlen=360)
        obj.messages = deque(data['messages'], maxlen=120)
        obj.pending_events = []
        obj.rng.bit_generator.state = data['rng']
        for rng, s in zip(obj.move_rng, data['move_rng']):
            rng.bit_generator.state = s
        for rng, s in zip(obj.social_rng, data['social_rng']):
            rng.bit_generator.state = s
        obj.brains.restore(data['brains'])
        if len(obj.flies) != obj.count or not math.isfinite(obj.t):
            raise ValueError('Invalid habitat save')
        return obj
