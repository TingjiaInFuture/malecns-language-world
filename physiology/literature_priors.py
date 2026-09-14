"""Literature-anchored parameter priors for sampled cell types.

Every record names its evidence class: 'measured' values carry a citation and
conditions; 'inferred' values state the inference; 'software_fixture' values
are placeholders with no direct measurement. Most Drosophila electrophysiology
is from female preparations - the cross-sex transfer to a male model is itself
an explicit hypothesis recorded in the applicability string.
Run: python -m physiology.literature_priors
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .parameter_tables import sample_parameters

AZEVEDO = 'Azevedo et al. 2020, eLife 9:e56754 (doi:10.7554/eLife.56754), Fig 3C-E'
GU = 'Gu & O\'Dowd 2006, J Neurosci 26:265-267 (doi:10.1523/JNEUROSCI.4109-05.2006), Table 1'
FEMALE_FLEXOR = 'female 1-4 dpe w1118 x Berlin-K, room temp; male unmeasured - cross-sex transfer is an explicit hypothesis'
FEMALE_KC = 'female 1-5 d, room temp; male unmeasured'


def records():
    flexor = 'Ti flexor MN'
    extensor = 'Ti extensor MN'
    kc = 'Kenyon cell'
    no_direct = 'no direct measurement found; engineering placeholder pending experiments'
    out = []
    # Measured leak conductances: Rin 150-900 MOhm across fast/intermediate/slow flexor classes.
    out.append({'type_or_class': flexor, 'parameter': 'leak_ns',
        'value_or_distribution': {'kind': 'uniform', 'low': 1.1, 'high': 6.7}, 'unit': 'nS',
        'measured_or_inferred': 'measured',
        'source': AZEVEDO+'; leak=1/Rin over the pooled class range 150-900 MOhm; per-cell class assignment pending trial data',
        'applicable_sex_age_temperature': FEMALE_FLEXOR})
    out.append({'type_or_class': flexor, 'parameter': 'resting_mv',
        'value_or_distribution': {'kind': 'uniform', 'low': -68., 'high': -48.}, 'unit': 'mV',
        'measured_or_inferred': 'measured', 'source': AZEVEDO,
        'applicable_sex_age_temperature': FEMALE_FLEXOR})
    for parameter, value in [('capacitance_pf', 10.), ('synapse_tau_ms', 5.),
                             ('adaptation_tau_ms', 100.), ('adaptation_ns', .1)]:
        out.append({'type_or_class': flexor, 'parameter': parameter,
            'value_or_distribution': {'kind': 'fixed', 'value': value},
            'unit': {'capacitance_pf': 'pF', 'synapse_tau_ms': 'ms',
                     'adaptation_tau_ms': 'ms', 'adaptation_ns': 'nS'}[parameter],
            'measured_or_inferred': 'software_fixture', 'source': no_direct,
            'applicable_sex_age_temperature': 'placeholder; no measured value located for any sex'})
    out.append({'type_or_class': extensor, 'parameter': 'leak_ns',
        'value_or_distribution': {'kind': 'uniform', 'low': 1.1, 'high': 6.7}, 'unit': 'nS',
        'measured_or_inferred': 'inferred',
        'source': 'transferred from the measured flexor pool ('+AZEVEDO+'); extensor electrophysiology not found',
        'applicable_sex_age_temperature': FEMALE_FLEXOR})
    out.append({'type_or_class': extensor, 'parameter': 'resting_mv',
        'value_or_distribution': {'kind': 'uniform', 'low': -68., 'high': -48.}, 'unit': 'mV',
        'measured_or_inferred': 'inferred',
        'source': 'transferred from the measured flexor pool ('+AZEVEDO+')',
        'applicable_sex_age_temperature': FEMALE_FLEXOR})
    for parameter, value in [('capacitance_pf', 10.), ('synapse_tau_ms', 5.),
                             ('adaptation_tau_ms', 100.), ('adaptation_ns', .1)]:
        out.append({'type_or_class': extensor, 'parameter': parameter,
            'value_or_distribution': {'kind': 'fixed', 'value': value},
            'unit': {'capacitance_pf': 'pF', 'synapse_tau_ms': 'ms',
                     'adaptation_tau_ms': 'ms', 'adaptation_ns': 'nS'}[parameter],
            'measured_or_inferred': 'software_fixture', 'source': no_direct,
            'applicable_sex_age_temperature': 'placeholder; no measured value located for any sex'})
    out.append({'type_or_class': kc, 'parameter': 'leak_ns',
        'value_or_distribution': {'kind': 'uniform', 'low': .95, 'high': 1.05}, 'unit': 'nS',
        'measured_or_inferred': 'measured', 'source': GU+'; Rin 1.00+-0.05 GOhm',
        'applicable_sex_age_temperature': FEMALE_KC})
    out.append({'type_or_class': kc, 'parameter': 'resting_mv',
        'value_or_distribution': {'kind': 'uniform', 'low': -62.6, 'high': -59.2}, 'unit': 'mV',
        'measured_or_inferred': 'measured', 'source': GU+'; -60.9+-1.7 mV',
        'applicable_sex_age_temperature': FEMALE_KC})
    out.append({'type_or_class': kc, 'parameter': 'synapse_tau_ms',
        'value_or_distribution': {'kind': 'uniform', 'low': 4.6, 'high': 5.8}, 'unit': 'ms',
        'measured_or_inferred': 'measured', 'source': GU+'; mEPSC decay tau 5.2+-0.3 ms (approximates synaptic+membrane filter)',
        'applicable_sex_age_temperature': FEMALE_KC})
    for parameter, value in [('capacitance_pf', 10.), ('adaptation_tau_ms', 100.), ('adaptation_ns', .1)]:
        out.append({'type_or_class': kc, 'parameter': parameter,
            'value_or_distribution': {'kind': 'fixed', 'value': value},
            'unit': {'capacitance_pf': 'pF', 'adaptation_tau_ms': 'ms', 'adaptation_ns': 'nS'}[parameter],
            'measured_or_inferred': 'software_fixture', 'source': no_direct,
            'applicable_sex_age_temperature': 'placeholder; no measured value located for any sex'})
    return out


def main():
    candidates = pd.read_parquet('data/graph_neurons/interfaces/lf_tibia_candidates.parquet')
    rows = []
    parameters, selected = sample_parameters(candidates.neuron_type.tolist(),
        candidates.neuron_type.tolist(), records(), seed=20260914)
    for i, row in candidates.iterrows():
        rows.append({'body_id': int(row.body_id), 'neuron_type': row.neuron_type,
                     'capacitance_pf': float(parameters.capacitance_pf[i]),
                     'leak_ns': float(parameters.leak_ns[i]),
                     'resting_mv': float(parameters.resting_mv[i]),
                     'synapse_tau_ms': float(parameters.synapse_tau_ms[i]),
                     'adaptation_tau_ms': float(parameters.adaptation_tau_ms[i]),
                     'adaptation_ns': float(parameters.adaptation_ns[i])})
    evidence_counts = {}
    for entry in selected:
        key = (entry['parameter'], entry['evidence'])
        evidence_counts[str(key)] = evidence_counts.get(str(key), 0)+1
    report = {'scope': 'literature-anchored priors sampled for reviewed motor candidates',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'sampled_neurons': rows, 'evidence_class_counts': evidence_counts,
        'records_sha256': hashlib.sha256(json.dumps(records(), sort_keys=True).encode()).hexdigest(),
        'caveats': ['Per-cell fast/intermediate/slow class assignment pending measured trials',
                    'Most source measurements are female; male transfer is an explicit hypothesis',
                    'Fixture-class parameters remain placeholders, not physiology'],
        'biological_acceptance': False}
    Path('validation/literature-priors-evidence.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'neurons': len(rows), 'evidence_classes': sorted(set(e['evidence'] for e in selected))}, indent=2))


if __name__ == '__main__':
    main()
