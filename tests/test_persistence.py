import math
import unittest

import numpy as np

from orbital_workflow.persistence import PersistenceSettings, measure_persistence


def circular_states(times, direction=1, growth=0):
    phase = direction * times
    radius = 1 + growth * times
    return np.column_stack((radius * np.cos(phase), radius * np.sin(phase),
        growth * np.cos(phase) - direction * radius * np.sin(phase),
        growth * np.sin(phase) + direction * radius * np.cos(phase)))


class PersistenceMeasurements(unittest.TestCase):
    def test_recurrence_duration_includes_partial_cycles_and_both_directions(self):
        horizon = 6 * math.pi + math.pi / 2
        times = np.linspace(0, horizon, 15001)
        forward = measure_persistence(times, circular_states(times))
        backward = measure_persistence(times, circular_states(times, direction=-1))
        expected = horizon - 2 * math.pi
        self.assertAlmostEqual(forward["effective_duration"], expected, places=5)
        self.assertAlmostEqual(backward["effective_duration"], expected, places=5)
        self.assertTrue(any(0 < cycle["phase_fraction_observed"] < 1 for cycle in forward["cycles"]))
        self.assertEqual(backward["direction"], -1)
        shorter_times = np.linspace(0, 3 * math.pi, 5001)
        shorter = measure_persistence(shorter_times, circular_states(shorter_times))
        self.assertAlmostEqual(shorter["effective_duration"], math.pi, places=5)

    def test_mismatch_scales_change_credit_continuously_and_nonwinding_is_recorded(self):
        times = np.linspace(0, 6 * math.pi, 12001)
        exact = measure_persistence(times, circular_states(times))
        drifting_states = circular_states(times, growth=0.005)
        drifting = measure_persistence(times, drifting_states)
        looser = measure_persistence(times, drifting_states,
                                    PersistenceSettings(position_scale=0.2, velocity_scale=0.2))
        self.assertLess(drifting["effective_duration"], looser["effective_duration"])
        self.assertLess(looser["effective_duration"], exact["effective_duration"])
        self.assertGreater(drifting["effective_duration"], 0)

        phase = 0.4 * np.sin(times)
        speed = 0.4 * np.cos(times)
        rocking = np.column_stack((np.cos(phase), np.sin(phase),
                                   -speed * np.sin(phase), speed * np.cos(phase)))
        observed = measure_persistence(times, rocking)
        self.assertEqual(observed["effective_duration"], 0)
        self.assertIsNone(observed["mean_similarity"])
        self.assertGreater(observed["reverse_angular_travel_fraction"], 0)
        self.assertTrue(observed["limitations"])


if __name__ == "__main__":
    unittest.main()
