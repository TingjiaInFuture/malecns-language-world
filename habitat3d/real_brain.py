"""Real MaleCNS left-front-tibia circuit brain for the habitat viewer.

Each fly runs an independent copy of the verified 98-node / 741-edge real
circuit (production motor ports, published-identity hook ports, transmitter
polarity) through the unit-carrying conductance core. Sensory drive is a
passive FeCO-style magnet protocol (imposed tibia angle, like the Dallmann
restraint experiments), NOT semantic world observations - the 24-dimension
ecology observation vector is deliberately ignored. The 8-dimension output is
an OBSERVATION PROJECTION of flexor/extensor muscle activation onto legacy
turn channels, not a physiological motor claim. No global reward learning is
applied; structural connectivity is immutable.
"""
from __future__ import annotations
import hashlib
import json
import math
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from physiology.reference import ConductanceNetwork, Parameters

LAB = Path(__file__).resolve().parent.parent
NPZ = LAB/'data/graph_neurons/interfaces/lf_tibia_circuit.npz'
OUTPUTS = ('food', 'water', 'shade', 'explore', 'left', 'right', 'broadcast', 'follow')
NEURAL_DT_MS = 0.5
PROTOCOL = {'amplitude_rad': 0.6, 'frequency_hz': 0.8,
            'static_gain_pa_per_rad': 200., 'dynamic_gain_pa_per_rad_s': 40.,
            'rest_angle_rad': 1.5,
            'declaration': 'passive imposed tibia-angle protocol (magnet-restraint analogue), '
                           'gains matched to the verified lf_tibia_circuit configuration; '
                           'no target, direction or semantic input reaches the circuit'}


class RealCircuitBrains:
    mode = 'real'

    def __init__(self, count, seed, npz_path=None):
        path = Path(npz_path or NPZ)
        if not path.exists():
            raise FileNotFoundError(
                'Real-circuit arrays missing; run '
                '".venv/Scripts/python.exe -m experiments.lf_tibia_circuit prepare" first')
        data = np.load(path, allow_pickle=False)
        manifest_path = Path(str(path)+'.manifest.json')
        manifest = json.loads(manifest_path.read_text(encoding='utf-8')) \
            if manifest_path.exists() else {}
        self.count, self.n = count, len(data['node_ids'])
        self.edge_count = int(len(data['pre']))
        self.sha = manifest.get('npz_sha256') or hashlib.sha256(path.read_bytes()).hexdigest()
        self.node_ids = data['node_ids'].astype(np.uint64)
        position = {int(b): i for i, b in enumerate(self.node_ids)}
        self.hook_ports = np.array([position[int(b)] for b in data['published_hook_port_ids']])
        # Full sensory set of the verified circuit: structural direct partners plus
        # published-identity hook afferents, identical to lf_tibia_circuit's ports.
        self.sensory_ports = np.array(sorted(set(
            [position[int(b)] for b in data['sensory_port_ids']] + self.hook_ports.tolist())))
        motor_positions = np.array([position[int(b)] for b in data['motor_ids']])
        muscles = [str(m) for m in data['motor_muscle_names']]
        parameters = Parameters(**{k[len('param_'):]: data[k]
                                   for k in data.files if k.startswith('param_')})
        conductance = np.minimum(data['count'].astype(float)*0.01, 20.)
        self.network = ConductanceNetwork(
            self.n, data['pre'], data['post'], conductance,
            data['reversal_mv'].astype(float), np.full(self.edge_count, 2.),
            dt_ms=NEURAL_DT_MS, parameters=parameters, individuals=count)
        thresholds = np.asarray(parameters.resting_mv, dtype=float)[motor_positions]+10.
        flexor_mask = np.array(['flex' in m for m in muscles])
        self.flexor = motor_positions[flexor_mask]
        self.extensor = motor_positions[~flexor_mask]
        self.flexor_thresholds = thresholds[flexor_mask]
        self.extensor_thresholds = thresholds[~flexor_mask]
        rng = np.random.default_rng(np.random.SeedSequence([seed, 2026]))
        self.phase = rng.uniform(0, 2*math.pi, count)
        self.last_output = np.zeros((count, len(OUTPUTS)), np.float32)
        self.protocol = dict(PROTOCOL)

    def _protocol_current(self):
        """FeCO-style static+dynamic current per fly from the imposed angle."""
        t_s = self.network.ticks*NEURAL_DT_MS/1000.
        angle = 2*math.pi*PROTOCOL['frequency_hz']*t_s + self.phase
        theta = PROTOCOL['rest_angle_rad'] + PROTOCOL['amplitude_rad']*np.sin(angle)
        dtheta = PROTOCOL['amplitude_rad']*2*math.pi*PROTOCOL['frequency_hz']*np.cos(angle)
        static = PROTOCOL['static_gain_pa_per_rad']*(theta-PROTOCOL['rest_angle_rad'])
        dynamic = PROTOCOL['dynamic_gain_pa_per_rad_s']*dtheta
        current = np.zeros((self.count, self.n))
        current[:, self.sensory_ports] = static[:, None]+dynamic[:, None]
        return current

    def forward(self, observations, dt, enabled=True):
        """Advance every fly's circuit by dt seconds of world time."""
        if not enabled:
            self.last_output.fill(0)
            return self.last_output
        steps = int(round(dt*1000./NEURAL_DT_MS))
        for _ in range(steps):
            self.network.step(self._protocol_current())
        voltages = self.network.v
        flexor = np.clip((voltages[:, self.flexor]-self.flexor_thresholds[None, :])*0.05, 0., 1.) \
            .mean(axis=1)
        extensor = np.clip((voltages[:, self.extensor]-self.extensor_thresholds[None, :])*0.05, 0., 1.) \
            .mean(axis=1)
        outputs = np.zeros((self.count, len(OUTPUTS)), np.float32)
        outputs[:, OUTPUTS.index('left')] = 1.5*flexor
        outputs[:, OUTPUTS.index('right')] = 1.5*extensor
        outputs[:, OUTPUTS.index('explore')] = .3*(flexor+extensor)
        self.last_output = outputs
        if not np.isfinite(self.network.v).all():
            raise FloatingPointError('Non-finite circuit voltage')
        return self.last_output

    def learn(self, rewards, enabled=True):
        """No global reward learning: structural connectivity and this viewer stay immutable."""
        return self.last_output

    def inspect(self, index):
        voltages = self.network.v[index]
        return {'activity': np.round(voltages, 4).tolist(),
                'body_ids': self.node_ids.tolist(),
                'rms': float(np.sqrt(np.mean((voltages-np.mean(voltages))**2))),
                'gain_change': 0.,
                'outputs': dict(zip(OUTPUTS, np.round(self.last_output[index], 4).tolist())),
                'mn_voltages_mv': np.round(voltages[np.r_[self.flexor, self.extensor]], 3).tolist(),
                'protocol': self.protocol['declaration']}

    def rms(self, index):
        voltages = self.network.v[index]
        return float(np.sqrt(np.mean((voltages-np.mean(voltages))**2)))

    def dump(self):
        state = self.network.snapshot()
        return {'mode': self.mode, 'sha': self.sha, 'fingerprint': state['fingerprint'],
                'ticks': state['ticks'],
                'v': state['v'].tolist(), 'g': state['g'].tolist(),
                'efficacy': state['efficacy'].tolist(), 'adaptation': state['adaptation'].tolist(),
                'history': state['history'].tolist(),
                'last_output': self.last_output.tolist(), 'phase': self.phase.tolist()}

    def restore(self, data):
        if data.get('sha') != self.sha:
            raise ValueError('Saved real-circuit arrays differ from installed data')
        state = {'fingerprint': data['fingerprint'], 'ticks': data['ticks'],
                 'v': data['v'], 'g': data['g'], 'efficacy': data['efficacy'],
                 'adaptation': data['adaptation'], 'history': data['history']}
        self.network.restore(state)
        phase = np.asarray(data['phase'], dtype=float)
        if phase.shape != self.phase.shape or not np.isfinite(phase).all():
            raise ValueError('Invalid saved protocol phase')
        self.phase = phase
