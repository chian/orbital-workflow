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
                      execution_identity, require_compatible_resume, save, snapshot_sources)
from .models import ModelConnection
from .persistence import PersistenceSettings
from .records import Observation, plain
from .runtime import CAPABILITIES, ChildAction, EpisodeBindings, EpisodeSpec, Kind, ToolAction
from .simulation import SimulationRequest, generate_forcing
from .gravity import GravitySystem, scenario_problem
from .score_yield import YieldParameters
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
When supplied measurements suffice for a scalar calculation, use math.arithmetic
locally if it is in available_tools. Calculate differences, ratios, convergence
orders and extrapolations directly; do not commission another child to repeat the
same arithmetic question with the same supplied data. Commission a simparts child
when a smaller simulation investigation will supply needed evidence. Arithmetic
is one local acquisition and does not invent a measured simulation score.
Choose further actions from measurements and child reports, not a fixed script.
Do not repeat identical calculations for credit. Numerical refinement can expose
discrepancies; it never qualifies/rejects science. A simulation returns its numerical
recurrence score. Each run is one turn; duration and solver steps are not exposure
counts for credit or yield. Credit assigns score improvements. Mathematical
calculations have no fabricated score bonus; use their guidance to obtain better
scored observations through simparts. Distinguish a
reduced model from the complete model. Suggest full-model insertion velocities
using reference mathematics, matched term investigations, or measured local fits.
When the assigned main question is already characterized, investigate residual
uncertainty or the smallest useful refinement; do not claim success or invent data.
Only direct-child contracted reports are delivered to the parent. No audit IDs.
"""

TOOLS = {
    "sim.run": "JSON: {trial:1,vx:0,vy:1,a:0.15,sigma:0.03,terms:{central:true,modulation:true,rotating:true,forcing:true}}. One completed integration returns its numerical score and this Episode's run_index. Scenario fixes masses/source motion and the physical observation window [0, study.horizon], also supplied as fixed_problem.observation_window. In simparts, active_bodies:['body_1'] isolates a force contribution while retaining source motion/collision surfaces; gravity_mode:'monopole' uses a barycentric approximation. Optional start,initial_state:[x,y,vx,vy],end,max_step:0.05,rtol:1e-7,atol:1e-9,sample_step:0.02,spatial_box,radial_limits. Require 0 <= start < end <= study.horizon, including for reduced models. Keep trial fixed for matched comparisons. Continue at absolute time with saved terminal state within this physical window. An outside-window request returns operation sim.request_diagnostic with code outside_observation_window, requested_interval and observation_window; no integration, score or run_index is produced. This feedback is a local acquisition; select another investigation from it. The physical window does not limit Episode turns.",
    "sim.compare": "JSON {left:1,right:2}. Compare two already-completed sim.run observations by their run_index in this Episode. This performs no integrations. First acquire each run separately, one run per turn. Keep trial and insertion fixed for numerical refinement or isolating terms. Returned run_indices.left and run_indices.right list every local run_index identifying each compared saved observation; repeated identical acquisitions can have multiple local indices. Persistent artifact references stay in audit storage. No agreement threshold.",
    "math.arithmetic": 'JSON {"expression":"(coarse-medium)/(medium-fine)","values":{"coarse":0.16618101298027446,"medium":0.1661407076470878,"fine":0.1661308271558801}}. Evaluate one bounded scalar expression from supplied finite measurements. Use +,-,*,/,**, unary signs, parentheses and declared math functions abs,sqrt,log,log2,log10,exp,sin,cos. Returns value (number or null), expression, inputs and diagnostic.code. Domain/division/overflow or expression diagnostics remain observations. Compute differences, ratios, log2 convergence orders and extrapolations locally when data suffice. No integration, adaptive search or additional score credit occurs.',
    "math.symbolic": 'JSON {"operation":"central_conic"}. SymPy derives exact unit central-only conic relationships for initial position (1,0). These relationships do not describe the full driven field.',
    "math.numeric": 'JSON {"operation":"central_circular_reference","radius":1}, {"operation":"central_candidate","vx":0,"vy":1}, {"operation":"binary_reference","time":0,"position":[1,0]}, or {"operation":"local_velocity_fit","points":[[vx,vy,measured_effective_duration],...]}. binary_reference calculates the scenario binary period, source states, individual attraction vectors, rotating-frame velocity and monopole circular-speed reference. Central conic tools describe the unit-mass monopole approximation, not the resolved binary. The fit reports rank and residual; it is one calculation, not an optimizer or simulation sweep. Numeric guidance itself has no additional credit bonus.',
    "math.lean": 'JSON {"source":"Lean source"}. Optional Lean diagnostics; if Lean is unavailable that is recorded. It is never a prerequisite. Lean does not assign knowledge credit in this initial binding.',
}


def load_settings(config_path):
    settings = tomllib.loads(config_path.read_text())
    settings["scenario"] = scenario_problem(settings)
    problem = settings["scenario"]
    SimulationRequest("configuration_only", scenario_id=problem["id"],
        initial_state=tuple(problem["initial_position"] + problem["reference_velocity"]),
        radial_limits=tuple(problem["radial_limits"]), gravity=GravitySystem.from_record(problem["gravity"]))
    for kind in Kind:
        local = settings["episodes"][kind]
        YieldParameters(**local["yield"])
        from numbers import Real
        import math
        cost = local["continuation_cost"]
        if isinstance(cost, bool) or not isinstance(cost, Real) or not math.isfinite(cost) or cost < 0:
            raise ValueError("Continuation cost must be finite and nonnegative")
    return settings


class ScientificBindings:
    def __init__(self, settings, models, tools):
        self.settings, self.models, self.tools = settings, models, tools
        self.problem = scenario_problem(settings)
        self.controllers = {}
        self.forcing = {}
        self.completed_runs = {}
        self.run_owners = {}

    def controller(self, path):
        projection = self.root_score if path[-1][0] == Kind.ROOT else None
        controller = CreditController(self.settings, path[-1][0], projection)
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
            self.project_tool, self.result,
            self.release)
            for kind in Kind}

    def release(self, path):
        self.controllers.pop(path, None)
        goal_id = self.run_owners.pop(path, None)
        if goal_id is not None:
            self.completed_runs.pop(goal_id, None)
        if hasattr(self.models, "release"):
            return self.models.release("decide-" + identity(list(path)))

    def spec(self, kind, key, objective, assignment):
        return EpisodeSpec(kind, key, objective, Observation("assignment", assignment),
                           lambda request: Policy(self, kind, request))

    def simulation_arguments(self, arguments):
        args = dict(arguments)
        window = [0.0, float(self.settings["study"]["horizon"])]
        if "observation_window" in args and plain(args["observation_window"]) != window:
            raise ValueError("The study fixes the physical observation window")
        args["observation_window"] = window
        for key, expected in (("gravity", self.problem["gravity"]), ("scenario_id", self.problem["id"])):
            if key in args and json.dumps(args[key], sort_keys=True) != json.dumps(expected, sort_keys=True):
                raise ValueError("The scenario fixes attractor masses, orbits and identity")
            args[key] = expected
        trial = args.pop("trial", 1)
        if trial not in self.forcing:
            self.forcing[trial] = generate_forcing(self.tools.store, trial, self.settings["study"]["horizon"])
        vx, vy = args.pop("vx", 0), args.pop("vy", 1)
        if "forcing_id" in args:
            raise ValueError("Select the forcing trial; workflow owns artifact references")
        args.setdefault("initial_state", [*self.problem["initial_position"], vx, vy])
        args.setdefault("radial_limits", self.problem["radial_limits"])
        args.setdefault("end", self.settings["study"]["horizon"])
        return asdict(SimulationRequest.from_record({"forcing_id": self.forcing[trial], **args}))

    def full_problem(self, args):
        gravity = GravitySystem.from_record(args["gravity"])
        active = args.get("active_bodies")
        return (args["a"] in self.settings["study"]["a"]
            and args["sigma"] in self.settings["study"]["sigma"]
            and all(args["terms"].values()) and args.get("gravity_mode", "resolved") == "resolved"
            and (active is None or sorted(active) == sorted(gravity.body_ids))
            and args["spatial_box"] is None and list(args["radial_limits"]) == self.problem["radial_limits"]
            and identity(args["gravity"]) == identity(self.problem["gravity"])
            and args["scenario_id"] == self.problem["id"]
            and (args["start"] > 0 or list(args["initial_state"][:2]) == self.problem["initial_position"]))

    def root_score(self, item):
        if item["type"] != "trajectory":
            return None
        args = item["physical"]
        if (self.full_problem(args) and args["start"] == 0
                and list(args["initial_state"][:2]) == self.problem["initial_position"]):
            return item["measurement"]["score"]
        return None

    def project_tool(self, observation, request):
        evidence = project_observation(observation, self.tools.store)
        if observation.operation == "sim.compare":
            # The comparison's saved artifact references are audit identities.
            # Models use this Episode's run indices, including repeated aliases.
            # Identical evidence may also have been acquired by a child; keep
            # the audit-identity guard intact instead of whitelisting overlaps.
            runs = self.completed_runs.get(request.goal.goal_id, ())
            measurements = plain(observation.findings)
            references = measurements.pop("observation_references")
            measurements["run_indices"] = {side: [index + 1 for index, ref in enumerate(runs)
                                                  if ref == references[side]]
                                           for side in ("left", "right")}
            findings = ({"operation": observation.operation, "measurements": measurements},)
            return Evidence(evidence.measurements, findings, evidence.artifacts)
        if observation.operation != "sim.run":
            return evidence
        runs = self.completed_runs.setdefault(request.goal.goal_id, [])
        runs.append(observation.artifacts[-1])
        findings = ({"operation": observation.operation, "run_index": len(runs),
                     "measurements": plain(observation.findings)},)
        return Evidence(evidence.measurements, findings, evidence.artifacts)

    def tool(self, response, *, kind, request):
        name = response["tool_name"]
        args = json.loads(response["arguments_json"])
        if name == "sim.run":
            args = self.simulation_arguments(args)
            if kind == Kind.SIMULATION and not self.full_problem(args):
                raise ValueError("Reduced force/source/environment/spatial requests belong to an explicit simparts child capability")
        elif name == "sim.compare":
            runs = self.completed_runs.get(request.goal.goal_id, ())
            if set(args) != {"left", "right"} or any(type(args[side]) is not int or not 1 <= args[side] <= len(runs) for side in ("left", "right")):
                raise ValueError("Compare identifies two completed observations by this Episode's run_index")
            args = {side: runs[args[side] - 1] for side in ("left", "right")}
        elif name == "math.numeric" and args.get("operation") == "binary_reference":
            args["gravity"] = self.problem["gravity"]
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
            # feeds the parent's score assignment; models receive contracted reports.
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
                    {"objective": plain(request.goal.objective),
                     "task_context": plain(request.goal.task_context),
                     "assignment": plain(request.message.findings),
                     "contract": contract.as_record(), "completion": completion.as_record(),
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
        binding.run_owners[view.path] = self.request.goal.goal_id
        children = {Kind.ROOT: [Kind.MATH, Kind.SIMULATION], Kind.MATH: [Kind.PARTS],
                    Kind.SIMULATION: [Kind.PARTS], Kind.PARTS: [Kind.PARTS]}[self.kind]
        context = parent_model_inputs(view, {
            "episode_kind": self.kind.value, "objective": plain(view.goal.objective),
            "task_context": plain(view.goal.task_context),
            "assignment": plain(self.request.message.findings),
            "parent_report_contract": (self.request.report_contract.as_record()
                                       if self.request.report_contract is not None else None),
            "fixed_problem": {"acceleration": "-(1+a*sin(0.7*t))*sum_i(M_i*(r-R_i(t))/|r-R_i(t)|^3) + 0.02*[[cos(0.4*t),sin(0.4*t)],[sin(0.4*t),-cos(0.4*t)]]*r + sigma*eta(t)",
                "scenario": binding.problem,
                "source_motion": "Single source is fixed at origin. Circular-binary primaries follow their exact mutual Newtonian circular orbit about their barycenter; angular speed sqrt(total_mass/separation^3). The ship is a test particle with no backreaction. Modulation and external rotating/random terms act on the ship, not on source orbits.",
                "forcing": "Stored AR(1) two-vector on 0.1 grid; rho=exp(-0.2); linear interpolation; same trial across matched cases",
                "initial_position": binding.problem["initial_position"], "spaceship_search_parameters": ["vx", "vy"],
                "study": binding.settings["study"], "radial_observation_region": binding.problem["radial_limits"],
                "observation_window": [0.0, float(binding.settings["study"]["horizon"])],
                "outcomes": "Horizon, barycentric radial exit, scoped region exit, or collision with an attractor surface. These are observations, not scientific acceptance decisions.",
                "persistence": "q=exp(-phase-aligned squared position,velocity,relative-period mismatch); sum duration*q, first revolution reference",
                "persistence_reference": "Inertial angles and states about the origin/barycenter. This unchanged winding metric can miss planet-relative or non-winding cycles; no path novelty bonus is currently assigned.",
                "persistence_scales": binding.settings["persistence"]},
            "available_tools": {name: TOOLS[name] + (
                " This simulation_investigation capability uses the complete scenario and a/sigma from the declared study cases. Commission simparts for any force/source/environment/spatial reduction."
                if self.kind == Kind.SIMULATION and name == "sim.run" else "") for name in CAPABILITIES[self.kind]},
            "available_children": [kind.value for kind in children],
            "report_field_examples": report_field_examples(),
            "controller": view.controller_state.as_record(),
            "local_credit_history": controller.history,
            "own_tool_observations": plain(controller.own_observations),
        }, reports=view.child_reports)
        response = await binding.models.complete("decide-" + identity(list(view.path)),
            binding.settings["models"]["routing"]["decide"], INSTRUCTIONS, context, ACTION_SCHEMA)
        if response["action"] == "tool":
            return binding.tool(response, kind=self.kind, request=self.request)
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
        provenance.update(execution="adaptive_scientific_run", scientific_credit="scored-turn-v1",
                          scientific_search_policy="live proposals; template-derived score yield and upper-bound continuation")
        save(directory / "environment.json", provenance)
        save(directory / "scenario.json", settings["scenario"])
        save(directory / "manifest.json", {"run_id": "orbital_" + uuid.uuid4().hex,
            "scenario_id": settings["scenario"]["id"],
            "restoration": "Replay cached decisions and acquisitions through fresh method_loop controllers; no restored totals added"})
        save(directory / "execution-identity.json", execution_identity(config_path.read_text()))
        snapshot_sources(directory)
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
                    "Use mathematical_exploration for scoped monopole/conic guidance, binary reference calculations, or a quantitative local model of measured trajectories.",
                    "Use simulation_investigation to measure a complete-model insertion and investigate its behavior.",
                    "Either branch can commission simparts to isolate a force term or a local disruption; simparts can commission a smaller simparts question."],
                "decision_policy": "Choose the next branch using expected scientific contribution and current uncertainty. There is no required branch order or mathematical prerequisite for simulation. Revisit branches as findings suggest; the numerical controller owns continuation.",
                "scenario": binding.problem,
                "initial_reference_velocity": binding.problem["reference_velocity"], "suggested_initial_environment": {"a": binding.problem["suggested_a"], "sigma": binding.problem["suggested_sigma"]},
                "credit": "The simulator returns the agreed recurrence score. Parent credit is recomputed from scored observations on its own complete-scenario target, never child totals. Every iteration pursues improved credit; no artificial knowledge proxy or gates.",
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
