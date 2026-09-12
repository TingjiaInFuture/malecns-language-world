"""Exact full published segment connectivity. Shared immutable CSR, independent states.

Structural counts are normalized with explicit NT sign assumptions. Neither the
artificial neuron dynamics nor the I/O ports are biological measurements.
"""
import base64,hashlib,json,zlib,io,tempfile,weakref,zipfile
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import sparse
from brain import Brains as MBON,INPUTS,OUTPUTS,LAB

_GRAPH=None
def graph():
    global _GRAPH
    if _GRAPH is not None:return _GRAPH
    p=LAB/'data/graph_full';audit=json.loads((p/'audit.json').read_text())
    if audit['excluded_rows']!=0 or audit['edges']!=151856684:raise ValueError('Full published graph is required')
    for name,expected in audit['files'].items():
        h=hashlib.sha256()
        with (p/name).open('rb') as f:
            for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
        if h.hexdigest()!=expected:raise ValueError('Full graph checksum mismatch: '+name)
    ids=np.load(p/'body_ids.npy',mmap_mode='r');indptr=np.load(p/'indptr.npy',mmap_mode='r');indices=np.load(p/'indices.npy',mmap_mode='r')
    counts=np.load(p/'counts.npy',mmap_mode='r')
    nt=pd.read_feather(LAB/'data/raw/body-neurotransmitters-male-cns-v1.0.feather',columns=['body','consensus_nt'])
    nt_path=LAB/'data/raw/body-neurotransmitters-male-cns-v1.0.feather'
    nt_receipt=json.loads(nt_path.with_suffix('.feather.receipt.json').read_text())
    if hashlib.sha256(nt_path.read_bytes()).hexdigest()!=nt_receipt['sha256']:raise ValueError('Neurotransmitter source checksum mismatch')
    signs=np.ones(len(ids),np.float32);idx=np.searchsorted(ids,nt.body.to_numpy());valid=idx<len(ids)
    valid &= ids[np.minimum(idx,len(ids)-1)]==nt.body.to_numpy()
    negative=valid & nt.consensus_nt.isin(['gaba','glutamate']).to_numpy();signs[idx[negative]]=-1
    known=valid & nt.consensus_nt.isin(['acetylcholine','gaba','glutamate']).to_numpy()
    # Preserve every edge. Unknown/modulatory transmitters use an explicit +1
    # structural propagation assumption rather than silently deleting connections.
    c=sparse.csr_matrix((counts,indices,indptr),shape=(len(ids),len(ids)),copy=False)
    incoming=np.asarray(c.sum(axis=1),dtype=np.float32).ravel()
    w=counts.astype(np.float32)
    for lo in range(0,len(ids),100000):
        hi=min(len(ids),lo+100000);a,b=int(indptr[lo]),int(indptr[hi])
        w[a:b]*=1.5*signs[indices[a:b]]/np.repeat(np.maximum(1,incoming[lo:hi]),np.diff(indptr[lo:hi+1]))
    matrix=sparse.csr_matrix((w,indices,indptr),shape=c.shape,copy=False)
    for array in [matrix.data,matrix.indices,matrix.indptr]:array.flags.writeable=False
    audit=dict(audit,explicit_fast_nt_nodes=int(known.sum()),assumed_positive_nodes=int(len(ids)-known.sum()),
               sign_assumptions={'acetylcholine':1,'gaba':-1,'glutamate':-1,'unknown_or_modulatory':1})
    _GRAPH=(ids,matrix,audit);return _GRAPH

class FullBrains:
    mode='full';plasticity_supported=False
    def __init__(self,count,seed):
        self.ids,self.matrix,self.audit=graph();self.n=len(self.ids);self.count=count
        self.sha=self.audit['source_sha256'];self.edge_count=self.matrix.nnz
        small=MBON(1,seed);self.display_indices=np.searchsorted(self.ids,small.ids)
        assert np.array_equal(self.ids[self.display_indices],small.ids)
        self.input_map=small.input_map;self.output_map=small.output_map
        # Sequential full CSR matvec avoids the huge intermediate expansion of
        # sparse-sparse propagation. All states live in a private disk-backed map.
        self._directory=tempfile.TemporaryDirectory(prefix='malecns-neural-')
        self.h=np.memmap(Path(self._directory.name)/'state.f32',mode='w+',dtype=np.float32,shape=(count,self.n))
        self._finalizer=weakref.finalize(self,self._cleanup,self.h._mmap,self._directory)
        self.theta=np.zeros((count,1),np.float32);self.last_output=np.zeros((count,len(OUTPUTS)),np.float32)
        self.steps=0
        self._rms=np.zeros(count,np.float64)
        self._rms_valid=np.ones(count,bool)
    def forward(self,observations,dt,enabled=True):
        if not enabled:raise ValueError('Full-connectome production mode cannot bypass its neural core')
        # All 151,856,684 edges are included for each individual, every update.
        inputs=np.asarray(observations,dtype=np.float32)@self.input_map
        for i in range(self.count):
            recurrent=self.matrix@self.h[i]
            recurrent[self.display_indices]+=inputs[i]
            np.tanh(recurrent,out=recurrent);recurrent*=.5
            self.h[i]*=.5;self.h[i]+=recurrent
        self.last_output=np.tanh(3*(self.h[:,self.display_indices]@self.output_map))
        self.steps+=1
        self._rms_valid[:]=False
        if not np.isfinite(self.last_output).all():raise FloatingPointError('Nonfinite neural output')
        return self.last_output
    def learn(self,rewards,enabled=False):
        if enabled:raise ValueError('Published structural weights are immutable in full mode')
    def dump(self):
        buffer=io.BytesIO()
        if self.steps:
            # NumPy writes each array through bounded buffers into the zip stream.
            with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as archive:
                for i in range(self.count):
                    with archive.open(f'f{i}.npy','w',force_zip64=True) as stream:
                        np.lib.format.write_array(stream,np.asarray(self.h[i]),allow_pickle=False)
        return {'mode':'full','sha':self.sha,'n':self.n,'count':self.count,'steps':self.steps,
                'h_encoding':'zeros' if self.steps==0 else 'npz-base64-dense-f32',
                'h':None if self.steps==0 else base64.b64encode(buffer.getvalue()).decode('ascii'),
                'last_output':self.last_output.tolist()}
    def restore(self,data):
        if data.get('mode')!='full' or data['sha']!=self.sha or data['n']!=self.n or data['count']!=self.count:
            raise ValueError('Save is not compatible with the complete published graph')
        self.steps=int(data['steps'])
        if data['h_encoding']=='zeros':
            if self.steps!=0:raise ValueError('Noninitial save cannot omit neural activity')
            self.h.fill(0)
        elif data['h_encoding']=='npz-base64-dense-f32':
            with np.load(io.BytesIO(base64.b64decode(data['h'],validate=True)),allow_pickle=False) as z:
                for i in range(self.count):
                    a=z[f'f{i}']
                    if a.shape!=(self.n,) or a.dtype!=np.float32 or not np.isfinite(a).all():raise ValueError('Invalid saved state')
                    self.h[i]=a
        else:raise ValueError('Unsupported neural encoding')
        self.last_output=np.asarray(data['last_output'],np.float32)
        self._rms_valid[:]=False
        if self.last_output.shape!=(self.count,len(OUTPUTS)):raise ValueError('Invalid readouts')
    def inspect(self,index):
        return {'activity':np.round(self.h[index,self.display_indices],4).tolist(),'body_ids':self.ids[self.display_indices].tolist(),
                'rms':self.rms(index),'gain_change':0.,
                'outputs':dict(zip(OUTPUTS,self.last_output[index].tolist())),
                'display_nodes':len(self.display_indices),'total_nodes':self.n,'total_edges':self.edge_count,
                'steps':self.steps,'full_graph_updates_per_individual':self.steps,
                'state_storage':'independent float32 disk-backed arrays; no pruning',
                'display_note':'Only 97 probe nodes displayed; every published edge participates in computation.'}
    def rms(self,index):
        if self._rms_valid[index]:return float(self._rms[index])
        total=0.
        for lo in range(0,self.n,1000000):
            a=self.h[index,lo:lo+1000000];total+=float(np.sum(a*a,dtype=np.float64))
        self._rms[index]=np.sqrt(total/self.n);self._rms_valid[index]=True
        return float(self._rms[index])
    @staticmethod
    def _cleanup(mapping,directory):
        mapping.close();directory.cleanup()
    def close(self):
        if self._finalizer.alive:self._finalizer()
