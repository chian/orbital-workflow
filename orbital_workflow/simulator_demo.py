"""Inspectable simulator example, using the same dispatcher as Episodes."""

from dataclasses import asdict
import json
import math
from pathlib import Path

import numpy as np

from .artifacts import Artifacts
from .persistence import PersistenceSettings
from .simulation import ModelTerms, SimulationRequest, generate_forcing
from .tools import ToolDispatcher


def plot_trajectories(store, observations, destination):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(1, 3, figsize=(15, 4.5), layout="constrained")
    for label, observation in observations.items():
        # sim.run exposes request, forcing, trajectory arrays, then summary.
        arrays = store.arrays(observation.artifacts[2])
        times, states = arrays["times"], arrays["states"]
        axes[0].plot(states[:, 0], states[:, 1], label=label, linewidth=1.2)
        axes[1].plot(times, np.linalg.norm(states[:, :2], axis=1), label=label)
        cycles = observation.findings["persistence_measurement"]["cycles"]
        axes[2].plot([cycle["interval"][1] for cycle in cycles],
                     [cycle["similarity"] for cycle in cycles], ".-", label=label)
    for radius in (0.5, 2):
        axes[0].add_patch(plt.Circle((0, 0), radius, fill=False, color="0.7", linestyle=":"))
        axes[1].axhline(radius, color="0.7", linestyle=":")
    axes[0].scatter([1], [0], color="black", marker="x", label="insertion")
    axes[0].set(xlabel="x", ylabel="y", title="Spaceship trajectories", aspect="equal")
    axes[1].set(xlabel="time", ylabel="radius", title="Observed radial motion")
    axes[2].set(xlabel="end of observed revolution", ylabel="continuous similarity",
                title="Recurrence relative to prior revolution", ylim=(-0.03, 1.03))
    axes[0].legend(fontsize=8)
    figure.savefig(destination, dpi=160)
    plt.close(figure)


def run_demo(directory: Path, settings: PersistenceSettings):
    directory.mkdir(parents=True, exist_ok=False)
    store = Artifacts(directory / "artifacts")
    forcing = generate_forcing(store, trial=1, horizon=40 * math.pi)
    dispatcher = ToolDispatcher(store, settings)
    observations = {}
    for label, terms, max_step, sample_step in (
            ("central only", ModelTerms(modulation=False, rotating=False, forcing=False), .05, .02),
            ("full environment", ModelTerms(), .05, .02),
            ("full, finer integration", ModelTerms(), .025, .01)):
        request = SimulationRequest(forcing, terms=terms, max_step=max_step, sample_step=sample_step)
        tool_request = {"tool": "sim.run", "arguments": asdict(request)}
        key = label.replace(",", "").replace(" ", "-")
        (directory / (key + "-request.json")).write_text(json.dumps(tool_request, indent=2) + "\n")
        observation = dispatcher.execute(tool_request["tool"], tool_request["arguments"])
        observations[label] = observation
        (directory / (key + "-observation.json")).write_text(json.dumps(observation.as_record(), indent=2) + "\n")
    plot_trajectories(store, observations, directory / "trajectories.png")
    summary = {label: {"outcome": obs.findings["outcome"],
                       "observed_until": obs.findings["observed_interval"][1],
                       "effective_recurrence_duration": obs.findings["persistence_measurement"]["effective_duration"],
                       "complete_revolutions": obs.findings["persistence_measurement"]["complete_revolutions"]}
               for label, obs in observations.items()}
    result = {"demonstration_only": True, "scientific_credit": None,
              "forcing": forcing, "measurements": summary,
              "plot": str(directory / "trajectories.png"),
              "note": "Same insertion and stored forcing; no trajectory search or Episode completion implied."}
    (directory / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
