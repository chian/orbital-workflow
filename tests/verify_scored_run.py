"""Read-only evidence checks for any completed scored-turn-v1 workflow run.

Usage: .venv/bin/python tests/verify_scored_run.py RUN --output EVIDENCE.json

An active run produces an explicitly incomplete prefix diagnostic. These are
software/accounting assertions, never scientific acceptance criteria. No model,
simulation, controller replay, or estimator fit is executed. Output must be
outside the run so its scientific records cannot be overwritten.
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
import fcntl
import hashlib
import io
import json
import math
from pathlib import Path
import sys
import tomllib
from types import SimpleNamespace


def same_number(actual, expected):
    return (type(actual) in (int, float) and type(expected) in (int, float)
            and math.isfinite(actual) and math.isfinite(expected)
            and math.isclose(actual, expected, rel_tol=1e-12, abs_tol=0.0))


def schema_required_order(schema):
    """Ignore required-name ordering while preserving every other constraint."""
    if not isinstance(schema, dict):
        return schema
    result = dict(schema)
    required = result.get("required")
    if isinstance(required, list) and all(isinstance(name, str) for name in required):
        result["required"] = sorted(required)
    for key in ("properties", "patternProperties", "$defs", "definitions", "dependentSchemas"):
        if isinstance(result.get(key), dict):
            result[key] = {name: schema_required_order(value) for name, value in result[key].items()}
    for key in ("allOf", "anyOf", "oneOf", "prefixItems"):
        if isinstance(result.get(key), list):
            result[key] = [schema_required_order(value) for value in result[key]]
    for key in ("items", "additionalItems", "contains", "additionalProperties", "propertyNames",
                "not", "if", "then", "else", "unevaluatedItems", "unevaluatedProperties", "contentSchema"):
        if key in result:
            value = result[key]
            result[key] = ([schema_required_order(item) for item in value] if isinstance(value, list)
                           else schema_required_order(value))
    return result


def active_writer(directory):
    path = directory / "run.lock"
    if not path.exists():
        return False
    with path.open("r") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
    return False


class Verifier:
    def __init__(self, directory):
        self.directory = directory.resolve()
        self.checked = Counter()
        self.discrepancies, self.pending, self.episodes = [], [], []
        self.hashes, self.machine, self.tools, self.metadata = {}, {}, {}, {}
        self.counts = {name: Counter() for name in ("branches", "tools", "cached_tools", "report_types", "model_roles")}
        self.unit_ids, self.links, self.observation_refs, self.report_ids = set(), {}, set(), set()
        self.form_ids, self.form_calls = set(), 0
        self.forcing_references = set()
        self.complete = (all((directory / name).is_file() for name in
                            ("record.json", "findings.json", "summary.json")) and not active_writer(directory))
        source = directory / "source-snapshot"
        if not (source / "orbital_workflow" / "credit.py").is_file():
            source = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(source))
        from orbital_workflow.bootstrap import use_method_loop
        loop_source = source if (source / "method_loop").is_dir() else source.parent / "OpenChia"
        use_method_loop(loop_source)
        from method_loop import EpisodeGoal, EpisodeRef, UnitRef
        from orbital_workflow.communication import ReportContract, generation_schema, validate_report
        from orbital_workflow.credit import compact_evidence, evidence_key, identity, project_observation
        from orbital_workflow.gravity import scenario_problem
        from orbital_workflow.records import Observation, plain
        from orbital_workflow.scientific import ScientificBindings
        from orbital_workflow.scenario import is_base_observation
        from orbital_workflow.report_facts import project_fields
        from orbital_workflow.failures import normalize_failure
        import numpy as np
        self.api = SimpleNamespace(EpisodeGoal=EpisodeGoal, EpisodeRef=EpisodeRef, UnitRef=UnitRef,
            ReportContract=ReportContract, compact=compact_evidence, key=evidence_key,
            identity=identity, project=project_observation, Observation=Observation, np=np)
        self.api.ScientificBindings = ScientificBindings
        self.api.generation_schema, self.api.validate_report = generation_schema, validate_report
        self.api.is_base_observation, self.api.project_fields = is_base_observation, project_fields
        self.api.normalize_failure = normalize_failure
        self.api.plain = plain
        self.source = source.resolve()
        self.settings = tomllib.loads(self.read_bytes(directory / "study.toml").decode())
        self.problem = plain(scenario_problem(self.settings))
        self.run_id = self.read_json(directory / "manifest.json")["run_id"]
        self.store = SimpleNamespace(directory=directory / "objects", json=self.artifact_json, arrays=self.forcing_seed)

    def check(self, condition, code, location, **details):
        self.checked[code] += 1
        if not condition:
            self.discrepancies.append({"code": code, "location": str(location), **details})

    def read_bytes(self, path):
        path = Path(path)
        payload = path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        if path in self.hashes and self.hashes[path] != digest:
            if self.complete:
                self.check(False, "input_changed_while_reading", path)
            else:
                self.pending.append({"code": "active_input_changed_while_reading", "file": str(path)})
        self.hashes[path] = digest
        return payload

    def read_json(self, path):
        return json.loads(self.read_bytes(path))

    def artifact_bytes(self, reference, suffix):
        if (not isinstance(reference, str) or len(reference) != 73 or not reference.startswith("artifact_")
                or any(c not in "0123456789abcdef" for c in reference[9:])):
            raise ValueError("Malformed artifact reference")
        path = self.directory / "objects" / (reference + suffix)
        payload = self.read_bytes(path)
        self.check("artifact_" + hashlib.sha256(payload).hexdigest() == reference,
                   "artifact_digest", path)
        return payload

    def artifact_json(self, reference):
        return json.loads(self.artifact_bytes(reference, ".json"))

    def forcing_seed(self, reference):
        # The evidence projector reads only the seed, not a forcing/trajectory log.
        with self.api.np.load(io.BytesIO(self.artifact_bytes(reference, ".npz")), allow_pickle=False) as data:
            return {"seed": data["seed"]}

    def guarded(self, location, function):
        try:
            return function()
        except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError) as error:
            self.check(False, "evidence_read_or_shape", location,
                       error=type(error).__name__, message=str(error))

    def references(self, value, location):
        for reference in value:
            paths = [self.directory / "objects" / (reference + suffix) for suffix in (".json", ".npz")]
            self.check(any(path.is_file() for path in paths), "artifact_exists", location, reference=reference)
            for path in paths:
                if path.is_file():
                    self.artifact_bytes(reference, path.suffix)

    def source_identity(self):
        identity = self.read_json(self.directory / "execution-identity.json")
        self.check(hashlib.sha256(self.read_bytes(self.directory / "study.toml")).hexdigest()
                   == identity["configuration_sha256"], "frozen_configuration_digest", "study.toml")
        for name, expected in identity["execution_sources"].items():
            path = self.source / name
            self.check(path.is_file() and hashlib.sha256(self.read_bytes(path)).hexdigest() == expected,
                       "frozen_source_digest", name)
        for kind, local in self.settings["episodes"].items():
            self.check(not {"forecast_memory", "initial_predicted_gain", "weights"}.intersection(local),
                       "no_controller_smoothing_configuration", kind)

    def tool_cache(self):
        for path in sorted((self.directory / "tool-cache").glob("*.json")):
            def inspect_tool():
                observation = self.read_json(path)
                self.references(observation["artifacts"], path)
                request_ref = observation["artifacts"][0]
                request = self.artifact_json(request_ref)
                diagnostic = (request["tool"] == "sim.run"
                              and observation["operation"] == "sim.request_diagnostic")
                self.check(request["tool"] == observation["operation"] or diagnostic,
                           "tool_operation_matches_request", path)
                self.counts["cached_tools"][observation["operation"]] += 1
                projected = self.api.project(self.api.Observation(observation["operation"],
                    observation["findings"], tuple(observation["artifacts"])), self.store)
                keys = []
                for item in projected.measurements:
                    key = self.api.key(item)
                    compact = self.api.compact(item)
                    self.machine[key] = compact
                    keys.append(key)
                    if compact["type"] == "trajectory":
                        measurement = compact["measurement"]
                        score = measurement["score"]
                        self.check(type(score) in (int, float) and math.isfinite(score) and score >= 0,
                                   "finite_nonnegative_simulator_score", path)
                        self.check(same_number(score, measurement["persistence_measurement"]["effective_duration"]),
                                   "score_is_measured_effective_duration", path)
                if observation["operation"] == "sim.run":
                    saved_ref = observation["artifacts"][-1]
                    saved = self.artifact_json(saved_ref)
                    self.observation_refs.add(saved_ref)
                    self.check(saved["summary"] == observation["findings"], "saved_score_and_summary_match_return", path)
                    self.check(saved["request"] == request["arguments"], "saved_simulator_request_matches", path)
                    self.check(len(keys) == 1, "one_run_one_scored_observation", path)
                    args = saved["request"]
                    self.forcing_references.add(args["forcing_id"])
                    self.check(args["forcing_seed"] == self.problem["forcing"]["seed"]
                        == int(self.forcing_seed(args["forcing_id"])["seed"]),
                        "every_run_uses_scenario_forcing_seed", path)
                    self.check(all(args[key] == self.problem[key] for key in
                        ("a", "sigma", "modulation_frequency", "rotating_amplitude", "rotating_frequency"))
                        and args["gravity"] == self.problem["gravity"]
                        and args["scenario_id"] == self.problem["id"]
                        and args["forcing_grid_step"] == self.problem["forcing"]["grid_step"]
                        and args["forcing_ar_decay"] == self.problem["forcing"]["ar_decay"],
                        "every_run_preserves_fixed_scenario_physics", path)
                    self.check(args["observation_window"] == self.problem["evaluation_interval"]
                        and saved["summary"]["persistence_measurement"]["settings"] == self.problem["persistence"],
                        "every_run_preserves_scenario_measurement_definition", path)
                    if args["experiment"]["kind"] == "base":
                        self.check(self.api.is_base_observation(args, self.problem)
                            and all(args[key] == value for key, value in self.problem["numerics"].items()),
                            "ordinary_run_uses_complete_bound_scenario", path)
                elif observation["operation"] == "sim.compare":
                    args = request["arguments"]
                    self.check(set(args) == {"left", "right"} and all(isinstance(v, str) for v in args.values()),
                               "comparison_uses_saved_observations", path)
                    for side in ("left", "right"):
                        self.check(self.artifact_json(args[side])["summary"] == observation["findings"][side],
                                   "comparison_preserves_saved_score", path, side=side)
                elif diagnostic:
                    args, findings = request["arguments"], observation["findings"]
                    window = args["observation_window"]
                    self.check(findings == {"code": "outside_observation_window",
                        "requested_interval": [args["start"], args["end"]], "observation_window": window},
                        "request_diagnostic_matches_declared_window", path)
                    self.check(window == [0.0, float(self.settings["study"]["horizon"])],
                               "request_diagnostic_uses_fixed_study_window", path)
                    self.check(args["start"] < window[0] or args["end"] > window[1],
                               "request_diagnostic_is_outside_window", path)
                    self.check(keys == [] and len(observation["artifacts"]) == 2,
                               "request_diagnostic_has_no_score_or_trajectory", path)
                    self.check(self.artifact_json(observation["artifacts"][-1]) == {
                        "operation": "sim.request_diagnostic", "findings": findings},
                        "request_diagnostic_result_saved_unchanged", path)
                self.tools[request_ref] = {"operation": observation["operation"],
                    "arguments": request["arguments"], "keys": keys, "artifacts": observation["artifacts"],
                    "findings": observation["findings"]}
            self.guarded(path, inspect_tool)
        self.check(len(self.forcing_references) <= 1,
                   "one_forcing_pattern_for_the_whole_scenario_run", "tool-cache")
        for path in sorted((self.directory / "tool-cache" / "failures").glob("*.json")):
            def failed_attempt():
                record = self.read_json(path)
                self.references(record["artifacts"], path)
                request = self.artifact_json(record["artifacts"][0])
                self.check(path.stem == self.api.identity({"attempt": record["attempt"], **request}),
                           "failed_attempt_retains_exact_request_and_correlation", path)
                self.api.normalize_failure(record["diagnostic"])
                self.checked["failed_attempt_has_only_typed_steering_diagnostic"] += 1
            self.guarded(path, failed_attempt)

    def root_score(self, item):
        if item["type"] != "trajectory":
            return None
        args = dict(item["physical"])
        interval = item["measurement"].get("requested_interval")
        if not isinstance(interval, (list, tuple)) or len(interval) != 2:
            return None
        args.update(start=interval[0], end=interval[1],
                    observation_window=item["measurement"].get("observation_window"))
        return item["measurement"]["score"] if self.api.is_base_observation(args, self.problem,
            forcing_seed=item.get("executed_forcing_seed", args.get("forcing_seed"))) else None

    def step(self, step, index, location):
        self.check(step["binding"] == "scored-turn-v1", "scored_turn_binding", location)
        self.check(step["units"] == index and step["yield_estimate"]["turns"] == index,
                   "one_controller_and_estimator_turn_per_unit", location)
        estimate = step["yield_estimate"]
        self.check(estimate["diagnostics"]["history_used"] == index,
                   "estimator_uses_full_acquisition_history", location)
        self.check(estimate["diagnostics"]["fitting_scope"] == "full_history"
                   and estimate["diagnostics"]["initialization"] == "cold_template_prior"
                   and estimate["provenance"]["credit_input"] == "projected_marginal_credit",
                   "estimator_is_declared_direct_history_fit", location)
        self.check(not {"forecast", "forecast_memory", "initial_predicted_gain", "forecast_residual"}.intersection(step),
                   "no_controller_smoothing_fields", location)
        band = estimate["expected_next_gain"]
        self.check(step["projected_credit"] == band == step["continuation"]["projected_gain"],
                   "continuation_consumes_estimator_output_unchanged", location)
        should_stop = band["status_code"] == 0 and band["upper"] <= step["continuation_cost"]
        self.check(step["stop"] == should_stop == step["continuation"]["stop"],
                   "continuation_is_current_upper_bound_rule", location)
        self.check(step["predicted_next_gain"] == (band["value"] if band["status_code"] == 0 else None),
                   "reported_prediction_is_current_estimate", location)

    def report_types(self, schema):
        kind = schema["type"]
        for name in kind if isinstance(kind, list) else [kind]:
            self.counts["report_types"][name] += 1
        if "string" in kind:
            self.counts["report_types"]["string:" + schema.get("format", "enum_or_const")] += 1
        for child in schema.get("properties", {}).values():
            self.report_types(child)
        if "items" in schema:
            self.report_types(schema["items"])

    def closed_episodes(self):
        for path in sorted((self.directory / "episodes").glob("episode_*.json")):
            def metadata():
                record = self.read_json(path)
                self.metadata[record["episode_id"]] = {key: record[key] for key in
                    ("episode_id", "path", "goal", "request", "scope_level", "controller_state", "units_consumed",
                     "ended_by", "end_reason")}
                self.metadata[record["episode_id"]]["file"] = path
            self.guarded(path, metadata)
        for episode_id, metadata in self.metadata.items():
            self.guarded(metadata["file"], lambda: self.episode(episode_id, metadata))

    def episode(self, episode_id, metadata):
        record = self.read_json(metadata["file"])
        self.counts["branches"][record["scope_level"]] += 1
        self.api.EpisodeGoal.from_record(record["goal"])
        self.api.EpisodeRef.from_record(record["episode_ref"])
        self.check(record["run_id"] == self.run_id, "episode_run_identity", episode_id)
        self.check(record["ended_by"] == "yield_stop", "closed_episode_ended_by_yield", episode_id)
        self.check(len(record["units"]) == record["units_consumed"], "recorded_unit_count", episode_id)
        initial = record["controller_state"].get("inherited_score", 0.0)
        target = record["controller_state"].get("credit_target")
        baseline = record["controller_state"].get("inherited_progress")
        complete_target = (target["projection"] == "complete_scenario" if target else
                           record["scope_level"] == "spaceship_trajectory_search")
        if target is not None:
            self.inheritance(record, target, baseline, initial)
        best, seen, own_runs, children = initial, set(), [], []
        for index, unit in enumerate(record["units"], 1):
            location = unit["unit_id"]
            self.api.UnitRef.from_record(unit["unit_ref"])
            self.check(unit["unit_ref"]["unit_index"] == index - 1, "unit_position_is_sequential", location)
            self.check(location not in self.unit_ids, "unit_identity_unique", location)
            self.unit_ids.add(location)
            step = unit["controller_step"]
            self.step(step, index, location)
            local = self.settings["episodes"][record["scope_level"]]
            self.check(step["continuation_cost"] == local["continuation_cost"]
                       and all(step["yield_estimate"]["parameters"][name] == value
                               for name, value in local["yield"].items()),
                       "controller_uses_frozen_episode_parameters", location)
            evidence = unit["controller_input"]
            expected_scores = []
            for item in evidence["measurements"]:
                key = self.api.key(item)
                seen.add(key)
                self.check(key in self.machine, "credit_evidence_has_machine_observation", location, evidence_key=key)
                if key in self.machine:
                    self.check(self.api.compact(item) == self.machine[key], "credit_evidence_matches_machine_values", location)
                score = (self.root_score(item) if complete_target
                         else item["measurement"]["score"] if item["type"] == "trajectory" else None)
                if score is not None:
                    expected_scores.append(score)
            assigned = step["score_assignment"]
            expected_best = max([best, *expected_scores])
            self.check(assigned["received_scores"] == expected_scores, "assigned_scores_are_projected_machine_scores", location,
                       actual=assigned["received_scores"], expected=expected_scores)
            self.check(same_number(step["credit"], expected_best) and same_number(assigned["score"], expected_best),
                       "credit_is_best_assigned_score", location)
            self.check(same_number(assigned["before"], best), "credit_before_matches_previous_turn", location)
            self.check(same_number(step["marginal_credit"], expected_best - best)
                       and same_number(assigned["marginal_credit"], expected_best - best),
                       "marginal_credit_is_best_score_delta", location)
            self.check(assigned["distinct_observations"] == len(seen), "observations_deduplicated", location)
            if target is not None:
                self.check(step["credit_target"] == target and step["inherited_progress"] == baseline
                           and same_number(step["inherited_score"], initial)
                           and same_number(step["gained_credit"], expected_best - initial),
                           "inherited_progress_is_separate_from_local_gain", location)
            best = expected_best
            durable = self.read_json(self.directory / "episodes" / "units" / (location + ".json"))
            self.check(durable["controller_step"] == step and durable["controller_input"] == evidence,
                       "durable_unit_matches_episode_record", location)
            if unit["child"] is not None:
                child = unit["child"]
                children.append(child["episode_id"])
                self.child(record, unit)
            else:
                tool = self.tools[evidence["artifacts"][0]]
                operation = tool["operation"]
                self.counts["tools"][operation] += 1
                self.check([self.api.key(item) for item in evidence["measurements"]] == tool["keys"],
                           "leaf_matches_one_declared_tool_observation", location)
                if operation == "sim.run":
                    own_runs.append(tool["artifacts"][-1])
                    self.check(evidence["findings"][0]["run_index"] == len(own_runs), "episode_run_index", location)
                    self.check(len(evidence["measurements"]) == 1
                               and evidence["measurements"][0]["type"] == "trajectory",
                               "run_acquisition_returns_one_score", location)
                elif operation == "sim.compare":
                    self.check(all(ref in own_runs for ref in tool["arguments"].values()),
                               "comparison_reuses_this_episodes_prior_runs", location)
                    # Reconstruct only the run-owned pure findings projection;
                    # this executes no acquisition, integration or controller.
                    # Historical snapshots may retain their former projection.
                    projection = self.api.ScientificBindings.project_tool(SimpleNamespace(
                        tools=SimpleNamespace(store=self.store), completed_runs={"verification": own_runs}),
                        self.api.Observation(operation, tool["findings"], tuple(tool["artifacts"])),
                        SimpleNamespace(goal=SimpleNamespace(goal_id="verification")))
                    self.check(evidence["findings"] == projection.as_record()["findings"],
                               "comparison_findings_match_run_owned_projection", location)
                    measurements = projection.as_record()["findings"][0]["measurements"]
                    if "run_indices" in measurements:
                        aliases = {side: [i + 1 for i, ref in enumerate(own_runs)
                                          if ref == tool["arguments"][side]] for side in ("left", "right")}
                        self.check(measurements["run_indices"] == aliases
                                   and "observation_references" not in measurements,
                                   "comparison_models_receive_all_local_indices_without_audit_references", location)
                    self.check(step["marginal_credit"] == 0, "saved_comparison_adds_no_score_improvement", location)
                elif operation == "sim.request_diagnostic":
                    self.check(expected_scores == [] and evidence["measurements"] == []
                               and step["marginal_credit"] == 0,
                               "request_diagnostic_is_one_unscored_feedback_acquisition", location)
                    self.check(all("run_index" not in finding for finding in evidence["findings"]),
                               "request_diagnostic_is_not_a_completed_simulation", location)
                elif operation.startswith("math."):
                    self.check(expected_scores == [] and step["marginal_credit"] == 0,
                               "math_has_no_fabricated_score_bonus", location)
        self.links[episode_id] = children
        self.check(bool(record["units"]) and record["controller_state"] == record["units"][-1]["controller_step"],
                   "final_controller_matches_last_unit", episode_id)
        self.check(record["controller_state"]["stop"] is True, "yield_end_has_controller_stop", episode_id)
        manifest_path = self.directory / "episode-store" / "episodes" / episode_id / "manifest.json"
        manifest = self.read_json(manifest_path)
        self.check(manifest["state"] == "closed" and manifest["children"] == children,
                   "closed_episode_manifest", episode_id)
        for field in ("audit_file", "request_file", "result_file"):
            if not manifest.get(field) and not self.complete:
                self.pending.append({"code": "closed_episode_publication_pending", "episode": episode_id, "field": field})
                continue
            self.check(bool(manifest.get(field)) and (self.directory / manifest[field]).is_file(),
                       "closed_episode_files_exist", episode_id, field=field)
        if manifest.get("result_file"):
            result = self.read_json(self.directory / manifest["result_file"])
            self.check({self.api.key(item) for item in result["measurements"]} == seen,
                       "episode_result_preserves_distinct_evidence", episode_id)
            if record["goal"]["parent_goal_id"] and manifest.get("parent_report_file"):
                self.typed_report(episode_id, metadata, result,
                    self.read_json(self.directory / manifest["parent_report_file"]), episode_id)
            elif record["goal"]["parent_goal_id"]:
                if self.complete:
                    self.check(False, "closed_child_parent_report_exists", episode_id)
                else:
                    self.pending.append({"code": "parent_report_publication_pending", "episode": episode_id})
        self.episodes.append({"episode_id": episode_id, "kind": record["scope_level"],
            "ended_by": record["ended_by"], "units": record["units_consumed"], "best_score": best})

    def inheritance(self, record, target, baseline, initial):
        """Read prior machine bookkeeping; do not execute/replay a controller."""
        location = record["episode_id"]
        if record["goal"]["parent_goal_id"]:
            relation = record["request"]["message"]["findings"]["credit_target"]
            parent_path = record["path"][:-1]
            parent_meta = next((meta for meta in self.metadata.values() if meta["path"] == parent_path), None)
            invocation_index = int(record["path"][-1][1].split("-", 2)[1])
            parent_unit = Verifier.recorded_unit(self, parent_path, invocation_index - 1) if invocation_index else None
            prior = parent_unit["controller_step"] if parent_unit is not None else None
            if prior is None and parent_meta is not None and not invocation_index:
                state = parent_meta["controller_state"]
                prior = {"credit": state["inherited_score"], "credit_target": state["credit_target"]}
            self.check(relation in {"parent", "new"}
                       and record["controller_state"]["credit_target_relationship"] == relation,
                       "parent_explicitly_declares_target_relationship", location)
            if prior is not None:
                parent_target = prior["credit_target"]
                self.check((target == parent_target and same_number(initial, prior["credit"]))
                           if relation == "parent" else (target != parent_target and initial == 0 and baseline is None),
                           "baseline_matches_known_same_parent_target", location)
            elif self.complete:
                self.check(False, "parent_initialization_or_prior_unit_exists", location)
            else:
                self.pending.append({"code": "parent_initialization_not_closed", "episode": location})
                if relation == "new" or (not invocation_index and len(parent_path) == 1):
                    self.check(initial == 0 and baseline is None, "new_or_initial_root_target_has_no_prior_gain", location)
        else:
            self.check(initial == 0 and baseline is None, "root_starts_without_inherited_progress", location)
        if baseline is None:
            self.check(initial == 0, "no_unbacked_numeric_baseline", location)
            return
        item = baseline["observation"]
        key = self.api.key(item)
        self.check(baseline["target"] == target and key in self.machine
                   and self.api.compact(item) == self.machine.get(key),
                   "baseline_is_unchanged_machine_evidence_on_same_target", location)
        score = (self.root_score(item) if target["projection"] == "complete_scenario"
                 else item["measurement"]["score"] if item["type"] == "trajectory" else None)
        self.check(same_number(initial, score), "baseline_is_eligible_machine_score", location)
        source_path, source_unit = baseline["source_path"], baseline["source_unit"]
        if (type(source_unit) is not int or source_unit < 1 or not source_path
                or len(source_path) >= len(record["path"]) or source_path != record["path"][:len(source_path)]):
            self.check(False, "baseline_source_is_prior_eligible_ancestor_acquisition", location)
            return
        source_observation = Verifier.recorded_unit(self, source_path, source_unit - 1)
        if source_observation is None:
            self.check(False, "baseline_source_acquisition_exists", location)
            return
        invocation_index = int(record["path"][len(source_path)][1].split("-", 2)[1])
        self.check(source_path == record["path"][:len(source_path)] and 0 < source_unit <= invocation_index
                   and source_observation["controller_step"]["credit_target"] == target
                   and any(self.api.compact(value) == self.api.compact(item)
                           for value in source_observation["controller_input"]["measurements"]),
                   "baseline_source_is_prior_eligible_ancestor_acquisition", location)

    def recorded_unit(self, path, index):
        """A still-open ancestor already has immutable committed unit events."""
        metadata = next((item for item in self.metadata.values() if item["path"] == path), None)
        if metadata is not None:
            units = self.read_json(metadata["file"])["units"]
            if 0 <= index < len(units):
                return units[index]
        episode = self.api.EpisodeRef(run_id=self.run_id, path=path)
        unit = self.api.UnitRef(episode.episode_id, index)
        source = self.directory / "episodes" / "units" / (unit.unit_id + ".json")
        return self.read_json(source) if source.is_file() else None

    def child(self, parent, unit):
        child, update = unit["child"], unit["episode_update"]
        location = unit["unit_id"]
        metadata = self.metadata[child["episode_id"]]
        self.check(child.get("unit_records_archived") is True and child["units"] == [],
                   "closed_child_trace_is_disk_reference", location)
        self.check((self.directory / child["record_file"]).resolve() == metadata["file"].resolve(),
                   "child_reference_resolves_to_actual_record", location)
        self.check(metadata["goal"]["parent_goal_id"] == parent["goal"]["goal_id"]
                   and metadata["goal"]["task_context"] == parent["goal"]["task_context"],
                   "child_goal_link_and_root_context", location)
        result_ref = unit["child_result"]
        self.check(result_ref["storage_format"] == "orbital.result-ref/v1", "closed_child_result_is_disk_reference", location)
        result = self.read_json(self.directory / result_ref["result_file"])
        expected = [self.api.compact(item) for item in result["measurements"]]
        self.check(unit["controller_input"]["measurements"] == expected,
                   "parent_receives_child_measurements_not_child_totals", location)
        self.check(update["controller_input"] == unit["controller_input"], "child_update_matches_parent_credit_input", location)
        self.typed_report(child["episode_id"], metadata, result, update["report"], location)
        report_path = self.directory / "episode-store" / "episodes" / child["episode_id"] / "parent-report.json"
        self.check(self.read_json(report_path) == update["report"], "parent_report_saved_unchanged", location)

    def typed_report(self, episode_id, metadata, result, values, location):
        contract = self.api.ReportContract.from_record(metadata["request"]["report_contract"])
        identifiers = tuple(dict.fromkeys([episode_id, metadata["goal"]["goal_id"],
            *metadata["request"]["message"]["artifacts"], *result["artifacts"]]))
        contract.admit(values, audit_identifiers=identifiers)
        if "report_values" in result:
            self.check(result["report_values"] == values,
                       "parent_receives_childs_completed_form_unchanged", location)
        bindings = self.api.plain(contract.fact_bindings)
        if bindings:
            parent = next((item for item in self.metadata.values()
                           if item["goal"]["goal_id"] == metadata["goal"]["parent_goal_id"]), None)
            target = parent["controller_state"]["credit_target"]["projection"] if parent is not None else None
            if target is None:
                invocation = int(metadata["path"][-1][1].split("-", 2)[1])
                parent_unit = self.recorded_unit(metadata["path"][:-1], invocation)
                if parent_unit is None and invocation:
                    parent_unit = self.recorded_unit(metadata["path"][:-1], invocation - 1)
                if parent_unit is not None:
                    target = parent_unit["controller_step"]["credit_target"]["projection"]
            if target is None:
                deferred = {name for name, binding in bindings.items()
                            if binding["select"].startswith("parent_target")}
                bindings = {name: binding for name, binding in bindings.items()
                            if name not in deferred}
                if deferred:
                    self.pending.append({"code": "parent_target_projection_awaits_parent_state", "episode": episode_id})
                projection = None
            else:
                projection = (self.root_score if target == "complete_scenario" else
                              lambda item: item["measurement"]["score"] if item["type"] == "trajectory" else None)
            expected = self.api.project_fields(bindings, result["measurements"], self.store, projection)
            self.check(all(values[name] == value for name, value in expected.items()),
                       "contracted_facts_match_exact_scored_saved_observations", location)
        if episode_id not in self.report_ids:
            self.checked["typed_parent_report_matches_actual_contract"] += 1
            self.report_types(contract.as_record()["value_schema"])
            self.report_ids.add(episode_id)

    def prefix_units(self):
        for path in sorted((self.directory / "episodes" / "units").glob("*.json")):
            event = self.read_json(path)
            unit_id = event["unit"]["unit_id"]
            if unit_id not in self.unit_ids:
                self.guarded(path, lambda: self.step(event["controller_step"], event["unit"]["unit_index"] + 1, unit_id))

    def models(self):
        decisions = {"decide-" + self.api.identity(meta["path"]): meta for meta in self.metadata.values()}
        expected_forms = {name for name, meta in decisions.items()
            if meta["goal"]["parent_goal_id"] and self.api.ReportContract.from_record(
                meta["request"]["report_contract"]).interpretation_schema()["properties"]}
        form_attempts = {}
        def form_attempt(name, context, location):
            index = context["form_attempt"]
            valid = type(index) is int and index >= 0
            self.check(valid, "form_attempt_is_nonnegative_integer", location)
            if valid:
                form_attempts.setdefault(name, set()).add(index)

        for path in sorted((self.directory / "model-cache").glob("*.json")):
            def cached_model():
                value = self.read_json(path)
                request = value["request"]
                self.check(path.stem == self.api.identity(request), "model_cache_request_identity", path)
                name, role = request["episode"], request["role"]
                self.check(name.startswith("decide-") or name == "final-report",
                           "no_independent_child_report_composer", path)
                expected_role = self.settings["models"]["routing"][
                    "decide" if name.startswith("decide-") else "human_report"]
                self.check(role == expected_role, "model_task_uses_configured_role", path)
                if name not in decisions:
                    if self.complete and name.startswith("decide-"):
                        self.check(False, "model_conversation_belongs_to_recorded_episode", path)
                    return
                meta = decisions[name]
                context = request["context"]
                self.check(context["task_context"] == meta["goal"]["task_context"]
                    and context["parent_report_contract"] == meta["request"]["report_contract"],
                    "planner_receives_root_context_and_parent_contract", path)
                self.check(context["mode"] in {"action", "form"}, "model_turn_has_declared_purpose", path)
                if context["mode"] == "form":
                    self.form_calls += 1
                    form_attempt(name, context, path)
                    self.form_input(name, meta, request, value["response"], path)
            self.guarded(path, cached_model)
        if self.complete:
            self.check(self.form_ids == expected_forms,
                       "children_fill_interpretations_in_their_own_conversation", "model-cache")
        retirements = []
        for attempt in sorted((self.directory / "model-attempts").glob("attempt-*")):
            sessions, retired = Counter(), Counter()
            for path in sorted(attempt.glob("session-*/session-*.json")):
                value = self.read_json(path)
                selected = self.settings["models"][value["role"]]
                self.check(value["model"] == value["server_model"] == selected["model"]
                    and value["effort"] == value["server_effort"] == selected["reasoning_effort"],
                    "server_model_and_effort_match_requested_role", path)
                sessions[(value["episode_id"], value["role"])] += 1
                self.counts["model_roles"][value["role"]] += 1
            for path in sorted(attempt.glob("session-*/call-*/request.json")):
                value = self.read_json(path)
                selected = self.settings["models"][value["role"]]
                self.check(value["model"] == selected["model"] and value["effort"] == selected["reasoning_effort"],
                           "model_call_matches_requested_role", path)
                context = value["context"]["current"]
                if context.get("mode") == "form":
                    # Malformed JSON is retained by the provider audit, but it
                    # never reaches CachedModels' successful-response cache.
                    form_attempt(value["episode_id"], context, path)
            for path in sorted((attempt / "retired-sessions").glob("*.json")):
                value = self.read_json(path)
                self.check(value["local_session_removed"] is True and type(value["provider_exit_code"]) is int,
                           "retired_provider_exited_and_session_removed", path)
                retired[(value["episode_id"], value["role"])] += 1
                retirements.append(value)
            if self.complete:
                self.check(all(retired[key] >= count for key, count in sessions.items()),
                           "completed_model_sessions_all_retired", attempt)
            elif sessions - retired:
                self.pending.append({"code": "active_model_sessions_not_retired_yet", "attempt": attempt.name,
                                     "count": sum((sessions - retired).values())})
        for name, attempts in form_attempts.items():
            self.check(sorted(attempts) == list(range(max(attempts) + 1)),
                       "form_corrections_retain_attempt_relationship", name)
        return {"retirement_records": len(retirements),
                "maximum_active_workers": max((v["maximum_active_workers"] for v in retirements), default=0)}

    def form_input(self, name, metadata, request, response, location):
        context = request["context"]
        contract = self.api.ReportContract.from_record(metadata["request"]["report_contract"])
        expected = {"objective": metadata["goal"]["objective"],
            "task_context": metadata["goal"]["task_context"],
            "assignment": metadata["request"]["message"]["findings"],
            "parent_report_contract": metadata["request"]["report_contract"],
            "completion": {key: metadata[key] for key in ("ended_by", "end_reason", "units_consumed")}}
        for field, value in expected.items():
            self.check(context.get(field) == value, "child_form_uses_own_" + field, location)
        self.check(schema_required_order(request["schema"]) == schema_required_order(
                       self.api.generation_schema(contract.interpretation_schema())),
                   "form_call_can_return_only_requested_interpretation_fields", location)
        record = self.read_json(metadata["file"])
        expected_observations = [finding for unit in record["units"]
                                 for finding in unit["controller_input"]["findings"]]
        expected_reports = [unit["episode_update"]["report"] for unit in record["units"]
                            if unit["episode_update"] is not None]
        self.check(context["own_tool_observations"] == expected_observations
                   and context["child_reports"] == expected_reports,
                   "child_form_receives_local_observations_and_only_admitted_direct_reports", location)
        self.check(context["controller"]["units"] == metadata["units_consumed"]
                   and len(context["local_credit_history"]) == metadata["units_consumed"],
                   "form_turn_adds_no_acquisition_or_estimator_observation", location)
        result_file = self.directory / "episode-store" / "episodes" / metadata["episode_id"] / "result.json"
        if not result_file.is_file():
            if self.complete:
                self.check(False, "closed_child_form_result_exists", location)
            else:
                self.pending.append({"code": "child_form_result_publication_pending", "episode": metadata["episode_id"]})
            return
        result = self.read_json(result_file)
        self.check(context["recorded_form_values"] == {key: result["report_values"][key]
                   for key in contract.fact_bindings}, "child_sees_exact_recorded_form_fields", location)
        identifiers = tuple(dict.fromkeys((metadata["episode_id"], metadata["goal"]["goal_id"],
            *metadata["request"]["message"]["artifacts"], *result["artifacts"])))
        try:
            self.api.validate_report(response, contract.interpretation_schema())
            completed = {**context["recorded_form_values"], **response}
            contract.admit(completed, audit_identifiers=identifiers)
        except (ValueError, TypeError):
            # Retain the invalid proposal; a later form_attempt must correct it.
            # This is not scientific work or an admitted parent result.
            self.checked["unadmitted_form_attempt_retained"] += 1
            return
        if completed == result["report_values"]:
            self.form_ids.add(name)

    def run(self):
        self.guarded("execution identity", self.source_identity)
        self.tool_cache()
        self.closed_episodes()
        self.prefix_units()
        model_summary = self.models()
        if self.complete:
            root = self.read_json(self.directory / "record.json")
            self.check(root == self.read_json(self.metadata[root["episode_id"]]["file"]),
                       "root_record_matches_closed_audit", "record.json")
            reachable, frontier = set(), [root["episode_id"]]
            while frontier:
                episode_id = frontier.pop()
                if episode_id not in reachable:
                    reachable.add(episode_id)
                    frontier.extend(self.links.get(episode_id, []))
            self.check(reachable == set(self.metadata), "completed_tree_contains_all_closed_episodes", "record.json")
            summary = self.read_json(self.directory / "summary.json")
            self.check(summary["controller"] == root["controller_state"] and summary["ended_by"] == root["ended_by"],
                       "summary_matches_final_root", "summary.json")
            for path, expected in tuple(self.hashes.items()):
                self.check(hashlib.sha256(path.read_bytes()).hexdigest() == expected,
                           "original_input_unchanged", path)
        else:
            self.pending.append({"code": "root_run_not_complete", "active_writer": active_writer(self.directory)})
        return {"format": "orbital.scored-run-verification/v1", "run": str(self.directory),
            "run_id": self.run_id, "verified_at": datetime.now(timezone.utc).isoformat(),
            "purpose": "Read-only software/accounting evidence; no scientific acceptance criteria",
            "status": ("complete_verified" if not self.discrepancies else "complete_with_discrepancies")
                      if self.complete else "incomplete_prefix",
            "complete": self.complete, "binding_sources": str(self.source),
            "counts": {**{name: dict(value) for name, value in self.counts.items()},
                "closed_episodes": len(self.episodes), "scored_observations": len(self.observation_refs),
                "closed_episode_units": len(self.unit_ids), "child_form_episodes": len(self.form_ids), "child_form_calls": self.form_calls, **model_summary},
            "checks": dict(self.checked), "checks_performed": sum(self.checked.values()),
            "episodes": self.episodes, "discrepancies": self.discrepancies, "pending": self.pending,
            "limitations": ["The estimator fitter is not recomputed; completed cached replay supplies that evidence",
                "Disk retirement records establish recorded teardown, not a process-heap memory inspection",
                "An active prefix may change during inspection and cannot establish final run completeness"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    directory, output = args.run.resolve(), args.output.resolve()
    if not directory.is_dir():
        parser.error("RUN must be an existing saved workflow directory")
    if output.is_relative_to(directory):
        parser.error("--output must be outside RUN to preserve the original records")
    report = Verifier(directory).run()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({"status": report["status"], "checks_performed": report["checks_performed"],
                      "discrepancies": len(report["discrepancies"]), "output": str(output)}))
    return 2 if not report["complete"] else 1 if report["discrepancies"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
