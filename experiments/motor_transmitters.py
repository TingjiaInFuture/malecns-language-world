"""Transmitter composition of the reviewed LF tibia motor circuit. Streaming.

Streams the per-T-bar neurotransmitter probabilities restricted to the reviewed
motor neurons and their top structural partners, so the premotor review sees
which transmitter classes actually contact the candidates. Probabilities are
predictions, not measurements; per-body means are reported with T-bar counts.
Run: python -m experiments.motor_transmitters
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa

TRANSMITTERS = ['acetylcholine', 'dopamine', 'gaba', 'glutamate', 'histamine', 'octopamine', 'serotonin']


def stream_profiles(tbar_path, bodies):
    wanted = set(int(b) for b in bodies)
    source = pa.memory_map(str(tbar_path), 'r')
    reader = pa.ipc.open_file(source)
    columns = ['body', 'conf']+['nt_'+t+'_prob' for t in TRANSMITTERS]
    sums = {b: np.zeros(len(TRANSMITTERS)+1) for b in wanted}  # + conf
    counts = {b: 0 for b in wanted}
    processed = 0
    for index in range(reader.num_record_batches):
        frame = reader.get_batch(index).select(columns).to_pandas()
        mask = frame.body.isin(wanted)
        if mask.any():
            part = frame[mask]
            for body, row in part.groupby('body'):
                sums[int(body)][:-1] += row[['nt_'+t+'_prob' for t in TRANSMITTERS]].to_numpy().sum(axis=0)
                sums[int(body)][-1] += float(row.conf.sum())
                counts[int(body)] += int(len(row))
        processed += len(frame)
        if index % 100 == 0:
            print(f'processed {processed:,} T-bars', flush=True)
    profiles = {}
    for body in wanted:
        n = counts[body]
        profiles[body] = {'tbar_count': n,
                          'mean_conf': float(sums[body][-1]/n) if n else None,
                          'mean_probabilities': {t: float(sums[body][i]/n) for i, t in enumerate(TRANSMITTERS)} if n else None}
        if n:
            probs = profiles[body]['mean_probabilities']
            profiles[body]['dominant'] = max(probs, key=probs.get)
    return profiles, processed


def main():
    interfaces = Path('data/graph_neurons/interfaces')
    reviewed = pd.read_parquet(interfaces/'motor_map_reviewed_automated.parquet')
    inputs = pd.read_parquet(interfaces/'lf_tibia_motor_inputs.parquet')
    outputs = pd.read_parquet(interfaces/'lf_tibia_motor_outputs.parquet')
    types = pd.read_parquet('data/graph_neurons/neurons.parquet').set_index('body_id').neuron_type
    bodies = list(reviewed.motor_body_id)+inputs.pre_body_id.tolist()+outputs.post_body_id.tolist()
    profiles, processed = stream_profiles('data/raw/tbar-neurotransmitters-male-cns-v1.0.feather', bodies)
    labeled = {}
    for body, profile in profiles.items():
        label = 'REVIEWED_MN' if body in set(reviewed.motor_body_id) else \
                ('input_partner' if body in set(inputs.pre_body_id) else 'output_partner')
        labeled[str(int(body))] = {'role': label, 'neuron_type': types.get(int(body)),
                                   **profile}
    report = {'scope': 'per-T-bar transmitter prediction profiles for the reviewed LF tibia motor circuit',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'source': 'tbar-neurotransmitters-male-cns-v1.0.feather (predictions, not measurements)',
        'processed_tbars': processed, 'bodies': len(labeled),
        'profiles': labeled,
        'note': 'Dominant transmitter of the largest premotor inputs constrains receptor hypotheses '
                'for the closed-loop review; unclear predictions stay unclear.',
        'biological_acceptance': False,
        'source_receipt': 'data/raw/tbar-neurotransmitters-male-cns-v1.0.feather.receipt.json is authoritative'}
    out = Path('validation/motor-transmitters.json')
    out.write_text(json.dumps(report, indent=2), encoding='utf-8')
    summary = {b: {'role': v['role'], 'type': v['neuron_type'], 'dominant': v.get('dominant'),
                   'tbars': v['tbar_count']} for b, v in labeled.items() if v['role'] == 'REVIEWED_MN'}
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
