"""Spool completed child audit data after the real method_loop delivers its report."""

from dataclasses import dataclass, fields, replace

from method_loop import ChildEpisodeUnit, ClosedRecord, Context, EpisodeRecord
from method_loop.runtime import ControllerRuntime


@dataclass(frozen=True)
class ArchivedEpisodeRecord(EpisodeRecord):
    record_file: str = ""

    @classmethod
    def from_record(cls, record, record_file):
        values = {field.name: getattr(record, field.name) for field in fields(EpisodeRecord)}
        values["unit_records"] = ()
        return cls(**values, record_file=record_file)

    def as_record(self):
        return {**super().as_record(), "storage_format": "orbital.episode-ref/v1",
                "record_file": self.record_file, "unit_records_archived": True}


@dataclass(frozen=True)
class ArchivedResult(ClosedRecord):
    result_file: str
    identifiers: tuple[str, ...]

    def as_record(self):
        return {"storage_format": "orbital.result-ref/v1", "result_file": self.result_file,
                "artifacts": list(self.identifiers)}

    def audit_identifiers(self):
        return (*self.identifiers, self.result_file)


class ReleasingRuntime(ControllerRuntime):
    def __init__(self):
        super().__init__()
        self.seen_scopes = set()

    def open_scope(self, path, factory):
        scope = self._normalize_path(path)
        if scope in self.seen_scopes:
            raise ValueError(f"scope already used at path {scope!r}")
        result = super().open_scope(scope, factory)
        self.seen_scopes.add(scope)
        return result

    def close_scope(self, scope):
        self._controllers.pop(scope, None)


class ReleasingContext(Context):
    def leave(self, scope):
        super().leave(scope)
        # The core exposes runtime injection, but no closed-scope retirement API.
        # This local adapter releases only state belonging to the closed scope.
        self._child_updates.pop(scope, None)
        self.runtime.close_scope(scope)


@dataclass(frozen=True)
class StoredChildEpisodeUnit(ChildEpisodeUnit):
    owner: object

    def acquire(self, ctx):
        try:
            acquired = super().acquire(ctx)
            return self._archive(acquired)
        finally:
            self.owner.retire_child(self.child)

    async def acquire_async(self, ctx):
        try:
            acquired = await super().acquire_async(ctx)
            return self._archive(acquired)
        finally:
            await self.owner.retire_child_async(self.child)

    def _archive(self, acquired):
        record = acquired.child_record
        result = acquired.child_result
        result_file = self.owner.storage.finish_episode(record, result, acquired.contribution.episode_update.report)
        return replace(acquired,
            child_record=ArchivedEpisodeRecord.from_record(record,
                self.owner.storage.relative(self.owner.audit_directory / (record.episode_id + ".json"))),
            child_result=ArchivedResult(result_file, result.audit_identifiers()))
