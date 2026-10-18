"""Adaptive scientific bindings; models propose, method_loop runs and controls."""

from dataclasses import asdict
import inspect
import json
from pathlib import Path
import tomllib
import uuid

from .artifacts import Artifacts
from .communication import generation_schema, parent_model_inputs, report_contract, report_field_examples, validate_report
from .credit import CreditController, Evidence, compact_evidence, evidence_key, identity, project_observation
from .durable import (CachedModels, CachedTools, DurableWorkflow, RunLock,
                      execution_identity, require_compatible_resume, save)
from .models import ModelConnection
from .persistence import PersistenceSettings
from .records import Observation, plain
from .runtime import CAPABILITIES, ChildAction, EpisodeBindings, EpisodeSpec, Kind, ToolAction
from .simulation import SimulationRequest, generate_forcing
from .smoke import environment


ACTION_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "action": {"type": "string", "enum": ["tool", "child"]},
        "label": {"type": "string"}, "rationale": {"type": "string"},
        "tool_name": {"type": "string"}, "arguments_json": {"type": "string"},
        "child_kind": {"type": "string"}, "objective": {"type": "string"},
        "child_assignment_json": {"type": "string"},
        "report_decision": {"type": "string"},
        "report_fields": {"type": "array", "items": {"type": "object",
            "properties": {"name": {"type": "string"}, "meaning": {"type": "string"},
                           "schema_json": {"type": "string"}},
            "required": ["name", "meaning", "schema_json"], "additionalProperties": False}},
    },
    "required": ["action", "label", "rationale", "tool_name", "arguments_json", "child_kind",
                 "objective", "child_assignment_json", "report_decision", "report_fields"],
}

INSTRUCTIONS = """You select one next scientific acquisition in an Episode.
Episodes exist to improve total credit. Pursue useful marginal improvement;
zero-yield evidence is retained. There are NO scientific acceptance gates, hidden
qualification thresholds, proof prerequisites, or successful/failed trajectories.
Do not decide when to stop. A numerical controller owns continuation.
Use only a declared tool or declared child Episode. Do not call native tools.
A tool executes its specified operation, not an adaptive search or hidden sweep.
Return exactly the structured action. For a tool, leave child fields empty and
report_fields []; arguments_json is a JSON object. For a child, leave tool_name
empty, arguments_json '{}', and supply its scientific objective, JSON assignment,
parent decision, and exact requested report field names/meanings/types. Every
report_fields item contains name, meaning, and schema_json: a JSON Schema object
serialized as JSON. This is a type declaration, not a returned child text field.
Parent reports allow numbers, integers, booleans, nulls, typed arrays and closed
objects. Every object declares properties, additionalProperties:false, and all
properties in required. Use nullable types for unknown values and typed empty
arrays for no observations. Strings are allowed as explicit enum/const codes,
or with format identifier, unit or mathematical_expression. Unrestricted strings,
open objects and untyped arrays are prohibited, including when nested. Field names
are identifiers; enums contain codes/names, not sentences. No prose summary slots.
See report_field_examples for exact typed field declarations. Choose the
information needed for your next decision; the examples are not mandatory fields.
Commission a smaller question with useful information to return; recursive simparts is allowed.
Choose further actions from measurements and child reports, not a fixed script.
Do not repeat identical calculations for credit. Numerical refinement can expose
discrepancies; it never qualifies/rejects science. Treat the knowledge score as
an initial coverage proxy, not truth or calibrated confidence. Distinguish a
reduced model from the complete model. Suggest full-model insertion velocities
using reference mathematics, matched term investigations, or measured local fits.
When the assigned main question is already characterized, investigate residual
uncertainty or the smallest useful refinement; do not claim success or invent data.
Only direct-child contracted reports are delivered to the parent. No audit IDs.
"""

TOOLS = {
    "sim.run": "JSON: {trial:1,vx:0,vy:1,a:0.15,sigma:0.03,end:125.66370614359172,terms:{central:true,modulation:true,rotating:true,forcing:true}}. Omitted fields use these defaults. Optional start,initial_state:[x,y,vx,vy],max_step:0.05,rtol:1e-7,atol:1e-9,sample_step:0.02,spatial_box:[xmin,xmax,ymin,ymax],radial_limits:[0.5,2]. trial selects stored forcing; keep trial fixed for matched comparisons. Continue at absolute time with saved terminal state. For original full-model persistence observe from start=0 to physical horizon or first radial exit. Scope smaller questions through simparts.",
    "sim.compare": "JSON {left:{...sim.run fields...},right:{...sim.run fields...}}. Two explicit matched observations. Same trial and insertion for numerical refinement or isolating force terms. Halve max_step and divide rtol/atol by ten for refinement; can also halve sample_step. No agreement threshold.",
    "math.symbolic": 'JSON {"operation":"central_conic"}. SymPy derives exact unit central-only conic relationships for initial position (1,0). These relationships do not describe the full driven field.',
    "math.numeric": 'JSON {"operation":"central_circular_reference","radius":1}, or {"operation":"central_candidate","vx":0,"vy":1}, or {"operation":"local_velocity_fit","points":[[vx,vy,measured_effective_duration],...]}. The fit reports rank and residual; it is one calculation, not an optimizer or a simulation sweep.',
    "math.lean": 'JSON {"source":"Lean source"}. Optional Lean diagnostics; if Lean is unavailable that is recorded. It is never a prerequisite. Lean does not assign knowledge credit in this initial binding.',
}


def load_settings(config_path):
    settings = tomllib.loads(config_path.read_text())
    settings["episodes"][Kind.ROOT]["weights"] = settings["credit"]["root"]["weights"]
    for kind in Kind:
        local = settings["episodes"][kind]
        weights = local["weights"]
        if set(weights) != {"orbital_persistence", "knowledge_gained"} or any(x < 0 for x in weights.values()) or abs(sum(weights.values()) - 1) > 1e-12:
            raise ValueError("Each Episode requires two nonnegative weights summing to one")
        if not 0 < local["forecast_memory"] < 1 or local["continuation_cost"] <= 0 or local["initial_predicted_gain"] <= 0:
            raise ValueError("Continuation settings require positive gains/cost and memory between zero and one")
    return settings


class ScientificBindings:
    def __init__(self, settings, models, tools):
        self.settings, self.models, self.tools = settings, models, tools
        self.controllers = {}
        self.forcing = {}

    def controller(self, path):
        controller = CreditController(self.settings, path[-1][0])
        self.controllers[path] = controller
        return controller

    def result(self, record):
        measurements, findings, artifacts = {}, [], []
        for unit in record.unit_records:
            evidence = unit.controller_input
            for item in evidence.measurements:
                measurements[evidence_key(item)] = plain(item)
            findings.extend(plain(evidence.findings))
            artifacts.extend(evidence.artifacts)
            if unit.episode_update:
                findings.append({"child_report": unit.episode_update.report.as_record()})
        return Evidence(tuple(measurements.values()), tuple(findings), tuple(dict.fromkeys(artifacts)))

    def bindings(self):
        return {kind: EpisodeBindings(self.controller,
            lambda observation, request: project_observation(observation, self.tools.store), self.result,
            self.release)
            for kind in Kind}

    def release(self, path):
        self.controllers.pop(path, None)
        if hasattr(self.models, "release"):
            return self.models.release("decide-" + identity(list(path)))

    def spec(self, kind, key, objective, assignment):
        return EpisodeSpec(kind, key, objective, Observation("assignment", assignment),
                           lambda request: Policy(self, kind, request))

    def simulation_arguments(self, arguments):
        args = dict(arguments)
        trial = args.pop("trial", 1)
        if trial not in self.forcing:
            self.forcing[trial] = generate_forcing(self.tools.store, trial, self.settings["study"]["horizon"])
        vx, vy = args.pop("vx", 0), args.pop("vy", 1)
        if "forcing_id" in args:
            raise ValueError("Select the forcing trial; workflow owns artifact references")
        args.setdefault("initial_state", [1, 0, vx, vy])
        args.setdefault("end", self.settings["study"]["horizon"])
        return asdict(SimulationRequest.from_record({"forcing_id": self.forcing[trial], **args}))

    def tool(self, response):
        name = response["tool_name"]
        args = json.loads(response["arguments_json"])
        if name == "sim.run":
            args = self.simulation_arguments(args)
        elif name == "sim.compare":
            args = {side: self.simulation_arguments(args[side]) for side in ("left", "right")}
        return ToolAction(response["label"], name, args)

    def child(self, response, view):
        kind = Kind(response["child_kind"])
        assignment = json.loads(response["child_assignment_json"])
        # The parent chooses findings to send, and declares exact report fields.
        spec = self.spec(kind, f"unit-{view.units_consumed:04d}-{kind.value}",
                         response["objective"], assignment)
        contract = report_contract(decision=response["report_decision"],
            measurements={"evidence": "Observed motion/recurrence, scoped mathematical relationships, discrepancies and limitations"},
            fields=response["report_fields"])

        def project(result, completion, request):
            # No child scalar credit crosses this boundary. Machine evidence
            # feeds the parent's ledger; model input receives contracted reports.
            return Evidence(tuple(compact_evidence(item) for item in result.measurements), (), result.artifacts)

        async def synthesize(result, completion, request):
            schema = generation_schema(contract.value_schema)
            report_id = "report-" + identity({"parent": list(view.path), "unit": view.units_consumed})
            try:
                report = await self.models.complete(report_id,
                    self.settings["models"]["routing"]["synthesize_report"],
                    "Compose the parent's requested typed report from supplied observations. Return exactly an instance of its value_schema. "
                    "Use numbers, typed records/arrays and declared string types. Strings may contain only declared codes, identifiers, "
                    "units or mathematical expressions, never paragraphs or prose summaries. Retain the requested scope and uncertainty "
                    "in typed fields. Use schema-permitted nulls, empty arrays or unknown codes for unobserved information. "
                    "No audit IDs, invented measurements, acceptance/rejection decisions, or serialized JSON inside report strings. "
                    "A yield stop is not scientific success.",
                    {"contract": contract.as_record(), "completion": completion.as_record(),
                     "observations": plain(result.findings)}, schema)
                validate_report(report, contract.value_schema)
                return report
            finally:
                if hasattr(self.models, "release"):
                    retirement = self.models.release(report_id)
                    if inspect.isawaitable(retirement):
                        await retirement

        return ChildAction(spec, contract, project, synthesize)


class Policy:
    def __init__(self, binding, kind, request):
        self.binding, self.kind, self.request = binding, kind, request

    async def next(self, view):
        binding = self.binding
        controller = binding.controllers[view.path]
        children = {Kind.ROOT: [Kind.MATH, Kind.SIMULATION], Kind.MATH: [Kind.PARTS],
                    Kind.SIMULATION: [Kind.PARTS], Kind.PARTS: [Kind.PARTS]}[self.kind]
        context = parent_model_inputs(view, {
            "episode_kind": self.kind.value, "objective": plain(view.goal.objective),
            "assignment": plain(self.request.message.findings),
            "fixed_problem": {"acceleration": "-(1+a*sin(0.7*t))*r/|r|^3 + 0.02*[[cos(0.4*t),sin(0.4*t)],[sin(0.4*t),-cos(0.4*t)]]*r + sigma*eta(t)",
                "forcing": "Stored AR(1) two-vector on 0.1 grid; rho=exp(-0.2); linear interpolation; same trial across matched cases",
                "initial_position": [1, 0], "spaceship_search_parameters": ["vx", "vy"],
                "study": binding.settings["study"], "radial_observation_region": [0.5, 2.0],
                "persistence": "q=exp(-phase-aligned squared position,velocity,relative-period mismatch); sum duration*q, first revolution reference",
                "persistence_scales": binding.settings["persistence"]},
            "available_tools": {name: TOOLS[name] for name in CAPABILITIES[self.kind]},
            "available_children": [kind.value for kind in children],
            "report_field_examples": report_field_examples(),
            "controller": view.controller_state.as_record(),
            "local_credit_history": controller.history,
            "own_tool_observations": plain(controller.own_observations),
        }, reports=view.child_reports)
        response = await binding.models.complete("decide-" + identity(list(view.path)),
            binding.settings["models"]["routing"]["decide"], INSTRUCTIONS, context, ACTION_SCHEMA)
        if response["action"] == "tool":
            return binding.tool(response)
        if response["action"] == "child":
            return binding.child(response, view)
        raise ValueError("The model must propose a declared acquisition, not stop")


async def run_scientific(directory: Path, config_path: Path, *, resume=False):
    if resume:
        config_path = directory / "study.toml"
        require_compatible_resume(directory, config_path.read_text())
    else:
        directory.mkdir(parents=True, exist_ok=False)
        (directory / "study.toml").write_text(config_path.read_text())
        settings = load_settings(config_path)
        provenance = environment(settings)
        provenance.update(execution="adaptive_scientific_run", scientific_credit="continuous-discovery-v1",
                          scientific_search_policy="live model proposals; numerical EWMA continuation")
        save(directory / "environment.json", provenance)
        save(directory / "manifest.json", {"run_id": "orbital_" + uuid.uuid4().hex,
            "restoration": "Replay cached decisions and acquisitions through fresh method_loop controllers; no restored totals added"})
        save(directory / "execution-identity.json", execution_identity(config_path.read_text()))
    settings = load_settings(config_path)
    manifest = json.loads((directory / "manifest.json").read_text())
    with RunLock(directory):
        attempts = directory / "model-attempts"
        attempts.mkdir(exist_ok=True)
        attempt = attempts / f"attempt-{len(list(attempts.iterdir())) + 1:03d}"
        async with ModelConnection(settings["models"], attempt, Path(__file__).resolve().parents[1]) as connection:
            models = CachedModels(connection, directory / "model-cache")
            tools = CachedTools(Artifacts(directory / "objects"), PersistenceSettings(**settings["persistence"]), directory / "tool-cache")
            binding = ScientificBindings(settings, models, tools)
            workflow = DurableWorkflow(binding.bindings(), tools, directory / "episodes")
            root = binding.spec(Kind.ROOT, "trajectory-search", "Find insertion velocities with longer quasi-stable recurrence and improve understanding of the fixed environment", {
                "initial_options": [
                    "Use mathematical_exploration for central conic guidance or a quantitative local model of measured trajectories.",
                    "Use simulation_investigation to measure a complete-model insertion and investigate its behavior.",
                    "Either branch can commission simparts to isolate a force term or a local disruption; simparts can commission a smaller simparts question."],
                "decision_policy": "Choose the next branch using expected scientific contribution and current uncertainty. There is no required branch order or mathematical prerequisite for simulation. Revisit branches as findings suggest; the numerical controller owns continuation.",
                "initial_reference_velocity": [0, 1], "suggested_initial_environment": {"a": .15, "sigma": .03},
                "credit": "Root weights persistence and knowledge equally; local Episode weights are separate. Every iteration pursues improved total credit. No gates.",
                "outputs": "Measured trajectory candidates, quantitative scoped findings, uncertainty and next investigative directions"})
            try:
                record, result = await workflow.run_async(root, manifest["run_id"])
            except BaseException as error:
                save(attempt / "workflow-error.json", {"error": type(error).__name__, "message": str(error),
                    "fresh_model_calls": models.fresh_calls, "replayed_model_calls": models.replayed_calls,
                    "fresh_tools": tools.fresh_calls, "replayed_tools": tools.replayed_calls})
                raise
            save(directory / "record.json", record.as_record())
            save(directory / "findings.json", result.as_record())
            summary = {"run_id": manifest["run_id"], "ended_by": record.ended_by,
                       "controller": record.controller_state.as_record(),
                       "record": str(directory.resolve() / "record.json")}
            save(directory / "summary.json", summary)
            save(attempt / "execution-summary.json", {"fresh_model_calls": models.fresh_calls,
                "replayed_model_calls": models.replayed_calls, "fresh_tools": tools.fresh_calls,
                "replayed_tools": tools.replayed_calls})
            return summary
