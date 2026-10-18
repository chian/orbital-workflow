"""Score assignment and composition of the Episode numerical binding.

One simulation supplies one scalar score. Assignment, yield estimation and
continuation are separate operations; all observations remain on disk.
"""

from dataclasses import asdict, dataclass
import hashlib
import json

from method_loop import ClosedRecord

from .records import freeze, plain
from .simulation import SimulationRequest
from .gravity import GravitySystem
from .score_yield import ScalarScoreYieldEstimator, YieldParameters, predicted_gain_upper_bound


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
    if observation.operation in ("sim.run", "sim.compare"):
        pairs = ([(arguments, findings)] if observation.operation == "sim.run" else [
            (store.json(arguments[side])["request"], findings[side]) for side in ("left", "right")])
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
        "forcing_id", "end", "method", "max_step", "sample_step", "rtol", "atol", "observation_window"}}
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



class BestScoreCredit:
    """Assign improvements in returned scores, without inspecting run duration.

    A parent may select the scores relevant to its own declared target. All
    evidence, including scoped and zero-valued observations, is retained.
    """

    def __init__(self, score_projection=None):
        self.score_projection = score_projection or self.simulation_score
        self.evidence = {}
        self.best_score = 0.0

    @staticmethod
    def simulation_score(item):
        if item["type"] != "trajectory":
            return None
        return item["measurement"]["score"]

    def observe(self, contribution):
        from numbers import Real
        import math
        before = self.best_score
        received_scores = []
        for item in contribution.measurements:
            item = plain(item)
            self.evidence[evidence_key(item)] = compact_evidence(item)
            score = self.score_projection(item)
            if score is None:
                continue
            if isinstance(score, bool) or not isinstance(score, Real) or not math.isfinite(score) or score < 0:
                raise ValueError("A completed observation supplies a finite nonnegative score")
            received_scores.append(float(score))
            self.best_score = max(self.best_score, float(score))
        return {"before": before, "score": self.best_score,
                "marginal_credit": self.best_score - before,
                "received_scores": received_scores,
                "distinct_observations": len(self.evidence)}


@dataclass(frozen=True)
class CreditStep:
    record: dict
    stop: bool
    requests_transition: bool = False

    def as_record(self):
        return {**self.record, "stop": self.stop, "requests_transition": self.requests_transition}


class CreditController:
    """Compose score assignment, template-derived yield and continuation.

    The Episode calls observe exactly once per acquired unit. This controller
    neither smooths estimates nor manufactures a forecast from an initial guess.
    """
    epoch = "scored-turn-v1"

    def __init__(self, settings, kind, score_projection=None):
        self.settings, self.kind = settings, kind
        self.local = settings["episodes"][kind]
        self.assignment = BestScoreCredit(score_projection)
        self.estimator = ScalarScoreYieldEstimator(YieldParameters(**self.local["yield"]))
        self.units = 0
        self.last_assignment = {"before": 0.0, "score": 0.0, "marginal_credit": 0.0,
                                "received_scores": [], "distinct_observations": 0}
        self.history = []
        self.own_observations = []

    def observe(self, unit_label, value, *, is_root):
        if not isinstance(value, Evidence):
            raise TypeError("The numerical binding consumes projected machine Evidence")
        self.last_assignment = self.assignment.observe(value)
        self.own_observations.extend(plain(value.findings))
        estimate = self.estimator.observe(self.last_assignment["marginal_credit"])
        self.units += 1
        self.history.append({"unit": self.units, "label": unit_label,
            "total_credit": self.assignment.best_score,
            "marginal_credit": self.last_assignment["marginal_credit"],
            "received_scores": self.last_assignment["received_scores"],
            "yield_estimate": estimate.as_record()})
        return self.state()

    def state(self):
        estimate = self.estimator.state()
        band = estimate.expected_next_gain
        decision = predicted_gain_upper_bound(band, self.local["continuation_cost"])
        return CreditStep({"binding": self.epoch, "units": self.units,
            "credit": self.assignment.best_score,
            "marginal_credit": self.last_assignment["marginal_credit"],
            "score_assignment": self.last_assignment,
            "predicted_next_gain": band.value if estimate.ready else None,
            "projected_credit": band.as_record(),
            "continuation_cost": decision.continuation_cost,
            "yield_estimate": estimate.as_record(),
            "continuation": decision.as_record()}, decision.stop)

    def transitioned(self, epoch):
        raise NotImplementedError("This workflow does not reset credit epochs")
