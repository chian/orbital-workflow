"""Human reporting uses the same fixed scenario and exports every measurement."""

import copy
import csv
import json
from pathlib import Path
import tempfile
import unittest

from orbital_workflow.bootstrap import use_method_loop
use_method_loop(Path(__file__).resolve().parents[2] / "OpenChia")

from orbital_workflow.artifacts import Artifacts
from orbital_workflow.credit import project_observation, trajectory_evidence
from orbital_workflow.reporting import all_observations, full_scope, select_observations, write_observations_csv
from orbital_workflow.scenario import ScenarioSimulator
from orbital_workflow.scientific import ScientificBindings, load_settings
from orbital_workflow.tools import ToolDispatcher


class ReportScope(unittest.TestCase):
    def test_complete_target_labels_match_root_for_fixed_scenario_and_derived_work(self):
        project = Path(__file__).resolve().parents[1]
        settings = load_settings(project / "scenarios/scenario_02/study.toml")
        with tempfile.TemporaryDirectory() as temporary:
            store = Artifacts(Path(temporary))
            simulator = ScenarioSimulator(settings, store)
            binding = ScientificBindings(settings, None, None)
            base = simulator.resolve_run({"vx": .1, "vy": -1.2})
            cases = [("complete", {}, True),
                ("different amplitude", {"sigma": 0}, False),
                ("different forcing", {"forcing_seed": 20261007}, False),
                ("different modulation frequency", {"modulation_frequency": .8}, False),
                ("different scenario", {"scenario_id": "another_scenario"}, False),
                ("monopole", {"gravity_mode": "monopole"}, False),
                ("one source", {"active_bodies": ["body_1"]}, False),
                ("shortened requested interval", {"end": 45}, False),
                ("missing observation window", {"observation_window": None}, False),
                ("different observation window", {"observation_window": [0, 200]}, False),
                ("continuation", {"start": 1}, False),
                ("spatial observation", {"spatial_box": [-1, 1, -1, 1]}, False),
                ("different position", {"initial_state": [2, 0, .1, -1.2]}, False),
                ("different radial domain", {"radial_limits": [0, 3]}, False),
                ("omitted forcing", {"terms": {**base["terms"], "forcing": False}}, False),
                ("numerical refinement", {"rtol": 1e-10, "max_step": .01}, True)]
            for name, changes, expected in cases:
                with self.subTest(name=name):
                    request = {**copy.deepcopy(base), **copy.deepcopy(changes)}
                    # The forcing mismatch case must use an actually different
                    # saved realization, not a forged metadata-only assertion.
                    if "forcing_seed" in changes:
                        from orbital_workflow.simulation import generate_forcing
                        request["forcing_id"] = generate_forcing(store,
                            horizon=request["end"], seed=changes["forcing_seed"])
                    summary = {"score": 1., "requested_interval": [request["start"], request["end"]],
                        "observation_window": request["observation_window"],
                        "experiment": request["experiment"],
                        "observed_interval": [request["start"], min(request["end"], request["start"] + .1)],
                        "outcome": "outer_exit", "numerical_settings": {
                            key: request[key] for key in ("method", "sample_step", "max_step", "rtol", "atol")},
                        "persistence_measurement": {"mean_similarity": .1, "complete_revolutions": 1}}
                    item = trajectory_evidence(request, summary, store, observation_ref="fixture")
                    projected = binding.root_score(item)
                    self.assertEqual(full_scope(request, simulator.problem), expected)
                    self.assertEqual(projected is not None, expected)
                    row = select_observations({"measurements": [item]})[0]
                    self.assertEqual(row["observation_window"], summary["observation_window"])
                    self.assertEqual(full_scope(row, simulator.problem), projected is not None)

    def test_selected_projected_integrations_match_root_scope_after_early_exit(self):
        project = Path(__file__).resolve().parents[1]
        settings = load_settings(project / "scenarios/scenario_02/study.toml")
        settings["study"]["horizon"] = .5  # Finite diagnostic fixture, no Episode or estimator.
        with tempfile.TemporaryDirectory() as temporary:
            store = Artifacts(Path(temporary) / "objects")
            simulator = ScenarioSimulator(settings, store)
            dispatcher = ToolDispatcher(store, simulator.persistence_settings)
            binding = ScientificBindings(settings, None, None)
            cases = [("complete", {}, True),
                ("refinement", {"refinement": {"sample_step": .01, "max_step": .025}}, True),
                ("short interval", {"interval": [0, .05]}, False),
                ("reduction", {"terms": {"forcing": False}}, False)]
            measurements = []
            for name, experiment, expected in cases:
                with self.subTest(name=name):
                    arguments = simulator.resolve_run({"vx": 30., "vy": 1.,
                        "experiment": experiment}, parts=True)
                    observation = dispatcher.execute("sim.run", arguments)
                    item = project_observation(observation, store).as_record()["measurements"][0]
                    measurements.append(item)
                    row = select_observations({"measurements": [item]})[0]
                    self.assertEqual(full_scope(row, simulator.problem), binding.root_score(item) is not None)
                    self.assertEqual(full_scope(row, simulator.problem), expected)
                    self.assertEqual(row["observation_window"], item["measurement"]["observation_window"])
                    self.assertEqual(row["experiment"], item["measurement"]["experiment"])
                    self.assertEqual(row["effective_duration"], item["measurement"]["score"])
                    if name != "short interval":
                        self.assertEqual(row["outcome"], "outer_exit")
                        self.assertLess(row["observed_until"], row["end"])
            selected = select_observations({"measurements": measurements})
            self.assertEqual(len(selected), 2)
            complete = [row for row in selected if full_scope(row, simulator.problem)]
            self.assertEqual(len(complete), 1)
            self.assertEqual(complete[0]["numerical_settings"]["sample_step"], .01)

    def test_csv_retains_each_refinement_and_its_actual_score_and_parameters(self):
        root = Path(__file__).resolve().parents[1]
        settings = load_settings(root / "scenarios/scenario_02/study.toml")
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            simulator = ScenarioSimulator(settings, Artifacts(directory / "objects"))
            physical = simulator.resolve_run({"vx": .1, "vy": -1.2})
            observations = []
            for index, (end, rtol, score) in enumerate(((45., 1e-7, .35),
                    (physical["end"], 1e-7, .166), (physical["end"], 1e-10, .165))):
                observations.append({"type": "trajectory", "physical_id": "fixture_same_physics",
                    "executed_forcing_seed": simulator.problem["forcing"]["seed"],
                    "evidence_key": "fixture_" + str(index), "physical": physical,
                    "measurement": {"score": score, "requested_interval": [0., end],
                        "observation_window": physical["observation_window"],
                        "experiment": physical["experiment"],
                        "observed_interval": [0., min(46., end)], "outcome": "outer_exit",
                        "numerical_settings": {"sample_step": .02, "max_step": .05, "rtol": rtol},
                        "persistence_measurement": {"effective_duration": score,
                            "mean_similarity": .01, "complete_revolutions": 3}}})
            findings = {"measurements": observations}
            self.assertEqual(len(select_observations(findings)), 1)
            self.assertEqual(select_observations(findings)[0]["effective_duration"], .165)
            self.assertEqual(len(all_observations(findings)), 3)
            path = directory / "observations.csv"
            write_observations_csv(path, findings)
            with path.open(newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual([row["evidence_key"] for row in rows], ["fixture_0", "fixture_1", "fixture_2"])
            self.assertEqual([float(row["effective_duration"]) for row in rows], [.35, .166, .165])
            self.assertEqual(json.loads(rows[0]["requested_interval"]), [0., 45.])
            self.assertEqual(json.loads(rows[0]["observation_window"]), list(physical["observation_window"]))
            self.assertEqual(json.loads(rows[0]["experiment"]), json.loads(json.dumps(physical["experiment"])))
            self.assertEqual(json.loads(rows[2]["numerical_settings"])["rtol"], 1e-10)
            self.assertEqual(float(rows[2]["maximum_observed_effective_duration"]), .35)


if __name__ == "__main__":
    unittest.main()
