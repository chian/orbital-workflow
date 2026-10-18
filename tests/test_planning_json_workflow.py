"""Malformed encoded proposals are corrected before any Episode acquisition."""

import asyncio
from collections import Counter
from contextlib import nullcontext
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from orbital_workflow.bootstrap import use_method_loop
use_method_loop(Path(__file__).resolve().parents[2] / "OpenChia")

from orbital_workflow.artifacts import Artifacts
from orbital_workflow.boundary_validation import ModelOutputError, parse_json_object
from orbital_workflow.communication import ReportBoundaryError, ReportContract, parent_model_inputs
from orbital_workflow.durable import CachedModels, CachedTools, DurableWorkflow
from orbital_workflow.persistence import PersistenceSettings
from orbital_workflow.records import plain
from orbital_workflow.runtime import Kind
from orbital_workflow.scientific import ScientificBindings, load_settings


CONFIG = Path(__file__).resolve().parents[1] / "study.toml"
RUN_ID = "planning-json-boundary-regression"
# Exact malformed arguments from final006 cache 00b8e43a6140091602ad740f79c6bcfe20e5af93407c7d0ce8d7ba828e590f79.
MALFORMED_ARGUMENTS = '{"expression":"-mu/(2*energy)*(1+sqrt(1+2*energy*(relative_distance*relative_vy)**2/mu**2))","values":{"mu":0.75,"energy":-0.10401693901408415,"relative_distance":1.2,"relative_vy":-1.30025+0.2*1.3975424859373686}}'
MALFORMED_ASSIGNMENT = '{"software_fixture_only": true, "value": 1+2}'
MALFORMED_SCHEMA = '{"type":"number",}'
CORRECT_ARGUMENTS = {
    "expression": "-mu/(2*energy)*(1+sqrt(1+2*energy*(relative_distance*(vy+primary_radius*angular_speed))**2/mu**2))",
    "values": {"mu": .75, "energy": -.10401693901408415, "relative_distance": 1.2,
               "vy": -1.30025, "primary_radius": .2, "angular_speed": 1.3975424859373686}}
ASSIGNMENT = {"software_fixture_only": True}
REPORT_FIELDS = [
    {"name": "apoapsis", "meaning": "Calculated primary-relative two-body reference apoapsis",
     "schema_json": '{"type":"number"}'},
    {"name": "half", "meaning": "Half of the calculated reference apoapsis",
     "schema_json": '{"type":"number"}'},
    {"name": "diagnostic", "meaning": "Arithmetic result code",
     "schema_json": '{"type":"string","enum":["ok"]}'},
]


def diagnostic(text, field, index=None, proposal_index=1):
    try:
        parse_json_object(text)
    except ModelOutputError as error:
        return {"code": "invalid_json", "category": error.diagnostic["category"],
                "field": field, "index": index,
                **{key: error.diagnostic.get(key) for key in ("line", "column", "position")},
                "proposal_index": proposal_index}
    raise AssertionError("Fixture must contain malformed JSON")


class CorrectingModelFixture:
    """Return explicit corrections; the binding must not evaluate bad JSON."""

    def __init__(self, tools):
        self.tools = tools
        self.corrections, self.next_decisions = [], []

    async def release(self, episode_id):
        pass

    async def complete(self, episode_id, role, instructions, payload, schema):
        context = payload["current"]
        if episode_id.startswith("report-"):
            first, second = context["observations"]
            return {"apoapsis": first["measurements"]["value"],
                    "half": second["measurements"]["value"],
                    "diagnostic": second["measurements"]["diagnostic"]["code"]}

        issue = context.get("action_request_diagnostic")
        if issue:
            self.corrections.append((episode_id, context, payload["previous_visible_exchanges"], self.tools.fresh_calls))
            if context["controller"]["units"] != 0:
                raise AssertionError("Invalid proposal manufactured an acquired unit")

        response = {"action": "", "label": "reference-arithmetic", "rationale": "software_fixture",
            "tool_name": "", "arguments_json": "{}", "child_kind": "", "objective": "",
            "child_assignment_json": "{}", "report_decision": "", "report_fields": []}
        if context["episode_kind"] == Kind.ROOT:
            fields = [dict(field) for field in REPORT_FIELDS]
            assignment = json.dumps(ASSIGNMENT)
            if context["controller"]["units"] == 0:
                if issue is None:
                    assignment = MALFORMED_ASSIGNMENT
                elif issue["field"] == "child_assignment_json":
                    if issue != diagnostic(MALFORMED_ASSIGNMENT, "child_assignment_json"):
                        raise AssertionError("Wrong assignment diagnostic")
                    fields[0]["schema_json"] = MALFORMED_SCHEMA
                elif issue != diagnostic(MALFORMED_SCHEMA, "report_fields.schema_json", 0, 2):
                    raise AssertionError("Wrong report-field diagnostic")
            response.update(action="child", child_kind=Kind.MATH,
                objective="Calculate the supplied two-body reference and its half",
                child_assignment_json=assignment, report_decision="Use the calculated numerical reference",
                report_fields=fields)
            return response

        position = context["controller"]["units"]
        if position == 0:
            if issue is None:
                arguments = MALFORMED_ARGUMENTS
            elif issue == diagnostic(MALFORMED_ARGUMENTS, "arguments_json", proposal_index=1):
                # Repeating exactly the same bad proposal must not create a
                # cache-key loop; the model must be asked again at the same unit.
                arguments = MALFORMED_ARGUMENTS
            else:
                if issue != diagnostic(MALFORMED_ARGUMENTS, "arguments_json", proposal_index=2):
                    raise AssertionError("Wrong actual malformed-action diagnostic")
                arguments = json.dumps(CORRECT_ARGUMENTS)
        elif position == 1:
            if issue is not None:
                raise AssertionError("Prior planning diagnostic leaked into next acquisition")
            self.next_decisions.append(context)
            first = context["own_tool_observations"][0]["measurements"]
            arguments = json.dumps({"expression": "apoapsis/2", "values": {"apoapsis": first["value"]}})
        else:
            raise AssertionError("Numerical fixture did not yield-stop after two acquisitions")
        response.update(action="tool", tool_name="math.arithmetic", arguments_json=arguments)
        return response


class NoFreshModels:
    async def complete(self, *args, **kwargs):
        raise AssertionError("Completed reconstruction must use saved model responses")


class PlanningJsonWorkflow(unittest.TestCase):
    def test_unrelated_errors_propagate_without_planning_retry_or_acquisition(self):
        model_error = ModelOutputError("provider model-output error", category="malformed_json", raw_response="{}")
        construction_error = ModelOutputError("unrelated construction error", category="malformed_json",
                                               raw_response="unrelated_boundary_payload")
        for failure in ("model", "schema_type", "unrelated_construction"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                tools = CachedTools(Artifacts(directory / "objects"), PersistenceSettings(), directory / "tool-cache")

                class FailingProposalFixture:
                    calls = 0

                    async def complete(self, *args):
                        self.calls += 1
                        if failure == "model":
                            raise model_error
                        fields = [dict(field) for field in REPORT_FIELDS]
                        if failure == "schema_type":
                            # Valid JSON but invalid declared report type: this
                            # remains the existing typed communication error.
                            fields[0]["schema_json"] = '{"type":"string"}'
                        return {"action": "child", "label": "unrelated-error", "rationale": "software_fixture",
                            "tool_name": "", "arguments_json": "{}", "child_kind": Kind.MATH,
                            "objective": "Reference arithmetic", "child_assignment_json": "{}",
                            "report_decision": "Use calculated values", "report_fields": fields}

                provider = FailingProposalFixture()
                models = CachedModels(provider, directory / "model-cache")
                binding = ScientificBindings(load_settings(CONFIG), models, tools)
                spec = binding.spec(Kind.ROOT, "unrelated-error", "Exercise an unrelated error boundary", ASSIGNMENT)
                construction = (patch.object(binding, "child", side_effect=construction_error)
                                if failure == "unrelated_construction" else nullcontext())
                expected = ReportBoundaryError if failure == "schema_type" else ModelOutputError
                with construction, self.assertRaises(expected) as caught:
                    asyncio.run(DurableWorkflow(binding.bindings(), tools, directory / "episodes").run_async(spec, RUN_ID))
                if failure != "schema_type":
                    self.assertIs(caught.exception, model_error if failure == "model" else construction_error)
                self.assertEqual(provider.calls, 1)
                self.assertEqual(tools.fresh_calls, 0)
                self.assertFalse(list((directory / "episodes" / "units").glob("*.json")))
                self.assertEqual(models.fresh_calls, 0 if failure == "model" else 1)

    def test_invalid_proposals_correct_before_acquisition_and_replay_without_extra_turns(self):
        settings = load_settings(CONFIG)
        for local in settings["episodes"].values():
            # Minimum fit information/cost fixture; no source cap or fake gain.
            local["yield"] = {"window_size": 2, "subsample_size": 1, "uncertainty_alpha": .05}
            local["continuation_cost"] = 100.
        self.assertEqual(diagnostic(MALFORMED_ARGUMENTS, "arguments_json"), {
            "code": "invalid_json", "category": "malformed_json", "field": "arguments_json", "index": None,
            "line": 1, "column": 190, "position": 189, "proposal_index": 1})

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            tools = CachedTools(Artifacts(directory / "objects"), PersistenceSettings(), directory / "tool-cache")

            def root(binding):
                return binding.spec(Kind.ROOT, "planning-json", "Obtain typed reference calculations", ASSIGNMENT)

            class InterruptAfterUnit(DurableWorkflow):
                def _record_unit(self, item, contribution, view):
                    super()._record_unit(item, contribution, view)
                    raise InterruptedError("Software interruption after first valid acquired calculation")

            with patch("orbital_workflow.tools.integrate", side_effect=AssertionError("Planning correction requires no simulation")) as simulate, patch(
                    "orbital_workflow.scientific.parent_model_inputs", wraps=parent_model_inputs) as guard:
                first_provider = CorrectingModelFixture(tools)
                first_models = CachedModels(first_provider, directory / "model-cache")
                first = ScientificBindings(settings, first_models, tools)
                with self.assertRaises(InterruptedError):
                    asyncio.run(InterruptAfterUnit(first.bindings(), tools, directory / "episodes").run_async(root(first), RUN_ID))
                self.assertEqual(tools.fresh_calls, 1)
                self.assertEqual(first_models.fresh_calls, 6)
                self.assertEqual(len(first_provider.corrections), 4)
                self.assertTrue(all(count == 0 for _, _, _, count in first_provider.corrections))
                self.assertEqual(len(list((directory / "episodes" / "units").glob("*.json"))), 1)

                prefix_file = next((directory / "episodes" / "units").glob("*.json"))
                original_prefix = prefix_file.read_bytes()
                prefix_models = CachedModels(NoFreshModels(), directory / "model-cache")
                prefix_binding = ScientificBindings(settings, prefix_models, tools)
                with self.assertRaises(InterruptedError):
                    asyncio.run(InterruptAfterUnit(prefix_binding.bindings(), tools, directory / "episodes").run_async(
                        root(prefix_binding), RUN_ID))
                self.assertEqual(prefix_models.fresh_calls, 0)
                self.assertEqual(prefix_models.replayed_calls, 6)
                self.assertEqual(tools.fresh_calls, 1)
                self.assertEqual(prefix_file.read_bytes(), original_prefix)

                provider = CorrectingModelFixture(tools)
                models = CachedModels(provider, directory / "model-cache")
                binding = ScientificBindings(settings, models, tools)
                record, result = asyncio.run(DurableWorkflow(binding.bindings(), tools, directory / "episodes").run_async(
                    root(binding), RUN_ID))
                self.assertEqual(models.replayed_calls, 6)
                self.assertEqual(models.fresh_calls, 8)
                self.assertEqual(tools.fresh_calls, 2)
                self.assertEqual(len(provider.next_decisions), 2)
                self.assertEqual(len(provider.corrections), 2)
                self.assertTrue(all(count == 2 for _, _, _, count in provider.corrections))
                self.assertEqual(record.controller_state.record["credit"], 0)
                self.assertEqual(result.measurements, ())

                completed_models = CachedModels(NoFreshModels(), directory / "model-cache")
                completed = ScientificBindings(settings, completed_models, tools)
                replay, replay_result = asyncio.run(DurableWorkflow(completed.bindings(), tools, directory / "episodes").run_async(
                    root(completed), RUN_ID))
                self.assertEqual(replay.as_record(), record.as_record())
                self.assertEqual(replay_result.as_record(), result.as_record())
                self.assertEqual(completed_models.fresh_calls, 0)
                self.assertEqual(completed_models.replayed_calls, 14)
                self.assertEqual(tools.fresh_calls, 2)
                simulate.assert_not_called()
                # Both interrupted prefix traversals make6 requests. Subsequent
                # traversals make12 policy requests each (plus2 composer calls).
                self.assertEqual(guard.call_count, 36)

            for _, context, history, _ in [*first_provider.corrections, *provider.corrections]:
                issue = context["action_request_diagnostic"]
                self.assertEqual(set(issue), {"code", "category", "field", "index", "line", "column", "position", "proposal_index"})
                self.assertEqual(context["controller"]["units"], 0)
                self.assertEqual(context["controller"]["credit"], 0)
                self.assertEqual(context["own_tool_observations"], [])
                self.assertTrue(history)
                self.assertEqual(history[-1]["context"]["controller"], context["controller"])

            caches = [json.loads(path.read_text()) for path in (directory / "model-cache").glob("*.json")]
            self.assertEqual(len(caches), 14)
            malformed = [row for row in caches if row["response"].get("arguments_json") == MALFORMED_ARGUMENTS]
            self.assertEqual(len(malformed), 4)
            self.assertTrue(all(row["request"]["context"]["controller"]["units"] == 0 for row in malformed))
            self.assertEqual(sorted(Counter(row["request"]["episode"] for row in malformed).values()), [2, 2])
            for episode in {row["request"]["episode"] for row in malformed}:
                repeated = [row for row in malformed if row["request"]["episode"] == episode]
                self.assertEqual(sum("action_request_diagnostic" in row["request"]["context"] for row in repeated), 1)
            self.assertEqual(sum(row["response"].get("child_assignment_json") == MALFORMED_ASSIGNMENT for row in caches), 1)
            self.assertEqual(sum(any(field["schema_json"] == MALFORMED_SCHEMA
                for field in row["response"].get("report_fields", [])) for row in caches), 1)
            self.assertEqual(Counter(row["request"]["context"]["action_request_diagnostic"]["field"] for row in caches
                if "action_request_diagnostic" in row["request"]["context"]),
                {"arguments_json": 4, "child_assignment_json": 1, "report_fields.schema_json": 1})

            values = CORRECT_ARGUMENTS["values"]
            relative_vy = values["vy"] + values["primary_radius"] * values["angular_speed"]
            expected = -values["mu"] / (2 * values["energy"]) * (1 + math.sqrt(
                1 + 2 * values["energy"] * (values["relative_distance"] * relative_vy) ** 2 / values["mu"] ** 2))
            rows = [json.loads(path.read_text()) for path in (directory / "episodes").glob("episode_*.json")]
            self.assertEqual(Counter(row["scope_level"] for row in rows), {Kind.ROOT: 1, Kind.MATH: 2})
            self.assertEqual(sum(len(row["units"]) for row in rows), 6)
            self.assertEqual(len(list((directory / "episodes" / "units").glob("*.json"))), 6)
            for row in rows:
                self.assertEqual(row["ended_by"], "yield_stop")
                self.assertEqual(row["units_consumed"], 2)
                self.assertEqual(row["controller_state"]["yield_estimate"]["turns"], 2)
                self.assertTrue(row["controller_state"]["continuation"]["stop"])
                for unit in row["units"]:
                    self.assertEqual(unit["controller_step"]["credit"], 0)
                    self.assertEqual(unit["controller_step"]["marginal_credit"], 0)
                    self.assertEqual(unit["controller_input"]["measurements"], [])
                    if unit["child"]:
                        contract = ReportContract.from_record(unit["child"]["request"]["report_contract"])
                        report = contract.admit(unit["episode_update"]["report"],
                            audit_identifiers=tuple(unit["child_result"]["artifacts"]))
                        self.assertEqual(plain(report.values), {"apoapsis": expected, "half": expected / 2, "diagnostic": "ok"})
                    else:
                        request = tools.store.json(unit["controller_input"]["artifacts"][0])
                        self.assertEqual(request["tool"], "math.arithmetic")
                        self.assertIn(request["arguments"]["expression"], [CORRECT_ARGUMENTS["expression"], "apoapsis/2"])
                        self.assertEqual(unit["controller_input"]["findings"][0]["measurements"]["diagnostic"], {"code": "ok"})


if __name__ == "__main__":
    unittest.main()
