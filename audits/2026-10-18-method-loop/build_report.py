"""Assemble read-only audit reports. Does not import or execute workflow code."""

from copy import deepcopy
import json
from pathlib import Path
import re

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[1]
GROUPS = ["Verified defects", "Unresolved questions", "Mechanisms checked and working correctly"]
FIELDS = [
    ("requirement", "Requirement"), ("owner", "Owner"), ("trigger", "Trigger"),
    ("code_path", "Code path"), ("state_effect", "State effect"),
    ("communication_effect", "Communication effect"), ("credit_effect", "Credit effect"),
    ("controller_effect", "Controller effect"), ("run_evidence", "Run evidence"),
    ("proposed_correction", "Proposed correction"), ("verification", "Verification"),
]


def load(name):
    return json.loads((BASE / name).read_text())


def collect(document):
    """Find assigned records despite the independent auditors' envelope choices."""
    found = {}

    def visit(value):
        if isinstance(value, dict):
            if (isinstance(value.get("id"), str) and value["id"].startswith("A")
                    and all(key in value for key, _ in FIELDS)):
                found[value["id"]] = value
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(document)
    return found


def as_text(value):
    if isinstance(value, dict):
        return "<br>".join(f"**{key.replace('_', ' ')}:** {as_text(item)}" for key, item in value.items())
    if isinstance(value, list):
        return "<br>".join(as_text(item) for item in value)
    return str(value).replace("|", "&#124;").replace("\n", "<br>")


def source_link(source_id):
    filename = next(path.name for path in BASE.glob(source_id.split("-")[0] + "-*.md"))
    return f"[{source_id}]({BASE / filename})"


def record_table(record):
    lines = [f"### {record['id']}: {record['title']}", "",
             f"**Severity:** {record.get('severity', 'see source')}. "
             f"**Evidence:** {as_text(record.get('evidence_classification', 'see source'))}", ""]
    if record.get("uncertainty"):
        lines += [f"**Limits:** {as_text(record['uncertainty'])}", ""]
    lines += ["Sources: " + ", ".join(source_link(item) for item in record["source_ids"]) + ".", "",
              "| Field | Explanation |", "| --- | --- |"]
    for key, label in FIELDS:
        lines.append(f"| {label} | {as_text(record[key])} |")
    lines += [""]
    references = record.get("references", [])
    links = []
    for reference in references:
        if isinstance(reference, dict) and reference.get("path"):
            path = Path(reference["path"])
            line = reference.get("line")
            target = str(path) + (f":{line}" if line else "")
            links.append(f"[{reference.get('label', path.name)}]({target})")
        elif isinstance(reference, str) and reference.startswith("/home/chia/repos/"):
            match = re.fullmatch(r"(.+?)(?::(\d+)(?:[-–]\d+)?)?", reference)
            target = match.group(1)
            if match.group(2):
                target += ":" + match.group(2)
            links.append(f"[{Path(match.group(1)).name}]({target})")
    if links:
        lines += ["Primary references: " + "; ".join(dict.fromkeys(links)) + ".", ""]
    return lines


def main():
    reports = sorted(BASE.glob("A[1-8]-*.json"))
    if len(reports) != 8:
        raise SystemExit(f"Need eight finished assigned reports, found {len(reports)}")
    documents = {path.name.split("-")[0]: load(path.name) for path in reports}
    records = {}
    for document in documents.values():
        records.update(collect(document))

    def choose(identifier, source_ids, *, title=None, **changes):
        result = deepcopy(records[source_ids[0]])
        result.update(id=identifier, source_ids=source_ids)
        if title:
            result["title"] = title
        result.update(changes)
        missing = [key for key, _ in FIELDS if key not in result]
        if missing:
            raise ValueError(f"{identifier} lacks {missing}")
        return result

    # Editorial choices below are deliberately explicit and reproducible.
    defects = [
        choose("D01", ["A1-F1"]),
        choose("D02", ["A1-F2", "A2-F01"]),
        choose("D03", ["A2-F03"], proposed_correction=
               "Declare score-target scope and parent information needs together before launching the child. "
               "Give the existing parent-selected typed return a faithful association between each relevant credited score, "
               "insertion, trial, force model and requested/observed interval. Keep the winning eligible observation in "
               "machine bookkeeping. Reporting omission is a reporting defect: it must not itself reject actual work, "
               "decide eligibility, erase credit, or become a scientific acceptance gate. Scope eligibility must follow "
               "the independently declared target. Preserve the report boundary; do not inject raw child traces or audit identities."),
        choose("D04", ["A3-F1", "A6-F01"]),
        choose("D05", ["A3-F2"]),
    ]
    failure_ids = ["A5-F1", "A3-F3", "A5-F2"]
    failure = {"id": "D06", "title": "Failure feedback and deterministic recovery are incomplete across action, execution and report boundaries",
               "source_ids": failure_ids, "severity": "medium",
               "principles": sorted({p for item in failure_ids for p in records[item]["principles"]}),
               "evidence_classification": "Current-code conditional failure paths; none caused stopped007 to end",
               "uncertainty": "These related paths are consolidated as one recovery defect family. The observed007 termination was the user's interrupt, not one of these failures."}
    for key, _ in FIELDS:
        failure[key] = [{"case": item, "explanation": records[item][key]} for item in failure_ids]
    failure["proposed_correction"] = (
        "Use one phase-aware operational outcome/recovery path, with typed cause, affected field/reference, attempt relation "
        "and preserved-work state. A pre-acquisition invalid proposal receives changed planning feedback without a turn. "
        "A completed diagnostic remains an acquired observation. Unfinished execution must not be fabricated as a successful "
        "or zero-scored acquisition. A closed child's pending/failed report delivery must preserve completed evidence and "
        "the exact parent contract; a changed representation correction can reuse that work. Keep original invalid proposals "
        "for audit, but do not replay the identical cached invalid output as a meaningful retry. Unrecoverable failure must "
        "remain distinguishable from yield and success. Preserve legitimate type/reference/capability checks, without a "
        "scientific quality reviewer, hidden retry budget, raw-child channel or repeat simulation."
    )
    failure["references"] = [ref for item in failure_ids for ref in records[item].get("references", [])]
    defects.append(failure)
    defects += [choose("D07", ["A4-D1"]), choose("D08", ["A4-D2"]),
                choose("D09", ["A5-F3"]), choose("D10", ["A6-F02"])]

    # A7/A8 decisions are applied through this separately inspectable data file.
    editorial = load("consolidation-decisions.json")
    for item in editorial.get("additional_defects", []):
        defects.append(choose(**item))
    question_sources = [
        ["A6-Q01", "A2-Q01"], ["A2-Q04"], ["A2-Q02"], ["A1-Q1"], ["A1-Q2"],
        ["A2-Q03", "A7-Q1"], ["A3-Q1"], ["A4-Q1"], ["A6-Q02", "A4-Q2"], ["A4-Q3"],
        ["A5-Q1"], ["A5-Q2"],
    ]
    question_sources += editorial.get("additional_question_sources", [])
    questions = [choose(f"Q{index:02}", sources) for index, sources in enumerate(question_sources, 1)]
    for change in editorial.get("overrides", []):
        item = next(item for item in defects + questions if item["id"] == change["id"])
        item.update(change["values"])
    defects = [item for item in defects if item["id"] not in editorial.get("remove_defect_ids", [])]
    moves = set(editorial.get("move_defects_to_questions", []))
    for item in defects[:]:
        if item["id"] in moves:
            defects.remove(item)
            item["original_draft_id"] = item["id"]
            item["id"] = f"Q{len(questions) + 1:02}"
            questions.append(item)

    coverage = load("principle-coverage.json")
    working = load("working-mechanisms.json")
    stopped = load("STOPPED_STATE.json")
    verifier = load("prefix-verification.json")
    integrity = load("INTEGRITY.json")
    for item in defects + questions:
        for key, _ in FIELDS:
            if key not in item:
                raise ValueError(f"Missing {key} in {item['id']}")
    output = {
        "format": "orbital.method-loop-audit/v1", "date": "2026-10-18",
        "status": "audit_complete_workflow_paused_no_repairs", "head": stopped["repository_head"],
        "source_authority": "The user's conversation and latest25 principles; BRIEF is an index, project approval labels are not approval evidence.",
        "stopped_state": stopped, "audit_limits": editorial["audit_limits"],
        "accounting_verifier": {key: verifier[key] for key in ["status", "checks_performed", "complete", "discrepancies", "pending"]},
        "integrity": integrity, "auditor_reports": [str(path.relative_to(REPO)) for path in reports],
        "adjudication": editorial, "principle_coverage": coverage,
        "conclusion_groups": {GROUPS[0]: defects, GROUPS[1]: questions, GROUPS[2]: working},
    }
    (BASE / "AUDIT.json").write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")

    lines = ["# Orbital workflow method_loop audit — 2026-10-18", "",
             "**The workflow has verified integration defects and is not yet faithful to all of the requested principles.** "
             "The real method_loop and several structural boundaries work, but assigned scope, recorded credit and delivered "
             "scientific facts can disagree. This is an audit of the stopped prefix, not a repaired or completed workflow.", "",
             "The scientific workflow and its persistent goal remain **paused**. Eight focused specialist reviews were "
             "completed in waves, followed by primary-agent consolidation. No repairs, scientific workflow launches, "
             "calls through the workflow model connection, simulator calls, tool replays, estimator fits or tests were performed. "
             "Read-only file/array inspection and the existing accounting "
             "verifier were used. Every correction and verification below is proposed future work, not a claim it ran.", "",
             "The user instruction is authoritative. Both actual OpenChia and nano-graphrag method_loop designs were read; "
             "the executed binding imports OpenChia. Domain-specific template acceptance, optional bounds and a project's "
             "'approved' label do not authorize new orbital restrictions. Unresolved questions authorize no new gate.", "",
             "The frozen run has **402 committed local units**, **375 tool acquisitions**, **27 closed child Episodes "
             "(19 simulation, 7 simparts, 1 math)** and **20 root turns**. There are **227 distinct saved simulations**, "
             "acquired by 277 local sim.run actions, plus repeated/comparison playback appearances. All 27 child closures "
             "are yield stops. The root still had stop=false (upper 0.05910150506675524 > cost 0.02) when the user interrupted "
             "its next model decision. No completed root summary exists; task completion is unproven.", "",
             f"The [read-only verifier]({BASE / 'prefix-verification.json'}) performed **{verifier['checks_performed']:,}** "
             "accounting/shape checks with **zero discrepancies**, returning incomplete_prefix. It does not certify factual "
             "report meaning, scientific completion, fitter calibration or a fresh replay. A2 independently checked all 20 "
             "root projections against the implemented eligibility rule. The five observed scientific-integration defects "
             "D01–D05 therefore coexist with successful structural checks.", "",
             f"[Stopped baseline]({BASE / 'STOPPED_STATE.json'}) · [Unchanged-source/run evidence]({BASE / 'INTEGRITY.json'}) · "
             f"[Machine-readable full audit]({BASE / 'AUDIT.json'}) · [Adversarial adjudication]({BASE / 'A8-adversarial-integration.md'})", "",
             "The integrity comparison covers all 5,347 original non-bytecode run files and the 76 baseline working-tree files "
             "outside artifacts/audits/environments. The exact results are in INTEGRITY.json. Source/run files were preserved.", "",
             "| Review | Scope |", "| --- | --- |"]
    for code, scope in editorial["review_scopes"].items():
        filename = next(path.name for path in BASE.glob(code + "-*.md"))
        lines.append(f"| [{code}]({BASE / filename}) | {scope} |")
    lines += ["", "Coverage of the 25 requested principles:", "",
              "| # | Principle | Primary reviews and disposition |", "| --- | --- | --- |"]
    for row in coverage:
        lines.append(f"| {row['number']} | {row['principle']} | {row['disposition']} |")
    lines += ["", "The individual blocking-condition/default inventory is in "
              f"[A5]({BASE / 'A5-failures-config.md'}); the requirement-authority and removed-consumer ledger is in "
              f"[A7]({BASE / 'A7-authority-mechanisms.md'}). "
              "These distinguish legitimate type/reference/capability/numerical-domain boundaries from result-quality approval. "
              "No new scientific acceptance mechanism is recommended.", "", "## Verified defects", ""]
    for item in defects:
        lines += record_table(item)
    lines += ["## Unresolved questions", "",
              "These are limits in established policy or evidence. None authorizes an added restriction, silent default, "
              "scientific rejection or automatic workflow restart.", ""]
    for item in questions:
        lines += record_table(item)
    lines += ["## Mechanisms checked and working correctly", ""]
    for item in working:
        lines += [f"### {item['id']}: {item['title']}", "", item["result"], "",
                  "Evidence/limits: " + item["evidence_limits"], "",
                  "Sources: " + ", ".join(source_link(source) for source in item["source_ids"]) + ".", ""]
    (BASE / "AUDIT.md").write_text("\n".join(lines))
    print(json.dumps({"verified_defects": len(defects), "unresolved_questions": len(questions),
                      "checked_mechanisms": len(working), "report": str(BASE / "AUDIT.md")}))


if __name__ == "__main__":
    main()
