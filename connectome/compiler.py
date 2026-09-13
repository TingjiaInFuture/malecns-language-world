"""Stream the frozen release into a conservative, explicitly provisional neuron graph.

Run: python -m connectome.compiler --out data/graph_neurons
No fragment merging is inferred. Non-Traced identities remain review candidates.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

EXPECTED = {
    'body-annotations-male-cns-v1.0-minconf-0.5.feather': '2177e246113e4cfbf1e7772ec37c6da1955ff22e8063d0b1f833101f99a9a3b2',
    'connectome-weights-male-cns-v1.0-minconf-0.5.feather': 'e35da783d1c686b2b58b3b87cd6a403ae43bfcfba8bff28e08ef752c1a56afc1',
    'body-neurotransmitters-male-cns-v1.0.feather': '95c9289220663abeb3409f3ad9e5a7f8a53f8093f5139d15502cd08da8879621',
}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def membership(ids, values):
    if not len(ids):
        return np.zeros(len(values), bool)
    i = np.searchsorted(ids, values)
    return (i < len(ids)) & (ids[np.minimum(i, len(ids)-1)] == values)


def identities(a):
    if a.bodyId.isna().any() or a.bodyId.duplicated().any():
        raise ValueError('Missing or duplicate official identity')
    # Deliberately provisional. Do not discard candidates because of absent soma/type.
    selected = a.status.eq('Traced')
    n = a.loc[selected].copy().rename(columns={'bodyId': 'body_id', 'type': 'neuron_type',
        'status': 'proofreading_status', 'rootSide': 'side', 'entryNerve': 'nerve'})
    n['dataset'] = 'male-cns:v1.0'
    n['boundary_status'] = 'not_adjudicated'
    n['identity_evidence'] = 'official annotation status=Traced; provisional inclusion rule v1'
    return n, a.loc[~selected].copy()


def compile_graph(raw, out):
    start = time.perf_counter()
    out.mkdir(parents=True, exist_ok=False)
    sources = {}
    for name, expected in EXPECTED.items():
        actual = digest(raw/name)
        if actual != expected:
            raise ValueError('Frozen release hash mismatch: ' + name)
        receipt = raw/(name+'.receipt.json')
        sources[name] = {'sha256': actual, 'receipt': json.loads(receipt.read_text()) if receipt.exists() else None}
    annotations = pd.read_feather(raw/next(iter(EXPECTED)))
    neurons, candidates = identities(annotations)
    neurons.to_parquet(out/'neurons.parquet', index=False)
    candidates.to_parquet(out/'identity_review.parquet', index=False)
    ids = np.sort(neurons.body_id.to_numpy(dtype=np.uint64))
    np.save(out/'body_ids.npy', ids)
    source = pa.memory_map(str(raw/'connectome-weights-male-cns-v1.0-minconf-0.5.feather'), 'r')
    reader = pa.ipc.open_file(source)
    schema = pa.schema([('pre_body_id', pa.uint64()), ('post_body_id', pa.uint64()),
        ('structural_count', pa.uint64()), ('source_record', pa.uint64())])
    totals = {k: {'rows': 0, 'structural_count': 0} for k in ['internal', 'incoming_boundary', 'outgoing_boundary', 'unmapped']}
    degree = np.zeros((len(ids), 4), np.uint64)
    offset = 0
    with pq.ParquetWriter(out/'edges.parquet', schema, compression='zstd') as writer:
        for batch_index in range(reader.num_record_batches):
            b = reader.get_batch(batch_index)
            pre, post, count = [b.column(b.schema.get_field_index(k)).to_numpy() for k in ['body_pre', 'body_post', 'weight']]
            if np.any(count <= 0):
                raise ValueError('Nonpositive structural count')
            p, q = membership(ids, pre), membership(ids, post)
            masks = [p & q, ~p & q, p & ~q, ~p & ~q]
            for key, mask in zip(totals, masks):
                totals[key]['rows'] += int(mask.sum())
                totals[key]['structural_count'] += int(count[mask].sum(dtype=np.uint64))
            keep = masks[0]
            writer.write_table(pa.Table.from_arrays([pa.array(x, type=t) for x, t in zip(
                [pre[keep], post[keep], count[keep], np.flatnonzero(keep).astype(np.uint64)+offset], schema.types)], schema=schema))
            for mask, endpoint, col in [(keep, post, 0), (keep, pre, 1), (masks[1], post, 2), (masks[2], pre, 3)]:
                np.add.at(degree[:, col], np.searchsorted(ids, endpoint[mask]), count[mask].astype(np.uint64))
            offset += len(pre)
            if batch_index % 500 == 0:
                print(f'compiled {offset:,} source rows', flush=True)
    coverage = pd.DataFrame(degree, columns=['internal_input_count','internal_output_count','boundary_input_count','boundary_output_count'])
    coverage.insert(0, 'body_id', ids)
    coverage = coverage.merge(neurons[['body_id','superclass','somaNeuromere']], on='body_id', validate='one_to_one')
    coverage.to_parquet(out/'coverage.parquet', index=False)
    coverage.groupby('somaNeuromere', dropna=False).sum(numeric_only=True).drop(columns='body_id').to_csv(out/'coverage_by_soma_neuromere.csv')
    # This is soma-region coverage, NOT synaptic ROI coverage: the weight table has no ROI.
    audit = {'dataset': 'male-cns:v1.0', 'status': 'PROVISIONAL_NOT_PRODUCTION',
        'neurons': len(ids), 'review_candidates': len(candidates), 'source_rows': offset,
        'partition': totals, 'sources': sources, 'seconds': time.perf_counter()-start,
        'orientation': 'pre_body_id -> post_body_id', 'merges': [],
        'unresolved_representation': 'Raw source rows outside internal partition remain immutable and recoverable; identity_review contains annotated candidates only.',
        'limitations': ['Non-Traced peripheral/boundary identities require expert adjudication',
            'No complete unresolved unique segment table yet', 'No independent official query comparison yet',
            'No synaptic ROI/confidence data in source weight table', 'Duplicate pair audit pending; source records preserved without aggregation'],
        'files': {p.name: digest(p) for p in out.iterdir() if p.is_file()}}
    (out/'audit.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
    print(json.dumps({k: audit[k] for k in ['status','neurons','review_candidates','source_rows','partition','seconds']}, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', type=Path, default=Path('data/raw'))
    parser.add_argument('--out', type=Path, default=Path('data/graph_neurons'))
    args = parser.parse_args()
    compile_graph(args.raw, args.out)
