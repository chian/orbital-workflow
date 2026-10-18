from dataclasses import replace
import math
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from orbital_workflow.bootstrap import use_method_loop

use_method_loop(Path(__file__).resolve().parents[2] / "OpenChia")

from orbital_workflow.artifacts import Artifacts
from orbital_workflow.records import Observation
from orbital_workflow.runtime import (DiagnosticController, DiagnosticStep, Kind,
                                      ToolAction, Workflow, diagnostic_bindings,
                                      diagnostic_child)
from orbital_workflow.simulation import (ModelTerms, SimulationRequest,
                                         generate_forcing, integrate)
from orbital_workflow.smoke import probe_plan, spec
from orbital_workflow.tools import ToolDispatcher


class SkeletonContracts(unittest.TestCase):
    def test_real_simulator_reductions_and_continuation_reuse_identical_forcing(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Artifacts(Path(directory))
            forcing = generate_forcing(store, 1, 4 * math.pi)
            reference = SimulationRequest(forcing, end=4 * math.pi,
                terms=ModelTerms(modulation=False, rotating=False, forcing=False))
            circle = integrate(reference, store)
            analytic = np.column_stack((np.cos(circle.times), np.sin(circle.times),
                                        -np.sin(circle.times), np.cos(circle.times)))
            np.testing.assert_allclose(circle.states, analytic, atol=1e-8, rtol=0)
            self.assertEqual(circle.outcome, "horizon_reached")

            full_request = replace(reference, terms=ModelTerms())
            full = integrate(full_request, store)
            split = 0.1 * 30
            prefix = integrate(replace(full_request, end=split), store)
            suffix = integrate(replace(full_request, start=split,
                                       initial_state=tuple(prefix.states[-1])), store)
            np.testing.assert_array_equal(full.states[-1], suffix.states[-1])
            self.assertGreater(np.max(np.abs(full.states - circle.states)), 1e-3)

            replay = integrate(full_request, store)
            np.testing.assert_array_equal(full.states, replay.states)
            np.testing.assert_array_equal(store.arrays(forcing)["eta"],
                                          store.arrays(generate_forcing(store, 1, 4 * math.pi))["eta"])
            self.assertEqual(store.arrays(forcing)["eta"].shape[1], 2)
            scoped = integrate(replace(reference, spatial_box=(0.8, 1.1, -0.1, 0.5)), store)
            self.assertEqual(scoped.outcome, "region_exit")
            first_boundary = min(math.acos(0.8), math.asin(0.5))
            np.testing.assert_allclose(scoped.times[-1], first_boundary, atol=1e-8)

    def test_recursive_method_loop_projects_reports_and_obeys_injected_controller(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = Artifacts(root / "objects")
            forcing = generate_forcing(store, 1, 4 * math.pi)
            workflow = Workflow(diagnostic_bindings(), ToolDispatcher(store), root / "audit")
            record, result = workflow.run(probe_plan(forcing), "nested-tool-test")
            self.assertEqual(record.ended_by, "exhausted")
            self.assertIsNone(result.as_record()["credit"])

            from orbital_workflow.communication import ReportContract
            def walk(node):
                if node.get("unit_records_archived"):
                    node = json.loads((root / node["record_file"]).read_text())
                yield node
                for unit in node["units"]:
                    if unit["child"] is not None:
                        child = unit["child"]
                        self.assertEqual(child["goal"]["parent_goal_id"], node["goal"]["goal_id"])
                        contract = ReportContract.from_record(child["request"]["report_contract"])
                        report = contract.admit(unit["episode_update"]["report"],
                            audit_identifiers=tuple(unit["child_result"]["artifacts"]))
                        self.assertEqual(set(report.values), set(contract.information))
                        yield from walk(child)

            self.assertEqual(record.unit_records[0].child.unit_records, ())
            nodes = list(walk(record.as_record()))
            self.assertEqual(len({node["episode_id"] for node in nodes}), len(nodes))
            self.assertTrue(any(node["path"][-2][0] == Kind.PARTS and node["scope_level"] == Kind.PARTS
                                for node in nodes if len(node["path"]) > 1))
            for node in nodes:
                self.assertEqual(node["controller_state"]["observations"], node["units_consumed"])

            calls = []
            tools = ToolDispatcher(store)
            tools.handlers["math.numeric"] = lambda args: (
                calls.append(args["value"]) or Observation("math.numeric", args))

            class StopAfterObservation(DiagnosticController):
                def observe(self, label, value, *, is_root):
                    super().observe(label, value, is_root=is_root)
                    return DiagnosticStep(self.observations, stop=True)

            bindings = diagnostic_bindings()
            bindings[Kind.MATH] = replace(bindings[Kind.MATH], controller=lambda path: StopAfterObservation())
            child = spec(Kind.MATH, "controlled", "Exercise an injected controller", [
                ToolAction("first", "math.numeric", {"value": 1}),
                ToolAction("second", "math.numeric", {"value": 2}),
            ])
            parent = spec(Kind.ROOT, "parent", "Observe a child return", [
                diagnostic_child(child, "Receive the stopped child's findings"),
            ])
            controlled = Workflow(bindings, tools, root / "controlled")
            stopped, _ = controlled.run(parent, "controller-routing-test")
            self.assertEqual(calls, [1])
            self.assertEqual(stopped.unit_records[0].child.ended_by, "yield_stop")
            self.assertIsNot(stopped.controller_state, stopped.unit_records[0].child.controller_state)


if __name__ == "__main__":
    unittest.main()
