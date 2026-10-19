"""Public request failures and completed private diagnostics remain distinct."""

import asyncio
from collections import Counter
from dataclasses import replace
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from orbital_workflow.bootstrap import use_method_loop
use_method_loop(Path(__file__).resolve().parents[2] / "OpenChia")

from method_loop import EpisodeTree
from orbital_workflow.artifacts import Artifacts
from orbital_workflow.communication import ReportContract
from orbital_workflow.durable import CachedModels, CachedTools, DurableWorkflow
from orbital_workflow.failures import ActionRequestError
from orbital_workflow.persistence import PersistenceSettings
from orbital_workflow.records import plain
from orbital_workflow.runtime import Kind, ToolAction
from orbital_workflow.scientific import ScientificBindings, load_settings
from orbital_workflow.simulation import integrate
from orbital_workflow.storage import read_index
from test_arithmetic_workflow import fixture_estimator
from verify_scored_run import Verifier

CONFIG = Path(__file__).resolve().parents[1] / "study.toml"
RUN_ID = "request-diagnostic-boundary-regression"
REPORT_FIELDS = [
    {"name": "feedback_category", "meaning": "Basic local request failure category",
     "schema_json": '{"type":"string","enum":["wrong_parameters"]}', "binding_json": "{}"},
    {"name": "run_index", "meaning": "Completed local simulation observation index",
     "schema_json": '{"type":"integer"}', "binding_json": "{}"},
    {"name": "score", "meaning": "Actual simulator recurrence score",
     "schema_json": '{"type":"number"}', "binding_json": "{}"},
]


class DiagnosticModelFixture:
    """Correct an invalid public parameter, then use the acquired measurement."""
    def __init__(self):
        self.followup_inputs, self.form_inputs = [], []

    async def release(self, episode_id):
        pass

    async def complete(self, episode_id, role, instructions, payload, schema):
        context = payload["current"]
        if context["mode"] == "form":
            self.form_inputs.append(context)
            simulation, arithmetic = context["own_tool_observations"]
            if arithmetic["operation"] != "math.arithmetic":
                raise AssertionError("The completed form lost the child's second acquisition")
            return {"feedback_category": "wrong_parameters", "run_index": simulation["run_index"],
                    "score": simulation["measurements"]["score"]}
        response = {"action": "", "label": "request-feedback", "rationale": "software_fixture",
            "tool_name": "", "arguments_json": "{}", "child_kind": "", "objective": "",
            "child_assignment_json": "{}", "report_decision": "", "report_fields": []}
        if context["episode_kind"] == Kind.ROOT:
            response.update(action="child", child_kind=Kind.SIMULATION,
                objective="Investigate a fixed-scenario insertion using local request feedback",
                child_assignment_json='{"software_fixture_only":true,"credit_target":"new"}',
                report_decision="Use the measured score and requested basic feedback", report_fields=REPORT_FIELDS)
            return response
        position = context["controller"]["units"]
        if position == 0:
            arguments = {"vx": 0., "vy": 1.}
            if "action_failure" not in context:
                arguments["end"] = context["fixed_problem"]["interface"]["evaluation_interval"][1] + 1.
            else:
                if context["action_failure"] != {"category": "wrong_parameters", "tool": "sim.run", "field": "end"}:
                    raise AssertionError("Wrong public parameter failure metadata")
                if context["own_tool_observations"] or context["local_credit_history"]:
                    raise AssertionError("An invalid request fabricated an acquisition")
                self.followup_inputs.append(context)
            response.update(action="tool", tool_name="sim.run", arguments_json=json.dumps(arguments))
        elif position == 1:
            if "action_failure" in context:
                raise AssertionError("Prior uncommitted feedback leaked into a later unit")
            simulation = context["own_tool_observations"][0]
            if simulation["operation"] != "sim.run" or simulation["run_index"] != 1:
                raise AssertionError("The simulation did not receive the first local run index")
            response.update(action="tool", tool_name="math.arithmetic", arguments_json=json.dumps({
                "expression": "score-score", "values": {"score": simulation["measurements"]["score"]}}))
        else:
            raise AssertionError("Numerical fixture did not stop after two acquisitions")
        return response


class NoFreshModels:
    async def complete(self, *args, **kwargs):
        raise AssertionError("Reconstruction must use saved model responses")


class SimulationDiagnosticWorkflow(unittest.TestCase):
    def setUp(self):
        fixture_estimator(self)

    @staticmethod
    def settings():
        settings = load_settings(CONFIG)
        for local in settings["episodes"].values():
            local["yield"] = {"window_size": 2, "subsample_size": 1, "uncertainty_alpha": .05}
            local["continuation_cost"] = 100.
        return settings

    def test_public_parameter_failure_has_no_turn_and_child_form_replays(self):
        settings = self.settings()
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            tools = CachedTools(Artifacts(directory / "objects"), PersistenceSettings(), directory / "tool-cache")
            def root(binding):
                return binding.spec(Kind.ROOT, "request-feedback", "Obtain measured evidence after feedback", {})
            class InterruptAfterRun(DurableWorkflow):
                def _record_unit(self, item, contribution, view):
                    super()._record_unit(item, contribution, view)
                    raise InterruptedError("Software interruption after first successful simulation")
            first_provider = DiagnosticModelFixture()
            first = ScientificBindings(settings, CachedModels(first_provider, directory / "model-cache"), tools)
            horizon = first.problem["evaluation_interval"][1]
            with self.assertRaises(ActionRequestError) as failure:
                first.simulation_arguments({"vx": 0., "vy": 1., "observation_window": [0., horizon + 1.]})
            self.assertEqual(failure.exception.diagnostic["field"], "observation_window")
            resolved = first.simulation_arguments({"vx": 0., "vy": 1.})
            self.assertEqual(resolved["observation_window"], (0., horizon))
            with self.assertRaises(ActionRequestError) as failure:
                first.simulation_arguments({"vx": 0., "vy": 1.,
                    "experiment": {"interval": [0., horizon + 1.]}}, parts=True)
            self.assertEqual(failure.exception.diagnostic["field"], "experiment.interval")
            derived = first.simulation_arguments({"vx": 0., "vy": 1., "experiment": {
                "interval": [0., 20.], "refinement": {"max_step": .025}}}, parts=True)
            self.assertEqual((derived["start"], derived["end"], derived["max_step"]), (0., 20., .025))
            self.assertEqual(derived["forcing_id"], resolved["forcing_id"])
            self.assertEqual(derived["experiment"]["kind"], "derived")
            self.assertEqual(resolved["max_step"], settings["numerics"]["max_step"])
            with patch("orbital_workflow.tools.integrate", wraps=integrate) as simulate:
                with self.assertRaises(InterruptedError):
                    asyncio.run(InterruptAfterRun(first.bindings(), tools, directory / "episodes").run_async(root(first), RUN_ID))
                self.assertEqual((simulate.call_count, tools.fresh_calls), (1, 1))
                self.assertEqual(len(first_provider.followup_inputs), 1)
                feedback = first_provider.followup_inputs[0]
                self.assertEqual((feedback["controller"]["units"], feedback["operation_attempt"]), (0, 1))
                self.assertEqual(first.completed_runs, {})
                provider = DiagnosticModelFixture()
                models = CachedModels(provider, directory / "model-cache")
                binding = ScientificBindings(settings, models, tools)
                record, result = asyncio.run(DurableWorkflow(binding.bindings(), tools, directory / "episodes").run_async(root(binding), RUN_ID))
                self.assertGreaterEqual(models.replayed_calls, 3)
                self.assertEqual((simulate.call_count, tools.fresh_calls), (1, 2))
                self.assertEqual((record.units_consumed, record.ended_by), (2, "yield_stop"))
                self.assertEqual(len(result.measurements), 1)
                score = result.measurements[0]["measurement"]["score"]
                self.assertTrue(math.isfinite(score) and score >= 0.)
                self.assertEqual(record.controller_state.record["credit"], score)
                self.assertEqual(record.controller_state.record["marginal_credit"], 0.)
                replay_models = CachedModels(NoFreshModels(), directory / "model-cache")
                replay_binding = ScientificBindings(settings, replay_models, tools)
                replay, replay_result = asyncio.run(DurableWorkflow(replay_binding.bindings(), tools, directory / "episodes").run_async(root(replay_binding), RUN_ID))
                self.assertEqual(replay.as_record(), record.as_record())
                self.assertEqual(replay_result.as_record(), result.as_record())
                self.assertEqual((replay_models.fresh_calls, tools.fresh_calls, simulate.call_count), (0, 2, 1))
            self.assertEqual((len(provider.followup_inputs), len(provider.form_inputs)), (1, 2))
            rows, warnings = read_index(directory)
            self.assertEqual((len(rows), warnings), (1, []))
            self.assertEqual(rows[0]["summary"]["score"], score)
            records = [json.loads(path.read_text()) for path in (directory / "episodes").glob("episode_*.json")]
            self.assertEqual(Counter(row["scope_level"] for row in records), {Kind.ROOT: 1, Kind.SIMULATION: 2})
            self.assertEqual(sum(row["units_consumed"] for row in records), 6)
            for row in records:
                self.assertEqual(row["ended_by"], "yield_stop")
                self.assertEqual(row["controller_state"]["yield_estimate"]["turns"], 2)
                if row["scope_level"] == Kind.SIMULATION:
                    run, arithmetic = row["units"]
                    self.assertEqual(run["controller_input"]["findings"][0]["run_index"], 1)
                    self.assertEqual(run["controller_step"]["score_assignment"]["received_scores"], [score])
                    self.assertEqual(arithmetic["controller_step"]["score_assignment"]["received_scores"], [])
                    self.assertEqual(arithmetic["controller_step"]["marginal_credit"], 0.)
                for unit in row["units"]:
                    if unit["child"]:
                        child = unit["child"]
                        contract = ReportContract.from_record(child["request"]["report_contract"])
                        report = contract.admit(unit["episode_update"]["report"], audit_identifiers=tuple(unit["child_result"]["artifacts"]))
                        self.assertEqual(plain(report.values), {"feedback_category": "wrong_parameters", "run_index": 1, "score": score})
                        self.assertTrue(child["unit_records_archived"])
                        saved = directory / "episode-store" / "episodes" / child["episode_id"] / "parent-report.json"
                        self.assertEqual(json.loads(saved.read_text()), plain(report.values))
            caches = [json.loads(path.read_text()) for path in (directory / "model-cache").glob("*.json")]
            self.assertTrue(all(row["request"]["role"] == "REASONING" for row in caches))
            self.assertEqual(sum(row["request"]["context"]["mode"] == "form" for row in caches), 2)

    def test_completed_private_window_diagnostic_is_acquired_once_without_a_score(self):
        """Private engine fixture; this does not grant public parameter ownership."""
        settings = self.settings()
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            tools = CachedTools(Artifacts(directory / "objects"), PersistenceSettings(), directory / "tool-cache")
            def build_fixture():
                binding = ScientificBindings(settings, None, tools)
                good = binding.simulation_arguments({"vx": 0., "vy": 1.})
                horizon = good["end"]
                actions = [ToolAction("private-window-diagnostic", "sim.run", {**good, "end": horizon + 1.}),
                           ToolAction("private-completed-run", "sim.run", good)]
                class EngineFixture:
                    def next(self, view):
                        return actions[view.units_consumed]
                spec = replace(binding.spec(Kind.SIMULATION, "private-window", "Private engine feedback fixture", {}),
                    source_factory=lambda request: EngineFixture())
                workflow = DurableWorkflow(binding.bindings(), tools, directory / "episodes")
                workflow.tree = EpisodeTree(root=workflow.grains[Kind.SIMULATION])
                return binding, spec, workflow, horizon
            binding, spec, workflow, horizon = build_fixture()
            original_record = workflow._record_unit
            def interrupt(item, contribution, view):
                original_record(item, contribution, view)
                raise InterruptedError("Software interruption after durable engine diagnostic")
            workflow._record_unit = interrupt
            with patch("orbital_workflow.tools.integrate", wraps=integrate) as simulate:
                with self.assertRaises(InterruptedError):
                    asyncio.run(workflow.run_async(spec, RUN_ID))
                simulate.assert_not_called()
                self.assertEqual(tools.fresh_calls, 1)
                self.assertEqual(read_index(directory), ([], []))
                binding, spec, workflow, _ = build_fixture()
                record, result = asyncio.run(workflow.run_async(spec, RUN_ID))
                self.assertEqual((simulate.call_count, tools.fresh_calls), (1, 2))
                binding, spec, workflow, _ = build_fixture()
                replay, replay_result = asyncio.run(workflow.run_async(spec, RUN_ID))
                self.assertEqual(replay.as_record(), record.as_record())
                self.assertEqual(replay_result.as_record(), result.as_record())
                self.assertEqual(simulate.call_count, 1)
            diagnostic, run = record.unit_records
            expected = {"code": "outside_observation_window", "requested_interval": [0., horizon + 1.], "observation_window": [0., horizon]}
            self.assertEqual(plain(diagnostic.controller_input.findings[0]["measurements"]), expected)
            self.assertEqual(diagnostic.controller_input.measurements, ())
            self.assertNotIn("run_index", diagnostic.controller_input.findings[0])
            self.assertEqual(diagnostic.controller_step.record["score_assignment"]["received_scores"], [])
            self.assertEqual(diagnostic.controller_step.record["marginal_credit"], 0.)
            self.assertEqual(diagnostic.controller_step.record["yield_estimate"]["turns"], 1)
            self.assertEqual(run.controller_input.findings[0]["run_index"], 1)
            self.assertEqual((record.units_consumed, record.controller_state.record["yield_estimate"]["turns"]), (2, 2))
            self.assertEqual(len(result.measurements), 1)
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
