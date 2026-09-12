# Data provenance

Official release: **male-cns:v1.0**. Source and licensing:
https://male-cns.janelia.org/download/ (CC-BY).

Attribution: FlyEM / HHMI Janelia, University of Cambridge (Department of Zoology),
MRC Laboratory of Molecular Biology, and Google Research.

The complete published segment connectivity file is:

`https://storage.googleapis.com/flyem-male-cns/v1.0/connectome-data/flat-connectome/connectome-weights-male-cns-v1.0-minconf-0.5.feather`

SHA-256: `e35da783d1c686b2b58b3b87cd6a403ae43bfcfba8bff28e08ef752c1a56afc1`

Annotation SHA-256: `2177e246113e4cfbf1e7772ec37c6da1955ff22e8063d0b1f833101f99a9a3b2`

Neurotransmitter prediction SHA-256: `95c9289220663abeb3409f3ad9e5a7f8a53f8093f5139d15502cd08da8879621`

All graph endpoints and rows in this release are retained. Isolated bodies absent
from the connection file are not added. The source's minconf-0.5 filtering belongs
to the published release; the builder adds no weight/NT/status filter. Counts use
orientation `C[post, pre]`. The builder never silently combines duplicates.

The bundled `data/graph_mbon` tables are a derived 97-node probe subgraph used to
define artificial ports and render the small neural monitor. These probe tables
are **not** the production recurrence matrix. Their selection and sign hypotheses
are recorded in `selection.json`; full recurrence uses every published row.

See `validation/graph_audit.json` for the generated graph inventory and checksums.
Neurotransmitter signs, normalization, model kinetics, sensory encoding and motor
interfaces are assumptions, not measured physiological synaptic parameters.
