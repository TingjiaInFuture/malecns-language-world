"""Materialize explicit LF tibia motor candidates, never approved muscle ports."""
import json
from pathlib import Path
import pandas as pd


def run():
    graph = Path('data/graph_neurons')
    a = pd.read_parquet(graph/'neurons.parquet')
    selected = a.neuron_type.isin(['Ti flexor MN','Ti extensor MN']) & a.somaNeuromere.eq('T1') & a.somaSide.eq('L')
    c = a.loc[selected,['body_id','neuron_type','somaSide','somaNeuromere','exitNerve','mancBodyid','mancType']].copy()
    c['dataset'] = 'male-cns:v1.0'
    c['candidate_muscle'] = c.neuron_type.map({'Ti flexor MN':'LFTibia_flex_93434','Ti extensor MN':'LFTibia_extensor_93932'})
    c['status'] = 'CANDIDATE_NOT_REVIEWED'
    c['evidence'] = 'Official v1.0 type + soma T1/L + exit nerve; same anatomical muscle group name in FlyGym'
    c['unresolved'] = 'Soma laterality does not alone prove peripheral laterality; recruitment and specific muscle crosswalk unvalidated; MANC version unspecified'
    c.to_parquet(graph/'interfaces/lf_tibia_candidates.parquet',index=False)
    report = {'candidate_count':len(c),'production_ports_added':0,
        'ids':c.body_id.tolist(),'sources':['https://male-cns.janelia.org/download/',
        'https://github.com/gizemozd/FlyMimic','https://github.com/NeLy-EPFL/flygym/issues/276'],
        'reason_not_approved':'No independently reviewed body-to-muscle mapping or recruitment curves. Numeric suffixes in muscle names are not MaleCNS IDs.'}
    Path('validation/interface-research.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    run()
