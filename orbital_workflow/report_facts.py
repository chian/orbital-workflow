"""Explicit parent-selected factual form bindings over actual child work.

No field name or prose is interpreted. Internal evidence/artifact identities
stay in the closed result; observation indices are scoped to its ordered rows.
"""

from collections.abc import Mapping
import json

from .records import plain


FACTS = frozenset({"observation_index", "initial_state", "velocity", "vx", "vy", "score",
                   "requested_interval", "observed_interval", "outcome", "experiment",
                   "experiment_kind", "experiment_operations", "term_mask", "active_bodies",
                   "gravity_mode", "spatial_box", "radial_limits", "refinement"})
SELECTIONS = frozenset({"all", "max_score", "parent_target_all", "parent_target_best"})
OPERATIONS = ["term_mask", "sources", "approximation", "region", "radial_scope", "interval", "refinement", "continuation"]


def _object(properties):
    return {"type": "object", "properties": properties}


def _nullable(schema):
    result = dict(schema)
    declared = result["type"]
    result["type"] = list(dict.fromkeys((declared if isinstance(declared, list) else [declared]) + ["null"]))
    if "enum" in result:
        result["enum"] = [*result["enum"], None]
    return result


def _vector(size, *, nonnegative=False):
    return {"type": "array", "minItems": size, "maxItems": size,
            "items": {"type": "number", **({"minimum": 0} if nonnegative else {})}}


def _source_schemas():
    number = {"type": "number"}
    terms = _object({key: {"type": "boolean", "enum": [False, True]}
                     for key in ("central", "modulation", "rotating", "forcing")})
    bodies = {"type": "array", "items": {"type": "string", "enum": ["body_1", "body_2"]}, "maxItems": 2}
    approximation = {"type": "string", "enum": ["resolved", "monopole"]}
    numerics = _object({"method": {"type": "string", "enum": ["RK23", "RK45", "DOP853", "Radau", "BDF", "LSODA"]},
        **{key: {"type": "number", "minimum": 0, "exclusiveMinimum": 0}
           for key in ("max_step", "rtol", "atol", "sample_step")}})
    kind = {"type": "string", "enum": ["base", "derived"]}
    operations = {"type": "array", "items": {"type": "string", "enum": OPERATIONS}, "maxItems": len(OPERATIONS)}
    experiment = _object({"kind": kind, "operations": operations,
        "source_run_index": _nullable({"type": "integer", "minimum": 1}),
        "terms": _nullable(terms), "active_bodies": _nullable(bodies), "gravity_mode": _nullable(approximation),
        "spatial_box": _nullable(_vector(4)), "radial_limits": _nullable(_vector(2, nonnegative=True)),
        "interval": _nullable(_vector(2, nonnegative=True)), "refinement": _nullable(numerics)})
    return {"observation_index": {"type": "integer", "minimum": 1}, "initial_state": _vector(4),
        "velocity": _vector(2), "vx": number, "vy": number, "score": {"type": "number", "minimum": 0},
        "requested_interval": _vector(2, nonnegative=True), "observed_interval": _vector(2, nonnegative=True),
        "outcome": {"type": "string", "enum": ["horizon_reached", "inner_exit", "outer_exit", "region_exit",
                                                   "solver_error", "collision_body_1", "collision_body_2"]},
        "experiment": experiment, "experiment_kind": kind, "experiment_operations": operations,
        "term_mask": _nullable(terms), "active_bodies": _nullable(bodies), "gravity_mode": _nullable(approximation),
        "spatial_box": _nullable(_vector(4)), "radial_limits": _nullable(_vector(2, nonnegative=True)),
        "refinement": _nullable(numerics)}


def validate_binding_schema(binding, schema):
    """Prove representation compatibility before acquiring scientific work.

    This checks the declared source's value domain, never an observed score or
    scientific quality. Parent restrictions may not filter possible source facts.
    """
    sources = _source_schemas()
    actual = (sources[binding["value"]] if "value" in binding else
              _object({name: sources[source] for name, source in binding["fields"].items()}))
    actual = ({"type": "array", "items": actual} if binding["select"] in {"all", "parent_target_all"}
              else _nullable(actual))

    def types(node):
        value = node["type"]
        return set(value) if isinstance(value, list) else {value}

    def cover(expected, declared):
        expected_types, declared_types = types(expected), types(declared)
        if any(kind not in declared_types and not (kind == "integer" and "number" in declared_types)
               for kind in expected_types):
            raise ValueError("Recorded source types, including absent values, must fit the parent schema")
        literals = declared.get("enum", [declared["const"]] if "const" in declared else None)
        if literals is not None:
            domain = expected.get("enum")
            if domain is None or not {json.dumps(value) for value in domain} <= {json.dumps(value) for value in literals}:
                raise ValueError("Recorded source values cannot be restricted by an incomplete enum or const")
        if "string" in expected_types:
            if declared.get("format") not in (None, "identifier"):
                raise ValueError("Recorded source codes require an identifier-compatible string schema")
        if expected_types.intersection({"number", "integer"}):
            lower = expected.get("exclusiveMinimum", expected.get("minimum"))
            exclusive = "exclusiveMinimum" in expected
            for key in ("minimum", "exclusiveMinimum"):
                if key in declared and (lower is None or declared[key] > lower
                        or (key == "exclusiveMinimum" and not exclusive and declared[key] == lower)):
                    raise ValueError("Recorded numeric bounds cannot exclude a possible source value")
            if "maximum" in declared or "exclusiveMaximum" in declared:
                raise ValueError("Recorded numeric sources have no smaller parent-selected upper bound")
        if "object" in expected_types:
            if set(expected["properties"]) != set(declared.get("properties", {})):
                raise ValueError("Recorded object properties must match the selected source columns")
            for name, child in expected["properties"].items():
                cover(child, declared["properties"][name])
        if "array" in expected_types:
            if declared.get("minItems", 0) > expected.get("minItems", 0):
                raise ValueError("Recorded arrays must permit every source length, including empty results")
            if "maxItems" in declared and ("maxItems" not in expected or declared["maxItems"] < expected["maxItems"]):
                raise ValueError("Recorded arrays cannot cap the number of actual source rows")
            if declared.get("uniqueItems"):
                raise ValueError("Recorded arrays must permit repeated actual values")
            cover(expected["items"], declared["items"])
    cover(actual, plain(schema))


def validate_binding(binding):
    if not isinstance(binding, Mapping):
        raise ValueError("A recorded binding must be an object")
    binding = plain(binding)
    if not binding:
        return binding
    if (set(binding) not in ({"scope", "select", "value"}, {"scope", "select", "fields"})
            or binding["scope"] != "returned_trajectories" or binding["select"] not in SELECTIONS):
        raise ValueError("Declare a supported recorded trajectory scope and selection")
    sources = [binding["value"]] if "value" in binding else binding["fields"].values() if isinstance(
        binding["fields"], dict) and binding["fields"] else []
    if not sources or any(not isinstance(source, str) or source not in FACTS for source in sources):
        raise ValueError("Recorded bindings require explicit supported factual sources")
    return binding


def public_experiment(source):
    """Show actual selected derived operations, never private scenario settings."""
    scope = source.get("experiment", {})
    operations = list(scope.get("operations", ()))
    interval = source.get("requested_interval", [source.get("start"), source.get("end")])
    numerics = source.get("numerical_settings") or {key: source.get(key) for key in
        ("method", "max_step", "rtol", "atol", "sample_step")}
    return {"kind": scope.get("kind", "base"), "operations": operations,
        "source_run_index": scope.get("source_run_index"),
        "terms": plain(source.get("terms")) if "term_mask" in operations else None,
        "active_bodies": plain(source.get("active_bodies")) if "sources" in operations else None,
        "gravity_mode": source.get("gravity_mode") if "approximation" in operations else None,
        "spatial_box": plain(source.get("spatial_box")) if "region" in operations else None,
        "radial_limits": plain(source.get("radial_limits")) if "radial_scope" in operations else None,
        "interval": plain(interval) if {"interval", "continuation"}.intersection(operations) else None,
        "refinement": plain(numerics) if "refinement" in operations else None}


def trajectory_facts(item, store, index):
    """Use the exact saved observation, including its recorded ship state."""
    saved = store.json(item["observation_ref"])
    request, summary = saved["request"], saved["summary"]
    if summary["score"] != item["measurement"]["score"]:
        raise ValueError("Saved trajectory and scored observation disagree")
    state = request["initial_state"]
    experiment = public_experiment(request)
    return {"observation_index": index, "initial_state": state, "velocity": state[2:4],
            "vx": state[2], "vy": state[3], "score": summary["score"],
            "requested_interval": [request["start"], request["end"]],
            "observed_interval": summary["observed_interval"], "outcome": summary["outcome"],
            "experiment": experiment, "experiment_kind": experiment["kind"],
            "experiment_operations": experiment["operations"], "term_mask": experiment["terms"],
            **{key: experiment[key] for key in ("active_bodies", "gravity_mode", "spatial_box", "radial_limits", "refinement")}}


def project_fields(bindings, measurements, store, parent_projection):
    """Fill only fields the parent explicitly bound, from one row per selection."""
    observations = [(index, item) for index, item in enumerate(measurements, 1)
                    if item["type"] == "trajectory"]
    result = {}
    for name, binding in bindings.items():
        if binding["select"].startswith("parent_target") and parent_projection is None:
            raise ValueError("A parent-target binding requires the receiving parent's actual projection")
        selected = []
        for index, item in observations:
            score = (parent_projection(item) if binding["select"].startswith("parent_target")
                     else item["measurement"]["score"])
            if score is not None:
                selected.append((score, index, item))
        multiple = binding["select"] in {"all", "parent_target_all"}
        if not multiple:
            # max is stable on ties, matching accounting's first winning row.
            selected = [max(selected, key=lambda row: row[0])] if selected else []
        values = []
        for _, index, item in selected:
            facts = trajectory_facts(item, store, index)
            values.append(plain(facts[binding["value"]]) if "value" in binding else
                          {key: plain(facts[source]) for key, source in binding["fields"].items()})
        result[name] = values if multiple else values[0] if values else None
    return result


def model_measurements(summary):
    """Communicate measured ship behavior without republishing scenario knobs."""
    values = {name: plain(summary[name]) for name in (
        "score", "initial_state", "requested_interval", "observed_interval", "outcome",
        "terminal_state", "radius_min", "radius_max", "rhs_evaluations", "persistence_measurement",
    ) if name in summary}
    if "persistence_measurement" in values:
        values["persistence_measurement"].pop("settings", None)
    if "experiment" in summary:
        values["experiment"] = public_experiment(summary)
    return values
