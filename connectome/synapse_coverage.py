"""Stream the syn-points export into per-ROI coverage and loss for the neuron set.

syn-points has one row per pre/post synapse side: body id, kind (PreSyn/PostSyn)
and encompassing ROI(s) (possibly multi-valued), positions in 8 nm voxel units.
This produces the roadmap's per-synaptic-ROI input/output coverage for the
compiled Traced identities and the unmapped loss, without loading the 12.7 GB
table into memory. Grouped cell-level tables stay on disk.
Run: python -m connectome.synapse_coverage --points data/raw/syn-points-...feather
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq


def membership(ids, values):
    if not len(ids):
        return np.zeros(len(values), bool)
    i = np.searchsorted(ids, values)
    return (i < len(ids)) & (ids[np.minimum(i, len(ids)-1)] == values)


def stream(points_path, ids, batch_limit=None, roi_column='primary'):
    import pandas as pd
    source = pa.memory_map(str(points_path), 'r')
    reader = pa.ipc.open_file(source)
    roi_counts = {}  # roi -> [known_pre, known_post, unknown_pre, unknown_post]
    totals = np.zeros(4, dtype=np.int64)
    body_counts = np.zeros((len(ids), 2), dtype=np.int64)
    processed = 0
    for index in range(reader.num_record_batches):
        batch = reader.get_batch(index)
        schema_names = batch.schema.names
        body_column = 'body' if 'body' in schema_names else 'bodyId'
        column = roi_column if roi_column in schema_names else ('roi' if 'roi' in schema_names else 'rois')
        frame = batch.select([body_column, 'kind', column]).to_pandas()
        frame.columns = ['body', 'kind', 'roi']
        frame['known'] = membership(ids, frame.body.to_numpy(dtype=np.uint64))
        frame['pre'] = frame.kind.eq('PreSyn')
        np.add.at(body_counts[:, 0], np.searchsorted(ids, frame.loc[frame.known & frame.pre, 'body'].to_numpy(dtype=np.uint64)), 1)
        np.add.at(body_counts[:, 1], np.searchsorted(ids, frame.loc[frame.known & ~frame.pre, 'body'].to_numpy(dtype=np.uint64)), 1)
        totals[0] += int((frame.known & frame.pre).sum()); totals[1] += int((frame.known & ~frame.pre).sum())
        totals[2] += int((~frame.known & frame.pre).sum()); totals[3] += int((~frame.known & ~frame.pre).sum())
        # ROI strings may be single or list-valued; explode normalizes both.
        exploded = frame.explode('roi')
        exploded['roi'] = exploded.roi.astype('object').fillna('unassigned')
        grouped = exploded.groupby(['roi', 'known', 'pre'], observed=True).size()
        for (roi, known, pre), count in grouped.items():
            slot = (0 if known else 2)+(0 if pre else 1)
            roi_counts.setdefault(roi, np.zeros(4, dtype=np.int64))[slot] += int(count)
        processed += len(frame)
        if batch_limit and processed >= batch_limit:
            break
        if index % 100 == 0:
            print(f'processed {processed:,} synapse sides', flush=True)
    roi_known = {k: [int(v[0]), int(v[1])] for k, v in roi_counts.items()}
    roi_unknown = {k: [int(v[2]), int(v[3])] for k, v in roi_counts.items() if v[2] or v[3]}
    return {'roi_known': roi_known, 'roi_unknown': roi_unknown,
            'totals': {'known_pre': int(totals[0]), 'known_post': int(totals[1]),
                       'unknown_pre': int(totals[2]), 'unknown_post': int(totals[3])},
            'body_counts': body_counts, 'processed': processed}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--points', type=Path, required=True)
    parser.add_argument('--graph', type=Path, default=Path('data/graph_neurons'))
    parser.add_argument('--roi-column', default='primary',
                        help="ROI hierarchy column in the export ('primary' matches the paper's ROI naming)")
    args = parser.parse_args()
    ids = np.load(args.graph/'body_ids.npy')
    result = stream(args.points, ids, roi_column=args.roi_column)
    import pandas as pd
    rows = [{'roi': roi, 'known_pre': v[0], 'known_post': v[1]} for roi, v in sorted(result['roi_known'].items())]
    rows += [{'roi': roi, 'unknown_pre': v[0], 'unknown_post': v[1]} for roi, v in sorted(result['roi_unknown'].items())]
    pd.DataFrame(rows).to_parquet(args.graph/'synapse_roi_coverage.parquet', index=False)
    bodies = pd.DataFrame({'body_id': ids, 'presynaptic_sites': result['body_counts'][:, 0],
                           'postsynaptic_sites': result['body_counts'][:, 1]})
    bodies.to_parquet(args.graph/'cell_synapse_counts.parquet', index=False)
    report = {'scope': 'per-ROI synapse-side coverage and loss for the compiled Traced identities',
        'source': str(args.points), 'roi_column': args.roi_column,
        'totals': result['totals'], 'processed_sides': result['processed'],
        'roi_count_known': len(result['roi_known']), 'roi_count_unknown': len(result['roi_unknown']),
        'biological_acceptance': False,
        'note': 'Coverage is of synapse sides, not weighted connectivity; cross-check against '
                'data/raw/quality CSVs (paper per-ROI precision/recall) before drawing conclusions.'}
    Path('validation/synapse-coverage.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(result['totals'], indent=2))


if __name__ == '__main__':
    main()
