"""Episode-facing tool dispatch; all integrations and their inputs are retained."""

from dataclasses import asdict
import ast
import math
from numbers import Real
import operator
import re
import shutil
import subprocess
import tempfile
from typing import Callable

from .artifacts import Artifacts
from .records import Observation
from .persistence import PersistenceSettings
from .simulation import SimulationRequest, compare, integrate
from .gravity import GravitySystem
from .failures import ActionRequestError, ToolAcquisitionFailure, TOOL_NAMES, failure_diagnostic


_ARITHMETIC_FUNCTIONS = {
    "log": (math.log, (1, 2)), "log2": (math.log2, (1,)),
    "log10": (math.log10, (1,)), "sqrt": (math.sqrt, (1,)),
    "abs": (abs, (1,)), "exp": (math.exp, (1,)),
    "sin": (math.sin, (1,)), "cos": (math.cos, (1,)),
}
_ARITHMETIC_BINARY = {ast.Add: operator.add, ast.Sub: operator.sub,
                      ast.Mult: operator.mul, ast.Div: operator.truediv,
                      ast.Pow: math.pow}
_ARITHMETIC_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
# Bounds apply to one scalar expression, never to Episode iteration or depth.
_ARITHMETIC_MAX_CHARACTERS = 1024
_ARITHMETIC_MAX_NODES = 128
_ARITHMETIC_MAX_DEPTH = 32


class _ArithmeticDiagnostic(Exception):
    def __init__(self, code):
        self.code = code


def _arithmetic_tree(expression):
    if len(expression) > _ARITHMETIC_MAX_CHARACTERS:
        raise _ArithmeticDiagnostic("expression_limit")
    try:
        tree = ast.parse(expression, mode="eval")
    except (SyntaxError, ValueError):
        raise _ArithmeticDiagnostic("invalid_expression") from None
    pending, count = [(tree, 0)], 0
    while pending:
        node, depth = pending.pop()
        count += 1
        if count > _ARITHMETIC_MAX_NODES or depth > _ARITHMETIC_MAX_DEPTH:
            raise _ArithmeticDiagnostic("expression_limit")
        pending.extend((child, depth + 1) for child in ast.iter_child_nodes(node))

    def validate(node):
        if isinstance(node, ast.Expression):
            validate(node.body)
        elif isinstance(node, ast.Constant) and type(node.value) in (int, float):
            pass
        elif isinstance(node, ast.Name):
            pass
        elif isinstance(node, ast.BinOp) and type(node.op) in _ARITHMETIC_BINARY:
            validate(node.left)
            validate(node.right)
        elif isinstance(node, ast.UnaryOp) and type(node.op) in _ARITHMETIC_UNARY:
            validate(node.operand)
        elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
              and node.func.id in _ARITHMETIC_FUNCTIONS and not node.keywords
              and len(node.args) in _ARITHMETIC_FUNCTIONS[node.func.id][1]):
            for argument in node.args:
                validate(argument)
        else:
            raise _ArithmeticDiagnostic("invalid_expression")

    validate(tree)
    return tree


def _arithmetic_value(node, values):
    if isinstance(node, ast.Expression):
        result = _arithmetic_value(node.body, values)
    elif isinstance(node, ast.Constant):
        result = float(node.value)
    elif isinstance(node, ast.Name):
        if node.id not in values:
            raise _ArithmeticDiagnostic("unknown_name")
        result = values[node.id]
    elif isinstance(node, ast.BinOp):
        result = _ARITHMETIC_BINARY[type(node.op)](
            _arithmetic_value(node.left, values), _arithmetic_value(node.right, values))
    elif isinstance(node, ast.UnaryOp):
        result = _ARITHMETIC_UNARY[type(node.op)](_arithmetic_value(node.operand, values))
    else:  # Calls were fully validated before any numerical evaluation.
        function = _ARITHMETIC_FUNCTIONS[node.func.id][0]
        result = function(*(_arithmetic_value(argument, values) for argument in node.args))
    if not math.isfinite(result):
        raise _ArithmeticDiagnostic("overflow")
    return float(result)


class ToolDispatcher:
    def __init__(self, store: Artifacts, persistence_settings: PersistenceSettings | None = None):
        self.store = store
        self.persistence_settings = persistence_settings or PersistenceSettings()
        self.handlers: dict[str, Callable] = {
            "sim.run": self.run_simulation,
            "sim.compare": self.compare_simulations,
            "math.arithmetic": self.arithmetic_calculation,
            "math.numeric": self.numeric_calculation,
            "math.symbolic": self.symbolic_calculation,
            "math.lean": self.lean_calculation,
        }

    def execute(self, name: str, arguments: dict) -> Observation:
        request_id = self.store.put_json({"tool": name, "arguments": arguments})
        try:
            if name not in self.handlers:
                raise ActionRequestError("wrong_command", field="tool_name")
            result = self.handlers[name](arguments)
        except Exception as error:
            error_id = self.store.put_json({"tool": name, "request": request_id,
                                           "execution_error": type(error).__name__,
                                           "message": str(error)})
            diagnostic = (error.diagnostic if isinstance(error, ActionRequestError) else
                          failure_diagnostic("unknown", tool=name if name in TOOL_NAMES else None))
            raise ToolAcquisitionFailure(diagnostic,
                audit_references=(request_id, error_id)) from error
        return Observation(result.operation, result.findings,
                           (request_id, *result.artifacts))

    def _run(self, request: SimulationRequest):
        trajectory = integrate(request, self.store)
        arrays_id = self.store.put_arrays(times=trajectory.times, states=trajectory.states)
        summary = trajectory.summary(self.persistence_settings)
        record_id = self.store.put_json({"request": asdict(request),
                                         "summary": summary,
                                         "trajectory": arrays_id})
        return summary, (request.forcing_id, arrays_id, record_id)

    def run_simulation(self, arguments):
        request = SimulationRequest.from_record(arguments)
        window = request.observation_window
        if window is not None and (request.start < window[0] or request.end > window[1]):
            findings = {"code": "outside_observation_window",
                        "requested_interval": [request.start, request.end],
                        "observation_window": list(window)}
            record = self.store.put_json({"operation": "sim.request_diagnostic", "findings": findings})
            return Observation("sim.request_diagnostic", findings, (record,))
        summary, artifacts = self._run(request)
        return Observation("sim.run", summary, artifacts)

    def compare_simulations(self, arguments):
        if set(arguments) != {"left", "right"}:
            raise ActionRequestError(tool="sim.compare")
        for side in ("left", "right"):
            if not isinstance(arguments[side], str):
                raise ActionRequestError(tool="sim.compare", field=side)
        observations, arrays, artifacts = {}, {}, []
        for side in ("left", "right"):
            reference = arguments[side]
            saved = self.store.json(reference)
            if not isinstance(saved, dict) or set(saved) != {"request", "summary", "trajectory"}:
                raise ActionRequestError(tool="sim.compare", field=side)
            observations[side] = saved
            arrays[side] = self.store.arrays(saved["trajectory"])
            artifacts.extend((saved["request"]["forcing_id"], saved["trajectory"], reference))
        findings = compare(observations["left"]["summary"],
            arrays["left"]["times"], arrays["left"]["states"],
            observations["right"]["summary"],
            arrays["right"]["times"], arrays["right"]["states"])
        findings["observation_references"] = dict(arguments)
        return Observation("sim.compare", findings, tuple(dict.fromkeys(artifacts)))

    def arithmetic_calculation(self, arguments):
        """One bounded scalar calculation over supplied values, without execution."""
        if not isinstance(arguments, dict) or set(arguments) != {"expression", "values"}:
            raise ActionRequestError(tool="math.arithmetic")
        expression, supplied = arguments["expression"], arguments["values"]
        if not isinstance(expression, str):
            raise ActionRequestError(tool="math.arithmetic", field="expression")
        if not isinstance(supplied, dict) or len(supplied) > 64:
            raise ActionRequestError(tool="math.arithmetic", field="values")
        values = {}
        for name, value in supplied.items():
            if (not isinstance(name, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,63}", name)
                    or isinstance(value, bool) or not isinstance(value, Real)):
                raise ActionRequestError(tool="math.arithmetic", field="values")
            try:
                number = float(value)
            except (ValueError, OverflowError):
                raise ActionRequestError(tool="math.arithmetic", field="values") from None
            if not math.isfinite(number):
                raise ActionRequestError(tool="math.arithmetic", field="values")
            values[name] = number
        result, code = None, "ok"
        try:
            result = _arithmetic_value(_arithmetic_tree(expression), values)
        except _ArithmeticDiagnostic as error:
            code = error.code
        except ZeroDivisionError:
            code = "division_by_zero"
        except ValueError:
            code = "domain_error"
        except OverflowError:
            code = "overflow"
        findings = {"expression": expression, "inputs": values,
                    "value": result, "diagnostic": {"code": code}}
        record = self.store.put_json({"operation": "math.arithmetic", "findings": findings})
        return Observation("math.arithmetic", findings, (record,))

    @staticmethod
    def numeric_calculation(arguments):
        # A concrete first tool operation. Additional operations are supplied by
        # the mathematical binding; this does not evaluate arbitrary Python.
        operation = arguments["operation"]
        if operation == "binary_reference":
            gravity = GravitySystem.from_record(arguments["gravity"])
            time = float(arguments.get("time", 0))
            position = tuple(float(v) for v in arguments.get("position", (1, 0)))
            if len(position) != 2 or not all(math.isfinite(v) for v in (*position, time)):
                raise ActionRequestError(tool="math.numeric",
                    field="time" if not math.isfinite(time) else "position")
            sources = gravity.sources(time)
            forces = [{"body": body["id"], "acceleration": list(gravity.acceleration(
                time, *position, active_bodies=(body["id"],)))} for body in sources]
            radius = math.hypot(*position)
            return Observation("math.numeric", {"operation": operation,
                "gravity": gravity.as_record(), "time": time, "position": list(position),
                "binary_angular_speed": gravity.angular_speed,
                "binary_period": 2 * math.pi / gravity.angular_speed if gravity.angular_speed else None,
                "sources": sources, "gravity_contributions": forces,
                "total_gravity": list(gravity.acceleration(time, *position)),
                "velocity_for_corotation": [-gravity.angular_speed * position[1], gravity.angular_speed * position[0]],
                "monopole_circular_speed": math.sqrt(sum(gravity.masses) / radius) if radius else None,
                "limitations": ["Circular motion describes the two massive sources exactly",
                    "A corotating velocity is kinematic, not a stable spaceship solution",
                    "The monopole speed is a reduced reference; resolved binary and external terms remain unpredicted"]})
        if operation == "central_circular_reference":
            radius = float(arguments["radius"])
            speed = math.sqrt(1 / radius)
            return Observation("math.numeric", {
                "model": "central inverse-square attraction only",
                "radius": radius, "circular_speed": speed,
                "period": 2 * math.pi * radius / speed,
                "assumptions": ["unit central coefficient", "no modulation",
                                "no rotating field", "no random forcing"],
            })
        if operation == "central_candidate":
            vx, vy = float(arguments["vx"]), float(arguments["vy"])
            energy = (vx * vx + vy * vy) / 2 - 1
            angular_momentum = vy
            eccentricity = math.sqrt(max(0, 1 + 2 * energy * angular_momentum ** 2))
            periapsis = angular_momentum ** 2 / (1 + eccentricity)
            apoapsis = angular_momentum ** 2 / (1 - eccentricity) if energy < 0 and eccentricity < 1 else None
            period = 2 * math.pi * (-2 * energy) ** -1.5 if energy < 0 and angular_momentum != 0 else None
            return Observation("math.numeric", {"model": "central only; position (1,0)",
                "vx": vx, "vy": vy, "specific_energy": energy,
                "angular_momentum": angular_momentum, "eccentricity": eccentricity,
                "periapsis": periapsis, "apoapsis": apoapsis, "period": period,
                "limitations": ["Predictions omit modulation, rotating field, and forcing",
                    "A radial collision orbit is degenerate and has no regular recurrence period"]})
        if operation == "local_velocity_fit":
            import numpy as np
            data = np.asarray(arguments["points"], dtype=float)
            if data.ndim != 2 or data.shape[1] != 3 or not len(data) or not np.all(np.isfinite(data)):
                raise ActionRequestError(tool="math.numeric", field="points")
            design = np.column_stack((np.ones(len(data)), data[:, :2]))
            coefficients, _, rank, singular = np.linalg.lstsq(design, data[:, 2], rcond=None)
            return Observation("math.numeric", {"operation": operation,
                "model": "local affine fit of measured persistence against velocity",
                "coefficients_intercept_vx_vy": coefficients.tolist(), "rank": int(rank),
                "singular_values": singular.tolist(),
                "rms_residual": float(np.sqrt(np.mean((design @ coefficients - data[:, 2]) ** 2))),
                "limitations": ["Local approximation; extrapolation and rank deficiency remain visible",
                    "No automatic optimizer or hidden simulation search was performed"]})
        raise ActionRequestError("wrong_command", tool="math.numeric", field="operation")

    @staticmethod
    def symbolic_calculation(arguments):
        import sympy as sp
        operation = arguments["operation"]
        if operation != "central_conic":
            raise ActionRequestError("wrong_command", tool="math.symbolic", field="operation")
        # Derive the conic parameters directly from E=v²/2-1 and L=vy at r=1.
        vx, vy = sp.symbols("vx vy", real=True)
        energy = (vx ** 2 + vy ** 2) / 2 - 1
        eccentricity_squared = sp.expand(1 + 2 * energy * vy ** 2)
        return Observation("math.symbolic", {"operation": operation, "sympy_version": sp.__version__,
            "central_relationships": {"specific_energy": str(energy), "angular_momentum": str(vy),
                "eccentricity_squared": str(eccentricity_squared),
                "periapsis": "vy**2 / (1 + sqrt(eccentricity_squared))",
                "apoapsis": "vy**2 / (1 - sqrt(eccentricity_squared)), for nondegenerate E<0",
                "period": "2*pi*(-2*E)**(-3/2), for nondegenerate E<0"},
            "assumptions": ["central inverse-square unit attraction only", "initial position (1,0)",
                "elliptical period requires negative energy and nonzero angular momentum"],
            "guidance": "vy=1 and vx=0 gives the circular central reference; inspect reduced perturbations with simparts",
            "limitations": ["Exact relationships describe the reduced central problem only",
                "They do not predict forced full-model persistence by themselves"]})

    def lean_calculation(self, arguments):
        executable = shutil.which("lean")
        if executable is None:
            return Observation("math.lean", {"available": False,
                "diagnostic": "Lean is not installed; formal exploration is optional"})
        with tempfile.TemporaryDirectory(prefix="lean-", dir=self.store.directory) as directory:
            from pathlib import Path
            source = Path(directory) / "Exploration.lean"
            source.write_text(arguments["source"])
            result = subprocess.run([executable, str(source)], cwd=directory,
                                    text=True, capture_output=True, timeout=60)
        return Observation("math.lean", {"available": True, "exit_code": result.returncode,
            "stdout": result.stdout, "stderr": result.stderr,
            "scope": "Supplied statement and assumptions only; no prerequisite for other work"})
