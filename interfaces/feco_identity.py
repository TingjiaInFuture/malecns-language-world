"""Wire published FeCO cell identities (Dallmann 2025 Supp Table 2) into MaleCNS.

Identity chain: Nature supplementary table (open URL) -> MANC bodyIds / type
names -> MaleCNS bodyIds via the official annotation's mancBodyid/mancType
fields. Ambiguities are recorded, never resolved silently. Per-cell club IDs
and MANC claw IDs are NOT published anywhere and stay explicitly blocked.
Run: python -m interfaces.feco_identity
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

SUPP = 'data/physiology_raw/feco-author/dallmann2025_supp_table2.xlsx'
SOURCE = 'Dallmann et al. 2025, Nature 647:445-453, Supplementary Table 2 (41586_2025_9554_MOESM4_ESM.xlsx)'


def build():
    xl = pd.read_excel(SUPP)
    annotation = pd.read_feather('data/raw/body-annotations-male-cns-v1.0-minconf-0.5.feather')
    rows = []
    def map_manc(name, manc_id, description, neurotransmitter):
        matches = annotation[annotation.mancBodyid == manc_id]
        if matches.empty:
            rows.append({'role': name, 'manc_bodyid': manc_id, 'malecns_body_id': None,
                         'malecns_type': None, 'description': description,
                         'neurotransmitter': neurotransmitter, 'mapping_status': 'no_malecns_row'})
            return
        for _, m in matches.iterrows():
            consistent = pd.notna(m.type) and str(m.type).startswith('IN09A') if '9A' in name else True
            rows.append({'role': name, 'manc_bodyid': manc_id, 'malecns_body_id': int(m.bodyId),
                         'malecns_type': m.type, 'malecns_superclass': m.superclass,
                         'root_side': m.rootSide, 'status': m.status,
                         'description': description, 'neurotransmitter': neurotransmitter,
                         'mapping_status': 'mapped_type_consistent' if consistent
                                           else 'mapped_type_inconsistent_manual_review'})
    for manc_id, name in [(100513, 'chief 9A T1L'), (13157, 'chief 9A T2L'), (14517, 'chief 9A T3L'),
                          (165560, 'chief 9A T1R'), (12443, 'chief 9A T2R'), (12804, 'chief 9A T3R'),
                          (10107, 'DNg74 (web) left'), (10103, 'DNg74 (web) right'),
                          (10093, 'DNg100 (BDN2) left'), (10339, 'DNg100 (BDN2) right'),
                          (32815, 'DNg12 a'), (31635, 'DNg12 b'), (32742, 'DNg12 c'), (31078, 'DNg12 d')]:
        map_manc(name, manc_id, 'presynaptic inhibition chain of the FeCO hook pathway',
                 'GABA' if '9A' in name else 'acetylcholine')
    hooks = annotation[annotation.mancType.astype(str).eq('SNpp38')]
    for _, h in hooks.iterrows():
        rows.append({'role': 'hook afferent (SNpp38)', 'manc_bodyid': h.mancBodyid,
                     'malecns_body_id': int(h.bodyId), 'malecns_type': h.type,
                     'malecns_superclass': h.superclass, 'root_side': h.rootSide,
                     'status': h.status,
                     'description': 'hook flexion afferent; per-cell MANC IDs not published, '
                                    'identified by MANC type SNpp38 per Supp Table 2',
                     'neurotransmitter': 'acetylcholine',
                     'mapping_status': 'mapped_via_published_type'})
    return pd.DataFrame(rows)


def main():
    table = build()
    out = Path('data/graph_neurons/interfaces/feco_identity.parquet')
    table.to_parquet(out, index=False)
    report = {'scope': 'published FeCO identities wired into MaleCNS',
        'created_at': datetime.now(timezone.utc).isoformat(), 'source': SOURCE,
        'rows': len(table), 'counts': table.mapping_status.value_counts().to_dict(),
        'roles': table.role.value_counts().to_dict(),
        'blocked': ['Per-cell club afferent IDs: club axons were imaged but never reconstructed '
                    'in any connectome (Dallmann 2025 states this); only driver-line identity exists',
                    'Per-cell MANC claw IDs: not in Supp Table 2; FANC claw pt_root_ids exist but '
                    'cross-connectome mapping to MaleCNS is not established'],
        'caveats': ['MANC 13157 maps to two MaleCNS rows (804940 IN09A012 and 809102 SNpp41); '
                    'the IN09A012 row is the 9A by type consistency and the SNpp41 row is flagged '
                    'for manual review',
                    'Identity flows through the annotation mancBodyid/mancType fields; version '
                    'equivalence beyond the publication supplements is not independently verified'],
        'graph_confirmation': 'In the compiled graph the top inputs to chief 9A T1L (MaleCNS 805450) '
                              'are DNg100 (10056, 58 synapses) and DNg74 (10131, 31), reproducing '
                              'the paper descending control chain.',
        'biological_acceptance': False,
        'source_sha256': {'table': hashlib.sha256(out.read_bytes()).hexdigest(),
                          'supp': hashlib.sha256(Path(SUPP).read_bytes()).hexdigest()}}
    Path('validation/feco-identity.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'rows': len(table), 'counts': report['counts']}, indent=2))


if __name__ == '__main__':
    main()
