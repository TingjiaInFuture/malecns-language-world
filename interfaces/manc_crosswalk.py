"""Join source-declared MaleCNS MANC identifiers to published MANC supplements.

Type agreement is a candidate check, not proof of physiological or cross-version
identity. Preserve missing matches, confidence and one-to-many mappings.
"""
import json
from pathlib import Path
import pandas as pd
from experiments.public_data import sha256


def join_candidates(candidates, matching, serial):
    if matching.bodyid.duplicated().any() or serial.bodyid.duplicated().any():
        raise ValueError('Supplement ID duplication needs explicit adjudication')
    matching=matching.rename(columns={c:'manc_'+c for c in matching.columns})
    serial=serial.rename(columns={c:'serial_'+c for c in serial.columns})
    out=candidates.merge(matching,how='left',left_on='mancBodyid',right_on='manc_bodyid',validate='many_to_one')
    out=out.merge(serial,how='left',left_on='mancBodyid',right_on='serial_bodyid',validate='many_to_one')
    out['type_agrees']=out.neuron_type.eq(out.manc_type)
    out['crosswalk_status']='candidate_type_agreement'
    out.loc[~out.type_agrees,'crosswalk_status']='type_conflict'
    out.loc[out.manc_bodyid.isna(),'crosswalk_status']='missing_supplement_identity'
    out['confidence_available']=out['manc_match_certainty(1-5)'].notna()
    out['manc_dataset_version']='publication supplement; do not infer equivalence to every MANC release'
    out['approved_production_io']=False
    return out


def main():
    paths=[Path('data/graph_neurons/interfaces/lf_tibia_candidates.parquet'),
           Path('data/physiology_raw/manc/elife-96084-supp3-v1.csv'),
           Path('data/physiology_raw/manc/elife-96084-supp6-v1.csv')]
    for path in paths[1:]:
        receipt=json.loads(path.with_suffix(path.suffix+'.receipt.json').read_text())
        if sha256(path)!=receipt['sha256']:raise ValueError('Supplement source changed')
    joined=join_candidates(pd.read_parquet(paths[0]),pd.read_csv(paths[1]),pd.read_csv(paths[2]))
    target=Path('data/graph_neurons/interfaces/manc_lf_tibia_crosswalk.parquet')
    joined.to_parquet(target,index=False)
    report={'sources':{str(p):sha256(p) for p in paths},'rows':len(joined),
        'counts':joined.crosswalk_status.value_counts().to_dict(),'production_ports_approved':0,
        'rows_for_review':json.loads(joined[['body_id','mancBodyid','neuron_type','manc_type','manc_target',
            'manc_exit_nerve','manc_match_certainty(1-5)','crosswalk_status']].to_json(orient='records'))}
    Path('validation/manc-crosswalk-evidence.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
