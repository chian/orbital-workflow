"""On-demand visualization of the versioned episode store."""

from hashlib import sha256
from importlib.resources import files
import json
from pathlib import Path
import tomllib

from .storage import read_index, read_observation, read_forcing
from .viewer_timeline import load_timeline
from .gravity import scenario_problem


def saved_scenarios():
    project = Path(__file__).resolve().parents[1]
    rows = []
    for config in sorted((project / "scenarios").glob("*/study.toml")):
        problem = scenario_problem(tomllib.loads(config.read_text()))
        runs = [path for path in (project / ".artifacts" / problem["id"]).glob("run-*")
                if (path / "manifest.json").is_file()]
        archive = config.parent / "archive.json"
        reference = None
        if archive.exists():
            reference = project / json.loads(archive.read_text())["reference_run"]
        latest = max(runs, key=lambda path: (path / "manifest.json").stat().st_mtime_ns) if runs else reference
        rows.append({"id": problem["id"], "name": problem["name"],
                     "run_path": str(latest.resolve()) if latest and latest.is_dir() else None})
    return rows


def _digest(value):
    return sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def load_catalog(directory):
    """Index metadata only. No trajectory arrays or recursive Episode logs."""
    directory = Path(directory).resolve()
    warnings = []

    def small_json(name):
        path = directory / name
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text())
        except (OSError, ValueError) as error:
            warnings.append({"file": name, "error": type(error).__name__})
            return {}

    manifest = small_json("manifest.json")
    summary = small_json("summary.json")
    scenario = small_json("scenario.json") or {"id": manifest.get("scenario_id", "scenario_01")}
    marker = small_json("episode-store/format.json")
    if marker and (marker.get("format") != "orbital.episode-store" or marker.get("version") != 1):
        raise ValueError("Unsupported episode-store format")
    rows, issues = read_index(directory)
    warnings.extend(issues)
    timeline, issues = load_timeline(directory, rows)
    warnings.extend(issues)
    simulations = [{**row, "times": [], "states": None} for row in rows]
    primary = simulations[-1]["id"] if simulations else None
    return {
        "run_name": directory.name, "run_path": str(directory),
        "run_id": manifest.get("run_id", directory.name),
        "scenario": scenario,
        "run_state": "completed" if summary else "awaiting_completed_observations",
        "warnings": warnings, "simulations": simulations, "forcing": {},
        "default_primary": primary, "default_selected": [primary] if primary else [],
        "root_credit": [],
        "root_units_completed": summary.get("controller", {}).get("units"),
        "total_observations": len(rows),
        "timeline": timeline, "default_playback_mode": "progress",
        "display_notes": [
            "The index contains metadata. Numerical data is fetched only for selected observations.",
            "Display paths may retain a subset of saved states; the selected observation shows its display and source counts.",
            "Marker position and velocity are linearly interpolated between the displayed saved states; full-resolution arrays remain on disk.",
            "Motion is never extrapolated beyond an observation endpoint.",
            "Recurrence is a step history of recorded cycle endpoints, including the terminal partial cycle.",
            "Field arrows evaluate the declared equation with exact stored forcing interpolation; arrow lengths use a compressed display scale.",
            "The recurrence log view uses log1p(S / 1e-12); axis labels show original S.",
            "Live refresh discovers completed tool acquisitions. Intermediate solver steps are not stored.",
            "Run progress plays completed acquisitions in saved publication order, including repeated observations and both sides of comparisons.",
            "Each observation has the same screen duration in run progress; the simulation-time cursor always shows its actual saved time.",
            "Earlier paths and best-so-far recurrence are compared only within matching environment, forcing, model terms and observation scope.",
            "Colored perturbation arrows show each declared term with explicit display magnification. They act throughout the region, not at localized sources.",
            "Attractor positions follow the saved scenario's exact circular-binary solution, or its fixed single source. Source glyphs are enlarged for visibility; dashed rings show source orbits.",
        ],
    }


def render_document(data):
    payload = json.dumps(data, separators=(",", ":"), allow_nan=False)
    payload = payload.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    template = files("orbital_workflow").joinpath("templates/playback.html").read_text()
    return template.replace("__PLAYBACK_DATA__", payload)


def make_viewer(directory, output=None, *, observation_ids=None):
    """Offline run tour; numerical packets are decoded for current selections."""
    directory = Path(directory)
    if not directory.is_dir():
        raise FileNotFoundError("Run does not exist yet. Use visualize --serve to wait for it.")
    output = Path(output) if output else directory / "visualizations" / "playback.html"
    data = load_catalog(directory)
    selected = observation_ids if observation_ids is not None else [row["id"] for row in data["simulations"]]
    known = {item["id"] for item in data["simulations"]}
    if set(selected) - known:
        raise ValueError("Observation is not present in this run's episode index")
    selected = [row["id"] for row in data["simulations"] if row["id"] in selected]
    data["simulations"] = [row for row in data["simulations"] if row["id"] in selected]
    data["timeline"] = [item for item in data["timeline"] if item["observation_id"] in selected]
    data["embedded_observations"], data["embedded_forcing"] = {}, {}
    display_samples = 0
    for identity in selected:
        packet = read_observation(directory, identity)
        display_samples += len(packet["simulation"]["times"])
        data["embedded_observations"][identity] = json.dumps(packet["simulation"], separators=(",", ":"), allow_nan=False)
        forcing_id = packet["simulation"]["request"]["forcing_id"]
        if forcing_id not in data["embedded_forcing"]:
            data["embedded_forcing"][forcing_id] = json.dumps(read_forcing(
                directory, identity, 0, max_points=None), separators=(",", ":"), allow_nan=False)
    data["default_selected"] = list(selected)
    data["default_primary"] = selected[0] if selected else None
    data["display_notes"].append("This offline file embeds the exported observations as saved packets; it decodes only current selections. The embedded file itself still occupies memory.")
    html = render_document(data)
    output.parent.mkdir(parents=True, exist_ok=True)
    pending = output.with_suffix(output.suffix + ".pending")
    pending.write_text(html)
    pending.replace(output)
    manifest = {
        "viewer": output.name, "source_run": str(directory.resolve()),
        "run_id": data["run_id"], "observations": len(data["simulations"]),
        "source_observations": data["total_observations"],
        "saved_samples": sum(sim["sample_count"] for sim in data["simulations"]),
        "display_samples": display_samples,
        "timeline_entries": len(data["timeline"]),
        "viewer_sha256": sha256(html.encode()).hexdigest(), "data_sha256": _digest(data),
        "simulation_operations": 0, "model_calls": 0, "credit_updates": 0,
        "display_notes": data["display_notes"],
    }
    output.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return {"viewer": str(output.resolve()), "observations": manifest["observations"],
            "source_observations": data["total_observations"], "offline": True}
