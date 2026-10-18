"""Observations have no scientific acceptance flag or fabricated credit."""

from dataclasses import dataclass
from collections.abc import Mapping
import json
from types import MappingProxyType

from method_loop import ClosedRecord


def plain(value):
    if isinstance(value, Mapping):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(item) for item in value]
    return value


def freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({key: freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class Observation(ClosedRecord):
    operation: str
    findings: Mapping
    artifacts: tuple[str, ...] = ()

    def __post_init__(self):
        data = json.loads(json.dumps(plain(self.findings), allow_nan=False))
        object.__setattr__(self, "findings", freeze(data))

    def as_record(self):
        return {"operation": self.operation, "findings": plain(self.findings),
                "artifacts": list(self.artifacts)}

    def audit_identifiers(self):
        return self.artifacts


@dataclass(frozen=True)
class Findings(ClosedRecord):
    observations: tuple[Observation, ...]
    ended_by: str

    def as_record(self):
        return {"observations": [item.as_record() for item in self.observations],
                "ended_by": self.ended_by, "credit": None}

    def audit_identifiers(self):
        return tuple(dict.fromkeys(ref for item in self.observations for ref in item.artifacts))

    def synthesis(self):
        return [{"operation": item.operation, "measurements": plain(item.findings)}
                for item in self.observations]
