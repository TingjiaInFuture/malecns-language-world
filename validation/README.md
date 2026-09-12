# Validation scope: neural-only actuation v1

Production uses the complete official structural graph: 88,384,522 endpoints,
151,856,684 edges, 311,833,243 summed structural counts, zero additional excluded
rows. See `graph_audit.json` for graph hashes and `DATA_PROVENANCE.md` for sources.

- `controller-tests.txt`: 18 local tests, comprising 10 new neural-control tests
  and 8 explicitly historical MBON regression tests. New tests cover zero-output
  clamping under hunger/rain/resource contact, separate motor stimulation,
  mouth/pump gating, local anonymous signals, absence of semantic/planning entry
  points, exact restart, collision without steering, and no random exploration.
  These mechanism tests deliberately use a small graph fixture or clamped outputs;
  they are not full-graph biological experiments.
- `full-acceptance.json`: actual complete-graph numerical checks for all twelve
  individuals, independent reference multiplication, exact neural-state resume,
  two-step sensory ablation for each fly, and 16 unassisted world steps (4 model
  seconds). Diagnostic neural calls are restored before the closed loop resumes;
  they do not advance world time. The report includes tested implementation hashes.
- `neural-trajectory.json`: per-fly positions, traveled distance, all eight neural
  motor outputs and both signal amplitudes for world steps 3 through 16. No target
  planner, random exploration, semantic hints or rescue action is active.
- `gui.json` and `gui-initial.png`: actual Chrome verification and screenshot of
  the full-mode observer. Text commands are disabled and neural amplitudes shown.
- `live-init.json`: Python exact comparison of the running simulation and the
  committed clean initial checkpoint, including integer RNG states.
- `small-model-tests.txt`: historical evidence only; its old hybrid-controller
  survival/navigation behavior does not describe the new production controller.

Twelve complete float32 neural states occupy 4,242,457,056 bytes. All graph edges
are included in each individual's recurrence; the 97 displayed nodes are probes.
Actual timing is reported in the JSON artifacts, separately from rendering FPS.

This acceptance establishes the software's neural-only active-control boundary
and short numerical correctness. It does not establish biological equivalence,
long-term survival, effective navigation, learned communication or language.
The 88,228,690 unknown/modulatory nodes assigned positive propagation, unvalidated
MBON sensory/motor mapping, rate-model dynamics and simplified body remain major
limitations. Small biased motion is an experimental result, not evidence of a
realistic fly policy. See `NEURAL_CONTROL.md` for the complete model contract.

The accepted clean run lasted 4 model seconds. All twelve individuals remained
alive during that short interval; traveled distances ranged from 0.089123 to 0.188763
model units. This weak movement does not establish purposeful navigation or
feeding. Closed-loop steps 3-16 took 10.55-15.58 wall seconds each on this machine.
