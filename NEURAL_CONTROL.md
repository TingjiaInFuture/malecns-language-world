# Neural actuation contract v1

Historical engineering sandbox only. The physiological reference in
`physiology/reference.py` is separate and has not been validated against animal
recordings. `FullBrains.forward` now uses alpha=1-exp(-dt/tau), with the explicitly
engineering tau=0.25/log(2) seconds. Thus the old recurrence below holds only at
dt=0.25 s; dt=0 is a no-op and negative/nonfinite dt is rejected. Existing report
hashes describe the prior source and are not current-code acceptance evidence.

## Causal boundary

`ecology.Habitat.step` samples all individuals before updating any body, calls the
neural core once, then passes only each individual's eight readouts into
`actuate`. It does not call any planner, behavioral policy, random generator,
semantic interpreter or learned external controller. `environment.py` contains
world initialization, climate, environmental interventions and persistence;
`legacy_ecology.py` is used only for old regression tests.

Sensors are 24 scalar channels listed in `ecology.SENSORS`. Two spatially separated
receptors sample odor, humidity and two anonymous emitted signal fields. Internal
energy, hydration, fatigue, contact, wind and velocity provide body feedback.
Resource identities, labels, goal coordinates and optimal actions are absent.
Field shapes and sensory scaling are artificial, not measured receptor physics.

The unchanged full recurrence is h' = 0.5 h + 0.5 tanh(W h + I x).
W[post,pre] = 1.5 sign(pre) count(post,pre) / sum_pre count(post,pre).
Readout is tanh(3 O h'). I/O maps are fixed, seeded and disjoint on 97 MBON probes;
no direct sensory-to-motor skip path exists. These ports are not anatomically
validated. All published edges participate in every individual's matrix update;
no claim is made that every edge causally influences the eight ports.

## Body transduction

Positive rectified neural readouts actuate left/right propulsion, lift, mouth
extension, pumping, signal A/B and braking. Constants are fixed model units:
turn rate 3*(right-left), thrust 4*(left+right), drag 2+4*brake+exposed_rain,
vertical acceleration 12*lift-3. Integration uses dt=0.25 and passive damping.
Rain increases passive drag and metabolic loss outside shelter. These are not calibrated muscle forces or flight dynamics. No output offset,
automatic gain adaptation or random motor noise forces activity when outputs are
small. Zero outputs from a stationary grounded body leave horizontal position,
heading and signal unchanged, and cannot consume nearby resources. Passive
inertia/gravity/contact can still move a body after actuation ceases.

Contact solids stop penetration without adjusting heading. Mouth extension times
pumping determines ingestion only at a resource surface. Metabolic depletion,
fatigue recovery and death are body processes, never action selectors. Physical
parameters, sensor maps and dynamical equations necessarily remain engineering
assumptions; this version removes engineered behavioral decisions, not all models.

Signals are continuous amplitudes, not tokens; reception uses prior-step signals
and distance attenuation. There are no invented dialogues, scheduling rules,
semantic labels or claims of emergent communication. The GUI shows raw amplitudes.
Legacy metric/memory keys remain empty for display/serialization compatibility.

## Acceptance and limits

Small graph mechanism tests clamp the neural output and stimulate individual
actuators, check contact gating, local signals, no semantic control, collision,
exact restart and environmental changes without neural actuation. This isolates
the actuator boundary; it is not an animal experiment or full-graph performance
benchmark. Full acceptance loads the real graph for all twelve individuals,
checks independent recurrence and exact neural continuation, compares sensory
ablation, and records a short unassisted closed loop. Counterfactual calls are
explicitly counted separately from world steps.

Static/circling/starving behavior is a possible negative result. No success claim
for feeding, navigation, survival, language or biological equivalence follows
from architectural or numerical acceptance. Future physiological validation
requires measured sensor/motor correspondence and independent animal data.
