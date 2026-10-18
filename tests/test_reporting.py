"""Human report labels must agree with the root's actual scientific scope."""

import copy
from pathlib import Path
import unittest

from orbital_workflow.bootstrap import use_method_loop
use_method_loop(Path(__file__).resolve().parents[2] / "OpenChia")

from orbital_workflow.reporting import full_scope
from orbital_workflow.scientific import ScientificBindings, load_settings


class ReportScope(unittest.TestCase):
    def test_complete_target_labels_follow_declared_environment_and_physical_scope(self):
        root = Path(__file__).resolve().parents[1]
        settings = load_settings(root / "scenarios/scenario_02/study.toml")
        binding = ScientificBindings(settings, None, None)
        problem, study = binding.problem, settings["study"]
        base = {"scenario_id": problem["id"], "gravity": problem["gravity"],
                "initial_state": [*problem["initial_position"], 0.1, -1.2],
                "start": 0, "spatial_box": None, "radial_limits": problem["radial_limits"],
                "terms": {"central": True, "modulation": True, "rotating": True, "forcing": True},
                "gravity_mode": "resolved", "active_bodies": None, "a": .15, "sigma": .03}
        cases = [("complete", {}, True),
                 ("declared environment", {"a": study["a"][0], "sigma": study["sigma"][0]}, True),
                 ("forcing amplitude reduction", {"sigma": 0}, False),
                 ("undeclared modulation", {"a": .123456}, False),
                 ("different scenario identity", {"scenario_id": "another_scenario"}, False),
                 ("monopole", {"gravity_mode": "monopole"}, False),
                 ("one source", {"active_bodies": ["body_1"]}, False),
                 ("continuation", {"start": 1}, False),
                 ("spatial observation", {"spatial_box": [-1, 1, -1, 1]}, False),
                 ("other insertion", {"initial_state": [2, 0, 0.1, -1.2]}, False),
                 ("other radial domain", {"radial_limits": [0, 3]}, False),
                 ("omitted forcing", {"terms": {**base["terms"], "forcing": False}}, False)]
        for name, changes, expected in cases:
            with self.subTest(name=name):
                request = {**copy.deepcopy(base), **copy.deepcopy(changes)}
                projected = binding.root_score({"type": "trajectory", "physical": request,
                                                "measurement": {"score": 1}})
                self.assertEqual(full_scope(request, problem, study), expected)
                self.assertEqual(full_scope(request, problem, study), projected is not None)


if __name__ == "__main__":
    unittest.main()
