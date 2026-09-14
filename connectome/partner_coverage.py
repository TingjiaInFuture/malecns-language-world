"""Stream syn-partners into a connection-level ROI partition with confidences.

Per synapse partner pair: which side is inside the compiled Traced set, the
postsynaptic primary ROI, and the mean partner confidences per partition. This
is the connection-level companion to synapse_coverage (synapse-side counts).
Run: python -m connectome.partner_coverage --partners data/raw/syn-partners-...feather
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa

from .synapse_coverage import membership

PARTITIONS = ['internal', 'incoming_boundary', 'outgoing_boundary', 'unmapped']


def stream(partners_path, ids):
    source = pa.memory_map(str(partners_path), 'r')
    reader = pa.ipc.open_file(source)
    roi_counts = {}
    totals = {k: 0 for k in PARTITIONS}
    confidence = {k: [0., 0., 0] for k in PARTITIONS}  # sum conf_pre, sum conf_post, n
    processed = 0
    for index in range(reader.num_record_batches):
        batch = reader.get_batch(index)
        frame = batch.select(['body_pre', 'body_post', 'conf_pre', 'conf_post', 'primary_post']).to_pandas()
        known_pre = membership(ids, frame.body_pre.to_numpy(dtype=np.uint64))
        known_post = membership(ids, frame.body_post.to_numpy(dtype=np.uint64))
        partitions = np.select(
            [known_pre & known_post, ~known_pre & known_post, known_pre & ~known_post],
            ['internal', 'incoming_boundary', 'outgoing_boundary'], default='unmapped')
        frame['partition'] = partitions
        frame['roi'] = frame.primary_post.astype('object').fillna('unassigned')
        grouped = frame.groupby(['roi', 'partition'], observed=True).size()
        for (roi, partition), count in grouped.items():
            key = (str(roi), str(partition))
            roi_counts[key] = roi_counts.get(key, 0)+int(count)
            totals[str(partition)] += int(count)
        for name, mask in [('internal', known_pre & known_post),
                           ('incoming_boundary', ~known_pre & known_post),
                           ('outgoing_boundary', known_pre & ~known_post),
                           ('unmapped', ~(known_pre | known_post))]:
            part = frame[mask]
            confidence[name][0] += float(part.conf_pre.sum())
            confidence[name][1] += float(part.conf_post.sum())
            confidence[name][2] += int(len(part))
        processed += len(frame)
        if index % 100 == 0:
            print(f'processed {processed:,} partner pairs', flush=True)
    return {'roi_counts': {f'{k[0]}|{k[1]}': v for k, v in roi_counts.items()},
            'totals': totals, 'confidence': {k: {'mean_conf_pre': v[0]/v[2] if v[2] else None,
                                                 'mean_conf_post': v[1]/v[2] if v[2] else None,
                                                 'pairs': v[2]} for k, v in confidence.items()},
            'processed': processed}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--partners', type=Path, required=True)
    parser.add_argument('--graph', type=Path, default=Path('data/graph_neurons'))
    args = parser.parse_args()
    ids = np.load(args.graph/'body_ids.npy')
    result = stream(args.partners, ids)
    rows = [{'roi': key.split('|')[0], 'partition': key.split('|')[1], 'pairs': value}
            for key, value in result['roi_counts'].items()]
    pd.DataFrame(rows).sort_values(['partition', 'pairs'], ascending=[True, False]) \
        .to_parquet(args.graph/'partner_roi_partition.parquet', index=False)
    report = {'scope': 'connection-level ROI partition of the syn-partners export',
        'source': str(args.partners), 'totals': result['totals'],
        'partner_confidences': result['confidence'], 'processed_pairs': result['processed'],
        'biological_acceptance': False,
        'note': 'Pairs are synapse-level partner records; primary_post is the postsynaptic ROI. '
                'Confidence means are per-partition summaries, not per-connection quality.'}
    Path('validation/partner-coverage.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'totals': result['totals'], 'processed_pairs': result['processed']}, indent=2))


if __name__ == '__main__':
    main()
