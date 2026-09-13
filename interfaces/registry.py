"""Validate manually reviewed interfaces without inventing biological IDs."""
import numpy as np
import pandas as pd

COMMON = ['dataset','side','evidence','confidence','reviewer','reviewed_at','unit']
SENSORY = COMMON + ['modality','receptor_or_neuron_type','body_id','peripheral_location',
    'receptive_field','transfer_function','gain','latency_ms','noise_model']
MOTOR = COMMON + ['motor_body_id','nerve','target_muscle','anatomical_attachments',
    'activation_model','recruitment','delay_ms']


def validate(table, neurons, kind):
    fields = SENSORY if kind == 'sensory' else MOTOR if kind == 'motor' else None
    if fields is None:
        raise ValueError('Unknown interface kind')
    if table.empty:
        raise ValueError('No reviewed '+kind+' mapping; physiological run unavailable')
    missing = set(fields)-set(table.columns)
    if missing:
        raise ValueError('Missing evidence fields: '+','.join(sorted(missing)))
    if table[fields].isna().any().any() or table[fields].astype(str).apply(lambda c: c.str.strip().eq('')).any().any():
        raise ValueError('Incomplete interface evidence')
    if not table.dataset.eq('male-cns:v1.0').all():
        raise ValueError('Cross-dataset IDs require an explicit independently reviewed crosswalk')
    key = 'body_id' if kind == 'sensory' else 'motor_body_id'
    known = neurons.set_index('body_id')
    if not table[key].isin(known.index).all():
        raise ValueError('Interface ID outside compiled neuron set')
    confidence = pd.to_numeric(table.confidence, errors='raise')
    delay = pd.to_numeric(table['latency_ms' if kind == 'sensory' else 'delay_ms'],errors='raise')
    if not np.isfinite(confidence).all() or not confidence.between(0,1).all() or not np.isfinite(delay).all() or (delay < 0).any():
        raise ValueError('Invalid confidence or delay')
    if kind == 'motor' and not known.loc[table[key],'superclass'].isin(['vnc_motor','cb_motor']).all():
        raise ValueError('Muscle output must originate in annotated motor neurons')
    if kind == 'sensory':
        gain = pd.to_numeric(table.gain,errors='raise')
        if not np.isfinite(gain).all():
            raise ValueError('Invalid receptor gain')
    return table.copy()


def write_review_tables(neurons, out):
    out.mkdir(parents=True, exist_ok=True)
    for name, fields in [('sensory',SENSORY),('motor',MOTOR)]:
        path = out/(name+'_map.parquet')
        if not path.exists():
            pd.DataFrame({k:pd.Series(dtype='string') for k in fields}).to_parquet(path,index=False)
    # Candidates are not approved ports; anatomical class alone cannot specify a muscle.
    neurons.loc[neurons.superclass.isin(['vnc_motor','cb_motor'])].to_parquet(out/'motor_candidates.parquet',index=False)
    neurons.loc[neurons.superclass.astype(str).str.contains('sensory')].to_parquet(out/'sensory_candidates.parquet',index=False)
