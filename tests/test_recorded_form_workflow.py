"""Actual method-loop communication over labelled synthetic saved observations.

No provider, integration, forcing generator or yield fit is executed.
"""

from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from orbital_workflow.bootstrap import use_method_loop
use_method_loop(Path(__file__).resolve().parents[2] / "OpenChia")

from orbital_workflow.artifacts import Artifacts
from orbital_workflow.communication import ReportBoundaryError, ReportContract, report_contract, report_field_examples
from orbital_workflow.credit import BestScoreCredit, compact_evidence, evidence_key, project_observation, trajectory_evidence
from orbital_workflow.durable import CachedModels, DurableWorkflow
from orbital_workflow.records import Observation, plain
from orbital_workflow.report_facts import model_measurements, project_fields, trajectory_facts
from orbital_workflow.runtime import Kind
from orbital_workflow.scientific import INSTRUCTIONS, ScientificBindings, load_settings
from orbital_workflow.score_yield import NumericBand, STATUS_NORMAL, YieldEstimate


CONFIG = Path(__file__).resolve().parents[1] / "study.toml"


def closed(properties, nullable=False):
    return {"type": ["object", "null"] if nullable else "object", "additionalProperties": False,
            "required": list(properties), "properties": properties}


def field(name, schema, binding=None):
    return {"name": name, "meaning": "Explicit synthetic recorded-work fixture",
            "schema_json": json.dumps(schema), "binding_json": json.dumps(binding or {})}


def bound(selection, fields=None, value=None):
    return {"scope": "returned_trajectories", "select": selection,
            **({"fields": fields} if fields is not None else {"value": value})}


PAIR = {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2}
ROW_PROPERTIES = {"source": {"type": "integer"}, "ship": PAIR, "value": {"type": "number"},
                  "requested": PAIR, "observed": PAIR,
                  "scope": {"type": "string", "enum": ["base", "derived"]}}
COLUMNS = {"source": "observation_index", "ship": "velocity", "value": "score",
           "requested": "requested_interval", "observed": "observed_interval", "scope": "experiment_kind"}


def requested_fields(interpret=True):
    fields = [field("actual_contribution", closed(ROW_PROPERTIES, nullable=True),
                    bound("parent_target_best", fields=COLUMNS)),
              field("observed_rows", {"type": "array", "items": closed(ROW_PROPERTIES)},
                    bound("all", fields=COLUMNS))]
    if interpret:
        fields += [field("shape", {"type": "string", "enum": ["undetermined"]}),
                   field("label", {"type": "string", "format": "identifier"})]
    return fields


class TwoTurnEstimator:
    def __init__(self, parameters):
        self.parameters, self.scores = parameters, []

    def observe(self, score):
        self.scores.append(score)
        return self.state()

    def state(self):
        gain = 0.0 if len(self.scores) >= 2 else 1.0
        return YieldEstimate(len(self.scores), NumericBand(gain, gain, gain, STATUS_NORMAL, 0, 0),
                             self.parameters, {"software_fixture_only": True, "fitter_executed": False})


def fixture_forcing(store, *, horizon, seed, **unused):
    return store.put_arrays(times=np.array([0., horizon]), eta=np.zeros((2, 2)), seed=np.array(seed))


class SavedFixtureTools:
    """Save explicit test data in the real tool artifact format; do no physics."""
    def __init__(self, store):
        self.store, self.observations = store, []

    def execute(self, name, arguments):
        if name != "sim.run":
            raise AssertionError("Only the declared synthetic trajectory fixture is available")
        args = plain(arguments)
        velocity = args["initial_state"][2:4]
        score = .357 if args["end"] == 45 else .3 if velocity[0] == .15 else .2
        observed_end = args["end"] if args["end"] == 45 else 50.
        summary = {"software_fixture_only": True, "score": score,
            "initial_state": args["initial_state"], "terms": args["terms"],
            "active_bodies": args["active_bodies"], "gravity_mode": args["gravity_mode"],
            "radial_limits": args["radial_limits"], "spatial_box": args["spatial_box"],
            "requested_interval": [args["start"], args["end"]],
            "observed_interval": [args["start"], observed_end],
            "observation_window": args["observation_window"], "experiment": args["experiment"],
            "outcome": "horizon_reached" if args["end"] == 45 else "outer_exit",
            "terminal_state": args["initial_state"], "persistence_measurement": {},
            "numerical_settings": {key: args[key] for key in ("method", "max_step", "rtol", "atol", "sample_step")}}
        arrays = self.store.put_arrays(times=np.array([args["start"], observed_end]),
                                       states=np.array([args["initial_state"], args["initial_state"]]))
        saved = self.store.put_json({"request": args, "summary": summary, "trajectory": arrays})
        request = self.store.put_json({"tool": name, "arguments": args})
        observation = Observation(name, summary, (request, args["forcing_id"], arrays, saved))
        self.observations.append(observation)
        return observation


class ParentReceived(Exception):
    pass


class ModelFixture:
    def __init__(self, tools, interpret=True, invalid_assignment=False, invalid_schema=None):
        self.tools, self.interpret = tools, interpret
        self.invalid_assignment = invalid_assignment
        self.invalid_schema = invalid_schema
        self.calls, self.releases, self.parent_input = [], [], None

    def has_session(self, episode_id, role):
        return any(call[0] == episode_id for call in self.calls)

    async def release(self, episode_id):
        self.releases.append(episode_id)

    async def complete(self, episode_id, role, instructions, payload, schema):
        context = payload["current"]
        self.calls.append((episode_id, role, instructions, deepcopy(context), schema))
        if context["mode"] == "form":
            if context["episode_kind"] != Kind.SIMULATION:
                raise AssertionError("Recorded-only parts form must not call a model")
            if context["form_attempt"] == 0:
                return {"shape": "paragraph", "label": "fixture"}
            if context["form_attempt"] == 1:
                return {"shape": "undetermined", "label": self.tools.observations[0].artifacts[-1]}
            return {"shape": "undetermined", "label": "fixture"}
        kind, units = context["episode_kind"], context["controller"]["units"]
        if kind == Kind.ROOT:
            if units:
                self.parent_input = context
                raise ParentReceived
            response = self.child(Kind.SIMULATION, requested_fields(self.interpret))
            if self.invalid_assignment and not context["operation_attempt"]:
                response["child_assignment_json"] = '{"credit_target":"new","trial":2}'
            if self.invalid_schema is not None and not context["operation_attempt"]:
                response["report_fields"] = [self.invalid_schema]
            if context["operation_attempt"] and self.tools.observations:
                raise AssertionError("Invalid parent commissioning acquired child work before correction")
            return response
        if kind == Kind.SIMULATION:
            return self.run(.1) if not units else self.child(Kind.PARTS, requested_fields(False))
        return self.run(.10330396, {"interval": [0, 45]}) if not units else self.run(.15)

    @staticmethod
    def child(kind, fields):
        return {"action": "child", "child_kind": kind, "label": "fixture-investigation",
                "objective": "Iterate over labelled synthetic saved observations",
                "child_assignment_json": '{"credit_target":"new","software_fixture_only":true}',
                "report_decision": "Use this exact returned synthetic contribution", "report_fields": fields}

    @staticmethod
    def run(vx, experiment=None):
        return {"action": "tool", "label": "synthetic-observation", "tool_name": "sim.run",
                "arguments_json": json.dumps({"vx": vx, "vy": -1.2,
                    **({"experiment": experiment} if experiment else {})})}


class RecordedFormWorkflow(unittest.IsolatedAsyncioTestCase):
    async def fixture(self, directory, interpret, invalid_assignment=False, invalid_schema=None):
        settings = load_settings(CONFIG)
        tools = SavedFixtureTools(Artifacts(directory / "objects"))
        fake = ModelFixture(tools, interpret, invalid_assignment, invalid_schema)
        models = CachedModels(fake, directory / "model-cache")
        binding = ScientificBindings(settings, models, tools)
        workflow = DurableWorkflow(binding.bindings(), tools, directory / "episodes")
        root = binding.spec(Kind.ROOT, "synthetic-parent", "Software fixture only", {})
        with patch("orbital_workflow.scenario.generate_forcing", fixture_forcing), \
             patch("orbital_workflow.credit.ScalarScoreYieldEstimator", TwoTurnEstimator), \
             patch("orbital_workflow.tools.integrate", side_effect=AssertionError("No integration allowed")), \
             patch("orbital_workflow.score_yield.estimate_score_yield", side_effect=AssertionError("No fit allowed")):
            with self.assertRaises(ParentReceived):
                await workflow.run_async(root, "recorded-form-software-fixture")
        return binding, tools, fake, models

    async def test_nested_return_identifies_same_credited_work_and_final_form_corrects_without_acquisition(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            binding, tools, fake, models = await self.fixture(directory, True)
            delivered = fake.parent_input["child_reports"][0]
            self.assertEqual(delivered["actual_contribution"]["value"], .3)
            self.assertEqual(delivered["actual_contribution"]["ship"], [.15, -1.2])
            self.assertEqual(delivered["actual_contribution"]["requested"], [0, binding.problem["evaluation_interval"][1]])
            self.assertEqual(delivered["actual_contribution"]["observed"], [0, 50])
            self.assertEqual([row["value"] for row in delivered["observed_rows"]], [.2, .357, .3])
            self.assertEqual(delivered["observed_rows"][1]["scope"], "derived")
            self.assertEqual(fake.parent_input["controller"]["credit"], .3)
            self.assertEqual(len(tools.observations), 3)
            form_calls = [call for call in fake.calls if call[3]["mode"] == "form"]
            self.assertEqual(len(form_calls), 3)
            self.assertEqual([call[3]["form_attempt"] for call in form_calls], [0, 1, 2])
            self.assertEqual(form_calls[1][3]["form_diagnostic"]["code"], "enum")
            self.assertEqual(form_calls[2][3]["form_diagnostic"]["code"], "audit_identity")
            self.assertTrue(all(set(call[4]["properties"]) == {"shape", "label"} for call in form_calls))
            self.assertTrue(all(call[3]["controller"]["units"] == 2 for call in form_calls))
            self.assertEqual([call[3]["controller"]["yield_estimate"]["turns"] for call in form_calls], [2, 2, 2])
            action_ids = {call[0] for call in fake.calls if call[3]["mode"] == "action"}
            self.assertTrue(all(call[0] in action_ids and call[1] == "REASONING" and call[2] == INSTRUCTIONS for call in form_calls))
            self.assertFalse(any(call[0].startswith("report-") for call in fake.calls))
            self.assertEqual(binding.controllers, {})
            self.assertEqual(binding.completed_runs, {})
            self.assertEqual(models.history, {})
            cached_forms = [json.loads(path.read_text()) for path in (directory / "model-cache").glob("*.json")
                            if json.loads(path.read_text())["request"]["context"]["mode"] == "form"]
            self.assertEqual(len(cached_forms), 3)
            self.assertTrue(any(item["response"]["shape"] == "paragraph" for item in cached_forms))
            self.assertTrue(any(item["request"]["context"].get("form_diagnostic", {}).get("code") == "audit_identity"
                                for item in cached_forms))
            # Reports retain exact parent fields, and private provenance stays in audit.
            self.assertEqual(set(delivered), {"actual_contribution", "observed_rows", "shape", "label"})
            serialized = json.dumps(fake.parent_input)
            for observation in tools.observations:
                for reference in observation.artifacts:
                    self.assertNotIn(reference, serialized)
            events = [json.loads(path.read_text()) for path in (directory / "episodes/units").glob("*.json")]
            self.assertEqual(len(events), 5)
            root_event = next(event for event in events if event["controller_step"]["units"] == 1
                              and event["controller_step"]["credit"] == .3)
            self.assertEqual(root_event["child_report"], delivered)
            self.assertEqual(root_event["controller_step"]["score_assignment"]["received_scores"], [.2, .3])
            for item in root_event["controller_input"]["measurements"]:
                self.assertIn("observation_ref", item)
                self.assertIn("executed_forcing_seed", item)
                self.assertEqual(evidence_key(item), evidence_key(compact_evidence(item)))

    async def test_recorded_only_parent_forms_need_no_final_model_call(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, tools, fake, _ = await self.fixture(Path(temporary), False)
            self.assertEqual(len(tools.observations), 3)
            self.assertFalse(any(call[3]["mode"] == "form" for call in fake.calls))
            self.assertEqual(fake.parent_input["child_reports"][0]["actual_contribution"]["value"], .3)

    async def test_bindings_are_explicit_and_use_same_stable_source_for_best_pair(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            binding, tools, _, _ = await self.fixture(directory, False)
            observations = [project_observation(observation, tools.store).measurements[0] for observation in tools.observations]
            selected = {"renamed_velocity": bound("parent_target_best", value="velocity"),
                        "renamed_score": bound("parent_target_best", value="score")}
            result = project_fields(selected, observations, tools.store, binding.root_score)
            self.assertEqual(result, {"renamed_velocity": [.15, -1.2], "renamed_score": .3})
            self.assertIsNone(project_fields({"empty": selected["renamed_score"]}, [], tools.store, binding.root_score)["empty"])
            contract = report_contract("Use exact measurements", {}, [field("best_score", {"type": "number"})])
            self.assertFalse(contract.fact_bindings)  # Names and prose never infer a selector.
            for example in report_field_examples():
                report_contract("Example", {}, [example])
            roundtrip = report_contract("Use source rows", {}, requested_fields(False))
            self.assertEqual(ReportContract.from_record(roundtrip.as_record()).as_record(), roundtrip.as_record())
            with self.assertRaises(ReportBoundaryError):
                report_contract("Bad invented source", {}, [field("x", {"type": "number"}, bound("max_score", value="trial"))])
            # Stamp credit identity before adding artifact provenance.
            first = tools.observations[0]
            request = tools.store.json(first.artifacts[0])["arguments"]
            legacy = trajectory_evidence(request, first.findings, tools.store)
            self.assertEqual(evidence_key(legacy), evidence_key(observations[0]))
            self.assertEqual(trajectory_facts(observations[1], tools.store, 2)["experiment"]["interval"], [0, 45])

    async def test_zero_forcing_base_and_selected_experiment_meaning_keep_exact_sources(self):
        with tempfile.TemporaryDirectory() as temporary:
            settings = load_settings(CONFIG)
            settings["study"]["sigma"] = 0.
            tools = SavedFixtureTools(Artifacts(Path(temporary) / "objects"))
            binding = ScientificBindings(settings, None, tools)
            with patch("orbital_workflow.scenario.generate_forcing", fixture_forcing):
                base = tools.execute("sim.run", binding.simulation_arguments({"vx": .1, "vy": -1.2}))
                reduced = tools.execute("sim.run", binding.simulation_arguments({"vx": .1, "vy": -1.2,
                    "experiment": {"terms": {"rotating": False}, "active_bodies": ["body_1"],
                                   "interval": [0, 45], "refinement": {"max_step": .01}}}, parts=True))
            base_item = project_observation(base, tools.store).measurements[0]
            reduced_item = project_observation(reduced, tools.store).measurements[0]
            self.assertEqual(base_item["physical"]["forcing_seed"], "deterministic")
            self.assertEqual(base_item["executed_forcing_seed"], settings["forcing"]["seed"])
            self.assertEqual(binding.root_score(base_item), .2)
            self.assertIsNone(binding.root_score(reduced_item))
            facts = trajectory_facts(reduced_item, tools.store, 2)
            experiment = facts["experiment"]
            self.assertFalse(experiment["terms"]["rotating"])
            self.assertEqual(experiment["active_bodies"], ["body_1"])
            self.assertEqual(experiment["interval"], [0, 45])
            self.assertEqual(experiment["refinement"]["max_step"], .01)
            self.assertEqual(model_measurements(reduced.findings)["experiment"], experiment)
            for field_name in ("source_observation", "a", "sigma", "forcing_seed", "gravity"):
                self.assertNotIn(field_name, experiment)

    async def test_parent_configuration_forwarding_is_corrected_before_child_execution(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, tools, fake, _ = await self.fixture(Path(temporary), False, invalid_assignment=True)
            proposals = [call[3] for call in fake.calls if call[3]["episode_kind"] == Kind.ROOT
                         and call[3]["controller"]["units"] == 0]
            self.assertEqual(len(proposals), 2)
            self.assertEqual(proposals[1]["action_failure"], {"category": "wrong_parameters", "tool": None,
                "field": "child_assignment_json.trial"})
            self.assertEqual(proposals[1]["controller"]["yield_estimate"]["turns"], 0)
            self.assertEqual(len(tools.observations), 3)

    async def test_bound_result_filters_are_rejected_before_child_and_real_zero_or_absence_fits(self):
        bad_fields = [field("score", {"type": ["number", "null"], "minimum": 999},
                            bound("max_score", value="score")),
                      field("rows", {"type": "array", "items": {"type": "number"}, "maxItems": 1},
                            bound("all", value="score"))]
        for declaration in bad_fields:
            with self.subTest(declaration=declaration), tempfile.TemporaryDirectory() as temporary:
                _, tools, fake, _ = await self.fixture(Path(temporary), False, invalid_schema=declaration)
                attempts = [call[3] for call in fake.calls if call[3]["episode_kind"] == Kind.ROOT
                            and call[3]["controller"]["units"] == 0]
                self.assertEqual(len(attempts), 2)
                self.assertEqual(attempts[1]["action_failure"], {"category": "wrong_parameters", "tool": None,
                                                               "field": "report_fields"})
                self.assertEqual(attempts[1]["controller"]["units"], 0)
                self.assertEqual(len(tools.observations), 3)
        compatible = report_contract("Retain actual zeros and empty work", {}, [
            field("best", {"type": ["number", "null"], "minimum": 0}, bound("max_score", value="score")),
            field("values", {"type": "array", "items": {"type": "number", "minimum": 0}}, bound("all", value="score"))])
        self.assertEqual(compatible.admit({"best": 0., "values": [0., 0.]}, audit_identifiers=()).values["best"], 0.)
        self.assertEqual(compatible.admit({"best": None, "values": []}, audit_identifiers=()).as_record(),
                         {"best": None, "values": []})

    async def test_unexpected_factual_source_failure_preserves_closed_scored_result_without_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            settings = load_settings(CONFIG)
            tools = SavedFixtureTools(Artifacts(directory / "objects"))
            fake = ModelFixture(tools, False)
            binding = ScientificBindings(settings, CachedModels(fake, directory / "model-cache"), tools)
            root = binding.spec(Kind.ROOT, "synthetic-parent", "Software fixture only", {})
            with patch("orbital_workflow.scenario.generate_forcing", fixture_forcing), \
                 patch("orbital_workflow.credit.ScalarScoreYieldEstimator", TwoTurnEstimator), \
                 patch("orbital_workflow.scientific.project_fields", side_effect=OSError("synthetic source read failure")):
                with self.assertRaises(ReportBoundaryError) as caught:
                    await DurableWorkflow(binding.bindings(), tools, directory / "episodes").run_async(root, "saved-source-failure")
            self.assertEqual(caught.exception.diagnostic["code"], "recorded_source")
            saved = list((directory / "episode-store/episodes").glob("*/result.json"))
            self.assertEqual(len(saved), 1)
            result = json.loads(saved[0].read_text())
            self.assertEqual([item["measurement"]["score"] for item in result["measurements"]], [.357, .3])
            self.assertTrue(all("observation_ref" in item for item in result["measurements"]))
            self.assertFalse(list((directory / "episode-store/episodes").glob("*/parent-report.json")))
            self.assertEqual(len(tools.observations), 3)
            self.assertIsNone(fake.parent_input)


if __name__ == "__main__":
    unittest.main()
