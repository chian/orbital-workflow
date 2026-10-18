"""A finite real-execution probe, explicitly not the scientific search policy."""

from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import platform
import sys
import tomllib
import uuid

import method_loop
import numpy as np
import scipy

from .artifacts import Artifacts
from .records import Observation
from .persistence import PersistenceSettings
from .runtime import (EpisodeSpec, Kind, ToolAction, Workflow,
                      diagnostic_bindings, diagnostic_child)
from .simulation import ModelTerms, SimulationRequest, generate_forcing
from .tools import ToolDispatcher


class SequenceSource:
    """A finite diagnostic workload; never a numerical continuation rule."""

    def __init__(self, actions):
        self.actions = iter(actions)

    def next(self, view):
        return next(self.actions, None)


def spec(kind, key, objective, actions):
    return EpisodeSpec(kind, key, objective,
                       Observation("assignment", {"question": objective}),
                       lambda request: SequenceSource(actions))


def probe_plan(forcing_id):
    baseline = SimulationRequest(forcing_id, end=4 * math.pi,
                                 terms=ModelTerms(modulation=False, rotating=False, forcing=False))
    modulated = SimulationRequest(forcing_id, end=baseline.end,
                                  terms=ModelTerms(rotating=False, forcing=False))
    full = SimulationRequest(forcing_id, end=baseline.end)
    central_motion = spec(Kind.PARTS, "central-motion",
        "Observe the central-only reference trajectory", [
            ToolAction("central-reference", "sim.run", asdict(baseline)),
        ])
    math_branch = spec(Kind.MATH, "reference-mathematics",
        "Calculate and investigate the central circular reference", [
            ToolAction("calculate-reference", "math.numeric",
                       {"operation": "central_circular_reference", "radius": 1}),
            diagnostic_child(central_motion, "Relate the calculated reference to observed motion"),
        ])
    modulation = spec(Kind.PARTS, "modulated-motion",
        "Observe motion with periodic central modulation", [
            ToolAction("modulated-observation", "sim.run", asdict(modulated)),
        ])
    isolate = spec(Kind.PARTS, "isolate-central-effects",
        "Investigate the central contribution with a smaller observation", [
            ToolAction("central-observation", "sim.run", asdict(baseline)),
            diagnostic_child(modulation, "Characterize the periodic term's contribution"),
        ])
    simulation_branch = spec(Kind.SIMULATION, "full-environment",
        "Observe a spaceship in the full environment and investigate a reduction", [
            ToolAction("full-observation", "sim.run", asdict(full)),
            diagnostic_child(isolate, "Relate a reduced investigation to the full observation"),
        ])
    return spec(Kind.ROOT, "diagnostic-root", "Exercise the declared Episode skeleton", [
        diagnostic_child(math_branch, "Obtain reference mathematics and scoped simulation findings"),
        diagnostic_child(simulation_branch, "Obtain full-environment and reduced-model findings"),
    ])


def environment(config):
    package = Path(__file__).parent
    method_package = Path(method_loop.__file__).parent
    files = [*package.rglob("*.py"), *method_package.rglob("*.py")]
    return {
        "execution": "diagnostic_skeleton_probe",
        "scientific_credit": None, "scientific_search_policy": None,
        "python": sys.version, "python_executable": sys.executable,
        "numpy": np.__version__, "scipy": scipy.__version__,
        "platform": platform.platform(), "method_loop_source": str(method_package),
        "source_hashes": {str(path.resolve()): hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in sorted(files)},
    }


def run_probe(directory: Path, config_path: Path):
    # The probe creates a new directory so previous evidence is never overwritten.
    directory.mkdir(parents=True, exist_ok=False)
    config_text = config_path.read_text()
    config = tomllib.loads(config_text)
    (directory / "study.toml").write_text(config_text)
    (directory / "environment.json").write_text(json.dumps(environment(config), indent=2))
    store = Artifacts(directory / "objects")
    forcing_id = generate_forcing(store, trial=1, horizon=4 * math.pi)
    tools = ToolDispatcher(store, PersistenceSettings(**config["persistence"]))
    workflow = Workflow(diagnostic_bindings(), tools, directory / "episodes")
    run_id = "skeleton_probe_" + uuid.uuid4().hex
    try:
        record, findings = workflow.run(probe_plan(forcing_id), run_id)
    except Exception as error:
        (directory / "execution_error.json").write_text(json.dumps({
            "run_id": run_id, "error": type(error).__name__, "message": str(error),
        }, indent=2))
        raise
    (directory / "record.json").write_text(json.dumps(record.as_record(), indent=2))
    (directory / "findings.json").write_text(json.dumps(findings.as_record(), indent=2))
    summary = {"run_id": run_id, "ended_by": record.ended_by,
               "execution": "diagnostic_skeleton_probe", "scientific_credit": None,
               "forcing": forcing_id, "record": str(directory.resolve() / "record.json")}
    (directory / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary
