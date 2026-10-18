"""Physical forcing coverage and explicit tool observation-window feedback."""

from dataclasses import asdict, replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from orbital_workflow.bootstrap import use_method_loop
use_method_loop(Path(__file__).resolve().parents[2] / "OpenChia")

from orbital_workflow.artifacts import Artifacts
from orbital_workflow.durable import CachedTools
from orbital_workflow.persistence import PersistenceSettings
from orbital_workflow.records import plain
from orbital_workflow.simulation import ModelTerms, SimulationRequest, generate_forcing, integrate
from orbital_workflow.tools import ToolDispatcher


class SimulationObservationScope(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.base = Path(self.directory.name)
        self.store = Artifacts(self.base / "objects")

    def test_standalone_unforced_continuation_beyond_stored_forcing_coverage(self):
        forcing = generate_forcing(self.store, 1, 1)
        request = SimulationRequest(forcing, end=1,
            terms=ModelTerms(modulation=False, rotating=False, forcing=False))
        first = integrate(request, self.store)
        continued = integrate(replace(request, start=1, end=2,
            initial_state=tuple(first.states[-1])), self.store)
        whole = integrate(replace(request, end=2), self.store)
        self.assertIsNone(request.observation_window)
        self.assertEqual(continued.outcome, "horizon_reached")
        self.assertEqual(continued.times[-1], 2)
        np.testing.assert_array_equal(np.concatenate([first.times, continued.times[1:]]), whole.times)
        np.testing.assert_array_equal(np.concatenate([first.states, continued.states[1:]]), whole.states)

    def test_active_forcing_still_requires_complete_coverage(self):
        forcing = generate_forcing(self.store, 1, 1)
        for start, end in [(0, 2), (2, 3)]:
            with self.subTest(start=start, end=end), self.assertRaisesRegex(ValueError, "Stored forcing"):
                integrate(SimulationRequest(forcing, start=start, end=end), self.store)

    def test_unforced_request_preserves_original_knot_segmentation_within_coverage(self):
        forcing = generate_forcing(self.store, 1, 1)
        request = SimulationRequest(forcing, end=.8,
            terms=ModelTerms(modulation=False, rotating=False, forcing=False))
        from orbital_workflow import simulation
        original_solver = simulation.solve_ivp
        spans = []
        def recorded_solver(function, span, state, **kwargs):
            spans.append(span)
            return original_solver(function, span, state, **kwargs)
        with patch.object(simulation, "solve_ivp", side_effect=recorded_solver):
            actual = integrate(request, self.store)
        times = self.store.arrays(forcing)["times"]
        knots = np.concatenate(([request.start], times[(times > request.start) & (times < request.end)], [request.end]))
        self.assertEqual(spans, list(zip(knots[:-1], knots[1:])))
        self.assertEqual(actual.times[-1], .8)
        scoped = integrate(replace(request, observation_window=(0, .8)), self.store)
        np.testing.assert_array_equal(scoped.times, actual.times)
        np.testing.assert_array_equal(scoped.states, actual.states)
        self.assertEqual(scoped.evaluations, actual.evaluations)

    def test_window_is_normalized_validated_and_optional(self):
        request = SimulationRequest.from_record({"forcing_id": "unused", "observation_window": [0, 10]})
        self.assertEqual(request.observation_window, (0., 10.))
        self.assertEqual(asdict(request)["observation_window"], (0., 10.))
        for window in ([0], [1, 0], [1, 1], [0, float("inf")], [False, 1], ["0", 1]):
            with self.subTest(window=window), self.assertRaises(ValueError):
                SimulationRequest("unused", observation_window=window)

    def test_outside_window_is_deterministic_durable_feedback_without_integration_or_score(self):
        tools = CachedTools(self.store, PersistenceSettings(), self.base / "tool-cache")
        request = SimulationRequest("no_array_read_for_request_diagnostic", start=10, end=20,
            terms=ModelTerms(forcing=False), observation_window=(0, 10))
        arguments = asdict(request)
        with patch("orbital_workflow.tools.integrate") as integrate_tool:
            first = tools.execute("sim.run", arguments)
            restored = CachedTools(self.store, PersistenceSettings(), self.base / "tool-cache")
            replay = restored.execute("sim.run", arguments)
        integrate_tool.assert_not_called()
        expected = {"code": "outside_observation_window", "requested_interval": [10., 20.],
                    "observation_window": [0., 10.]}
        self.assertEqual(first.operation, "sim.request_diagnostic")
        self.assertEqual(plain(first.findings), expected)
        self.assertEqual(first.as_record(), replay.as_record())
        self.assertEqual(tools.fresh_calls, 1)
        self.assertEqual(restored.replayed_calls, 1)
        self.assertEqual(len(first.artifacts), 2)
        saved_request, saved_result = map(self.store.json, first.artifacts)
        self.assertEqual(saved_request["tool"], "sim.run")
        self.assertEqual(saved_result, {"operation": "sim.request_diagnostic", "findings": expected})
        self.assertNotIn("score", saved_result)
        self.assertFalse(list(self.store.directory.glob("*.npz")))

    def test_both_window_edges_are_checked_and_endpoints_are_inclusive(self):
        tools = ToolDispatcher(self.store)
        for start, end in [(0, 2), (1, 4)]:
            with self.subTest(start=start, end=end), patch("orbital_workflow.tools.integrate") as integrate_tool:
                observation = tools.execute("sim.run", asdict(SimulationRequest("unused",
                    start=start, end=end, observation_window=(1, 3))))
                self.assertEqual(observation.operation, "sim.request_diagnostic")
                integrate_tool.assert_not_called()
        forcing = generate_forcing(self.store, 1, 1)
        observation = tools.execute("sim.run", asdict(SimulationRequest(forcing,
            end=1, observation_window=(0, 1))))
        self.assertEqual(observation.operation, "sim.run")
        self.assertEqual(observation.findings["requested_interval"], (0., 1.))

    def test_valid_window_run_returns_actual_recurrence_score_and_saves_window(self):
        forcing = generate_forcing(self.store, 1, 20)
        request = SimulationRequest(forcing, end=20, observation_window=(0, 20),
            terms=ModelTerms(modulation=False, rotating=False, forcing=False))
        tools = ToolDispatcher(self.store)
        observation = tools.execute("sim.run", asdict(request))
        expected = integrate(request, self.store).summary()
        self.assertEqual(observation.operation, "sim.run")
        self.assertGreater(observation.findings["score"], 0)
        self.assertEqual(observation.findings["score"], expected["persistence_measurement"]["effective_duration"])
        saved = self.store.json(observation.artifacts[-1])
        self.assertEqual(saved["request"]["observation_window"], [0., 20.])
        self.assertEqual(saved["summary"]["score"], observation.findings["score"])


if __name__ == "__main__":
    unittest.main()
