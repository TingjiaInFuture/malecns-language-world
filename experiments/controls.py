"""Explicit causal null models. Rewiring preserves in/out degree, not physiology."""
import numpy as np


def degree_preserving_rewire(pre, post, seed, swaps=None):
    p,q = np.array(pre,dtype=np.int64),np.array(post,dtype=np.int64)
    if p.ndim != 1 or p.shape != q.shape or np.any(p<0) or np.any(q<0):
        raise ValueError('Invalid directed edge arrays')
    occupied = set(zip(p.tolist(),q.tolist()))
    if len(occupied) != len(p):
        raise ValueError('Simple graph required; duplicate edges cannot be rewired')
    target = len(p)*5 if swaps is None else swaps
    if not isinstance(target,int) or target < 0:
        raise ValueError('Nonnegative integer swap budget required')
    rng = np.random.default_rng(seed)
    accepted = 0
    for _ in range(max(1,target*30)):
        if accepted >= target or len(p)<2:
            break
        a,b = rng.choice(len(p),2,replace=False)
        old_a,old_b = (int(p[a]),int(q[a])),(int(p[b]),int(q[b]))
        new_a,new_b = (int(p[a]),int(q[b])),(int(p[b]),int(q[a]))
        if new_a[0] == new_a[1] or new_b[0] == new_b[1] or new_a in occupied or new_b in occupied:
            continue
        occupied.remove(old_a); occupied.remove(old_b)
        occupied.add(new_a); occupied.add(new_b)
        q[a],q[b] = q[b],q[a]
        accepted += 1
    return p,q,{'requested_swaps':target,'accepted_swaps':accepted,
        'changed_edges':int(np.count_nonzero(q!=np.asarray(post))),
        'fully_mixed':False}
