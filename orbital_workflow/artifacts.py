"""Local immutable inputs and observations, separate from upward reports."""

import hashlib
import io
import json
import os
from pathlib import Path
import tempfile

import numpy as np


def sync_directory(directory):
    """Make a completed rename/link durable before publishing its dependents."""
    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


class Artifacts:
    def __init__(self, directory: Path):
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)

    def _put(self, payload: bytes, suffix: str) -> str:
        identity = "artifact_" + hashlib.sha256(payload).hexdigest()
        path = self.directory / (identity + suffix)
        if path.exists():
            try:
                self.payload(identity, suffix)
                sync_directory(self.directory)
                return identity
            except ValueError:
                # Repair is possible only here, where the exact bytes named by
                # the identity are supplied. Readers never invent replacements.
                pass
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="wb", dir=self.directory,
                    prefix="." + identity + ".", suffix=suffix + ".pending", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                # Exclusive final publication preserves an existing valid input.
                os.link(temporary, path)
            except FileExistsError:
                try:
                    self.payload(identity, suffix)
                except ValueError:
                    damaged = path.read_bytes()
                    retained = path.with_name(path.name + ".corrupt-" + hashlib.sha256(damaged).hexdigest())
                    try:
                        os.link(path, retained)
                    except FileExistsError:
                        if retained.read_bytes() != damaged:
                            raise ValueError("Retained corrupt artifact bytes changed")
                    sync_directory(self.directory)
                    temporary.replace(path)
            sync_directory(self.directory)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return identity

    def put_json(self, record: dict) -> str:
        return self._put(json.dumps(record, sort_keys=True, allow_nan=False).encode(), ".json")

    def put_arrays(self, **arrays) -> str:
        stream = io.BytesIO()
        np.savez_compressed(stream, **arrays)
        return self._put(stream.getvalue(), ".npz")

    def payload(self, identity: str, suffix: str) -> bytes:
        if (not identity.startswith("artifact_") or len(identity) != 73
                or any(char not in "0123456789abcdef" for char in identity[9:])):
            raise ValueError("Malformed artifact identity")
        payload = (self.directory / (identity + suffix)).read_bytes()
        if "artifact_" + hashlib.sha256(payload).hexdigest() != identity:
            raise ValueError("Artifact bytes changed")
        return payload

    def json(self, identity: str):
        return json.loads(self.payload(identity, ".json"))

    def arrays(self, identity: str) -> dict[str, np.ndarray]:
        with np.load(io.BytesIO(self.payload(identity, ".npz")), allow_pickle=False) as archive:
            return {name: archive[name] for name in archive.files}
