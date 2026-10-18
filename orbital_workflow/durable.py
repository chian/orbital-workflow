"""Replay completed acquisitions to restore the actual method_loop state.

Reconstruction starts with a fresh controller and replays cached decisions and
observations exactly once. It never adds a restored total to replayed credits.
An interrupted tool acquisition may be recomputed deterministically; immutable
objects and a keyed result prevent duplicated accounting. No concurrent writer.
"""

import fcntl
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import sys
import shutil

import method_loop

from .credit import identity
from .records import Observation
from .runtime import Workflow
from .tools import ToolDispatcher


class IncompatibleResumeError(RuntimeError):
    """Stored execution cannot be continued by a different execution binding."""


def snapshot_sources(directory):
    """Keep executable source alongside each frozen run, including its real loop."""
    destination = directory / "source-snapshot"
    for package in (Path(__file__).resolve().parent, Path(method_loop.__file__).parent):
        for source in package.rglob("*"):
            if source.is_file() and source.suffix in (".py", ".html") and "__pycache__" not in source.parts:
                target = destination / package.name / source.relative_to(package)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
    shutil.copy2(directory / "study.toml", destination / "study.toml")


def execution_identity(configuration_text):
    package = Path(__file__).resolve().parent
    critical = ("simulation.py", "persistence.py", "tools.py", "credit.py", "scientific.py",
                "runtime.py", "communication.py", "boundary_validation.py", "records.py",
                "artifacts.py", "durable.py", "models.py", "bootstrap.py",
                "storage.py", "archival.py", "gravity.py")
    source = {"orbital_workflow/" + name: hashlib.sha256((package / name).read_bytes()).hexdigest()
              for name in critical}
    source.update({"method_loop/" + path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                   for path in Path(method_loop.__file__).parent.glob("*.py")})
    return {"configuration_sha256": hashlib.sha256(configuration_text.encode()).hexdigest(),
            "execution_sources": source, "python": sys.version,
            "libraries": {name: version(name) for name in ("numpy", "scipy", "sympy", "jsonschema")}}


def require_compatible_resume(directory, configuration_text):
    path = directory / "execution-identity.json"
    if not path.exists():
        raise IncompatibleResumeError("This historical run has no compatible execution snapshot; its evidence is preserved. Start a new run with the revised binding.")
    stored = json.loads(path.read_text())
    current = execution_identity(configuration_text)
    if current != stored:
        raise IncompatibleResumeError("Execution code, configuration or numerical libraries changed. Resume did not start; the saved history and credit were not altered.")


def save(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if path.exists():
        if json.loads(path.read_text()) != value:
            raise RuntimeError(f"Durable replay diverged at {path}")
        return
    temporary = path.with_suffix(path.suffix + ".pending")
    with temporary.open("w") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


class RunLock:
    def __init__(self, directory):
        self.path = directory / "run.lock"

    def __enter__(self):
        self.stream = self.path.open("a")
        try:
            fcntl.flock(self.stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.stream.close()
            raise RuntimeError("This run already has an active writer") from None
        return self

    def __exit__(self, *exception):
        self.stream.close()


class CachedTools(ToolDispatcher):
    def __init__(self, store, settings, directory):
        super().__init__(store, settings)
        self.directory = directory
        self.fresh_calls = 0
        self.replayed_calls = 0

    def execute(self, name, arguments):
        key = identity({"tool": name, "arguments": arguments})
        path = self.directory / (key + ".json")
        if path.exists():
            record = json.loads(path.read_text())
            for ref in record["artifacts"]:
                candidates = [self.store.directory / (ref + suffix) for suffix in (".json", ".npz")]
                if not any(candidate.exists() for candidate in candidates):
                    raise FileNotFoundError(f"Cached tool evidence missing: {ref}")
                for candidate in candidates:
                    if candidate.exists():
                        self.store.payload(ref, candidate.suffix)
            self.replayed_calls += 1
            return Observation(record["operation"], record["findings"], tuple(record["artifacts"]))
        observation = super().execute(name, arguments)
        save(path, observation.as_record())
        self.fresh_calls += 1
        return observation


class CachedModels:
    def __init__(self, connection, directory):
        self.connection, self.directory = connection, directory
        self.history = {}
        self.fresh_calls = 0
        self.replayed_calls = 0

    async def release(self, episode_id):
        for key in [key for key in self.history if key[0] == episode_id]:
            self.history.pop(key)
        if hasattr(self.connection, "release"):
            await self.connection.release(episode_id)

    async def complete(self, episode_id, role, instructions, context, schema):
        key = (episode_id, role)
        history = self.history.setdefault(key, [])
        request = {"episode": episode_id, "role": role, "instructions": instructions,
                   "context": context, "schema": schema}
        path = self.directory / (identity(request) + ".json")
        if path.exists():
            self.replayed_calls += 1
            result = json.loads(path.read_text())["response"]
        else:
            # Prior prompts/answers restore the visible conversation after a
            # process restart. Native hidden model state is not persisted.
            # Keep log references in memory. Read previous visible exchanges
            # only when restoring a conversation, not on each live turn.
            previous = []
            if not (hasattr(self.connection, "has_session") and self.connection.has_session(episode_id, role)):
                for prior_path in history:
                    prior = json.loads(prior_path.read_text())
                    previous.append({"context": prior["request"]["context"], "response": prior["response"]})
            payload = {"current": context, "previous_visible_exchanges": previous}
            result = await self.connection.complete(episode_id, role, instructions, payload, schema)
            save(path, {"request": request, "response": result})
            self.fresh_calls += 1
        history.append(path)
        return result


class DurableWorkflow(Workflow):
    def _record_unit(self, item, contribution, view):
        self._publish_observations(item, view)
        event = {"unit": view.unit_ref.as_record(), "label": view.unit_label,
                 "controller_input": view.controller_input.as_record(),
                 "controller_step": view.controller_step.as_record(),
                 "child_report": (view.episode_update.report.as_record()
                                  if view.episode_update else None)}
        save(self.audit_directory / "units" / (view.unit_ref.unit_id + ".json"), event)

    def _record_close(self, record):
        path = self.audit_directory / (record.episode_id + ".json")
        save(path, record.as_record())
        self.storage.close_episode(record, path)
