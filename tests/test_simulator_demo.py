"""Finite demo fixtures verify scenario propagation without scientific search."""

from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest.mock import patch

import numpy as np

from orbital_workflow.bootstrap import use_method_loop
use_method_loop(Path(__file__).resolve().parents[2] / "OpenChia")

from orbital_workflow.__main__ import main
from orbital_workflow.artifacts import Artifacts
from orbital_workflow.gravity import GravitySystem
from orbital_workflow.simulation import Trajectory
from orbital_workflow.simulator_demo import plot_trajectories, run_demo


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "scenarios" / "scenario_02" / "study.toml"


class ScenarioDemo(unittest.TestCase):
    def test_cli_passes_complete_selected_configuration_to_demo(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "demo"
            arguments = ["orbital_workflow", "simulator-demo", "--config", str(CONFIG), "--output", str(output)]
            with patch("sys.argv", arguments), patch("orbital_workflow.simulator_demo.run_demo",
                    return_value={"demonstration_only": True}) as demo, redirect_stdout(io.StringIO()) as stdout:
                main()
            demo.assert_called_once_with(output, tomllib.loads(CONFIG.read_text()))
            self.assertTrue(json.loads(stdout.getvalue())["demonstration_only"])
            self.assertFalse(output.exists())

    def test_demo_derives_cases_and_plot_from_one_unchanged_binary_scenario(self):
        configuration = tomllib.loads(CONFIG.read_text())
        configuration["scenario"].update(initial_position=[1.3, .2], reference_velocity=[.4, 1.1],
                                          radial_limits=[0., 3.5])
        configuration["study"].update(a=.22, sigma=.04, horizon=1.)
        configuration["physics"].update(modulation_frequency=.9, rotating_amplitude=.07, rotating_frequency=.6)
        configuration["forcing"].update(seed=1234, grid_step=.2, ar_decay=.5)
        configuration["numerics"].update(max_step=.04, sample_step=.06, rtol=1e-6, atol=1e-8)
        configuration["persistence"].update(position_scale=.2, velocity_scale=.3, relative_period_scale=.4, phase_samples=16)
        original = deepcopy(configuration)
        requests = []

        def fixture_integration(request, store):
            # Explicit software states, not a numerical solution or evidence
            # about the physical binary. The real recording/measurement/plot
            # consumers still process the returned finite fixture normally.
            requests.append(request)
            states = np.array([request.initial_state, request.initial_state], dtype=float)
            return Trajectory(request, np.array([request.start, request.end]), states,
                              "horizon_reached", "software fixture; integration not executed", 0)

        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "demo"
            with patch("orbital_workflow.tools.integrate", side_effect=fixture_integration) as integrate, patch(
                    "orbital_workflow.simulator_demo.plot_trajectories", wraps=plot_trajectories) as plot, patch(
                    "matplotlib.pyplot.close", wraps=plt.close) as close:
                result = run_demo(directory, configuration)
            self.assertEqual(configuration, original)
            self.assertEqual(integrate.call_count, 3)
            self.assertTrue(result["demonstration_only"])
            self.assertIsNone(result["scientific_credit"])
            self.assertEqual(result["scenario_id"], "scenario_02")
            self.assertEqual(len(result["saved_observation_comparisons"]), 2)
            problem = json.loads((directory / "scenario.json").read_text())
            self.assertEqual(plot.call_args.args[3], problem)
            self.assertTrue((directory / "trajectories.png").is_file())
            self.assertGreater((directory / "trajectories.png").stat().st_size, 0)
            self.assertEqual(len({request.forcing_id for request in requests}), 1)
            store = Artifacts(directory / "artifacts")
            self.assertEqual(int(store.arrays(result["forcing"])["seed"]), 1234)
            for request in requests:
                self.assertEqual(request.scenario_id, "scenario_02")
                self.assertEqual(request.gravity, GravitySystem.from_record(configuration["scenario"]["gravity"]))
                self.assertEqual(request.initial_state, (1.3, .2, .4, 1.1))
                self.assertEqual((request.start, request.end, request.observation_window), (0., 1., (0., 1.)))
                self.assertEqual(request.radial_limits, (0., 3.5))
                self.assertEqual((request.a, request.sigma), (.22, .04))
                self.assertEqual((request.modulation_frequency, request.rotating_amplitude, request.rotating_frequency), (.9, .07, .6))
                self.assertEqual((request.forcing_seed, request.forcing_grid_step, request.forcing_ar_decay), (1234, .2, .5))
            reduced, base, refined = requests
            self.assertTrue(reduced.terms.central)
            self.assertFalse(reduced.terms.modulation or reduced.terms.rotating or reduced.terms.forcing)
            self.assertEqual(reduced.experiment.operations, ("term_mask",))
            self.assertEqual(base.experiment.kind, "base")
            self.assertTrue(base.terms.central and base.terms.modulation and base.terms.rotating and base.terms.forcing)
            self.assertEqual((base.max_step, base.sample_step), (.04, .06))
            self.assertEqual((refined.max_step, refined.sample_step), (.02, .03))
            self.assertEqual((refined.rtol, refined.atol), (base.rtol, base.atol))
            self.assertEqual(refined.experiment.operations, ("refinement",))
            for label, files in result["public_requests"].items():
                public = json.loads((directory / files["file"]).read_text())
                self.assertEqual(public["tool"], "sim.run")
                self.assertEqual(set(public["arguments"]), {"vx", "vy", "experiment"} if files["parts"] else {"vx", "vy"})
                self.assertNotIn("forcing_id", public["arguments"])
                saved = json.loads((directory / files["resolved_file"]).read_text())
                self.assertEqual(saved["arguments"]["gravity"], problem["gravity"])
                observation_file = files["file"].replace("-request.json", "-observation.json")
                observation = json.loads((directory / observation_file).read_text())
                self.assertEqual(observation["findings"]["persistence_measurement"]["settings"], configuration["persistence"])

            figure = next(call.args[0] for call in reversed(close.call_args_list)
                          if call.args and hasattr(call.args[0], "axes"))
            positions = figure.axes[0]
            insertion = next(artist for artist in positions.collections if artist.get_label() == "insertion")
            np.testing.assert_array_equal(insertion.get_offsets(), [[1.3, .2]])
            self.assertIn(3.5, [circle.radius for circle in positions.patches])
            for source in GravitySystem.from_record(problem["gravity"]).sources(0.):
                marker = next(line for line in positions.lines if line.get_label().startswith(source["id"] + ","))
                np.testing.assert_array_equal([marker.get_xdata()[0], marker.get_ydata()[0]], source["position"])


if __name__ == "__main__":
    unittest.main()
