"""Out-of-window feedback remains a local acquisition through durable replay."""

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
from orbital_workflow.records import plain
from orbital_workflow.runtime import Kind
from orbital_workflow.scientific import ScientificBindings, load_settings
from orbital_workflow.simulation import integrate
from orbital_workflow.storage import read_index
from verify_scored_run import Verifier


CONFIG = Path(__file__).resolve().parents[1] / "study.toml"
RUN_ID = "request-diagnostic-boundary-regression"
REPORT_FIELDS = [
    {"name": "feedback_code", "meaning": "Observed request diagnostic code",
     "schema_json": '{"type":"string","enum":["outside_observation_window"]}'},
    {"name": "requested_interval", "meaning": "Requested interval receiving feedback",
     "schema_json": '{"type":"array","items":{"type":"number"},"minItems":2,"maxItems":2}'},
    {"name": "observation_window", "meaning": "Fixed physical observation window",
     "schema_json": '{"type":"array","items":{"type":"number"},"minItems":2,"maxItems":2}'},
    {"name": "run_index", "meaning": "Completed local simulation observation index",
     "schema_json": '{"type":"integer"}'},
    {"name": "score", "meaning": "Actual simulator recurrence score",
     "schema_json": '{"type":"number"}'},
]


class DiagnosticModelFixture:
    """Choose a valid acquisition after seeing actual invalid-request feedback.

    The software fixture does not emit exhaustion or a stopping action. The
    numerical controller alone decides when each Episode has sufficient units.
    """

    def __init__(self):
        self.followup_inputs = []

    async def release(self, episode_id):
        pass

    async def complete(self, episode_id, role, instructions, payload, schema):
        context = payload["current"]
        if episode_id.startswith("report-"):
            feedback, simulation = context["observations"]
            diagnostic = feedback["measurements"]
            return {"feedback_code": diagnostic["code"],
                    "requested_interval": diagnostic["requested_interval"],
                    "observation_window": diagnostic["observation_window"],
                    "run_index": simulation["run_index"],
                    "score": simulation["measurements"]["score"]}

        response = {"action": "", "label": "request-feedback", "rationale": "software_fixture",
            "tool_name": "", "arguments_json": "{}", "child_kind": "", "objective": "",
            "child_assignment_json": "{}", "report_decision": "", "report_fields": []}
        if context["episode_kind"] == Kind.ROOT:
            response.update(action="child", child_kind=Kind.SIMULATION,
                objective="Use request feedback to obtain one complete-model trajectory observation",
                child_assignment_json=json.dumps(context["assignment"]),
                report_decision="Use the measured score and structured request feedback",
                report_fields=REPORT_FIELDS)
            return response

        position = context["controller"]["units"]
        if position not in (0, 1):
            raise AssertionError("Numerical fixture controller did not stop after two acquisitions")
        horizon = context["fixed_problem"]["observation_window"][1]
        if position == 1:
            expected = {"code": "outside_observation_window",
                        "requested_interval": [0., horizon + 1.],
                        "observation_window": [0., horizon]}
            if context["own_tool_observations"] != [
                {"operation": "sim.request_diagnostic", "measurements": expected}]:
                raise AssertionError("Next policy turn did not receive exact diagnostic feedback")
            self.followup_inputs.append(context)
        response.update(action="tool", tool_name="sim.run", arguments_json=json.dumps({
            "trial": 1, "a": 0., "sigma": .002, "vx": 0., "vy": 1.,
            "end": horizon + 1. if position == 0 else 20.}))
        return response


class NoFreshModels:
    async def complete(self, *args, **kwargs):
        raise AssertionError("Completed reconstruction must use saved model responses")


class SimulationDiagnosticWorkflow(unittest.TestCase):
    def test_feedback_then_simulation_yield_typed_report_and_replay_once(self):
        settings = load_settings(CONFIG)
        # Short estimator/cost fixture, not a source cap or a scientific gate.
        # Keep the actual scenario and physical window unchanged.
        for local in settings["episodes"].values():
            local["yield"] = {"window_size": 2, "subsample_size": 1, "uncertainty_alpha": .05}
            local["continuation_cost"] = 100.

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            tools = CachedTools(Artifacts(directory / "objects"), PersistenceSettings(), directory / "tool-cache")

            def root(binding):
                return binding.spec(Kind.ROOT, "request-diagnostic", "Obtain scored evidence after request feedback",
                                    {"software_fixture_only": True})

            first_binding = ScientificBindings(settings,
                CachedModels(DiagnosticModelFixture(), directory / "model-cache"), tools)
            horizon = settings["study"]["horizon"]
            with self.assertRaisesRegex(ValueError, "study fixes the physical observation window"):
                first_binding.simulation_arguments({"observation_window": [0., horizon + 1.]})
            self.assertEqual(first_binding.simulation_arguments({
                "observation_window": [0., horizon]})["observation_window"], (0., horizon))

            interrupted = []
            class InterruptAfterDiagnostic(DurableWorkflow):
                def _record_unit(self, item, contribution, view):
                    super()._record_unit(item, contribution, view)
                    interrupted.append(view.controller_input.as_record())
                    raise InterruptedError("Software interruption after durable request feedback")

            with patch("orbital_workflow.tools.integrate", wraps=integrate) as simulate:
                with self.assertRaises(InterruptedError):
                    asyncio.run(InterruptAfterDiagnostic(first_binding.bindings(), tools, directory / "episodes").run_async(
                        root(first_binding), RUN_ID))
                simulate.assert_not_called()
                self.assertEqual(tools.fresh_calls, 1)
                self.assertEqual(interrupted[0]["measurements"], [])
                self.assertNotIn("run_index", interrupted[0]["findings"][0])
                self.assertEqual(read_index(directory), ([], []))
                self.assertEqual(first_binding.completed_runs, {})

                provider = DiagnosticModelFixture()
                models = CachedModels(provider, directory / "model-cache")
                binding = ScientificBindings(settings, models, tools)
                record, result = asyncio.run(DurableWorkflow(binding.bindings(), tools, directory / "episodes").run_async(
                    root(binding), RUN_ID))
                self.assertGreaterEqual(models.replayed_calls, 2)
                self.assertEqual(simulate.call_count, 1)
                self.assertEqual(tools.fresh_calls, 2)
                self.assertEqual(record.units_consumed, 2)
                self.assertEqual(record.ended_by, "yield_stop")
                self.assertEqual(len(result.measurements), 1)
                score = result.measurements[0]["measurement"]["score"]
                self.assertGreater(score, 0)
                self.assertEqual(record.controller_state.record["credit"], score)
                self.assertEqual(record.controller_state.record["marginal_credit"], 0)
                self.assertEqual(binding.completed_runs, {})

                replay_models = CachedModels(NoFreshModels(), directory / "model-cache")
                replay_binding = ScientificBindings(settings, replay_models, tools)
                replay, replay_result = asyncio.run(DurableWorkflow(replay_binding.bindings(), tools, directory / "episodes").run_async(
                    root(replay_binding), RUN_ID))
                self.assertEqual(replay.as_record(), record.as_record())
                self.assertEqual(replay_result.as_record(), result.as_record())
                self.assertEqual(replay_models.fresh_calls, 0)
                self.assertEqual(tools.fresh_calls, 2)
                self.assertEqual(simulate.call_count, 1)

            self.assertEqual(len(provider.followup_inputs), 2)
            rows, warnings = read_index(directory)
            self.assertEqual(warnings, [])
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["summary"]["score"], score)
            records = [json.loads(path.read_text()) for path in (directory / "episodes").glob("episode_*.json")]
            self.assertEqual(Counter(row["scope_level"] for row in records), {Kind.ROOT: 1, Kind.SIMULATION: 2})
            for row in records:
                state = row["controller_state"]
                self.assertEqual(row["ended_by"], "yield_stop")
                self.assertTrue(state["continuation"]["stop"])
                self.assertEqual(row["units_consumed"], 2)
                self.assertEqual(state["yield_estimate"]["turns"], 2)
                self.assertEqual(state["credit"], score)
                if row["scope_level"] == Kind.SIMULATION:
                    feedback, run = row["units"]
                    self.assertEqual(feedback["controller_input"]["measurements"], [])
                    self.assertEqual(feedback["controller_step"]["score_assignment"]["received_scores"], [])
                    self.assertEqual(feedback["controller_step"]["marginal_credit"], 0)
                    self.assertEqual(feedback["controller_step"]["yield_estimate"]["turns"], 1)
                    self.assertEqual(run["controller_input"]["findings"][0]["run_index"], 1)
                    self.assertEqual(run["controller_step"]["score_assignment"]["received_scores"], [score])
                    self.assertEqual(run["controller_step"]["marginal_credit"], score)
                    self.assertNotIn("observation_window", run["controller_input"]["measurements"][0]["physical"])
                for unit in row["units"]:
                    if unit["child"]:
                        child = unit["child"]
                        contract = ReportContract.from_record(child["request"]["report_contract"])
                        report = contract.admit(unit["episode_update"]["report"],
                            audit_identifiers=tuple(unit["child_result"]["artifacts"]))
                        self.assertEqual(plain(report.values), {"feedback_code": "outside_observation_window",
                            "requested_interval": [0., horizon + 1.], "observation_window": [0., horizon],
                            "run_index": 1, "score": score})
                        self.assertTrue(child["unit_records_archived"])
                        self.assertEqual(unit["child_result"]["storage_format"], "orbital.result-ref/v1")
                        saved = directory / "episode-store" / "episodes" / child["episode_id"] / "parent-report.json"
                        self.assertEqual(json.loads(saved.read_text()), plain(report.values))

            # Exercise the manual read-only verifier on the actual cached tool
            # records. This fixture intentionally has no live-model provenance
            # and does not claim to be a completed scientific-run verification.
            (directory / "study.toml").write_text(CONFIG.read_text())
            (directory / "manifest.json").write_text(json.dumps({"run_id": RUN_ID}))
            verifier = Verifier(directory)
            verifier.tool_cache()
            self.assertEqual(verifier.discrepancies, [])
            self.assertEqual(verifier.counts["cached_tools"], {"sim.request_diagnostic": 1, "sim.run": 1})
            self.assertEqual(len(verifier.observation_refs), 1)
            self.assertEqual(verifier.checked["request_diagnostic_has_no_score_or_trajectory"], 1)


if __name__ == "__main__":
    unittest.main()
