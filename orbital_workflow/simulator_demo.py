"""Finite scenario-bound examples; no trajectory search or Episode credit."""

import json
from pathlib import Path

import numpy as np

from .artifacts import Artifacts
from .gravity import GravitySystem
from .records import plain
from .scenario import ScenarioSimulator
from .tools import ToolDispatcher


def plot_trajectories(store, observations, destination, problem):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(1, 3, figsize=(15, 4.5), layout="constrained")
    for label, observation in observations.items():
        saved = store.json(observation.artifacts[-1])
        arrays = store.arrays(saved["trajectory"])
        times, states = arrays["times"], arrays["states"]
        axes[0].plot(states[:, 0], states[:, 1], label=label, linewidth=1.2)
        axes[1].plot(times, np.linalg.norm(states[:, :2], axis=1), label=label)
        cycles = observation.findings["persistence_measurement"]["cycles"]
        axes[2].plot([cycle["interval"][1] for cycle in cycles],
                     [cycle["similarity"] for cycle in cycles], ".-", label=label)
    for radius in problem["radial_limits"]:
        if radius > 0:
            axes[0].add_patch(plt.Circle((0, 0), radius, fill=False, color="0.7", linestyle=":"))
        axes[1].axhline(radius, color="0.7", linestyle=":")
    initial = problem["initial_position"]
    axes[0].scatter([initial[0]], [initial[1]], color="black", marker="x", label="insertion")
    gravity = GravitySystem.from_record(plain(problem["gravity"]))
    for body in gravity.sources(problem["evaluation_interval"][0]):
        radius = float(np.linalg.norm(body["position"]))
        if radius:
            axes[0].add_patch(plt.Circle((0, 0), radius, fill=False, color="0.7", linestyle="--"))
        axes[0].plot(*body["position"], "o", label=f"{body['id']}, M={body['mass']:g}, start")
    axes[0].set(xlabel="x", ylabel="y", title="Spaceship trajectories", aspect="equal")
    axes[1].set(xlabel="time", ylabel="radius", title="Observed radial motion")
    axes[2].set(xlabel="end of observed revolution", ylabel="continuous similarity",
                title="Recurrence relative to prior revolution", ylim=(-0.03, 1.03))
    axes[0].legend(fontsize=8)
    figure.savefig(destination, dpi=160)
    plt.close(figure)


def run_demo(directory: Path, configuration: dict):
    directory.mkdir(parents=True, exist_ok=False)
    store = Artifacts(directory / "artifacts")
    simulator = ScenarioSimulator(configuration, store)
    problem = plain(simulator.problem)
    (directory / "scenario.json").write_text(json.dumps(problem, indent=2) + "\n")
    dispatcher = ToolDispatcher(store, simulator.persistence_settings)
    vx, vy = problem["reference_velocity"]
    insertion = {"vx": vx, "vy": vy}
    numerics = problem["numerics"]
    observations, public_requests = {}, {}
    for label, arguments, parts in (
            ("gravity only", {**insertion, "experiment": {
                "terms": {"modulation": False, "rotating": False, "forcing": False}}}, True),
            ("full environment", insertion, False),
            ("full, finer integration", {**insertion, "experiment": {"refinement": {
                "max_step": numerics["max_step"] / 2, "sample_step": numerics["sample_step"] / 2}}}, True)):
        resolved = simulator.resolve_run(arguments, parts=parts)
        tool_request = {"tool": "sim.run", "arguments": arguments}
        key = label.replace(",", "").replace(" ", "-")
        (directory / (key + "-request.json")).write_text(json.dumps(tool_request, indent=2) + "\n")
        (directory / (key + "-resolved-request.json")).write_text(json.dumps({
            "tool": "sim.run", "arguments": resolved}, indent=2) + "\n")
        public_requests[label] = {"file": key + "-request.json", "parts": parts,
                                  "resolved_file": key + "-resolved-request.json"}
        observation = dispatcher.execute("sim.run", resolved)
        observations[label] = observation
        (directory / (key + "-observation.json")).write_text(json.dumps(observation.as_record(), indent=2) + "\n")
    comparisons = {}
    for label, left, right in (
            ("gravity-to-full", "gravity only", "full environment"),
            ("integration-refinement", "full environment", "full, finer integration")):
        request = {"tool": "sim.compare", "arguments": {
            "left": observations[left].artifacts[-1],
            "right": observations[right].artifacts[-1]}}
        (directory / (label + "-request.json")).write_text(json.dumps(request, indent=2) + "\n")
        comparison = dispatcher.execute(request["tool"], request["arguments"])
        (directory / (label + "-observation.json")).write_text(json.dumps(comparison.as_record(), indent=2) + "\n")
        comparisons[label] = comparison.as_record()
    plot_trajectories(store, observations, directory / "trajectories.png", problem)
    summary = {label: {"outcome": obs.findings["outcome"],
                       "score": obs.findings["score"],
                       "observed_until": obs.findings["observed_interval"][1],
                       "effective_recurrence_duration": obs.findings["persistence_measurement"]["effective_duration"],
                       "complete_revolutions": obs.findings["persistence_measurement"]["complete_revolutions"]}
               for label, obs in observations.items()}
    result = {"demonstration_only": True, "scientific_credit": None,
              "scenario_id": problem["id"], "public_requests": public_requests,
              "forcing": next(iter(observations.values())).artifacts[1], "measurements": summary,
              "saved_observation_comparisons": comparisons,
              "plot": str(directory / "trajectories.png"),
              "note": "Same insertion and stored forcing; no trajectory search or Episode completion implied."}
    (directory / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
