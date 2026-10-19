"""Failed attempts steer the same real Episode without successful acquisitions."""

import asyncio
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from orbital_workflow.bootstrap import use_method_loop
use_method_loop(Path(__file__).resolve().parents[2] / "OpenChia")

from method_loop import EpisodeTree
from orbital_workflow.artifacts import Artifacts
from orbital_workflow.durable import CachedTools, DurableWorkflow
from orbital_workflow.failures import ActionRequestError, ToolAcquisitionFailure, failure_diagnostic
from orbital_workflow.persistence import PersistenceSettings
from orbital_workflow.records import Observation
from orbital_workflow.tools import ToolDispatcher
from orbital_workflow.runtime import (
    DiagnosticController, DiagnosticStep, EpisodeBindings, EpisodeSpec, Kind,
    ToolAction,
)


class OneObservationController(DiagnosticController):
    def state(self):
        return DiagnosticStep(self.observations, stop=self.observations >= 1)


class CorrectingPolicy:
    def __init__(self):
        self.failures = []
        self.views = []

    def accept_failure(self, diagnostic):
        self.failures.append(diagnostic)

    async def next(self, view):
        self.views.append((view.units_consumed, view.controller_state.observations))
        return ToolAction("scalar", "math.arithmetic", {
            "expression": "1+1" if self.failures else "bad", "values": {}})


def fixture(directory, policy, handler, *, projection=None):
    tools = CachedTools(Artifacts(directory / "objects"), PersistenceSettings(), directory / "cache")
    tools.handlers["math.arithmetic"] = handler
    binding = EpisodeBindings(lambda path: OneObservationController(),
        projection or (lambda observation, request: observation),
        lambda record: Observation("fixture", {"units": record.units_consumed}))
    workflow = DurableWorkflow({kind: binding for kind in Kind}, tools, directory / "episodes")
    # This fixture is a single mathematical root; production topology is unchanged.
    workflow.tree = EpisodeTree(root=workflow.grains[Kind.MATH])
    spec = EpisodeSpec(Kind.MATH, "feedback", "Fixture calculation",
        Observation("assignment", {}), lambda request: policy)
    return workflow, spec, tools


class FailureFeedback(unittest.TestCase):
    def test_explicit_request_boundaries_report_only_known_category_tool_and_field(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = Artifacts(Path(temporary))
            dispatcher = ToolDispatcher(store)
            wrong_kind = store.put_json({"not": "a simulation observation"})
            cases = [
                ("math.arithmetic", {"expression": 1, "values": {}}, "wrong_parameters", "expression"),
                ("math.arithmetic", {"expression": "x", "values": {"x": True}}, "wrong_parameters", "values"),
                ("sim.compare", {"left": {}, "right": "unused"}, "wrong_parameters", "left"),
                ("sim.compare", {"left": wrong_kind, "right": wrong_kind}, "wrong_parameters", "left"),
                ("math.numeric", {"operation": "unsupported"}, "wrong_command", "operation"),
            ]
            for name, arguments, category, field in cases:
                with self.subTest(name=name, field=field), self.assertRaises(ToolAcquisitionFailure) as failed:
                    dispatcher.execute(name, arguments)
                self.assertEqual(failed.exception.diagnostic,
                    failure_diagnostic(category, tool=name, field=field))

    def test_failed_operation_reaches_same_episode_and_restores_without_execution(self):
        for known in (False, True):
            with self.subTest(known=known), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                calls = []

                def handler(arguments):
                    calls.append(arguments["expression"])
                    if arguments["expression"] == "bad":
                        if known:
                            raise ActionRequestError(tool="math.arithmetic", field="values")
                        raise ValueError("private implementation details must stay in the audit")
                    return Observation("math.arithmetic", {"value": 2.0})

                policy = CorrectingPolicy()
                workflow, spec, tools = fixture(directory, policy, handler)
                record, result = asyncio.run(workflow.run_async(spec, "failure-feedback"))
                expected = failure_diagnostic("wrong_parameters" if known else "unknown",
                    tool="math.arithmetic", field="values" if known else None)
                self.assertEqual(policy.failures, [expected])
                self.assertEqual(policy.views, [(0, 0), (0, 0)])
                self.assertEqual(record.units_consumed, 1)
                self.assertEqual(record.controller_state.observations, 1)
                self.assertEqual(record.ended_by, "yield_stop")
                self.assertEqual(calls, ["bad", "1+1"])
                self.assertEqual((tools.fresh_failures, tools.fresh_calls), (1, 1))
                self.assertEqual(len(list((directory / "episodes" / "units").glob("*.json"))), 1)
                self.assertEqual(record.unit_records[0].controller_input.findings["value"], 2.0)

                replay_policy = CorrectingPolicy()
                def no_execute(arguments):
                    raise AssertionError("A saved failed or completed attempt must not execute again")
                replay_workflow, replay_spec, replay_tools = fixture(directory, replay_policy, no_execute)
                replay, replay_result = asyncio.run(replay_workflow.run_async(replay_spec, "failure-feedback"))
                self.assertEqual(replay_policy.failures, [expected])
                self.assertEqual(replay.as_record(), record.as_record())
                self.assertEqual(replay_result.as_record(), result.as_record())
                self.assertEqual((replay_tools.replayed_failures, replay_tools.replayed_calls), (1, 1))

    def test_cancellation_projection_and_publication_faults_do_not_become_tool_feedback(self):
        for phase in ("cancellation", "projection", "publication", "stepping"):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                policy = CorrectingPolicy()

                def handler(arguments):
                    if phase == "cancellation":
                        raise asyncio.CancelledError()
                    return Observation("math.arithmetic", {"value": 2.0})

                def projection(observation, request):
                    if phase == "projection":
                        # Even the dedicated type is not a tool failure here.
                        raise ToolAcquisitionFailure(failure_diagnostic("unknown", tool="math.arithmetic"))
                    return observation

                workflow, spec, tools = fixture(directory, policy, handler, projection=projection)
                if phase == "stepping":
                    episode = workflow.build(spec)
                    with self.assertRaises(NotImplementedError):
                        asyncio.run(episode.run_unit_async(None, expected_label="scalar"))
                elif phase == "publication":
                    with patch("orbital_workflow.durable.save", side_effect=OSError("storage unavailable")):
                        with self.assertRaises(OSError):
                            asyncio.run(workflow.run_async(spec, "fault-boundary"))
                else:
                    error = asyncio.CancelledError if phase == "cancellation" else ToolAcquisitionFailure
                    with self.assertRaises(error):
                        asyncio.run(workflow.run_async(spec, "fault-boundary"))
                self.assertEqual(policy.failures, [])
                self.assertEqual(tools.fresh_failures, 0)
                self.assertEqual(len(list((directory / "episodes" / "units").glob("*.json"))), 0)
                if phase == "projection":
                    # The real operation has completed and remains reusable.
                    self.assertEqual(tools.fresh_calls, 1)
                    with patch.dict(tools.handlers, {"math.arithmetic": lambda arguments: self.fail("rerun")}):
                        saved = tools.execute("math.arithmetic", {"expression": "bad", "values": {}})
                    self.assertEqual(saved.findings["value"], 2.0)


if __name__ == "__main__":
    unittest.main()
