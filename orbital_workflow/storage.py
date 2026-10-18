"""Versioned on-disk episode and simulation records, independent of the loop."""

from hashlib import sha256
import json
import os
from pathlib import Path
import re

import numpy as np

from .artifacts import Artifacts


def publish(path, value, *, immutable=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n"
    if immutable and path.exists():
        if json.loads(path.read_text()) != value:
            raise ValueError(f"Stored episode data diverged: {path}")
        return
    temporary = path.with_suffix(path.suffix + ".pending")
    with temporary.open("w") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.:-]{0,127}", value):
        raise ValueError("Malformed storage identity")
    return value


def scalar_summary(summary):
    result = {key: value for key, value in summary.items() if key != "solver_message"}
    result["persistence_measurement"] = {
        key: value for key, value in summary["persistence_measurement"].items()
        if key not in {"cycles", "limitations"}}
    return result


class EpisodeStore:
    def __init__(self, directory, *, producer="workflow"):
        self.directory = Path(directory).resolve()
        self.base = self.directory / "episode-store"
        self.base.mkdir(parents=True, exist_ok=True)
        marker = self.base / "format.json"
        if not marker.exists():
            publish(marker, {"format": "orbital.episode-store", "version": 1,
                             "producer": producer}, immutable=True)

    def relative(self, path):
        return str(Path(path).resolve().relative_to(self.directory))

    def episode_directory(self, episode_id):
        return self.base / "episodes" / identifier(episode_id)

    def array_files(self, artifact_id, names):
        target = self.base / "arrays" / identifier(artifact_id)
        paths = {name: target / (name + ".npy") for name in names}
        missing = [name for name, path in paths.items() if not path.exists()]
        if missing:
            arrays = Artifacts(self.directory / "objects").arrays(artifact_id)
            target.mkdir(parents=True, exist_ok=True)
            for name in missing:
                temporary = paths[name].with_suffix(".npy.pending")
                with temporary.open("wb") as stream:
                    np.save(stream, arrays[name], allow_pickle=False)
                    stream.flush()
                    os.fsync(stream.fileno())
                temporary.replace(paths[name])
        return {name: self.relative(path) for name, path in paths.items()}

    def observe(self, references, episode_id, unit_id, *, origin=None, order=None):
        """Publish only completed acquisitions; no array is retained afterwards."""
        artifacts = Artifacts(self.directory / "objects")
        observations = []
        for ref in references:
            source = artifacts.directory / (ref + ".json")
            if not source.exists():
                continue
            value = artifacts.json(ref)
            if set(value) != {"request", "summary", "trajectory"}:
                continue
            observations.append(ref)
            target = self.base / "observations" / ref
            manifest_path = target / "manifest.json"
            if manifest_path.exists():
                old = json.loads(manifest_path.read_text())
                if old["episode_id"] is None and episode_id is not None:
                    old.update(episode_id=episode_id, unit_id=unit_id, origin=origin)
                    publish(manifest_path, old)
                    publish(self.base / "index" / (ref + ".json"),
                            {**old, "manifest_file": self.relative(manifest_path)})
                continue
            request, summary = value["request"], value["summary"]
            trajectory_files = self.array_files(value["trajectory"], ("times", "states"))
            forcing_files = self.array_files(request["forcing_id"], ("times", "eta"))
            forcing = artifacts.arrays(request["forcing_id"])
            times = np.load(self.directory / trajectory_files["times"], mmap_mode="r")
            group = {key: item for key, item in request.items()
                     if key not in {"end", "method", "max_step", "sample_step", "rtol", "atol"}}
            manifest = {
                "format": "orbital.simulation", "version": 1, "id": ref,
                "episode_id": episode_id, "unit_id": unit_id,
                "trajectory_id": value["trajectory"], "forcing_id": request["forcing_id"],
                "group": sha256(json.dumps(group, sort_keys=True).encode()).hexdigest(),
                "request": request, "summary": scalar_summary(summary),
                "sample_count": len(times),
                "trajectory_files": trajectory_files, "forcing_files": forcing_files,
                "forcing_seed": int(forcing["seed"]),
                "measurements_file": self.relative(source),
                "origin": origin,
                "acquisition_order": list(order or (source.stat().st_mtime_ns, 0)),
            }
            publish(manifest_path, manifest, immutable=True)
            publish(self.base / "index" / (ref + ".json"),
                    {**manifest, "manifest_file": self.relative(manifest_path)}, immutable=True)
        if observations and episode_id and unit_id:
            publish(self.base / "ownership" / identifier(episode_id) / (identifier(unit_id) + ".json"),
                    {"observations": observations}, immutable=True)
        return observations

    def close_episode(self, record, audit_file):
        value = record.as_record() if hasattr(record, "as_record") else record
        target = self.episode_directory(value["episode_id"])
        observations = []
        for path in sorted((self.base / "ownership" / value["episode_id"]).glob("*.json")):
            observations.extend(json.loads(path.read_text())["observations"])
        request_file = target / "request.json"
        publish(request_file, value["request"], immutable=True)
        manifest = {
            "format": "orbital.episode", "version": 1,
            "episode_id": value["episode_id"], "run_id": value["run_id"],
            "parent_goal_id": value["goal"]["parent_goal_id"],
            "kind": value["scope_level"], "path": value["path"], "state": "closed",
            "completion": {key: value[key] for key in ("ended_by", "end_reason", "units_consumed")},
            "request_file": self.relative(request_file), "audit_file": self.relative(audit_file),
            "result_file": self.relative(target / "result.json") if (target / "result.json").exists() else None,
            "parent_report_file": self.relative(target / "parent-report.json") if (target / "parent-report.json").exists() else None,
            "children": [unit["child"]["episode_id"] for unit in value["units"] if unit["child"]],
            "observations": list(dict.fromkeys(observations)),
        }
        # These manifest fields become available after parent report composition.
        path = target / "manifest.json"
        if path.exists():
            old = json.loads(path.read_text())
            for key in ("result_file", "parent_report_file"):
                manifest[key] = old[key]
        publish(path, manifest)
        return manifest

    def finish_episode(self, record, result, report):
        target = self.episode_directory(record.episode_id)
        result_file, report_file = target / "result.json", target / "parent-report.json"
        publish(result_file, result.as_record(), immutable=True)
        if report is not None:
            publish(report_file, report.as_record(), immutable=True)
        path = target / "manifest.json"
        manifest = json.loads(path.read_text())
        manifest.update(result_file=self.relative(result_file),
                        parent_report_file=self.relative(report_file) if report is not None else None)
        publish(path, manifest)
        return self.relative(result_file)




def read_index(directory):
    """Small metadata only: no numerical arrays, cycle logs or recursive audits."""
    rows = []
    warnings = []
    for path in sorted((Path(directory) / "episode-store" / "index").glob("*.json")):
        try:
            row = json.loads(path.read_text())
            if row.get("format") != "orbital.simulation" or row.get("version") != 1:
                raise ValueError("Unknown simulation storage version")
            rows.append(row)
        except (OSError, ValueError) as error:
            warnings.append({"file": str(path), "error": type(error).__name__})
    rows.sort(key=lambda item: (item["acquisition_order"], item["id"]))
    return rows, warnings


def read_observation(directory, observation_id, *, start=None, end=None, max_points=10000):
    """Read selected saved states through memory-mapped NPY files."""
    directory = Path(directory).resolve()
    path = directory / "episode-store" / "observations" / identifier(observation_id) / "manifest.json"
    row = json.loads(path.read_text())
    times = np.load(directory / row["trajectory_files"]["times"], mmap_mode="r")
    states = np.load(directory / row["trajectory_files"]["states"], mmap_mode="r")
    left = 0 if start is None else max(0, int(np.searchsorted(times, start, side="left")) - 1)
    right = len(times) if end is None else min(len(times), int(np.searchsorted(times, end, side="right")) + 1)
    if right <= left:
        raise ValueError("Requested time range does not overlap this observation")
    count = right - left
    count_limit = max(2, min(int(max_points), 10000))
    indices = (np.arange(left, right) if count <= count_limit
               else np.unique(np.linspace(left, right - 1, count_limit, dtype=np.int64)))
    source = json.loads((directory / row["measurements_file"]).read_text())
    return {
        "simulation": {**row, "summary": source["summary"],
                       "times": times[indices].tolist(), "states": states[indices].tolist(),
                       "display_sampling": {"source_samples": count, "display_samples": len(indices),
                                            "decimated": len(indices) < count}},
        "forcing": read_forcing(directory, observation_id, float(times[indices[0]])),
    }


def read_forcing(directory, observation_id, time, *, max_points=5001):
    directory = Path(directory).resolve()
    path = directory / "episode-store" / "observations" / identifier(observation_id) / "manifest.json"
    row = json.loads(path.read_text())
    times = np.load(directory / row["forcing_files"]["times"], mmap_mode="r")
    eta = np.load(directory / row["forcing_files"]["eta"], mmap_mode="r")
    count = len(times) if max_points is None else min(len(times), max_points)
    center = int(np.searchsorted(times, time))
    left = max(0, min(center - count // 2, len(times) - count))
    return {"times": times[left:left + count].tolist(), "eta": eta[left:left + count].tolist(),
            "seed": row["forcing_seed"], "source_interval": [float(times[0]), float(times[-1])]}
