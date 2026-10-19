"""Finite scalar calculations used to close numerical investigation questions."""

from decimal import Decimal, localcontext
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from orbital_workflow.bootstrap import use_method_loop
use_method_loop(Path(__file__).resolve().parents[2] / "OpenChia")

from orbital_workflow.artifacts import Artifacts
from orbital_workflow.records import plain
from orbital_workflow.tools import ToolDispatcher
from orbital_workflow.failures import ActionRequestError, ToolAcquisitionFailure, failure_diagnostic


class ScalarArithmetic(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store = Artifacts(Path(self.directory.name))
        self.tools = ToolDispatcher(self.store)

    def calculate(self, expression, **values):
        return self.tools.execute("math.arithmetic", {"expression": expression, "values": values})

    def test_actual_stalled_three_score_ratio_and_order(self):
        # Actual supplied scores from run-scored-003; this is an arithmetic
        # regression fixture and does not run or manufacture a simulation.
        inputs = {"coarse": .16618101298027446,
                  "medium": .1661407076470878, "fine": .1661308271558801}
        ratio = self.calculate("(coarse-medium)/(medium-fine)", **inputs)
        order = self.calculate("log2((coarse-medium)/(medium-fine))", **inputs)
        with localcontext() as context:
            context.prec = 40
            coarse, medium, fine = (Decimal(str(inputs[key])) for key in ("coarse", "medium", "fine"))
            expected = (coarse - medium) / (medium - fine)
        self.assertEqual(ratio.findings["diagnostic"]["code"], "ok")
        self.assertAlmostEqual(ratio.findings["value"], float(expected), places=10)
        self.assertAlmostEqual(order.findings["value"], math.log2(float(expected)), places=10)
        self.assertEqual(set(ratio.findings), {"expression", "inputs", "value", "diagnostic"})
        self.assertEqual(plain(ratio.findings["inputs"]), inputs)

    def test_whitelisted_arithmetic_functions_and_signs(self):
        for expression, expected in [
            ("-x + +y * 3 / 2", 2), ("x**3", 8),
            ("log(exp(x))", 2), ("log(8,2)", 3),
            ("log2(8)+log10(100)", 5), ("sqrt(9)+abs(-x)", 5),
            ("sin(0)+cos(0)", 1),
        ]:
            with self.subTest(expression=expression):
                result = self.calculate(expression, x=2, y=8/3)
                self.assertEqual(result.findings["diagnostic"]["code"], "ok")
                self.assertAlmostEqual(result.findings["value"], expected)

    def test_division_domain_and_overflow_are_typed_null_observations(self):
        for expression, code in [
            ("1/0", "division_by_zero"), ("0/0", "division_by_zero"),
            ("sqrt(-1)", "domain_error"), ("log(0)", "domain_error"),
            ("(-1)**0.5", "domain_error"), ("exp(1000)", "overflow"),
            ("1e308*1e308", "overflow"), ("2**1e308", "overflow"),
        ]:
            with self.subTest(expression=expression):
                result = self.calculate(expression)
                self.assertIsNone(result.findings["value"])
                self.assertEqual(result.findings["diagnostic"], {"code": code})
                self.assertNotIn("score", result.findings)

    def test_unsupported_syntax_cannot_execute_side_effects(self):
        marker = Path(self.directory.name) / "side-effect"
        expressions = [
            f"__import__('pathlib').Path({str(marker)!r}).touch()",
            "x.__class__", "x[0]", "[x for x in (1,2)]", "lambda:1",
            "(x:=1)", "True", "'hello'", "1j", "1;2", "1//2", "1%2",
            "sqrt(x=4)", "sqrt(*(4,))", "sqrt()", "sqrt(1,2)",
        ]
        with patch("orbital_workflow.tools.subprocess.run") as subprocess:
            for expression in expressions:
                with self.subTest(expression=expression):
                    result = self.calculate(expression, x=1)
                    self.assertIsNone(result.findings["value"])
                    self.assertEqual(result.findings["diagnostic"]["code"], "invalid_expression")
        subprocess.assert_not_called()
        self.assertFalse(marker.exists())

    def test_unknown_name_is_reported_without_guessing_a_value(self):
        result = self.calculate("missing+1")
        self.assertIsNone(result.findings["value"])
        self.assertEqual(result.findings["diagnostic"]["code"], "unknown_name")

    def test_expression_resource_bounds_are_per_calculation(self):
        for expression in ["1" * 1025, "+".join(["1"] * 100), "-" * 40 + "1"]:
            with self.subTest(length=len(expression)):
                result = self.calculate(expression)
                self.assertIsNone(result.findings["value"])
                self.assertEqual(result.findings["diagnostic"]["code"], "expression_limit")
        # A rejected expression has no effect on later independent calculations.
        self.assertEqual(self.calculate("2+3").findings["value"], 5)

    def test_inputs_are_only_named_finite_real_scalars(self):
        for values in [{"x": True}, {"x": "1"}, {"x": [1]}, {"x": math.nan},
                       {"x": math.inf}, {"not-a-name": 1}]:
            with self.subTest(values=values), self.assertRaises(ActionRequestError) as failure:
                self.tools.arithmetic_calculation({"expression": "x", "values": values})
            self.assertEqual(failure.exception.diagnostic,
                failure_diagnostic("wrong_parameters", tool="math.arithmetic", field="values"))
        for arguments in [{}, {"expression": 1, "values": {}},
                          {"expression": "1", "values": {}, "code": "pass"}]:
            with self.subTest(arguments=arguments), self.assertRaises(ToolAcquisitionFailure) as failure:
                self.tools.execute("math.arithmetic", arguments)
            self.assertIsInstance(failure.exception.__cause__, ActionRequestError)
            self.assertEqual(failure.exception.diagnostic, failure_diagnostic("wrong_parameters",
                tool="math.arithmetic", field="expression" if arguments.get("expression") == 1 else None))

    def test_calculation_stores_deterministic_results_without_integrating(self):
        with patch("orbital_workflow.tools.integrate") as integrate:
            first = self.calculate("sqrt(x*x)+1", x=2)
            second = self.calculate("sqrt(x*x)+1", x=2)
        integrate.assert_not_called()
        self.assertEqual(first.as_record(), second.as_record())
        self.assertEqual(len(first.artifacts), 2)  # Exact request and result.
        request, result = map(self.store.json, first.artifacts)
        self.assertEqual(request["tool"], "math.arithmetic")
        self.assertEqual(result, {"operation": "math.arithmetic", "findings": plain(first.findings)})
        self.assertFalse(list(self.store.directory.glob("*.npz")))


if __name__ == "__main__":
    unittest.main()
