"""Storage boundaries exercised through actual nested method_loop execution."""
from dataclasses import replace
import gc
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import weakref

import numpy as np

from orbital_workflow.bootstrap import use_method_loop
use_method_loop(Path(__file__).resolve().parents[2] / 'OpenChia')
from orbital_workflow.artifacts import Artifacts
from orbital_workflow.runtime import (DiagnosticController, EpisodeSpec, Kind,
    Workflow, diagnostic_bindings, diagnostic_child)
from orbital_workflow.records import Observation
from orbital_workflow.simulation import generate_forcing
from orbital_workflow.smoke import probe_plan
from orbital_workflow.storage import read_index, read_observation, read_forcing
from orbital_workflow.visualization import load_catalog
from orbital_workflow.viewer_server import ViewerServer


class StorageLifecycle(unittest.TestCase):
    def test_closed_nested_logs_and_controllers_are_released_before_parent_continues(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifacts = Artifacts(root / 'objects')
            from orbital_workflow.tools import ToolDispatcher
            forcing = generate_forcing(artifacts, 1, 4 * math.pi)
            controllers, observations, checks = [], [], []
            bindings = diagnostic_bindings()
            def controller(path):
                instance = DiagnosticController()
                controllers.append((len(path), weakref.ref(instance)))
                return instance
            def project(observation, request):
                observations.append(weakref.ref(observation))
                return observation
            bindings = {kind: replace(binding, controller=controller, project_tool=project)
                        for kind, binding in bindings.items()}
            plan = probe_plan(forcing)
            original_factory = plan.source_factory
            def factory(request):
                inner = original_factory(request)
                class CheckingParent:
                    def next(self, view):
                        if view.units_consumed:
                            gc.collect()
                            # Even though the parent is still open, no completed
                            # descendant controller or raw tool observation lives.
                            self_test.assertTrue(all(ref() is None for depth, ref in controllers if depth > 1))
                            self_test.assertTrue(all(ref() is None for ref in observations))
                            checks.append(view.units_consumed)
                        return inner.next(view)
                return CheckingParent()
            self_test = self
            workflow = Workflow(bindings, ToolDispatcher(artifacts), root / 'episodes')
            record, _ = workflow.run(replace(plan, source_factory=factory), 'storage-lifecycle')
            self.assertEqual(checks, [1, 2])
            gc.collect()
            self.assertTrue(all(ref() is None for _, ref in controllers))
            self.assertEqual(workflow.active_paths, {})
            self.assertEqual(workflow.episode_paths, {})
            self.assertTrue(all(unit.child.unit_records == () for unit in record.unit_records))
            manifests = list((root / 'episode-store/episodes').glob('*/manifest.json'))
            self.assertEqual(len(manifests), 6)
            for path in manifests:
                manifest = json.loads(path.read_text())
                self.assertEqual(manifest['state'], 'closed')
                for key in ('audit_file', 'request_file', 'result_file'):
                    self.assertTrue((root / manifest[key]).is_file())
                if manifest['parent_goal_id']:
                    self.assertTrue((root / manifest['parent_report_file']).is_file())

    def test_index_is_metadata_only_and_selected_range_reloads_exact_saved_values(self):
        with tempfile.TemporaryDirectory() as temporary:
            from orbital_workflow.smoke import run_probe
            root = Path(temporary) / 'run'
            run_probe(root, Path(__file__).resolve().parents[1] / 'study.toml')
            with patch('numpy.load', side_effect=AssertionError('catalog loaded arrays')):
                catalog = load_catalog(root)
            rows, warnings = read_index(root)
            self.assertEqual(warnings, [])
            self.assertEqual(len(rows), 3)  # Four explicit runs reuse one identical baseline.
            self.assertEqual(len(catalog['simulations']), 3)
            for row in rows:
                self.assertIsNotNone(row['episode_id'])
                self.assertNotIn('cycles', row['summary']['persistence_measurement'])
                raw = Artifacts(root / 'objects').arrays(row['trajectory_id'])
                packet = read_observation(root, row['id'], start=2.1, end=3.7)
                shown = packet['simulation']
                left = max(0, np.searchsorted(raw['times'], 2.1) - 1)
                right = min(len(raw['times']), np.searchsorted(raw['times'], 3.7, side='right') + 1)
                np.testing.assert_array_equal(shown['times'], raw['times'][left:right])
                np.testing.assert_array_equal(shown['states'], raw['states'][left:right])
                self.assertIn('cycles', shown['summary']['persistence_measurement'])
                tiny = read_observation(root, row['id'], max_points=5)['simulation']
                self.assertLessEqual(len(tiny['times']), 5)
                np.testing.assert_array_equal(tiny['states'][0], raw['states'][0])
                np.testing.assert_array_equal(tiny['states'][-1], raw['states'][-1])
                exact_forcing = Artifacts(root / 'objects').arrays(row['forcing_id'])
                window = read_forcing(root, row['id'], 7, max_points=17)
                positions = np.searchsorted(exact_forcing['times'], window['times'])
                np.testing.assert_array_equal(window['eta'], exact_forcing['eta'][positions])
            # An unfinished publication is never discovered as an observation.
            (root / 'episode-store/index/unfinished.json.pending').write_text('{')
            self.assertEqual(len(read_index(root)[0]), 3)
            server = ViewerServer(root, port=0, cache_bytes=200000)
            try:
                snapshot = server.snapshot(root)
                self.assertTrue(all(row['states'] is None for row in snapshot['data']['simulations']))
                for row in rows:
                    self.assertIn('simulation', json.loads(server.observation(root, row['id'])))
                self.assertLessEqual(server.observation_bytes, server.cache_budget)
                missing = root / 'not-created'
                self.assertEqual(server.snapshot(missing)['data']['simulations'], [])
                self.assertFalse(missing.exists())
            finally:
                server.server_close()

class GrowingHistory(unittest.TestCase):
    def test_parent_history_grows_by_disk_references_without_child_logging_payloads(self):
        from orbital_workflow.runtime import ToolAction
        from orbital_workflow.smoke import spec
        from orbital_workflow.tools import ToolDispatcher
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tools = ToolDispatcher(Artifacts(root / 'objects'))
            weak_observations = []
            def diagnostic_payload(arguments):
                value = Observation('math.numeric', {'software_fixture': True,
                    'index':arguments['index'], 'diagnostic_trace':'saved log detail ' * 10000})
                weak_observations.append(weakref.ref(value))
                return value
            tools.handlers['math.numeric'] = diagnostic_payload
            children = [diagnostic_child(spec(Kind.MATH, f'child-{i}', 'Software storage fixture', [
                ToolAction('fixture', 'math.numeric', {'index':i})]), 'Return diagnostic operation counts')
                for i in range(20)]
            plan = spec(Kind.ROOT, 'growing', 'Software memory fixture; no scientific credit', children)
            factory = plan.source_factory
            checked_sizes = []
            self_test = self
            def source(request):
                inner = factory(request)
                class Check:
                    def next(self, view):
                        if view.units_consumed:
                            gc.collect()
                            self_test.assertTrue(all(ref() is None for ref in weak_observations))
                            checked_sizes.append(view.units_consumed)
                        return inner.next(view)
                return Check()
            record, result = Workflow(diagnostic_bindings(),tools,root/'episodes').run(
                replace(plan,source_factory=source), 'growing-storage-fixture')
            self.assertEqual(checked_sizes,list(range(1,21)))
            self.assertIsNone(result.as_record()['credit'])
            self.assertTrue(all(unit.child.unit_records == () for unit in record.unit_records))
            child_bytes=sum(path.stat().st_size for path in (root/'episodes').glob('*.json'))
            parent_bytes=len(json.dumps(record.as_record()))
            self.assertGreater(child_bytes,3000000)
            self.assertLess(parent_bytes,child_bytes/10)

class CompactAccounting(unittest.TestCase):
    def test_disk_compaction_preserves_parent_scores_and_duplicate_identity(self):
        from dataclasses import asdict
        from orbital_workflow.credit import CreditController, Evidence, compact_evidence, project_observation
        from orbital_workflow.scientific import load_settings
        from orbital_workflow.simulation import SimulationRequest
        from orbital_workflow.tools import ToolDispatcher
        with tempfile.TemporaryDirectory() as temporary:
            store=Artifacts(Path(temporary)/'objects')
            forcing=generate_forcing(store,1,20)
            full=project_observation(ToolDispatcher(store).execute('sim.run',
                asdict(SimulationRequest(forcing,end=20))),store)
            compact=Evidence(tuple(compact_evidence(item) for item in full.measurements),(),full.artifacts)
            settings=load_settings(Path(__file__).resolve().parents[1]/'study.toml')
            original,retained=(CreditController(settings,Kind.ROOT) for _ in range(2))
            a=original.observe('child',full,is_root=True)
            b=retained.observe('child',compact,is_root=True)
            self.assertEqual(a.as_record(),b.as_record())
            self.assertNotIn('cycles',compact.measurements[0]['measurement']['persistence_measurement'])
            self.assertGreater(len(full.measurements[0]['measurement']['persistence_measurement']['cycles']),0)
            duplicate=retained.observe('same child',full,is_root=True)
            self.assertEqual(duplicate.record['marginal_credit'],0)
            self.assertEqual(len(retained.assignment.evidence),1)

if __name__ == '__main__':
    unittest.main()
