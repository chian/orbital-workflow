"""Explicit discovery accounting and a configurable numerical yield forecast.

Knowledge is an initial smooth evidence-support proxy, not measured truth or a
calibrated posterior probability. Every observation remains in the record.
"""

from dataclasses import asdict, dataclass
import hashlib
import itertools
import json
import math

import numpy as np
from method_loop import ClosedRecord

from .records import freeze, plain
from .simulation import SimulationRequest
from .gravity import GravitySystem, scenario_problem, source_model


def identity(value):
    return hashlib.sha256(json.dumps(plain(value), sort_keys=True, allow_nan=False).encode()).hexdigest()


def evidence_key(item):
    return item.get("evidence_key", identity(item))


def compact_evidence(item):
    """Parent accounting needs numerical state, not a child's raw cycle log."""
    from .storage import scalar_summary
    value = plain(item)
    value["evidence_key"] = evidence_key(item)
    if value["type"] == "trajectory":
        value["measurement"] = scalar_summary(value["measurement"])
    return value


@dataclass(frozen=True)
class Evidence(ClosedRecord):
    measurements: tuple
    findings: tuple = ()
    artifacts: tuple[str, ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "measurements", tuple(freeze(plain(x)) for x in self.measurements))
        object.__setattr__(self, "findings", tuple(freeze(plain(x)) for x in self.findings))

    def as_record(self):
        return {"measurements": plain(self.measurements), "findings": plain(self.findings),
                "artifacts": list(self.artifacts)}

    def audit_identifiers(self):
        return self.artifacts


def project_observation(observation, store):
    """Machine measurements for accounting; prose/model assertions earn none."""
    request = store.json(observation.artifacts[0])
    arguments = request["arguments"]
    findings = plain(observation.findings)
    measurements = []
    if observation.operation.startswith("sim."):
        pairs = [(arguments, findings)] if observation.operation == "sim.run" else [
            (arguments[side], findings[side]) for side in ("left", "right")]
        for args, result in pairs:
            measurements.append(trajectory_evidence(args, result, store))
    elif observation.operation.startswith("math.") and findings.get("central_relationships"):
        measurements.append({"type": "central_analytic", "physical_id": "unit-central-conic",
                             "relationships": findings["central_relationships"]})
    return Evidence(tuple(measurements), ({"operation": observation.operation, "measurements": findings},),
                    observation.artifacts)


def trajectory_evidence(arguments, measurement, store):
    """Canonical physical input, shared by accounting and display grouping."""
    args = asdict(SimulationRequest.from_record(arguments))
    forcing = store.arrays(args["forcing_id"])
    physical = {key: value for key, value in args.items() if key not in {
        "forcing_id", "end", "method", "max_step", "sample_step", "rtol", "atol"}}
    terms = physical["terms"]
    gravity = GravitySystem.from_record(physical["gravity"])
    physical["active_bodies"] = sorted(gravity.body_ids if physical["active_bodies"] is None else physical["active_bodies"])
    if gravity.kind == "single":
        physical["gravity_mode"] = "resolved"
    if not terms["central"] or not terms["modulation"]:
        physical["a"] = 0.0
    if not terms["forcing"] or not physical["sigma"]:
        physical["sigma"] = 0.0
        seed = "deterministic"
    else:
        seed = str(int(forcing["seed"]))
    physical["forcing_seed"] = seed
    return {"type": "trajectory", "physical_id": identity(physical),
            "physical": physical, "forcing_group": seed, "measurement": measurement}


class Ledger:
    def __init__(self, settings, kind):
        self.settings, self.kind = settings, kind
        self.evidence = {}
        self.problem = scenario_problem(settings)
        self.gravity = GravitySystem.from_record(self.problem["gravity"])
        study = settings["study"]
        self.cases = list(itertools.product(study["a"], study["sigma"]))
        self.source_models = (["monopole"] if self.gravity.kind == "circular_binary" else []) + [
            "bodies:" + str(mask) for mask in range(1, 2 ** len(self.gravity.masses))]
        self.reference_model = "monopole" if self.gravity.kind == "circular_binary" else "bodies:1"
        self.variants = list(itertools.product(self.source_models, (False, True), (False, True), (False, True)))
        self.velocities = list(itertools.product(settings["support"]["radial_velocity_anchors"],
                                                 settings["support"]["tangential_velocity_anchors"]))

    def add(self, contribution):
        for item in contribution.measurements:
            # Identical physical realization/refinement belongs to one support
            # group, but retain every distinct observation for current estimates.
            self.evidence[evidence_key(item)] = plain(item)

    def scores(self):
        cfg = self.settings["support"]
        horizon = self.settings["study"]["horizon"]
        groups = {}
        best = np.zeros(len(self.cases))
        analytic = any(item["type"] == "central_analytic" for item in self.evidence.values())
        for item in self.evidence.values():
            if item["type"] != "trajectory":
                continue
            physical, result = item["physical"], item["measurement"]
            terms = physical["terms"]
            model = source_model(physical["gravity"], physical["active_bodies"], physical["gravity_mode"])
            variant = (model, terms["modulation"] and terms["central"], terms["rotating"], terms["forcing"])
            duration = result["observed_interval"][1] - result["observed_interval"][0]
            numerical = result["numerical_settings"]
            # Nominal resolution support, not a rigorous integration error bound.
            quality = ((1 - math.exp(-duration / cfg["duration_scale"]))
                / (1 + (numerical["sample_step"] / cfg["sample_scale"]) ** 2
                   + numerical["rtol"] / cfg["rtol_scale"]
                   + (numerical["max_step"] / cfg["integration_step_scale"]) ** 2))
            values = np.zeros((len(self.variants), len(self.cases), len(self.velocities)))
            if terms["central"] and model in self.source_models:
                vi = self.variants.index(variant)
                vx, vy = physical["initial_state"][2:]
                for ci, (a, sigma) in enumerate(self.cases):
                    env = ((a - physical["a"]) / cfg["a_scale"]) ** 2 if variant[0] else 0.0
                    if variant[2]:
                        env += ((sigma - physical["sigma"]) / cfg["sigma_scale"]) ** 2
                    for si, (ax, ay) in enumerate(self.velocities):
                        distance = env + ((vx - ax) / cfg["vx_scale"]) ** 2 + ((vy - ay) / cfg["vy_scale"]) ** 2
                        values[vi, ci, si] = quality * math.exp(-0.5 * distance)
            # Spatial/time scope support scales with actual observed duration;
            # such evidence is retained even outside this initial anchor family.
            group = groups.setdefault(item["forcing_group"], np.zeros_like(values))
            np.maximum(group, values, out=group)
            # This component means discoveries in the original complete model,
            # from the agreed insertion and observation domain. Reduced models
            # still contribute immediately through their knowledge support.
            full_scope = (all(terms.values()) and physical["initial_state"][:2] == self.problem["initial_position"]
                          and physical["start"] == 0 and physical["spatial_box"] is None
                          and physical["radial_limits"] == self.problem["radial_limits"]
                          and physical["gravity_mode"] == "resolved"
                          and physical["active_bodies"] == sorted(self.gravity.body_ids)
                          and identity(physical["gravity"]) == identity(self.problem["gravity"])
                          and physical["scenario_id"] == self.problem["id"])
            if full_scope and (physical["a"], physical["sigma"]) in self.cases:
                ci = self.cases.index((physical["a"], physical["sigma"]))
                best[ci] = max(best[ci], result["persistence_measurement"]["effective_duration"] / horizon)
        remaining = np.ones((len(self.variants), len(self.cases), len(self.velocities)))
        for support in groups.values():
            remaining *= 1 - support
        coverage = 1 - remaining
        if analytic:
            coverage[self.variants.index((self.reference_model, False, False, False))] = 1.0
        # Math measures guidance about the central reference as its local target.
        # Its parent recomputes the same evidence on the parent's full scope.
        local_coverage = (coverage[[self.variants.index((model, False, False, False)) for model in self.source_models]]
                          if self.kind == "mathematical_exploration" else coverage)
        return {"orbital_persistence": float(best.mean()),
                "knowledge_gained": float(local_coverage.mean()),
                "best_observed_persistence_by_case": best.tolist(),
                "knowledge_definition": "smooth evidence support on configured reference anchors",
                "support_by_model_variant": [float(x.mean()) for x in coverage],
                "model_variants": [list(variant) for variant in self.variants],
                "distinct_observations": len(self.evidence),
                "limitations": ["Support is an initial proxy, not a calibrated epistemic uncertainty",
                    "Nominal resolution support is not an integration error bound",
                    "Persistence is observed discovery credit, not expected performance over forcing",
                    "Anchor coverage is restricted to the declared inputs and model family"]}


@dataclass(frozen=True)
class CreditStep:
    record: dict
    stop: bool
    requests_transition: bool = False

    def as_record(self):
        return {**self.record, "stop": self.stop, "requests_transition": self.requests_transition}


class CreditController:
    epoch = "continuous-discovery-v1"

    def __init__(self, settings, kind):
        self.settings, self.kind = settings, kind
        self.ledger = Ledger(settings, kind)
        self.local = settings["episodes"][kind]
        self.total = 0.0
        self.prediction = self.local["initial_predicted_gain"]
        self.units = 0
        self.last_gain = 0.0
        self.last_components = self.ledger.scores()
        self.history = []
        self.own_observations = []

    def observe(self, unit_label, value, *, is_root):
        if not isinstance(value, Evidence):
            raise TypeError("Scientific controller requires projected machine Evidence")
        self.ledger.add(value)
        self.own_observations.extend(plain(value.findings))
        components = self.ledger.scores()
        weights = self.local["weights"]
        current = sum(weights[name] * components[name] for name in weights)
        # Ledger accumulation uses maxima and support unions. It is monotone
        # discovery accounting; every raw measurement, including decreases,
        # remains available rather than being overwritten with the high water.
        if current < self.total - 1e-12:
            raise ArithmeticError("Discovery accounting decreased unexpectedly")
        gain = max(0.0, current - self.total)
        decay = self.local["forecast_memory"]
        forecast_error = gain - self.prediction
        self.prediction = decay * self.prediction + (1 - decay) * gain
        self.units += 1
        self.last_gain, self.total, self.last_components = gain, current, components
        self.history.append({"unit": self.units, "label": unit_label,
            "total_credit": current, "marginal_credit": gain,
            "forecast_residual": forecast_error, "predicted_next_gain": self.prediction})
        return self.state()

    def state(self):
        return CreditStep({"binding": self.epoch, "units": self.units,
            "credit": self.total, "marginal_credit": self.last_gain,
            "components": self.last_components, "weights": self.local["weights"],
            "predicted_next_gain": self.prediction,
            "continuation_cost": self.local["continuation_cost"],
            "forecast": "EWMA of measured marginal discovery credit; heuristic, not calibrated",
            "forecast_memory": self.local["forecast_memory"]},
            self.units > 0 and self.prediction <= self.local["continuation_cost"])

    def transitioned(self, epoch):
        raise NotImplementedError("This study does not change credit epochs within a run")
