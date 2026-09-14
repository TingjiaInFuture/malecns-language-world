"""Named causal perturbations assembled from preregisterable protocols.

Activation injects explicit current; silencing clamps membrane voltage;
ablation removes a neuron's contribution for the experiment's duration. These
are experimental interventions on the model, matching the roadmap's causal
control matrix; none of them edits structure or claims biology by itself.
"""
import numpy as np

KINDS = ('activate', 'silence', 'ablate')


class Perturbation:
    def __init__(self, kind, neuron_indices, evidence, duration_ms, amplitude_pa=0., clamp_mv=None):
        if kind not in KINDS:
            raise ValueError('Unknown perturbation ' + str(kind))
        indices = np.asarray(neuron_indices, dtype=np.int64)
        if indices.ndim != 1 or not len(indices) or np.any(indices < 0) or not evidence:
            raise ValueError('Explicit target indices and evidence required')
        if not np.isfinite(duration_ms) or duration_ms <= 0:
            raise ValueError('Positive duration required')
        if kind == 'silence' and (clamp_mv is None or not np.isfinite(clamp_mv)):
            raise ValueError('Silencing requires a clamp voltage')
        if kind == 'activate' and not np.isfinite(amplitude_pa):
            raise ValueError('Activation requires a finite amplitude')
        self.kind, self.neuron_indices, self.evidence = kind, indices, str(evidence)
        self.duration_ms, self.amplitude_pa, self.clamp_mv = float(duration_ms), float(amplitude_pa), clamp_mv

    def current_pa(self, n_neurons):
        current = np.zeros(n_neurons)
        if self.kind == 'activate':
            current[self.neuron_indices] = self.amplitude_pa
        return current

    def targets_silent(self):
        return self.kind in ('silence', 'ablate')
