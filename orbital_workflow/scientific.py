"""Adaptive scientific bindings; models propose, method_loop runs and controls."""

import json
from pathlib import Path
import tomllib
import uuid

from .artifacts import Artifacts
from .boundary_validation import ModelOutputError, parse_json_object
from .communication import (ReportBoundaryError, completed_model_inputs, generation_schema,
    parent_model_inputs, report_contract, report_field_examples, validate_report)
from .credit import CreditController, CreditTarget, Evidence, ReportedEvidence, compact_evidence, evidence_key, identity, project_observation
from .durable import (CachedModels, CachedTools, DurableWorkflow, RunLock,
                      execution_identity, require_compatible_resume, save, snapshot_sources)
from .models import ModelConnection
from .persistence import PersistenceSettings
from .records import Observation, plain
from .runtime import CAPABILITIES, CHILD_CAPABILITIES, ChildAction, EpisodeBindings, EpisodeSpec, Kind, ToolAction
from .scenario import ScenarioSimulator, is_base_observation
from .report_facts import model_measurements, project_fields
from .failures import ActionRequestError, TOOL_NAMES, normalize_failure
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
                           "schema_json": {"type": "string"}, "binding_json": {"type": "string"}},
            "required": ["name", "meaning", "schema_json", "binding_json"], "additionalProperties": False}},
    },
    "required": ["action", "label", "rationale", "tool_name", "arguments_json", "child_kind",
                 "objective", "child_assignment_json", "report_decision", "report_fields"],
}

INSTRUCTIONS = """You are the scientific reasoning component of one Episode.
The host supplies mode 'action' while acquiring work, or mode 'form' after the
numerical loop has ended. In action mode select one next scientific acquisition.
In form mode fill exactly the requested interpretation fields using recorded
observations, admitted child reports and already filled factual form fields.
Return only the form's supplied output schema; do not propose an action or stop.
Filling this final form is communication, not an acquisition or yield observation.
Episodes exist to improve total credit. Pursue useful marginal improvement;
zero-yield evidence is retained. There are NO scientific acceptance gates, hidden
qualification thresholds, proof prerequisites, or successful/failed trajectories.
Do not decide when to stop. A numerical controller owns continuation.
Use only a declared tool or declared child Episode. Do not call native tools.
A tool executes its specified operation, not an adaptive search or hidden sweep.
In action mode return exactly the structured action. For a tool, leave child fields empty and
report_fields []; arguments_json encodes a strict JSON object. Numeric values
must be literal JSON numbers; put calculations in the math.arithmetic expression
string with separately supplied numeric inputs. Do not put unevaluated arithmetic
in JSON numeric slots. If action_request_diagnostic is supplied, propose a new
well-formed action using its field and parser location. That earlier proposal
was not executed and created no acquisition, score or controller turn.
For a child, leave tool_name
empty, arguments_json '{}', and supply its scientific objective, JSON assignment,
parent decision, and exact requested report field names/meanings/types. Every
child assignment must explicitly set credit_target to "parent" when it pursues
the current credit target, or "new" for a genuinely different scientific target.
A new objective label, path or wording alone does not make a different target.
You own this target declaration; choose "parent" when the target is the same.
Reusing the parent's target inherits its recorded best eligible score: acquiring the
same saved run earns zero new gain, and a higher score earns only the difference.
Inherited progress is prior knowledge, not a completed child acquisition. A new
target keeps its own credit scheme and can use the same evidence independently.
Objective wording, names and reference_score never set a numerical baseline.
Every report_fields item contains name, meaning, schema_json and binding_json. schema_json is a JSON Schema object
serialized as JSON. This is a type declaration, not a returned child text field.
binding_json is '{}' for your child's interpretation, or an explicit recorded
binding. Recorded bindings use scope 'returned_trajectories', select 'all',
'max_score', 'parent_target_all' or 'parent_target_best', and either value naming
one source or fields mapping your object properties to exact sources. Supported
sources are observation_index, initial_state, velocity, vx, vy, score,
requested_interval, observed_interval, outcome, experiment, experiment_kind,
experiment_operations, term_mask, active_bodies, gravity_mode, spatial_box,
radial_limits and refinement. Derived-operation sources contain only actual
explicitly selected experiment changes; absent changes are null. An 'all' selection
returns an array; a maximum returns one value/record or null. Source indices are
scoped to this returned contribution, never forcing trials or global run IDs.
Bound facts and associated best velocity/score come from the same actual saved
observation; arbitrary field names or prose never choose their source. Use
nullable maxima and typed empty arrays for absent observations.
Whenever a child can contribute to your score target, request its
parent_target_best observation with velocity, score and requested/observed
intervals, as shown in report_field_examples. This identifies the work supplying
your numerical gain, including work from deeper descendants. You choose the
field name and exact form before launch; no extra fields are injected afterward.
Do not pass scenario physics, forcing trials, solver configuration or their
ownership through child assignments or forms. The scenario host owns them.
Ordinary sim.run selects only spaceship vx and vy. Explicit simparts experiments
use the scenario host's derived-operation interface; they never replace base
physics or supply a different forcing realization.
Parent reports allow numbers, integers, booleans, nulls, typed arrays and closed
objects. Every object declares properties, additionalProperties:false, and all
properties in required. Use nullable types for unknown values and typed empty
arrays for no observations. Strings are allowed as explicit enum/const codes,
or with format identifier, unit or mathematical_expression. Unrestricted strings,
open objects and untyped arrays are prohibited, including when nested. Field names
are identifiers; enums contain codes/names, not sentences. No prose summary slots.
See report_field_examples for exact typed field declarations. Choose the
information needed for your next decision; the examples are not mandatory fields.
Commission an iterative sub-investigation with its own scientific question and
numerical controller; recursive simparts is allowed. The parent assigns the
question and the child chooses successive observations, comparisons, refinements
and subdivisions that investigate it. Do not assign a child a fixed one-operation
task. Use a declared local tool for a single specified experiment or calculation
when that capability is available. Reduced work outside the local capability
belongs to an iterative simparts investigation, not a one-run child assignment.
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
using reference mathematics, matched term investigations, or measured local fits
when full-model velocity search belongs to the assigned investigation.
When the assigned main question is already characterized, investigate residual
uncertainty or the smallest useful refinement within that same investigation.
Completing an experiment, characterizing a question or filling the parent's
report form does not end an Episode. Scientific continuation belongs only to its
numerical controller's yield estimate; do not invent a completion or scope
exhaustion stop. Do not claim success or invent data.
Only direct-child contracted reports are delivered to the parent. No audit IDs.
"""

TOOLS = {
    "sim.run": "Ordinary JSON {vx:0,vy:1}: one specified spaceship insertion in the fixed scenario. Physics, forcing, observation interval, boundaries and numerical defaults are bound by the scenario host. Never send trial, forcing_id, a, sigma, gravity, initial_state or solver controls as ordinary arguments. In simparts only, an explicit experiment selects derived term/source/region/interval/refinement operations from fixed_problem.interface. Continuation uses experiment.continuation.run_index and end, taking its state from that saved observation. Each completed integration supplies one score and this Episode's run_index; neither solver steps nor duration count as extra acquisitions.",
    "sim.compare": "JSON {left:1,right:2}. Compare two already-completed sim.run observations by their run_index in this Episode. This performs no integrations. First acquire each run separately, one run per turn. Keep insertion fixed for numerical refinement or isolating terms; scenario forcing is fixed automatically. Returned run_indices.left and run_indices.right list every local run_index identifying each compared saved observation; repeated identical acquisitions can have multiple local indices. Persistent artifact references stay in audit storage. No agreement threshold.",
    "math.arithmetic": 'JSON {"expression":"(coarse-medium)/(medium-fine)","values":{"coarse":0.16618101298027446,"medium":0.1661407076470878,"fine":0.1661308271558801}}. Evaluate one bounded scalar expression from supplied finite measurements. Use +,-,*,/,**, unary signs, parentheses and declared math functions abs,sqrt,log,log2,log10,exp,sin,cos. Returns value (number or null), expression, inputs and diagnostic.code. Domain/division/overflow or expression diagnostics remain observations. Compute differences, ratios, log2 convergence orders and extrapolations locally when data suffice. No integration, adaptive search or additional score credit occurs.',
    "math.symbolic": 'JSON {"operation":"central_conic"}. SymPy derives exact unit central-only conic relationships for initial position (1,0). These relationships do not describe the full driven field.',
    "math.numeric": 'JSON {"operation":"central_circular_reference","radius":1}, {"operation":"central_candidate","vx":0,"vy":1}, {"operation":"binary_reference","time":0,"position":[1,0]}, or {"operation":"local_velocity_fit","points":[[vx,vy,measured_effective_duration],...]}. binary_reference calculates the scenario binary period, source states, individual attraction vectors, rotating-frame velocity and monopole circular-speed reference. Central conic tools describe the unit-mass monopole approximation, not the resolved binary. The fit reports rank and residual; it is one calculation, not an optimizer or simulation sweep. Numeric guidance itself has no additional credit bonus.',
    "math.lean": 'JSON {"source":"Lean source"}. Optional Lean diagnostics; if Lean is unavailable that is recorded. It is never a prerequisite. Lean does not assign knowledge credit in this initial binding.',
}


def _action_json_diagnostic(response, error, proposal_index):
    """Locate an encoded planning-field error without exposing raw payloads.

    Only action construction uses this feedback. Model output, scientific tools
    and upward reports retain their existing error and communication boundaries.
    """
    candidates = []
    if response["action"] == "tool":
        candidates.append(("arguments_json", None, response["arguments_json"]))
    elif response["action"] == "child":
        candidates.append(("child_assignment_json", None, response["child_assignment_json"]))
        candidates.extend(("report_fields.schema_json", index, field["schema_json"])
                          for index, field in enumerate(response["report_fields"]))
        candidates.extend(("report_fields.binding_json", index, field.get("binding_json", "{}"))
                          for index, field in enumerate(response["report_fields"]))
    for field, index, raw in candidates:
        if raw == error.raw_response:
            details = error.diagnostic
            return {"code": "invalid_json", "category": details["category"],
                    "field": field, "index": index,
                    "line": details.get("line"), "column": details.get("column"),
                    "position": details.get("position"), "proposal_index": proposal_index}
    return None


def _validate_child_assignment(assignment, kind):
    """Reject configuration roles without interpreting scientific findings."""
    fixed = {"a", "sigma", "trial", "forcing_id", "forcing_seed", "forcing_grid_step",
        "forcing_ar_decay", "modulation_frequency", "rotating_amplitude", "rotating_frequency",
        "gravity", "scenario", "scenario_id", "study", "physics", "forcing", "numerics",
        "persistence", "observation_window", "initial_position", "method", "max_step", "rtol",
        "atol", "sample_step", "start", "end", "radial_limits", "spatial_box", "terms",
        "active_bodies", "gravity_mode"}
    conflict = sorted(set(assignment) & fixed)
    if conflict:
        raise ActionRequestError(field="child_assignment_json." + conflict[0])
    containers = {"scenario", "study", "physics", "forcing", "numerics", "persistence",
                  "config", "configuration", "simulation_request"}

    def inspect(value):
        if isinstance(value, dict):
            # A complete engine request remains private even inside another
            # envelope. Ordinary measured rows and interpretation are allowed.
            if {"forcing_id", "initial_state"} <= set(value):
                raise ActionRequestError(field="child_assignment_json")
            for key, item in value.items():
                if key in containers and isinstance(item, dict) and set(item) & fixed:
                    raise ActionRequestError(field="child_assignment_json." + key)
                if key == "experiment" and isinstance(item, dict):
                    allowed = {"terms", "active_bodies", "gravity_mode", "spatial_box", "radial_limits",
                               "interval", "refinement", "continuation"}
                    if kind != Kind.PARTS or set(item) - allowed:
                        raise ActionRequestError(field="child_assignment_json.experiment")
                    subfields = {"refinement": {"method", "max_step", "rtol", "atol", "sample_step"},
                        "terms": {"central", "modulation", "rotating", "forcing"},
                        "continuation": {"run_index", "end"}}
                    if any(name in item and (not isinstance(item[name], dict) or set(item[name]) - permitted)
                           for name, permitted in subfields.items()):
                        raise ActionRequestError(field="child_assignment_json.experiment")
                    # Explicit derived-operation coordinates/refinements remain
                    # permitted; they never override scenario forcing/physics.
                    continue
                inspect(item)
        elif isinstance(value, list):
            for item in value:
                inspect(item)
    inspect(assignment)


def load_settings(config_path):
    settings = tomllib.loads(config_path.read_text())
    ScenarioSimulator(settings, None)
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
        self.simulator = ScenarioSimulator(settings, getattr(tools, "store", None))
        self.problem = plain(self.simulator.problem)
        self.controllers = {}
        self.completed_runs = {}
        self.run_owners = {}
        self.controller_assignments = {}

    def prepare_controller(self, path, request):
        """Bind a target before the real method_loop opens its controller."""
        relation = request.message.findings.get("credit_target", "new" if len(path) == 1 else None)
        if relation not in ("parent", "new"):
            raise ValueError("credit_target must be 'parent' or 'new'")
        inherited = None
        if relation == "parent":
            if len(path) == 1:
                raise ValueError("A root credit target has no parent")
            parent = self.controllers[path[:-1]]
            target = parent.assignment.target
            inherited = parent.assignment.inheritance()
        else:
            projection = "complete_scenario" if path[-1][0] in (Kind.ROOT, Kind.SIMULATION) else "acquired_trajectories"
            target = CreditTarget("target_" + identity({"path": list(path),
                "goal": request.goal.goal_id, "scenario": self.problem, "projection": projection}), projection)
        self.controller_assignments[path] = (target, inherited, relation)

    def controller(self, path):
        target, inherited, relationship = self.controller_assignments.pop(path)
        complete = target.projection == "complete_scenario"
        projection = self.root_score if complete else None
        controller = CreditController(self.settings, path[-1][0], projection,
            target=target, inherited=inherited, path=path, target_relationship=relationship)
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
        evidence = Evidence(tuple(measurements.values()), tuple(findings), tuple(dict.fromkeys(artifacts)))
        contract = record.request.report_contract
        if contract is None:
            return evidence
        parent = self.controllers.get(record.path[:-1])
        projection = parent.assignment.score_projection if parent is not None else None
        try:
            values = project_fields(contract.fact_bindings, evidence.measurements, self.tools.store, projection)
            bound_properties = {name: plain(contract.value_schema["properties"][name]) for name in values}
            validate_report(values, {"type": "object", "additionalProperties": False,
                "properties": bound_properties, "required": list(bound_properties)})
        except (ValueError, KeyError, OSError) as error:
            failure = error if isinstance(error, ReportBoundaryError) else ReportBoundaryError(
                "The recorded factual source could not be projected", code="recorded_source")
            failure.closed_result = evidence
            if failure is error:
                raise
            raise failure from error
        schema = contract.interpretation_schema()
        if not schema["properties"]:
            validate_report(values, contract.value_schema)
            return ReportedEvidence(evidence.measurements, evidence.findings, evidence.artifacts, values)
        if self.models is None:
            # Finite diagnostic sources may supply their own report callback.
            return evidence
        return self._finish_form(record, evidence, values, schema)

    async def _finish_form(self, record, evidence, values, schema):
        """Child-owned final reasoning in its existing conversation, after work."""
        controller = self.controllers[record.path]
        declared_inputs = {
            "mode": "form", "episode_kind": record.scope_level,
            "objective": plain(record.goal.objective), "task_context": plain(record.goal.task_context),
            "assignment": plain(record.request.message.findings),
            "parent_report_contract": record.request.report_contract.as_record(),
            "completion": {"ended_by": record.ended_by, "end_reason": record.end_reason,
                           "units_consumed": record.units_consumed},
            "controller": controller.model_state(), "local_credit_history": controller.history,
            "own_tool_observations": plain(controller.own_observations),
            "recorded_form_values": values,
        }
        diagnostic, attempt = None, 0
        identifiers = tuple(dict.fromkeys((record.episode_id, record.goal.goal_id,
            *record.request.message.audit_identifiers(), *evidence.audit_identifiers())))
        while True:
            inputs = completed_model_inputs(record, {**declared_inputs, "form_attempt": attempt,
                **({"form_diagnostic": diagnostic} if diagnostic is not None else {})})
            try:
                interpretation = await self.models.complete("decide-" + identity(list(record.path)),
                    self.settings["models"]["routing"]["decide"], INSTRUCTIONS, inputs, generation_schema(schema))
                validate_report(interpretation, schema)
                completed = {**values, **interpretation}
                validate_report(completed, record.request.report_contract.value_schema)
                try:
                    record.request.report_contract.admit(completed, audit_identifiers=identifiers)
                except ReportBoundaryError:
                    raise
                except ValueError as error:
                    raise ReportBoundaryError(str(error), code="audit_identity") from error
                return ReportedEvidence(evidence.measurements, evidence.findings, evidence.artifacts, completed)
            except ReportBoundaryError as error:
                diagnostic = error.diagnostic
            except ModelOutputError as error:
                diagnostic = {"category": "report_format", "code": error.diagnostic["category"], "field": None}
            attempt += 1

    def bindings(self):
        return {kind: EpisodeBindings(self.controller,
            self.project_tool, self.result,
            self.release, self.prepare_controller)
            for kind in Kind}

    def release(self, path):
        self.controllers.pop(path, None)
        self.controller_assignments.pop(path, None)
        goal_id = self.run_owners.pop(path, None)
        if goal_id is not None:
            self.completed_runs.pop(goal_id, None)
        if hasattr(self.models, "release"):
            return self.models.release("decide-" + identity(list(path)))

    def spec(self, kind, key, objective, assignment):
        return EpisodeSpec(kind, key, objective, Observation("assignment", assignment),
                           lambda request: Policy(self, kind, request))

    def simulation_arguments(self, arguments, *, parts=False, request=None):
        def saved_run(index):
            runs = self.completed_runs.get(request.goal.goal_id, ()) if request is not None else ()
            if type(index) is not int or not 1 <= index <= len(runs):
                raise ActionRequestError(tool="sim.run", field="experiment.continuation.run_index")
            return self.tools.store.json(runs[index - 1])
        return self.simulator.resolve_run(arguments, parts=parts, continuation_lookup=saved_run)

    def full_problem(self, args):
        return is_base_observation(args, self.problem)

    def root_score(self, item):
        if item["type"] != "trajectory":
            return None
        args = plain(item["physical"])
        interval = item["measurement"].get("requested_interval")
        if not isinstance(interval, (tuple, list)) or len(interval) != 2:
            return None
        args.update(start=interval[0], end=interval[1],
                    observation_window=plain(item["measurement"].get("observation_window")))
        if is_base_observation(args, self.problem,
                               forcing_seed=item.get("executed_forcing_seed", args.get("forcing_seed"))):
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
            for side in ("left", "right"):
                measurements[side] = model_measurements(measurements[side])
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
                     "measurements": model_measurements(observation.findings)},)
        return Evidence(evidence.measurements, findings, evidence.artifacts)

    def tool(self, response, *, kind, request):
        name = response["tool_name"]
        if name not in CAPABILITIES[kind]:
            raise ActionRequestError("wrong_command", tool=name if name in TOOL_NAMES else None, field="tool_name")
        args = parse_json_object(response["arguments_json"])
        if name == "sim.run":
            args = self.simulation_arguments(args, parts=kind == Kind.PARTS, request=request)
        elif name == "sim.compare":
            runs = self.completed_runs.get(request.goal.goal_id, ())
            if set(args) != {"left", "right"} or any(type(args[side]) is not int or not 1 <= args[side] <= len(runs) for side in ("left", "right")):
                raise ActionRequestError(tool=name, field="run_index")
            args = {side: runs[args[side] - 1] for side in ("left", "right")}
        elif name == "math.numeric":
            args = self.simulator.resolve_numeric(args)
        return ToolAction(response["label"], name, args)

    def child(self, response, view):
        try:
            kind = Kind(response["child_kind"])
        except ValueError as error:
            raise ActionRequestError("wrong_command", field="child_kind") from error
        if kind not in CHILD_CAPABILITIES[Kind(view.path[-1][0])]:
            raise ActionRequestError("wrong_command", field="child_kind")
        assignment = parse_json_object(response["child_assignment_json"])
        if assignment.get("credit_target") not in ("parent", "new"):
            raise ActionRequestError(field="credit_target")
        _validate_child_assignment(assignment, kind)
        # The parent chooses findings to send, and declares exact report fields.
        spec = self.spec(kind, f"unit-{view.units_consumed:04d}-{kind.value}",
                         response["objective"], assignment)
        try:
            contract = report_contract(decision=response["report_decision"],
                measurements={"evidence": "Observed motion/recurrence, scoped mathematical relationships, discrepancies and limitations"},
                fields=response["report_fields"])
        except ReportBoundaryError as error:
            raise ActionRequestError(field="report_fields") from error

        def project(result, completion, request):
            # No child scalar credit crosses this boundary. Machine evidence
            # feeds the parent's score assignment; models receive contracted reports.
            return Evidence(tuple(compact_evidence(item) for item in result.measurements), (), result.artifacts)

        def synthesize(result, completion, request):
            if not isinstance(result, ReportedEvidence) or result.report_values is None:
                raise ReportBoundaryError("The child must return its completed parent form")
            values = plain(result.report_values)
            validate_report(values, request.report_contract.value_schema)
            return values

        return ChildAction(spec, contract, project, synthesize)


class Policy:
    def __init__(self, binding, kind, request):
        self.binding, self.kind, self.request = binding, kind, request
        self.failure, self.operation_attempt, self.at_unit = None, 0, None

    def accept_failure(self, diagnostic):
        self.failure = normalize_failure(diagnostic)
        self.operation_attempt += 1

    async def next(self, view):
        if self.at_unit != view.units_consumed:
            self.failure, self.operation_attempt, self.at_unit = None, 0, view.units_consumed
        binding = self.binding
        controller = binding.controllers[view.path]
        binding.run_owners[view.path] = self.request.goal.goal_id
        children = CHILD_CAPABILITIES[self.kind]
        declared_inputs = {
            "mode": "action", "episode_kind": self.kind.value, "objective": plain(view.goal.objective),
            "task_context": plain(view.goal.task_context),
            "assignment": plain(self.request.message.findings),
            "parent_report_contract": (self.request.report_contract.as_record()
                                       if self.request.report_contract is not None else None),
            "fixed_problem": {"interface": self.binding.simulator.describe(),
                "scenario_definition": binding.problem,
                "ownership": "Read-only scientific context. The scenario host owns this definition; never copy its configuration into child assignments or ordinary tool arguments.",
                "persistence": "q=exp(-phase-aligned squared position,velocity,relative-period mismatch); sum duration*q, first revolution reference",
                "persistence_reference": "Inertial angles and states about the origin/barycenter. This unchanged winding metric can miss planet-relative or non-winding cycles; no path novelty bonus is currently assigned.",
                "persistence_scales": binding.settings["persistence"]},
            "available_tools": {name: TOOLS[name] + (
                " This simulation_investigation uses the fixed complete scenario. For a derived experiment, commission an iterative simparts investigation with a scientific question; the child chooses its successive observations under its own numerical controller."
                if self.kind == Kind.SIMULATION and name == "sim.run" else "") for name in CAPABILITIES[self.kind]},
            "available_children": [kind.value for kind in children],
            "report_field_examples": report_field_examples(),
            "controller": controller.model_state(),
            "local_credit_history": controller.history,
            "own_tool_observations": plain(controller.own_observations),
        }
        diagnostic, proposal_index = None, 0
        while True:
            # Every proposal still passes the unchanged parent-report boundary.
            own_inputs = {**declared_inputs, "operation_attempt": self.operation_attempt,
                **({"action_failure": self.failure} if self.failure is not None else {}),
                **({"action_request_diagnostic": diagnostic} if diagnostic is not None else {})}
            context = parent_model_inputs(view, own_inputs, reports=view.child_reports)
            response = await binding.models.complete("decide-" + identity(list(view.path)),
                binding.settings["models"]["routing"]["decide"], INSTRUCTIONS, context, ACTION_SCHEMA)
            try:
                if response["action"] == "tool":
                    return binding.tool(response, kind=self.kind, request=self.request)
                if response["action"] == "child":
                    return binding.child(response, view)
                raise ActionRequestError("wrong_command", field="action")
            except ActionRequestError as error:
                self.accept_failure(error.diagnostic)
            except ModelOutputError as error:
                # No Acquirable exists yet. Preserve the original cached response;
                # request another proposal instead of evaluating or repairing it.
                next_diagnostic = _action_json_diagnostic(response, error, proposal_index + 1)
                if next_diagnostic is None:
                    raise
                diagnostic, proposal_index = next_diagnostic, proposal_index + 1
                # The deterministic proposal index also distinguishes repeated
                # identical parser errors in the keyed model cache on replay.


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
        problem = plain(ScenarioSimulator(settings, None).problem)
        save(directory / "scenario.json", problem)
        save(directory / "manifest.json", {"run_id": "orbital_" + uuid.uuid4().hex,
            "scenario_id": problem["id"],
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
                "scenario_reference": binding.problem["id"],
                "initial_reference_velocity": binding.problem["reference_velocity"],
                "credit": "The simulator returns the agreed recurrence score. Parent credit is recomputed from scored observations on its own complete-scenario target, never child totals. Every iteration pursues improved credit; no artificial knowledge proxy or gates.",
                "outputs": "Measured trajectory candidates, quantitative scoped findings, uncertainty and next investigative directions"})
            try:
                record, result = await workflow.run_async(root, manifest["run_id"])
            except BaseException as error:
                save(attempt / "workflow-error.json", {"error": type(error).__name__, "message": str(error),
                    "diagnostic": getattr(error, "diagnostic", None),
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
