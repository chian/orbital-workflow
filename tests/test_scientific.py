from dataclasses import asdict, replace
from pathlib import Path
import tempfile
import unittest

from orbital_workflow.bootstrap import use_method_loop
use_method_loop(Path(__file__).resolve().parents[2] / "OpenChia")

from orbital_workflow.artifacts import Artifacts
from orbital_workflow.credit import CreditController, Evidence, project_observation
from orbital_workflow.durable import CachedTools, DurableWorkflow
from orbital_workflow.persistence import PersistenceSettings
from orbital_workflow.runtime import EpisodeBindings, Kind, ToolAction, diagnostic_child
from orbital_workflow.scientific import ScientificBindings, load_settings
from orbital_workflow.simulation import ModelTerms, SimulationRequest, generate_forcing, integrate
from orbital_workflow.smoke import spec
from orbital_workflow.tools import ToolDispatcher


CONFIG = Path(__file__).resolve().parents[1] / "study.toml"


class ScientificSemantics(unittest.TestCase):
    def test_duplicate_credit_parent_scale_and_zero_yield_continuation(self):
        settings = load_settings(CONFIG)
        with tempfile.TemporaryDirectory() as directory:
            store = Artifacts(Path(directory))
            tools = ToolDispatcher(store)
            symbolic = project_observation(tools.execute("math.symbolic", {"operation": "central_conic"}), store)
            parent = CreditController(settings, Kind.ROOT)
            child = CreditController(settings, Kind.MATH)
            child_step = child.observe("derive", symbolic, is_root=False)
            parent_step = parent.observe("receive", Evidence(symbolic.measurements), is_root=True)
            self.assertAlmostEqual(child_step.record["credit"], 1)
            self.assertAlmostEqual(parent_step.record["credit"], .5 / 8)
            duplicate = parent.observe("repeat", Evidence(symbolic.measurements), is_root=True)
            self.assertEqual(duplicate.record["marginal_credit"], 0)
            self.assertEqual(duplicate.record["credit"], parent_step.record["credit"])
            while not parent.state().stop:
                parent.observe("no additional knowledge", Evidence(()), is_root=True)
            self.assertLessEqual(parent.state().record["predicted_next_gain"], settings["episodes"][Kind.ROOT]["continuation_cost"])

    def test_reduced_motion_contributes_without_full_model_approval_and_refinement_is_not_independent(self):
        settings = load_settings(CONFIG)
        with tempfile.TemporaryDirectory() as directory:
            store = Artifacts(Path(directory))
            tools = ToolDispatcher(store)
            forcing = generate_forcing(store, 1, 20)
            request = SimulationRequest(forcing, end=20, terms=ModelTerms(modulation=False, rotating=False, forcing=False))
            controller = CreditController(settings, Kind.ROOT)
            observation = project_observation(tools.execute("sim.run", asdict(request)), store)
            step = controller.observe("reduced", observation, is_root=True)
            self.assertGreater(step.record["components"]["knowledge_gained"], 0)
            self.assertEqual(step.record["components"]["orbital_persistence"], 0)
            before = step.record["credit"]
            duplicate = controller.observe("repeat", observation, is_root=True)
            self.assertEqual(duplicate.record["credit"], before)
            finer = replace(request, sample_step=.01, max_step=.025, rtol=1e-8, atol=1e-10)
            step = controller.observe("finer", project_observation(tools.execute("sim.run", asdict(finer)), store), is_root=True)
            self.assertGreater(step.record["credit"], before)
            # Same deterministic physical input, finer evidence, one forcing group.
            self.assertEqual(len({item["forcing_group"] for item in controller.ledger.evidence.values()}), 1)
            self.assertEqual(len({item["physical_id"] for item in controller.ledger.evidence.values()}), 1)

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
            self.assertAlmostEqual(record.controller_state.record["credit"], .5 / 8)
            self.assertEqual(tools.replayed_calls, 1)
            self.assertEqual(tools.fresh_calls, 2)
            again_binding = ScientificBindings(settings, None, tools)
            again = DurableWorkflow(again_binding.bindings(), tools, directory / "episodes")
            replay, _ = again.run(plan(again_binding), "resume-test")
            self.assertEqual(replay.as_record(), record.as_record())
            self.assertEqual(tools.fresh_calls, 2)


if __name__ == "__main__":
    unittest.main()
