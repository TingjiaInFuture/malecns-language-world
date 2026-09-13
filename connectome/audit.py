"""Audit preserved neuron pairs and index unresolved IDs from verified raw graph inventory."""
import argparse
import json
from pathlib import Path
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from .compiler import digest, membership


def audit_graph(path, segment_graph):
    audit = json.loads((path/'audit.json').read_text())
    raw = json.loads((segment_graph/'audit.json').read_text())
    source_hash = audit['sources']['connectome-weights-male-cns-v1.0-minconf-0.5.feather']['sha256']
    if raw['source_sha256'] != source_hash:
        raise ValueError('Segment inventory is from a different release')
    if digest(segment_graph/'body_ids.npy') != raw['files']['body_ids.npy']:
        raise ValueError('Invalid segment inventory hash')
    ids = np.load(path/'body_ids.npy')
    segments = np.load(segment_graph/'body_ids.npy',mmap_mode='r')
    schema = pa.schema([('segment_id',pa.uint64()),('reason',pa.string()),
        ('candidate_parent_ids',pa.list_(pa.uint64())),('mapping_evidence',pa.string())])
    unresolved = 0
    with pq.ParquetWriter(path/'unresolved.parquet',schema,compression='zstd') as writer:
        previous = -1
        for lo in range(0,len(segments),500000):
            values = segments[lo:lo+500000]
            if len(values) and (int(values[0]) <= previous or np.any(values[1:] <= values[:-1])):
                raise ValueError('Segment inventory is not unique and ordered')
            previous = int(values[-1])
            values = values[~membership(ids,values)]
            n = len(values); unresolved += n
            writer.write_table(pa.Table.from_arrays([pa.array(values,type=pa.uint64()),
                pa.array(['outside_provisional_Traced_set']*n),
                pa.array([None]*n,type=pa.list_(pa.uint64())),
                pa.array(['No verified fragment-parent mapping supplied']*n)],schema=schema))
    edges = pq.ParquetFile(path/'edges.parquet')
    scratch = path/'pair_audit.npy'
    keys = np.lib.format.open_memmap(scratch,mode='w+',dtype=np.uint64,shape=(edges.metadata.num_rows,))
    offset = 0
    total = 0
    for batch in edges.iter_batches(batch_size=500000):
        p,q,c = [batch.column(i).to_numpy() for i in range(3)]
        if np.any(p >= 2**32) or np.any(q >= 2**32):
            raise ValueError('Pair-key audit requires this release\'s documented 32-bit ID range')
        if not membership(ids,p).all() or not membership(ids,q).all():
            raise ValueError('Unmapped endpoint in neuron edges')
        keys[offset:offset+len(p)] = (p.astype(np.uint64)<<np.uint64(32)) | q.astype(np.uint64)
        total += int(c.sum(dtype=np.uint64)); offset += len(p)
    keys.sort()
    duplicates = 0
    for lo in range(1,len(keys),500000):
        hi = min(len(keys),lo+500000)
        duplicates += int(np.count_nonzero(keys[lo:hi] == keys[lo-1:hi-1]))
    del keys
    scratch.unlink()
    if duplicates or total != audit['partition']['internal']['structural_count']:
        raise ValueError('Duplicate pairs or structural count mismatch')
    audit['unique_unresolved_segments'] = unresolved
    audit['duplicates_checked'] = True
    audit['duplicate_pairs'] = duplicates
    audit['segment_inventory_sha256'] = raw['files']['body_ids.npy']
    audit['limitations'] = [x for x in audit['limitations'] if not x.startswith(('No complete unresolved','Duplicate pair'))]
    audit['unresolved_representation'] = 'unresolved.parquet enumerates every unique raw endpoint outside the provisional set; original rows remain in immutable raw source'
    audit['files']['unresolved.parquet'] = digest(path/'unresolved.parquet')
    (path/'audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    print(json.dumps({'unresolved_segments':unresolved,'duplicate_pairs':duplicates,'internal_count':total}),flush=True)


def check_source_samples(graph, raw_file):
    """Independent row-address comparison against the frozen official Arrow file."""
    samples = []
    for batch in pq.ParquetFile(graph/'edges.parquet').iter_batches(batch_size=100000):
        if len(batch):
            samples.append(tuple(int(batch.column(i)[len(batch)//2].as_py()) for i in range(4)))
    with pa.memory_map(str(raw_file),'r') as source:
        reader = pa.ipc.open_file(source)
        lengths = [reader.get_batch(i).num_rows for i in range(reader.num_record_batches)]
        offsets = np.r_[0,np.cumsum(lengths)]
        for pre,post,count,row in samples:
            index = int(np.searchsorted(offsets,row,side='right')-1)
            b = reader.get_batch(index)
            local = row-int(offsets[index])
            expected = tuple(int(b.column(b.schema.get_field_index(name))[local].as_py()) for name in ['body_pre','body_post','weight'])
            if (pre,post,count) != expected:
                raise ValueError('Compiled edge differs from official source row '+str(row))
    result = {'samples':len(samples),'id_direction_count_match':True,
        'source':'frozen official local Arrow table; not a neuPrint API cross-check'}
    (graph/'source_sample_audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--graph',type=Path,default=Path('data/graph_neurons'))
    parser.add_argument('--segments',type=Path,default=Path('data/graph_full'))
    parser.add_argument('--samples-only',action='store_true')
    parser.add_argument('--raw',type=Path,default=Path('data/raw/connectome-weights-male-cns-v1.0-minconf-0.5.feather'))
    args = parser.parse_args()
    if not args.samples_only:
        audit_graph(args.graph,args.segments)
    check_source_samples(args.graph,args.raw)
