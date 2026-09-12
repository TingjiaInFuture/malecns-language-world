# Validation scope

- `graph_audit.json`: complete official segment graph, 88,384,522 endpoints,
  151,856,684 edges, 311,833,243 summed structural counts, zero excluded rows.
- `full-acceptance.json`: 9 full-graph checks. Twelve individuals performed two
  actual world steps, followed by independent-reference and exact restoration
  checks of neural updates. This is a short correctness test, not a long-running
  biological or language experiment.
- The measured world steps took **17.86 and 22.74 seconds** on the local machine
  under the acceptance workload. Earlier warm measurements were around 11 seconds.
  Each step advances only 0.25 model seconds. Rendering FPS is a separate metric.
- Twelve complete float32 states occupy **4,242,457,056 bytes** in temporary
  memory-mapped storage. Checkpoint compression and restoration also take time.
- `gui.json` and `gui-initial.png`: 12 actual Chrome checks of the full-mode
  observation window, including clean init, disabled structural-weight mutation,
  real graph scope, twelve bodies, selection, camera, export, and local-only loads.
- `live-init.json`: Python verified exact production/init equality, preserving
  integer RNG states without JavaScript numeric rounding.
- `small-model-tests.txt`: 8 fast regression tests, deliberately using the legacy
  MBON fixture. Their 10-model-day test is **not** a full-graph endurance test.

The matrix is built from all published structural counts, with an explicit
normalization and sign model. **88,228,690 segment nodes** do not have one of the
model's supported fast-transmitter consensus labels and receive the documented
positive structural-propagation assumption. Many are fragments. This is a major
limitation, not evidence that those segments are biologically excitatory.

No physiological equivalence, exclusive neural control, learned natural language,
or survival advantage has been established. The engineering navigation/need and
symbolic protocol components are retained explicitly.
