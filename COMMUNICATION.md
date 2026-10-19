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

1. The parent's `report_fields` specifies each field's name, meaning,
   `schema_json`, and `binding_json`. The schema encodes the type declaration, not child-return
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
4. Explicit recorded bindings copy requested facts from the exact saved scored
   observation. Remaining interpretation fields are filled by the child in a
   final REASONING turn in its existing decision conversation, after its last
   acquired result. Recorded-only forms need no final model call. There is no
   independent FAST composer. The return is validated locally, including cached returns.
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
Malformed final interpretation receives a small typed format diagnostic in that
same child conversation. Correction changes neither acquired units nor the yield
history; invalid responses remain in the model cache. Completed observations
remain in audit. There is no conversion to prose, silent coercion, or invented
fallback form. A parent schema incompatible with recorded factual values is a
communication error, never a rule for excluding the underlying scored evidence.

## Recorded facts and contribution identity

`binding_json: "{}"` declares interpretation. A factual binding explicitly names
`scope: "returned_trajectories"`, a selection, and either a single `value` source
or `fields` mapping parent-selected object properties to sources. For example:

```json
{"scope":"returned_trajectories","select":"parent_target_best","fields":{"source":"observation_index","velocity":"velocity","score":"score","requested":"requested_interval","observed":"observed_interval"}}
```

The parent still supplies its closed schema and field meanings. Names and prose
never imply a binding. `all` and `parent_target_all` return arrays; `max_score` and
`parent_target_best` return one selected row/value, or null when absent. Parent
target selections use the receiving parent's exact score projection, including
its declared scenario scope. Velocity, score and intervals come from the same
observation; maximum fields use the same stable first-winning row on ties.
The selection covers this child's returned acquired work, including descendants;
an inherited prior winner is not silently inserted as newly acquired work.

Internal saved observation references and credit evidence keys remain linked
through compaction and archival. Public observation indices are integers scoped
to this returned contribution, never audit hashes, forcing trials, or global
run identifiers. The commissioning instructions ask parents to declare the
contributing observation field before launch; the host adds no unrequested field.
The next parent input contains only the admitted form.

Scenario physics and forcing remain read-only scientific context rather than
assignment or report configuration. Supported factual sources cover measured
ship state/velocity, score, requested/observed intervals, outcome and explicitly
selected derived experiment scope. Derived scope describes the actual chosen
term/source/region/interval/refinement changes; it omits private source references
and unchanged base physics. Subjective scientific interpretations remain child-owned.

Recorded bindings are checked against their source domains before a child is
created. Maximum selections must permit null; all-row selections must permit an
empty array and any number of actual rows. Numeric bounds may retain a proven
source domain such as nonnegative scores, but cannot exclude possible recorded
values. Fixed ship/interval vector lengths and complete code vocabularies are
checked structurally. An incompatible declaration returns typed `report_fields`
feedback to the commissioning parent before any child acquisition. Schemas and
facts are never rewritten to make a result fit. An unexpected later source-read
failure preserves the already closed scored result in the existing episode store
without inventing an admitted form or replaying scientific work.

Objective and assignment prose still describe scientific questions. Work-tool
diagnostics and the human-readable final report remain separate records. They
are not automatically substituted for the child's typed upward return.

Saved comparison artifact references are machine audit data, including when a
parent acquires an observation that a child previously acquired. Scientific
model-facing comparison findings use `run_indices.left` and `run_indices.right`
arrays of local integers instead. Each lists all local acquisitions identifying
that saved observation; repeated identical runs can have several aliases. The
left/right numerical summaries are unchanged. Raw references remain in immutable
tool results and machine evidence. The audit-identity guard stays intact and
continues checking the final declared model inputs.

Historical run artifacts retain their original contracts. The earlier all-string
reports are not migrated, silently accepted, or presented as evidence that this
new boundary was used.

## Encoded planning requests

The copied strict JSON-object parser also handles the planner's encoded tool
arguments and child assignments. A syntax/shape error attributable to
`arguments_json`, `child_assignment_json` or a requested field's `schema_json`/`binding_json`
returns typed field/category/location feedback before an action becomes an
acquisition. The same planner supplies a new well-formed action. Original
proposals remain cached; the binding does not evaluate or repair invalid JSON.

Every proposal passes the unchanged parent-report input guard. A deterministic
`proposal_index` distinguishes repeated identical format errors in cache keys
and reconstructs on replay. This counts planning corrections, not Episode turns.
Other model, capability, scientific execution and upward-report errors retain
their existing boundaries.

For example, JSON cannot contain `{"value":1+2}`. A scalar calculation belongs
in a declared arithmetic request such as
`{"expression":"vy+radius*omega","values":{"vy":-1.30025,"radius":0.2,"omega":1.3975424859373686}}`.
The parser supplies feedback; the model supplies the corrected operation.

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
