"""Automated evidence cross-check of candidate I/O ports, one step from production.

Adjudication rules (documented, replayable):
  1. MaleCNS type == MANC supplement type  -> reviewed candidate.
  2. Supplement row missing but the official annotation's own mancType agrees
     -> reviewed candidate with an explicit supplement gap.
  3. MaleCNS type conflicts with the MANC supplement (including the embedded
     mancType field) -> unresolved; excluded from every port table.

Automated review is recorded as such and never equals human sign-off. Production
tables change only through --approve with an explicit human reviewer name.
Run: python -m interfaces.review [--approve "Full Name" --role "PI"]
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REVIEWER = 'automated_crosscheck_v1 (claude-code session 2026-09-14)'
OUT = Path('data/graph_neurons/interfaces')

MOTOR_FIELDS = ['dataset', 'side', 'evidence', 'confidence', 'reviewer', 'reviewed_at', 'unit',
    'motor_body_id', 'nerve', 'target_muscle', 'anatomical_attachments', 'activation_model',
    'recruitment', 'delay_ms']


def adjudicate(crosswalk):
    rows, unresolved = [], []
    for _, c in crosswalk.iterrows():
        nerve = 'ProLN_L' if str(c.exitNerve) == 'ProLN' and c.somaSide == 'L' else str(c.exitNerve)
        muscle = 'LFTibia_flex_93434' if c.neuron_type == 'Ti flexor MN' else \
            'LFTibia_extensor_93932' if c.neuron_type == 'Ti extensor MN' else None
        if muscle is None:
            raise ValueError('Unexpected candidate type outside the tibia motor set')
        base_evidence = (f"official male-cns:v1.0 annotation: Traced {c.neuron_type}, root side {c.somaSide}, "
                         f"exit nerve {c.exitNerve}, T1; FlyMimic LF muscle model {muscle} (numeric suffix is an "
                         f"upstream mesh id, not a MaleCNS body id); MANC crosswalk {c.crosswalk_status}")
        if c.crosswalk_status == 'candidate_type_agreement':
            status, confidence = 'reviewed_automated', .5
            evidence = base_evidence+f"; MANC supp3/supp6 type {c.manc_type} agrees"
        elif c.crosswalk_status == 'missing_supplement_identity':
            status, confidence = 'reviewed_automated_supplement_gap', .4
            evidence = base_evidence+"; no supp3 row; official embedded mancType agrees with MaleCNS type"
        else:
            unresolved.append({'body_id': int(c.body_id), 'manc_bodyid': None if pd.isna(c.manc_bodyid) else int(c.manc_bodyid),
                'malecns_type': c.neuron_type, 'manc_type': c.manc_type,
                'reason': 'cross-dataset type conflict (MaleCNS Ti flexor MN vs MANC Acc. ti flexor MN); '
                          'accessory tibia flexor is a distinct target muscle, so the port is withheld '
                          'until anatomical or measured evidence adjudicates the label'})
            continue
        rows.append({'dataset': 'male-cns:v1.0', 'side': f"{c.somaSide} (root side; peripheral laterality unverified)",
            'evidence': evidence, 'confidence': confidence, 'reviewer': REVIEWER,
            'reviewed_at': datetime.now(timezone.utc).isoformat(), 'unit': 'mV membrane potential -> muscle activation [0,1]',
            'motor_body_id': int(c.body_id), 'nerve': nerve, 'target_muscle': muscle,
            'anatomical_attachments': 'tibia flexor/extensor muscle group of the left front leg in the FlyMimic '
                                      'musculoskeletal model; exact origin/insertion awaits anatomical audit',
            'activation_model': 'voltage-threshold linear recruitment placeholder; class-specific force-per-spike '
                                'curves pending measured trial data (Azevedo et al. 2020 size-principle dataset not yet obtained)',
            'recruitment': 'pool-level size principle established (slow->intermediate->fast; force per spike ~10/1/<0.1 uN '
                           'for fast/intermediate/slow flexor classes, Azevedo 2020 eLife 9:e56754, female 1-4 dpe); '
                           'per-cell class assignment and thresholds pending measured trials',
            'delay_ms': 1.3,
            'delay_ms_evidence': 'upper bound of measured soma->EMG conduction delay 0.6-1.3 ms '
                                 '(Azevedo 2020, Fig 4G; female 1-4 dpe); excludes NMJ and muscle activation (~8.5 ms half-max), '
                                 'which live in the MuJoCo muscle model',
            'review_status': status})
    return pd.DataFrame(rows, columns=MOTOR_FIELDS+['review_status', 'delay_ms_evidence']), unresolved


def main():
    crosswalk = pd.read_parquet(OUT/'manc_lf_tibia_crosswalk.parquet')
    reviewed, unresolved = adjudicate(crosswalk)
    OUT.mkdir(parents=True, exist_ok=True)
    reviewed.to_parquet(OUT/'motor_map_reviewed_automated.parquet', index=False)
    pd.DataFrame(unresolved).to_parquet(OUT/'motor_unresolved_conflicts.parquet', index=False)
    report = {'reviewer': REVIEWER, 'human_signoff': None, 'reviewed_rows': len(reviewed),
        'unresolved_conflicts': unresolved, 'production_ports_approved': 0,
        'rules': ['type agreement -> reviewed', 'supplement gap with agreeing embedded mancType -> reviewed with gap',
                  'type conflict -> unresolved, excluded'],
        'note': 'Automated cross-check only. Production interface tables remain empty until a named human '
                'reviewer runs --approve after inspecting the evidence columns.',
        'sensory_status': 'No local evidence identifies MaleCNS body IDs for FeCO club/hook/claw afferents; '
                          'requires manc_v1_classifications.csv (Dryad, token-gated) and experimental driver mapping.',
        'biological_acceptance': False}
    args = None
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--approve':
        parser = argparse.ArgumentParser()
        parser.add_argument('--approve', metavar='REVIEWER_NAME', required=True)
        parser.add_argument('--role', default='human expert')
        parsed = parser.parse_args(sys.argv[1:])
        production = reviewed.drop(columns=['review_status', 'delay_ms_evidence']).copy()
        production['reviewer'] = f"{parsed.approve} ({parsed.role}); on top of {REVIEWER}"
        production['reviewed_at'] = datetime.now(timezone.utc).isoformat()
        production.to_parquet(OUT/'motor_map.parquet', index=False)
        report['production_ports_approved'] = len(production)
        report['human_signoff'] = parsed.approve
    Path('validation/interface-review.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k: report[k] for k in ['reviewed_rows', 'production_ports_approved']}, indent=2))


if __name__ == '__main__':
    main()
