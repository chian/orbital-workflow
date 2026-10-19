"""Reviewable observations, figures and a contracted FAST interpretation."""

import csv
import hashlib
from importlib.metadata import version
import json
from pathlib import Path

import numpy as np

from .artifacts import Artifacts
from .credit import identity, trajectory_evidence
from .durable import CachedModels, RunLock, save
from .models import ModelConnection
from .scientific import load_settings
from .gravity import GravitySystem, scenario_problem
from .scenario import is_base_observation


def walk(record, directory=None):
    if directory is not None and record.get("unit_records_archived"):
        record = json.loads((Path(directory) / record["record_file"]).read_text())
    yield record
    for unit in record["units"]:
        if unit["child"]:
            yield from walk(unit["child"], directory)


def observation_groups(findings):
    groups = {}
    for item in findings["measurements"]:
        if item["type"] == "trajectory":
            groups.setdefault(item["physical_id"], []).append(item)
    return groups


def observation_row(chosen, group):
    """One recorded measurement; display selection never replaces its values."""
    measurement, physical = chosen["measurement"], chosen["physical"]
    persistence = measurement["persistence_measurement"]
    durations = [x["measurement"]["score"] for x in group]
    return {**physical, "forcing_seed": chosen["executed_forcing_seed"],
        "physical_id": chosen["physical_id"],
        "evidence_key": chosen.get("evidence_key"),
        "initial_state": physical["initial_state"],
        "vx": physical["initial_state"][2], "vy": physical["initial_state"][3],
        "scenario_id": physical["scenario_id"],
        "gravity": physical["gravity"],
        "outcome": measurement["outcome"],
        "requested_interval": measurement["requested_interval"],
        "observation_window": measurement.get("observation_window"),
        "experiment": measurement.get("experiment"),
        "start": measurement["requested_interval"][0],
        "end": measurement["requested_interval"][1],
        "observed_interval": measurement["observed_interval"],
        "observed_until": measurement["observed_interval"][1],
        "effective_duration": measurement["score"],
        "mean_similarity": persistence["mean_similarity"],
        "complete_revolutions": persistence["complete_revolutions"],
        "numerical_settings": measurement["numerical_settings"],
        "distinct_observations": len(group),
        "minimum_observed_effective_duration": min(durations),
        "maximum_observed_effective_duration": max(durations)}


def all_observations(findings):
    """Every distinct acquired measurement, including numerical refinements."""
    return [observation_row(item, group)
            for group in observation_groups(findings).values() for item in group]


def write_observations_csv(path, findings):
    """Export actual rows, preserving refinements instead of display winners."""
    fields = ["physical_id", "evidence_key", "scenario_id", "gravity", "gravity_mode", "active_bodies", "a", "sigma", "vx", "vy", "forcing_seed", "terms", "requested_interval", "observation_window", "experiment", "observed_interval", "numerical_settings", "outcome", "observed_until", "effective_duration",
              "mean_similarity", "complete_revolutions", "distinct_observations", "minimum_observed_effective_duration", "maximum_observed_effective_duration"]
    with Path(path).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows({key: json.dumps(value, sort_keys=True) if isinstance(value, (dict, list, tuple)) else value
                          for key, value in row.items()} for row in all_observations(findings))


def select_observations(findings):
    selected = []
    for group in observation_groups(findings).values():
        def resolution(item):
            measured = item["measurement"]
            settings = measured["numerical_settings"]
            return (measured["requested_interval"][1], -settings["sample_step"],
                    -settings["max_step"], -settings["rtol"])
        # Largest observed interval, then finest declared resolution. This is a
        # display choice, not a scientific qualification of an observation.
        chosen = max(group, key=resolution)
        selected.append(observation_row(chosen, group))
    return selected


def full_scope(item, problem, study=None):
    """Project the same fixed scenario definition used for root accounting."""
    return is_base_observation(item, problem, forcing_seed=item.get("forcing_seed"))


def comparison_context(observation, store):
    values = observation["findings"]
    arguments = store.json(observation["artifacts"][0])["arguments"]
    arguments = {side: store.json(arguments[side])["request"] for side in ("left", "right")}
    left, right = arguments["left"], arguments["right"]
    physical = [name for name in ("initial_state", "a", "sigma", "terms", "forcing_id", "gravity", "active_bodies", "gravity_mode") if left.get(name) != right.get(name)]
    scope = [name for name in ("start", "end", "radial_limits", "spatial_box") if left[name] != right[name]]
    numerical = [name for name in ("method", "max_step", "rtol", "atol", "sample_step") if left[name] != right[name]]
    kind = ("physical_comparison" if physical else "observation_scope_comparison" if scope
            else "numerical_comparison" if numerical else "replay_comparison")
    result = {key: values[key] for key in ("score_difference", "common_time_count", "common_interval", "max_absolute_component_difference", "terminal_time_difference")}
    result.update(comparison_kind=kind, changed_physical_inputs=physical,
                  changed_scope_inputs=scope, changed_numerical_inputs=numerical)
    for side in ("left", "right"):
        result[side] = {key: value for key, value in values[side].items()
                        if key not in {"persistence_measurement", "solver_message"}}
        persistence = values[side]["persistence_measurement"]
        result[side]["persistence"] = {key: persistence[key] for key in
            ("effective_duration", "mean_similarity", "complete_revolutions", "settings")}
        result[side]["forcing_seed"] = int(store.arrays(arguments[side]["forcing_id"])["seed"])
    return result


def make_figure(directory, record, store, problem, study):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    trajectories = []
    for path in sorted(store.directory.glob("*.json")):
        value = json.loads(path.read_text())
        if set(value) == {"request", "summary", "trajectory"}:
            value["physical_id"] = trajectory_evidence(value["request"], value["summary"], store)["physical_id"]
            value["request"]["forcing_seed"] = int(store.arrays(value["request"]["forcing_id"])["seed"])
            trajectories.append(value)
    grouped = {}
    for value in trajectories:
        request = value["request"]
        order = (request["end"], -request["sample_step"], -request["max_step"], -request["rtol"])
        prior = grouped.get(value["physical_id"])
        if prior is None or order > prior[0]:
            grouped[value["physical_id"]] = (order, value)
    trajectories = [item[1] for item in grouped.values()]
    full = [item for item in trajectories if full_scope(item["request"], problem, study)]
    full.sort(key=lambda x: x["summary"]["persistence_measurement"]["effective_duration"], reverse=True)
    choices, seen = [], set()
    for value in full:
        request = value["request"]
        key = (request["a"], request["sigma"], tuple(request["initial_state"]), request["forcing_id"])
        if key not in seen:
            choices.append(value)
            seen.add(key)
        if len(choices) == 4:
            break
    if not choices:
        choices = trajectories[:4]
    figure, axes = plt.subplots(2, 2, figsize=(12, 9), layout="constrained")
    for value in choices:
        arrays = store.arrays(value["trajectory"])
        req, result = value["request"], value["summary"]
        vx, vy = req["initial_state"][2:]
        label = f"v=({vx:g},{vy:g}), a={req['a']:g}, σ={req['sigma']:g}"
        axes[0, 0].plot(arrays["states"][:, 0], arrays["states"][:, 1], label=label, linewidth=1)
        axes[0, 1].plot(arrays["times"], np.linalg.norm(arrays["states"][:, :2], axis=1), label=label)
        cycles = result["persistence_measurement"]["cycles"]
        axes[1, 0].plot([cycle["interval"][1] for cycle in cycles],
                        np.cumsum([cycle["effective_duration"] for cycle in cycles]), ".-")
    for radius in problem["radial_limits"]:
        axes[0, 0].add_patch(plt.Circle((0, 0), radius, fill=False, color="0.7", linestyle=":"))
        axes[0, 1].axhline(radius, color="0.7", linestyle=":")
    gravity = GravitySystem.from_record(problem["gravity"])
    for body in gravity.sources(0):
        radius = float(np.linalg.norm(body["position"]))
        if radius:
            axes[0, 0].add_patch(plt.Circle((0, 0), radius, fill=False, linestyle="--", alpha=.35))
        axes[0, 0].plot(*body["position"], "o", label=f"{body['id']}, M={body['mass']:g}, t=0")
    axes[0, 0].set(xlabel="x", ylabel="y", title="Observed trajectory candidates", aspect="equal")
    axes[0, 0].legend(fontsize=7)
    axes[0, 1].set(xlabel="time", ylabel="radius", title="Observed radial motion")
    axes[1, 0].set(xlabel="time", ylabel="effective recurrence duration", title="Measured recurrence accumulation")
    units = record["units"]
    positions = [0, *range(1, len(units) + 1)]
    axes[1, 1].plot(positions, [0, *[u["controller_step"]["credit"] for u in units]], ".-", label="best assigned returned score")
    axes[1, 1].plot(positions[1:], [u["controller_step"]["predicted_next_gain"] for u in units], ".-", label="predicted next gain")
    axes[1, 1].axhline(record["controller_state"]["continuation_cost"], color="0.6", linestyle=":", label="continuation cost")
    axes[1, 1].set(xlabel="root investigation unit", ylabel="credit", title="Root accounting and numerical continuation")
    axes[1, 1].legend(fontsize=8)
    figure.savefig(directory / "findings.png", dpi=160)
    plt.close(figure)


async def report_run(directory: Path):
    with RunLock(directory):
        return await _report_run(directory)


async def _report_run(directory: Path):
    settings = load_settings(directory / "study.toml")
    problem = scenario_problem(settings)
    record = json.loads((directory / "record.json").read_text())
    findings = json.loads((directory / "findings.json").read_text())
    selected = select_observations(findings)
    full = sorted([item for item in selected if full_scope(item, problem, settings["study"])], key=lambda x: x["effective_duration"], reverse=True)
    episodes = [{key: item[key] for key in ("scope_level", "units_consumed", "ended_by")}
                for item in walk(record, directory)]
    review_path = directory / "communication-review.json"
    communication_review = json.loads(review_path.read_text()) if review_path.exists() else None
    editorial_path = directory / "editorial-review.json"
    editorial = json.loads(editorial_path.read_text()) if editorial_path.exists() else None
    if editorial is not None:
        replacements = editorial["replacements"]
        allowed_fields = {"observed_findings", "credit_behavior", "limitations", "next_investigation"}
        if not isinstance(replacements, dict) or set(replacements) - allowed_fields or any(
                not isinstance(value, str) for value in replacements.values()):
            raise ValueError("Editorial review replaces only declared human-report prose fields")
    store = Artifacts(directory / "objects")
    comparisons = []
    for path in sorted((directory / "tool-cache").glob("*.json")):
        observation = json.loads(path.read_text())
        if observation["operation"] == "sim.compare":
            comparisons.append(comparison_context(observation, store))
    context = {"question": record["goal"]["objective"], "root_control": record["controller_state"],
        "scenario": problem,
        "recurrence_definition": "Compare each revolution with its immediate predecessor at matching orbital phases; the first revolution supplies the initial reference only. Sum each subsequent full or partial revolution's observed duration times exp(-squared normalized position, velocity and relative-period mismatch). This effective duration is not radial residence time.",
        "episodes": episodes,
        "selected_observations": selected, "matched_differences": comparisons,
        "communication_review": communication_review,
        "limitations": ["Finite, adaptively selected trajectories; no survival probability estimate or global optimum",
            "Base-scenario and explicitly derived experiment observations have separate scientific scopes",
            "One fixed forcing realization is reused throughout this scenario; there is no independent forcing-sample estimate",
            "Recurrence compares successive winding cycles; first revolution supplies the initial reference; non-winding cycles unmeasured",
            "Yield uncertainty is a template-derived working-model approximation, not a calibrated confidence interval",
            "Available branches need not be visited; episode records identify the branches actually used",
            "A numerical yield stop expresses the configured forecast, not scientific success"]}
    provenance = {"report_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  "matplotlib": version("matplotlib"), "models": settings["models"],
                  "editorial_review": editorial}
    destination = directory / "reports" / ("report-" + identity({"input": context, "provenance": provenance})[:16])
    destination.mkdir(parents=True, exist_ok=True)
    schema = {"type": "object", "properties": {name: {"type": "string"} for name in
              ("observed_findings", "credit_behavior", "limitations", "next_investigation")},
              "required": ["observed_findings", "credit_behavior", "limitations", "next_investigation"], "additionalProperties": False}
    attempt_root = directory / "model-attempts"
    attempt = attempt_root / f"attempt-{len(list(attempt_root.iterdir())) + 1:03d}"
    async with ModelConnection(settings["models"], attempt, Path(__file__).resolve().parents[1]) as connection:
        models = CachedModels(connection, directory / "model-cache")
        interpretation = await models.complete("final-report", settings["models"]["routing"]["human_report"],
            "Interpret supplied measured observations concisely. Distinguish original full model from reductions, high-water discovery credit from current measurements, and unobserved cases from zero performance. "
            "Comparison kinds and changed inputs are explicit. A physical-model or insertion-velocity difference is an experimental effect, not a solver discrepancy or loss of numerical confidence. "
            "Numerical comparisons hold physical inputs and scope fixed. Display selected effective_duration values as current measurements; maximum_observed_effective_duration is the historical high water. "
            "Retain any supplied communication-review issues: declared types do not establish correct arithmetic or interpretation. "
            "No invented results, acceptance gates, global optimum, indefinite stability or survival probability claims. Every numerical claim must follow the supplied data.", context, schema)
        save(attempt / "report-execution.json", {"fresh_model_calls": models.fresh_calls, "replayed_model_calls": models.replayed_calls})
    save(destination / "report-input.json", context)
    save(destination / "report-provenance.json", provenance)
    save(destination / "interpretation.json", interpretation)
    if editorial:
        save(destination / "editorial-review.json", editorial)
        interpretation = {**interpretation, **editorial["replacements"]}
    write_observations_csv(destination / "observations.csv", findings)
    state = record["controller_state"]
    lines = ["# Orbital trajectory investigation: " + problem["id"], "", problem["name"], "",
        "Fixed gravity: `" + json.dumps(problem["gravity"]) + "`. The ship is a test particle. Collision surfaces and radial exits describe observations. Reduced source-force models remain labelled separately.", "", interpretation["observed_findings"], "",
        "Effective recurrence duration compares each revolution with the preceding one at matching orbital phases, then sums duration times continuous similarity. The first revolution supplies the initial reference; it is not itself credited as recurrence. This quantity differs from time spent inside the radial observation region.", "",
        "## Complete-model observations", "",
        "The row shows the best displayed candidate in the fixed scenario, using the longest observation and then finest declared resolution for each physical input. Every distinct recorded observation and numerical refinement is included in observations.csv.", "",
        "| a | σ | Displayed insertion (vx, vy) | End time | Outcome | Effective recurrence duration |",
        "|---|---|---|---|---|---|"]
    a, sigma = problem["a"], problem["sigma"]
    if full:
        item = full[0]
        lines.append(f"| {a:g} | {sigma:g} | ({item['vx']:g}, {item['vy']:g}) | {item['observed_until']:.8g} | {item['outcome']} | {item['effective_duration']:.8g} |")
    else:
        lines.append(f"| {a:g} | {sigma:g} | unknown | — | unobserved | unknown |")
    visited = sorted({episode["scope_level"] for episode in episodes})
    lines += ["", "The episodes visited in this run were " + ", ".join(f"`{kind}`" for kind in visited) + ". Availability of a branch does not imply that this run used it.",
        "", "## Credit and continuation", "",
        f"The root ended by `{record['ended_by']}` after {record['units_consumed']} units. Its best returned score was {state['credit']:.8g}. The current projected marginal-credit band was `{json.dumps(state['projected_credit'])}` against continuation cost {state['continuation_cost']:g}.", "",
        interpretation["credit_behavior"], "", "The score assignment, estimator and continuation contracts are in CREDIT.md. Each simulator call supplies one score. Its duration and integration steps are not estimator exposure. Parent credit is recomputed from scored observations; child scalar credits are never summed into the root.", "",
        "## Limits and next investigation", "", interpretation["limitations"], "", interpretation["next_investigation"], ""]
    if communication_review:
        lines += ["## Communication observations", "",
            "The upward reports met their parent-selected types. The following post-run observations concern interpretation, not format admission. Original reports and credit are unchanged.", ""]
        for issue in communication_review["issues"]:
            lines += [issue["explanation"], ""]
    lines += ["## Evidence", "", "![Trajectories, recurrence and root credit](findings.png)", "",
        "Run inputs and execution records below are in the run directory, two levels above this report version.", "",
        "- `study.toml`, `environment.json`: frozen configuration and execution provenance.",
        "- `record.json`, `episodes/`: actual recursive method_loop records and numerical control.",
        "- `model-attempts/`, `model-cache/`: prompts, responses, selected model/effort and reports.",
        "- `tool-cache/`, `objects/`: exact tool inputs, stored forcing, trajectories and diagnostics.",
        "- `communication-review.json`: post-run review observations, when present.",
        "- `observations.csv`, `report-input.json`: displayed measurements and interpretation inputs.", ""]
    if editorial:
        lines += ["The final prose incorporates the saved Codex editorial review. `interpretation.json` retains the unedited FAST draft; `editorial-review.json` records the reviewed replacements. These human-readable report files are separate from child-to-parent communication.", ""]
    (destination / "REPORT.md").write_text("\n".join(lines))
    make_figure(destination, record, store, problem, settings["study"])
    # Retain pre-revision human reports before updating the latest pointer.
    latest = directory / "REPORT.md"
    if latest.exists() and not (directory / "latest-report.json").exists():
        legacy = directory / "reports" / "legacy"
        legacy.mkdir(exist_ok=True)
        for name in ("REPORT.md", "findings.png", "observations.csv", "report-input.json", "interpretation.json"):
            old = directory / name
            if old.exists():
                (legacy / name).write_bytes(old.read_bytes())
    (directory / "latest-report.json").write_text(json.dumps({"report": str(destination.relative_to(directory) / "REPORT.md")}, indent=2) + "\n")
    latest.write_text("# Orbital trajectory report\n\n[Current findings](" + str(destination.relative_to(directory) / "REPORT.md") + ")\n")
    return {"report": str(destination.resolve() / "REPORT.md"), "figure": str(destination.resolve() / "findings.png"),
            "episodes": len(episodes), "full_model_inputs": len(full), "all_selected_inputs": len(selected)}
