"""Grouped-data calibration utilities with explicit biological acceptance gates."""
from datetime import datetime
import hashlib
import json
import numpy as np
from scipy.optimize import least_squares
from .measurement import assert_disjoint_groups


def validate_protocol(protocol, records):
    required = ['protocol_id','registered_at','dataset_sha256','conditions','thresholds','scope']
    if any(k not in protocol for k in required):
        raise ValueError('Incomplete preregistration')
    if protocol['scope'] not in ['software_fixture','biological']:
        raise ValueError('Unknown protocol scope')
    when = datetime.fromisoformat(protocol['registered_at'])
    if when.tzinfo is None:
        raise ValueError('Registration time requires timezone')
    if not protocol['dataset_sha256'] or any(len(h)!=64 or any(c not in '0123456789abcdef' for c in h) for h in protocol['dataset_sha256']):
        raise ValueError('Dataset SHA-256 identities required')
    for key in ['sex','age_days','strain','temperature_c','light_protocol','nutrition']:
        if key not in protocol['conditions'] or protocol['conditions'][key] is None:
            raise ValueError('Missing experimental condition '+key)
    if not protocol['thresholds']:
        raise ValueError('No registered validation thresholds')
    for name,spec in protocol['thresholds'].items():
        if not spec.get('unit') or not spec.get('reliability_source') or not np.isfinite(spec['maximum']) or spec['maximum'] < 0:
            raise ValueError('Invalid empirical tolerance '+name)
    assert_disjoint_groups(records)
    if set(r['split'] for r in records) != {'train','validation','test'}:
        raise ValueError('Train, validation and test groups all required')
    for r in records:
        if r['dataset_sha256'] not in protocol['dataset_sha256']:
            raise ValueError('Unregistered data')
        recorded = datetime.fromisoformat(r['evaluated_at'])
        if recorded.tzinfo is None or recorded <= when:
            raise ValueError('Evaluation must follow preregistration')
    return hashlib.sha256(json.dumps(protocol,sort_keys=True).encode()).hexdigest()


def fit_ensemble(residual, starts, lower, upper, prior_mean, prior_sd, prior_weight=1.):
    """Fit on caller-supplied training residual only; retain all optimizer outcomes.

    residual(parameters) must exclude validation/test observations. The returned
    parameter ensemble is calibration, not lifetime neural learning.
    """
    lower,upper,mean,sd = [np.asarray(a,dtype=float) for a in [lower,upper,prior_mean,prior_sd]]
    if any(a.shape != mean.shape or not np.isfinite(a).all() for a in [lower,upper,sd]) or not np.isfinite(mean).all() or np.any(sd<=0) or np.any(lower>=upper) or not np.isfinite(prior_weight) or prior_weight<0:
        raise ValueError('Invalid finite parameter priors or bounds')
    outcomes = []
    def objective(parameters):
        r = np.asarray(residual(parameters),dtype=float).ravel()
        if not np.isfinite(r).all():
            raise ValueError('Nonfinite training residual')
        return np.r_[r,np.sqrt(prior_weight)*(parameters-mean)/sd]
    for start in starts:
        fit = least_squares(objective,start,bounds=(lower,upper))
        outcomes.append({'parameters':fit.x.tolist(),'cost':float(fit.cost),
            'optimizer_success':bool(fit.success),'message':str(fit.message),
            'evaluations':int(fit.nfev)})
    if not outcomes:
        raise ValueError('At least one initial parameter set required')
    return outcomes


def assess(protocol, metrics, data_scope):
    rows = {}
    for name,spec in protocol['thresholds'].items():
        value = metrics.get(name)
        passed = value is not None and np.isfinite(value) and value <= spec['maximum']
        rows[name] = {'value':value,'maximum':spec['maximum'],'unit':spec['unit'],'passed':bool(passed)}
    return {'metrics':rows,'thresholds_pass':all(r['passed'] for r in rows.values()),
        'biological_acceptance':False,
        'scope_matches':data_scope==protocol['scope'],
        'note':'Numeric tolerance checks alone do not certify anatomy, independent data or biological validity'}
