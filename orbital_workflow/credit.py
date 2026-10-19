"""Score assignment and composition of the Episode numerical binding.

One simulation supplies one scalar score. Assignment, yield estimation and
continuation are separate operations; all observations remain on disk.
"""

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from numbers import Real

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


@dataclass(frozen=True)
class ReportedEvidence(Evidence):
    """Child work plus its completed parent form; accounting uses measurements."""
    report_values: dict | None = None

    def __post_init__(self):
        super().__post_init__()
        object.__setattr__(self, "report_values", freeze(plain(self.report_values)))

    def as_record(self):
        return {**super().as_record(), "report_values": plain(self.report_values)}


def project_observation(observation, store):
    """Machine measurements for accounting; prose/model assertions earn none."""
    request = store.json(observation.artifacts[0])
    arguments = request["arguments"]
    findings = plain(observation.findings)
    measurements = []
    if observation.operation in ("sim.run", "sim.compare"):
        pairs = ([(arguments, findings, observation.artifacts[-1])]
                 if observation.operation == "sim.run" else [
            (store.json(arguments[side])["request"], findings[side], arguments[side])
            for side in ("left", "right")])
        for args, result, reference in pairs:
            measurements.append(trajectory_evidence(args, result, store, observation_ref=reference))
    elif observation.operation.startswith("math.") and findings.get("central_relationships"):
        measurements.append({"type": "central_analytic", "physical_id": "unit-central-conic",
                             "relationships": findings["central_relationships"]})
    return Evidence(tuple(measurements), ({"operation": observation.operation, "measurements": findings},),
                    observation.artifacts)


def trajectory_evidence(arguments, measurement, store, *, observation_ref=None):
    """Canonical physical input, shared by accounting and display grouping."""
    args = asdict(SimulationRequest.from_record(arguments))
    forcing = store.arrays(args["forcing_id"])
    physical = {key: value for key, value in args.items() if key not in {
        "forcing_id", "end", "method", "max_step", "sample_step", "rtol", "atol", "observation_window", "experiment"}}
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
    value = {"type": "trajectory", "physical_id": identity(physical),
             "physical": physical, "forcing_group": seed, "measurement": measurement}
    if observation_ref is not None:
        # A saved reference adds provenance, never a new credit identity.
        value["evidence_key"] = evidence_key(value)
        value["observation_ref"] = observation_ref
        value["executed_forcing_seed"] = int(forcing["seed"])
    return value



@dataclass(frozen=True)
class CreditTarget:
    """An explicit local target identity and its existing score projection."""
    target_id: str
    projection: str

    def __post_init__(self):
        if not isinstance(self.target_id, str) or not self.target_id:
            raise ValueError("A credit target needs an explicit identity")
        if self.projection not in {"complete_scenario", "acquired_trajectories"}:
            raise ValueError("Unknown credit target projection")

    def as_record(self):
        return asdict(self)


@dataclass(frozen=True)
class InheritedProgress:
    """One prior winning observation, never an acquired child observation."""
    target: CreditTarget
    observation: dict
    source_path: tuple
    source_unit: int

    def __post_init__(self):
        if not isinstance(self.target, CreditTarget):
            raise TypeError("Inherited progress requires a typed credit target")
        if type(self.source_unit) is not int or self.source_unit < 1 or not self.source_path:
            raise ValueError("Inherited progress requires a prior source acquisition")
        object.__setattr__(self, "observation", freeze(compact_evidence(self.observation)))
        object.__setattr__(self, "source_path", tuple(tuple(part) for part in self.source_path))

    def as_record(self):
        return {"target": self.target.as_record(), "observation": plain(self.observation),
                "source_path": plain(self.source_path), "source_unit": self.source_unit}


class BestScoreCredit:
    """Assign improvements in returned scores, without inspecting run duration.

    A parent may select the scores relevant to its own declared target. All
    evidence, including scoped and zero-valued observations, is retained.
    """

    def __init__(self, score_projection=None, *, target=None, inherited=None):
        self.score_projection = score_projection or self.simulation_score
        self.target, self.inherited = target, inherited
        self.evidence = {}
        self.best_score = 0.0
        self.winning_observation = None
        self.winning_source = None
        if inherited is not None:
            if target is None or inherited.target != target:
                raise ValueError("Inherited progress must belong to the same explicit target")
            score = self._score(inherited.observation)
            if score is None:
                raise ValueError("Inherited progress must be eligible for its declared target")
            self.best_score = score
            self.winning_observation = plain(inherited.observation)
            self.winning_source = (inherited.source_path, inherited.source_unit)
        self.inherited_score = self.best_score

    @property
    def gained_credit(self):
        return self.best_score - self.inherited_score

    def _score(self, item):
        score = self.score_projection(item)
        if score is None:
            return None
        if isinstance(score, bool) or not isinstance(score, Real) or not math.isfinite(score) or score < 0:
            raise ValueError("A completed observation supplies a finite nonnegative score")
        return float(score)

    def inheritance(self):
        if self.winning_observation is None:
            return None
        if self.target is None or self.winning_source is None:
            raise ValueError("Inherited progress requires a recorded target and source acquisition")
        return InheritedProgress(self.target, self.winning_observation, *self.winning_source)

    @staticmethod
    def simulation_score(item):
        if item["type"] != "trajectory":
            return None
        return item["measurement"]["score"]

    def observe(self, contribution, *, source=None):
        before = self.best_score
        received_scores = []
        for item in contribution.measurements:
            item = plain(item)
            self.evidence[evidence_key(item)] = compact_evidence(item)
            score = self._score(item)
            if score is None:
                continue
            received_scores.append(score)
            if self.winning_observation is None or score > self.best_score:
                self.best_score = score
                self.winning_observation = compact_evidence(item)
                self.winning_source = source
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

    def __init__(self, settings, kind, score_projection=None, *, target=None, inherited=None, path=(),
                 target_relationship="new"):
        self.settings, self.kind = settings, kind
        self.path = path
        self.target_relationship = target_relationship
        self.local = settings["episodes"][kind]
        self.assignment = BestScoreCredit(score_projection, target=target, inherited=inherited)
        self.estimator = ScalarScoreYieldEstimator(YieldParameters(**self.local["yield"]))
        self.units = 0
        baseline = self.assignment.inherited_score
        self.last_assignment = {"before": baseline, "score": baseline, "marginal_credit": 0.0,
                                "received_scores": [], "distinct_observations": 0}
        self.history = []
        self.own_observations = []

    def observe(self, unit_label, value, *, is_root):
        if not isinstance(value, Evidence):
            raise TypeError("The numerical binding consumes projected machine Evidence")
        self.last_assignment = self.assignment.observe(value, source=(self.path, self.units + 1))
        self.own_observations.extend(plain(value.findings))
        estimate = self.estimator.observe(self.last_assignment["marginal_credit"])
        self.units += 1
        self.history.append({"unit": self.units, "label": unit_label,
            "total_credit": self.assignment.best_score,
            "inherited_score": self.assignment.inherited_score,
            "gained_credit": self.assignment.gained_credit,
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
            "credit_target": (self.assignment.target.as_record() if self.assignment.target else None),
            "credit_target_relationship": self.target_relationship,
            "inherited_score": self.assignment.inherited_score,
            "gained_credit": self.assignment.gained_credit,
            "inherited_progress": (self.assignment.inherited.as_record() if self.assignment.inherited else None),
            "marginal_credit": self.last_assignment["marginal_credit"],
            "score_assignment": self.last_assignment,
            "predicted_next_gain": band.value if estimate.ready else None,
            "projected_credit": band.as_record(),
            "continuation_cost": decision.continuation_cost,
            "yield_estimate": estimate.as_record(),
            "continuation": decision.as_record()}, decision.stop)

    def model_state(self):
        # Provenance is machine bookkeeping; own inputs expose its numerical
        # meaning without delivering an ancestor's audit identities.
        record = self.state().as_record()
        record.pop("inherited_progress")
        if record["credit_target"] is not None:
            record["credit_target"] = {"projection": self.assignment.target.projection}
        return record

    def transitioned(self, epoch):
        raise NotImplementedError("This workflow does not reset credit epochs")
