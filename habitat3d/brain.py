"""Independent MBON recurrent cores with fixed artificial ports.

The dense evaluation of this 97-node matrix preserves the sparse edge support.
This is an engineering hybrid controller, not a validated physiological brain.
"""
import hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import sparse

INPUTS = ('hunger','thirst','fatigue','light','rain','heat','crowding','food_left','food_right',
          'water_left','water_right','shade','wind_x','wind_z','speed','word_food','word_water',
          'word_shade','word_danger','energy','hydration','age','bias','novelty')
OUTPUTS = ('food','water','shade','explore','left','right','broadcast','follow')
LAB = Path(__file__).resolve().parent.parent


class Brains:
    mode='mbon'
    def __init__(self, count, seed, graph_dir=None):
        graph_dir = Path(graph_dir or LAB/'data/graph_mbon')
        c = sparse.load_npz(graph_dir/'counts.npz').tocsr()
        c.sort_indices()
        self.ids = np.load(graph_dir/'body_ids.npy',allow_pickle=False)
        signs = pd.read_csv(graph_dir/'signs.csv').set_index('bodyId').reindex(self.ids)['sign'].to_numpy()
        if c.shape != (97,97) or c.nnz != 1606 or not np.isin(signs,[-1,1]).all():
            raise ValueError('Expected the audited 97-node MBON graph and explicit signs')
        coo = c.tocoo()
        self.row, self.col = coo.row,coo.col
        incoming = np.asarray(c.sum(axis=1)).ravel()
        self.base = (1.5*signs[self.col]*coo.data/np.maximum(1,incoming[self.row])).astype(np.float32)
        self.sha = hashlib.sha256((graph_dir/'counts.npz').read_bytes()).hexdigest()
        self.count, self.n = count,len(self.ids)
        rng = np.random.default_rng(np.random.SeedSequence([seed,91]))
        order = rng.permutation(self.n)
        self.input_map = np.zeros((len(INPUTS),self.n),np.float32)
        self.output_map = np.zeros((self.n,len(OUTPUTS)),np.float32)
        for j in range(len(INPUTS)):
            self.input_map[j,order[2*j:2*j+2]] = rng.choice([-1.5,1.5],2)
        for j in range(len(OUTPUTS)):
            self.output_map[order[48+3*j:48+3*j+3],j] = 1/3
        assert not set(np.where(self.input_map.any(axis=0))[0]) & set(np.where(self.output_map.any(axis=1))[0])
        self.h = np.zeros((count,self.n),np.float32)
        self.theta = np.zeros((count,c.nnz),np.float32)
        self.trace = np.zeros_like(self.theta)
        self.last_output = np.zeros((count,len(OUTPUTS)),np.float32)

    def forward(self, observations, dt, enabled=True):
        if not enabled:
            self.last_output.fill(0)
            return self.last_output
        weights = np.zeros((self.count,self.n,self.n),np.float32)
        weights[:,self.row,self.col] = self.base[None,:]*np.exp(self.theta)
        stimulus = np.asarray(observations,dtype=np.float32)@self.input_map
        for _ in range(3):
            self.h = .5*self.h+.5*np.tanh(np.einsum('bij,bj->bi',weights,self.h)+stimulus)
        eligibility = self.h[:,self.row]*self.h[:,self.col]*np.sign(self.base)
        decay = np.exp(-dt/6)
        self.trace = (decay*self.trace+(1-decay)*eligibility).astype(np.float32)
        self.last_output = np.tanh(3*(self.h@self.output_map))
        if not np.isfinite(self.h).all():
            raise FloatingPointError('Non-finite neural activity')
        return self.last_output

    def learn(self, rewards, enabled=True):
        if enabled:
            self.theta = np.clip(self.theta+.035*np.asarray(rewards)[:,None]*self.trace,-.75,.75).astype(np.float32)

    def dump(self):
        return {'sha':self.sha,'h':self.h.tolist(),'theta':self.theta.tolist(),'trace':self.trace.tolist(),
                'last_output':self.last_output.tolist()}

    def restore(self,data):
        if data['sha'] != self.sha:
            raise ValueError('Saved brain graph checksum differs from installed data')
        for k in ['h','theta','trace','last_output']:
            a = np.asarray(data[k],np.float32)
            if a.shape != getattr(self,k).shape or not np.isfinite(a).all():
                raise ValueError('Invalid saved neural array: '+k)
            setattr(self,k,a)
        if np.abs(self.theta).max() > .751:
            raise ValueError('Saved gain outside supported bounds')

    def inspect(self,index):
        return {'activity':np.round(self.h[index],4).tolist(), 'body_ids':self.ids.tolist(),
                'rms':float(np.sqrt(np.mean(self.h[index]**2))),
                'gain_change':float(np.mean(np.abs(self.theta[index]))),
                'outputs':dict(zip(OUTPUTS,np.round(self.last_output[index],4).tolist()))}

    def rms(self,index):
        return float(np.sqrt(np.mean(self.h[index]**2)))
