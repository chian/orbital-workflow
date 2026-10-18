"""Template-derived yield prediction for real-valued Episode acquisition credit.

The public input is one non-negative projected marginal credit per completed
Episode acquisition turn. A direct sim.run acquires one integration and score;
math and comparison acquisitions can yield zero credit without a new simulation
score, as can explicit tool-request diagnostics before integration. At the root,
one completed child investigation is one root acquisition.
It contains no result identities, simulation duration, solver steps, bins, or
controller-smoothed predictions. Each estimate cold-fits the entire supplied
history using nano-graphrag's original numerical fitter and Laplace machinery.

This is an explicit adaptation of a count model. For real responses its
fractional Poisson kernel is a working quasi-likelihood, not a probability mass
function or continuous-response density. Curvature-based Laplace uncertainty
is approximate and model-dependent, not a calibrated confidence interval.
Changing credit units can change the fit's effective information; the declared
credit units must therefore remain fixed within an Episode.

The original model describes attempted units and observation failures. Our
acquisitions have completed and their marginal credit has been projected, so
this adapter conditions on observation:
it omits the observation/failure kernel and usability multiplier. The latent
lognormal yield model, rank decay, yield priors, optimizer, numerical safeguards,
minimum-information statuses and delta/Laplace machinery remain from the source.
"""

from dataclasses import dataclass
import math
from numbers import Real
from typing import Sequence

from .vendor import nano_rarefaction as template


NumericBand = template.NumericBand
STATUS_NORMAL = template.STATUS_NORMAL
STATUS_INSUFFICIENT = template.STATUS_INSUFFICIENT
STATUS_UNIDENTIFIABLE = template.STATUS_UNIDENTIFIABLE

SOURCE_SHA256 = "02af19652d69f368ee8875d3b27cad0bb2bbc8d1f8274344b72a4437092cdd35"
SOURCE_REVISION = "60a167f9eeda0c9ea2ca294724174948947baf3f"
ESTIMATOR_VERSION = "completed_real_score_preferential_yield_v1"


def _score(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite non-negative real number")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{name} must be a finite non-negative real number")
    return number


@dataclass(frozen=True)
class YieldParameters:
    # These preserve the actual template's availability semantics. They are
    # minimum information for a fit, not a rolling mean or an episode cap.
    window_size: int = template.DEFAULT_WINDOW_SIZE
    subsample_size: int = template.DEFAULT_SUBSAMPLE_SIZE
    uncertainty_alpha: float = template.DEFAULT_ALPHA

    def __post_init__(self):
        template._IncidenceEstimator.validate_parameters(
            self.window_size, self.subsample_size, self.uncertainty_alpha)

    def as_record(self):
        return {
            "window_size": self.window_size,
            "subsample_size": self.subsample_size,
            "uncertainty_alpha": self.uncertainty_alpha,
            "window_semantics": "minimum_completed_acquisition_turns_before_full_history_fit",
            "subsample_semantics": "minimum_evaluated_acquisition_turns_before_full_history_fit",
        }


def provenance():
    return {
        "estimator": ESTIMATOR_VERSION,
        "source_repository": "nano-graphrag",
        "source_path": "question_pipeline/utilities/rarefaction.py",
        "source_revision": SOURCE_REVISION,
        "source_sha256": SOURCE_SHA256,
        "source_license": "MIT; orbital_workflow/vendor/LICENSE.nano-graphrag",
        "vendored_source": "orbital_workflow/vendor/nano_rarefaction.py",
        "template_estimator": template.INCIDENCE_ESTIMATOR_VERSION,
        "turn_unit": "completed_episode_acquisition",
        "credit_input": "projected_marginal_credit",
        "per_episode_units": {
            "direct_sim_run": "One integration returns one score in one acquisition turn",
            "math_or_comparison": "An acquisition can have zero marginal credit without a new simulation score",
            "request_diagnostic": "One acquired tool diagnostic has no completed simulation or score",
            "root": "One completed child investigation supplies one root acquisition turn",
        },
        "adaptations": [
            "Real marginal credit responses pass into the fit without integer coercion",
            "Completed Episode acquisitions condition on observation; no failure/usability model",
            "A fresh original fitter cold-fits the entire score history each turn",
            "Original numeric bands and delta/Laplace curvature approximation are retained",
        ],
        "statistical_model": "latent_lognormal_fractional_poisson_working_quasi_likelihood",
        "uncertainty": "approximate_model_dependent_curvature_laplace_band",
        "calibrated_confidence_interval": False,
        "limitations": [
            "The fractional kernel is not a continuous-response probability density",
            "Uncertainty assumes the working model and is not coverage calibrated",
            "Credit units affect effective information and must remain fixed within an Episode",
            "Rank-decay extrapolation assumes declining yield; late discoveries can violate it",
            "No failed-attempt probability is estimated from completed-only acquisitions",
            "The inherited local optimizer has no global optimum or convergence certificate; bands can jump across history lengths",
        ],
    }


class _RealScoreFit(template._IncidenceEstimator):
    """Reuse the original fitter, with the two input/model changes above."""

    @staticmethod
    def _observation_loss(parameters, rank, status, discovery):
        if status != template.OBSERVATION_OBSERVED:
            raise ValueError("Only completed Episode acquisition turns enter this estimator")
        beta, log_delta, _observation_intercept, _coupling = parameters
        delta = math.exp(float(log_delta))
        # The gamma term is constant with respect to parameters. It retains
        # the original kernel's numerical offset; it is not a density claim.
        terms = tuple(
            weight + discovery * potential
            - math.exp(max(-50.0, min(50.0, potential)))
            - math.lgamma(discovery + 1.0)
            for weight, potential in (
                (weight, beta - delta * (rank - 1) + latent)
                for weight, latent in zip(
                    template._LOG_QUADRATURE_WEIGHTS, template._QUADRATURE_LATENT)
            )
        )
        return -template._logsumexp(terms)

    @classmethod
    def _history_loss(cls, parameters, statuses, discoveries):
        # Deliberately no int(discovery), identity conversion or smoothing.
        return cls._prior_loss(parameters) + sum(
            cls._observation_loss(parameters, rank, status, discovery)
            for rank, (status, discovery) in enumerate(zip(statuses, discoveries), 1)
        )

    @staticmethod
    def _metric_discovery(parameters, rank):
        beta, log_delta, _observation_intercept, _coupling = parameters
        delta = math.exp(float(log_delta))
        return sum(
            math.exp(weight) * math.exp(max(-50.0, min(50.0,
                beta - delta * (rank - 1.0) + latent)))
            for weight, latent in zip(
                template._LOG_QUADRATURE_WEIGHTS, template._QUADRATURE_LATENT)
        )


@dataclass(frozen=True)
class YieldEstimate:
    turns: int
    expected_next_gain: NumericBand
    parameters: YieldParameters
    diagnostics: dict

    @property
    def ready(self):
        return self.expected_next_gain.status_code == STATUS_NORMAL

    def as_record(self):
        return {
            "turns": self.turns,
            "expected_next_gain": self.expected_next_gain.as_record(),
            "parameters": self.parameters.as_record(),
            "diagnostics": dict(self.diagnostics),
            "provenance": provenance(),
        }


def estimate_score_yield(scores: Sequence[Real], parameters: YieldParameters | None = None):
    """Pure current-history estimate; previous predictions are never an input."""
    parameters = YieldParameters() if parameters is None else parameters
    if not isinstance(parameters, YieldParameters):
        raise TypeError("parameters must be YieldParameters")
    history = tuple(_score(value, "marginal credit") for value in scores)
    turns = len(history)
    diagnostics = {"completed_acquisition_turns": turns, "history_used": turns,
                   "fitting_scope": "full_history", "initialization": "cold_template_prior"}
    if turns < parameters.window_size or turns < parameters.subsample_size:
        return YieldEstimate(turns, NumericBand.coded(STATUS_INSUFFICIENT), parameters, diagnostics)

    # Never reuse last turn's prediction or fit state. The history alone
    # determines this turn's fit, including the original fixed yield priors.
    fit = _RealScoreFit(window_size=parameters.window_size,
                        subsample_size=parameters.subsample_size,
                        alpha=parameters.uncertainty_alpha)
    statuses = (template.OBSERVATION_OBSERVED,) * turns
    try:
        fitted, covariance, objective = fit._fit_full_history(
            statuses, history, coupling_identifiable=False)
        if not all(math.isfinite(value) for row in covariance for value in row):
            raise ArithmeticError("Non-finite fitted covariance")
        next_rank = turns + 1
        point = fit._metric_discovery(fitted, next_rank)
        variance = fit._metric_variance(fitted, covariance,
            lambda values: fit._metric_discovery(values, next_rank))
        band = NumericBand.laplace(point, variance, parameters.uncertainty_alpha)
        diagnostics.update({"yield_intercept": fitted[0],
            "rank_decay": math.exp(fitted[1]), "fit_objective": objective,
            "next_gain_variance": variance})
    except (ArithmeticError, OverflowError, ValueError) as error:
        # Numerical non-identifiability is a prediction status, never a zero
        # yield or a reason for continuation to manufacture a stop.
        band = NumericBand.coded(STATUS_UNIDENTIFIABLE)
        diagnostics["fit_status"] = type(error).__name__
    return YieldEstimate(turns, band, parameters, diagnostics)


class ScalarScoreYieldEstimator:
    """One Episode's projected acquisition-credit stream and current prediction."""

    def __init__(self, parameters: YieldParameters | None = None):
        self.parameters = YieldParameters() if parameters is None else parameters
        self._scores = []
        self._current = estimate_score_yield((), self.parameters)

    @property
    def scores(self):
        return tuple(self._scores)

    def observe(self, marginal_credit: Real):
        self._scores.append(_score(marginal_credit, "marginal credit"))
        self._current = estimate_score_yield(self._scores, self.parameters)
        return self._current

    def state(self):
        return self._current


@dataclass(frozen=True)
class ContinuationDecision:
    stop: bool
    projected_gain: NumericBand
    continuation_cost: float

    def as_record(self):
        return {"stop": self.stop, "projected_gain": self.projected_gain.as_record(),
                "continuation_cost": self.continuation_cost,
                "decision_basis": "current_estimator_marginal_credit_upper_bound"}


def predicted_gain_upper_bound(projected_gain: NumericBand, continuation_cost: Real):
    """Independent rule consuming the current estimator output unchanged."""
    if not isinstance(projected_gain, NumericBand):
        raise TypeError("Continuation consumes a NumericBand")
    cost = _score(continuation_cost, "continuation cost")
    return ContinuationDecision(
        projected_gain.status_code == STATUS_NORMAL and projected_gain.upper <= cost,
        projected_gain, cost)
