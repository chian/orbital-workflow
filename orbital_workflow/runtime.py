"""Compose the real method_loop; sources and scientific bindings stay injectable."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
import json
import inspect
from pathlib import Path
from typing import Protocol

from method_loop import (
    ChildEpisodeUnit, ClosedRecord, Context, ControllerFactory, Episode,
    EpisodeCompletion, EpisodeGoal, EpisodeRecord, EpisodeRequest, EpisodeTree,
    EpisodeView, Grain, Leaf, SourceEnd,
)

from .communication import ReportBoundaryError, ReportContract
from .records import Findings, Observation
from .tools import ToolDispatcher
from .storage import EpisodeStore
from .archival import ReleasingContext, ReleasingRuntime, StoredChildEpisodeUnit


class Kind(StrEnum):
    ROOT = "spaceship_trajectory_search"
    MATH = "mathematical_exploration"
    SIMULATION = "simulation_investigation"
    PARTS = "simparts"


CAPABILITIES = {
    Kind.ROOT: (),
    Kind.MATH: ("math.numeric", "math.symbolic", "math.lean"),
    Kind.SIMULATION: ("sim.run", "sim.compare"),
    Kind.PARTS: ("sim.run", "sim.compare"),
}


@dataclass(frozen=True)
class ToolAction:
    label: str
    tool: str
    arguments: dict


class ActionSource(Protocol):
    def next(self, view: EpisodeView): ...


@dataclass(frozen=True)
class EpisodeSpec:
    kind: Kind
    key: str
    objective: str
    assignment: Observation
    source_factory: Callable[[EpisodeRequest], ActionSource]


@dataclass(frozen=True)
class ChildAction:
    spec: EpisodeSpec
    report_contract: ReportContract
    project_credit: Callable[[ClosedRecord, EpisodeCompletion, EpisodeRequest], ClosedRecord]
    synthesize_report: Callable[[ClosedRecord, EpisodeCompletion, EpisodeRequest], dict]


@dataclass(frozen=True)
class EpisodeBindings:
    controller: ControllerFactory
    project_tool: Callable[[Observation, EpisodeRequest], ClosedRecord]
    build_result: Callable[[EpisodeRecord], ClosedRecord]
    release: Callable | None = None


class _Source:
    def __init__(self, runtime, spec, request):
        self.runtime, self.spec, self.request = runtime, spec, request
        self.policy = spec.source_factory(request)

    def next(self, view):
        self.runtime.active_paths[self.request.goal.goal_id] = view.path
        self.runtime.episode_paths[view.episode_ref.episode_id] = view.path
        action = self.policy.next(view)
        if inspect.isawaitable(action):
            return self._next_async(action)
        return self._wrap(action)

    async def _next_async(self, action):
        return self._wrap(await action)

    def _wrap(self, action):
        if action is None or isinstance(action, SourceEnd):
            return action
        if isinstance(action, ChildAction):
            if not isinstance(action.report_contract, ReportContract):
                raise ReportBoundaryError("Child invocations require a typed parent report contract")
            child = self.runtime.build(action.spec, parent=self.request.goal,
                                       report_contract=action.report_contract)
            return StoredChildEpisodeUnit(child, action.project_credit, action.synthesize_report,
                                          self.runtime)
        if not isinstance(action, ToolAction):
            raise TypeError("Sources return ToolAction, ChildAction, SourceEnd, or None")
        if action.tool not in CAPABILITIES[self.spec.kind]:
            raise ValueError(f"{action.tool} is not a declared tool for {self.spec.kind}")
        binding = self.runtime.bindings[self.spec.kind]
        return Leaf(unit=action, label=action.label,
                    extract=lambda call: self.runtime.tools.execute(call.tool, call.arguments),
                    result=lambda call, observation: binding.project_tool(observation, self.request))


class Workflow:
    def __init__(self, bindings: dict[Kind, EpisodeBindings], tools: ToolDispatcher,
                 audit_directory: Path):
        self.bindings, self.tools = bindings, tools
        self.audit_directory = audit_directory
        audit_directory.mkdir(parents=True, exist_ok=True)
        self.storage = EpisodeStore(audit_directory.parent)
        self.active_paths, self.episode_paths = {}, {}
        self.grains = {
            kind: Grain(name=kind.value, unit="One investigation contribution",
                        result="Measurements and contracted scientific findings",
                        controller=bindings[kind].controller)
            for kind in Kind
        }
        root, math, sim, parts = (self.grains[kind] for kind in Kind)
        self.tree = EpisodeTree(root=root, children={
            root: (math, sim), math: (parts,), sim: (parts,), parts: (parts,),
        }, self_nesting=(parts.name,))

    def build(self, spec: EpisodeSpec, *, parent=None, report_contract=None):
        if parent is not None and not isinstance(report_contract, ReportContract):
            raise ReportBoundaryError("Child invocations require a typed parent report contract")
        contract = {"episode": spec.kind.value, "result": "scientific findings"}
        goal = (EpisodeGoal.root(objective=spec.objective, result_contract=contract)
                if parent is None else
                EpisodeGoal.child(parent, objective=spec.objective, result_contract=contract))
        request = EpisodeRequest(goal=goal, message=spec.assignment,
                                 report_contract=report_contract)
        source = _Source(self, spec, request)
        return Episode(grain=self.grains[spec.kind], key=spec.key, source=source,
                       request=request, build_result=self.bindings[spec.kind].build_result,
                       on_unit=self._record_unit, on_close=self._record_close)

    def _record_unit(self, item, contribution, view):
        self._publish_observations(item, view)
        event = {"unit": view.unit_ref.as_record(), "label": view.unit_label,
                 "controller_input": view.controller_input.as_record(),
                 "controller_step": view.controller_step.as_record(),
                 "child_report": (view.episode_update.report.as_record()
                                  if view.episode_update else None)}
        with (self.audit_directory / "units.jsonl").open("a") as stream:
            stream.write(json.dumps(event, allow_nan=False) + "\n")

    def _record_close(self, record):
        path = self.audit_directory / (record.episode_id + ".json")
        with path.open("x") as stream:
            json.dump(record.as_record(), stream, indent=2, allow_nan=False)
        self.storage.close_episode(record, path)

    def _publish_observations(self, item, view):
        if isinstance(item, Leaf) and isinstance(item.unit, ToolAction):
            path = self.episode_paths.get(view.unit_ref.episode_id, ())
            root_unit = None
            if len(path) > 1 and path[1][1].startswith("unit-"):
                root_unit = int(path[1][1].split("-")[1]) + 1
            self.storage.observe(view.controller_input.audit_identifiers(),
                view.unit_ref.episode_id, view.unit_ref.unit_id,
                origin={"episode": path[-1][0] if path else None,
                        "investigation": root_unit, "action": view.unit_label})

    def _retire(self, child):
        path = self.active_paths.pop(child.goal.goal_id, None)
        if path is None:
            return None
        for episode_id, episode_path in tuple(self.episode_paths.items()):
            if episode_path == path:
                self.episode_paths.pop(episode_id)
        release = self.bindings[child.grain.name].release
        return release(path) if release else None

    def retire_child(self, child):
        result = self._retire(child)
        if inspect.isawaitable(result):
            result.close()
            raise TypeError("Asynchronous model retirement requires run_async")

    async def retire_child_async(self, child):
        result = self._retire(child)
        if inspect.isawaitable(result):
            await result

    def run(self, root: EpisodeSpec, run_id: str):
        context = ReleasingContext(tree=self.tree, run_id=run_id, runtime=ReleasingRuntime())
        episode = self.build(root)
        try:
            record = episode.run(context)
            result = episode.build_result(record)
            self.storage.finish_episode(record, result, None)
            return record, result
        finally:
            self.retire_child(episode)

    async def run_async(self, root: EpisodeSpec, run_id: str):
        context = ReleasingContext(tree=self.tree, run_id=run_id, runtime=ReleasingRuntime())
        episode = self.build(root)
        try:
            record = await episode.run_async(context)
            result = episode.build_result(record)
            result = await result if inspect.isawaitable(result) else result
            self.storage.finish_episode(record, result, None)
            return record, result
        finally:
            await self.retire_child_async(episode)


# The following bindings are diagnostic only. They assign no credit and make
# no yield-based stopping decision. A finite probe may exhaust its source.
@dataclass(frozen=True)
class DiagnosticStep:
    observations: int
    stop: bool = False
    requests_transition: bool = False

    def as_record(self):
        return {"binding": "diagnostic_unscored", "observations": self.observations,
                "credit": None, "projected_credit": None,
                "stop": self.stop, "requests_transition": self.requests_transition}


class DiagnosticController:
    def __init__(self, epoch="diagnostic"):
        self.epoch = epoch
        self.observations = 0

    def observe(self, unit_label, value, *, is_root):
        self.observations += 1
        return self.state()

    def state(self):
        return DiagnosticStep(self.observations)

    def transitioned(self, epoch):
        raise NotImplementedError("Diagnostic probes do not define scientific epochs")


def diagnostic_bindings():
    def result(record):
        return Findings(tuple(unit.controller_input for unit in record.unit_records),
                        record.ended_by)

    return {kind: EpisodeBindings(lambda path: DiagnosticController(),
                                  lambda observation, request: observation, result)
            for kind in Kind}


def diagnostic_child(spec: EpisodeSpec, decision: str):
    contract = ReportContract(decision=decision, measurements={"observations":
        "Physical and numerical observations; scientific credit is not bound"},
        information={"tool_counts": "Counts of executed diagnostic operations; no scientific credit",
                     "ended_by": "Method-owned diagnostic termination"},
        value_schema={"type": "object", "additionalProperties": False,
            "required": ["tool_counts", "ended_by"], "properties": {
                "tool_counts": {"type": "array", "items": {"type": "object",
                    "additionalProperties": False, "required": ["tool", "count"], "properties": {
                        "tool": {"type": "string", "enum": ["sim.run", "sim.compare", "math.numeric", "math.symbolic", "math.lean", "child_contribution"]},
                        "count": {"type": "integer"}}}},
                "ended_by": {"type": "string", "enum": ["exhausted", "yield_stop", "incomplete", "source_failed"]}}})

    def projection(result, completion, request):
        from collections import Counter
        return Observation("child_contribution", {"tool_counts": dict(Counter(
            item.operation for item in result.observations)),
                           "ended_by": completion.ended_by, "credit": None},
                           result.audit_identifiers())

    def report(result, completion, request):
        from collections import Counter
        counts = Counter(item.operation for item in result.observations)
        return {"tool_counts": [{"tool": tool, "count": count} for tool, count in sorted(counts.items())],
                "ended_by": completion.ended_by}

    return ChildAction(spec, contract, projection, report)
