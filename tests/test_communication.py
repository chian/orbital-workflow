"""Report-boundary checks; no live models or scientific workflow runs."""

import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from orbital_workflow.bootstrap import use_method_loop
use_method_loop(Path(__file__).resolve().parents[2] / "OpenChia")

from method_loop import ReportContract as UntypedContract

from orbital_workflow.artifacts import Artifacts
from orbital_workflow.boundary_validation import ModelOutputError, parse_json_object
from orbital_workflow.communication import (
    ParentModelInputError, ReportBoundaryError, ReportContract, parent_model_inputs,
    generation_schema, report_contract,
)
from orbital_workflow.runtime import ChildAction, Kind, Workflow, diagnostic_bindings
from orbital_workflow.scientific import ScientificBindings, load_settings
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
    async def test_parent_requested_cycle_information_is_available_to_the_report_composer(self):
        from orbital_workflow.credit import Evidence
        from method_loop import EpisodeCompletion

        class Composer:
            async def complete(self, episode_id, role, instructions, context, schema):
                cycles = context["observations"][0]["measurements"]["persistence_measurement"]["cycles"]
                return {"cycle_similarities": [cycle["similarity"] for cycle in cycles]}

        with tempfile.TemporaryDirectory() as directory:
            binding = ScientificBindings(load_settings(Path(__file__).resolve().parents[1] / "study.toml"),
                Composer(), ToolDispatcher(Artifacts(Path(directory))))
            request = {"child_kind": Kind.SIMULATION, "objective": "Return recurrence changes by cycle",
                "child_assignment_json": "{}", "report_decision": "Locate a recurrence disruption",
                "report_fields": fields({"cycle_similarities": {"type": "array", "items": {"type": "number"}}})}
            action = binding.child(request, SimpleNamespace(path=((Kind.ROOT, "fixture"),), units_consumed=0))
            result = Evidence((), ({"operation": "sim.run", "measurements": {
                "persistence_measurement": {"cycles": [{"similarity": .9}, {"similarity": .4}]}}},))
            reply = await action.synthesize_report(result, EpisodeCompletion("yield_stop", "", 1), None)
            self.assertEqual(reply, {"cycle_similarities": [.9, .4]})

    async def run_boundary_fixture(self, report_value):
        class CapturedParentInputs(Exception):
            pass

        class Models:
            parent_context = None
            report_schema = None
            parent_calls = 0

            async def complete(self, episode_id, role, instructions, context, output_schema):
                if episode_id.startswith("report-"):
                    self.report_schema = output_schema
                    return report_value
                if context["episode_kind"] == Kind.ROOT:
                    self.parent_calls += 1
                    if self.parent_calls == 2:
                        self.parent_context = context
                        raise CapturedParentInputs
                    return {"action": "child", "label": "central-reference", "rationale": "Boundary fixture",
                        "child_kind": Kind.MATH, "objective": "Calculate the central circular reference",
                        "child_assignment_json": "{}", "report_decision": "Choose a reference insertion",
                        "report_fields": fields({"circular_speed": {"type": "number"}, "trend": TREND}),
                        "tool_name": "", "arguments_json": "{}"}
                return {"action": "tool", "label": "circular-calculation", "tool_name": "math.numeric",
                        "arguments_json": '{"operation":"central_circular_reference","radius":1}'}

        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            models = Models()
            settings = load_settings(Path(__file__).resolve().parents[1] / "study.toml")
            binding = ScientificBindings(settings, models, ToolDispatcher(Artifacts(directory / "objects")))
            workflow = Workflow(binding.bindings(), binding.tools, directory / "episodes")
            root = binding.spec(Kind.ROOT, "root", "Communication fixture", {})
            expected_error = CapturedParentInputs if isinstance(report_value.get("circular_speed"), (int, float)) else ReportBoundaryError
            with self.assertRaises(expected_error):
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

    async def test_prose_response_cannot_reach_the_real_next_parent_decision(self):
        models = await self.run_boundary_fixture({"circular_speed": "The reference speed is one.", "trend": "undetermined"})
        self.assertIsNone(models.parent_context)
        self.assertEqual(models.parent_calls, 1)


if __name__ == "__main__":
    unittest.main()
