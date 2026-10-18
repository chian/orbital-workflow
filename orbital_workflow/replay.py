"""Fresh execution of the finite saved tool history, with no credit updates."""

from datetime import datetime, timezone
import json
from pathlib import Path

from .artifacts import Artifacts
from .durable import RunLock, save
from .persistence import PersistenceSettings
from .scientific import load_settings
from .smoke import environment
from .tools import ToolDispatcher


def replay_tools(directory: Path):
    with RunLock(directory):
        settings = load_settings(directory / "study.toml")
        destination = directory / datetime.now(timezone.utc).strftime("tool-replay-%Y%m%dT%H%M%S%fZ")
        destination.mkdir()
        provenance = environment(settings)
        provenance.update(execution="fresh_execution_of_saved_tool_history", scientific_credit=None)
        save(destination / "environment.json", provenance)
        store = Artifacts(directory / "objects")
        dispatcher = ToolDispatcher(store, PersistenceSettings(**settings["persistence"]))
        comparisons = []
        for path in sorted((directory / "tool-cache").glob("*.json")):
            original = json.loads(path.read_text())
            request_id = original["artifacts"][0]
            request = json.loads((store.directory / (request_id + ".json")).read_text())
            observation = dispatcher.execute(request["tool"], request["arguments"]).as_record()
            save(destination / path.name, observation)
            comparisons.append({"saved_tool_request": request_id, "tool": request["tool"],
                "identical_findings": observation["findings"] == original["findings"],
                "identical_artifact_references": observation["artifacts"] == original["artifacts"]})
        result = {"execution": "fresh tool replay; no Episode credit updates",
            "tool_operations": len(comparisons), "comparisons": comparisons,
            "all_findings_identical": all(item["identical_findings"] for item in comparisons),
            "all_artifact_references_identical": all(item["identical_artifact_references"] for item in comparisons),
            "scope": "Same source and machine libraries, same saved forcing; not independent equation verification",
            "directory": str(destination.resolve())}
        save(destination / "summary.json", result)
        return result
