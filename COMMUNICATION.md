# Parent-selected typed reports

The parent chooses the information it needs for its next decision and declares
the return types before commissioning a child. Names such as `findings` or
`trends` do not constrain the content by themselves. The declared schema does.

## Code copied from episodic_workflow

Source checkout: `/home/chia/repos/episodic_workflow`, revision
`6578c49add92cfe1fb713a64a6d4635fb1c76509`.

- `method_loop/communication.py`: `ParentModelInputError`, the report admission
  sequence, `ParentReport.exclude_audit_identifiers`, and
  `ParentReport.validate_model_inputs`.
- `method_loop/episode.py`: `_model_inputs` selection and dispatch boundary.
- `case_reports/research/engine.py`: the `number` and `enum` helpers inside
  `ResearchSource.parent_report`. That method constructs a closed domain report
  from work records instead of delivering arbitrary strings from its ledger.
- `task_executors/evidence_extraction/argo.py`: `parse_json_object` and
  `ModelOutputError`. The copied exception inherits ValueError locally rather
  than importing the source checkout's provider exception.

The local implementation is in `orbital_workflow/communication.py` and
`orbital_workflow/boundary_validation.py`. The identity and routing guards are
adapted to the existing OpenChia method_loop types through subclasses. The source
checkout's domain-specific disease report is not copied into the orbital model.
There are no runtime imports from episodic_workflow, and neither source checkout
is modified. The accompanying method-loop license is retained in `licenses/`.

The generic source contract checks exact fields and audit identities; that alone
does not prohibit prose values. This project adds recursive typed-schema checks
to enforce the orbital return boundary while leaving the requested information
under parent control.

## Enforcement

1. The parent's `report_fields` specifies each field's name, meaning, and
   `schema_json`. This last field encodes the type declaration, not child-return
   content. It is parsed with the copied strict JSON parser and compiled into a
   closed `ReportContract.value_schema` before the child can be invoked.
2. Every object has explicit properties, `additionalProperties: false`, and all
   fields required. Unknown values use a declared nullable type; arrays have a
   typed item schema. Open text, open dictionaries, untyped arrays, composite
   literal escape hatches, unsupported schema keywords and undeclared references
   cannot become report types.
3. Strings remain valid as enum/const codes and names, or with a declared
   `identifier`, `unit`, or `mathematical_expression` format. Expression strings
   are parsed as mathematical syntax and never executed. A mathematical
   expression's syntactic validity does not establish scientific correctness.
4. The requested schema is passed to the FAST report composer. Its return is
   validated locally, including returns supplied by a cache or alternate provider.
   The same typed contract validates admission into the real method_loop report.
   Custom formats are translated for model generation: identifiers become a
   string pattern and units become enum values. Mathematical expressions remain
   strings with explicit instructions during generation, then pass the local
   syntax checker before delivery. The model server cannot implement a custom
   Python format checker; the original full contract remains authoritative.
5. Before a parent's next model call, the copied routing/identity guard checks
   the selected direct-child reports and their types. An untyped legacy report
   cannot be substituted into this input path. All child invocation paths,
   including finite diagnostics, require the guarded contract.

Type checking cannot establish that a trend is useful or an interpretation is
correct. Scientific reasoning and credit remain separate from this communication
format. No scientific result must pass a quality threshold to contribute.
Format errors stop malformed communication; completed child observations remain
in audit. There is no conversion to prose, silent coercion, or hidden repair.

Objective and assignment prose still describe scientific questions. Work-tool
diagnostics and the human-readable final report remain separate records. They
are not automatically substituted for the child's typed upward return.

Historical run artifacts retain their original contracts. The earlier all-string
reports are not migrated, silently accepted, or presented as evidence that this
new boundary was used.

## Exact examples

`examples/communication/parent-request.json` contains the parent's field
declarations, and `examples/communication/child-report.json` contains a matching
reply. The numbers are software examples, not new simulation results. Parents
receive the same examples in `Policy.next` and can choose different fields.

For a numeric response curve, the parent requests an array of closed records:

```json
{
  "type": "array",
  "items": {
    "type": "object",
    "additionalProperties": false,
    "required": ["vx", "effective_duration"],
    "properties": {
      "vx": {"type": "number"},
      "effective_duration": {"type": "number"}
    }
  }
}
```

For a trend, a string is appropriate with defined codes:

```json
{"type": "string", "enum": ["increasing", "decreasing", "nonmonotonic", "undetermined"]}
```

Other allowed string declarations include:

```json
{"type": "string", "format": "identifier"}
```

```json
{"type": "string", "format": "unit"}
```

```json
{"type": ["string", "null"], "format": "mathematical_expression"}
```

An unrestricted `{"type":"string"}` or open `{"type":"object"}` cannot
serve as a return type. Putting those inside an array or nested record does not
evade the boundary.

## Verification

`tests/test_communication.py` exercises parent request construction, nested
types, legitimate strings, unknowns, extra fields, prose, serialized JSON,
duplicate keys, nonfinite numbers, audit identities and untyped invocation bypasses.
Its integration fixtures run the actual method_loop with local model stubs:
a typed child report reaches the next parent decision; a paragraph in a numeric
slot cannot reach that decision, and the child's completed work stays in audit.
These are development checks, not a scientific workflow run or result gate.

The live three-call component round trip is saved in
`.artifacts/communication-live-first/`. REASONING chose the fields, FAST returned
their typed values, and REASONING selected a subsequent query using that report.
Its input numbers are labelled software fixtures and no simulator was called.
The initial custom-format transport failure is preserved under
`.artifacts/typed-string-formats-first/`; the corrected export is exercised in
`.artifacts/typed-string-formats-second/`.

The revised adaptive scientific run is `.artifacts/adaptive-typed-first/`. Its
four child reports use parent-selected numerical records, nullable quantities,
arrays and enum strings. Completed replay reproduces the same records and credit
without fresh model/tool calls; deliberate interruption/resumption preserves all
28 completed prefix files. The finite `.artifacts/skeleton-typed-first/` diagnostic
also exercises both branches and two levels of recursive simparts with typed
reports and actual tools, without assigning scientific credit.

The scientific run illustrates the limit of type enforcement: one valid enum
mislabels a decreasing noise response as nonmonotonic, and one returned ratio is
arithmetically inaccurate. `communication-review.json` records both observations.
The original reports remain unchanged, and neither error changes machine-projected
credit. The reviewed human findings report uses the recorded measurements. This
is not a scientific admission gate or a claim that the schema establishes truth.
