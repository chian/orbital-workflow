"""Episode-facing tool dispatch; all integrations and their inputs are retained."""

from dataclasses import asdict
import math
import shutil
import subprocess
import tempfile
from typing import Callable

from .artifacts import Artifacts
from .records import Observation
from .persistence import PersistenceSettings
from .simulation import SimulationRequest, compare, integrate


class ToolDispatcher:
    def __init__(self, store: Artifacts, persistence_settings: PersistenceSettings | None = None):
        self.store = store
        self.persistence_settings = persistence_settings or PersistenceSettings()
        self.handlers: dict[str, Callable] = {
            "sim.run": self.run_simulation,
            "sim.compare": self.compare_simulations,
            "math.numeric": self.numeric_calculation,
            "math.symbolic": self.symbolic_calculation,
            "math.lean": self.lean_calculation,
        }

    def execute(self, name: str, arguments: dict) -> Observation:
        request_id = self.store.put_json({"tool": name, "arguments": arguments})
        try:
            result = self.handlers[name](arguments)
        except Exception as error:
            self.store.put_json({"tool": name, "request": request_id,
                                 "execution_error": type(error).__name__,
                                 "message": str(error)})
            raise
        return Observation(result.operation, result.findings,
                           (request_id, *result.artifacts))

    def _run(self, request: SimulationRequest):
        trajectory = integrate(request, self.store)
        arrays_id = self.store.put_arrays(times=trajectory.times, states=trajectory.states)
        record_id = self.store.put_json({"request": asdict(request),
                                         "summary": trajectory.summary(self.persistence_settings),
                                         "trajectory": arrays_id})
        return trajectory, (request.forcing_id, arrays_id, record_id)

    def run_simulation(self, arguments):
        trajectory, artifacts = self._run(SimulationRequest.from_record(arguments))
        return Observation("sim.run", trajectory.summary(self.persistence_settings), artifacts)

    def compare_simulations(self, arguments):
        left, left_refs = self._run(SimulationRequest.from_record(arguments["left"]))
        right, right_refs = self._run(SimulationRequest.from_record(arguments["right"]))
        return Observation("sim.compare", compare(left, right, self.persistence_settings),
                           tuple(dict.fromkeys((*left_refs, *right_refs))))

    @staticmethod
    def numeric_calculation(arguments):
        # A concrete first tool operation. Additional operations are supplied by
        # the mathematical binding; this does not evaluate arbitrary Python.
        operation = arguments["operation"]
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
                raise ValueError("Fit points must contain finite vx, vy, measured score")
            design = np.column_stack((np.ones(len(data)), data[:, :2]))
            coefficients, _, rank, singular = np.linalg.lstsq(design, data[:, 2], rcond=None)
            return Observation("math.numeric", {"operation": operation,
                "model": "local affine fit of measured persistence against velocity",
                "coefficients_intercept_vx_vy": coefficients.tolist(), "rank": int(rank),
                "singular_values": singular.tolist(),
                "rms_residual": float(np.sqrt(np.mean((design @ coefficients - data[:, 2]) ** 2))),
                "limitations": ["Local approximation; extrapolation and rank deficiency remain visible",
                    "No automatic optimizer or hidden simulation search was performed"]})
        raise NotImplementedError(operation)

    @staticmethod
    def symbolic_calculation(arguments):
        import sympy as sp
        operation = arguments["operation"]
        if operation != "central_conic":
            raise NotImplementedError(operation)
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
