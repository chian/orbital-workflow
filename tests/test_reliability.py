"""Reproduction, identity and interpretation boundaries, using local tools."""

import asyncio
from dataclasses import asdict, replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from orbital_workflow.bootstrap import use_method_loop
use_method_loop(Path(__file__).resolve().parents[2] / "OpenChia")

from orbital_workflow.artifacts import Artifacts
from orbital_workflow.credit import CreditController, project_observation
from orbital_workflow.durable import (CachedTools, IncompatibleResumeError,
    execution_identity, require_compatible_resume, save)
from orbital_workflow.persistence import PersistenceSettings
from orbital_workflow.reporting import comparison_context
from orbital_workflow.runtime import Kind
from orbital_workflow.scientific import load_settings, run_scientific
from orbital_workflow.simulation import ModelTerms, SimulationRequest, generate_forcing
from orbital_workflow.tools import ToolDispatcher


CONFIG = Path(__file__).resolve().parents[1] / "study.toml"


class ReproductionSemantics(unittest.TestCase):
    def test_numeric_spelling_does_not_duplicate_a_physical_observation_or_credit(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Artifacts(Path(directory))
            forcing = generate_forcing(store, 1, 2)
            tools = ToolDispatcher(store)
            integer_state = SimulationRequest(forcing, end=2, initial_state=(1, 0, 0, 1))
            float_state = SimulationRequest(forcing, end=2.0, start=0.0, initial_state=(1.0, 0.0, 0.0, 1.0))
            first = project_observation(tools.execute("sim.run", asdict(integer_state)), store)
            second = project_observation(tools.execute("sim.run", asdict(float_state)), store)
            self.assertEqual(first.measurements, second.measurements)
            controller = CreditController(load_settings(CONFIG), Kind.ROOT)
            controller.observe("first", first, is_root=True)
            step = controller.observe("same physical input", second, is_root=True)
            self.assertEqual(step.record["marginal_credit"], 0)
            self.assertEqual(step.record["components"]["distinct_observations"], 1)

    def test_switches_are_booleans_and_booleans_are_not_numeric_coordinates(self):
        with self.assertRaises(ValueError):
            ModelTerms(forcing="false")
        with self.assertRaises(ValueError):
            SimulationRequest("unused", initial_state=(1, 0, True, 1))
        with self.assertRaises(ValueError):
            SimulationRequest("unused", radial_limits=(.5, float("inf")))

    def test_resume_with_changed_configuration_fails_before_any_model_process_or_state_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            text = CONFIG.read_text()
            (directory / "study.toml").write_text(text)
            save(directory / "execution-identity.json", execution_identity(text))
            require_compatible_resume(directory, text)
            (directory / "study.toml").write_text(text + "\n# Changed frozen configuration\n")
            before = {path.name: path.read_bytes() for path in directory.iterdir()}
            with patch("orbital_workflow.scientific.ModelConnection") as provider:
                with self.assertRaises(IncompatibleResumeError):
                    asyncio.run(run_scientific(directory, CONFIG, resume=True))
                provider.assert_not_called()
            self.assertEqual(before, {path.name: path.read_bytes() for path in directory.iterdir()})

    def test_corrupted_artifact_cannot_be_replayed_as_a_completed_tool_observation(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            store = Artifacts(directory / "objects")
            tools = CachedTools(store, PersistenceSettings(), directory / "cache")
            arguments = {"operation": "central_circular_reference", "radius": 1}
            observation = tools.execute("math.numeric", arguments)
            path = store.directory / (observation.artifacts[0] + ".json")
            path.write_bytes(path.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "Artifact bytes changed"):
                tools.execute("math.numeric", arguments)
            self.assertEqual(tools.replayed_calls, 0)

    def test_report_comparisons_keep_the_physical_and_numerical_change_context(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Artifacts(Path(directory))
            tools = ToolDispatcher(store)
            forcing = generate_forcing(store, 1, 2)
            full = SimulationRequest(forcing, end=2)
            reduced = replace(full, terms=ModelTerms(rotating=False))
            physical = tools.execute("sim.compare", {"left": asdict(full), "right": asdict(reduced)})
            view = comparison_context(physical.as_record(), store)
            self.assertEqual(view["comparison_kind"], "physical_comparison")
            self.assertEqual(view["changed_physical_inputs"], ["terms"])
            self.assertTrue(view["left"]["terms"]["rotating"])
            self.assertFalse(view["right"]["terms"]["rotating"])
            refined = replace(full, max_step=.025, rtol=1e-8, atol=1e-10)
            comparison = tools.execute("sim.compare", {"left": asdict(full), "right": asdict(refined)})
            view = comparison_context(comparison.as_record(), store)
            self.assertEqual(view["comparison_kind"], "numerical_comparison")
            self.assertEqual(view["changed_physical_inputs"], [])
            self.assertEqual(set(view["changed_numerical_inputs"]), {"max_step", "rtol", "atol"})
            self.assertEqual(view["left"]["forcing_seed"], view["right"]["forcing_seed"])


if __name__ == "__main__":
    unittest.main()
