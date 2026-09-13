"""Full compiled topology resource benchmark with declared nonbiological parameters.

Uniform receptor extremes are numerical fixtures, not predictions of NT action.
No brain/body or behavioral claim follows from this workload.
"""
import json
import hashlib
from pathlib import Path
import time
import numpy as np
import pyarrow.parquet as pq
from physiology.reference import ConductanceNetwork


def run():
    path = Path('data/graph_neurons')
    ids = np.load(path/'body_ids.npy')
    source = pq.ParquetFile(path/'edges.parquet')
    m = source.metadata.num_rows
    pre,post,count = [np.empty(m,dtype=np.int64) for _ in range(3)]
    at = 0
    for batch in source.iter_batches(batch_size=250000,columns=['pre_body_id','post_body_id','structural_count']):
        a,b,c = [batch.column(i).to_numpy() for i in range(3)]
        pre[at:at+len(a)] = np.searchsorted(ids,a)
        post[at:at+len(a)] = np.searchsorted(ids,b)
        count[at:at+len(a)] = c
        at += len(a)
    started = time.perf_counter()
    brain = ConductanceNetwork(len(ids),pre,post,count*.001,np.full(m,-80.),np.zeros(m),dt_ms=.1)
    del pre,post,count
    construction = time.perf_counter()-started
    current = np.zeros((1,len(ids)))
    current[0,:100] = 30.  # explicitly arbitrary numerical stress input
    started = time.perf_counter()
    for _ in range(5):
        brain.step(current)
    wall = time.perf_counter()-started
    state_bytes = sum(getattr(brain,name).nbytes for name in ['v','adaptation','g','efficacy','history'])
    topology_bytes = sum(getattr(brain,name).nbytes for name in ['pre','post','gbar','reversal','delay_ticks'])
    result = {'scope':'full compiled topology numerical fixture, NOT a calibrated physiological model',
        'neurons':brain.n,'edges':m,'dt_ms':.1,'steps':5,'simulated_seconds':.0005,
        'construction_seconds':construction,'neural_seconds':wall,'seconds_per_simulated_second':wall/.0005,
        'edge_evaluations':m*5,'state_array_bytes':state_bytes,'topology_array_bytes':topology_bytes,
        'voltage_min_mv':float(brain.v.min()),'voltage_max_mv':float(brain.v.max()),
        'parameters':'uniform -80 mV receptor extreme; 0.001 nS/count, default uncalibrated membrane fixture',
        'finite_pass':bool(np.isfinite(brain.v).all()),'biological_acceptance':False}
    result['executed_source_sha256']={p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
        for p in ['physiology/reference.py','validation/full_neuron_benchmark.py']}
    Path('validation/full-neuron-evidence.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2),flush=True)


if __name__ == '__main__':
    run()
