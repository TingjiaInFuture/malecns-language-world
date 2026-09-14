"""Per-class MN anatomy summary from the Azevedo confocal workbook (Fig 3A source).

Requires the publisher-hash-verified workbook in data/physiology_raw/motor/
(fetched by experiments.public_data.motor_selected_assets). Sheet2 layout:
value rows 0/2/4 are slow/intermediate/fast; rows 1/3/5 carry the sample
counts. Units are micrometers.
Run: python -m experiments.mn_anatomy
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

WORKBOOK = Path('data/physiology_raw/motor/MN_anatomy_confocal_measurements.xlsx')
ROWS = [(0, 1, 'slow'), (2, 3, 'intermediate'), (4, 5, 'fast')]


def summarize(sheet):
    classes = []
    for value_row, count_row, label in ROWS:
        classes.append({'class': label,
                        'soma_diameter_um_mean': float(sheet.iloc[value_row, 1]),
                        'soma_sd': float(sheet.iloc[value_row, 2]),
                        'primary_neurite_um_mean': float(sheet.iloc[value_row, 3]),
                        'primary_neurite_sd': float(sheet.iloc[value_row, 4]),
                        'axon_in_neuropil_um_mean': float(sheet.iloc[value_row, 5]),
                        'axon_in_neuropil_sd': float(sheet.iloc[value_row, 6]),
                        'n_soma': int(sheet.iloc[count_row, 1]),
                        'n_neurite_measurements': int(sheet.iloc[count_row, 3]),
                        'n_axon': int(sheet.iloc[count_row, 5])})
    return classes


def main():
    receipt = WORKBOOK.with_suffix('.xlsx.receipt.json')
    if not WORKBOOK.exists() or not receipt.exists():
        raise FileNotFoundError('Verified workbook missing; run experiments.public_data '
                                '(motor_selected_assets) first')
    if not json.loads(receipt.read_text(encoding='utf-8')).get('publisher_sha256_verified'):
        raise ValueError('Publisher-verified workbook required')
    sheet = pd.ExcelFile(WORKBOOK).parse('Sheet2', header=None)
    report = {'scope': 'per-class MN anatomy from the Azevedo confocal workbook (paper Fig 3A source)',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'source': str(WORKBOOK)+' (Dryad 76hdr7stb, publisher SHA-256 verified)',
        'classes': summarize(sheet), 'units': 'micrometers',
        'ordering': 'soma diameter slow < intermediate < fast (size principle)',
        'biological_acceptance': False}
    Path('validation/mn-anatomy-classes.json').write_text(json.dumps(report, indent=2),
                                                          encoding='utf-8')
    print(json.dumps({c['class']: round(c['soma_diameter_um_mean'], 2) for c in report['classes']}))


if __name__ == '__main__':
    main()
