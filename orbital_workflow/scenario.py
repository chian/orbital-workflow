"""One immutable scenario owns public simulator execution parameters.

The public capability accepts ship velocity and, for simparts, explicit derived
experiments. Complete SimulationRequest records remain a private engine/replay
interface; they are never interpreted as public proposals.
"""

from collections.abc import Mapping
from dataclasses import asdict, replace
import hashlib
import json
import math
from numbers import Real
import re
from types import MappingProxyType

from .failures import ActionRequestError
from .gravity import GravitySystem, scenario_problem
from .persistence import PersistenceSettings
from .simulation import ExperimentScope, ModelTerms, SimulationRequest, generate_forcing


def _plain(value):
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


def _freeze(value):
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(item) for item in value)
    return value


def _invalid(field):
    if not isinstance(field, str) or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.:-]{0,127}", field) is None:
        field = "arguments"
    raise ActionRequestError("wrong_parameters", tool="sim.run", field=field)


def _number(value, field):
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        _invalid(field)
    return float(value)


def is_base_observation(arguments, problem, *, forcing_seed=None, require_full_interval=True):
    """Pure scope predicate over executed machine values; no objects generated.

    Full-interval numerical refinements still measure the same base problem.
    A physically early termination does not change its requested interval.
    """
    try:
        args, fixed = _plain(arguments), _plain(problem)
        seed = args.get("forcing_seed") if forcing_seed is None else forcing_seed
        if isinstance(seed, str) and seed.isdecimal():
            seed = int(seed)
        if type(seed) is not int or seed != fixed["forcing"]["seed"]:
            return False
        if any(args.get(key) != fixed[key] for key in (
                "a", "sigma", "modulation_frequency", "rotating_amplitude", "rotating_frequency")):
            return False
        if args.get("scenario_id") != fixed["id"] or args.get("gravity") != fixed["gravity"]:
            return False
        if (args.get("forcing_grid_step") != fixed["forcing"]["grid_step"]
                or args.get("forcing_ar_decay") != fixed["forcing"]["ar_decay"]):
            return False
        gravity = GravitySystem.from_record(fixed["gravity"])
        active = args.get("active_bodies")
        if (active is not None and sorted(active) != sorted(gravity.body_ids)):
            return False
        if (args.get("gravity_mode") not in {"resolved", "monopole"}
                or (args.get("gravity_mode") != "resolved" and gravity.kind != "single")):
            return False
        if args.get("terms") != asdict(ModelTerms()) or args.get("spatial_box") is not None:
            return False
        if args.get("radial_limits") != fixed["radial_limits"]:
            return False
        window = fixed["evaluation_interval"]
        if args.get("observation_window") != window:
            return False
        start, end = args["start"], args["end"]
        if not window[0] <= start < end <= window[1]:
            return False
        if require_full_interval and [start, end] != window:
            return False
        if start == window[0]:
            return args["initial_state"][:2] == fixed["initial_position"]
        return not require_full_interval and args.get("experiment", {}).get("source_observation") is not None
    except (KeyError, TypeError, ValueError):
        return False


class ScenarioSimulator:
    def __init__(self, settings, store=None):
        self._problem = _freeze(scenario_problem(settings))
        self.store = store
        self.persistence_settings = PersistenceSettings(**self.problem["persistence"])
        problem = _plain(self.problem)
        self._base = SimulationRequest("scenario_forcing_not_loaded",
            scenario_id=problem["id"], gravity=GravitySystem.from_record(problem["gravity"]),
            initial_state=(*problem["initial_position"], *problem["reference_velocity"]),
            start=problem["evaluation_interval"][0], end=problem["evaluation_interval"][1],
            a=problem["a"], sigma=problem["sigma"],
            modulation_frequency=problem["modulation_frequency"],
            rotating_amplitude=problem["rotating_amplitude"], rotating_frequency=problem["rotating_frequency"],
            forcing_seed=problem["forcing"]["seed"], forcing_grid_step=problem["forcing"]["grid_step"],
            forcing_ar_decay=problem["forcing"]["ar_decay"], radial_limits=tuple(problem["radial_limits"]),
            observation_window=tuple(problem["evaluation_interval"]), **problem["numerics"])
        self._forcing_id = None

    @property
    def problem(self):
        return self._problem

    def describe(self):
        """Read-only scientific interface; fixed engine settings are not knobs."""
        return {"scenario_id": self.problem["id"], "name": self.problem["name"],
            "ship_fields": ["vx", "vy"], "initial_position": _plain(self.problem["initial_position"]),
            "reference_velocity": _plain(self.problem["reference_velocity"]),
            "evaluation_interval": _plain(self.problem["evaluation_interval"]),
            "ordinary_run": "Supply exactly vx and vy. The simulator owns the fixed scenario and forcing.",
            "parts_experiment": {
                "terms": "Partial boolean mask: central, modulation, rotating, forcing",
                "active_bodies": "Declared source IDs to include: " + ", ".join(self._base.gravity.body_ids),
                "gravity_mode": ["resolved", "monopole"],
                "spatial_box": "Four bounds [xmin,xmax,ymin,ymax] for a regional observation",
                "radial_limits": "Two bounds [inner,outer] for a radial observation scope",
                "interval": "Absolute [start,end] inside the scenario evaluation interval",
                "refinement": "Explicit method, max_step, rtol, atol and/or sample_step values",
                "continuation": "{run_index: local saved run index, end: absolute endpoint}; omit vx/vy and interval"}}

    def _forcing(self):
        if self._forcing_id is None:
            if self.store is None:
                raise RuntimeError("Scenario execution requires its artifact store")
            self._forcing_id = generate_forcing(self.store, horizon=self._base.end,
                seed=self._base.forcing_seed, grid_step=self._base.forcing_grid_step,
                ar_decay=self._base.forcing_ar_decay)
        return self._forcing_id

    def resolve_numeric(self, arguments):
        """Resolve public mathematical queries against this same fixed scenario."""
        def invalid(field, category="wrong_parameters"):
            raise ActionRequestError(category, tool="math.numeric", field=field)

        if not isinstance(arguments, Mapping):
            invalid("arguments")
        args = _plain(arguments)
        operation = args.get("operation")
        fields = {
            "central_circular_reference": ({"radius"}, set()),
            "central_candidate": ({"vx", "vy"}, set()),
            "binary_reference": (set(), {"time", "position"}),
            "local_velocity_fit": ({"points"}, set()),
        }
        if operation not in fields:
            invalid("operation", "wrong_command")
        required, optional = fields[operation]
        extra = set(args) - {"operation"} - required - optional
        missing = required - set(args)
        if extra or missing:
            invalid(sorted(extra or missing)[0])
        if operation == "binary_reference":
            time = args.get("time", self.problem["evaluation_interval"][0])
            position = args.get("position", _plain(self.problem["initial_position"]))
            if isinstance(time, bool) or not isinstance(time, Real) or not math.isfinite(time):
                invalid("time")
            if (not isinstance(position, (list, tuple)) or len(position) != 2
                    or any(isinstance(x, bool) or not isinstance(x, Real) or not math.isfinite(x)
                           for x in position)):
                invalid("position")
            args.update(time=float(time), position=[float(x) for x in position],
                        gravity=_plain(self.problem["gravity"]))
        return args

    def resolve_run(self, arguments, *, parts=False, continuation_lookup=None):
        if not isinstance(arguments, Mapping):
            _invalid("arguments")
        args = _plain(arguments)
        if any(not isinstance(key, str) for key in args):
            _invalid("arguments")
        allowed = {"vx", "vy", "experiment"} if parts else {"vx", "vy"}
        if set(args) - allowed:
            _invalid(next(iter(sorted(set(args) - allowed))))
        experiment = args.get("experiment", {})
        if not isinstance(experiment, dict):
            _invalid("experiment")
        fields = {"terms", "active_bodies", "gravity_mode", "spatial_box", "radial_limits",
                  "interval", "refinement", "continuation"}
        if set(experiment) - fields:
            _invalid("experiment." + next(iter(sorted(set(experiment) - fields))))
        changes, operations = {}, []
        source_observation = source_index = None
        base = self._base
        if "continuation" in experiment:
            if "vx" in args or "vy" in args or "interval" in experiment:
                _invalid("experiment.continuation")
            continuation = experiment["continuation"]
            if (not isinstance(continuation, dict) or set(continuation) != {"run_index", "end"}
                    or type(continuation["run_index"]) is not int or continuation["run_index"] < 1
                    or continuation_lookup is None):
                _invalid("experiment.continuation")
            source_index = continuation["run_index"]
            source = _plain(continuation_lookup(source_index))
            try:
                previous = SimulationRequest.from_record(source["request"])
                if any(getattr(previous, key) != getattr(base, key) for key in (
                        "scenario_id", "gravity", "a", "sigma", "modulation_frequency", "rotating_amplitude",
                        "rotating_frequency", "forcing_seed", "forcing_grid_step", "forcing_ar_decay", "observation_window")):
                    _invalid("experiment.continuation")
                if previous.forcing_id != self._forcing():
                    _invalid("experiment.continuation")
                changes.update(initial_state=tuple(source["summary"]["terminal_state"]),
                    start=source["summary"]["observed_interval"][1], end=_number(continuation["end"], "experiment.continuation.end"))
                source_observation = "artifact_" + hashlib.sha256(json.dumps(source, sort_keys=True, allow_nan=False).encode()).hexdigest()
                base = previous
            except ActionRequestError:
                raise
            except (KeyError, TypeError):
                _invalid("experiment.continuation")
            operations.append("continuation")
        else:
            if not {"vx", "vy"} <= set(args):
                _invalid("vx" if "vx" not in args else "vy")
            changes["initial_state"] = (*self.problem["initial_position"], _number(args["vx"], "vx"), _number(args["vy"], "vy"))
        mapping = {"terms": "term_mask", "active_bodies": "sources", "gravity_mode": "approximation",
                   "spatial_box": "region", "radial_limits": "radial_scope", "interval": "interval", "refinement": "refinement"}
        for key, operation in mapping.items():
            if key not in experiment:
                continue
            value = experiment[key]
            operations.append(operation)
            if key == "terms":
                if not isinstance(value, dict) or set(value) - set(asdict(ModelTerms())):
                    _invalid("experiment.terms")
                try:
                    changes["terms"] = ModelTerms(**{**asdict(base.terms), **value})
                except (TypeError, ValueError):
                    _invalid("experiment.terms")
            elif key == "interval":
                if not isinstance(value, list) or len(value) != 2:
                    _invalid("experiment.interval")
                changes["start"], changes["end"] = (_number(item, "experiment.interval") for item in value)
            elif key == "refinement":
                if not isinstance(value, dict) or set(value) - set(self.problem["numerics"]):
                    _invalid("experiment.refinement")
                for field, item in value.items():
                    if field == "method":
                        if item not in ("RK23", "RK45", "DOP853", "Radau", "BDF", "LSODA"):
                            _invalid("experiment.refinement.method")
                        changes[field] = item
                    else:
                        changes[field] = _number(item, "experiment.refinement." + field)
                        if changes[field] <= 0:
                            _invalid("experiment.refinement." + field)
            elif key == "active_bodies":
                if (not isinstance(value, list) or any(not isinstance(item, str) for item in value)
                        or len(set(value)) != len(value) or set(value) - set(self._base.gravity.body_ids)):
                    _invalid("experiment.active_bodies")
                changes[key] = tuple(value)
            elif key == "gravity_mode":
                if value not in ("resolved", "monopole"):
                    _invalid("experiment.gravity_mode")
                changes[key] = value
            elif key in {"spatial_box", "radial_limits"}:
                if key == "spatial_box" and value is None:
                    changes[key] = None
                    continue
                count = 4 if key == "spatial_box" else 2
                if not isinstance(value, list) or len(value) != count:
                    _invalid("experiment." + key)
                values = tuple(_number(item, "experiment." + key) for item in value)
                if ((key == "spatial_box" and not (values[0] < values[1] and values[2] < values[3]))
                        or (key == "radial_limits" and not 0 <= values[0] < values[1])):
                    _invalid("experiment." + key)
                changes[key] = values
            else:
                changes[key] = value
        changes["experiment"] = ExperimentScope("derived" if operations else "base", tuple(operations), source_observation, source_index)
        start, end = changes.get("start", base.start), changes.get("end", base.end)
        if not self._base.start <= start < end <= self._base.end:
            _invalid("experiment.interval")
        request = replace(base, **changes)
        return asdict(replace(request, forcing_id=self._forcing()))

    def is_base_observation(self, arguments, *, require_full_interval=True):
        return is_base_observation(arguments, self.problem, require_full_interval=require_full_interval)
