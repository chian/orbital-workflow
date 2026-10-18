"""Local immutable inputs and observations, separate from upward reports."""

import hashlib
import io
import json
from pathlib import Path

import numpy as np


class Artifacts:
    def __init__(self, directory: Path):
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)

    def _put(self, payload: bytes, suffix: str) -> str:
        identity = "artifact_" + hashlib.sha256(payload).hexdigest()
        path = self.directory / (identity + suffix)
        if not path.exists():
            # Exclusive creation prevents an observation replacing an input.
            with path.open("xb") as stream:
                stream.write(payload)
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
