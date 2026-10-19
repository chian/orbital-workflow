"""Temporary synthetic interruption fixtures; no science, providers or fitting."""

import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from orbital_workflow.bootstrap import use_method_loop
use_method_loop(Path(__file__).resolve().parents[2] / "OpenChia")

from orbital_workflow.artifacts import Artifacts
from orbital_workflow.communication import ReportContract
from orbital_workflow.credit import CreditController, Evidence, evidence_key
from orbital_workflow.durable import CachedTools, DurableWorkflow
from orbital_workflow.persistence import PersistenceSettings
from orbital_workflow.records import Observation, plain
from orbital_workflow.runtime import ChildAction, EpisodeBindings, Kind, ToolAction
from orbital_workflow.score_yield import NumericBand, STATUS_INSUFFICIENT, YieldEstimate
from orbital_workflow.smoke import spec
from orbital_workflow.storage import EpisodeStore, read_index, read_observation
from orbital_workflow.viewer_timeline import load_timeline


def synthetic_observation(store, score):
    """Predeclared array/score data, never a simulator measurement."""
    forcing = store.put_arrays(times=np.array([0., 1., 2.]), eta=np.zeros((3, 2)), seed=np.array(7))
    trajectory = store.put_arrays(times=np.array([0., 1., 2.]), states=np.zeros((3, 4)))
    request = {"forcing_id": forcing, "software_fixture_only": True, "label": str(score)}
    summary = {"score": score, "software_fixture_only": True, "observed_interval": [0., 2.],
               "persistence_measurement": {"cycles": [], "limitations": []}}
    record = store.put_json({"request": request, "summary": summary, "trajectory": trajectory})
    return Observation("software_fixture", summary, (forcing, trajectory, record))


class FakeEstimator:
    """Record acquisition deltas without estimating or fitting anything."""
    def __init__(self, parameters):
        self.parameters, self.scores = parameters, []

    def observe(self, score):
        self.scores.append(score)
        return self.state()

    def state(self):
        return YieldEstimate(len(self.scores), NumericBand.coded(STATUS_INSUFFICIENT), self.parameters,
            {"software_fixture_only": True, "fitter_executed": False})


class DurablePublication(unittest.TestCase):
    def setUp(self):
        for target in ("orbital_workflow.tools.integrate", "orbital_workflow.score_yield.estimate_score_yield"):
            guard = patch(target, side_effect=AssertionError("Synthetic storage fixtures cannot simulate or fit"))
            guard.start()
            self.addCleanup(guard.stop)

    def test_interrupted_json_and_npz_staging_exposes_only_absent_or_complete_objects(self):
        array_buffer = io.BytesIO()
        np.savez_compressed(array_buffer, values=np.arange(8))
        variants = [(b'{"software_fixture_only": true}', ".json"), (array_buffer.getvalue(), ".npz")]
        named_temporary_file = tempfile.NamedTemporaryFile
        for payload, suffix in variants:
            for offset in (0, 1, len(payload) // 2, len(payload) - 1):
                with self.subTest(suffix=suffix, offset=offset), tempfile.TemporaryDirectory() as temporary:
                    directory = Path(temporary)
                    store = Artifacts(directory)
                    previous = store.put_json({"already_committed_fixture": True})
                    previous_path = directory / (previous + ".json")
                    before = previous_path.read_bytes(), previous_path.stat().st_mtime_ns
                    identity = "artifact_" + hashlib.sha256(payload).hexdigest()
                    final = directory / (identity + suffix)

                    class InterruptedStream:
                        def __init__(self, *args, **kwargs):
                            self.stream = named_temporary_file(*args, **kwargs)
                            self.name = self.stream.name

                        def __enter__(self):
                            return self

                        def __exit__(self, *args):
                            return self.stream.__exit__(*args)

                        def write(self, data):
                            self.stream.write(data[:offset])
                            self.stream.flush()
                            raise InterruptedError("Synthetic byte-offset interruption")

                    with patch("orbital_workflow.artifacts.tempfile.NamedTemporaryFile", InterruptedStream):
                        with self.assertRaises(InterruptedError):
                            store._put(payload, suffix)
                    self.assertFalse(final.exists())
                    # A hard process exit may leave a partial stage file; it is
                    # neither a final artifact nor a source for identical retry.
                    abandoned = directory / ("." + identity + ".abandoned" + suffix + ".pending")
                    abandoned.write_bytes(payload[:offset])
                    self.assertEqual(store._put(payload, suffix), identity)
                    self.assertEqual(store.payload(identity, suffix), payload)
                    self.assertEqual((previous_path.read_bytes(), previous_path.stat().st_mtime_ns), before)

            with self.subTest(suffix=suffix, phase="after_final_link"), tempfile.TemporaryDirectory() as temporary:
                store = Artifacts(Path(temporary))
                identity = "artifact_" + hashlib.sha256(payload).hexdigest()
                with patch("orbital_workflow.artifacts.sync_directory", side_effect=InterruptedError("After link")):
                    with self.assertRaises(InterruptedError):
                        store._put(payload, suffix)
                self.assertEqual(store.payload(identity, suffix), payload)
                final = store.directory / (identity + suffix)
                before = final.stat().st_ino, final.stat().st_mtime_ns
                self.assertEqual(store._put(payload, suffix), identity)
                self.assertEqual((final.stat().st_ino, final.stat().st_mtime_ns), before)

    def test_exact_payload_retry_preserves_damaged_bytes_and_repairs_the_hash_path(self):
        array_buffer = io.BytesIO()
        np.savez_compressed(array_buffer, values=np.arange(8))
        for payload, suffix in ((b'{"software_fixture_only": true}', ".json"), (array_buffer.getvalue(), ".npz")):
            with self.subTest(suffix=suffix), tempfile.TemporaryDirectory() as temporary:
                store = Artifacts(Path(temporary))
                identity = "artifact_" + hashlib.sha256(payload).hexdigest()
                final = store.directory / (identity + suffix)
                damaged = payload[:len(payload) // 2]
                final.write_bytes(damaged)
                with self.assertRaisesRegex(ValueError, "Artifact bytes changed"):
                    store.payload(identity, suffix)
                self.assertEqual(store._put(payload, suffix), identity)
                self.assertEqual(store.payload(identity, suffix), payload)
                retained = list(store.directory.glob(final.name + ".corrupt-*"))
                self.assertEqual(len(retained), 1)
                self.assertEqual(retained[0].read_bytes(), damaged)
                before = final.read_bytes(), final.stat().st_mtime_ns
                self.assertEqual(store._put(payload, suffix), identity)
                self.assertEqual((final.read_bytes(), final.stat().st_mtime_ns), before)
                self.assertEqual(list(store.directory.glob(final.name + ".corrupt-*")), retained)

    def test_unknown_damaged_cached_evidence_is_not_recomputed(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            store = Artifacts(directory / "objects")
            tools = CachedTools(store, PersistenceSettings(), directory / "cache")
            value = synthetic_observation(store, .166)
            with patch.dict(tools.handlers, {"math.numeric": lambda arguments: value}):
                observed = tools.execute("math.numeric", {"software_fixture_only": True})
            final = store.directory / (observed.artifacts[-1] + ".json")
            final.write_bytes(final.read_bytes()[:10])
            with patch.dict(tools.handlers, {"math.numeric": lambda arguments: self.fail("No scientific repair execution")}), \
                    self.assertRaisesRegex(ValueError, "Artifact bytes changed"):
                tools.execute("math.numeric", {"software_fixture_only": True})
            self.assertEqual(tools.fresh_calls, 1)
            self.assertEqual(tools.replayed_calls, 0)

    def test_missing_index_and_interrupted_first_owner_adoption_are_idempotent(self):
        from orbital_workflow import storage
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            objects = Artifacts(directory / "objects")
            observation = synthetic_observation(objects, .166)
            ref = observation.artifacts[-1]
            store = EpisodeStore(directory)
            store.observe(observation.artifacts, None, None, order=[123, 0])
            index_path = store.base / "index" / (ref + ".json")
            original_publish = storage.publish

            def interrupt_index(path, *args, **kwargs):
                if Path(path) == index_path:
                    raise InterruptedError("Synthetic owner adoption interruption")
                return original_publish(path, *args, **kwargs)

            with patch("orbital_workflow.storage.publish", side_effect=interrupt_index):
                with self.assertRaises(InterruptedError):
                    store.observe(observation.artifacts, "fixture_episode", "fixture_unit", origin={"action": "fixture"})
            self.assertIsNone(json.loads(index_path.read_text())["episode_id"])
            store.observe(observation.artifacts, "fixture_episode", "fixture_unit", origin={"action": "fixture"})
            manifest_path = store.base / "observations" / ref / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            self.assertEqual(manifest["episode_id"], "fixture_episode")
            self.assertEqual(manifest["acquisition_order"], [123, 0])
            index_path.unlink()
            store.observe(observation.artifacts, "fixture_episode", "fixture_unit", order=[999, 0])
            self.assertEqual(json.loads(index_path.read_text()), {**manifest, "manifest_file": store.relative(manifest_path)})
            before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in
                      [index_path, manifest_path, store.base / "ownership/fixture_episode/fixture_unit.json"]}
            store.observe(observation.artifacts, "fixture_episode", "fixture_unit", order=[999, 0])
            self.assertEqual(before, {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in before})
            rows, warnings = read_index(directory)
            timeline, issues = load_timeline(directory, rows)
            self.assertEqual(warnings + issues, [])
            self.assertEqual(len(rows), 1)
            self.assertEqual(len(timeline), 1)
            self.assertEqual(read_observation(directory, ref)["simulation"]["summary"]["score"], .166)

    def test_divergent_manifest_or_index_cannot_publish_new_ownership(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            observation = synthetic_observation(Artifacts(directory / "objects"), .166)
            ref = observation.artifacts[-1]
            store = EpisodeStore(directory)
            store.observe(observation.artifacts, "original_episode", "original_unit")
            manifest_path = store.base / "observations" / ref / "manifest.json"
            index_path = store.base / "index" / (ref + ".json")
            original_manifest = manifest_path.read_bytes()
            manifest = json.loads(original_manifest)
            manifest["id"] = "different_observation"
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "manifest diverged"):
                store.observe(observation.artifacts, "another_episode", "another_unit")
            self.assertFalse((store.base / "ownership/another_episode/another_unit.json").exists())
            manifest_path.write_bytes(original_manifest)
            index = json.loads(index_path.read_text())
            index["summary"]["score"] = 999
            index_path.write_text(json.dumps(index))
            damaged_index = index_path.read_bytes()
            with self.assertRaisesRegex(ValueError, "Stored episode data diverged"):
                store.observe(observation.artifacts, "another_episode", "another_unit")
            self.assertEqual(index_path.read_bytes(), damaged_index)
            self.assertFalse((store.base / "ownership/another_episode/another_unit.json").exists())

    def test_publication_boundaries_preserve_prefix_and_one_observation_per_fixture_acquisition(self):
        from orbital_workflow import durable, storage
        settings = {"episodes": {kind: {"continuation_cost": 1., "yield": {
            "window_size": 8, "subsample_size": 4, "uncertainty_alpha": .05}} for kind in Kind}}
        for phase in ("before_index", "after_index", "after_ownership", "after_unit"):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as temporary, \
                    patch("orbital_workflow.credit.ScalarScoreYieldEstimator", FakeEstimator):
                directory = Path(temporary)
                objects = Artifacts(directory / "objects")
                values = {index: synthetic_observation(objects, score) for index, score in enumerate((.05, .166))}
                tools = CachedTools(objects, PersistenceSettings(), directory / "cache")
                executed = []

                def synthetic_tool(arguments):
                    executed.append(arguments["fixture_index"])
                    return values[arguments["fixture_index"]]

                tools.handlers["math.numeric"] = synthetic_tool
                controllers = []

                def controller(path):
                    value = CreditController(settings, path[-1][0], path=path)
                    controllers.append(value)
                    return value

                def project(observation, request):
                    return Evidence(({"type": "trajectory", "measurement": plain(observation.findings)},),
                        ({"software_fixture_only": True},), observation.artifacts)

                def result(record):
                    items, artifacts = {}, []
                    for unit in record.unit_records:
                        for item in unit.controller_input.measurements:
                            items[evidence_key(item)] = plain(item)
                        artifacts.extend(unit.controller_input.artifacts)
                    return Evidence(tuple(items.values()), (), tuple(dict.fromkeys(artifacts)))

                bindings = {kind: EpisodeBindings(controller, project, result) for kind in Kind}
                child = spec(Kind.MATH, "fixture-child", "Finite synthetic storage workload", [
                    ToolAction("fixture-" + str(index), "math.numeric", {"fixture_index": index}) for index in values])
                contract = ReportContract("Use the synthetic fixture score", {}, {"score": "Synthetic acquired score"},
                    {"type": "object", "additionalProperties": False, "required": ["score"],
                     "properties": {"score": {"type": "number"}}})
                action = ChildAction(child, contract,
                    lambda value, completion, request: Evidence(value.measurements, (), value.artifacts),
                    lambda value, completion, request: {"score": max(item["measurement"]["score"] for item in value.measurements)})
                root = spec(Kind.ROOT, "fixture-root", "Finite synthetic storage fixture", [action])
                original_publish, original_save = storage.publish, durable.save
                last_ref = values[1].artifacts[-1]

                def interrupted_publish(path, value, **kwargs):
                    is_index = Path(path).parent.name == "index" and Path(path).stem == last_ref
                    is_ownership = Path(path).parent.parent.name == "ownership" and value.get("observations") == [last_ref]
                    if is_index and phase == "before_index":
                        raise InterruptedError("Synthetic split publication")
                    original_publish(path, value, **kwargs)
                    if (is_index and phase == "after_index") or (is_ownership and phase == "after_ownership"):
                        raise InterruptedError("Synthetic split publication")

                def interrupted_save(path, value):
                    original_save(path, value)
                    if phase == "after_unit" and value.get("label") == "fixture-1":
                        raise InterruptedError("Synthetic committed unit interruption")

                with patch("orbital_workflow.storage.publish", side_effect=interrupted_publish), \
                        patch("orbital_workflow.durable.save", side_effect=interrupted_save):
                    with self.assertRaises(InterruptedError):
                        DurableWorkflow(bindings, tools, directory / "episodes").run(root, "synthetic-publication")
                prefix = {path: (path.read_bytes(), path.stat().st_mtime_ns) for folder, pattern in [
                    (directory / "episodes/units", "*.json"), (directory / "cache", "*.json"),
                    (directory / "episode-store/ownership", "*/*.json")] for path in folder.glob(pattern)}
                controllers.clear()
                record, _ = DurableWorkflow(bindings, tools, directory / "episodes").run(root, "synthetic-publication")
                self.assertEqual(prefix, {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in prefix})
                self.assertEqual(executed, [0, 1])
                self.assertEqual(record.units_consumed, 1)
                self.assertEqual(record.controller_state.record["credit"], .166)
                self.assertEqual(sorted(controller.estimator.scores for controller in controllers), [[.05, .166 - .05], [.166]])
                self.assertEqual(len(list((directory / "episodes/units").glob("*.json"))), 3)
                rows, warnings = read_index(directory)
                timeline, issues = load_timeline(directory, rows)
                self.assertEqual(warnings + issues, [])
                self.assertEqual(len(rows), 2)
                self.assertEqual(len(timeline), 2)
                self.assertEqual(len(list((directory / "episode-store/ownership").glob("*/*.json"))), 2)


if __name__ == "__main__":
    unittest.main()
