# Consolidated method audit and repair boundaries

Baseline: `d1545122ea3dddb6970ddd17488d1bc93ac58700` (`d154512`).
Date: 2026-10-18. Baseline line references below identify that revision, before
repair edits. Local audit inputs and detailed review artifacts are under
`.artifacts/method-audit-20261018/`.

The audit follows actual data paths through both method_loop implementations and
their numerical/communication bindings. It is not a generic review of product
areas. Each finding separates a method obligation, a project promise, or a useful
omission. Software type validation is allowed; scientific acceptance gates are not.
The user has authorized replacing the existing orbital credit implementation;
this is not a silent requirement to copy discrete hypervolume credit into a
continuous-score problem.

## Confirmed baseline findings

### P1: An EWMA replaced the supplied numerical yield-estimation design

`orbital_workflow/credit.py:200-247` maintains a prior prediction and updates it
using `forecast_memory` after each observed gain. There is no template-derived
rarefaction estimator, its window/subsampling policy, or its fitting result in
that path. This places a second, invented prediction policy in the controller.
OpenChia `numeric_control_library/controller.py` explicitly composes score/credit,
rarefaction and continuation; `method_loop/runtime.py:19-25` leaves estimator
semantics to that injected numerical binding rather than the generic loop.
Nano's numerical estimator source is
`question_pipeline/utilities/rarefaction.py`; the source snapshot/hash used for
this audit is recorded in `audit-inputs.json`.

The user's instruction is unambiguous: turn-by-turn yields remain actual
observations; estimation history/window policy belongs to the yield estimator.
Remove EWMA and its memory/prior-decay mechanism rather than tuning it.

### P1: Point-estimate stopping discarded uncertainty and unavailable states

`orbital_workflow/credit.py:239-247` stops on one scalar prediction versus a cost.
There is no separate estimator-ready state or uncertainty band. In the supplied
OpenChia continuation implementation,
`numeric_control_library/continuation.py:92-104`, unavailable estimates continue
and a ready upper bound supplies the stopping statistic. A lack of information
must not be replaced with an invented decaying scalar that eventually forces a
stop after a few unproductive turns.

The repair must keep estimation and continuation independent, retain unavailable
states explicitly and describe any fitted bands honestly as approximate and
model-dependent. It must not claim calibrated statistical coverage without
support.

### P2: Anchor-support environment flags used the wrong tuple positions

At baseline `credit.py:131`, variant tuples contain source model, modulation,
rotation and forcing. Lines `144-146` instead use the source-model string to
decide whether to include amplitude distance and the rotation flag to decide
whether to include forcing-amplitude distance. Reduced-model support can
therefore depend on a disabled term or ignore an enabled term. Historical
full-term runs have all these flags enabled and are not affected by this
particular indexing error.

A narrow correction was possible, but the entire unsupported anchor/coverage
credit implementation is being removed under the user's repair direction. Do
not carry its heuristic scores into the replacement under a different name.

### P2: Production simulation requests could bypass explicit simparts

`runtime.py:31-35` gives simulation and parts the same simulator capability;
`scientific.py:142-168` normalizes physical requests without checking the caller's
Episode kind. A simulation investigation could directly request omitted terms,
source-force reductions or smaller observation scopes. That bypasses the
accepted explicit simparts design even though the declared Episode tree itself
is enforced.

The repair should enforce declared scientific acquisition scope at the request
boundary and keep scoped/reduced work in simparts. This is Episode ownership,
not scientific rejection of a result.

### P2: Reopening a completed logical investigation was promised but unsupported

`EPISODES.md:60-63` promised preserving prior evidence and controller history when
continuing an investigation. `scientific.py:170-175` always constructs a fresh
child scope, and `110-113` constructs a fresh local controller. There is no
reopening action in `ACTION_SCHEMA`. New same-topic children can use prior
contracted findings but do not resume the previous child's accounting.

This violates a project capability promise, not the generic rule that distinct
Episode instances own distinct controllers. Existing exact whole-run crash
recovery is supported and is a different operation. See `steering-boundary.md`
and `resumeunit-probe.json` for the actual method restoration limits.

Reopening an already stopped child requires an explicit lifecycle decision about
Goal preservation, identity and immutable records, estimator-owned grounds for
renewed continuation, and rightful restoration of admitted child reports.
`ResumeUnit` only restores numerical inputs; silently clearing stop or routing
old reports through an extra context field would not repair this correctly.
Documentation now states the limitation rather than claiming implementation.

### P2: Full-target classification omitted declared field/forcing cases

The replacement classification initially checked source physics, terms, insertion
and observation domain but omitted membership of a/sigma in the declared study
family. An all-terms-enabled request with sigma=0 could therefore disable forcing
and receive complete-target root credit. This was found before completed repair
evidence. Full-target classification now includes both declared case memberships;
other environments remain available as explicit parts investigations with scoped
scores. The unfinished run-scored-001 used only a=.15/sigma=.03, so its saved
physical scores were unaffected. It remains an incomplete development run.

The final human-report scope label also omitted that declared case family and
scenario identity. Its display classification now follows the root assignment;
forcing-amplitude reductions and other undeclared cases retain their measurements
without being listed as complete-target observations. A regression compares
report labels with the actual root projection across declared cases, reductions,
continuations and altered physical scopes. This presentation repair does not
change the live workflow's frozen scientific execution or its credit.

### P2: Provider context compaction was misclassified as tool execution

The first fresh run exposed a transport error: the connection rejected the
provider's contextCompaction item as if it were an attempted scientific tool.
The narrow repair follows the locally generated app-server protocol and permits
that internal event while preserving refusal of model-side command execution.
Provider compaction creates no scientific acquisition or controller turn.

## Useful planner-context omission

The child's immutable root task context and its exact parent reporting contract
were stored but absent from `Policy.next` model inputs (`scientific.py:219-238`).
The objects and pre-execution contract enforcement were preserved. Neither
method_loop template mandates exposing these fields to a model, so this is not
classified as a proven generic-loop violation. Supplying them helps the planner
choose work relevant to the original objective and requested return fields.

Fresh-run report review also found a distinct composer-context omission. The
parent asked for the best score among an inherited anchor and new probes, but
report synthesis received only new observations, contract and completion. The
planner had the anchor assignment; the composer did not. The repair supplies the
child's assignment, objective and inherited task context to its own composer.
The development run's typed reports and physical observations remain unchanged.
This supplies rightful inputs; it neither checks scientific conclusions nor
requires a report's numerical interpretation to pass a result gate.

The same review found a separate model arithmetic error selecting the maximum
among tiny positive scores even when all rows were supplied. The root recovered
the correct maximum from the rows, and machine-derived credit remained correct.
Types constrain representation, not arithmetic truth. This limitation is retained
as posthoc review evidence rather than silently editing upward reports.

## Stronger acquisition requirement applied in the repair

### Fresh-run defect: recursive delegation of arithmetic without an acquisition

The incomplete `run-scored-003` exposed 65 simparts child edges for supplied-score
Richardson/difference/ratio arithmetic. Sixty-four consecutive arithmetic-only
scopes had zero acquired units. Their only tools were `sim.run` and `sim.compare`;
neither could compute the requested scalar from the inherited scores. No local
controller advanced while these scopes repeatedly commissioned the same question.
The run was interrupted and its evidence preserved. All recorded provider sessions
retired and no owned provider workers remained after cancellation.

`math.arithmetic` now supplies one bounded scalar calculation to math, simulation
and parts. Planner instructions direct calculations from sufficient supplied data
to this local tool; children remain available for smaller simulation questions.
The repair adds no recursion cap, duplicate-goal rejection, forced branch visit
or scientific gate. Arithmetic advances its own Episode by one acquired unit and
has no fabricated score bonus. Its zero marginal improvement reaches the same
estimator as any other actual acquisition. Fresh execution is still required.

At baseline `sim.compare` executed two explicitly specified integrations. The
old documentation disclosed that bounded operation; it was not a hidden adaptive
optimizer. The repair now requires one scored `sim.run` per integration turn and
comparison of already-saved observations only. A comparison must not conceal two
new scored acquisitions from the estimator's per-turn history. This is recorded
as the current repair requirement, without retroactively claiming that the
generic method_loop forbids every bounded multi-input tool operation.

### Fresh-run defect: unused forcing coverage aborted an unforced continuation

`run-scored-004` reached five completed root contributions and exercised math,
simulation and simparts, then failed during a reduced-model continuation from
the physical horizon H to 2H. The request disabled forcing, but the integrator
unconditionally required saved forcing coverage. The failure is an execution
error, not a yield stop;004 remains preserved as an incomplete development run.

The integrator now requires coverage only when forcing is enabled. Valid
in-coverage trajectories retain identical solver knots, states and scores.
Standalone unforced continuations can exceed unused forcing coverage.

The original problem fixes T=40pi, and the Episode design describes advancing
within the physical horizon. However, the prior model-facing simparts interface
advertised optional start/end and continuation without an upper bound. The
workflow now explicitly publishes and owns `[0, study.horizon]` as its physical
observation domain, including reductions. This tightens an incompletely specified
tool boundary; it is not a rule supplied by generic method_loop. Requests outside
the domain return retained typed `sim.request_diagnostic` feedback before any
integration. That acquisition has zero marginal credit, no simulation score and
no completed-run index. The Episode can use the feedback to investigate further;
its numerical controller still owns continuation. No existing result is rejected
or rewritten and no Episode turn cap is introduced.

### Fresh-run defect: own comparison exposed a shared child audit identity

`run-scored-005` completed one root investigation and two parts investigations,
then stopped before the next simulation-planner call. Its own comparison findings
included a persistent artifact reference for a numerical refinement. An earlier
child had acquired the identical simulation, so the same content-addressed
reference was also in that child's audit identities. The copied guard correctly
blocked the raw identity in the parent's declared model inputs. The typed child
report itself contained no identity.

The repair is confined to scientific model-facing comparison projection. Saved
tool findings, numerical summaries, machine evidence and artifact references stay
unchanged. Models receive all matching parent-local run-index aliases for each
side, including repeated acquisitions, instead of persistent references. No
cross-scope lookup or identifier whitelist is introduced. The report/identity
guard remains unchanged.005 is preserved incomplete; a new source identity and
fresh run are required for end-to-end evidence.

### Fresh-run defect: malformed encoded planning JSON aborted before acquisition

Run006 saved 549 acquired units, then its planner placed an unevaluated arithmetic
expression directly in a JSON numeric value for `math.arithmetic`. The outer
structured response was cached, but decoding `arguments_json` raised before
forming a tool action. No corresponding acquisition or score exists.006 remains
preserved as an execution-error development run.

Tool arguments and child assignments now reuse the copied strict JSON-object
parser already used for parent report-schema declarations. During action
construction only, an attributable parser error returns fixed field/category
codes, numeric/null parser positions and a deterministic proposal index to the
same planner. Each proposal passes the unchanged parent-report input guard.
The model supplies a new well-formed action; the binding never repairs JSON or
evaluates an expression embedded in a numeric slot. Planning corrections create
no acquired unit, score, controller advance or fabricated zero gain.

The proposal index also prevents identical parser diagnostics from reusing one
model-cache key indefinitely and reconstructs deterministically on recovery.
Model-provider, unrelated construction, executed-tool and upward-report errors
remain outside this narrow feedback boundary. Actual-loop regressions cover
repeated identical malformed arguments, child assignments, schema declarations,
typed reports, guard dispatch, interruption and completed cached reconstruction.
All 77 automated tests pass; fresh007 remains required for end-to-end evidence.

## Boundaries satisfied in reviewed paths

- The real method_loop owns acquisition, one controller advance, post-controller
  hooks, stopping, topology and Goal linkage.
- Parent-owned credit projection receives machine evidence; separate report
  synthesis returns the parent's predeclared typed fields. Child scalar totals
  are not added to parent credit.
- Closed schema validation and known audit-identity guards apply at contract
  construction, report admission and parent model dispatch. Valid types do not
  guarantee correct arithmetic or complete scientific interpretation.
- Saved root decision contexts from both binary runs contained typed
  `child_reports` and no raw child tool-observation channel.
- Closed child raw units/results are written to disk and replaced with compact
  references; controllers, model histories and owned provider workers retire.
- Exact interruption replay reconstructs controllers from cached transitions,
  without adding saved totals. Original code/configuration/library identities
  remain checked, and historical records remain immutable.
- Viewer and human reporting read saved evidence; their prose/editorial changes
  do not become scientific controller decisions or child-report replacements.

Full steering path coverage and citations are in `steering-boundary.md`.

## Authorized replacement and remaining limits

The repaired path is explicit score assignment from the simulator's agreed S
measurement, best observed assigned score and per-turn improvement, a
nano-template-derived scalar yield estimator, then independent continuation.
One real-valued marginal credit enters the estimator per Episode turn. No
identities, bins, rounding, artificial gain, controller memory or EWMA are used.
Window/subsample/fitting policy stays inside the estimator, with exact source
provenance and honest fractional-response/model-dependent uncertainty semantics.

Turns belong to their Episode's acquisition scope: one simulator integration
and score is one local tool turn; a mathematical operation or saved-data
comparison is another local acquisition whose marginal improvement may be zero.
One completed child investigation is one parent turn. Planning and reporting
model calls do not create additional controller turns. The integration review
explicitly checked this against method_loop's one advance per acquired unit;
skipping zero-credit acquisitions would distort the method's continuation stream.

The root scores observations of its fixed complete physical problem. Reduced
observations retain their scores/scope and return typed scientific information;
local parts/math can score their assigned observations. No theorem-count bonus
or replacement knowledge metric is invented. The removed 50/50 support-proxy
implementation is historical, not a claim about the new executable score path.
The simulator's agreed duration-weighted recurrence definition itself remains
unchanged; the controller does not inspect simulation duration to assign credit.

Historical simulations, model decisions, arrays and original credit remain
saved. Repairs affect new runs; old stopping results are not rewritten under
new semantics. Fresh end-to-end execution, replay and viewer verification of
the repaired binding are pending and must be recorded in their own completion
evidence. Tests or demonstrations performed before the repair are not that
verification. No arbitrary Episode cap, required branch visit or scientific
acceptance gate is introduced.
