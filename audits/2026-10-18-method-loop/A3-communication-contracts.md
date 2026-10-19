# A3 — Communication contracts

Read-only stopped run-scored-007; persistent scientific goal remains paused. Only these two assigned audit artifacts were written. No model/simulator calls, workflow imports/execution, replays, fits or tests were run.

Latest user requirements override historical documents; BRIEF.md is an index, not approval evidence.

Final stopped evidence: 27 closed child reports (19 SIM, 7 simparts, 1 MATH), 20 committed root acquisitions, 429 completed model calls (402 acquisition decisions + 27 typed FAST composers). The root has no closed summary. Its final subsequent model request was cancelled before a response.

The representation boundary works on the inspected prefix. Concrete report truth and observation provenance do not consistently match the machine evidence. These are separate conclusions.

## Scope and source ownership

Read complete current relevant source functions/files and both actual method_loop designs; read original episodic_workflow guards/projection/parser. Analyze immutable primary JSON records with Python 3 -B and standard-library arithmetic only. Prior 007 reviews were used as discovery leads, never as proof of row truth. Primary bounded semantic inspection includes SIM8 and late SIM14-19; this is not exhaustive semantic certification of all 27 reports.

| Source | Actual role |
| --- | --- |
| OpenChia | Actual imported core; parent-owned ClosedRecord/ReportContract/ChildEpisodeUnit and separate numerical/report projections. Core permits broader JSON values; orbital binding adds restricted recursive types. |
| nano-graphrag | Read-only source comparison; compact messages include result/prompt_context/output, no current ReportContract. Not imported as orbital runtime. |
| episodic_workflow | Original communication.py current sha256 357d4ee021d55b645318f296d1c86fab8c3100d7adf8a3f0f64eb5208c288005 equals documented revision 6578c49add92cfe1fb713a64a6d4635fb1c76509; current checkout HEAD is 92af787b292530c9f4ceee7dac70cbf481f0aad6. Original ResearchSource.parent_report explicitly separates source/target identities and performs record-derived number/enum/unit/relationship projection; these disease-specific semantic rules were not copied wholesale into orbital. |

The JSON companion records all 27 exact report/composer/result links and current/frozen source hashes. All 19 source files checked here are byte-identical to the 007 snapshot. No completion claim follows from this stopped prefix.

## Findings

### A3-F1 — Model-facing run observations omit forcing-trial provenance; actual reports invent or swap trial labels

**Severity:** high. **Principles:** 4, 9, 17, 19, 20, 21, 24, 25.

**Evidence:** Verified current-code defect and actual stopped-007 communication errors; no simulator-control defect established.

**Uncertainty:** Observed false labels are certain for the cited records. Missing metadata is a plausible contributor; the audit does not claim it is the sole cause of every model error.

**1. Requirement and authority.** Latest user principles 9, 20 and 21; central invariant quoted in BRIEF.md: Actual progress, recorded state, communication to the responsible episode, and credit assignment must describe the same work. Parent SIM14 requests trial-resolved measurements; SIM19 objective explicitly requests each requested trial index. **Authority status:** Explicit user requirement and explicit saved parent contracts; inference only for causal contribution of metadata omission.

**2. Owner.** ScientificBindings owns request-to-observation projection and model input delivery; the FAST composer owns the asserted trial labels; the parent owns which fields to request.

**3. Trigger.** A run uses an explicitly selected forcing trial, and a later decision or requested upward row needs to distinguish that trial from the local run_index. simulation_arguments removes trial in favor of a forcing artifact; Trajectory.summary returns neither trial nor forcing seed. project_tool forwards that summary, while the composer receives result.findings only.

**4. Code path.** scientific.py:189-208 simulation_arguments; simulation.py:123-149 Trajectory.summary and 152-170 generate_forcing (seed=20261005+trial); scientific.py:231-252 project_tool; scientific.py:285-301 synthesize; scientific.py:323-348 Policy.next; credit.py:73-93 trajectory_evidence; models.py:275-284 per-role worker creation.

**5. State effect.** Saved machine Evidence retains forcing_seed and raw requests retain forcing_id. Model-facing own_tool_observations and fresh composer observations retain initial_state, local run_index, score and numerical settings but omit the row-wise forcing-trial/seed link. Recorded report rows can therefore contradict authoritative machine provenance without changing it.

**6. Communication effect.** SIM14 reports the [0.2,-1.2] score 0.0004787638584971068 as trial 1, whereas its unit Evidence has seed 20261007, i.e. trial 2; its collision counterpart is mislabeled trial 2 although seed 20261006 is trial 1. Five of its ten row labels disagree with saved seeds. SIM19 reports trial_index 1..10, while all ten runs have seed 20261006 (trial 1): nine false labels. The exact SIM19 report reached final root call-00021; that root call was cancelled before any response.

**7. Credit effect.** None from the false strings/integers themselves: parent credit consumes compact machine Evidence, never these report fields. SIM14/SIM19 did not raise the root historical maximum of 0.3574559702785158. The responsible model nevertheless receives scientific rows inconsistent with the machine inputs that accounting used.

**8. Controller effect.** The numerical continuation controller consumes recorded machine marginal credit, so report trial labels do not directly change its stop statistic. Scientific action selection can change: after SIM17 reproduced a collision at [0.2,-1.2], the root explicitly commissioned SIM18 to resolve an apparent forcing-trial mismatch, citing the earlier swapped labels. This demonstrates actual extra investigation prompted by false provenance; it does not establish faulty forcing control.

**9. Run evidence.** Primary checks linked all 27 closed reports to their own FAST cache response, exact saved assignment/contract, and exact result.findings. SIM14 composer cache 2776db... lacks trial metadata. SIM19 composer f37f1c... likewise lacks it. SIM18 raw requests/seeds show consistent selection of trials 1/2, and its nullable reported_trial_index values correctly remain null. Its trial_mapping=swapped interpretation is not proof that the simulator swapped anything. The following root itself notes the matched data do not establish a consistent swap.

**10. Proposed correction — no edits.** Carry typed requested_trial_index and executed forcing_seed (or an equivalent non-audit scientific trial key) alongside each own-run observation when ScientificBindings still knows the selected trial. Include that same row-wise metadata in the saved result.findings and composer input, preserving run_index as a distinct local acquisition index. When the parent requests trial identity, project it from that recorded metadata rather than infer it from row order or prior labels. Preserve exact parent-selected fields and audit-identity guards; do not expose raw child records, artifact IDs, or add a freeform report field. Historical false reports remain immutable and are identified as such in human findings.

**11. Verification needed — not run.** On a separately authorized future run, request trials 1/2/3 in a deliberately nonsequential order, repeat a cached request, and verify that proposed trial, executed seed, own observation, contracted trial field, parent input and machine Evidence agree. Verify that run_index remains acquisition order, that no extra simulation/yield turn is minted for metadata, and that a missing identifier uses only a contract-permitted unknown rather than an invented label. This verification was not run.

**Primary references:**

- [request translation and forcing ownership](/home/chia/repos/orbital_workflow/orbital_workflow/scientific.py:189).
- [own observation projection](/home/chia/repos/orbital_workflow/orbital_workflow/scientific.py:231).
- [composer input](/home/chia/repos/orbital_workflow/orbital_workflow/scientific.py:285).
- [summary fields omit trial/seed](/home/chia/repos/orbital_workflow/orbital_workflow/simulation.py:123).
- [trial-to-seed definition](/home/chia/repos/orbital_workflow/orbital_workflow/simulation.py:152).
- [machine provenance](/home/chia/repos/orbital_workflow/orbital_workflow/credit.py:73).
- [SIM14 false trial-1 label](/home/chia/repos/orbital_workflow/.artifacts/scenario_02/run-scored-007/episode-store/episodes/episode_0892c3c72be9696fdbeca1ca94fbc2e83c7fd7e3d96c98a58583b5ade97b77b7/parent-report.json:57).
- [same SIM14 measurement seed 20261007](/home/chia/repos/orbital_workflow/.artifacts/scenario_02/run-scored-007/episodes/units/unit_df49f886d027552232843cb47f4e2086d498a28aea1a451e02190a75c3bfb4d9.json:427).
- [SIM19 second row wrongly calls run index 2 a trial](/home/chia/repos/orbital_workflow/.artifacts/scenario_02/run-scored-007/episode-store/episodes/episode_aa7f08b68916f69e7fce77ac8ddc3cb1877a014d60d27223bb396d00581f26fa/parent-report.json:19).
- [same SIM19 run seed 20261006](/home/chia/repos/orbital_workflow/.artifacts/scenario_02/run-scored-007/episodes/units/unit_2d7bb70741caa4b26619d6eeeb29c0de56525b47d4401b5a52be51dd7bd1f8af.json:331).
- [SIM14 exact composer observations](/home/chia/repos/orbital_workflow/.artifacts/scenario_02/run-scored-007/model-cache/2776db24b0c6aa252ce2a9afc53bf500db85cb187b1c0b067298a3232272ac79.json:144).
- [SIM19 exact composer observations](/home/chia/repos/orbital_workflow/.artifacts/scenario_02/run-scored-007/model-cache/f37f1c9bcbc9aa4a0ee74d7c39079058d96f7181a122abb2b152b70d3254bc27.json:139).
- [root explicitly commissions mismatch investigation](/home/chia/repos/orbital_workflow/.artifacts/scenario_02/run-scored-007/model-cache/6052266f2693bc3927e62d15049572b274158024f9674a79d76fc7826ce76a82.json:3357).
- [last root input includes false SIM19 trial labels](/home/chia/repos/orbital_workflow/.artifacts/scenario_02/run-scored-007/model-attempts/attempt-001/session-0001/call-00021/request.json:3539).
- [no subsequent completed root decision](/home/chia/repos/orbital_workflow/.artifacts/scenario_02/run-scored-007/model-attempts/attempt-001/session-0001/call-00021/error.json:1).

### A3-F2 — Valid typed reports misassociate recorded measurements and contradict their own requested best-value relationships

**Severity:** high. **Principles:** 4, 5, 6, 9, 20, 21, 24, 25.

**Evidence:** Verified factual report errors in stopped 007, distinct from a structural admission defect or a wrong simulation measurement.

**Uncertainty:** Specific numeric associations and maximum comparisons are established from saved records. The counterfactual effect on future discovery/optimum is not established. Arbitrary qualitative enums are not treated as demonstrably false without a defined observational basis.

**1. Requirement and authority.** Latest user principles 9, 20 and 21. Saved parent meanings explicitly define measured candidate velocity/score/outcome and highest-scoring local velocity/score. The typed boundary cannot by itself establish these scientific relationships. **Authority status:** Explicit parent-contract meaning and explicit user synchronization requirement; no invented scientific acceptance threshold.

**2. Owner.** The binding synthesis in ScientificBindings.child owns evidence interpretation; parent declarations own requested meanings. The generic method owns representation/admission and delivery, not scientific truth.

**3. Trigger.** The independent FAST composer recopies measurements and computes a best field, while local admission checks shape, enums, finite values and known identities only. A schema-valid value can belong to a different run, or a best field can disagree with the valid table in the same report.

**4. Code path.** scientific.py:270-310 child/project/synthesize; communication.py:152-168 validate_report, 232-238 ParentReport, 268-282 final model-input guard; OpenChia/method_loop/episode.py:1524-1573 child completion and report admission; credit.py:115-133 machine score assignment.

**5. State effect.** The exact inaccurate composer output is admitted, persisted as parent-report.json and stored in the parent acquisition alongside numerically correct machine Evidence. No assertion in the composer changes the immutable simulation observations.

**6. Communication effect.** SIM8 swaps the first two candidate velocity associations and reports several nonzero vx runs as vx=0; for example the score 1.0688757651245246e-281 at vy=1.3975424859373684 is returned under vy=1.4364307617610164. Seven returned row velocity associations and three outcome codes are wrong in this inspected report. Its best score belongs to vx=0.05, but best_observed_velocity says vx=0. SIM17 reports best_local_score=8.793796938194116e-67 at [0.2,-1.202], although its own correctly copied row has 5.691136865141231e-25 at [0.199,-1.201], the actual maximum among its ten runs. The higher value and velocity were present in the composer input.

**7. Credit effect.** Machine Evidence and BestScoreCredit remain independent of these report errors; no incorrect model claim earns extra credit. Conversely, correct numerical credit is not evidence that the parent was accurately informed. For SIM17 all scores are below the root historical maximum, so root credit remains 0.3574559702785158.

**8. Controller effect.** No direct effect on the numeric yield/continuation rule. The actual next root decision after SIM8 receives its inaccurate report and chooses outward-biased insertions; the audit cannot isolate the counterfactual action under a corrected table. The actual next root input after SIM17 contains the false best fields unchanged; its ensuing decision addresses the separate trial-label discrepancy.

**9. Run evidence.** SIM8 composer 3649ef... includes exact saved velocities and scores; report and next root cache be75d... preserve the inaccurate output. SIM17 composer 0822e... includes all ten exact saved own observations; report and next root cache 605226... preserve the wrong best pair. These are actual completed returned reports, not hypotheses or tests of simulator truth.

**10. Proposed correction — no edits.** Give contractual scalar copying, run association and explicit maximum/minimum relationships one faithful projection from recorded work. Keep parent field/type selection, and use explicit binding-supported semantic projections or source-row mappings rather than infer arbitrary field meaning from its name. Preserve subjective interpretation/uncertainty as separately declared typed fields produced by the existing work reasoning where possible. If a typed composer remains authorized, it should not independently reassign already recorded fact tuples or recompute simple exact relationships inconsistently. Retain malformed/incorrect proposals and exact diagnostics; do not add a scientific quality gate or discard valid measurements.

**11. Verification needed — not run.** On future authorized component/live verification, request distinct reports containing close velocity values, scientific-notation scores with widely separated exponents, a requested best pair, and multiple outcome types. Check association against saved runs and best fields against the stated table/scope, then inspect actual next-parent input and decision. Confirm that a valid but erroneous interpretation is recorded honestly and earns no machine credit. No model call, replay, test or fit was run for this audit.

**Primary references:**

- [binding owns model synthesis](/home/chia/repos/orbital_workflow/orbital_workflow/scientific.py:285).
- [representation validator](/home/chia/repos/orbital_workflow/orbital_workflow/communication.py:152).
- [delivery rechecks types/identity](/home/chia/repos/orbital_workflow/orbital_workflow/communication.py:268).
- [generic boundary admits synthesis](/home/chia/repos/OpenChia/method_loop/episode.py:1524).
- [separate numerical credit](/home/chia/repos/orbital_workflow/orbital_workflow/credit.py:115).
- [SIM8 wrong velocity association](/home/chia/repos/orbital_workflow/.artifacts/scenario_02/run-scored-007/episode-store/episodes/episode_dc2ebe76cef003960039ecd643e6337293e7ed55dca428f0ec126ca03128d089/parent-report.json:9).
- [SIM8 correct source observation in composer input](/home/chia/repos/orbital_workflow/.artifacts/scenario_02/run-scored-007/model-cache/3649ef8aa600e7f0535f958d80f1ed220ea060f0353d00d7506092a2c06c8666.json:299).
- [original saved SIM8 observation](/home/chia/repos/orbital_workflow/.artifacts/scenario_02/run-scored-007/objects/artifact_42e2d6eb3c0f76e9801341f3375154468d2cb01b54dfe358276363605443a3af.json:1).
- [SIM17 false best pair](/home/chia/repos/orbital_workflow/.artifacts/scenario_02/run-scored-007/episode-store/episodes/episode_393cb2ef975d052d716b63668107d3c0860dfe04e07a6873d5adb87064245d64/parent-report.json:2).
- [higher score in same returned table](/home/chia/repos/orbital_workflow/.artifacts/scenario_02/run-scored-007/episode-store/episodes/episode_393cb2ef975d052d716b63668107d3c0860dfe04e07a6873d5adb87064245d64/parent-report.json:45).
- [corresponding recorded SIM17 observation](/home/chia/repos/orbital_workflow/.artifacts/scenario_02/run-scored-007/episodes/units/unit_419a8416d914b785e08318921a8c1023c254e0da03be8c409098769bce1c059d.json:153).
- [SIM17 correct input observation](/home/chia/repos/orbital_workflow/.artifacts/scenario_02/run-scored-007/model-cache/0822e2c634ef7038331341fef5180d7ae15c505c3ca10e3fe3a66306d4de50f0.json:1051).
- [wrong SIM17 best fields reach root](/home/chia/repos/orbital_workflow/.artifacts/scenario_02/run-scored-007/model-cache/6052266f2693bc3927e62d15049572b274158024f9674a79d76fc7826ce76a82.json:1494).

### A3-F3 — Upward representation failure aborts the ancestor call stack without actionable Episode feedback

**Severity:** medium. **Principles:** 4, 7, 17, 18, 20, 21.

**Evidence:** Verified current-code failure path; occurrence in stopped 007 is not established.

**Uncertainty:** All 27 completed 007 reports succeeded structurally. This is an inspected reachable behavior, not a claim the stopped run ended for it; that run ended on user cancellation.

**1. Requirement and authority.** Latest user principles 17 and 18 require useful structured failure feedback and retained valid partial work. Principle 20 separately authorizes exact type/identity representation enforcement. OpenChia episode_communication.md describes synthesis/admission ownership but does not authorize silently turning malformed communication into scientific rejection. **Authority status:** Explicit failure/representation requirements; proposed recovery design is an implementation recommendation.

**2. Owner.** The binding owns synthesis failure interpretation; ChildEpisodeUnit and DurableWorkflow own integration/lifecycle; the responsible parent Episode owns the subsequent action.

**3. Trigger.** validate_report raises on malformed composer output, or report admission rejects a known child audit identity after the child has closed. ScientificBindings.synthesize has only a finally-release clause; ChildEpisodeUnit._finish_async and StoredChildEpisodeUnit.acquire_async do not convert the exception into an Episode-visible structured result.

**4. Code path.** scientific.py:285-308 synthesize; communication.py:152-168 validation and 241-265 identity guard; OpenChia/method_loop/episode.py:1524-1573 _finish_async/acquire_async; archival.py:74-88 acquire_async/_archive; scientific.py:413-419 top-level error; storage.py:126-165 close/finish boundaries.

**5. State effect.** Child local units and the full closed trace have already been saved. The result/report archive is finalized only after successful synthesis/admission. Failure unwinds the acquisition before the parent _append_record, so there is no committed parent acquisition or parent credit/yield turn for that child; manifest can remain closed with result_file/parent_report_file absent. Valid local evidence survives on disk.

**6. Communication effect.** The active parent receives an exception through infrastructure, not a typed status identifying the affected contracted field and recoverable child evidence. The top-level workflow-error.json receives exception type/message/counters; no later Episode decision consumes a structured diagnostic. Identity errors are generic ValueError messages, with no field location.

**7. Credit effect.** Valid child local evidence remains durable. It is not integrated into parent credit on the failing invocation. The audit does not recommend crediting a malformed report or fabricating a completed parent turn.

**8. Controller effect.** Parent continuation never receives the unfinished acquisition. The exception aborts all active ancestors rather than returning an honest recoverable/incomplete communication state. Re-execution can reuse the same cached invalid composer response because its request key is unchanged; there is no report-correction feedback/attempt relation in this path.

**9. Run evidence.** No such failure among 27 final stopped reports; their exact successful report links were inspected. The top-level 007 failure is CancelledError from the user stop. The failure path follows current and frozen-identical source directly and is not presented as end-to-end reproduction.

**10. Proposed correction — no edits.** Record report composition/admission as an explicit pending/failed/delivered boundary tied to the completed child evidence. Send the responsible Episode a separate typed operational diagnostic identifying the contract field/category and preserved completed work, or use only parent-predeclared unknown/failure states where available. Any format correction must change the diagnosed output/input and record an attempt relation; it must not rerun completed scientific acquisitions, reuse the identical invalid cached response as a meaningful retry, add a hidden retry budget or weaken exact contracts. Commit parent accounting and its contracted report coherently once integration succeeds; make unresolved operational termination explicit.

**11. Verification needed — not run.** On a separately authorized future failure-path experiment, have a completed child produce one wrong numeric type and one known audit identity. Establish that local observations remain durable, parent accounting has no phantom duplicate turn, the affected contract field is visible to the responsible Episode, and a changed correction/recovery can reuse completed work. Establish honest terminal status when recovery is unavailable. No such experiment was run here.

**Primary references:**

- [no synthesis error-to-Episode diagnostic](/home/chia/repos/orbital_workflow/orbital_workflow/scientific.py:285).
- [field-specific type error](/home/chia/repos/orbital_workflow/orbital_workflow/communication.py:152).
- [identity rejection](/home/chia/repos/orbital_workflow/orbital_workflow/communication.py:241).
- [failure before admitted update](/home/chia/repos/OpenChia/method_loop/episode.py:1544).
- [parent append occurs only after acquire returns](/home/chia/repos/OpenChia/method_loop/episode.py:1421).
- [archive only after successful acquire](/home/chia/repos/orbital_workflow/orbital_workflow/archival.py:74).
- [closed versus delivered lifecycle](/home/chia/repos/orbital_workflow/orbital_workflow/storage.py:126).
- [unchanged composer request reuses cached response](/home/chia/repos/orbital_workflow/orbital_workflow/durable.py:139).
- [top-level operational error record](/home/chia/repos/orbital_workflow/orbital_workflow/scientific.py:413).

### A3-Q1 — A separate typed FAST synthesis callback is real; the evidence does not establish that it violates the ban on a separate freeform summarizer

**Severity:** authorization_question. **Principles:** 1, 4, 5, 20.

**Evidence:** Verified architecture and count; unresolved authorization interpretation.

**Uncertainty:** The user explicitly requested FAST reporting earlier, and the latest wording forbids a separate freeform summarization call while instructing use of the existing work call. The implemented extra call is typed, not freeform. Do not assume either historical documentation or any second call alone resolves this.

**1. Requirement and authority.** Latest user principle 20 supplied by parent: Use the existing work call to gather required information. Do not add a separate freeform summarization call. Earlier user requirement selects FAST report composition. OpenChia episode_communication.md:54-67 specifies a synthesis callback, not a required extra model dispatch. **Authority status:** Explicit user requirements; scope of any conflict is unresolved, not inferred permission for new restrictions.

**2. Owner.** Parent chooses contract; binding implements synthesis; the user owns model-call architecture authorization. The generic method requires a callback but can accept a pure projection.

**3. Trigger.** Every completed scientific child enters ScientificBindings.child.synthesize, which launches a fresh report-* FAST completion after all child acquisitions, using the completed result.findings.

**4. Code path.** scientific.py:285-308; models.py:275-284; OpenChia/method_loop/episode.py:1438-1455. Earlier source ResearchSource.parent_report constructs a structured report directly from work records rather than launching a summarizer.

**5. State effect.** Stopped 007 has 27 completed extra typed report calls, separately cached and retired, beyond 402 completed acquisition-decision calls.

**6. Communication effect.** The caller receives the requested schema instance. No unrestricted prose field is allowed by this callback; its result can still be semantically inaccurate as A3-F2 establishes.

**7. Credit effect.** The composer earns no scientific credit or estimator turn.

**8. Controller effect.** No extra continuation observation; report success is required before committing the parent acquisition, making it a separate operational dependency as A3-F3 describes.

**9. Run evidence.** All 27 report cache entries have role FAST; each exactly equals a saved parent-report.json and has observations equal to saved result.findings. STOPPED_STATE records 429 completed cached model calls in total. This count establishes a separate typed call, not prohibited freeform synthesis.

**10. Proposed correction — no edits.** Resolve the specific authorization scope before claiming this mechanism must be removed. Prefer deterministic projection for recorded fact tuples and simple relations; gather any required interpretation in existing scientific reasoning calls where feasible. Do not introduce a second freeform summarizer, a raw-child bypass, or remove the required exact report boundary. No change is made in this audit.

**11. Verification needed — not run.** If the user clarifies that all extra synthesis completions are prohibited, trace an implementation through the existing work-call response, parent contract, result assembly, cache/recording and delivery, verifying identical factual information without the extra completion. If typed synthesis remains allowed, verify it remains typed and credit-free and correct the concrete factual defects. This is a proposal, not executed verification.

**Primary references:**

- [actual extra FAST dispatch](/home/chia/repos/orbital_workflow/orbital_workflow/scientific.py:285).
- [callback requires synthesis, not a model call](/home/chia/repos/OpenChia/docs/openchia/episode_communication.md:54).
- [callback abstraction](/home/chia/repos/OpenChia/method_loop/episode.py:1438).
- [original record-derived domain projection](/home/chia/repos/episodic_workflow/case_reports/research/engine.py:764).
- [stopped prefix counts](/home/chia/repos/orbital_workflow/audits/2026-10-18-method-loop/STOPPED_STATE.json:1).

## Verified defects

- **A3-F1:** Model-facing run observations omit forcing-trial provenance; actual reports invent or swap trial labels.
- **A3-F2:** Valid typed reports misassociate recorded measurements and contradict their own requested best-value relationships.
- **A3-F3:** Upward representation failure aborts the ancestor call stack without actionable Episode feedback.

## Unresolved questions

- A3-Q1: A separate typed FAST synthesis callback is real; the evidence does not establish that it violates the ban on a separate freeform summarizer
- Whether parent contracts/work assignments should select a distinct explicitly typed provenance/steering return when accounting can incorporate evidence outside a narrow report is a contract-design question, not authorization for raw-child trace access or a new scientific rejection rule. A1/A2 own the concrete work-scope/credit mismatch.

## Mechanisms checked and working correctly

- Parent construction compiles exact selected name/meaning/schema_json fields before child launch; all object levels are required/closed and arrays have item types. Numeric, boolean, nullable, enum/const, identifier, unit and mathematical-expression restrictions recurse through nested fields. Strict JSON parsing rejects duplicate keys, nonfinite numbers and non-object envelopes. These are representation checks, not scientific quality gates.
- The typed orbital subclass adds restrictions absent from OpenChia generic ReportContract. Generic admission checks exact fields and known identities; orbital admission rechecks finite values/types/formats and final declared model inputs. Format syntax is not semantic identity membership, unit compatibility or scientific truth, and the audit does not credit it as such.
- Actual OpenChia nesting requires the active parent-owned ChildEpisodeUnit, the exact parent goal link and an existing report contract. The orbital source also rejects an untyped contract. Direct-child report selection uses admitted object identity and reserves child_reports for the boundary.
- Numerical credit projection and model communication are separate callbacks. Parent machine Evidence contains the retained observations; the scientific model receives only selected contracted child reports plus its rightful own inputs. No inspected primary path delivers a raw recursive child trace or child artifact identities to the parent model. A narrow report legitimately omits unrequested child facts; that does not authorize a raw bypass.
- All 27 final saved closed reports have exact requested top-level keys, equal their FAST composer response, and are composed from exact saved result.findings/assignment/contracts. This establishes delivery/provenance and implemented representation success for this prefix, not factual accuracy or full completion.
- The root historical maximum 0.3574559702785158 comes from the earlier end=45 measurement in machine evidence. Absence of its full provenance from an unrelated narrow requested report is not itself a contract violation. Needed steering context must be supplied through a rightful parent-defined interface and aligned work scope; see A1/A2 for scope/credit findings. Do not repair this by leaking audit records.
- Closed child full traces are stored before archival; runtime retains compact typed reports and compact numerical projections. ReleasingContext/Runtime and model retirement release closed scopes. Archives remain evidence, not a parent-model expansion channel.
- The generic nano-graphrag source is materially different: EpisodeResult/Update have result/prompt_context/output channels and no ReportContract admission; it also has bound_hit support. Orbital imports the actual OpenChia implementation, whose child wrapper/closed-record/report contract is authoritative here. Nano behavior is design history, not a currently reachable orbital bypass.
- Malformed encoded planning-field JSON has structured field/index/location feedback and a changed proposal_index without executing an acquisition. This exists in Policy.next/_action_json_diagnostic; no such feedback occurrence was found among the 429 completed 007 cache records. Upward-report errors use a different, incomplete path (A3-F3).
