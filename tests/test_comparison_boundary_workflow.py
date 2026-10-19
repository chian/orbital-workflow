"""A comparison can reuse own evidence also acquired by a child safely."""

import asyncio
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from orbital_workflow.bootstrap import use_method_loop
use_method_loop(Path(__file__).resolve().parents[2] / "OpenChia")

from orbital_workflow.artifacts import Artifacts
from orbital_workflow.communication import ParentModelInputError, ReportContract, _model_inputs
from orbital_workflow.durable import CachedModels, CachedTools, DurableWorkflow
from orbital_workflow.persistence import PersistenceSettings
from orbital_workflow.records import plain
from orbital_workflow.runtime import Kind
from orbital_workflow.scientific import ScientificBindings, load_settings
from orbital_workflow.simulation import integrate
from verify_scored_run import Verifier


CONFIG = Path(__file__).resolve().parents[1] / "study.toml"
RUN_ID = "comparison-boundary-regression"
LEFT_RUN = {"vx": 0., "vy": 1.}
RIGHT_RUN = {"vx": .01, "vy": 1.}
SCORE_FIELD = {"name": "score", "meaning": "Greatest actual observed recurrence score",
               "schema_json": '{"type":"number"}', "binding_json": "{}"}
COMPARISON_FIELDS = [SCORE_FIELD, *[
    {"name": side + "_indices", "meaning": "All own local aliases for the compared observation",
     "schema_json": '{"type":"array","items":{"type":"integer"}}', "binding_json": "{}"}
    for side in ("left", "right")]]


class ComparisonModelFixture:
    """Exercise policy decisions; all measurements come from the real tools."""

    def __init__(self):
        self.after_comparison = []

    async def release(self, episode_id):
        pass

    async def complete(self, episode_id, role, instructions, payload, schema):
        context = payload["current"]
        if context["mode"] == "form":
            scores = [report["score"] for report in context["child_reports"]]
            comparison = None
            for finding in context["own_tool_observations"]:
                if finding["operation"] == "sim.run":
                    scores.append(finding["measurements"]["score"])
                elif finding["operation"] == "sim.compare":
                    comparison = finding["measurements"]
            report = {"score": max(scores)}
            if comparison:
                report.update({side + "_indices": comparison["run_indices"][side]
                               for side in ("left", "right")})
            return report

        response = {"action": "", "label": "shared-evidence", "rationale": "software_fixture",
            "tool_name": "", "arguments_json": "{}", "child_kind": "", "objective": "",
            "child_assignment_json": "{}", "report_decision": "", "report_fields": []}
        kind, position = context["episode_kind"], context["controller"]["units"]
        if kind == Kind.ROOT or (kind == Kind.SIMULATION and position == 1):
            response.update(action="child", child_kind=Kind.SIMULATION if kind == Kind.ROOT else Kind.PARTS,
                objective="Investigate and compare the assigned spaceship insertions",
                child_assignment_json=json.dumps({"software_fixture_only": True, "credit_target": "new"}),
                report_decision="Use actual recurrence measurements",
                report_fields=COMPARISON_FIELDS if kind == Kind.ROOT else [SCORE_FIELD])
            return response

        response.update(action="tool")
        if kind == Kind.PARTS:
            if position == 0:
                response.update(tool_name="sim.run", arguments_json=json.dumps(RIGHT_RUN))
            elif position == 1:
                score = context["own_tool_observations"][0]["measurements"]["score"]
                response.update(tool_name="math.arithmetic", arguments_json=json.dumps({
                    "expression": "fine-fine", "values": {"fine": score}}))
            else:
                raise AssertionError("Parts numerical fixture did not yield-stop")
        elif position in (0, 2, 3):
            response.update(tool_name="sim.run", arguments_json=json.dumps(LEFT_RUN if position == 0 else RIGHT_RUN))
        elif position == 4:
            response.update(tool_name="sim.compare", arguments_json='{"left":1,"right":2}')
        elif position == 5:
            # Reaching this provider proves the unchanged model-input guard
            # admitted the full actual context after the shared-ID comparison.
            self.after_comparison.append(deepcopy(context))
            comparison = context["own_tool_observations"][-1]["measurements"]
            if comparison["run_indices"] != {"left": [1], "right": [2, 3]}:
                raise AssertionError("Comparison lost repeated own aliases")
            if "observation_references" in comparison:
                raise AssertionError("Comparison leaked raw artifact identities")
            response.update(tool_name="math.arithmetic", arguments_json=json.dumps({
                "expression": "fine-coarse", "values": {
                    "fine": comparison["right"]["score"], "coarse": comparison["left"]["score"]}}))
        else:
            raise AssertionError("Simulation numerical fixture did not yield-stop")
        return response


class NoFreshModels:
    async def complete(self, *args, **kwargs):
        raise AssertionError("Completed reconstruction needs no fresh model responses")


class ComparisonBoundaryWorkflow(unittest.TestCase):
    maxDiff = None

    def test_shared_child_evidence_compare_continues_and_replays_with_local_aliases(self):
        settings = load_settings(CONFIG)
        for kind, local in settings["episodes"].items():
            # Minimum fit information keeps a policy turn after the comparison.
            # It is a test numerical fixture, never a source/iteration cap.
            local["yield"] = {"window_size": 6 if kind == Kind.SIMULATION else 2,
                              "subsample_size": 1, "uncertainty_alpha": .05}
            local["continuation_cost"] = 100.

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            tools = CachedTools(Artifacts(directory / "objects"), PersistenceSettings(), directory / "tool-cache")

            def root(binding):
                return binding.spec(Kind.ROOT, "shared-evidence", "Investigate and compare insertions",
                                    {"software_fixture_only": True})

            class InterruptAfterCompare(DurableWorkflow):
                def _record_unit(self, item, contribution, view):
                    super()._record_unit(item, contribution, view)
                    if view.controller_input.findings and view.controller_input.findings[0]["operation"] == "sim.compare":
                        raise InterruptedError("Software interruption after durable comparison")

            with patch("orbital_workflow.tools.integrate", wraps=integrate) as simulate:
                first = ScientificBindings(settings,
                    CachedModels(ComparisonModelFixture(), directory / "model-cache"), tools)
                with self.assertRaises(InterruptedError):
                    asyncio.run(InterruptAfterCompare(first.bindings(), tools, directory / "episodes").run_async(
                        root(first), RUN_ID))
                self.assertEqual(simulate.call_count, 2)
                self.assertEqual(tools.fresh_calls, 4)

                provider = ComparisonModelFixture()
                models = CachedModels(provider, directory / "model-cache")
                binding = ScientificBindings(settings, models, tools)
                record, result = asyncio.run(DurableWorkflow(binding.bindings(), tools, directory / "episodes").run_async(
                    root(binding), RUN_ID))
                self.assertGreater(models.replayed_calls, 0)
                self.assertEqual(len(provider.after_comparison), 2)
                self.assertEqual(simulate.call_count, 2)
                self.assertEqual(tools.fresh_calls, 5)
                expected_best = max(item["measurement"]["score"] for item in result.measurements)
                self.assertEqual(record.controller_state.record["credit"], expected_best)
                self.assertEqual(record.controller_state.record["marginal_credit"], 0)

                replay_models = CachedModels(NoFreshModels(), directory / "model-cache")
                replay_binding = ScientificBindings(settings, replay_models, tools)
                replay, replay_result = asyncio.run(DurableWorkflow(replay_binding.bindings(), tools, directory / "episodes").run_async(
                    root(replay_binding), RUN_ID))
                self.assertEqual(replay.as_record(), record.as_record())
                self.assertEqual(replay_result.as_record(), result.as_record())
                self.assertEqual(replay_models.fresh_calls, 0)
                self.assertEqual(tools.fresh_calls, 5)
                self.assertEqual(simulate.call_count, 2)

            records = [json.loads(path.read_text()) for path in (directory / "episodes").glob("episode_*.json")]
            self.assertEqual(Counter(row["scope_level"] for row in records),
                             {Kind.ROOT: 1, Kind.SIMULATION: 2, Kind.PARTS: 2})
            for row in records:
                self.assertEqual(row["ended_by"], "yield_stop")
                self.assertEqual(row["units_consumed"], 6 if row["scope_level"] == Kind.SIMULATION else 2)
                self.assertTrue(row["controller_state"]["continuation"]["stop"])
                for unit in row["units"]:
                    if unit["child"]:
                        contract = ReportContract.from_record(unit["child"]["request"]["report_contract"])
                        contract.admit(unit["episode_update"]["report"],
                            audit_identifiers=tuple(unit["child_result"]["artifacts"]))
                    elif unit["controller_input"]["findings"][0]["operation"] == "sim.compare":
                        self.assertEqual(unit["controller_step"]["marginal_credit"], 0)

            parent = next(row for row in records if row["scope_level"] == Kind.SIMULATION)
            coarse, child, fine, repeated, compared, arithmetic = parent["units"]
            coarse_ref = coarse["controller_input"]["artifacts"][-1]
            fine_ref = fine["controller_input"]["artifacts"][-1]
            self.assertEqual(repeated["controller_input"]["artifacts"][-1], fine_ref)
            child_result = json.loads((directory / child["child_result"]["result_file"]).read_text())
            self.assertIn(fine_ref, child_result["artifacts"])
            self.assertEqual([fine["controller_input"]["findings"][0]["run_index"],
                              repeated["controller_input"]["findings"][0]["run_index"]], [2, 3])
            compared_findings = compared["controller_input"]["findings"][0]["measurements"]
            self.assertEqual(compared_findings["run_indices"], {"left": [1], "right": [2, 3]})
            self.assertNotIn("observation_references", compared_findings)
            for unit in (fine, repeated, compared, arithmetic):
                self.assertEqual(unit["controller_step"]["marginal_credit"], 0)

            # Direct alias check: selecting the second or third index resolves
            # the same raw evidence and retains both aliases in model findings.
            request = SimpleNamespace(goal=SimpleNamespace(goal_id="direct-alias-check"))
            binding.completed_runs[request.goal.goal_id] = [coarse_ref, fine_ref, fine_ref]
            action = binding.tool({"tool_name": "sim.compare", "arguments_json": '{"left":1,"right":3}',
                                   "label": "direct-alias-check"}, kind=Kind.SIMULATION, request=request)
            raw = tools.execute(action.tool, action.arguments)
            self.assertEqual(plain(raw.findings["observation_references"]), {"left": coarse_ref, "right": fine_ref})
            projected = binding.project_tool(raw, request)
            self.assertEqual(plain(projected.findings[0]["measurements"]), compared_findings)
            self.assertEqual(tools.fresh_calls, 5)

            # Reinject the actual shared identity and prove the original guard
            # still rejects it, using the real admitted typed child report.
            contract = ReportContract.from_record(child["child"]["request"]["report_contract"])
            report = contract.admit(child["episode_update"]["report"], audit_identifiers=tuple(child_result["artifacts"]))
            context = deepcopy(provider.after_comparison[0])
            context.pop("child_reports")
            self.assertEqual(_model_inputs(context, (report,), (report,))["child_reports"], [report.as_record()])
            context["own_tool_observations"][-1]["measurements"]["observation_references"] = {
                "left": coarse_ref, "right": fine_ref}
            with self.assertRaisesRegex(ParentModelInputError, "child audit identity"):
                _model_inputs(context, (report,), (report,))

            # Read only the fixture's actual saved records with the generic
            # verifier; no provenance claim about this fake model connection.
            (directory / "study.toml").write_text(CONFIG.read_text())
            (directory / "manifest.json").write_text(json.dumps({"run_id": RUN_ID}))
            verifier = Verifier(directory)
            verifier.settings = settings
            verifier.tool_cache()
            verifier.closed_episodes()
            self.assertEqual(verifier.discrepancies, [])
            self.assertEqual(verifier.checked["comparison_models_receive_all_local_indices_without_audit_references"], 2)
            self.assertEqual(verifier.counts["cached_tools"]["sim.compare"], 1)


if __name__ == "__main__":
    unittest.main()
