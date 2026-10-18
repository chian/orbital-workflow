"""Continuous recurrence measurements for orbital winding cycles.

Successive revolutions are aligned by their first arrival at equal orbital
angles. Partial revolutions use the available overlap with the preceding one.
The first revolution is a reference, not evidence of recurrence. Backtracking
is measured separately; this winding-based definition does not detect libration
cycles that never complete a revolution.
"""

from dataclasses import asdict, dataclass
import math

import numpy as np


@dataclass(frozen=True)
class PersistenceSettings:
    position_scale: float = 0.1
    velocity_scale: float = 0.1
    relative_period_scale: float = 0.1
    phase_samples: int = 128

    def __post_init__(self):
        if any(not math.isfinite(value) or value <= 0 for value in (
                self.position_scale, self.velocity_scale, self.relative_period_scale)):
            raise ValueError("Persistence scales must be positive and finite")
        if type(self.phase_samples) is not int or self.phase_samples < 2:
            raise ValueError("Phase sampling requires at least two points")


def _at_phases(targets, phase, times, states):
    """Interpolate each target on its first forward crossing in recorded data."""
    targets = np.minimum(targets, np.max(phase))
    target_index = 0
    crossing_times = np.empty(len(targets))
    crossing_states = np.empty((len(targets), 4))
    if targets[0] == 0:
        crossing_times[0], crossing_states[0] = times[0], states[0]
        target_index = 1
    for index in range(1, len(phase)):
        while (target_index < len(targets) and phase[index] >= targets[target_index]
               and phase[index - 1] < targets[target_index]):
            fraction = ((targets[target_index] - phase[index - 1])
                        / (phase[index] - phase[index - 1]))
            crossing_times[target_index] = times[index - 1] + fraction * (times[index] - times[index - 1])
            crossing_states[target_index] = states[index - 1] + fraction * (states[index] - states[index - 1])
            target_index += 1
        if target_index == len(targets):
            return crossing_times, crossing_states
    if target_index != len(targets):
        raise ValueError("Requested phase was not reached by the recorded trajectory")
    return crossing_times, crossing_states


def measure_persistence(times, states, settings: PersistenceSettings | None = None):
    settings = settings or PersistenceSettings()
    times, states = np.asarray(times), np.asarray(states)
    if times.ndim != 1 or states.shape != (len(times), 4) or not len(times):
        raise ValueError("Persistence requires matching times and x,y,vx,vy states")
    if not np.all(np.isfinite(times)) or not np.all(np.isfinite(states)):
        raise ValueError("Persistence observations must be finite")
    if np.any(np.diff(times) <= 0):
        raise ValueError("Observation times must increase")

    raw_phase = np.unwrap(np.arctan2(states[:, 1], states[:, 0]))
    initial_rotation = states[0, 0] * states[0, 3] - states[0, 1] * states[0, 2]
    if initial_rotation == 0:
        changes = np.diff(raw_phase)
        nonzero = changes[changes != 0]
        initial_rotation = nonzero[0] if len(nonzero) else 0
    direction = -1 if initial_rotation < 0 else 1
    phase = direction * (raw_phase - raw_phase[0])
    increments = np.diff(phase)
    angular_travel = float(np.sum(np.abs(increments)))
    reverse_fraction = float(np.sum(np.maximum(-increments, 0)) / angular_travel) if angular_travel else 0.0
    peak = float(np.max(phase))
    turn = 2 * math.pi
    revolutions = peak / turn
    complete = int(math.floor(revolutions))
    cycles = []
    effective_duration = 0.0
    comparable_duration = 0.0

    # A zero-width phase overlap carries no recurrence duration. This is a
    # measurement definition, not an acceptance threshold on observations.
    for cycle in range(1, complete + 1):
        fraction = min(1.0, max(0.0, revolutions - cycle))
        if fraction == 0:
            continue
        overlap = np.linspace(0, fraction, settings.phase_samples)
        prior_times, prior_states = _at_phases((cycle - 1 + overlap) * turn, phase, times, states)
        current_times, current_states = _at_phases((cycle + overlap) * turn, phase, times, states)
        duration = float(current_times[-1] - current_times[0])
        prior_overlap_duration = float(prior_times[-1] - prior_times[0])
        if duration == 0 or prior_overlap_duration == 0:
            continue
        position_mismatch = float(np.mean(((current_states[:, :2] - prior_states[:, :2])
                                           / settings.position_scale) ** 2))
        velocity_mismatch = float(np.mean(((current_states[:, 2:] - prior_states[:, 2:])
                                           / settings.velocity_scale) ** 2))
        period_mismatch = ((duration / prior_overlap_duration - 1)
                           / settings.relative_period_scale) ** 2
        mismatch_squared = position_mismatch + velocity_mismatch + period_mismatch
        similarity = math.exp(-mismatch_squared)
        effective_duration += duration * similarity
        comparable_duration += duration
        cycles.append({
            "revolution": cycle + 1, "phase_fraction_observed": fraction,
            "interval": [float(current_times[0]), float(current_times[-1])],
            "duration": duration, "reference_overlap_duration": prior_overlap_duration,
            "position_mismatch_squared": position_mismatch,
            "velocity_mismatch_squared": velocity_mismatch,
            "period_mismatch_squared": period_mismatch,
            "mismatch_squared": mismatch_squared, "similarity": similarity,
            "effective_duration": duration * similarity,
        })
    reference_duration = None
    if complete:
        reference_times, _ = _at_phases(np.array([0.0, turn]), phase, times, states)
        reference_duration = float(reference_times[-1] - reference_times[0])
    return {
        "definition": "first-passage angular-phase recurrence, duration weighted",
        "settings": asdict(settings), "direction": direction,
        "complete_revolutions": complete, "maximum_winding_revolutions": revolutions,
        "reference_duration": reference_duration,
        "comparable_duration": comparable_duration,
        "effective_duration": effective_duration,
        "mean_similarity": effective_duration / comparable_duration if comparable_duration else None,
        "reverse_angular_travel_fraction": reverse_fraction,
        "maximum_observation_gap": float(np.max(np.diff(times))) if len(times) > 1 else 0.0,
        "cycles": cycles,
        "limitations": [
            "First revolution supplies the recurrence reference",
            "Angular winding does not measure non-winding libration cycles",
            "First-passage phase alignment uses interpolation of saved states",
            "Interrupted stretches can both contribute to the duration sum",
            "Finite-time recurrence does not establish indefinite stability",
        ],
    }
