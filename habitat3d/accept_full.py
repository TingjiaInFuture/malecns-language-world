"""Real full-graph acceptance and clean init creation. Not a synthetic substitute."""
import copy,hashlib,json,time
from pathlib import Path
import numpy as np
from scipy import sparse
from ecology import Habitat

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'habitat3d/evidence/full';OUT.mkdir(parents=True,exist_ok=True)
start=time.perf_counter();world=Habitat(20260913,12,'full');b=world.brains
print('full graph loaded',b.n,b.edge_count,'seconds',time.perf_counter()-start,flush=True)
assert b.n==88384522 and b.edge_count==151856684
assert b.audit['excluded_rows']==0 and not b.matrix.data.flags.writeable
assert b.h.shape==(12,88384522) and all(not np.any(b.h[i]) for i in range(12))
assert not world.plasticity and world.neural_enabled
for f in world.flies:assert not f['memory'] and f['experience']==0 and f['target'] is None
assert world.t==0 and world.tick==0 and all(v==0 for v in world.metrics.values())
init={'application':'MaleCNS Micro Habitat','schema':'habitat3d/1','saved_at':'2026-09-13T00:00:00Z',
      'runtime':{'paused':True,'speed':1},'simulation':world.dump(),
      'limitations':'Complete published structural segment graph, not physiological weights; hybrid controller and artificial I/O.'}
(ROOT/'init').mkdir(exist_ok=True)
init_bytes=json.dumps(init,ensure_ascii=False,indent=2,allow_nan=False).encode('utf8')
(ROOT/'init/world_state.json').write_bytes(init_bytes)
checks=['complete published graph and zero excluded rows','immutable shared structural matrix','twelve independent zero neural states',
        'clean init: zero time, experience, metrics and memory','no neural bypass or weight mutation']
for action,value in [('plasticity',True),('neural_enabled',False)]:
    try:world.control(action,value)
    except ValueError:pass
    else:raise AssertionError('Production bypass was allowed')
times=[]
for _ in range(2):
    t=time.perf_counter();world.step();times.append(time.perf_counter()-t)
    print('real full step',world.tick,'seconds',times[-1],flush=True)
assert b.steps==2 and all(np.isfinite(b.h[i]).all() for i in range(12))
assert all(np.any(b.h[i]) for i in range(12))
assert not np.array_equal(b.h[0],b.h[1])
checks+=['all twelve individuals updated through full graph','finite and distinct individual activity']
# Independent sparse column multiplication checks that batching does not mix flies.
obs=np.stack([world.observation(f,world.perceive(f)) for f in world.flies])
col=b.h[0].copy();recurrent=b.matrix@col
inputs=obs[0]@b.input_map
recurrent[b.display_indices]+=inputs;np.tanh(recurrent,out=recurrent)
expected=.5*col+.5*recurrent
del col,recurrent
print('saving complete twelve-individual neural state',flush=True)
t=time.perf_counter();saved=b.dump();print('saved in',time.perf_counter()-t,'seconds',flush=True)
b.forward(obs,.25)
assert np.array_equal(b.h[0],expected)
del expected
checks.append('independent full-column multiplication agrees with batch computation')
def state_hash():
    h=hashlib.sha256()
    for i in range(b.count):h.update(memoryview(b.h[i]))
    return h.hexdigest()
next_hash=state_hash();print('restoring complete neural state',flush=True);b.restore(saved);b.forward(obs,.25)
assert state_hash()==next_hash
checks.append('compressed mapped state restores exact neural continuation')
report={'checks':checks,'passed':len(checks),'nodes':b.n,'edges':b.edge_count,'flies':12,
        'step_seconds':times,'state_bytes':int(b.h.nbytes),'graph_source_sha256':b.sha,
        'assumptions':b.audit['sign_assumptions'],'unknown_or_modulatory_positive_nodes':b.audit['assumed_positive_nodes'],
        'init_sha256':hashlib.sha256(init_bytes).hexdigest(),'init_bytes':len(init_bytes),
        'not_proven':['physiological equivalence','exclusive neural control','learned language','survival improvement']}
(OUT/'acceptance.json').write_text(json.dumps(report,indent=2),encoding='utf8')
(ROOT/'init/manifest.json').write_text(json.dumps({'seed':world.seed,'count':12,'brain_mode':'full','t':0,'paused':True,
    'world_sha256':report['init_sha256'],'graph_source_sha256':b.sha,'nodes':b.n,'edges':b.edge_count},indent=2),encoding='utf8')
print(json.dumps(report),flush=True)
b.close()
