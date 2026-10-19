"""Report-boundary checks; no live models or scientific workflow runs."""

import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from orbital_workflow.bootstrap import use_method_loop
use_method_loop(Path(__file__).resolve().parents[2] / "OpenChia")

from method_loop import EpisodeGoal, EpisodeRequest, ReportContract as UntypedContract

from orbital_workflow.artifacts import Artifacts
from orbital_workflow.boundary_validation import ModelOutputError, parse_json_object
from orbital_workflow.communication import (
    ParentModelInputError, ReportBoundaryError, ReportContract, parent_model_inputs,
    generation_schema, report_contract,
)
from orbital_workflow.runtime import ChildAction, Kind, Workflow, diagnostic_bindings
from orbital_workflow.records import plain
from orbital_workflow.scientific import ScientificBindings, load_settings
from orbital_workflow.score_yield import NumericBand, STATUS_NORMAL, YieldEstimate
from orbital_workflow.smoke import spec
from orbital_workflow.tools import ToolDispatcher


def closed(properties):
    return {"type": "object", "additionalProperties": False,
            "required": list(properties), "properties": properties}


def contract(properties):
    return ReportContract("Choose the next velocity investigation", {},
        {name: "Requested typed scientific information" for name in properties}, closed(properties))


def fields(properties):
    return [{"name": name, "meaning": "Requested typed scientific information", "schema_json": json.dumps(schema)}
            for name, schema in properties.items()]


CURVE = {"type": "array", "items": closed({"vx": {"type": "number"},
                                             "effective_duration": {"type": "number"}})}
TREND = {"type": "string", "enum": ["increasing", "decreasing", "nonmonotonic", "undetermined"]}


class FixtureEstimator:
    """Finite numeric feedback for communication fixtures; no estimator fit."""
    def __init__(self, parameters):
        self.parameters, self.scores = parameters, []

    def observe(self, score):
        self.scores.append(score)
        return self.state()

    def state(self):
        gain = 0. if len(self.scores) >= 2 else 1.
        return YieldEstimate(len(self.scores), NumericBand(gain, gain, gain, STATUS_NORMAL, 0, 0),
                             self.parameters, {"software_fixture_only": True, "fitter_executed": False})


class TypedReportBoundary(unittest.TestCase):
    def test_provider_schema_translation_preserves_local_string_validation(self):
        requested = contract({"quantity": {"type": "string", "format": "identifier"},
            "unit": {"type": ["string", "null"], "format": "unit"},
            "expression": {"type": "string", "format": "mathematical_expression"}})
        exported = generation_schema(requested.value_schema)
        self.assertNotIn("format", exported["properties"]["quantity"])
        self.assertIn("pattern", exported["properties"]["quantity"])
        self.assertIn("sim_time", exported["properties"]["unit"]["enum"])
        self.assertIn(None, exported["properties"]["unit"]["enum"])
        self.assertEqual(requested.value_schema["properties"]["expression"]["format"], "mathematical_expression")
        with self.assertRaises(ReportBoundaryError):
            requested.admit({"quantity": "effective_duration", "unit": "sim_time", "expression": "Here is a paragraph."}, audit_identifiers=())

    def test_bundled_parent_request_compiles_and_its_example_reply_matches(self):
        directory = Path(__file__).resolve().parents[1] / "examples" / "communication"
        request = parse_json_object((directory / "parent-request.json").read_text())
        requested = report_contract(request["report_decision"], {}, request["report_fields"])
        reply = parse_json_object((directory / "child-report.json").read_text())
        self.assertEqual(requested.admit(reply, audit_identifiers=()).as_record(), reply)
        self.assertEqual(requested.as_record(), parse_json_object((directory / "compiled-contract.json").read_text()))

    def test_parent_selects_typed_information_and_strings_keep_defined_roles(self):
        properties = {"curve": CURVE, "trend": TREND,
            "velocity": {"type": ["array", "null"], "items": {"type": "number"}, "minItems": 2, "maxItems": 2},
            "quantity": {"type": "string", "format": "identifier"},
            "unit": {"type": "string", "format": "unit"},
            "relationship": {"type": ["string", "null"], "format": "mathematical_expression"}}
        requested = report_contract("Choose a smaller velocity neighborhood", {}, fields(properties))
        data = {"curve": [{"vx": -.1, "effective_duration": 2}, {"vx": 0, "effective_duration": 5},
                          {"vx": .1, "effective_duration": 3}],
                "trend": "nonmonotonic", "velocity": [0, 1], "quantity": "effective_duration", "unit": "sim_time",
                "relationship": "sqrt(1/r)"}
        report = requested.admit(data, audit_identifiers=())
        self.assertEqual(report.as_record(), data)
        data["relationship"] = None
        data["velocity"] = None
        self.assertEqual(requested.admit(data, audit_identifiers=()).values["relationship"], None)
        self.assertEqual(ReportContract.from_record(requested.as_record()).as_record(), requested.as_record())

    def test_parent_cannot_request_open_text_at_any_depth(self):
        unsafe = [{"type": "string"},
            {"type": "array", "items": {"type": "string"}},
            {"type": "array", "items": closed({"notes": {"type": "string"}})},
            {"type": "object", "additionalProperties": True},
            {"type": "array"},
            {"type": "string", "format": "made_up_text_type"},
            {"type": "string", "enum": ["Here is a paragraph about the trajectory."]},
            {"type": "number", "anyOf": [{"type": "string"}]},
            {"type": "array", "items": {"type": "number"}, "const": ["paragraph"]},
            {"$ref": "https://example.test/open-schema"}]
        for schema in unsafe:
            with self.subTest(schema=schema), self.assertRaises(ReportBoundaryError):
                contract({"information": schema})

    def test_paragraphs_extra_fields_encoded_json_and_wrong_numeric_types_cannot_cross(self):
        requested = contract({"curve": CURVE, "trend": TREND})
        valid = {"curve": [{"vx": 0, "effective_duration": 0}], "trend": "undetermined"}
        unsafe = [
            {**valid, "trend": "The result looks promising. Please explore more."},
            {**valid, "summary": "Here is my interpretation."},
            {**valid, "curve": [{"vx": 0, "effective_duration": 0, "notes": "Extra prose"}]},
            {**valid, "curve": [{"vx": True, "effective_duration": 0}]},
            {**valid, "curve": [{"vx": 0, "effective_duration": float("nan")}]},
            {**valid, "curve": json.dumps(valid["curve"])},
        ]
        for value in unsafe:
            with self.subTest(value=value), self.assertRaises(ReportBoundaryError):
                requested.admit(value, audit_identifiers=())
        for value in ('{"summary":"paragraph"}', "This is a paragraph.", '"paragraph"'):
            with self.subTest(value=value), self.assertRaises(ReportBoundaryError):
                contract({"expression": {"type": "string", "format": "mathematical_expression"}}).admit(
                    {"expression": value}, audit_identifiers=())
        for value in ("a paragraph with spaces", '{"data":1}'):
            with self.subTest(value=value), self.assertRaises(ReportBoundaryError):
                contract({"name": {"type": "string", "format": "identifier"}}).admit(
                    {"name": value}, audit_identifiers=())

    def test_copied_identity_guard_and_selected_report_guard_reach_model_inputs(self):
        requested = contract({"quantity": {"type": "string", "format": "identifier"}})
        with self.assertRaisesRegex(ValueError, "child audit identity"):
            requested.admit({"quantity": "artifact_private"}, audit_identifiers=("artifact_private",))
        report = requested.admit({"quantity": "effective_duration"}, audit_identifiers=("artifact_private",))
        view = SimpleNamespace(child_reports=(report,))
        with self.assertRaises(ParentModelInputError):
            parent_model_inputs(view, {"bypass": "artifact_private"}, reports=(report,))
        with self.assertRaises(ParentModelInputError):
            parent_model_inputs(view, {"child_reports": []}, reports=(report,))
        copied = requested.admit({"quantity": "effective_duration"}, audit_identifiers=())
        with self.assertRaises(ParentModelInputError):
            parent_model_inputs(view, {}, reports=(copied,))
        data = parent_model_inputs(view, {"current_vx": 0}, reports=(report,))
        self.assertEqual(data["child_reports"], [{"quantity": "effective_duration"}])

    def test_copied_json_parser_preserves_format_failures_without_repair(self):
        for text, category in (("{\"x\":1,\"x\":2}", "duplicate_json_key"),
                               ("{\"x\":NaN}", "nonfinite_json_number"),
                               ("{\"x\":1e999}", "nonfinite_json_number"),
                               ("[]", "non_object_json")):
            with self.subTest(text=text), self.assertRaises(ModelOutputError) as failure:
                parse_json_object(text)
            self.assertEqual(failure.exception.diagnostic["category"], category)
            self.assertEqual(failure.exception.raw_response, text)

    def test_runtime_does_not_allow_an_untyped_child_invocation(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            child = spec(Kind.MATH, "child", "Boundary fixture", [])
            action = ChildAction(child, UntypedContract("Fixture", {}, {"notes": "Free text"}),
                lambda *args: None, lambda *args: {"notes": "paragraph"})
            root = spec(Kind.ROOT, "root", "Boundary fixture", [action])
            workflow = Workflow(diagnostic_bindings(), ToolDispatcher(Artifacts(directory / "objects")), directory / "episodes")
            with self.assertRaises(ReportBoundaryError):
                workflow.run(root, "untyped-boundary-test")
            self.assertFalse(list((directory / "episodes").glob("*.json")))


class ScientificReportIntegration(unittest.IsolatedAsyncioTestCase):
    async def finish_fixture(self, binding, action, request, evidence):
        # A child-owned closing component fixture, with no fitter or provider.
        path = ((Kind.ROOT, "fixture"), (Kind.SIMULATION, "child"))
        binding.controllers[path] = SimpleNamespace(model_state=lambda: {"units": 1}, history=[],
                                                     own_observations=plain(evidence.findings))
        record = SimpleNamespace(path=path, scope_level=Kind.SIMULATION, goal=request.goal,
            request=request, unit_records=(), ended_by="yield_stop", end_reason="", units_consumed=1,
            episode_id="fixture_episode")
        completed = await binding._finish_form(record, evidence, {}, action.report_contract.interpretation_schema())
        return action.synthesize_report(completed, None, request)

    async def test_parent_requested_cycle_information_is_available_to_the_report_composer(self):
        from orbital_workflow.credit import Evidence
        from method_loop import EpisodeCompletion

        class Composer:
            async def complete(self, episode_id, role, instructions, context, schema):
                cycles = context["own_tool_observations"][0]["measurements"]["persistence_measurement"]["cycles"]
                return {"cycle_similarities": [cycle["similarity"] for cycle in cycles]}

        with tempfile.TemporaryDirectory() as directory:
            binding = ScientificBindings(load_settings(Path(__file__).resolve().parents[1] / "study.toml"),
                Composer(), ToolDispatcher(Artifacts(Path(directory))))
            request = {"child_kind": Kind.SIMULATION, "objective": "Return recurrence changes by cycle",
                "child_assignment_json": '{"credit_target":"new"}', "report_decision": "Locate a recurrence disruption",
                "report_fields": fields({"cycle_similarities": {"type": "array", "items": {"type": "number"}}})}
            action = binding.child(request, SimpleNamespace(path=((Kind.ROOT, "fixture"),), units_consumed=0))
            result = Evidence((), ({"operation": "sim.run", "measurements": {
                "persistence_measurement": {"cycles": [{"similarity": .9}, {"similarity": .4}]}}},))
            goal = EpisodeGoal.root(objective=action.spec.objective, result_contract={})
            child_request = EpisodeRequest(goal, action.spec.assignment, action.report_contract)
            reply = await self.finish_fixture(binding, action, child_request, result)
            self.assertEqual(reply, {"cycle_similarities": [.9, .4]})

    async def test_report_composer_receives_inherited_anchor_without_widening_parent_inputs(self):
        from orbital_workflow.credit import Evidence
        from method_loop import EpisodeCompletion

        class Composer:
            context = None

            async def complete(self, episode_id, role, instructions, context, schema):
                self.context = context
                return {"best_score": context["assignment"]["anchor_score"],
                        "velocity": context["assignment"]["anchor_velocity"]}

        with tempfile.TemporaryDirectory() as directory:
            composer = Composer()
            binding = ScientificBindings(load_settings(Path(__file__).resolve().parents[1] / "study.toml"),
                composer, ToolDispatcher(Artifacts(Path(directory))))
            assignment = {"credit_target": "new", "anchor_velocity": [0.0, 1.495], "anchor_score": 1.1996493280889582e-64}
            action = binding.child({"child_kind": Kind.SIMULATION,
                "objective": "Compare the inherited anchor with new local observations",
                "child_assignment_json": json.dumps(assignment),
                "report_decision": "Choose the best anchor or newly measured velocity",
                "report_fields": fields({"best_score": {"type": "number"}, "velocity": {
                    "type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2}})},
                SimpleNamespace(path=((Kind.ROOT, "fixture"),), units_consumed=1))
            parent_goal = EpisodeGoal.root(objective="Find better complete-model recurrence",
                                          result_contract={"result": "scored_findings"})
            child_goal = EpisodeGoal.child(parent_goal, objective=action.spec.objective,
                                           result_contract={"result": "local_comparison"})
            child_request = EpisodeRequest(child_goal, action.spec.assignment, action.report_contract)
            result = Evidence((), ({"operation": "sim.run", "measurements": {
                "score": 1.1351019262107581e-70, "initial_state": [1.0, 0.0, 0.0, 1.4945]}},),
                ("artifact_private",))
            reply = await self.finish_fixture(binding, action, child_request, result)
            self.assertEqual(composer.context["assignment"], assignment)
            self.assertEqual(composer.context["objective"], child_goal.objective)
            self.assertEqual(composer.context["task_context"]["root_objective"], parent_goal.objective)
            self.assertEqual(composer.context["own_tool_observations"][0]["measurements"]["score"], 1.1351019262107581e-70)
            self.assertEqual(set(composer.context), {
                "mode", "episode_kind", "objective", "task_context", "assignment", "parent_report_contract",
                "completion", "controller", "local_credit_history", "own_tool_observations",
                "recorded_form_values", "form_attempt", "child_reports"})
            serialized = json.dumps(composer.context)
            for identifier in ("artifact_private", child_goal.goal_id, parent_goal.goal_id):
                self.assertNotIn(identifier, serialized)

            admitted = action.report_contract.admit(reply, audit_identifiers=("artifact_private",))
            view = SimpleNamespace(child_reports=(admitted,))
            parent_inputs = parent_model_inputs(view, {"credit": assignment["anchor_score"]}, reports=(admitted,))
            self.assertEqual(parent_inputs["child_reports"], [{
                "best_score": assignment["anchor_score"], "velocity": assignment["anchor_velocity"]}])
            self.assertEqual(set(parent_inputs), {"credit", "child_reports"})
            with self.assertRaises(ParentModelInputError):
                parent_model_inputs(view, {"raw_child": "artifact_private"}, reports=(admitted,))
            with self.assertRaises(ReportBoundaryError):
                action.report_contract.admit({**reply, "assignment": assignment}, audit_identifiers=())

    async def run_boundary_fixture(self, report_value):
        class CapturedParentInputs(Exception):
            pass

        class Models:
            parent_context = None
            child_context = None
            report_schema = None
            parent_calls = 0
            rejected_form = None

            async def complete(self, episode_id, role, instructions, context, output_schema):
                if context["mode"] == "form":
                    self.report_schema = output_schema
                    if not context["form_attempt"]:
                        return report_value
                    self.rejected_form = context["form_diagnostic"]
                    return {"circular_speed": 1., "trend": "undetermined"}
                if context["episode_kind"] == Kind.ROOT:
                    self.parent_calls += 1
                    if self.parent_calls == 2:
                        self.parent_context = context
                        raise CapturedParentInputs
                    return {"action": "child", "label": "central-reference", "rationale": "Boundary fixture",
                        "child_kind": Kind.MATH, "objective": "Calculate the central circular reference",
                        "child_assignment_json": '{"credit_target":"new"}', "report_decision": "Choose a reference insertion",
                        "report_fields": fields({"circular_speed": {"type": "number"}, "trend": TREND}),
                        "tool_name": "", "arguments_json": "{}"}
                self.child_context = context
                return {"action": "tool", "label": "circular-calculation", "tool_name": "math.numeric",
                        "arguments_json": '{"operation":"central_circular_reference","radius":1}'}

        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            models = Models()
            settings = load_settings(Path(__file__).resolve().parents[1] / "study.toml")
            # This fixture isolates report delivery, not estimator behavior.
            settings["episodes"][Kind.MATH]["yield"].update(window_size=2, subsample_size=1)
            settings["episodes"][Kind.MATH]["continuation_cost"] = 100
            binding = ScientificBindings(settings, models, ToolDispatcher(Artifacts(directory / "objects")))
            workflow = Workflow(binding.bindings(), binding.tools, directory / "episodes")
            root = binding.spec(Kind.ROOT, "root", "Communication fixture", {})
            with patch("orbital_workflow.credit.ScalarScoreYieldEstimator", FixtureEstimator), \
                 patch("orbital_workflow.score_yield.estimate_score_yield", side_effect=AssertionError("No fit allowed")):
                with self.assertRaises(CapturedParentInputs):
                    await workflow.run_async(root, "typed-boundary-fixture")
            # The child's completed numerical work remains in audit even when
            # a report has a format error. Nothing is a science rejection.
            self.assertTrue(list((directory / "episodes").glob("*.json")))
            return models

    async def test_declared_typed_report_reaches_the_real_next_parent_decision(self):
        models = await self.run_boundary_fixture({"circular_speed": 1.0, "trend": "undetermined"})
        self.assertEqual(models.parent_context["child_reports"], [{"circular_speed": 1.0, "trend": "undetermined"}])
        self.assertEqual(models.report_schema["properties"]["circular_speed"], {"type": "number"})
        self.assertEqual(models.parent_calls, 2)
        self.assertEqual(models.child_context["task_context"]["root_objective"], "Communication fixture")
        parent_request = models.child_context["parent_report_contract"]
        self.assertEqual(set(parent_request["information"]), {"circular_speed", "trend"})
        self.assertEqual(parent_request["decision"], "Choose a reference insertion")

    async def test_prose_response_cannot_reach_the_real_next_parent_decision(self):
        models = await self.run_boundary_fixture({"circular_speed": "The reference speed is one.", "trend": "undetermined"})
        self.assertEqual(models.parent_context["child_reports"], [{"circular_speed": 1., "trend": "undetermined"}])
        self.assertEqual(models.rejected_form, {"category": "report_format", "code": "type", "field": "circular_speed"})


if __name__ == "__main__":
    unittest.main()
