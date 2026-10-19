"""Compare audit baselines without importing or running scientific code."""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[1]


def manifest(root, excluded):
    result = {}
    for directory, children, names in os.walk(root):
        children[:] = [name for name in children if name not in excluded]
        for name in names:
            path = Path(directory) / name
            if path.suffix in {".pyc", ".pyo"}:
                continue
            if path.is_file():
                result[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def differences(before, after):
    return {
        "original_files": len(before), "current_files": len(after),
        "changed": sorted(key for key in before.keys() & after.keys() if before[key] != after[key]),
        "deleted": sorted(before.keys() - after.keys()),
        "added": sorted(after.keys() - before.keys()),
    }


def main():
    baseline = json.loads((BASE / "run-before-sha256.json").read_text())
    run = Path(baseline["run"])
    scientific = differences(baseline["sha256"], manifest(run, {"__pycache__"}))
    before = json.loads((BASE / "working-tree-before-sha256.json").read_text())
    working = differences(before, manifest(REPO, {".git", ".venv", ".artifacts", "audits", "__pycache__"}))
    source = json.loads((run / "execution-identity.json").read_text())["execution_sources"]
    source_matches = {}
    for name, digest in source.items():
        path = (REPO.parent / "OpenChia" / name) if name.startswith("method_loop/") else REPO / name
        source_matches[name] = hashlib.sha256(path.read_bytes()).hexdigest() == digest
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, text=True, capture_output=True, check=True).stdout.strip()
    status = subprocess.run(["git", "status", "--short"], cwd=REPO, text=True, capture_output=True, check=True).stdout
    snapshot = json.loads((BASE / "STOPPED_STATE.json").read_text())
    result = {
        "format": "orbital.audit-integrity/v1", "checked_at": datetime.now(timezone.utc).isoformat(),
        "scientific_run": str(run), "scientific_files": scientific,
        "working_tree_outside_artifacts_audits_environments": working,
        "critical_frozen_sources_match": source_matches,
        "repository_head": head, "repository_head_matches_baseline": head == snapshot["repository_head"],
        "git_status": status,
        "goal_status": "paused", "goal_evidence": "Primary agent read get_goal after seven reviews; returned status paused. No goal mutation during this audit.",
        "scientific_goal_completion_claimed": False,
        "audit_actions": "Read-only source/JSON/CSV/saved-array inspection, existing accounting verifier and audit-artifact validation only; audit outputs live exclusively in this directory.",
        "limits": ["Python bytecode is excluded from both baselines.", "Working-tree baseline was captured after the scientific-run baseline; frozen source comparison independently binds execution code.", "Audit artifact writes are intentionally excluded from the working-tree baseline."]
    }
    result["unchanged"] = (not any(scientific[key] or working[key] for key in ("changed", "deleted", "added"))
                           and all(source_matches.values()) and result["repository_head_matches_baseline"])
    (BASE / "INTEGRITY.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"unchanged": result["unchanged"], "scientific_files": scientific,
                      "working_tree_files": working, "critical_sources": len(source_matches)}))


if __name__ == "__main__":
    main()
