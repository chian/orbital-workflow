"""Fixed scenario ownership and explicit experiments; no model/provider calls."""

from contextlib import redirect_stdout
from dataclasses import replace
import io
import json
import math
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest.mock import patch

import numpy as np

from orbital_workflow.bootstrap import use_method_loop
use_method_loop(Path(__file__).resolve().parents[2] / "OpenChia")

from orbital_workflow.artifacts import Artifacts
from orbital_workflow.failures import ActionRequestError
from orbital_workflow.records import Observation, plain
from orbital_workflow.replay import private_replay_arguments
from orbital_workflow.scenario import ScenarioSimulator, is_base_observation
from orbital_workflow.simulation import SimulationRequest, integrate
from orbital_workflow.tools import ToolDispatcher


ROOT = Path(__file__).resolve().parents[1]


class ScenarioOwnership(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.store = Artifacts(self.directory / "objects")
        self.settings = tomllib.loads((ROOT / "scenarios/scenario_02/study.toml").read_text())

    def test_immutable_definition_and_one_lazy_forcing_realization(self):
        from orbital_workflow import scenario
        with patch("orbital_workflow.scenario.generate_forcing", wraps=scenario.generate_forcing) as generate:
            simulator = ScenarioSimulator(self.settings, self.store)
            self.assertEqual(generate.call_count, 0)
            with self.assertRaises(TypeError):
                simulator.problem["forcing"]["seed"] = 9
            with self.assertRaises(AttributeError):
                simulator.problem = {}
            self.settings["study"]["a"] = 999
            self.settings["forcing"]["seed"] = 9
            first = simulator.resolve_run({"vx": 0, "vy": 1})
            second = simulator.resolve_run({"vx": .2, "vy": -1.2})
            self.assertEqual(generate.call_count, 1)
            self.assertEqual(first["forcing_id"], second["forcing_id"])
            self.assertEqual(first["forcing_seed"], 20261006)
            self.assertEqual(first["a"], .15)
            first["a"] = 42
            self.assertEqual(simulator.resolve_run({"vx": 0, "vy": 1})["a"], .15)
            self.assertEqual(simulator.describe()["ship_fields"], ["vx", "vy"])

    def test_ordinary_runs_require_only_two_explicit_finite_velocities(self):
        simulator = ScenarioSimulator(self.settings, self.store)
        cases = [{}, {"vx": 0}, {"vy": 1}, {"vx": True, "vy": 1}, {"vx": "1+2", "vy": 1},
                 {"vx": math.nan, "vy": 1}]
        for key in ("a", "sigma", "trial", "seed", "forcing_id", "gravity", "initial_state", "start", "end",
                    "observation_window", "terms", "active_bodies", "radial_limits", "method", "rtol", "sample_step", "experiment"):
            cases.append({"vx": 0, "vy": 1, key: 999})
        with patch("orbital_workflow.scenario.generate_forcing", side_effect=AssertionError("Invalid proposals do not allocate forcing")):
            for arguments in cases:
                with self.subTest(arguments=arguments), self.assertRaises(ActionRequestError):
                    simulator.resolve_run(arguments)

    def test_explicit_parts_parameters_are_derivations_without_a_preset_catalog(self):
        simulator = ScenarioSimulator(self.settings, self.store)
        base = simulator.resolve_run({"vx": .13, "vy": -1.17})
        derived = simulator.resolve_run({"vx": .13, "vy": -1.17, "experiment": {
            "terms": {"modulation": False, "forcing": False}, "active_bodies": ["body_2"],
            "gravity_mode": "monopole", "spatial_box": [-2.17, 3.91, -1.37, 2.09],
            "radial_limits": [.07, 3.83], "interval": [.137, 3.141],
            "refinement": {"max_step": .037, "sample_step": .013, "rtol": 9e-8, "atol": 1.23e-10}}}, parts=True)
        for field in ("forcing_id", "forcing_seed", "gravity", "a", "sigma", "modulation_frequency", "rotating_amplitude", "rotating_frequency"):
            self.assertEqual(derived[field], base[field])
        self.assertEqual(derived["start"], .137)
        self.assertEqual(derived["end"], 3.141)
        self.assertEqual(derived["max_step"], .037)
        self.assertEqual(derived["experiment"]["kind"], "derived")
        self.assertIn("term_mask", derived["experiment"]["operations"])
        self.assertFalse(is_base_observation(derived, simulator.problem))
        self.assertEqual(simulator.resolve_run({"vx": .13, "vy": -1.17}), base)
        for experiment in ({"a": .3}, {"seed": 42}, {"terms": {"forcing": "false"}},
                           {"active_bodies": ["unknown"]}, {"interval": [0, 999]},
                           {"spatial_box": [1, -1, 0, 2]}, {"refinement": {"rtol": 0}}):
            with self.subTest(experiment=experiment), self.assertRaises(ActionRequestError):
                simulator.resolve_run({"vx": 0, "vy": 1, "experiment": experiment}, parts=True)

    def test_base_scope_predicate_is_pure_and_full_interval_refinements_remain_base(self):
        simulator = ScenarioSimulator(self.settings, self.store)
        base = simulator.resolve_run({"vx": .1, "vy": -1.2})
        refined = simulator.resolve_run({"vx": .1, "vy": -1.2, "experiment": {
            "refinement": {"max_step": .017, "sample_step": .011}}}, parts=True)
        with patch("orbital_workflow.scenario.generate_forcing", side_effect=AssertionError("A predicate cannot generate evidence")):
            self.assertTrue(is_base_observation(base, simulator.problem))
            self.assertTrue(is_base_observation(refined, simulator.problem))
            canonical = plain(base)
            canonical.pop("forcing_id")
            self.assertTrue(is_base_observation(canonical, simulator.problem, forcing_seed="20261006"))
            for field, value in (("forcing_seed", 20261007), ("a", .3), ("sigma", .08),
                    ("end", 45.), ("observation_window", [0, 45]), ("rotating_frequency", .41),
                    ("initial_state", [2, 0, .1, -1.2]), ("spatial_box", [-2, 2, -2, 2])):
                changed = {**base, field: value}
                self.assertFalse(is_base_observation(changed, simulator.problem), field)
            missing = dict(base)
            missing.pop("end")
            self.assertFalse(is_base_observation(missing, simulator.problem))

    def test_forcing_keeps_the_original_reference_recipe_exactly(self):
        simulator = ScenarioSimulator(self.settings, self.store)
        arguments = simulator.resolve_run({"vx": 0, "vy": 1})
        saved = self.store.arrays(arguments["forcing_id"])
        times = .1 * np.arange(math.ceil(125.66370614359172 / .1) + 1, dtype=np.float64)
        gaussian = np.random.Generator(np.random.PCG64DXSM(20261006)).standard_normal((len(times), 2), dtype=np.float64)
        expected = np.empty_like(gaussian)
        expected[0] = gaussian[0]
        rho = math.exp(-.2)
        for index in range(1, len(times)):
            expected[index] = rho * expected[index - 1] + math.sqrt(1 - rho * rho) * gaussian[index]
        np.testing.assert_array_equal(saved["times"], times)
        np.testing.assert_array_equal(saved["eta"], expected)

    def test_original_equations_and_default_private_trajectory_are_preserved(self):
        from orbital_workflow import simulation
        single = tomllib.loads((ROOT / "scenarios/scenario_01/study.toml").read_text())
        simulator = ScenarioSimulator(single, self.store)
        arguments = simulator.resolve_run({"vx": 0, "vy": 1})
        request = SimulationRequest.from_record(arguments)
        forcing = self.store.arrays(request.forcing_id)
        original_solver = simulation.solve_ivp
        checked = []

        def check_equation(rhs, interval, state, **kwargs):
            if not checked:
                time = .137
                x, y, vx, vy = 1.1, .2, -.3, .8
                factor = -(1 + .15 * math.sin(.7 * time)) / math.hypot(x, y) ** 3
                c, d = math.cos(.4 * time), math.sin(.4 * time)
                ax = factor * x + .02 * (c * x + d * y) + .03 * np.interp(time, forcing["times"], forcing["eta"][:, 0])
                ay = factor * y + .02 * (d * x - c * y) + .03 * np.interp(time, forcing["times"], forcing["eta"][:, 1])
                np.testing.assert_array_equal(rhs(time, [x, y, vx, vy]), [vx, vy, ax, ay])
                checked.append(True)
            return original_solver(rhs, interval, state, **kwargs)

        with patch("orbital_workflow.simulation.solve_ivp", side_effect=check_equation):
            bound = integrate(request, self.store)
        original_defaults = integrate(SimulationRequest(request.forcing_id), self.store)
        self.assertTrue(checked)
        np.testing.assert_array_equal(bound.times, original_defaults.times)
        np.testing.assert_array_equal(bound.states, original_defaults.states)
        self.assertEqual(bound.summary()["score"], original_defaults.summary()["score"])

    def test_continuation_uses_saved_terminal_state_and_preserves_absolute_forcing(self):
        simulator = ScenarioSimulator(self.settings, self.store)
        split = .1 * 3
        prefix_arguments = simulator.resolve_run({"vx": 0, "vy": 1, "experiment": {"interval": [0, split]}}, parts=True)
        observation = ToolDispatcher(self.store, simulator.persistence_settings).execute("sim.run", prefix_arguments)
        saved = self.store.json(observation.artifacts[-1])
        continued = simulator.resolve_run({"experiment": {"continuation": {"run_index": 1, "end": .8}}},
            parts=True, continuation_lookup=lambda index: saved)
        self.assertEqual(continued["initial_state"], tuple(saved["summary"]["terminal_state"]))
        self.assertEqual(continued["start"], saved["summary"]["observed_interval"][1])
        self.assertEqual(continued["experiment"]["source_observation"], observation.artifacts[-1])
        self.assertEqual(continued["forcing_id"], prefix_arguments["forcing_id"])
        suffix = integrate(SimulationRequest.from_record(continued), self.store)
        whole = integrate(replace(SimulationRequest.from_record(prefix_arguments), end=.8), self.store)
        np.testing.assert_array_equal(suffix.states[-1], whole.states[-1])
        self.assertFalse(is_base_observation(continued, simulator.problem))
        with self.assertRaises(ActionRequestError):
            simulator.resolve_run({"vx": 999, "vy": 999, "experiment": {"continuation": {"run_index": 1, "end": .8}}},
                parts=True, continuation_lookup=lambda index: saved)

    def test_private_replay_requires_complete_executed_specifications(self):
        simulator = ScenarioSimulator(self.settings, self.store)
        saved = simulator.resolve_run({"vx": .1, "vy": -1.2})
        self.assertEqual(private_replay_arguments("sim.run", saved), saved)
        for arguments in ({"vx": .1, "vy": -1.2}, {key: value for key, value in saved.items() if key != "a"}):
            with self.assertRaises(ValueError):
                private_replay_arguments("sim.run", arguments)

    def test_public_cli_uses_the_same_scenario_resolver(self):
        from orbital_workflow.__main__ import main
        path = self.directory / "request.json"
        arguments = {"vx": .123, "vy": -1.234, "experiment": {"interval": [0, .3], "refinement": {"max_step": .017}}}
        path.write_text(json.dumps({"tool": "sim.run", "arguments": arguments}))
        cli = ["orbital_workflow", "tool", "--parts", "--artifacts", str(self.store.directory),
               "--request", str(path), "--config", str(ROOT / "scenarios/scenario_02/study.toml")]
        with patch("sys.argv", cli), patch("orbital_workflow.tools.ToolDispatcher.execute", return_value=Observation("software_fixture", {})) as execute, redirect_stdout(io.StringIO()):
            main()
        expected = ScenarioSimulator(self.settings, self.store).resolve_run(arguments, parts=True)
        self.assertEqual(execute.call_args.args, ("sim.run", expected))
        path.write_text(json.dumps({"tool": "sim.run", "arguments": {"vx": 0, "vy": 1, "sigma": 999}}))
        with patch("sys.argv", cli), patch("orbital_workflow.tools.ToolDispatcher.execute") as execute, self.assertRaises(ActionRequestError):
            main()
        execute.assert_not_called()

    def test_math_reference_queries_share_the_scenario_owner_and_cli_path(self):
        from orbital_workflow.__main__ import main
        from orbital_workflow.scientific import ScientificBindings
        from orbital_workflow.runtime import Kind
        from types import SimpleNamespace
        simulator = ScenarioSimulator(self.settings, self.store)
        query = {"operation": "binary_reference", "time": .137, "position": [1.2, .3]}
        expected = simulator.resolve_numeric(query)
        self.assertEqual(expected["gravity"], plain(simulator.problem["gravity"]))
        self.assertEqual(query, {"operation": "binary_reference", "time": .137, "position": [1.2, .3]})
        binding = ScientificBindings(self.settings, None, ToolDispatcher(self.store))
        action = binding.tool({"tool_name": "math.numeric", "arguments_json": json.dumps(query),
                               "label": "query"}, kind=Kind.MATH, request=SimpleNamespace())
        self.assertEqual(action.arguments, expected)
        path = self.directory / "math-query.json"
        path.write_text(json.dumps({"tool": "math.numeric", "arguments": query}))
        cli = ["orbital_workflow", "tool", "--artifacts", str(self.store.directory),
               "--request", str(path), "--config", str(ROOT / "scenarios/scenario_02/study.toml")]
        with patch("sys.argv", cli), patch("orbital_workflow.tools.ToolDispatcher.execute",
                return_value=Observation("software_fixture", {})) as execute, redirect_stdout(io.StringIO()):
            main()
        self.assertEqual(execute.call_args.args, ("math.numeric", expected))
        for field in ("gravity", "a", "sigma", "trial", "forcing_id"):
            with self.subTest(field=field), self.assertRaises(ActionRequestError) as caught:
                simulator.resolve_numeric({**query, field: 999})
            self.assertEqual(caught.exception.diagnostic,
                {"category": "wrong_parameters", "tool": "math.numeric", "field": field})


if __name__ == "__main__":
    unittest.main()
