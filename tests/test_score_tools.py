"""One simulator observation produces one score; comparisons reuse saved evidence."""

from dataclasses import asdict, replace
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from orbital_workflow.bootstrap import use_method_loop
use_method_loop(Path(__file__).resolve().parents[2] / "OpenChia")

from orbital_workflow.artifacts import Artifacts
from orbital_workflow.persistence import PersistenceSettings, measure_persistence
from orbital_workflow.simulation import ModelTerms, SimulationRequest, generate_forcing, integrate
from orbital_workflow.tools import ToolDispatcher


class SimulatorScores(unittest.TestCase):
    def test_one_run_integrates_once_and_saves_the_same_measured_score_it_returns(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = Artifacts(Path(temporary))
            forcing = generate_forcing(store, trial=1, horizon=4 * math.pi)
            request = SimulationRequest(forcing, end=4 * math.pi, terms=ModelTerms(
                modulation=False, rotating=False, forcing=False))
            dispatcher = ToolDispatcher(store)
            with patch("orbital_workflow.tools.integrate", wraps=integrate) as solve, patch(
                    "orbital_workflow.simulation.measure_persistence", wraps=measure_persistence) as measure:
                observation = dispatcher.execute("sim.run", asdict(request))
            self.assertEqual(solve.call_count, 1)
            self.assertEqual(measure.call_count, 1)
            saved = store.json(observation.artifacts[-1])
            score = observation.findings["score"]
            self.assertIsInstance(score, float)
            self.assertTrue(math.isfinite(score))
            self.assertEqual(score, observation.findings["persistence_measurement"]["effective_duration"])
            self.assertEqual(score, saved["summary"]["score"])
            # The first circular revolution is a reference, not scored residence time.
            self.assertAlmostEqual(score, 2 * math.pi, delta=2e-6)
            self.assertLess(score, observation.findings["observed_interval"][1])

    def test_a_short_observation_returns_its_real_zero_score(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = Artifacts(Path(temporary))
            forcing = generate_forcing(store, trial=1, horizon=0.2)
            observation = ToolDispatcher(store).execute("sim.run", asdict(
                SimulationRequest(forcing, end=0.2)))
            self.assertEqual(observation.findings["score"], 0.0)
            self.assertGreater(observation.findings["observed_interval"][1], 0.0)

    def test_comparison_reads_saved_scores_and_arrays_without_integration_or_rescoring(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = Artifacts(Path(temporary))
            forcing = generate_forcing(store, trial=1, horizon=4 * math.pi)
            dispatcher = ToolDispatcher(store)
            circular = SimulationRequest(forcing, end=4 * math.pi, terms=ModelTerms(
                modulation=False, rotating=False, forcing=False))
            left = dispatcher.execute("sim.run", asdict(circular))
            right = dispatcher.execute("sim.run", asdict(replace(circular,
                terms=ModelTerms(central=False, modulation=False, rotating=False, forcing=False))))
            left_ref, right_ref = left.artifacts[-1], right.artifacts[-1]
            original_left = store.json(left_ref)
            original_right = store.json(right_ref)
            with patch("orbital_workflow.tools.integrate", side_effect=AssertionError("new integration")), patch(
                    "orbital_workflow.simulation.measure_persistence", side_effect=AssertionError("rescoring")):
                # A different diagnostic setting must not rewrite historical scores.
                diagnostic = ToolDispatcher(store, PersistenceSettings(position_scale=0.5))
                observation = diagnostic.execute("sim.compare", {"left": left_ref, "right": right_ref})
            result = observation.findings
            self.assertEqual(result["left"]["score"], left.findings["score"])
            self.assertEqual(result["right"]["score"], right.findings["score"])
            self.assertEqual(result["score_difference"], right.findings["score"] - left.findings["score"])
            self.assertLess(result["score_difference"], 0.0)
            self.assertEqual(dict(result["observation_references"]), {"left": left_ref, "right": right_ref})
            left_arrays = store.arrays(original_left["trajectory"])
            right_arrays = store.arrays(original_right["trajectory"])
            common, il, ir = np.intersect1d(left_arrays["times"], right_arrays["times"], return_indices=True)
            expected = np.abs(left_arrays["states"][il] - right_arrays["states"][ir]).max(axis=0)
            self.assertEqual(result["common_time_count"], len(common))
            np.testing.assert_array_equal(result["max_absolute_component_difference"], expected)
            self.assertEqual(store.json(left_ref), original_left)
            self.assertEqual(store.json(right_ref), original_right)
            self.assertIn(left_ref, observation.artifacts)
            self.assertIn(right_ref, observation.artifacts)

    def test_comparison_cannot_create_simulations_from_nested_requests(self):
        with tempfile.TemporaryDirectory() as temporary:
            dispatcher = ToolDispatcher(Artifacts(Path(temporary)))
            with patch("orbital_workflow.tools.integrate", side_effect=AssertionError("new integration")):
                with self.assertRaisesRegex(ValueError, "saved simulation observation references"):
                    dispatcher.execute("sim.compare", {"left": {"vx": 0}, "right": {"vx": 0.1}})


if __name__ == "__main__":
    unittest.main()
