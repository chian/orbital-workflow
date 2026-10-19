"""Synthetic accounting fixtures only: no model, simulator or estimator fits."""

from dataclasses import asdict, replace
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from orbital_workflow.bootstrap import use_method_loop
use_method_loop(Path(__file__).resolve().parents[2] / "OpenChia")

from orbital_workflow.credit import (BestScoreCredit, CreditController, CreditTarget, Evidence,
                                    compact_evidence, evidence_key)
from orbital_workflow.durable import DurableWorkflow
from orbital_workflow.gravity import GravitySystem
from orbital_workflow.failures import ActionRequestError
from orbital_workflow.records import Observation, plain
from orbital_workflow.runtime import Kind, ToolAction
from orbital_workflow.scientific import ScientificBindings, load_settings
from orbital_workflow.simulation import SimulationRequest
from orbital_workflow.score_yield import NumericBand, STATUS_INSUFFICIENT, YieldEstimate


CONFIG = Path(__file__).resolve().parents[1] / "study.toml"
PARENT_PATH = ((Kind.ROOT.value, "synthetic-parent"),)


def fixture_evidence(score, name="saved-observation", *, eligible=True):
    # These numbers are declared software fixtures, never simulation output.
    return Evidence(({"type": "trajectory", "evidence_key": name,
        "software_fixture_only": True, "eligible": eligible,
        "measurement": {"score": score, "persistence_measurement": {}}},))


class FakeEstimator:
    """Expose precisely the credited input stream without doing any fitting."""
    def __init__(self, parameters):
        self.parameters, self.scores = parameters, []

    def observe(self, value):
        self.scores.append(value)
        return self.state()

    def state(self):
        return YieldEstimate(len(self.scores), NumericBand.coded(STATUS_INSUFFICIENT),
            self.parameters, {"software_fixture_only": True, "fitter_executed": False})


class InheritedCredit(unittest.TestCase):
    def setUp(self):
        self.estimator = patch("orbital_workflow.credit.ScalarScoreYieldEstimator", FakeEstimator)
        self.estimator.start()
        self.addCleanup(self.estimator.stop)
        self.no_fit = patch("orbital_workflow.score_yield.estimate_score_yield",
            side_effect=AssertionError("This software fixture must never estimate or fit yield"))
        self.no_fit.start()
        self.addCleanup(self.no_fit.stop)
        self.settings = load_settings(CONFIG)
        self.target = CreditTarget("same_explicit_target", "acquired_trajectories")

    def controller(self, *, inherited=None, target=None, path=PARENT_PATH, projection=None):
        return CreditController(self.settings, Kind.PARTS, projection,
            target=target or self.target, inherited=inherited, path=path)

    def test_same_target_inherits_without_observation_then_only_new_delta_is_credited(self):
        parent = self.controller()
        original = fixture_evidence(.166)
        parent.observe("recorded existing progress", original, is_root=True)
        baseline = parent.assignment.inheritance()
        child = self.controller(inherited=baseline, path=(*PARENT_PATH, (Kind.PARTS.value, "renamed")))
        initial = child.state().as_record()
        self.assertEqual(initial["inherited_score"], .166)
        self.assertEqual(initial["credit"], .166)
        self.assertEqual(initial["gained_credit"], 0)
        self.assertEqual(initial["units"], 0)
        self.assertEqual(initial["yield_estimate"]["turns"], 0)
        self.assertEqual(child.history, [])
        self.assertEqual(child.own_observations, [])
        self.assertEqual(child.assignment.evidence, {})

        repeat = child.observe("retrieve saved run", original, is_root=False).record
        self.assertEqual(repeat["marginal_credit"], 0)
        self.assertEqual(repeat["score_assignment"]["received_scores"], [.166])
        self.assertEqual(repeat["score_assignment"]["distinct_observations"], 1)
        improvement = child.observe("real higher fixture score", fixture_evidence(.2, "improvement"),
            is_root=False).record
        self.assertEqual(improvement["marginal_credit"], .2 - .166)
        self.assertEqual(improvement["gained_credit"], .2 - .166)
        self.assertEqual(child.estimator.scores, [0, .2 - .166])
        # Parent accounting receives actual evidence, never child credit totals.
        received = parent.observe("completed child contribution", fixture_evidence(.2, "improvement"),
            is_root=True).record
        self.assertEqual(received["marginal_credit"], .2 - .166)
        self.assertEqual(received["credit"], .2)
        self.assertEqual(parent.observe("repeat projection", original, is_root=True).record["marginal_credit"], 0)

    def test_distinct_target_can_use_same_evidence_but_cannot_import_other_target_baseline(self):
        parent = self.controller()
        observation = fixture_evidence(.166)
        parent.observe("original", observation, is_root=True)
        different = CreditTarget("different_explicit_target", "acquired_trajectories")
        with self.assertRaisesRegex(ValueError, "same explicit target"):
            self.controller(target=different, inherited=parent.assignment.inheritance())
        changed_projection = CreditTarget(self.target.target_id, "complete_scenario")
        with self.assertRaisesRegex(ValueError, "same explicit target"):
            self.controller(target=changed_projection, inherited=parent.assignment.inheritance())
        child = self.controller(target=different)
        assigned = child.observe("same evidence supports different contribution", observation, is_root=False).record
        self.assertEqual(assigned["inherited_score"], 0)
        self.assertEqual(assigned["marginal_credit"], .166)
        self.assertEqual(child.assignment.evidence["saved-observation"]["measurement"]["score"], .166)

    def test_baseline_uses_prior_eligible_winner_and_retains_original_source_across_ancestry(self):
        projection = lambda item: item["measurement"]["score"] if item["eligible"] else None
        parent = self.controller(projection=projection)
        parent.observe("ineligible high score retained", fixture_evidence(20, "out-of-target", eligible=False),
            is_root=True)
        self.assertIsNone(parent.assignment.inheritance())
        parent.observe("eligible prior score", fixture_evidence(.166), is_root=True)
        baseline = parent.assignment.inheritance()
        self.assertEqual(baseline.source_unit, 2)
        child = self.controller(inherited=baseline, projection=projection)
        grandchild = self.controller(inherited=child.assignment.inheritance(), projection=projection)
        self.assertEqual(grandchild.assignment.inherited.as_record(), baseline.as_record())
        self.assertEqual(grandchild.assignment.evidence, {})
        self.assertNotIn("inherited_progress", grandchild.model_state())
        self.assertEqual(grandchild.model_state()["inherited_score"], .166)
        with self.assertRaisesRegex(ValueError, "eligible"):
            self.controller(inherited=baseline, projection=lambda item: None)

    def test_no_baseline_can_be_derived_from_findings_or_reference_score(self):
        assignment = BestScoreCredit(target=self.target)
        assignment.observe(Evidence((), ({"reference_score": 999, "claim": "known progress"},)))
        self.assertEqual(assignment.best_score, 0)
        self.assertIsNone(assignment.inheritance())

    def test_live_child_declaration_requires_explicit_target_relationship(self):
        binding = ScientificBindings(self.settings, None, None)
        for missing in ({}, {"reference_score": 999}, {"credit_target": "renamed"}):
            with self.subTest(assignment=missing), self.assertRaises(ActionRequestError) as caught:
                binding.child({"child_kind": Kind.SIMULATION, "child_assignment_json": json.dumps(missing)},
                    SimpleNamespace(path=PARENT_PATH))
            self.assertEqual(caught.exception.diagnostic,
                {"category": "wrong_parameters", "tool": None, "field": "credit_target"})

    def test_actual_loop_archives_and_reconstructs_only_synthetic_acquisitions(self):
        """Run the framework on finite fixtures, never a scientific workflow."""
        class FixtureTools:
            store = None

            def execute(self, name, arguments):
                if name != "math.arithmetic":
                    raise AssertionError("Only the synthetic acquisition adapter is allowed")
                return Observation("software_fixture", {"item": arguments["item"]})

        class InterruptOnce(DurableWorkflow):
            def _record_unit(self, item, contribution, view):
                super()._record_unit(item, contribution, view)
                if view.unit_label == "fixture-retrieve":
                    raise InterruptedError("Intentional interruption of synthetic accounting fixture")

        def build_fixture(directory):
            tools = FixtureTools()
            binding = ScientificBindings(self.settings, None, tools)
            physical = asdict(SimulationRequest("synthetic_forcing_not_generated",
                a=self.settings["study"]["a"], sigma=self.settings["study"]["sigma"],
                scenario_id=binding.problem["id"], gravity=GravitySystem.from_record(binding.problem["gravity"]),
                initial_state=(*binding.problem["initial_position"], 0, 1),
                forcing_seed=binding.problem["forcing"]["seed"],
                observation_window=tuple(binding.problem["evaluation_interval"]),
                radial_limits=tuple(binding.problem["radial_limits"])))
            initials = []

            def source(actions):
                class FiniteFixture:
                    def next(self, view):
                        if view.units_consumed == 0:
                            initials.append((view.path, view.controller_state.as_record(),
                                             binding.controllers[view.path].model_state()))
                        if view.units_consumed == len(actions):
                            return None
                        action = actions[view.units_consumed]
                        if isinstance(action, tuple):
                            label, score = action
                            item = plain(fixture_evidence(score, "fixture_" + str(score)).measurements[0])
                            item["physical"] = physical
                            item["measurement"].update(requested_interval=binding.problem["evaluation_interval"],
                                observation_window=binding.problem["evaluation_interval"])
                            return ToolAction("fixture-" + label, "math.arithmetic", {"item": item})
                        relation, objective, child_actions = action["relation"], action["objective"], action["actions"]
                        response = {"child_kind": (Kind.SIMULATION if len(view.path) == 1 else Kind.PARTS),
                            "objective": objective, "child_assignment_json": json.dumps({
                                "credit_target": relation, "reference_score": 999, "software_fixture_only": True}),
                            "report_decision": "Use the requested synthetic score", "report_fields": [{
                                "name": "observed_score", "meaning": "Largest score actually acquired in this fixture child",
                                "schema_json": '{"type":["number","null"]}'}]}
                        child = binding.child(response, view)
                        return replace(child, spec=replace(child.spec, source_factory=lambda request: source(child_actions)),
                            synthesize_report=lambda result, completion, request: {"observed_score": max(
                                (item["measurement"]["score"] for item in result.measurements), default=None)})
                return FiniteFixture()

            actions = [
                {"relation": "new", "objective": "Seed recorded fixture progress", "actions": [("seed", .166)]},
                {"relation": "parent", "objective": "Renamed investigation A", "actions": [("retrieve", .166)]},
                {"relation": "parent", "objective": "Renamed investigation B", "actions": [("retrieve-again", .166)]},
                {"relation": "parent", "objective": "Improve the same target", "actions": [("improve", .2)]},
                {"relation": "new", "objective": "Explicitly independent fixture contribution", "actions": [("independent", .166)]},
                {"relation": "parent", "objective": "No acquired child observations", "actions": []},
                {"relation": "parent", "objective": "Same target through an intermediate child", "actions": [
                    {"relation": "parent", "objective": "Same target grandchild", "actions": [("nested", .3)]}]},
            ]
            root = replace(binding.spec(Kind.ROOT, "synthetic-root", "Software accounting fixture", {}),
                source_factory=lambda request: source(actions))
            bindings = {kind: replace(value, project_tool=lambda observation, request: Evidence(
                (observation.findings["item"],), ({"software_fixture_only": True},)))
                for kind, value in binding.bindings().items()}
            return binding, bindings, tools, root, initials

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            binding, bindings, tools, root, _ = build_fixture(directory)
            with self.assertRaises(InterruptedError):
                InterruptOnce(bindings, tools, directory / "episodes").run(root, "synthetic-inheritance")
            prefix = {path.relative_to(directory): path.read_bytes() for path in
                      (directory / "episodes" / "units").glob("*.json")}
            binding, bindings, tools, root, initials = build_fixture(directory)
            record, result = DurableWorkflow(bindings, tools, directory / "episodes").run(root, "synthetic-inheritance")
            for relative, payload in prefix.items():
                self.assertEqual((directory / relative).read_bytes(), payload)
            self.assertEqual(record.units_consumed, 7)
            self.assertEqual(record.controller_state.record["credit"], .3)
            self.assertEqual([unit.controller_step.record["marginal_credit"] for unit in record.unit_records],
                [.166, 0, 0, .2 - .166, 0, 0, .3 - .2])
            self.assertEqual(len(result.measurements), 3)

            children = [json.loads((directory / unit.child.record_file).read_text()) for unit in record.unit_records]
            target = record.controller_state.record["credit_target"]
            for index in (1, 2):
                child = children[index]
                self.assertEqual(child["controller_state"]["credit_target"], target)
                self.assertEqual(child["controller_state"]["inherited_score"], .166)
                self.assertEqual(child["units"][0]["controller_step"]["marginal_credit"], 0)
                self.assertEqual(len(child["units"]), 1)
                self.assertEqual(record.unit_records[index].child.unit_records, ())
            self.assertEqual(children[3]["controller_state"]["gained_credit"], .2 - .166)
            self.assertNotEqual(children[4]["controller_state"]["credit_target"], target)
            self.assertEqual(children[4]["controller_state"]["marginal_credit"], .166)
            empty = children[5]
            self.assertEqual(empty["units"], [])
            self.assertEqual(empty["controller_state"]["units"], 0)
            self.assertEqual(empty["controller_state"]["inherited_score"], .2)
            self.assertEqual(empty["controller_state"]["yield_estimate"]["turns"], 0)
            empty_result = json.loads((directory / record.unit_records[5].child_result.result_file).read_text())
            self.assertEqual(empty_result["measurements"], [])
            self.assertEqual(empty_result["findings"], [])
            self.assertIsNone(record.unit_records[5].episode_update.report.values["observed_score"])
            self.assertEqual(binding.controllers, {})

            for path, machine, model in initials:
                self.assertNotIn("inherited_progress", model)
                self.assertNotIn("target_id", model["credit_target"])
                self.assertEqual(machine["units"], 0)
            # Exercise only the read-only verifier's new baseline checks on
            # these explicitly synthetic temporary records, without its run
            # loader, any tools, controller reconstruction or fitting.
            module_spec = importlib.util.spec_from_file_location("synthetic_credit_verifier",
                Path(__file__).with_name("verify_scored_run.py"))
            verifier_module = importlib.util.module_from_spec(module_spec)
            module_spec.loader.exec_module(verifier_module)
            metadata = {}
            for path in (directory / "episodes").glob("episode_*.json"):
                value = json.loads(path.read_text())
                metadata[value["episode_id"]] = {**value, "file": path}
            checks = []

            def check(condition, code, location):
                self.assertTrue(condition, (code, location))
                checks.append(code)

            verifier = SimpleNamespace(metadata=metadata,
                read_json=lambda path: json.loads(path.read_text()), check=check,
                api=SimpleNamespace(key=evidence_key, compact=compact_evidence),
                machine={evidence_key(item): compact_evidence(item) for item in result.measurements},
                root_score=binding.root_score)
            for value in metadata.values():
                state = value["controller_state"]
                verifier_module.Verifier.inheritance(verifier, value, state["credit_target"],
                    state["inherited_progress"], state["inherited_score"])
            self.assertIn("baseline_source_is_prior_eligible_ancestor_acquisition", checks)
            binding, bindings, tools, root, _ = build_fixture(directory)
            reconstructed, reconstructed_result = DurableWorkflow(bindings, tools, directory / "episodes").run(
                root, "synthetic-inheritance")
            self.assertEqual(reconstructed.as_record(), record.as_record())
            self.assertEqual(reconstructed_result.as_record(), result.as_record())


if __name__ == "__main__":
    unittest.main()
