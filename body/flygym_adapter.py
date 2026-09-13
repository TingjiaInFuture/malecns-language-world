"""Pinned FlyGym 2.1 CPU muscle adapter. Direct activation is a body-only control.

Joint positions are radians, velocity rad/s. Forces retain MJCF model units until
male-specific mass/force calibration is supplied. No prebuilt gait is used.
"""
from importlib.metadata import version
import numpy as np
import mujoco as mj
from flygym.compose import build_musculoskeletal_simulation
from flygym.compose.fly.musculoskeletal import DEFAULT_MUSCULOSKELETAL_XML
from pathlib import Path
import hashlib


class LeftFrontLeg:
    def __init__(self, dt_s=.0001):
        if version('flygym') != '2.1.0' or version('mujoco') != '3.9.0':
            raise RuntimeError('Validated adapter requires flygym 2.1.0 and mujoco 3.9.0')
        if not np.isfinite(dt_s) or dt_s <= 0:
            raise ValueError('Invalid physical timestep')
        self.sim, self.fly = build_musculoskeletal_simulation()
        self.model, self.data = self.sim.mj_model, self.sim.mj_data
        self.model.opt.timestep = dt_s
        self.names = list(self.fly.muscle_names)
        self.actuator_ids = np.array([mj.mj_name2id(self.model,mj.mjtObj.mjOBJ_ACTUATOR,n) for n in self.names])
        if len(self.names) != 15 or np.any(self.actuator_ids < 0):
            raise ValueError('Unexpected muscle model')
        self.joint_ids = np.array([i for i in range(self.model.njnt)
            if 'joint_LF' in (mj.mj_id2name(self.model,mj.mjtObj.mjOBJ_JOINT,i) or '')])
        self.joint_names = [mj.mj_id2name(self.model,mj.mjtObj.mjOBJ_JOINT,int(i)) for i in self.joint_ids]
        self.qpos_ids = self.model.jnt_qposadr[self.joint_ids]
        self.qvel_ids = self.model.jnt_dofadr[self.joint_ids]
        self.fingerprint = hashlib.sha256(Path(DEFAULT_MUSCULOSKELETAL_XML).read_bytes()+repr(dt_s).encode()).hexdigest()
        self.reset()

    def reset(self):
        self.sim.reset()
        mj.mj_forward(self.model,self.data)

    def step(self, activations):
        values = np.asarray(activations,dtype=float)
        if values.shape != (len(self.names),) or not np.isfinite(values).all() or np.any((values<0)|(values>1)):
            raise ValueError('Muscle activation must be finite in [0,1]')
        self.data.ctrl[:] = 0
        self.data.ctrl[self.actuator_ids] = values
        self.sim.step()
        if not np.isfinite(self.data.qpos).all() or not np.isfinite(self.data.qvel).all():
            raise FloatingPointError('Nonfinite body state')
        if not np.isfinite(self.data.actuator_force).all() or np.any(self.data.warning.number):
            raise FloatingPointError('MuJoCo warning or invalid muscle force; inspect the physical baseline')
        return self.observe()

    def observe(self):
        return {'time_s':float(self.data.time),'joint_names':self.joint_names,
            'qpos_rad':self.data.qpos[self.qpos_ids].copy(),
            'qvel_rad_s':self.data.qvel[self.qvel_ids].copy(),
            'muscle_force_model_units':self.data.actuator_force[self.actuator_ids].copy(),
            'activation':self.data.act.copy(),'contacts':int(self.data.ncon)}

    def snapshot(self):
        spec = mj.mjtState.mjSTATE_INTEGRATION
        state = np.empty(mj.mj_stateSize(self.model,spec))
        mj.mj_getState(self.model,self.data,state,spec)
        return state

    def restore(self, state):
        spec = mj.mjtState.mjSTATE_INTEGRATION
        state = np.asarray(state,dtype=float)
        if state.shape != (mj.mj_stateSize(self.model,spec),) or not np.isfinite(state).all():
            raise ValueError('Invalid body checkpoint')
        mj.mj_setState(self.model,self.data,state,spec)
        mj.mj_forward(self.model,self.data)
