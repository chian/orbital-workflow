"""Numerical contracts over finite projected acquisition-credit streams."""

import hashlib
import math
from pathlib import Path
import unittest
from unittest.mock import patch

from orbital_workflow.bootstrap import use_method_loop
use_method_loop(Path(__file__).resolve().parents[2] / "OpenChia")

from orbital_workflow.score_yield import (
    NumericBand, SOURCE_SHA256, STATUS_INSUFFICIENT, STATUS_NORMAL,
    STATUS_UNIDENTIFIABLE, ScalarScoreYieldEstimator, YieldParameters,
    estimate_score_yield, predicted_gain_upper_bound,
)


class ScalarScoreYieldContract(unittest.TestCase):
    def test_fractional_responses_survive_and_change_the_fit(self):
        scores = [0, .125, 0, .375, 0, .5, 0, .25]
        estimator = ScalarScoreYieldEstimator()
        for score in scores:
            estimate = estimator.observe(score)
        self.assertEqual(estimator.scores, tuple(scores))
        self.assertTrue(estimate.ready)
        rounded = estimate_score_yield([0] * len(scores))
        self.assertNotEqual(estimate.expected_next_gain.value,
                            rounded.expected_next_gain.value)
        self.assertEqual(estimate.turns, len(scores))

    def test_each_turn_is_exact_current_history_fit_without_prediction_mixing(self):
        parameters = YieldParameters(window_size=4, subsample_size=2)
        estimator = ScalarScoreYieldEstimator(parameters)
        scores = [.375, 0, .125, .25, 0, 0, .5]
        for turns, score in enumerate(scores, 1):
            actual = estimator.observe(score)
            pure = estimate_score_yield(scores[:turns], parameters)
            self.assertEqual(actual.as_record(), pure.as_record())
            self.assertIs(estimator.state(), actual)
            self.assertEqual(actual.turns, turns)
            self.assertEqual(actual.diagnostics["completed_acquisition_turns"], turns)

    def test_minimum_information_is_unavailable_and_continuation_never_reads_sentinel_as_zero(self):
        estimator = ScalarScoreYieldEstimator()
        for score in [.125, 0, 0]:
            estimate = estimator.observe(score)
            self.assertEqual(estimate.expected_next_gain.status_code, STATUS_INSUFFICIENT)
            self.assertFalse(predicted_gain_upper_bound(
                estimate.expected_next_gain, 1e6).stop)
        unavailable = NumericBand.coded(STATUS_UNIDENTIFIABLE)
        self.assertFalse(predicted_gain_upper_bound(unavailable, 1e6).stop)

    def test_one_or_two_zero_turns_do_not_create_a_forced_stop(self):
        # No run-length rule: an informative full history still supports
        # additional gain after the latest two turns yield zero.
        estimate = estimate_score_yield([.2] * 6 + [0, 0])
        self.assertTrue(estimate.ready)
        self.assertGreater(estimate.expected_next_gain.upper, .04)
        self.assertFalse(predicted_gain_upper_bound(estimate.expected_next_gain, .04).stop)

    def test_zero_history_has_an_uncertainty_band_after_availability(self):
        estimate = estimate_score_yield([0] * 8)
        self.assertEqual(estimate.expected_next_gain.status_code, STATUS_NORMAL)
        self.assertGreater(estimate.expected_next_gain.upper, 0)
        self.assertGreaterEqual(estimate.expected_next_gain.value, 0)
        self.assertGreaterEqual(estimate.expected_next_gain.upper,
                                estimate.expected_next_gain.value)
        self.assertFalse(estimate.as_record()["provenance"]["calibrated_confidence_interval"])

    def test_continuation_uses_current_upper_bound_unchanged(self):
        band = NumericBand.laplace(.03, .01, .05)
        self.assertGreater(band.upper, .04)
        continuing = predicted_gain_upper_bound(band, .04)
        self.assertIs(continuing.projected_gain, band)
        self.assertFalse(continuing.stop)  # Point alone would have stopped.
        self.assertTrue(predicted_gain_upper_bound(band, band.upper).stop)
        previous = NumericBand.exact(100)
        self.assertFalse(predicted_gain_upper_bound(previous, .04).stop)
        current = NumericBand.exact(0)
        stopped = predicted_gain_upper_bound(current, .04)
        self.assertIs(stopped.projected_gain, current)
        self.assertTrue(stopped.stop)

    def test_history_is_full_and_not_truncated_to_window(self):
        left = estimate_score_yield([.125] * 4 + [0] * 8)
        right = estimate_score_yield([.75] * 4 + [0] * 8)
        self.assertEqual(left.diagnostics["history_used"], 12)
        self.assertEqual(right.diagnostics["history_used"], 12)
        self.assertNotEqual(left.expected_next_gain.value, right.expected_next_gain.value)

    def test_invalid_inputs_do_not_become_turns_or_observed_zeroes(self):
        estimator = ScalarScoreYieldEstimator()
        for value in [True, -1, math.inf, math.nan, "0.125", None]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                estimator.observe(value)
        self.assertEqual(estimator.scores, ())
        self.assertEqual(estimator.state().turns, 0)
        with self.assertRaises(TypeError):
            estimate_score_yield([], parameters=0)

    def test_numerical_unidentifiability_is_not_a_zero_prediction(self):
        with patch("orbital_workflow.score_yield._RealScoreFit._fit_full_history",
                   side_effect=ArithmeticError("non-identifiable fit")):
            estimate = estimate_score_yield([.125] * 8)
        self.assertEqual(estimate.expected_next_gain.status_code, STATUS_UNIDENTIFIABLE)
        self.assertFalse(predicted_gain_upper_bound(estimate.expected_next_gain, 1).stop)

    def test_template_is_exact_and_provenance_exposes_adaptation(self):
        vendored = Path(__file__).resolve().parents[1] / "orbital_workflow/vendor/nano_rarefaction.py"
        self.assertEqual(hashlib.sha256(vendored.read_bytes()).hexdigest(), SOURCE_SHA256)
        provenance = estimate_score_yield([]).as_record()["provenance"]
        self.assertEqual(provenance["source_sha256"], SOURCE_SHA256)
        self.assertIn("working_quasi_likelihood", provenance["statistical_model"])
        self.assertEqual(provenance["turn_unit"], "completed_episode_acquisition")
        self.assertEqual(provenance["credit_input"], "projected_marginal_credit")
        self.assertEqual(set(provenance["per_episode_units"]),
                         {"direct_sim_run", "math_or_comparison", "request_diagnostic", "root"})
        self.assertTrue(any("without integer coercion" in change
                            for change in provenance["adaptations"]))


if __name__ == "__main__":
    unittest.main()
