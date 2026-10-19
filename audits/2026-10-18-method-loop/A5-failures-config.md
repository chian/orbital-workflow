# A5 audit — failures, retries, configuration and termination

The scientific workflow remains **paused**. This report is inspection and saved-record analysis only. No source/configuration/scientific record was changed, and no model, simulator, tool, replay, fit, test, launch or recovery was run. The only writes are this report and its JSON companion. `BRIEF.md` indexes the user’s authority and mandatory fields; `STOPPED_STATE.json` is the stopped-prefix accounting source. A3-F3 is cross-referenced, not counted again here.

The actual loaded implementation is `/home/chia/repos/OpenChia/method_loop`, confirmed by frozen `environment.json` and the CLI/bootstrap path. I read the actual loop/source/controller boundary in both OpenChia and nano-graphrag. OpenChia’s generic loop owns structural nesting, acquisition integration and numerical stop obedience; orbital owns physical admission, tools, scalar projection, cache, model protocol and report schemas. The nano-graphrag loop remains useful design evidence, but its optional `bound`, `bound_hit`, older EpisodeResult channels and failure model are not the loaded orbital execution.

The stopped prefix has **402 committed local units**, **375 tool acquisitions**, **27 child completion acquisitions**, **27 closed Episodes (all yield_stop)**, and **20 root committed turns**. The last root continuation state is **stop=false**, upper projected gain **0.05910150506675524** against cost **0.02**. The 007 workflow ended by **external user interruption**, evidenced by SIGINT and CancelledError, with no root summary and no proof of goal completion. This is neither source exhaustion nor numeric convergence.

## Individual blocking conditions and partial-work behavior

The classification below concerns the exact blocked operation. A legitimate representation/reference/fixed-problem/capability check does not become an unauthorized scientific quality gate merely because it raises. The incomplete operational delivery after many such checks is A5-F1. No inspected current primary path contains a proof prerequisite, score threshold for accepting a simulation, solver-agreement gate, confidence threshold for accepting evidence, fixed scientific turn cap, retry cap or depth cap.

| Operation and exact condition | Authority/category and code | What is blocked; what survives; responsible Episode feedback |
| --- | --- | --- |
| Outer model response is not strict finite object JSON; duplicate keys/nonfinite tokens | Explicit representation boundary; `boundary_validation.py:22–57`, `models.py:229–239` | That physical response fails before a successful model cache. Raw response/error audit survives; no acquisition/score/turn. Policy does not catch the failure around `models.complete`; no Episode correction input (F1). |
| Encoded `arguments_json`, `child_assignment_json`, or a field’s `schema_json` is malformed strict JSON | Explicit representation boundary; `scientific.py:103–123,349–371` | No Acquirable exists. Original proposal remains cached; exact category/field/index/parser location and incremented proposal_index enter the same Episode’s next proposal. No tool, score or controller turn. Changed context makes this a meaningful correction attempt; no cap is present. No occurrence in 007. |
| Child report declaration is empty/open/untyped, uses an unsupported string/type, duplicates field name, or does not match required information | Explicit parent-owned type boundary; `communication.py:90–149,204–229,289–302`; generic core checks contract and parent edge | Child launch is blocked before work. Valid earlier units survive. JSON parser errors get the preceding repair loop; schema/type errors raise ReportBoundaryError and get no Episode feedback (F1/F2). Parent-specific minimum/maximum constraints are declared contract data, not evidence of a hidden host scientific gate. |
| Upward report malformed, wrong keys/type, or contains an actual child audit identity | Explicit representation/identity boundary; `communication.py:152–168,232–265`; OpenChia `episode.py:1524–1573` | A3-F3 owns the verified failure path: child work already closed/saved; report delivery and parent acquisition fail, invalid response may be cached. No 007 occurrence. No recommendation to weaken type/identity boundaries. |
| Tool or child type is outside declared capabilities/tree, child Goal/contract linkage invalid | Explicit scoped execution boundary; orbital `runtime.py:31–36,91–108,125–142`; OpenChia `episode.py:1190–1215,1763–1789` | Prevents ungranted operation/nesting. Valid earlier work remains; no acquisition for the blocked action; current exception reaches infrastructure, not useful local feedback. Model-side native actions are independently prevented by `models.py:140–167,208–220`. |
| `sim.run` explicitly conflicts with scenario gravity/id or workflow observation window; supplies raw forcing_id | Explicit fixed-problem/reference ownership; `scientific.py:189–208` | Conflicting simulation is not integrated. Original proposal survives; sometimes forcing generation precedes a later rejection. Exception gives no responsible-Episode diagnostic (F1). `binary_reference` uses a different silent override path (F3). |
| `simulation_investigation` requests reduced terms/active bodies/monopole/environment outside declared cases/spatial box/changed radial limits or start-zero position | Declared complete-model capability, with explicit simparts alternative; `scientific.py:210–220,257–260,340–342` | Blocks that invocation under the wrong capability. Explicit simparts retains reduction tools, source motion and collision surfaces. It is not a scientific result acceptance test. Earlier work survives; no automatic substitution/delegation; current error feedback incomplete (F1). Root score eligibility uses related scope predicates separately; A1/A2 audit their semantics. |
| Simulation inputs are nonfinite/bool numerics, malformed state/terms/interval/limits, nonpositive numerical settings, unknown body/approximation; invalid forcing trial | Representation/math-validity/reference checks; `simulation.py:19–111,152–156`; `gravity.py:11–44` | Prevents a mathematically undefined/malformed specified operation. Numerical settings positivity is not a demand for high accuracy. No valid completed observation is discarded. Error is operationally unhandled by Episode (F1); trial is validated at generation, and cached forcing makes type validation path-dependent (see defaults discussion). |
| Valid request has end beyond fixed physical observation window | Fixed physical domain, not an Episode effort budget; `tools.py:137–147` | Returns **sim.request_diagnostic** with code, exact requested interval and fixed window. No integration/score/run_index. Diagnostic becomes a local acquired observation with empty received_scores, zero marginal credit and one estimator turn via `project_observation`/`CreditController.observe`. No 007 occurrence. Invalid start<0/start>=end fails constructor first and does not use this diagnostic. |
| `sim.compare` run_index absent/noninteger/outside current Episode, saved object absent/not a simulation, or artifact integrity mismatch | Exact local-reference/type/integrity boundary; `scientific.py:261–265`, `tools.py:149–167`, `artifacts.py:33–47`, `durable.py:106–123` | Blocks only requested comparison/reuse. Existing observations remain. No new integrations; no manufactured zero score. Cache corruption/missing references fail explicitly; action/execution failures lack Episode diagnostic (F1). Equal/unequal/no shared sample times are returned measurements without acceptance threshold. |
| Arithmetic envelope invalid/named inputs nonfinite or exceeds 64; expression over 1024 chars/128 AST nodes/depth32 or unsupported syntax/name; domain/division/overflow | Bounded declared scalar capability and mathematical validity, implementation-owned bounds, not science/yield budget; `tools.py:21–100,169–202` | Invalid envelope/input raises (F1). Valid envelope with expression/domain problem **returns value=null and diagnostic code**, preserved expression/inputs; zero marginal credit with no fabricated simulation score. Successful arithmetic also creates no measurement credit. All 69 actual 007 arithmetic returns are code=ok. |
| Numeric/symbolic unknown operation, malformed/nonfinite reference position/time, invalid fit points, arithmetic singular/domain error | Declared mathematical operation/domain; `tools.py:205–290`, `gravity.py:63–75` | Blocks only undefined/unsupported calculation, retaining prior work; current thrown errors abort active stack (F1). Rank deficiency and residuals in local fit are observations, not rejection. Unit central/conic references explicitly describe a reduced model; scenario binary reference receives fixed scenario gravity. No hidden optimizer/simulation sweep. |
| Lean unavailable, exits nonzero, or exceeds subprocess60s | Optional capability availability/execution; `tools.py:292–305` | Unavailable/nonzero exit **returns diagnostics**, never prevents other work and earns no bonus. Source timeout=60 is an implementation execution limit for one optional tool, not an Episode cap; TimeoutExpired instead raises through F1. No Lean acquisition in 007. No user provenance for that precise time is established. |
| Score is None versus numeric0; nonfinite/negative/bool score | Explicit finite numerical representation for completed scored observation; `credit.py:109–133` | None means no eligible score and is skipped; 0 is retained in received_scores; malformed numeric score raises. This does not create a hidden minimum useful score. All genuine0 runs survive. Failing before a score is not represented as a zero simulation. |
| Yield history lacks template minimum information, or numeric fit is unidentifiable | Estimator status/validity, not result gate; `score_yield.py:178–214,250–257` | Coded insufficient/unidentifiable is not normal zero and cannot trigger stop. Actual score/history survives; controller does not overwrite prediction or introduce another chooser. Template optimizer’s 100 iterations/bounds are internal numerical work, not scientific attempts/retries. |
| Resume source/config/runtime numerical-library identity differs; cached artifact absent/corrupt; durable replay diverges; writer lock already held | Exact dependency/identity/single-writer integrity, `durable.py:42–95,106–123` | Resume/write/reuse is blocked explicitly, saved scientific evidence retained. No automatic source migration or credit transplantation. No blanket permission to remove these checks. These are operational errors and not convergence/completion. |

The forcing-trial check has one small path-dependent detail: `simulation_arguments` consults the Python dictionary before calling `generate_forcing`, so an already present integer trial1 can also be retrieved by `1.0` or `True` due to Python key equality; a fresh such trial is rejected by `type(trial) is int`. Effective forcing remains the same stored realization, and 007 always supplied integer trial values. This is an input normalization edge, not evidence of extra physical trials or a hidden scientific gate; validate the selector consistently if that interface is revised, together with F3.

## Effective configuration and ownership

| Layer/setting | Effective behavior and consumers | Authority/provenance and audit conclusion |
| --- | --- | --- |
| CLI source/config | `__main__.py:12–13` defaults actual source to sibling OpenChia; bootstrap checks exact loaded module. `--scenario` explicitly selects saved scenario study.toml even when `--config` is present (`:126–130`), consistent with help’s frozen-scenario selection. Resume uses run’s stored study.toml (`scientific.py:374–377`). | Source design; actual007 invocation supplied `--scenario scenario_02`. Frozen environment confirms OpenChia. No accidental nano import or silent changed resume config is shown. Simultaneous --config/--scenario precedence is code-defined, not a second merged configuration. |
| Study scenario/physics | Scenario02 supplies masses[.75,.25], separation.8, phase0, surfaces[.05,.035], insertion position[1,0], radial[0,4]. Fixed gravity/id/window are injected; default end=study.horizon=125.66370614359172. simparts may explicitly scope dynamics/space/time within the same window. | Explicit fixed-problem rule plus implementer scenario data; raw forcing reference remains workflow-owned. Scenario defaults in `gravity.py:88–95` apply if omitted, not to this saved scenario. |
| Simulation request defaults | Missing trial→1; vx→0/vy→1 (not `scenario.reference_velocity`); state→scenario initial position plus vx/vy; limits→scenario radial; end→study horizon. SimulationRequest then defaults a=.15,sigma=.03, all terms=true, DOP853,max_step=.05,rtol1e-7,atol1e-9,sample_step.02,start0,resolved gravity/all bodies, no spatial box (`scientific.py:189–208`, `simulation.py:31–64`). | Implementation defaults, not all user-selected constants. `suggested_a/sigma/reference_velocity` are model context suggestions, not automatic request defaults. In007 every sim proposal explicitly supplies trial,vx,vy,a,sigma,terms; radial defaults in all277 and end defaults in259. No changed a/sigma or reference-velocity execution is inferred. Conflicting explicit duplicates are F3. |
| Mathematical reference context | Binary_reference receives scenario gravity; omitted time0/position[1,0] remain tool-local defaults, not dynamically scenario.initial_position (`scientific.py:266–268`, `tools.py:209–229`). Unit central tools intentionally use unit mass and position(1,0), with explicit reduced assumptions. Fit points are caller data and rank/residual remain visible. | Fixed physics is rightful; silent conflicting explicit gravity replacement is F3. All current scenarios use position[1,0] and total mass1, so the duplicate reference defaults cause no established007 error. The actual reference explicitly supplies time and position. Do not claim an absent general scenario-default propagation bug was observed. |
| Score/persistence | Run passes configured scales(.1,.1,.1) and128 phase samples to CachedTools; standalone dispatcher falls back to PersistenceSettings only if not supplied. Duration-weighted recurrence is retained; first revolution reference and nonwinding limitation are explicit. | Agreed measurement; defaults exist both dataclass and TOML but effective run config is explicit. No score acceptance threshold. Solver-prefix semantics remain Q1. |
| Yield/continuation | Per-kind `[yield]` overrides template defaultsW8,m4,alpha.05. Cost root.02, others.04 is explicit TOML, read at controller construction and every state decision. Stop only when normal current upper≤cost; no smoothing/counter/budget/alternate chooser. | A2 owns exact cost/statistical provenance question. Constants are transparent implementation choices rather than proven user-selected numeric values. Generic method only routes stop/transition booleans. |
| Models/routing | Config→ModelRole→thread/start and turn/start with exact model/effort. Server mismatch raises; no silent fallback. FAST luna/none, REASONING sol/medium; decide→REASONING, report→FAST. Native execution disabled per thread. Command is codex app-server --stdio. | Explicit user model/connection choices. 007 cache role counts agree:402 decisions+27 reports. Operational timeout/recovery beyond adapter remains Q2; existing OpenChia host launch docs are not an alternative config source for this direct binding. |

## Findings and open policy questions

### A5-F1 — Non-parser action and tool failures terminate all active Episodes without a usable failure return

**Severity:** medium. **Principles:** 2, 4, 7, 16, 17, 18, 21.

**Evidence:** Verified reachable current-code behavior; not an observed non-cancellation incident in stopped 007.

**Uncertainty:** The audit establishes exception propagation by inspection, not by a fault injection. Required input/reference/capability enforcement is legitimate; the defect is its failure-delivery scope. A3-F3 separately owns upward-report synthesis/admission failure.

**1. Requirement and authority.** Explicit latest user principles 7 and 17 require identifying the individual blocked component, retaining valid partial contributions and giving useful structured feedback to the responsible Episode. Principles 2 and 16 separate operational failure from its scientific owner’s next decision and from goal completion. The required type/reference/capability boundaries and the fixed physical problem are explicit user requirements. A particular recovery protocol is a proposed implementation choice, not an existing user-selected retry rule.

**2. Owner.** ScientificBindings/Policy own admission and scientific tool feedback; ToolDispatcher owns operation execution; Workflow and the actual OpenChia Episode own integration and lifecycle. The responsible Episode is the one whose Policy proposed the failing action, and its parent owns whether to pursue a different child after a partial failure.

**3. Trigger.** Any action-construction error other than the specially recognized ModelOutputError for an encoded JSON field: e.g. invalid local sim.compare run_index, conflicting scenario/window, reduced sim.run in simulation_investigation, invalid SimulationRequest shape, unknown child kind/report type, undeclared tool or nesting. During acquisition the same path applies to an actual tool exception, including invalid saved comparison object, invalid mathematical input, missing forcing/reference, singular force calculation or subprocess.TimeoutExpired from optional Lean. These conditions are individually classified in the operation table; none is evidence of a scientific quality gate.

**4. Code path.** scientific.py:254–278 tool/child construction; Policy.next:355–369 catches only ModelOutputError with matching encoded field; runtime.py:_Source._wrap:91–108 and Workflow.run_async:203–213; tools.py:execute:116–126 writes an execution_error object then re-raises. OpenChia/method_loop/episode.py:_leaf_acquisition_async:1008–1028 and _run_loop_async:1392–1419 do not convert exceptions; _acquire_unit_async:1421–1435 appends only after acquisition. Episode.run_async:1126–1140 leaves in finally, without on_close when the loop raises. run_scientific:413–419 writes workflow-error.json and re-raises.

**5. State effect.** Previously committed unit records, tool-cache successes, immutable inputs/arrays and successfully closed descendants remain durable. The failing action has no UnitRecord or new local acquisition/controller turn. A construction failure may create a forcing artifact before the later check; an execution exception records an immutable request/error object but no successful tool cache. Completed work in an interrupted current child is not packaged into a returned child result; active in-memory controller state is retired on unwind. No earlier saved contribution is explicitly deleted.

**6. Communication effect.** No later Policy.next receives a typed failure category, affected input/reference or retained-partial-work status. Construction errors generally reach only the top-level exception type/message; execution errors also exist as detached audit objects. The failing Episode and all active ancestors stop; they do not consume that audit object as an ordinary rightful input. This differs from math.arithmetic domain diagnostics and sim.request_diagnostic, which do reach own_tool_observations. A source_failed completion exists in the core but this binding does not construct it for these errors.

**7. Credit effect.** No artificial zero simulation score or bonus is invented for the absent acquisition. Prior child-local credit can exist on disk without integration into parent credit because the child has not returned. Parent credit is unchanged by that unfinished child call. The audit does not recommend declaring a failed acquisition successful or bypassing the parent report contract.

**8. Controller effect.** There is no new yield observation for the failure and no subsequent local continuation decision. An operational exception instead aborts the complete active call stack, regardless of each current numeric continuation rule. The missing recovery is not permission to install a scientific acceptance test or hidden retry/effort budget.

**9. Run evidence.** 007 contains 375 committed tool acquisitions: 277 sim.run, 69 math.arithmetic, 28 sim.compare and 1 math.numeric. All 69 arithmetic diagnostics are ok; no window diagnostic, solver_error or tool exception was found among committed units. The only model error.json and workflow-error.json are CancelledError from the explicit user stop, so this finding is code-path evidence only. The actual external interruption is accounted separately below.

**10. Proposed correction — no edits.** Introduce binding-owned structured operational outcomes identifying phase, exact field/reference, cause class and preserved work. Feed recoverable request/execution diagnostics to the responsible Episode using its permitted typed interface; retain exact audit details on disk. Where recovery is impossible, close honestly with an operational failure while preserving valid partial evidence and a contractually permitted parent status. Keep each representation/reference/fixed-problem/capability check, distinguish a changed action from a replay, and do not silently rerun completed science, fabricate a score, add a raw child channel or impose an invented retry cap. Pre-acquisition invalid request/type/capability feedback stays at the same controller state and creates no acquisition turn. An actually completed diagnostic remains a normal feedback acquisition; an unfinished operational failure must not be converted generically into a completed zero-credit turn.

**11. Verification needed — not run.** In a future separately authorized focused failure experiment, use one bad run_index, one validly encoded invalid SimulationRequest, one undeclared capability and one execution exception after valid work. Verify only the affected operation is blocked, exact structured feedback reaches the rightful Episode, earlier evidence is retained, no phantom score/turn appears, and an unrecoverable close is distinguishable from yield or success. No fault injection, tool execution, model call, test or replay was performed in this audit.

**Primary references:**

- [scientific.py:254](/home/chia/repos/orbital_workflow/orbital_workflow/scientific.py:254).
- [scientific.py:355](/home/chia/repos/orbital_workflow/orbital_workflow/scientific.py:355).
- [tools.py:116](/home/chia/repos/orbital_workflow/orbital_workflow/tools.py:116).
- [runtime.py:91](/home/chia/repos/orbital_workflow/orbital_workflow/runtime.py:91).
- [episode.py:1008](/home/chia/repos/OpenChia/method_loop/episode.py:1008).
- [episode.py:1392](/home/chia/repos/OpenChia/method_loop/episode.py:1392).
- [scientific.py:413](/home/chia/repos/orbital_workflow/orbital_workflow/scientific.py:413).
- [workflow-error.json:1](/home/chia/repos/orbital_workflow/.artifacts/scenario_02/run-scored-007/model-attempts/attempt-001/workflow-error.json:1).

### A5-F2 — A parsed but invalid action becomes the durable answer for an unchanged resume

**Severity:** medium. **Principles:** 8, 17, 18, 19, 21.

**Evidence:** Verified deterministic current-code cache/admission path; occurrence in stopped 007 is not established.

**Uncertainty:** This concerns action/tool admission, not A3-F3’s independently reported invalid typed upward-report cache. Provider failures and malformed outer model JSON are not successful cache entries in this path.

**1. Requirement and authority.** Explicit principle 18 requires retries to be meaningful: changed input/dependency for deterministic failure, recorded relation between attempts, and no repeated unchanged invalid work. Principle 19 requires reuse keyed to the actual dependency; principle 8 distinguishes returned proposal from admitted/committed acquisition. Persisting a returned proposal for audit is appropriate; automatically treating it as an admitted reusable decision is the mismatch.

**2. Owner.** CachedModels owns response persistence/reuse; Policy and _Source own action admission; resume reconstructs execution through those same consumers.

**3. Trigger.** A completion parses as a JSON object and returns through ModelConnection, but later fails semantic/type/reference/capability action construction or _Source wrapping. For example a well-encoded sim.compare with run_index outside this Episode’s completed runs raises ValueError. A later resume with identical source/configuration and history reaches the identical current request/cache key.

**4. Code path.** models.py:229–239 parses outer JSON and returns it; durable.py:CachedModels.complete:139–163 saves response at 159–160 before returning. scientific.py:355–369 admits only afterwards. durable.py:145–147 returns an existing response without calling a provider; require_compatible_resume:57–64 permits only identical execution identity. run_scientific:374–401 constructs fresh controllers/cache wrappers and replays the same history.

**5. State effect.** The bad proposal is correctly retained, but there is no durable admission/failure marker or correction attempt linked to it. Unchanged resume reconstructs all successful prior acquisitions and then repeats the same deterministic rejection. The bad proposal never becomes a successful scientific unit; valid tool/model caches before it remain reusable. A fresh execution attempt directory alone does not alter the failed proposal’s effective input.

**6. Communication effect.** The responsible Episode again receives no corrective input for these non-parser failures, because F1 unwinds before the next Policy turn. Operator-visible errors repeat. The recorded action cache supplies the same bad response. By contrast, the special encoded JSON feedback loop changes context with field/location/category/proposal_index and therefore can ask for a different proposal without pretending an acquisition occurred.

**7. Credit effect.** No score or yield turn is earned for the rejected action. Replay of prior successes reconstructs their old accounting rather than adding a saved total. The problem is inability to recover the next decision under identical resume, not credit inflation by the failing proposal.

**8. Controller effect.** No new estimator observation is created on each rejection; the active run aborts again. Consequently continuation cannot select useful new work even where its last current band says continue. There is no built-in retry cap here; claiming a hidden cap or recommending one would be unsupported.

**9. Run evidence.** All 429 completed 007 model-cache records correspond to 402 acquisition decisions plus 27 report calls, with no action_request_diagnostic input. The stopped error is external CancelledError while root’s next completion was pending; that failed physical call did not add a model-cache entry. No invalid action-cache poisoning incident is established in 007.

**10. Proposed correction — no edits.** Retain proposal cache records as immutable returned proposals and explicitly record their admission outcome/diagnosis. Reuse completed acquisitions; for a deterministic invalid proposal, route the diagnosed correction through a changed typed request/attempt relation rather than return the identical response as a new attempt. Preserve original cache and failure provenance; do not bypass compatibility by editing scientific records or add an automatic hidden retry count.

**11. Verification needed — not run.** Under future authorization, stop after a validly encoded invalid reference proposal, then continue with unchanged code/settings. Verify the original proposal remains durable, the correction request contains the exact diagnostic and an attempt link, the provider sees changed input, and successful earlier simulations are reused once per original unit without duplicate accounting. Also establish that actual provider/outer-JSON failures remain failed physical attempts rather than poisoned successful cache entries. Not executed here.

**Primary references:**

- [models.py:229](/home/chia/repos/orbital_workflow/orbital_workflow/models.py:229).
- [durable.py:139](/home/chia/repos/orbital_workflow/orbital_workflow/durable.py:139).
- [scientific.py:355](/home/chia/repos/orbital_workflow/orbital_workflow/scientific.py:355).
- [durable.py:57](/home/chia/repos/orbital_workflow/orbital_workflow/durable.py:57).
- [error.json:1](/home/chia/repos/orbital_workflow/.artifacts/scenario_02/run-scored-007/model-attempts/attempt-001/session-0001/call-00021/error.json:1).

### A5-F3 — Conflicting explicit action inputs can be silently ignored or replaced during normalization

**Severity:** low. **Principles:** 2, 9, 10, 17.

**Evidence:** Verified conditional current-code behavior; changed execution from conflicting inputs is not observed in 007.

**Uncertainty:** An explicit initial_state may reasonably own all four state components, and the scenario must own source physics. The defect is that conflicting duplicated inputs have neither a declared conflict rule in the Episode-facing interface nor structured normalization feedback. Do not infer authority to change physical parameters.

**1. Requirement and authority.** Explicit user principles 2 and 10 prohibit infrastructure silently substituting/cancelling an owner’s action and require tracing effective defaults/overrides. Fixed source masses and motion are explicitly problem-owned. The exact precedence for simultaneous vx/vy plus initial_state, or an explicit gravity argument to binary_reference, is an implementer choice and is not established as user-selected.

**2. Owner.** The proposing Episode owns insertion/continuation state and mathematical reference position/time; ScientificBindings owns normalization and scenario injection; the scenario owns gravity. Tools execute the effective normalized request.

**3. Trigger.** For sim.run, arguments include initial_state and a contradictory vx or vy: simulation_arguments pops vx/vy, then setdefault(initial_state, ...) preserves the full state and discards the explicit scalar velocities. For math.numeric binary_reference, an explicit gravity field is unconditionally assigned self.problem[gravity], including a conflicting proposal. In the simulation path explicit conflicting gravity/scenario/window instead raise; this asymmetry makes the mathematical reference silently change a supplied argument. A related normalization edge is trial=True or trial=1.0 after integer trial1 is already cached: Python dictionary equality bypasses generate_forcing’s strict int check, whereas the same supplied type on first use is rejected.

**4. Code path.** scientific.py:189–208 simulation_arguments, especially 195–198 fixed-physics conflict checks, 202 pop velocities and 205 setdefault; scientific.py:266–268 binary_reference gravity assignment; tools.py:numeric_calculation:209–229 consumes effective gravity and reports it. Scientific instructions/tools at 93–99 describe optional initial_state and a scenario binary reference, but do not declare simultaneous-state conflict precedence. tools.py:116–126 stores effective arguments; CachedModels stores the original proposal separately. The trial edge is scientific.py:199–201 dictionary lookup followed by simulation.py:152–156 validation only when generation is needed.

**5. State effect.** The effective request is retained faithfully after normalization, and the original proposal is retained in model cache. Execution can therefore differ from an explicit part of the proposal without a conflict/normalization receipt. No already completed observation is deleted. This is not a scientific quality rejection and does not show that 007 executed an unintended velocity.

**6. Communication effect.** The Episode eventually sees sim.run.initial_state or math.numeric.gravity in its own observations, so effective settings are inspectable after successful work. It does not receive an explicit indication that another supplied value was ignored/replaced or a field-specific correction before executing. The omission differs from intentional defaulting of an absent field.

**7. Credit effect.** Credit follows the executed saved request, not the discarded proposed scalar. A genuine conflict could therefore yield truthful machine credit for different work from one explicit part of the model action. No such changed-credit occurrence is established in 007.

**8. Controller effect.** A successfully normalized operation supplies one ordinary acquisition/continuation observation. The controller has no record that a supplied parameter was cancelled. Fixing this must not create an extra scientific turn solely for routine agreeing normalization.

**9. Run evidence.** Seven of 277 sim.run proposals in 007 supply both initial_state and vx/vy. All seven agree numerically; none demonstrates unintended substitution. The one binary_reference proposal supplies time=0, position=[1,0], and no gravity. Its scenario injection is intended and correct. The conditional conflicting-input defect is current-code evidence only. All 277 actual sim.run proposals use integer trial selectors; no path-dependent type acceptance is established in 007.

**10. Proposed correction — no edits.** Give one declared owner/representation to each state input. Either document and surface a single explicit precedence or return a field-specific ambiguity diagnostic when duplicated inputs disagree; agreeing duplicates can normalize once. For scenario-owned reference gravity, inject only as declared context and explicitly diagnose an attempted conflict, matching the simulation path’s fixed-problem ownership. Preserve original proposal plus effective settings, without permitting alternative source physics or adding an output-quality gate. Validate the trial selector consistently before the forcing-cache lookup; this preserves the existing exact integer reference contract and does not add a scientific gate.

**11. Verification needed — not run.** Future authorized focused checks should submit agreeing and conflicting dual state inputs, a normal binary_reference with omitted gravity, and a conflicting explicit gravity. Establish exact proposed/effective values, a clear diagnostic or declared precedence, one actual operation, and alignment of saved request, Episode feedback and credit. Confirm 007’s agreeing proposals retain their same physical meaning. No tools or tests were run here. Compare invalid selector types before and after the valid integer trial is cached; behavior should depend on the declared type contract rather than cache state.

**Primary references:**

- [scientific.py:189](/home/chia/repos/orbital_workflow/orbital_workflow/scientific.py:189).
- [scientific.py:266](/home/chia/repos/orbital_workflow/orbital_workflow/scientific.py:266).
- [tools.py:209](/home/chia/repos/orbital_workflow/orbital_workflow/tools.py:209).
- [2ed6740575d2e621d5ff521dd11d3fd77da8df10afda8de4bf97c54c3398ce5f.json:1](/home/chia/repos/orbital_workflow/.artifacts/scenario_02/run-scored-007/model-cache/2ed6740575d2e621d5ff521dd11d3fd77da8df10afda8de4bf97c54c3398ce5f.json:1).
- [2399a7e89465ff4128b30e196518075d450b1c6b1e5715af90f9e5c9c53f7af0.json:1](/home/chia/repos/orbital_workflow/.artifacts/scenario_02/run-scored-007/model-cache/2399a7e89465ff4128b30e196518075d450b1c6b1e5715af90f9e5c9c53f7af0.json:1).

### A5-Q1 — Which solver failures represent a valid scored prefix, and which represent an unscored operation?

**Severity:** policy_question. **Principles:** 6, 7, 10, 16, 17.

**Evidence:** Verified code behavior; authorization/semantic question. No solver_error in stopped 007.

**Uncertainty:** Finite partial integration is real observed work and must not be erased. The user’s no-gate rule does not authorize converting all solver errors into rejection, nor does a returned finite array by itself settle whether the configured scientific measurement remains valid.

**1. Requirement and authority.** Explicit user requirements preserve valid partial contributions and distinguish failure/no observation from an actual score of zero. The simulator supplies the agreed recurrence score without a quality gate. Neither the indexed requirements nor inspected code supplies an explicit user decision about scoring a finite numerical prefix after solve_ivp reports failure.

**2. Owner.** The simulation binding owns interpreting solver outcomes and the validity/domain of its measurement; the user owns problem/score semantics. Episode and controller must consume that declared meaning rather than infer it from success labels.

**3. Trigger.** solve_ivp returns solution.success=False after producing finite saved samples. integrate marks outcome=solver_error and returns a Trajectory. Trajectory.summary nevertheless runs measure_persistence and returns its numerical score, which project_observation/BestScoreCredit can credit. If solve_ivp or measurement instead raises, F1 applies and there is no scored acquisition.

**4. Code path.** simulation.py:242–266 handles returned solver status; Trajectory.summary:123–149 computes score independent of outcome; tools.py:_run:128–147 records arrays/summary; credit.py:55–70 projects all sim.run results and BestScoreCredit.observe:115–133 consumes finite nonnegative scores without an outcome gate. persistence.py:55–63 enforces measurement shape/finite/increasing-time validity.

**5. State effect.** Finite returned solver-error prefixes would be saved with outcome/message and retained as ordinary simulation observations. Exceptions before summary produce no sim.run observation, though some immutable inputs or arrays may already exist. A partial prefix is not represented as a completed requested horizon: requested_interval and observed_interval remain separate.

**6. Communication effect.** A returned solver_error reaches own_tool_observations with outcome, actual observed interval and solver_message. A thrown error reaches no later Episode input (F1). Closed parent projections drop solver_message from compact machine summaries but report composers see original local findings; typed parent fields are parent-selected.

**7. Credit effect.** A finite solver-error prefix can increase local/root best score if otherwise eligible; no outcome filter suppresses it. A thrown failure supplies no score. An actual completed trajectory can validly measure zero. Whether every solver-error prefix supports the same numerical score is the unresolved policy, not proof of wrong credit in 007.

**8. Controller effect.** A returned finite solver_error would be one completed tool acquisition and one marginal-credit yield observation; an exception would be none. The current estimator explicitly conditions on completed acquisitions and has no failed-attempt probability model.

**9. Run evidence.** All 277 saved sim.run acquisitions in 007 terminate by horizon, outer exit or collision; none has solver_error. Thirty-six have score=0 and are retained as completed scored observations. Example unit_05570c0d... has outer_exit at 3.3964317702869558 with score=0. No numerical integration or reproduction was performed for this question.

**10. Proposed correction — no edits.** Specify the measurement meaning for a returned finite solver-failure prefix and preserve outcome/observed-domain uncertainty. If the measurement is defined for that prefix, retain its genuine score and do not reject it merely for solver status. If the numerical work cannot define the measurement, represent no score and the operational diagnostic explicitly, preserving usable partial data. Do not default to a new solver-agreement threshold or silently relabel absence as zero.

**11. Verification needed — not run.** A future authorized diagnostic should inspect one genuinely finite failed-solver prefix and one thrown integration error against the agreed score domain, then trace saved samples, reported interval/status, any score and resulting local/parent accounting. It must establish actual measurement validity, not only exercise the status branch. Not run.

**Primary references:**

- [simulation.py:242](/home/chia/repos/orbital_workflow/orbital_workflow/simulation.py:242).
- [simulation.py:123](/home/chia/repos/orbital_workflow/orbital_workflow/simulation.py:123).
- [tools.py:128](/home/chia/repos/orbital_workflow/orbital_workflow/tools.py:128).
- [credit.py:115](/home/chia/repos/orbital_workflow/orbital_workflow/credit.py:115).
- [persistence.py:55](/home/chia/repos/orbital_workflow/orbital_workflow/persistence.py:55).
- [unit_05570c0d4be36658b370a67d2b2c6b1d641927a44f6a546105422143fe32dbe4.json:1](/home/chia/repos/orbital_workflow/.artifacts/scenario_02/run-scored-007/episodes/units/unit_05570c0d4be36658b370a67d2b2c6b1d641927a44f6a546105422143fe32dbe4.json:1).

### A5-Q2 — Provider inactivity and retry ownership are not specified by this orbital adapter

**Severity:** policy_question. **Principles:** 1, 10, 16, 18, 23.

**Evidence:** Verified adapter behavior; unresolved external-provider configuration/recovery boundary.

**Uncertainty:** No timeout/retry requirement is inferred. The audit did not inspect or execute the ambient Codex binary’s internal provider policy. OpenChia launch-policy documentation describes a different broker path and cannot silently become this direct app-server adapter’s runtime guarantee.

**1. Requirement and authority.** Explicit principles 1, 10, 16 and 18 require provenance for timeout/retry/stop rules and separation of transient failures, deterministic invalid results and external interruption. The explicit user model choices are FAST=gpt-6-luna/none and REASONING=gpt-6-sol/medium through the existing connection. No indexed user instruction specifies a new orbital model timeout, retry count, fallback or provider health probe.

**2. Owner.** ModelConnection/_SessionConnection own direct app-server protocol and owned subprocess cleanup. The invoked Codex app-server owns any internal provider transport behavior. The scientific Episode owns work selection, not provider account/model fallback.

**3. Trigger.** The provider is silent during initialize/thread/start/turn/start or event reading, closes transport, returns an RPC error, produces a failed turn, or attempts an unbound model-side capability. Silence can leave awaits pending; explicit errors raise. External cancellation takes the ordinary exception-cleanup path.

**4. Code path.** models.py:_read:96–100 awaits stdout without wait_for; _rpc:102–112 awaits the matching RPC; complete:179–239 waits for matching turn completion, preserves local request/events/error and raises on failure. Model/effort mismatch raises at 161–167. The only adapter wait_for is process teardown:69–90 (3 seconds after SIGTERM then SIGKILL). ModelConnection:275–284 creates one worker per Episode/role and contains no call retry or fallback. study.toml and run study.toml declare the command and roles, with no provider timeout/recovery fields.

**5. State effect.** A failed physical call has request/error records and any received event stream but no successful CachedModels record. Silence leaves the action unacquired and the run pending; explicit failure unwinds as F1. A new physical attempt may be possible on resume because there was no successful cache response. No frozen source-code/library identity can establish an unrecorded remote backend policy.

**6. Communication effect.** On explicit failure the operator gets ModelCallError/type/message and native event/error records; the active scientific Episode receives no new structured diagnostic (F1). Silence has no adapter-generated failure message. Native unexpected tool/request types are interrupted/rejected to preserve declared execution ownership.

**7. Credit effect.** Neither provider silence nor a failed call invents a score or credit. Earlier completed work remains cached and durable. A retry, if externally undertaken, must not duplicate completed acquisitions.

**8. Controller effect.** No yield/stop event occurs while awaiting an unfinished model action. This is neither a numerical stop nor goal completion. The adapter contains no hidden retry cap, model fallback or side-probe chooser. Any native Codex internal behavior is not established by inspection of this wrapper.

**9. Run evidence.** 007 has 429 cached successful model responses, routed 402 REASONING decisions and 27 FAST reports. Its sole saved model call error is CancelledError at session-0001/call-00021, paired with the user SIGINT record; no explicit provider failure or timeout is evidenced. Retirement records and STOPPED_STATE report no live owned provider process groups after stop.

**10. Proposed correction — no edits.** Record the effective external connection/runtime and its supported policy as provenance, and resolve whether pending requests intentionally remain unbounded/cancellable or use an explicitly owned health/recovery policy. If a policy is chosen, distinguish failed requests from silent pending calls and deterministic cached invalid outputs; retain attempt relations and original diagnostics. Do not import another component’s defaults or invent timeout, retry, budget, fallback or probing behavior from this unresolved question.

**11. Verification needed — not run.** Future authorized verification should use the real configured connection to establish behavior for a failed request, a silent pending call, and an external interrupt, tracing physical attempts, response cache, provider cleanup and no acquired turn before response. The user’s intended policy must be known before asserting a particular retry/deadline is correct. No connection or live probe was made for this audit.

**Primary references:**

- [models.py:96](/home/chia/repos/orbital_workflow/orbital_workflow/models.py:96).
- [models.py:179](/home/chia/repos/orbital_workflow/orbital_workflow/models.py:179).
- [models.py:69](/home/chia/repos/orbital_workflow/orbital_workflow/models.py:69).
- [durable.py:159](/home/chia/repos/orbital_workflow/orbital_workflow/durable.py:159).
- [error.json:1](/home/chia/repos/orbital_workflow/.artifacts/scenario_02/run-scored-007/model-attempts/attempt-001/session-0001/call-00021/error.json:1).
- [episode_launch_configuration.md:280](/home/chia/repos/OpenChia/docs/openchia/episode_launch_configuration.md:280).

## Verified defects

- **A5-F1:** Legitimate request/capability/execution failures outside the encoded-JSON correction path abort all active Episodes without actionable local failure delivery.
- **A5-F2:** Parsed invalid actions are cached before admission, so unchanged resume deterministically repeats their rejection.
- **A5-F3:** Conflicting explicit state/reference inputs can be silently ignored/replaced; no conflicting007 execution is established.
- A3-F3’s report-admission/cache failure is related and independently checked, but remains one finding owned by A3.

## Unresolved questions

- **A5-Q1:** Whether a finite solver-error prefix is a valid score on its observed domain or an unscored operation must be declared. There is no007 solver-error occurrence.
- **A5-Q2:** The intended provider inactivity/recovery policy and external app-server defaults are not established by this adapter. No new timeout, retry count or probe is authorized by this question.
- A2-Q03 owns numeric continuation-cost/quasi-likelihood provenance; A2-Q01 owns shortened-horizon root eligibility. They are not reclassified as hidden gates here.

## Mechanisms checked and working correctly

- The real generic OpenChia loop has no bound/safety_bound fields or bound_hit stop path. Nano’s optional bound at episode.py:789,1104–1180 is not imported. The orbital live Policy has no model stop action: every selection is a declared tool/child, and numerical continuation owns yield_stop. Explicit simparts recursion is declared without a runtime depth/turn limit.
- Core exhaustion is source.next→None; source failure is SourceEnd(source_failed); numeric stop is yield_stop; a root requested epoch transition without a valid mutation is incomplete. These are distinct code paths in OpenChia episode.py:1330–1419. Scientific Policy currently produces neither None nor SourceEnd and requests_transition is always false in CreditStep, so source exhaustion/source_failed/incomplete are available generic vocabulary, not observed live-scientific explanations.
- 007’s 27 closed Episodes are yield_stop, not success claims. The live root was still numerically continuing. Actual SIGINT/CancelledError interrupted the pending21st root decision after20 committed turns. Root record/summary were not fabricated. The audit’s paused persistent goal is an external user decision and is not the workflow estimator’s completion output.
- Successful simulations return their score independently of exit/collision/horizon category. Of277 actual acquired simulations,36 score exactly0 and remain committed. Math/comparison observations carry no fabricated simulation score. This preserves the no-score-versus-zero distinction at the normal acquisition boundary.
- Malformed encoded action JSON is handled before an Acquirable exists and generates changed correction context including deterministic proposal_index, field/index and parser location. It neither repeats a tool nor earns a turn. No arbitrary retry cap is present. All completed007 proposals parse without this repair path.
- Outside-window diagnostic and arithmetic expression/domain diagnostics retain their explicit cause and inputs as local observations with no simulation score. Lean unavailable/nonzero-exit output is optional diagnostic evidence. These are checked current-code mechanisms;007 has no failure/window/Lean occurrence, so working behavior here is inspection-level evidence only.
- Transient/provider/outer-JSON failure does not populate a successful CachedModels entry; requests/events/errors survive. The adapter does not implement hidden retries, role fallback, account hopping or a provider-driven scientific acquisition. Native unexpected tools/requests are blocked by explicit execution ownership. External cancellation cleans up owned workers; STOPPED_STATE reports none alive.
- Cache success reuse verifies all referenced artifact bytes; strict execution identity prevents a changed source/config/library binding from silently replaying old numerical credit. Fresh controllers replay completed work without adding stored totals. A5-F2 is the narrower distinction between cached returned proposal and an admitted decision, not evidence that every cache/replay is defective.
- Unidentifiable/insufficient estimator output remains a coded status, not a zero-yield scientific observation or stop. Current normal-band upper controls stopping with recorded cost, with no prior prediction/EWMA/controller memory. Optimizer inner numerical iteration bounds do not create simulation acquisition turns. A2 owns deeper estimator/credit findings.
- Orbital binds no Leaf.accept callback. Generic support for acceptance or GoalState commitment is not evidence of an active scientific gate here. Removed support/anchor/qualification/EWMA mechanisms have no live failure/config/controller consumer in the inspected primary path; no fake placeholders or hidden legacy acceptance test were found. Parent type/identity checks remain operative by explicit requirement.
