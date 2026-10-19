from dataclasses import asdict, replace
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from orbital_workflow.bootstrap import use_method_loop
use_method_loop(Path(__file__).resolve().parents[2] / "OpenChia")

from orbital_workflow.artifacts import Artifacts
from orbital_workflow.credit import CreditController, Evidence, project_observation
from orbital_workflow.durable import CachedTools, DurableWorkflow
from orbital_workflow.failures import ActionRequestError
from orbital_workflow.persistence import PersistenceSettings
from orbital_workflow.records import Observation
from orbital_workflow.runtime import EpisodeBindings, Kind, ToolAction, diagnostic_child
from orbital_workflow.scientific import ScientificBindings, load_settings
from orbital_workflow.simulation import ModelTerms, SimulationRequest, generate_forcing, integrate
from orbital_workflow.smoke import spec
from orbital_workflow.tools import ToolDispatcher


CONFIG = Path(__file__).resolve().parents[1] / "study.toml"


class ScientificSemantics(unittest.TestCase):
    def test_reduced_simulation_requires_the_explicit_parts_capability(self):
        from types import SimpleNamespace
        import json
        with tempfile.TemporaryDirectory() as directory:
            binding = ScientificBindings(load_settings(CONFIG), None,
                ToolDispatcher(Artifacts(Path(directory))))
            request = SimpleNamespace(goal=SimpleNamespace(goal_id="capability-fixture"))
            response = {"label":"isolate-term", "tool_name":"sim.run",
                        "arguments_json":json.dumps({"vx": 0, "vy": 1,
                            "experiment": {"terms":{"rotating":False}, "interval":[0,1]}})}
            with self.assertRaises(ActionRequestError) as caught:
                binding.tool(response, kind=Kind.SIMULATION, request=request)
            self.assertEqual(caught.exception.diagnostic["field"], "experiment")
            action = binding.tool(response, kind=Kind.PARTS, request=request)
            self.assertFalse(action.arguments["terms"]["rotating"])

    def test_acquired_units_count_runs_saved_comparison_and_math_at_their_own_grain(self):
        from orbital_workflow.communication import ReportContract
        from orbital_workflow.runtime import ChildAction

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            tools = ToolDispatcher(Artifacts(directory / "objects"))
            settings = load_settings(CONFIG)
            # Declared software fixture with a simple deterministic environment;
            # production forcing cases remain unchanged.
            settings["study"].update(a=0., sigma=0., horizon=20.)
            settings["physics"]["rotating_amplitude"] = 0.
            binding = ScientificBindings(settings, None, tools)

            def simulation_source(request):
                class Acquisitions:
                    def next(self, view):
                        # A finite software diagnostic drives the actual method;
                        # each proposal is acquired and scored before the next.
                        binding.run_owners[view.path] = request.goal.goal_id
                        if view.units_consumed == 3:
                            return None
                        if view.units_consumed < 2:
                            name = "sim.run"
                            arguments = {"vx": 0, "vy": [1.0, .99][view.units_consumed]}
                        else:
                            name, arguments = "sim.compare", {"left": 1, "right": 2}
                        return binding.tool({"label": name + "-" + str(view.units_consumed),
                            "tool_name": name, "arguments_json": json.dumps(arguments)},
                            kind=Kind.SIMULATION, request=request)
                return Acquisitions()

            simulation = replace(spec(Kind.SIMULATION, "two-observations", "Measure two full-model scores", []),
                                 assignment=Observation("assignment", {"credit_target": "new"}),
                                 source_factory=simulation_source)
            mathematics = spec(Kind.MATH, "unscored-mathematics", "Calculate a reference without a score bonus", [
                ToolAction("conic", "math.symbolic", {"operation": "central_conic"})])
            mathematics = replace(mathematics, assignment=Observation("assignment", {"credit_target": "new"}))
            contract = ReportContract(decision="Compare returned measured scores", measurements={},
                information={"best_score": "Largest supplied trajectory score, null when none was supplied"},
                value_schema={"type": "object", "additionalProperties": False,
                    "required": ["best_score"], "properties": {"best_score": {"type": ["number", "null"]}}})

            def child_action(child):
                return ChildAction(child, contract,
                    lambda result, completion, request: Evidence(result.measurements),
                    lambda result, completion, request: {"best_score": max(
                        (item["measurement"]["score"] for item in result.measurements
                         if item["type"] == "trajectory"), default=None)})

            root = spec(Kind.ROOT, "unit-accounting", "Receive scored child contributions", [
                child_action(simulation), child_action(mathematics)])
            with patch("orbital_workflow.tools.integrate", wraps=integrate) as calls:
                record, _ = DurableWorkflow(binding.bindings(), tools, directory / "episodes").run(
                    root, "per-episode-unit-accounting")
            self.assertEqual(calls.call_count, 2)

            child = json.loads((directory / record.unit_records[0].child.record_file).read_text())
            steps = [unit["controller_step"] for unit in child["units"]]
            scores = [child["units"][i]["controller_input"]["measurements"][0]["measurement"]["score"]
                      for i in range(2)]
            self.assertTrue(all(score > 0 for score in scores))
            self.assertEqual(child["units_consumed"], 3)
            self.assertEqual([step["units"] for step in steps], [1, 2, 3])
            self.assertEqual([step["yield_estimate"]["turns"] for step in steps], [1, 2, 3])
            self.assertEqual([len(step["score_assignment"]["received_scores"]) for step in steps[:2]], [1, 1])
            self.assertEqual(steps[0]["credit"], scores[0])
            self.assertEqual(steps[1]["credit"], max(scores))
            self.assertEqual(steps[2]["marginal_credit"], 0)
            self.assertEqual(steps[2]["score_assignment"]["distinct_observations"], 2)

            # Two scored observations and their comparison arrive as one root
            # acquisition. Their best score is projected, never their sum.
            first_root = record.unit_records[0].controller_step.record
            self.assertEqual(first_root["units"], 1)
            self.assertEqual(first_root["yield_estimate"]["turns"], 1)
            self.assertEqual(len(first_root["score_assignment"]["received_scores"]), 2)
            self.assertEqual(first_root["credit"], max(scores))
            self.assertLess(first_root["credit"], sum(scores))

            math_step = record.unit_records[1].child.controller_state.record
            self.assertEqual(math_step["units"], 1)
            self.assertEqual(math_step["yield_estimate"]["turns"], 1)
            self.assertEqual(math_step["score_assignment"]["received_scores"], [])
            self.assertEqual(math_step["marginal_credit"], 0)
            self.assertEqual(math_step["credit"], 0)
            self.assertEqual(record.units_consumed, 2)
            self.assertEqual(record.controller_state.record["marginal_credit"], 0)
            self.assertEqual(record.controller_state.record["credit"], max(scores))

    def test_derived_reduction_keeps_scoped_score_without_changing_fixed_environment(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as directory:
            settings = load_settings(CONFIG)
            binding = ScientificBindings(settings, None, ToolDispatcher(Artifacts(Path(directory))))
            request = SimpleNamespace(goal=SimpleNamespace(goal_id="environment-scope-fixture"))
            response = {"label":"unforced-approximation", "tool_name":"sim.run",
                        "arguments_json":json.dumps({"vx": 0, "vy": 1,
                            "experiment": {"terms":{"modulation":False,"forcing":False}}})}
            with self.assertRaises(ActionRequestError):
                binding.tool(response, kind=Kind.SIMULATION, request=request)
            scoped = binding.tool(response, kind=Kind.PARTS, request=request)
            self.assertEqual((scoped.arguments["a"], scoped.arguments["sigma"]), (.15,.03))
            self.assertFalse(binding.full_problem(scoped.arguments))
            item = {"type":"trajectory", "physical":scoped.arguments,
                    "software_fixture_only": True,
                    "measurement":{"score":123.0, "persistence_measurement":{},
                        "requested_interval": binding.problem["evaluation_interval"],
                        "observation_window": binding.problem["evaluation_interval"]}}
            self.assertIsNone(binding.root_score(item))
            self.assertEqual(CreditController(settings, Kind.PARTS).observe(
                "scoped score", Evidence((item,)), is_root=False).record["credit"],123.0)
            changed_amplitude = {**scoped.arguments, "a":10, "sigma":.03}
            self.assertFalse(binding.full_problem(changed_amplitude))
            complete = binding.simulation_arguments({"vx":0,"vy":1})
            self.assertTrue(binding.full_problem(complete))
            self.assertEqual(binding.root_score({**item, "physical":complete}),123.0)

    def test_returned_score_alone_drives_credit_and_duplicate_gain_is_zero(self):
        settings = load_settings(CONFIG)
        with tempfile.TemporaryDirectory() as directory:
            store = Artifacts(Path(directory))
            tools = ToolDispatcher(store)
            forcing = generate_forcing(store, 1, 20)
            request = SimulationRequest(forcing, end=20,
                terms=ModelTerms(modulation=False, rotating=False, forcing=False))
            observation = project_observation(tools.execute("sim.run", asdict(request)), store)
            changed = deepcopy(observation.as_record())
            measured = changed["measurements"][0]["measurement"]
            measured["observed_interval"] = [0, 100000]
            measured["rhs_evaluations"] = 999999
            measured["numerical_settings"]["sample_step"] = .000001
            # Software metamorphic fixture: returned score is unchanged while
            # simulator duration/work metadata changes. Neither enters credit.
            altered = Evidence(tuple(changed["measurements"]))
            a, b = (CreditController(settings, Kind.PARTS) for _ in range(2))
            first = a.observe("original", Evidence(observation.measurements), is_root=False)
            other = b.observe("changed metadata", altered, is_root=False)
            self.assertGreater(first.record["credit"], 0)
            for key in ("credit", "marginal_credit", "projected_credit", "yield_estimate"):
                self.assertEqual(first.record[key], other.record[key])
            duplicate = a.observe("repeat", observation, is_root=False)
            self.assertEqual(duplicate.record["credit"], first.record["credit"])
            self.assertEqual(duplicate.record["marginal_credit"], 0)
            self.assertFalse(duplicate.stop)
            self.assertEqual(len(a.assignment.evidence), 1)

    def test_parent_projects_scored_evidence_without_adding_child_credit(self):
        settings = load_settings(CONFIG)
        with tempfile.TemporaryDirectory() as directory:
            store = Artifacts(Path(directory))
            tools = ToolDispatcher(store)
            binding = ScientificBindings(settings, None, tools)
            forcing = generate_forcing(store, 1, 20)
            request = SimulationRequest(forcing, end=20,
                terms=ModelTerms(modulation=False, rotating=False, forcing=False))
            observation = project_observation(tools.execute("sim.run", asdict(request)), store)
            child = CreditController(settings, Kind.PARTS)
            parent = CreditController(settings, Kind.ROOT, binding.root_score)
            local = child.observe("reduction", observation, is_root=False)
            received = parent.observe("scoped evidence", Evidence(observation.measurements), is_root=True)
            self.assertGreater(local.record["credit"], 0)
            self.assertEqual(received.record["credit"], 0)
            self.assertEqual(len(parent.assignment.evidence), 1)
            self.assertEqual(observation.measurements[0]["measurement"]["score"], local.record["credit"])

    def test_terminal_event_without_an_output_sample_is_retained(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Artifacts(Path(directory))
            forcing = generate_forcing(store, 1, 40)
            request = SimulationRequest(forcing, end=40, sample_step=100)
            trajectory = integrate(request, store)
            self.assertEqual(trajectory.outcome, "outer_exit")
            self.assertAlmostEqual(float((trajectory.states[-1, :2] ** 2).sum()), 4, places=10)
            self.assertLess(trajectory.times[-1], request.end)

    def test_interrupted_nested_run_restores_controller_from_evidence_once(self):
        settings = load_settings(CONFIG)
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            store = Artifacts(directory / "objects")
            tools = CachedTools(store, PersistenceSettings(), directory / "cache")
            child = spec(Kind.MATH, "central", "derive reference", [
                ToolAction("conic", "math.symbolic", {"operation": "central_conic"}),
                ToolAction("candidate", "math.numeric", {"operation": "central_candidate", "vx": 0, "vy": 1}),
            ])
            child = replace(child, assignment=Observation("assignment", {"credit_target": "new"}))
            # Explicit finite diagnostic source for exercising a real interrupted
            # nested acquisition. Scientific run sources are model-driven.
            def plan(binding):
                from orbital_workflow.communication import ReportContract
                from orbital_workflow.runtime import ChildAction
                action = ChildAction(child, ReportContract(decision="reference", measurements={},
                    information={"reference": "central circular speed at radius 1"},
                    value_schema={"type": "object", "additionalProperties": False,
                        "required": ["reference"], "properties": {"reference": {"type": "number"}}}),
                    lambda result, completion, request: Evidence(result.measurements),
                    lambda result, completion, request: {"reference": 1.0})
                return spec(Kind.ROOT, "root", "resume diagnostic", [action])

            class InterruptOnce(DurableWorkflow):
                def _record_unit(self, item, contribution, view):
                    super()._record_unit(item, contribution, view)
                    raise InterruptedError("Injected interruption after a durable unit")

            first_binding = ScientificBindings(settings, None, tools)
            first = InterruptOnce(first_binding.bindings(), tools, directory / "episodes")
            with self.assertRaises(InterruptedError):
                first.run(plan(first_binding), "resume-test")
            self.assertEqual(tools.fresh_calls, 1)
            restored_binding = ScientificBindings(settings, None, tools)
            restored = DurableWorkflow(restored_binding.bindings(), tools, directory / "episodes")
            record, result = restored.run(plan(restored_binding), "resume-test")
            self.assertEqual(record.units_consumed, 1)
            self.assertEqual(record.unit_records[0].child.units_consumed, 2)
            self.assertEqual(record.controller_state.record["credit"], 0)
            self.assertEqual(tools.replayed_calls, 1)
            self.assertEqual(tools.fresh_calls, 2)
            again_binding = ScientificBindings(settings, None, tools)
            again = DurableWorkflow(again_binding.bindings(), tools, directory / "episodes")
            replay, _ = again.run(plan(again_binding), "resume-test")
            self.assertEqual(replay.as_record(), record.as_record())
            self.assertEqual(tools.fresh_calls, 2)


if __name__ == "__main__":
    unittest.main()
