"""Assigned three-score arithmetic completes through the real Episode boundary."""

import asyncio
from collections import Counter
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from orbital_workflow.bootstrap import use_method_loop
use_method_loop(Path(__file__).resolve().parents[2] / "OpenChia")

from orbital_workflow.artifacts import Artifacts
from orbital_workflow.communication import ReportContract
from orbital_workflow.durable import CachedModels, CachedTools, DurableWorkflow
from orbital_workflow.persistence import PersistenceSettings
from orbital_workflow.runtime import Kind
from orbital_workflow.scientific import ScientificBindings, load_settings


CONFIG = Path(__file__).resolve().parents[1] / "study.toml"
# Supplied values from the stalled question; this test creates no new simulation
# evidence and never treats its arithmetic as a new trajectory score.
VALUES = {"coarse": .16618101298027446, "medium": .1661407076470878,
          "fine": .1661308271558801}
DIFFERENCE = "coarse-fine"
RATIO = "(coarse-medium)/(medium-fine)"
EXPECTED = {"difference": VALUES["coarse"] - VALUES["fine"],
            "ratio": (VALUES["coarse"] - VALUES["medium"]) / (VALUES["medium"] - VALUES["fine"]),
            "diagnostic": "ok"}
ASSIGNMENT = {"software_fixture_only": True, "supplied_scores": VALUES,
              "requested_expressions": [DIFFERENCE, RATIO]}
REPORT_FIELDS = [
    {"name": "difference", "meaning": "Difference between supplied coarse and fine scores",
     "schema_json": '{"type":"number"}'},
    {"name": "ratio", "meaning": "Ratio of the two successive supplied score differences",
     "schema_json": '{"type":"number"}'},
    {"name": "diagnostic", "meaning": "Arithmetic operation diagnostic",
     "schema_json": '{"type":"string","enum":["ok"]}'},
]


class ArithmeticModelFixture:
    """Deterministic model substitute; arithmetic itself executes in the tool.

    The fixture commissions an already-assigned parts question to exercise that
    boundary. It makes no claim that delegation is needed for simple arithmetic.
    No source returns exhaustion or a model-authored stopping decision.
    """

    def __init__(self):
        self.parts_inputs = []

    async def release(self, episode_id):
        pass

    async def complete(self, episode_id, role, instructions, payload, schema):
        context = payload["current"]
        if episode_id.startswith("report-"):
            if context["observations"][0].get("child_report"):
                return context["observations"][-1]["child_report"]
            arithmetic = {item["measurements"]["expression"]: item["measurements"]
                          for item in context["observations"]}
            return {"difference": arithmetic[DIFFERENCE]["value"],
                    "ratio": arithmetic[RATIO]["value"],
                    "diagnostic": arithmetic[RATIO]["diagnostic"]["code"]}

        response = {"action": "", "label": "supplied-score-arithmetic", "rationale": "software_fixture",
            "tool_name": "", "arguments_json": "{}", "child_kind": "", "objective": "",
            "child_assignment_json": "{}", "report_decision": "", "report_fields": []}
        kind = context["episode_kind"]
        if kind == Kind.PARTS:
            self.parts_inputs.append((instructions, context))
            position = context["controller"]["units"]
            if position not in (0, 1):
                raise AssertionError("The fixture's numerical controller did not stop after sufficient information")
            response.update(action="tool", tool_name="math.arithmetic", arguments_json=json.dumps({
                "expression": [DIFFERENCE, RATIO][position],
                "values": context["assignment"]["supplied_scores"]}))
        else:
            response.update(action="child", child_kind=(Kind.MATH if kind == Kind.ROOT else Kind.PARTS),
                objective="Calculate the two requested expressions from the supplied scores",
                child_assignment_json=json.dumps(context["assignment"]),
                report_decision="Use the requested numerical differences", report_fields=REPORT_FIELDS)
        return response


class NoFreshModels:
    async def complete(self, *args, **kwargs):
        raise AssertionError("Completed reconstruction must use saved model responses")


class ArithmeticWorkflow(unittest.TestCase):
    def test_assigned_arithmetic_yields_typed_report_and_replays_without_credit_or_simulations(self):
        settings = load_settings(CONFIG)
        # Short numerical information/cost fixture, not a source/iteration cap.
        # Production settings are neither changed nor written by this test.
        for local in settings["episodes"].values():
            local["yield"] = {"window_size": 2, "subsample_size": 1, "uncertainty_alpha": .05}
            local["continuation_cost"] = 100.0

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            tools = CachedTools(Artifacts(directory / "objects"), PersistenceSettings(), directory / "tool-cache")

            def root(binding):
                return binding.spec(Kind.ROOT, "assigned-arithmetic", "Return the supplied three-score calculation", ASSIGNMENT)

            class InterruptAfterDurableUnit(DurableWorkflow):
                def _record_unit(self, item, contribution, view):
                    super()._record_unit(item, contribution, view)
                    raise InterruptedError("Software interruption after one durable arithmetic acquisition")

            first_models = CachedModels(ArithmeticModelFixture(), directory / "model-cache")
            first_binding = ScientificBindings(settings, first_models, tools)
            with patch("orbital_workflow.tools.integrate", side_effect=AssertionError("Arithmetic needs no simulation")) as simulate:
                with self.assertRaises(InterruptedError):
                    asyncio.run(InterruptAfterDurableUnit(first_binding.bindings(), tools, directory / "episodes").run_async(
                        root(first_binding), "arithmetic-boundary-regression"))
                self.assertEqual(tools.fresh_calls, 1)
                self.assertEqual(first_binding.controllers, {})

                provider = ArithmeticModelFixture()
                restored_models = CachedModels(provider, directory / "model-cache")
                restored_binding = ScientificBindings(settings, restored_models, tools)
                record, result = asyncio.run(DurableWorkflow(restored_binding.bindings(), tools, directory / "episodes").run_async(
                    root(restored_binding), "arithmetic-boundary-regression"))
                self.assertGreaterEqual(restored_models.replayed_calls, 3)
                self.assertEqual(tools.fresh_calls, 2)
                self.assertEqual(record.units_consumed, 2)
                self.assertEqual(record.ended_by, "yield_stop")
                self.assertEqual(record.controller_state.record["credit"], 0)
                self.assertEqual(result.measurements, ())

                replay_models = CachedModels(NoFreshModels(), directory / "model-cache")
                replay_binding = ScientificBindings(settings, replay_models, tools)
                replay, replay_result = asyncio.run(DurableWorkflow(replay_binding.bindings(), tools, directory / "episodes").run_async(
                    root(replay_binding), "arithmetic-boundary-regression"))
                self.assertEqual(replay.as_record(), record.as_record())
                self.assertEqual(replay_result.as_record(), result.as_record())
                self.assertEqual(replay_models.fresh_calls, 0)
                self.assertEqual(tools.fresh_calls, 2)
                simulate.assert_not_called()

            self.assertTrue(provider.parts_inputs)
            for instructions, context in provider.parts_inputs:
                self.assertIn("math.arithmetic", context["available_tools"])
                guidance = " ".join(instructions.split())
                self.assertIn("use math.arithmetic locally", guidance)
                self.assertIn("do not commission another child to repeat the same arithmetic question", guidance)
                self.assertEqual(context["assignment"], ASSIGNMENT)
                self.assertIsNotNone(context["parent_report_contract"])

            records = [json.loads(path.read_text()) for path in (directory / "episodes").glob("episode_*.json")]
            self.assertEqual(Counter(row["scope_level"] for row in records),
                             {Kind.ROOT: 1, Kind.MATH: 2, Kind.PARTS: 4})
            for row in records:
                state = row["controller_state"]
                self.assertEqual(row["ended_by"], "yield_stop")
                self.assertTrue(state["continuation"]["stop"])
                self.assertLessEqual(state["projected_credit"]["upper"], state["continuation_cost"])
                self.assertEqual(row["units_consumed"], 2)
                self.assertEqual(state["yield_estimate"]["turns"], 2)
                self.assertEqual(state["credit"], 0)
                if row["scope_level"] == Kind.PARTS:
                    self.assertTrue(all(unit["controller_input"]["measurements"] == [] for unit in row["units"]))
                    self.assertTrue(all(unit["controller_input"]["findings"][0]["operation"] == "math.arithmetic"
                                        for unit in row["units"]))
                    for unit in row["units"]:
                        evidence = unit["controller_input"]
                        calculation = evidence["findings"][0]["measurements"]
                        self.assertEqual(calculation["diagnostic"], {"code": "ok"})
                        self.assertEqual(tools.store.json(evidence["artifacts"][-1]),
                                         {"operation": "math.arithmetic", "findings": calculation})
                        self.assertEqual(tools.store.json(evidence["artifacts"][0])["arguments"]["values"], VALUES)
                for unit in row["units"]:
                    if unit["child"]:
                        child = unit["child"]
                        contract = ReportContract.from_record(child["request"]["report_contract"])
                        report = contract.admit(unit["episode_update"]["report"],
                            audit_identifiers=tuple(unit["child_result"]["artifacts"]))
                        self.assertEqual(dict(report.values), EXPECTED)
                        self.assertTrue(child["unit_records_archived"])
                        self.assertEqual(unit["child_result"]["storage_format"], "orbital.result-ref/v1")
                        saved = directory / "episode-store" / "episodes" / child["episode_id"] / "parent-report.json"
                        self.assertEqual(json.loads(saved.read_text()), EXPECTED)


if __name__ == "__main__":
    unittest.main()
