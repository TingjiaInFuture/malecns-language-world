"""Extract the real MaleCNS circuit around reviewed left-front tibia motor candidates.

Structural evidence for the pre-connection review: inputs and outputs of the
candidate motor neurons from the compiled graph, with partner type, soma side,
neurotransmitter and structural counts. Counts constrain nothing physiological;
they are the substrate a reviewed closed loop must account for.
Run: python -m experiments.motor_circuit_extract
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

CANDIDATES = 'data/graph_neurons/interfaces/motor_map_reviewed_automated.parquet'
UNRESOLVED = 'data/graph_neurons/interfaces/motor_unresolved_conflicts.parquet'


def extract(graph='data/graph_neurons', top=25):
    reviewed = pd.read_parquet(CANDIDATES)
    neurons = pd.read_parquet(Path(graph)/'neurons.parquet')
    types = neurons.set_index('body_id')[['neuron_type', 'superclass', 'side', 'somaNeuromere', 'nerve']]
    nt = pd.read_feather('data/raw/body-neurotransmitters-male-cns-v1.0.feather')
    nt_cols = {c: c for c in nt.columns}
    body_nt = nt.set_index('bodyId') if 'bodyId' in nt.columns else None
    motors = reviewed.motor_body_id.tolist()
    edges = pd.read_parquet(Path(graph)/'edges.parquet',
                            filters=[('post_body_id', 'in', motors)])
    inputs = edges.groupby('pre_body_id').structural_count.sum().sort_values(ascending=False)
    inputs = inputs.head(top).reset_index()
    inputs = inputs.join(types, on='pre_body_id')
    outputs_all = pd.read_parquet(Path(graph)/'edges.parquet',
                                  filters=[('pre_body_id', 'in', motors)])
    outputs = outputs_all.groupby('post_body_id').structural_count.sum().sort_values(ascending=False)
    outputs = outputs.head(top).reset_index()
    outputs = outputs.join(types, on='post_body_id')
    if body_nt is not None:
        for table, key in [(inputs, 'pre_body_id'), (outputs, 'post_body_id')]:
            name = [c for c in body_nt.columns if 'transmitter' in c.lower()]
            if name:
                table[name[0]] = body_nt[name[0]].reindex(table[key]).to_numpy()
    total_in = int(edges.structural_count.sum())
    total_out = int(outputs_all.structural_count.sum())
    return reviewed, inputs, outputs, {'input_partner_rows': len(inputs), 'output_partner_rows': len(outputs),
        'input_structural_count_total': total_in, 'output_structural_count_total': total_out,
        'input_partners_traced_total': int(edges.pre_body_id.nunique()),
        'output_partners_traced_total': int(outputs_all.post_body_id.nunique())}


def main():
    reviewed, inputs, outputs, totals = extract()
    out_dir = Path('data/graph_neurons/interfaces')
    inputs.to_parquet(out_dir/'lf_tibia_motor_inputs.parquet', index=False)
    outputs.to_parquet(out_dir/'lf_tibia_motor_outputs.parquet', index=False)
    unresolved = pd.read_parquet(UNRESOLVED)
    report = {'scope': 'structural partner evidence for the reviewed LF tibia motor candidates',
        'created_at': datetime.now(timezone.utc).isoformat(), 'totals': totals,
        'reviewed_motor_ids': reviewed.motor_body_id.tolist(),
        'unresolved_conflicts': unresolved.to_dict(orient='records'),
        'top_inputs': json.loads(inputs.to_json(orient='records')),
        'top_outputs': json.loads(outputs.to_json(orient='records')),
        'note': 'Structural counts are not conductances; no partner is approved as a production port here.',
        'biological_acceptance': False,
        'source_sha256': {p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
            for p in ['data/graph_neurons/edges.parquet', 'data/graph_neurons/neurons.parquet']}}
    Path('validation/motor-circuit-extract.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(totals, indent=2))


if __name__ == '__main__':
    main()
