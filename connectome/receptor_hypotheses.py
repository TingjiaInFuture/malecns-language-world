"""Receptor/polarity hypotheses per predicted transmitter. Roadmap product 2.3.

Polarities are literature hypotheses at the receptor-class level, not per-synapse
measurements. 'unclear' transmitters get NO entry: they cannot silently become
excitatory (the conductance core already rejects unspecified reversal
potentials). Glutamate is deliberately dual (cation channel vs GluCl) because
its sign is post-type dependent in Drosophila. Amine transmitters are modulatory
and carry no fixed reversal; they act through the neuromodulation layer.
Run: python -m connectome.receptor_hypotheses
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HYPOTHESES = [
    {'pre_type': 'acetylcholine', 'post_type': 'any', 'transmitter': 'acetylcholine',
     'receptor_class': 'nicotinic ACh receptor (cation)', 'reversal_potential_mv': 0., 'polarity': 'excitatory',
     'probability': 1., 'evidence': 'Fast insect cholinergic excitation; standard insect nAChR cation channel'},
    {'pre_type': 'gaba', 'post_type': 'any', 'transmitter': 'gaba',
     'receptor_class': 'GABA-A/Rdl-like chloride channel', 'reversal_potential_mv': -70., 'polarity': 'inhibitory',
     'probability': 1., 'evidence': 'Insect GABA-A Cl- channel; Dallmann et al. 2025 Nature 647 for Rdl in leg proprioception'},
    {'pre_type': 'glutamate', 'post_type': 'any', 'transmitter': 'glutamate',
     'receptor_class': 'glutamate-gated cation channel', 'reversal_potential_mv': 0., 'polarity': 'excitatory',
     'probability': .5, 'evidence': 'Excitatory at the insect NMJ; post-type dependent, unresolved for CNS targets'},
    {'pre_type': 'glutamate', 'post_type': 'any', 'transmitter': 'glutamate',
     'receptor_class': 'GluCl chloride channel', 'reversal_potential_mv': -70., 'polarity': 'inhibitory',
     'probability': .5, 'evidence': 'Liu & Wilson 2013, PNAS 110:10294 (doi:10.1073/pnas.1220560110): glutamate is inhibitory in the Drosophila olfactory system'},
    {'pre_type': 'histamine', 'post_type': 'any', 'transmitter': 'histamine',
     'receptor_class': 'Ort/HclA histamine-gated chloride channel', 'reversal_potential_mv': -70., 'polarity': 'inhibitory',
     'probability': 1., 'evidence': 'Gengs et al. 2002, JBC 277:42116 (doi:10.1074/jbc.M207133200)'},
    {'pre_type': 'dopamine', 'post_type': 'any', 'transmitter': 'dopamine',
     'receptor_class': 'DopR1/DopR2-like GPCR (modulatory)', 'reversal_potential_mv': None, 'polarity': 'modulatory',
     'probability': 1., 'evidence': 'Handler et al. 2019, Cell 178:60-75; acts via neuromodulation layer, not fast conductance'},
    {'pre_type': 'serotonin', 'post_type': 'any', 'transmitter': 'serotonin',
     'receptor_class': '5-HT7-like GPCR (modulatory)', 'reversal_potential_mv': None, 'polarity': 'modulatory',
     'probability': 1., 'evidence': 'Howard et al. 2019, Curr Biol 29:4218; modulatory'},
    {'pre_type': 'octopamine', 'post_type': 'any', 'transmitter': 'octopamine',
     'receptor_class': 'Oct-beta-like GPCR (modulatory)', 'reversal_potential_mv': None, 'polarity': 'modulatory',
     'probability': 1., 'evidence': 'Creamer et al. 2018, Neuron 100:1460; modulatory'},
]


def main():
    table = pd.DataFrame(HYPOTHESES)
    out = Path('data/graph_neurons/receptor_hypotheses.parquet')
    table.to_parquet(out, index=False)
    nt = pd.read_feather('data/raw/body-neurotransmitters-male-cns-v1.0.feather')
    counts = nt.predicted_nt.value_counts().to_dict()
    unclear = int(counts.get('unclear', 0))
    report = {'scope': 'transmitter-level receptor polarity hypotheses; not per-synapse physiology',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'rows': len(table), 'transmitter_counts_in_source': counts,
        'unclear_policy': 'No hypothesis row for unclear transmitters; the conductance core rejects unspecified reversal, so unclear cannot default to excitation',
        'glutamate_policy': 'Dual hypothesis kept at p=.5/.5 until post-type/expression data resolves the sign per target',
        'amine_policy': 'Dopamine/serotonin/octopamine act through the neuromodulation layer; no fast reversal potential asserted',
        'source_sha256': {'table': hashlib.sha256(out.read_bytes()).hexdigest()},
        'biological_acceptance': False}
    Path('validation/receptor-hypotheses.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'rows': len(table), 'transmitters': sorted(table.transmitter.unique()),
                      'unclear_bodies_excluded': unclear}, indent=2))


if __name__ == '__main__':
    main()
