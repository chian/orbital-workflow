"""Typed parent-report boundary, adapted from episodic_workflow.

Copied/adapted: method_loop/communication.py (ParentModelInputError,
ReportContract.admit, ParentReport identity guards), method_loop/episode.py
(_model_inputs), and the number/enum helpers in ResearchSource.parent_report
in case_reports/research/engine.py. See ../COMMUNICATION.md for provenance.

The source's numerical/enum projection is domain-specific. This binding enforces
the same boundary with a restricted typed schema supplied by the parent, retaining
the real OpenChia method_loop through subclasses of its contract/report types.
"""

import ast
from collections.abc import Mapping
from dataclasses import dataclass, field
import json
import math
import re

from jsonschema import Draft202012Validator, FormatChecker, SchemaError
from method_loop import ReportContract as MethodReportContract
from method_loop.communication import ParentReport as MethodParentReport

from .boundary_validation import parse_json_object
from .records import freeze, plain
from .report_facts import validate_binding, validate_binding_schema


class ParentModelInputError(ValueError):
    """The binding assembled invalid parent inputs before model dispatch."""


class ReportBoundaryError(ValueError):
    """A communication format error; no scientific evidence is discarded."""

    def __init__(self, message, *, code="invalid_report", field=None):
        self.diagnostic = {"category": "report_format", "code": code, "field": field}
        super().__init__(message)


# Copied from ResearchSource.parent_report: types and finite values, not prose
# classification. The caller raises on malformed data instead of coercing it.
def number(value):
    return value if type(value) in (int, float) and math.isfinite(value) else None


def enum(value, allowed, default="unknown"):
    return value if isinstance(value, str) and value in allowed else default


IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_.:-]{0,127}$")
UNITS = frozenset({"dimensionless", "sim_time", "position", "velocity", "acceleration",
                   "radian", "count", "position/sim_time", "position/sim_time^2"})
FORMATS = FormatChecker()


def is_identifier(value):
    return isinstance(value, str) and IDENTIFIER.fullmatch(value) is not None


def is_unit(value):
    return enum(value, UNITS, None) is not None


def is_expression(value):
    """Check expression syntax only; never evaluate model-supplied code."""
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        tree = ast.parse(value, mode="eval")
    except (SyntaxError, ValueError):
        return False
    allowed = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Name, ast.Load,
               ast.Constant, ast.Call, ast.Add, ast.Sub, ast.Mult, ast.Div,
               ast.Pow, ast.USub, ast.UAdd)
    functions = {"sqrt", "sin", "cos", "tan", "exp", "log", "abs"}
    for node in ast.walk(tree):
        if not isinstance(node, allowed):
            return False
        if isinstance(node, ast.Constant) and number(node.value) is None:
            return False
        if isinstance(node, ast.Call) and (
                not isinstance(node.func, ast.Name)
                or enum(node.func.id, functions, None) is None or node.keywords):
            return False
    return True


for format_name, checker in (("identifier", is_identifier), ("unit", is_unit),
                              ("mathematical_expression", is_expression)):
    # JSON Schema string formats do not apply to null or other JSON types.
    FORMATS.checks(format_name)(lambda value, check=checker: not isinstance(value, str) or check(value))


def validate_report_schema(schema):
    """Recursively require closed objects and declared scalar/string types.

    Parent-selected identifiers, units, enums and expressions remain strings.
    Open text/JSON containers and unsupported schema escape hatches cannot be
    used as report types. This checks the interface, not scientific quality.
    """
    schema = plain(schema)
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:
        raise ReportBoundaryError(f"Invalid parent report schema: {error.message}") from error
    allowed_keywords = {"type", "properties", "required", "additionalProperties", "items",
        "minItems", "maxItems", "uniqueItems", "minimum", "maximum", "exclusiveMinimum",
        "exclusiveMaximum", "enum", "const", "format", "description"}

    def check(node, path):
        if not isinstance(node, dict) or set(node) - allowed_keywords:
            raise ReportBoundaryError(f"{path}: use an explicit supported report type")
        declared = node.get("type")
        types = set(declared) if isinstance(declared, list) else {declared}
        if len(types - {"null"}) > 1 or not types <= {
                "object", "array", "number", "integer", "boolean", "null", "string"}:
            raise ReportBoundaryError(f"{path}: declare one JSON type, optionally nullable")
        if "object" in types:
            properties = node.get("properties")
            if (not isinstance(properties, dict) or node.get("additionalProperties") is not False
                    or set(node.get("required", ())) != set(properties)):
                raise ReportBoundaryError(f"{path}: object fields must be explicit, required and closed")
            for key, child in properties.items():
                if not is_identifier(key):
                    raise ReportBoundaryError(f"{path}: field names must be identifiers")
                check(child, path + "." + key)
        elif "array" in types:
            if "items" not in node:
                raise ReportBoundaryError(f"{path}: arrays require a declared item type")
            check(node["items"], path + "[]")
        elif "string" in types:
            choices = node.get("enum", [node["const"]] if "const" in node else None)
            if choices is not None:
                if not choices or any(value is not None and not (is_identifier(value) or is_unit(value))
                                      for value in choices):
                    raise ReportBoundaryError(f"{path}: enum strings must be declared codes, names or units")
            elif node.get("format") not in {"identifier", "unit", "mathematical_expression"}:
                raise ReportBoundaryError(f"{path}: strings require declared codes or a typed string format")
        elif "format" in node:
            raise ReportBoundaryError(f"{path}: string formats require a string type")
        if "enum" in node or "const" in node:
            for literal in node.get("enum", [node["const"]] if "const" in node else []):
                if isinstance(literal, (dict, list)):
                    raise ReportBoundaryError(f"{path}: composite literals cannot bypass typed fields")
                if isinstance(literal, str) and "string" not in types:
                    raise ReportBoundaryError(f"{path}: string literals require a string type")
                if isinstance(literal, float) and number(literal) is None:
                    raise ReportBoundaryError(f"{path}: literals must be finite")

    if not isinstance(schema, dict) or schema.get("type") != "object":
        raise ReportBoundaryError("A parent report requires a closed object schema")
    check(schema, "report")
    return schema


def validate_report(value, schema):
    def finite_values(item):
        if isinstance(item, float) and number(item) is None:
            raise ReportBoundaryError("Parent reports require finite JSON numbers", code="nonfinite_number")
        if isinstance(item, Mapping):
            for child in item.values():
                finite_values(child)
        elif isinstance(item, (tuple, list)):
            for child in item:
                finite_values(child)

    finite_values(value)
    errors = list(Draft202012Validator(plain(schema), format_checker=FORMATS).iter_errors(plain(value)))
    if errors:
        error = errors[0]
        path = ".".join(map(str, error.absolute_path)) or "report"
        raise ReportBoundaryError(f"{path}: {error.message}", code=error.validator,
                                  field=path if is_identifier(path) else None)


def generation_schema(schema):
    """Translate local string formats for model servers using standard types.

    The full contract stays authoritative at delivery. The model server does
    not implement our custom format checkers, including the expression parser.
    """
    schema = validate_report_schema(schema)

    def translate(node):
        result = dict(node)
        if "properties" in result:
            result["properties"] = {name: translate(child) for name, child in result["properties"].items()}
        if "items" in result:
            result["items"] = translate(result["items"])
        kind = result.pop("format", None)
        if kind == "identifier":
            result["pattern"] = IDENTIFIER.pattern
        elif kind == "unit" and "enum" not in result and "const" not in result:
            result["enum"] = sorted(UNITS)
            if isinstance(result["type"], list) and "null" in result["type"]:
                result["enum"].append(None)
        elif kind == "mathematical_expression":
            result["description"] = (result.get("description", "") +
                " Mathematical expression syntax; functions sqrt, sin, cos, tan, exp, log and abs. No prose or JSON strings.").strip()
        if "const" in result:
            result["enum"] = [result.pop("const")]
        # Host validation retains uniqueness; generation need not implement it.
        result.pop("uniqueItems", None)
        return result

    return translate(schema)


@dataclass(frozen=True)
class ReportContract(MethodReportContract):
    value_schema: Mapping
    fact_bindings: Mapping = field(default_factory=dict)

    def __post_init__(self):
        super().__post_init__()
        schema = validate_report_schema(self.value_schema)
        if set(schema["properties"]) != set(self.information):
            raise ReportBoundaryError("Requested information and typed report fields must match")
        if not isinstance(self.fact_bindings, Mapping) or set(self.fact_bindings) - set(self.information):
            raise ReportBoundaryError("Recorded bindings require a parent-requested field")
        bindings = {}
        for name, binding in self.fact_bindings.items():
            try:
                binding = validate_binding(binding)
            except ValueError as error:
                raise ReportBoundaryError(str(error)) from error
            if not binding:
                continue
            try:
                validate_binding_schema(binding, schema["properties"][name])
            except (KeyError, ValueError) as error:
                raise ReportBoundaryError(str(error)) from error
            if "fields" in binding:
                target = schema["properties"][name]
                if binding["select"] in {"all", "parent_target_all"}:
                    target = target.get("items", {})
                if set(target.get("properties", {})) != set(binding["fields"]):
                    raise ReportBoundaryError("Recorded columns must match the parent's declared object fields")
            bindings[name] = binding
        object.__setattr__(self, "value_schema", freeze(schema))
        object.__setattr__(self, "fact_bindings", freeze(bindings))

    def admit(self, value, *, audit_identifiers):
        # Adapted directly from episodic_workflow ReportContract.admit.
        report = ParentReport(self, value)
        report.exclude_audit_identifiers(audit_identifiers)
        object.__setattr__(report, "_audit_identifiers", audit_identifiers)
        return report

    def as_record(self):
        return {**super().as_record(), "value_schema": plain(self.value_schema),
                **({"fact_bindings": plain(self.fact_bindings)} if self.fact_bindings else {})}

    def interpretation_schema(self):
        properties = {name: plain(schema) for name, schema in self.value_schema["properties"].items()
                      if name not in self.fact_bindings}
        return {"type": "object", "additionalProperties": False,
                "properties": properties, "required": list(properties)}

    @classmethod
    def from_record(cls, value):
        if (not isinstance(value, Mapping) or set(value) not in (
                {"decision", "measurements", "information", "value_schema"},
                {"decision", "measurements", "information", "value_schema", "fact_bindings"})):
            raise ReportBoundaryError("Parent report contract requires its declared value_schema")
        return cls(**plain(value))


@dataclass(frozen=True)
class ParentReport(MethodParentReport):
    def __post_init__(self):
        if not isinstance(self.contract, ReportContract):
            raise ReportBoundaryError("Parent reports require a typed ReportContract")
        validate_report(self.values, self.contract.value_schema)
        super().__post_init__()

    # The following two guards are copied from episodic_workflow's ParentReport.
    def exclude_audit_identifiers(self, identifiers: tuple[str, ...], *, inputs=None) -> None:
        """Compare against actual identities, not patterns or shortened aliases."""
        if not isinstance(identifiers, tuple) or any(not isinstance(item, str) or not item for item in identifiers):
            raise TypeError("audit identifiers must be a tuple of nonempty strings")

        def inspect(value):
            if isinstance(value, str):
                if any(identifier in value for identifier in identifiers):
                    raise ValueError("parent report contains a child audit identity")
            elif isinstance(value, Mapping):
                for key, item in value.items():
                    inspect(key)
                    inspect(item)
            elif isinstance(value, (list, tuple)):
                for item in value:
                    inspect(item)

        inspect(self.values if inputs is None else inputs)

    def validate_model_inputs(self, inputs: Mapping) -> None:
        """Apply the same identity boundary to the final declared model inputs."""
        try:
            self.exclude_audit_identifiers(self._audit_identifiers, inputs=inputs)
        except ValueError as exc:
            raise ParentModelInputError(str(exc)) from exc


def _model_inputs(declared_inputs, available, selected):
    """Copied boundary routing with typed-report checks added before dispatch."""
    if not isinstance(declared_inputs, Mapping) or "child_reports" in declared_inputs:
        raise ParentModelInputError("child_reports is owned by the method's reporting boundary")
    if not isinstance(selected, tuple) or any(
        not any(report is admitted for admitted in available) for report in selected
    ):
        raise ParentModelInputError("model inputs require reports admitted for this parent")
    inputs = plain(declared_inputs)
    for report in available:
        if not isinstance(report, ParentReport):
            raise ParentModelInputError("Parent decision inputs require typed child reports")
        validate_report(report.values, report.contract.value_schema)
        report.validate_model_inputs(inputs)
    return {**inputs, "child_reports": [report.as_record() for report in selected]}


def parent_model_inputs(view, declared_inputs, *, reports):
    return _model_inputs(declared_inputs, view.child_reports, reports)


def completed_model_inputs(record, declared_inputs):
    """Use the same admitted direct-child reports while filling the final form."""
    reports = tuple(unit.episode_update.report for unit in record.unit_records if unit.episode_update)
    return _model_inputs(declared_inputs, reports, reports)


def report_contract(decision, measurements, fields):
    """Compile parent-selected fields; legacy all-string contracts cannot pass."""
    information, properties, bindings = {}, {}, {}
    for field in fields:
        if not isinstance(field, Mapping) or set(field) not in (
                {"name", "meaning", "schema_json"}, {"name", "meaning", "schema_json", "binding_json"}):
            raise ReportBoundaryError("Every requested field requires name, meaning and schema_json")
        name = field["name"]
        if not is_identifier(name) or name in properties:
            raise ReportBoundaryError("Report field names must be unique identifiers")
        information[name] = field["meaning"]
        properties[name] = parse_json_object(field["schema_json"])
        binding = parse_json_object(field.get("binding_json", "{}"))
        if binding:
            bindings[name] = binding
    return ReportContract(decision=decision, measurements=measurements, information=information,
        value_schema={"type": "object", "additionalProperties": False,
                      "required": list(properties), "properties": properties}, fact_bindings=bindings)


def report_field_examples():
    """Concrete type declarations for parents; field selection remains theirs."""
    samples = {"type": "array", "items": {"type": "object", "additionalProperties": False,
        "required": ["vx", "effective_duration"], "properties": {
            "vx": {"type": "number"}, "effective_duration": {"type": "number"}}}}
    definitions = [
        ("response_curve", "Measured effective duration against initial vx under the assigned fixed environment and vy", samples),
        ("trend", "Observed shape of the response curve; undetermined when observations do not define it",
            {"type": "string", "enum": ["increasing", "decreasing", "nonmonotonic", "undetermined"]}),
        ("best_observed_velocity", "Initial velocity with the greatest observed effective duration, or null if unobserved",
            {"type": ["array", "null"], "items": {"type": "number"}, "minItems": 2, "maxItems": 2}),
        ("persistence_unit", "Unit of effective recurrence duration", {"type": "string", "format": "unit"}),
    ]
    examples = [{"name": name, "meaning": meaning, "schema_json": json.dumps(schema), "binding_json": "{}"}
                for name, meaning, schema in definitions]
    best = {"type": ["object", "null"], "additionalProperties": False,
        "required": ["source_index", "velocity", "score", "requested_interval", "observed_interval"],
        "properties": {"source_index": {"type": "integer"},
            **{key: {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2}
               for key in ("velocity", "requested_interval", "observed_interval")},
            "score": {"type": "number"}}}
    examples.append({"name": "contributing_observation",
        "meaning": "The highest-scoring observation eligible for my target in this child's returned work, or null if none; source_index is scoped to this returned contribution",
        "schema_json": json.dumps(best), "binding_json": json.dumps({
            "scope": "returned_trajectories", "select": "parent_target_best", "fields": {
                "source_index": "observation_index", "velocity": "velocity", "score": "score",
                "requested_interval": "requested_interval", "observed_interval": "observed_interval"}})})
    return examples
