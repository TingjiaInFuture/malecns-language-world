"""Per-synaptic-ROI coverage audit. Requires synapse-level data with an ROI column.

The v1.0 weight table has no ROI, so this tool refuses substitute inputs: soma
region is NOT synaptic ROI. When a synapse export exists, this reports
input/output structural counts and unmapped loss per ROI, per cell.
Run: python -m connectome.roi_audit --synapses <path> --graph data/graph_neurons
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

REQUIRED = {'pre_body_id', 'post_body_id', 'roi'}


def audit(synapses, neurons):
    missing = REQUIRED-set(synapses.columns)
    if missing:
        raise ValueError('Synapse export lacks columns: '+','.join(sorted(missing))+
                         '; a weight-only table cannot support a synaptic ROI audit')
    known = set(neurons.body_id.tolist())
    s = synapses
    pre_in, post_in = s.pre_body_id.isin(known), s.post_body_id.isin(known)
    masks = {'internal_rows': pre_in & post_in, 'incoming_boundary_rows': ~pre_in & post_in,
             'outgoing_boundary_rows': pre_in & ~post_in, 'unmapped_rows': ~pre_in & ~post_in}
    counts = {name: s[mask].groupby('roi').size() for name, mask in masks.items()}
    per_roi = pd.DataFrame(counts).fillna(0).astype(int).sort_index().reset_index(names='roi')
    cell_roi = s[masks['internal_rows']].groupby(['post_body_id', 'roi']).size() \
        .rename('roi_input_count').reset_index()
    conservation = {'rows': int(len(s)), **{name: int(mask.sum()) for name, mask in masks.items()}}
    return {'roi_partition': per_roi, 'cell_roi_inputs': cell_roi, 'conservation': conservation}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--synapses', type=Path, required=True)
    parser.add_argument('--graph', type=Path, default=Path('data/graph_neurons'))
    args = parser.parse_args()
    if not args.synapses.exists():
        raise SystemExit('synapse export missing: '+str(args.synapses))
    synapses = pd.read_parquet(args.synapses) if args.synapses.suffix == '.parquet' else pd.read_csv(args.synapses)
    neurons = pd.read_parquet(args.graph/'neurons.parquet')
    result = audit(synapses, neurons)
    out = Path('validation/roi-audit.json')
    out.write_text(json.dumps({'scope': 'synaptic ROI partition of supplied export',
        'source': str(args.synapses), 'biological_acceptance': False,
        'conservation': result['conservation'],
        'roi_partition': json.loads(result['roi_partition'].to_json(orient='records'))}, indent=2), encoding='utf-8')
    result['roi_partition'].to_parquet(args.graph/'roi_partition.parquet', index=False)
    result['cell_roi_inputs'].to_parquet(args.graph/'cell_roi_inputs.parquet', index=False)
    print(json.dumps(result['conservation'], indent=2))


if __name__ == '__main__':
    main()
