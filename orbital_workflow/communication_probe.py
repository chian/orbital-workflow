"""Live parent/report/parent round trip with labelled software fixtures only."""

import json
from pathlib import Path
from types import SimpleNamespace

from method_loop import EpisodeCompletion

from .artifacts import Artifacts
from .communication import parent_model_inputs, report_field_examples
from .credit import Evidence
from .durable import CachedModels, save
from .models import ModelConnection
from .scientific import ACTION_SCHEMA, INSTRUCTIONS, ScientificBindings, load_settings
from .tools import ToolDispatcher


async def probe_communication(config_path: Path, directory: Path):
    directory.mkdir(parents=True, exist_ok=False)
    settings = load_settings(config_path)
    (directory / "study.toml").write_text(config_path.read_text())
    fixture = {"software_fixture_only": True, "scientific_credit": None,
        "fixed_vy": 1.0,
        "samples": [{"vx": -.1, "effective_duration": 2.0},
                    {"vx": 0.0, "effective_duration": 5.0},
                    {"vx": .1, "effective_duration": 3.0}]}
    save(directory / "fixture.json", fixture)
    async with ModelConnection(settings["models"], directory / "transport", config_path.resolve().parent) as connection:
        models = CachedModels(connection, directory / "model-cache")
        binding = ScientificBindings(settings, models, ToolDispatcher(Artifacts(directory / "objects")))
        try:
            proposal = await models.complete("communication-probe-commission", "REASONING", INSTRUCTIONS,
                {"software_fixture_only": True,
                 "task": "Commission a simulation_investigation child solely to characterize this supplied software fixture. "
                    "No simulator will be run. You are defining the report fields you need to steer a later velocity query. "
                    "Request a numeric response curve, a declared trend code, and the best observed velocity. "
                    "Choose exact field names/types. Use at least one defined string type. Return a child action.",
                 "fixture": fixture, "available_children": ["simulation_investigation"],
                 "report_field_examples": report_field_examples()}, ACTION_SCHEMA)
            save(directory / "parent-commission.json", proposal)
            view = SimpleNamespace(path=(("spaceship_trajectory_search", "communication-fixture"),), units_consumed=0)
            action = binding.child(proposal, view)
            save(directory / "contract.json", action.report_contract.as_record())
            result = Evidence((), ({"operation": "software_fixture", "measurements": fixture},))
            reply = await action.synthesize_report(result, EpisodeCompletion("exhausted", "", 0), None)
            report = action.report_contract.admit(reply, audit_identifiers=())
            save(directory / "child-report.json", report.as_record())
            next_schema = {"type": "object", "additionalProperties": False,
                "required": ["next_velocity", "basis"], "properties": {
                    "next_velocity": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2},
                    "basis": {"type": "string", "enum": ["refine_observed_peak", "explore_unobserved_region"]}}}
            inputs = parent_model_inputs(SimpleNamespace(child_reports=(report,)), {
                "software_fixture_only": True,
                "task": "Choose one next velocity query from the typed child report. Return a data proposal only; it will not be simulated.",
            }, reports=(report,))
            decision = await models.complete("communication-probe-followup", "REASONING",
                "Use the supplied typed child findings to choose one next query. This is a software-only communication probe, "
                "not scientific evidence. Return only the requested typed fields; execute nothing.", inputs, next_schema)
            save(directory / "parent-followup-input.json", inputs)
            save(directory / "parent-followup.json", decision)
            summary = {"execution": "live_typed_communication_component_probe", "scientific_credit": None,
                "simulator_operations": 0, "live_model_calls": models.fresh_calls,
                "report_fields": list(report.values), "parent_followup": decision,
                "directory": str(directory.resolve())}
            save(directory / "summary.json", summary)
            return summary
        except BaseException as error:
            save(directory / "execution-error.json", {"error": type(error).__name__, "message": str(error),
                 "scientific_credit": None, "simulator_operations": 0})
            raise
