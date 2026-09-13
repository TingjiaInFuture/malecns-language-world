"""Explicit type/class parameter priors; no source-free default physiology."""
import json
import numpy as np
from .reference import Parameters

UNITS={'capacitance_pf':'pF','leak_ns':'nS','resting_mv':'mV','synapse_tau_ms':'ms',
       'adaptation_tau_ms':'ms','adaptation_ns':'nS'}


def sample_parameters(neuron_types, neuron_classes, records, seed):
    if len(neuron_types)!=len(neuron_classes):
        raise ValueError('Identity arrays differ')
    indexed = {}
    for row in records:
        parameter = row['parameter']
        if parameter not in UNITS or row['unit']!=UNITS[parameter] or not row['source'] or not row['applicable_sex_age_temperature']:
            raise ValueError('Missing provenance, applicability or wrong unit')
        if row['measured_or_inferred'] not in ['measured','inferred','software_fixture']:
            raise ValueError('Unknown evidence class')
        key=(row['type_or_class'],parameter)
        if key in indexed:
            raise ValueError('Conflicting priors for '+str(key))
        indexed[key]=row
    rng=np.random.default_rng(seed)
    values={p:np.empty(len(neuron_types)) for p in UNITS}
    selected=[]
    for i,(kind,category) in enumerate(zip(neuron_types,neuron_classes)):
        for parameter in UNITS:
            row=indexed.get((kind,parameter),indexed.get((category,parameter)))
            if row is None:
                raise ValueError(f'No explicit prior for {kind}/{category}: {parameter}')
            distribution=row['value_or_distribution']
            if isinstance(distribution,str):distribution=json.loads(distribution)
            if distribution['kind']=='fixed':value=float(distribution['value'])
            elif distribution['kind']=='uniform':
                lo,hi=distribution['low'],distribution['high']
                if not np.isfinite([lo,hi]).all() or lo>hi:raise ValueError('Invalid prior interval')
                value=rng.uniform(lo,hi)
            else:raise ValueError('Unsupported prior distribution')
            values[parameter][i]=value
            selected.append({'neuron_index':i,'parameter':parameter,'source':row['source'],
                'evidence':row['measured_or_inferred']})
    return Parameters(**values),selected
