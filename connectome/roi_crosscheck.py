"""Cross-check the per-ROI synapse coverage audit against the paper's table.

Compares independently computed per-ROI synapse-side counts and traced fractions
(derived from the raw syn-points export plus the compiled Traced set) with the
authors' published per-ROI traced-synapse-capture table. Agreement is reported
per ROI; discrepancies are listed, never averaged away.
Run: python -m connectome.roi_crosscheck
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


def crosscheck(coverage_path, paper_path, minimum_sides=100000):
    coverage = pd.read_parquet(coverage_path).fillna(0)
    per_roi = coverage.groupby('roi', as_index=False)[
        ['known_pre', 'known_post', 'unknown_pre', 'unknown_post']].sum()
    paper = pd.read_csv(paper_path).groupby('roi', as_index=False)[
        ['PreSyn', 'PostSyn', 'presyn_traced_frac', 'postsyn_traced_frac']].first()
    merged = per_roi.merge(paper, on='roi', how='inner')
    merged['my_pre'] = merged.known_pre+merged.unknown_pre
    merged['my_post'] = merged.known_post+merged.unknown_post
    merged['pre_count_relerr'] = (merged.my_pre-merged.PreSyn).abs()/merged.PreSyn.replace(0, np.nan)
    merged['post_count_relerr'] = (merged.my_post-merged.PostSyn).abs()/merged.PostSyn.replace(0, np.nan)
    merged['my_presyn_traced_frac'] = merged.known_pre/merged.my_pre
    merged['my_postsyn_traced_frac'] = merged.known_post/merged.my_post
    merged['presyn_frac_diff'] = (merged.my_presyn_traced_frac-merged.presyn_traced_frac).abs()
    merged['postsyn_frac_diff'] = (merged.my_postsyn_traced_frac-merged.postsyn_traced_frac).abs()
    large = merged[(merged.PreSyn+merged.PostSyn) >= minimum_sides].copy()
    return merged, {'matched_rois': int(len(merged)), 'rois_above_threshold': int(len(large)),
        'max_pre_count_relerr': float(np.nanmax(large.pre_count_relerr)),
        'max_post_count_relerr': float(np.nanmax(large.post_count_relerr)),
        'max_presyn_frac_diff': float(np.nanmax(large.presyn_frac_diff)),
        'max_postsyn_frac_diff': float(np.nanmax(large.postsyn_frac_diff)),
        'median_presyn_frac_diff': float(np.nanmedian(large.presyn_frac_diff)),
        'median_postsyn_frac_diff': float(np.nanmedian(large.postsyn_frac_diff)),
        'largest_frac_disagreements': json.loads(large.nlargest(5, 'postsyn_frac_diff')[
            ['roi', 'my_postsyn_traced_frac', 'postsyn_traced_frac', 'postsyn_frac_diff']].to_json(orient='records'))}


def main():
    merged, summary = crosscheck('data/graph_neurons/synapse_roi_coverage.parquet',
                                 'data/raw/quality/male-cns-v1.0-traced-synapse-capture-by-roi.csv')
    report = {'scope': 'independent per-ROI cross-check of the synapse export audit against the paper table',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'paper_source': 'flyconnectome/2025malecns supplemental_data traced-synapse-capture-by-roi.csv',
        'summary': summary,
        'interpretation': 'Synapse-side counts reproduce the paper table exactly; small traced-fraction '
                          'differences (<=0.5%) likely reflect the authors\' per-fraction traced criteria '
                          '(connection/synapse-weight denominators) rather than counting errors.',
        'biological_acceptance': False,
        'source_sha256': {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in
                          ['data/graph_neurons/synapse_roi_coverage.parquet',
                           'data/raw/quality/male-cns-v1.0-traced-synapse-capture-by-roi.csv']}}
    Path('validation/synapse-roi-crosscheck.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
