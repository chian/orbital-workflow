"""Fixed dynamics with explicit reductions and observation scopes.

This tool performs a specified integration, not an Episode's adaptive search.
Numerical diagnostics are measurements, never scientific acceptance decisions.
"""

from dataclasses import asdict, dataclass
import math
from numbers import Real

import numpy as np
from scipy.integrate import solve_ivp

from .artifacts import Artifacts
from .persistence import PersistenceSettings, measure_persistence


@dataclass(frozen=True)
class ModelTerms:
    central: bool = True
    modulation: bool = True
    rotating: bool = True
    forcing: bool = True

    def __post_init__(self):
        if any(type(value) is not bool for value in asdict(self).values()):
            raise ValueError("Model-term switches must be JSON booleans")


@dataclass(frozen=True)
class SimulationRequest:
    forcing_id: str
    initial_state: tuple[float, float, float, float] = (1.0, 0.0, 0.0, 1.0)
    start: float = 0.0
    end: float = 40 * math.pi
    a: float = 0.15
    sigma: float = 0.03
    terms: ModelTerms = ModelTerms()
    method: str = "DOP853"
    max_step: float = 0.05
    rtol: float = 1e-7
    atol: float = 1e-9
    sample_step: float = 0.02
    radial_limits: tuple[float, float] = (0.5, 2.0)
    # A box restricts observation; it does not truncate the physical field.
    spatial_box: tuple[float, float, float, float] | None = None

    @classmethod
    def from_record(cls, value):
        data = dict(value)
        data["terms"] = ModelTerms(**data.get("terms", {}))
        for name in ("initial_state", "radial_limits", "spatial_box"):
            if data.get(name) is not None:
                data[name] = tuple(data[name])
        return cls(**data)

    def __post_init__(self):
        def finite_number(value):
            if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
                raise ValueError("Simulation inputs must be finite real numbers")
            return float(value)

        # Numerically identical JSON spellings have one physical identity.
        # bools are not accepted as numeric simulation inputs.
        for name in ("start", "end", "a", "sigma", "max_step", "rtol", "atol", "sample_step"):
            object.__setattr__(self, name, finite_number(getattr(self, name)))
        for name in ("initial_state", "radial_limits", "spatial_box"):
            values = getattr(self, name)
            if values is not None:
                object.__setattr__(self, name, tuple(finite_number(value) for value in values))
        if not isinstance(self.terms, ModelTerms):
            raise ValueError("Simulation terms require declared boolean switches")
        if not 0 <= self.start < self.end:
            raise ValueError("Observation requires 0 <= start < end")
        if len(self.initial_state) != 4 or not np.all(np.isfinite(self.initial_state)):
            raise ValueError("State must contain finite x, y, vx, vy")
        if not all(math.isfinite(x) for x in (self.a, self.sigma, self.end)):
            raise ValueError("Environment and horizon must be finite")
        if not all(math.isfinite(x) and x > 0 for x in (self.max_step, self.rtol, self.atol, self.sample_step)):
            raise ValueError("Numerical step and tolerances must be positive and finite")
        if len(self.radial_limits) != 2 or not 0 < self.radial_limits[0] < self.radial_limits[1]:
            raise ValueError("Radial observation limits must be positive and ordered")
        if self.spatial_box is not None:
            if len(self.spatial_box) != 4:
                raise ValueError("Spatial box requires xmin, xmax, ymin, ymax")
            xmin, xmax, ymin, ymax = self.spatial_box
            if not xmin < xmax or not ymin < ymax:
                raise ValueError("Spatial box limits must be ordered")


@dataclass
class Trajectory:
    request: SimulationRequest
    times: np.ndarray
    states: np.ndarray
    outcome: str
    message: str
    evaluations: int

    def summary(self, persistence_settings: PersistenceSettings | None = None):
        radius = np.linalg.norm(self.states[:, :2], axis=1)
        return {
            "environment": {"a": self.request.a, "sigma": self.request.sigma},
            "terms": asdict(self.request.terms),
            "initial_state": list(self.request.initial_state),
            "requested_interval": [self.request.start, self.request.end],
            "observed_interval": [float(self.times[0]), float(self.times[-1])],
            "radial_limits": list(self.request.radial_limits),
            "spatial_box": self.request.spatial_box,
            "outcome": self.outcome,
            "terminal_state": self.states[-1].tolist(),
            "radius_min": float(radius.min()), "radius_max": float(radius.max()),
            "rhs_evaluations": self.evaluations, "solver_message": self.message,
            "numerical_settings": {"method": self.request.method,
                                   "max_step": self.request.max_step,
                                   "rtol": self.request.rtol, "atol": self.request.atol,
                                   "sample_step": self.request.sample_step},
            "persistence_measurement": measure_persistence(self.times, self.states, persistence_settings),
        }


def generate_forcing(store: Artifacts, trial: int, horizon: float) -> str:
    if type(trial) is not int or trial < 1:
        raise ValueError("Trial numbers start at 1")
    if not math.isfinite(horizon) or horizon <= 0:
        raise ValueError("Forcing horizon must be positive and finite")
    seed = 20261005 + trial
    generator = np.random.Generator(np.random.PCG64DXSM(seed))
    times = 0.1 * np.arange(math.ceil(horizon / 0.1) + 1, dtype=np.float64)
    z = generator.standard_normal((len(times), 2), dtype=np.float64)
    eta = np.empty_like(z)
    eta[0] = z[0]
    rho = math.exp(-0.2)
    scale = math.sqrt(1 - rho * rho)
    for j in range(1, len(times)):
        eta[j] = rho * eta[j - 1] + scale * z[j]
    return store.put_arrays(times=times, eta=eta, seed=np.array(seed),
                            generator=np.array("PCG64DXSM"),
                            gaussian_sampler=np.array("Generator.standard_normal(float64)"),
                            numpy_version=np.array(np.__version__))


def _events(request):
    low, high = request.radial_limits
    functions = [lambda t, s: np.hypot(s[0], s[1]) - low,
                 lambda t, s: high - np.hypot(s[0], s[1])]
    names = ["inner_exit", "outer_exit"]
    if request.spatial_box is not None:
        xmin, xmax, ymin, ymax = request.spatial_box
        functions.extend([lambda t, s: s[0] - xmin, lambda t, s: xmax - s[0],
                          lambda t, s: s[1] - ymin, lambda t, s: ymax - s[1]])
        names.extend(["region_exit"] * 4)
    for function in functions:
        function.terminal = True
        function.direction = -1
    return functions, names


def integrate(request: SimulationRequest, store: Artifacts) -> Trajectory:
    saved = store.arrays(request.forcing_id)
    times, eta = saved["times"], saved["eta"]
    if times[0] > request.start or times[-1] < request.end:
        raise ValueError("Stored forcing must bracket the complete observation")
    state = np.array(request.initial_state, dtype=np.float64)
    events, names = _events(request)
    for event, name in zip(events, names):
        if event(request.start, state) <= 0:
            return Trajectory(request, np.array([request.start]), state[None, :], name,
                              "Initial state lies on or outside observation boundary", 0)

    def rhs(t, s):
        x, y, vx, vy = s
        ax = ay = 0.0
        if request.terms.central:
            strength = 1 + (request.a * math.sin(0.7 * t) if request.terms.modulation else 0)
            factor = -strength / math.hypot(x, y) ** 3
            ax, ay = factor * x, factor * y
        if request.terms.rotating:
            c, d = math.cos(0.4 * t), math.sin(0.4 * t)
            ax += 0.02 * (c * x + d * y)
            ay += 0.02 * (d * x - c * y)
        if request.terms.forcing:
            ax += request.sigma * np.interp(t, times, eta[:, 0])
            ay += request.sigma * np.interp(t, times, eta[:, 1])
        return vx, vy, ax, ay

    # Every solve interval ends at an interpolation knot. Absolute time is retained
    # for continuation, periodic fields, and forcing lookup.
    internal = times[(times > request.start) & (times < request.end)]
    nodes = np.concatenate(([request.start], internal, [request.end]))
    output_grid = request.sample_step * np.arange(math.ceil(request.end / request.sample_step) + 1)
    sample_times = [request.start]
    sample_states = [state.copy()]
    evaluations = 0
    outcome, message = "horizon_reached", "Requested observation horizon reached"
    for left, right in zip(nodes[:-1], nodes[1:]):
        solution = solve_ivp(rhs, (left, right), state, method=request.method,
                             max_step=request.max_step, rtol=request.rtol,
                             atol=request.atol, events=events, dense_output=True)
        evaluations += solution.nfev
        state = solution.y[:, -1]
        terminal_time = float(solution.t[-1])
        selected = output_grid[(output_grid > left) & (output_grid < terminal_time)]
        sampled_states = solution.sol(selected).T if len(selected) else np.empty((0, 4))
        for timestamp, sample in zip(selected, sampled_states):
            if timestamp > sample_times[-1]:
                sample_times.append(float(timestamp))
                sample_states.append(sample.copy())
        if terminal_time > sample_times[-1]:
            sample_times.append(terminal_time)
            sample_states.append(state.copy())
        if not solution.success:
            outcome, message = "solver_error", solution.message
            break
        if solution.status == 1:
            outcome = next(name for name, values in zip(names, solution.t_events) if len(values))
            message = solution.message
            break
    return Trajectory(request, np.array(sample_times), np.array(sample_states),
                      outcome, message, evaluations)


def compare(left: Trajectory, right: Trajectory,
            persistence_settings: PersistenceSettings | None = None):
    # Compare only actually saved common times; no invented interpolation accuracy.
    common, il, ir = np.intersect1d(left.times, right.times, return_indices=True)
    difference = np.abs(left.states[il] - right.states[ir])
    return {
        "left": left.summary(persistence_settings), "right": right.summary(persistence_settings),
        "common_time_count": len(common),
        "common_interval": [float(common[0]), float(common[-1])] if len(common) else None,
        "max_absolute_component_difference": difference.max(axis=0).tolist() if len(common) else None,
        "terminal_time_difference": abs(float(left.times[-1] - right.times[-1])),
        "comparison_scope": "saved common times only; no acceptance threshold",
    }
