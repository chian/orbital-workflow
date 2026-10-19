# A6 simulator, score, provenance, viewer and reporting audit

Audit only, 2026-10-18. Scientific goal remains **paused**. Stopped evidence: `.artifacts/scenario_02/run-scored-007`. No completion is claimed.

The simulator score is preserved: all **227** distinct saved trajectories have `score == persistence_measurement.effective_duration`. The end-45 root high water is a real complete-force score. Its difference from the full-requested-horizon score is explained by the agreed partial-cycle measurement, with an exactly identical saved trajectory prefix. The additional defects concern model-facing forcing provenance and a human CSV-description mismatch.

Read `BRIEF.md` and `STOPPED_STATE.json` first. Inspected complete relevant producers and consumers, the actual OpenChia method_loop and the different nano-graphrag method_loop design, applicable AGENTS, communication documentation, current/frozen sources, and saved records. Python3 `-B` read JSON/CSV/NPZ and compared saved arrays without production function calls. No simulation, model/tool execution, replay, estimator fit, test, launch, repair or scientific-record change occurred. Only this report and its JSON companion were written.

Observed facts are distinguished from possible conditions. The historical report below supports only the same export-description defect; it does not validate the present scoring binding. A3 owns actual SIM14/SIM19 false labels and wrong-best findings; A2 owns the root-HWM communication omission. Those are cross-referenced rather than recounted.

## Verified defects

### A6-F01 — The model-facing simulation observation drops forcing-trial provenance that its report consumer requests

Severity: **medium**. Principles: 9, 19, 20, 21, 25.

Evidence classification: Observed omission in saved 007 model inputs, supported by current and frozen producer/consumer source. The false typed labels themselves are the separate A3 findings; this is the provenance-delivery defect, not evidence of wrong forcing execution.

Uncertainty: The omission is certain. Its exact causal contribution to any particular model assertion is not provable: decision conversations can remember earlier action proposals, and parent assignments can name trials. The report synthesizer has neither the decision conversation nor a deterministic observation-to-trial field.

**Requirement and authority.** Explicit: the central user invariant requires recorded state, responsible-Episode communication and credit to describe the same work; principles 9 and 21 require actual observations and stable dependency identity. Parent-owned contracts in the saved matched-trial investigation explicitly request requested and simulator-reported forcing-trial identifiers. Inferred implementation obligation: carry semantic trial/seed metadata with the measurement. No authority requires passing raw artifact identities upward.

**Owner.** Orbital ScientificBindings/ToolDispatcher observation projection and its report synthesis input, not generic method_loop and not the gravitational integrator.

**Trigger.** Any completed sim.run is summarized and projected into local own_tool_observations or the child report observations. A concrete affected case is a parent asking which forcing trial actually produced each matched run.

**Code path.** orbital_workflow/scientific.py:189-208 maps trial to forcing_id; simulation.py:123-149 returns no forcing seed or trial; tools.py:128-147 returns that summary; credit.py:73-93 recovers forcing_seed only into machine Evidence.physical; scientific.py:248-252 sends only summary plus run_index to models; scientific.py:285-301 synthesizes from result.findings, not Evidence.measurements or tool arguments; scientific.py:323-348 supplies own_tool_observations; reporting.py:100 and storage.py:101-114 separately recover seed for human/viewer consumers.

**State effect.** The exact request, forcing NPZ and score are durably retained, while the model-facing observation lacks the trial linkage. All 227 index summaries omit both trial and forcing_seed; the accounting projection and viewer metadata retain seed. The producer therefore creates different provenance richness for its consumers.

**Communication effect.** The local decision receives a run_index and numerical summary without trial/seed. The FAST composer receives assignment, contract, completion and observations without the direct decision proposals. In model-cache/0d57b255c1e83f91fe3081d7254a5a6611e0dca572639ad0be073aaa36f1278e.json all four sim.run observations lack trial/seed, although contract.information.matched_runs asks for requested and simulator-reported trial identifiers. Its four reported_trial_index values are null. The response nevertheless labels trial_mapping swapped; A3 owns the factual false-label analysis.

**Credit effect.** Machine credit uses the actual stored forcing seed recovered from forcing_id, preserving correct measured S and root eligibility. A falsely inferred report trial can disagree with this correct accounting without changing the integrated force or numeric score.

**Controller effect.** No direct score or estimator mutation. Misattributed semantic provenance can affect later REASONING action selection, and hence future acquisitions. That possibility does not establish an erroneous controller calculation.

**Run evidence.**

- .artifacts/scenario_02/run-scored-007/model-cache/0d57b255c1e83f91fe3081d7254a5a6611e0dca572639ad0be073aaa36f1278e.json: request.context.contract.information.matched_runs; request.context.observations[0..3]; response.matched_runs[*].reported_trial_index
- .artifacts/scenario_02/run-scored-007/model-cache/2776db24b0c6aa252ce2a9afc53bf500db85cb187b1c0b067298a3232272ac79.json: ten direct observations similarly omit forcing metadata; response has trial_index fields
- .artifacts/scenario_02/run-scored-007/episode-store/index/*.json: 227 summaries omit forcing metadata; three saved forcing seeds are 20261006, 20261007, 20261008
- A3-communication-contracts.md: actual false SIM14/SIM19 trial labels; those findings are not independently counted again here

**Proposed correction only.** At the existing deterministic observation projection, attach semantic forcing-trial index and forcing seed to each direct simulation measurement; propagate them consistently to both sides of comparisons, own_tool_observations and existing report synthesis input. Keep exact forcing_id/array identities in machine audit records. Parent-selected typed reports may select the supplied numeric trial fields. Do not add a raw-child bypass, new scientific gate, automatic factual reviewer or a second reporting process.

**Verification proposed; not run.** After separate authorization to change/run: acquire two declared trials and compare their already-saved observations; inspect local next-decision input and the existing synthesis input for exact run_index/trial/seed linkage, including repeats and comparison sides. Assert metadata matches stored request/NPZ while S, credit, estimator turn count and numerical arrays are unchanged. A correct input alone would not prove the synthesized output correct.

### A6-F02 — The human report promises every refinement in a CSV that deliberately contains one selected observation per physical input

Severity: **low**. Principles: 8, 9, 21, 24, 25.

Evidence classification: Verified current-source report/CSV contradiction, with an actual historical emitted report and CSV demonstrating the same retained defect. No final human report was emitted for stopped run 007.

Uncertainty: No uncertainty about the current writer: it writes selected, not all measurements. The older report used a different source hash and historical credit binding; it proves only this same human-report promise was actually emitted, not current-scoring correctness or a completed 007 report.

**Requirement and authority.** Explicit central invariant and principles 8, 21 and 25: a human report must truthfully identify what its exported view contains. No requirement mandates a new export format; current selected-view behavior can remain if labelled accurately.

**Owner.** Orbital human reporting.py, specifically the report prose paired with observations.csv. It is separate from child-to-parent contracts and the live viewer.

**Trigger.** report_run processes two or more retained observations with the same canonical physical_id but different endpoint or numerical settings.

**Code path.** credit.py:73-93 excludes endpoint/numerical settings from physical_id; reporting.py:28-65 groups on physical_id and selects one; reporting.py:176-182 uses that selection; reporting.py:239-244 writes exactly selected to observations.csv; reporting.py:250 claims other candidates and every refinement remain in observations.csv and immutable evidence.

**State effect.** Immutable measurements retain every refinement. The CSV intentionally contains only a representative row per physical input and its min/max/count, not every underlying observation. The prose describes a more complete CSV than the writer produces.

**Communication effect.** A human following the report to inspect every refinement finds selected rows instead. This does not affect the responsible Episode, whose typed report path is independent. The viewer separately retains selectable saved observation records.

**Credit effect.** None: the human report runs after workflow accounting and does not update BestScoreCredit.

**Controller effect.** None in the scientific execution. This can mislead human review of sampling sensitivity or current-vs-historical score changes.

**Run evidence.**

- .artifacts/scenario_02/run-scored-007/episode-store/index/*.json: 227 observations independently group into 201 canonical physical inputs; 11 groups have multiple observations, so collapse is material on this prefix. No record.json/findings.json/summary.json or final report exists for 007.
- .artifacts/adaptive-typed-first/reports/report-ff519a224606e95c/REPORT.md:9 actually promises every refinement in observations.csv; that CSV has 11 rows for 13 trajectory measurements in the associated findings.json, with two numerical-refinement groups collapsed.
- .artifacts/adaptive-typed-first/reports/report-ff519a224606e95c/report-provenance.json: historical report_source_sha256 3daf92d34bdab7a154b475a8c0ebcf502ace9ca6f6d8c58688e95618013ba7d0; current/frozen-007 reporting.py SHA256 5f7fc80c2ea5116faf560e1a3682058cb62ef2be86bc66496af060a5e5bde9e2

**Proposed correction only.** Correct the existing sentence to say observations.csv contains the selected observation for each physical input, while all refinements remain in immutable evidence and the saved-observation viewer. That is the smallest coherent correction; exporting a second all-observation table is optional future scope, not necessary to fix the false promise.

**Verification proposed; not run.** After separate authorization: render a report fixture with two refinements of one physical input and another candidate. Confirm row count matches the declared selected-view description and both refinements remain accessible through saved records. No simulation/model call is required for a deterministic wording/CSV contract check; no such check was run in this audit.

## Unresolved questions

### A6-Q01 — Authority for choosing among endpoint-dependent recurrence measurements remains unresolved

Severity: **unresolved; high impact**. Principles: 1, 9, 11, 12, 19, 21, 25.

Evidence classification: Actual saved measurements and exact saved-array equality; unresolved temporal credit authorization. Shared question with A2, not an additional proven root-score defect.

Uncertainty: The observed S values and equal trajectory prefix are certain. Neither BRIEF nor the saved implementation documentation alone establishes the user-approved endpoint eligibility/aggregation policy. No horizon gate is inferred.

**Requirement and authority.** Explicit: preserve the agreed duration-weighted recurrence measurement; each simulation returns S; no invented scientific gates. Explicit central invariant: accounting and communication describe the same contribution. The precise rule for assigning discovery credit across different requested endpoints is not established by these records and must not be inferred from study.horizon alone.

**Owner.** The user/goal owner defines eligible temporal scope and meaning of root discovery credit; Orbital ScientificBindings.root_score and report/viewer projections implement that declared meaning.

**Trigger.** The same insertion, forcing and full physical dynamics are observed to different endpoints; the terminal partial-cycle overlap and similarity change as its observed endpoint grows.

**Code path.** persistence.py:86-115 recalculates each full/partial cycle on its available phase overlap; simulation.py:123-148 returns measured S unchanged; credit.py:77-78 omits end from physical grouping; credit.py:115-133 retains the best observed assigned score; scientific.py:210-229 checks complete physical problem/start but not requested end; reporting.py:28-65 and 227-230 distinguish selected current measurement and historical high water; playback.html:157-221 compares best-so-far only within a key that includes end.

**State effect.** Root stopped HWM is 0.3574559702785158 from a complete-force end=45 observation. The same physical insertion/forcing requested through H=125.66370614359172 exits at 46.01676870277573 with S=0.16618918808347596. These are different finite-observation measurements, not contradictory stored states. The longer request does not invalidate the earlier saved measurement by itself.

**Communication effect.** A2 documents the separate omission of the HWM contribution from the responsible root report. This question does not authorize an extra reporting channel. Human reports explicitly label current selections versus historical maxima; the viewer displays final recorded S and a comparable best for its declared scope.

**Credit effect.** Current code credits the actual end=45 S, retaining it above later/lower full-H or refined measurements. Whether that cross-endpoint high-water assignment matches the authorized root scientific objective is unresolved. Calling it a reduced-force score is factually wrong.

**Controller effect.** The credited improvement enters root marginal-credit history on its returned child acquisition, which can affect subsequent yield forecasts. No evidence supports replacing that value, clamping a correction or adding an H eligibility gate during this audit.

**Run evidence.**

- .artifacts/scenario_02/run-scored-007/objects/artifact_f2e0195355548a277642704c008e13912c50da68174dd43eb27d39b909f82c2c.json: request.end=45; all terms true; both resolved binary sources; S=0.3574559702785158
- .artifacts/scenario_02/run-scored-007/objects/artifact_b666e73e01dfbcf9fd13d203be81a3dc72fde2ebaec3af9da06723d54051d442.json: same insertion [1,0,0.10330396,-1.19999604], same forcing, numerical settings and force model; requested end=125.66370614359172; actual endpoint=46.01676870277573; S=0.16618918808347596
- Read-only saved-array comparison: all 2327 short-run samples are exact common samples through [0,45]; max absolute state difference is 0.0; longer trajectory has 2380 saved samples. No integration or persistence recomputation was performed.
- Terminal partial-cycle stored duration/similarity: short 5.513322170252685 × 0.06483495053511619; long 6.5300908730284135 × 0.025449751194715015. Earlier complete-cycle contributions match.
- STOPPED_STATE.json: root_latest_controller.credit=0.3574559702785158; root units=20; stop=false; user_interrupted_prefix; completion_proven=false

**Proposed correction only.** First resolve the intended temporal meaning with exact user authority: historical best finite-observation score, a declared comparable scope, or another explicitly authorized policy. Preserve every measured S and its requested/observed endpoint. Then implement that single policy coherently in accounting, requested report fields and human labels. This question is not authorization to impose a full-H gate, change the recurrence formula or erase the valid end=45 record.

**Verification proposed; not run.** After the policy is explicitly resolved and changes separately authorized: use saved equal-prefix observations as data to verify the declared credit/communication relation. Confirm endpoint and numerical-setting differences remain visible and only a newly eligible contribution changes assigned credit. Fresh scientific execution is unnecessary to resolve the existing evidence; none was performed.

### A6-Q02 — Playback chronology depends on filesystem timestamps rather than an immutable acquisition order

Severity: **unresolved; medium portability impact**. Principles: 8, 9, 19, 21, 22, 25.

Evidence classification: Verified source dependency and actual metadata shape; possible portability/recovery ordering issue. No incorrect 007 timeline order is established. Shared with A4.

Uncertainty: The filesystem dependency is certain. A timestamp-changing copy, restore, clock discontinuity or tied timestamps has not been observed to reorder this stopped run. The required portability scope of chronological playback needs explicit treatment before claiming a runtime chronology defect.

**Requirement and authority.** Explicit: standard saved simulation records power generic live/offline chronological playback and durable provenance. Inferred portability expectation: a saved work chronology should remain the same when file timestamps are not preserved. The latter is the unresolved scope, not permission to add a scientific restriction.

**Owner.** Orbital EpisodeStore publication and viewer_timeline.load_timeline, with runtime._publish_observations supplying committed unit identity.

**Trigger.** Ownership-file mtimes are changed or tied relative to original publication, or a copy/restore does not preserve them. Original 007 files currently retain publication timestamps.

**Code path.** runtime.py:160-169 supplies episode_id/unit_id/origin but no explicit order; storage.py:76-124 publishes acquisition_order from object st_mtime_ns and ownership records containing only observations; durable.py:166-174 writes unit event after publication without a global chronology field; viewer_timeline.py:16-28 sorts ownership path st_mtime_ns and then assigns acquisition ordinals; storage.py:171-184 sorts index entries by acquisition_order, but viewer ownership chronology does not consume that stored field.

**State effect.** Simulation identity and numerical records survive. The 305 saved ownership records contain 333 timeline positions but no immutable global event ordinal. Their ordering can follow filesystem publication metadata instead of a portable logical chronology.

**Communication effect.** No model-facing Episode input is changed. The viewer could show a different chronology and different best-so-far order after a timestamp-changing transfer, although all final measured scores would remain available.

**Credit effect.** No direct accounting change: credit replay uses cached acquisition/decision logic, not the viewer timeline. A viewer best-so-far display could diverge from original order in the stated possible condition.

**Controller effect.** None; the viewer performs no estimator fit, simulation or credit update.

**Run evidence.**

- .artifacts/scenario_02/run-scored-007/episode-store/ownership/*/*.json: 305 files, each stores only observations; all 227 index acquisition_order[0] values equal their source JSON object mtime on disk.
- First saved ownership example: episode_5e51407e891f0205c498230180081c1660fc0336fde762d3e5b1d893d2e9e7fd/unit_6f0869ba0e251fb14832289245d5cc4c87097d4b938dfd7a794c2fe9bf7ea2d8.json; contains only artifact_c433b1e333d8df18c840aca09abf5b56ff54f424e2603805d5a3cda4e10c4e56
- .artifacts/method-audit-20261018/fresh-live-viewer-007/checkpoints.json: final existing checkpoint contains observationCount=227 and timelineCount=333; no wrong-order observation is established by this evidence.

**Proposed correction only.** If portable chronology is within the intended saved-record contract, persist one immutable acquisition sequence/ordering value together with the existing committed UnitRef, origin and observation list; let timeline and offline export consume it. Keep comparison sides and repeated observation acquisitions as distinct event positions. Preserve legacy timestamp provenance honestly instead of inventing an exact historical order. No repair was made.

**Verification proposed; not run.** After scope resolution and separate authorization: compare the timeline from an original saved fixture and a copy whose mtimes are intentionally changed; event order and comparison-side positions should match without loading recursive Episode traces. Also inspect publication after an interrupted commit/recovery. No copy, replay or test was performed here.

## Mechanisms checked and working correctly

The following table separates observed outcome from meaning and scope. Source-based behavior is identified explicitly where the stopped prefix did not exercise it.

| Mechanism | Outcome | Meaning and scope | Primary references |
|---|---|---|---|
| A6-W01 One integration, one measured S and one local acquisition turn | All 227 distinct saved simulation summaries satisfy score == persistence_measurement.effective_duration exactly. ToolDispatcher._run calls integrate once and summary once; comparisons read saved observations without integrations. CreditController.observe passes one marginal-credit value per acquired unit; generic OpenChia Episode advances once after acquisition. Duration, output samples and RHS evaluations do not enter estimator exposure. | The user-specified recurrence formula remains the simulator score. This is in scope and supported by code plus all saved scalar records; no simulator or estimator was run by the audit. | `simulation.py:123-149,199-266,269-283`; `tools.py:128-167`; `credit.py:115-133,165-177`; `score_yield.py:217-232`; `/home/chia/repos/OpenChia/method_loop/episode.py:1248-1258,1421-1435` |
| A6-W02 Score is recurrence, not radial lifetime; sampling and endpoint dependence are recorded | The first revolution is reference; later full/partial winding cycles contribute duration × exp(-normalized mismatch). Saved records include settings, cycle overlap, duration, mismatch, terminal outcome and actual interval. The exact-prefix end=45/full-H pair above demonstrates endpoint dependence without changed physics. At the same full-H physical input, sample_step 0.02 versus 0.005 produces stored S about 0.166189188 versus 0.166138144; this is saved-state measurement sensitivity, not an automatic extra reward or proof of invalidity. | In scope. Preserve this agreed metric and label comparisons; neither HWM nor a lower refined score alone establishes invalidation. Finite-time recurrence establishes neither indefinite stability nor survival probability. | `persistence.py:55-139`; `simulation.py:123-149`; `objects/artifact_f2e0195355548a277642704c008e13912c50da68174dd43eb27d39b909f82c2c.json`; `objects/artifact_b666e73e01dfbcf9fd13d203be81a3dc72fde2ebaec3af9da06723d54051d442.json`; `objects/artifact_46555b2820d885445da41227a1be2f5efb3a0eae2ab85e9a95bcc31ffc71c5b8.json` |
| A6-W03 The implemented source motion and all time-dependent terms use absolute time | GravitySystem fixes masses, source separation/phase/collision surfaces, uses angular speed sqrt(total_mass/separation^3), and keeps both primaries on their barycentric circular orbit. Integrate evaluates gravity, modulation, rotating term, event surfaces and forcing at solver absolute t, splitting solves at forcing knots. Simparts can retain one body or a monopole explicitly without changing source or collision motion. | Source inspection supports correct declared binary/shifted-time semantics. There are zero start>0 trajectories in 007, so actual continuation/shifted-binary numerical equivalence is not established by this prefix. A typed report mistake does not imply the integrator changed primaries or forcing. | `gravity.py:17-75`; `simulation.py:173-266`; `scientific.py:189-229,254-268,329-339`; `run-scored-007/study.toml`; `run-scored-007/scenario.json` |
| A6-W04 Physical identity, numerical refinement, forcing objects and execution compatibility have separate recorded roles | Artifact payloads are content-addressed and verified on read. Forcing records retain seed, PCG64DXSM, Gaussian sampler and NumPy version; matched trials reuse the same forcing_id. Accounting physical identity excludes endpoint/numerical settings and normalizes inactive a/sigma and source selection. Different numerical observations remain distinct measurement evidence. Frozen critical sources/configuration/libraries determine resume compatibility. | In scope for this fixed run. Different view keys are not automatically conflicting state: storage.group uses raw request grouping, canonical physical_id is an accounting/display physical key, and comparisonKey includes endpoint for comparable playback history. Cross-environment equality of a numeric seed alone is not proved. The actual missing semantic forcing metadata for models is F01. | `artifacts.py:16-47`; `simulation.py:152-170`; `credit.py:73-93`; `storage.py:103-116`; `durable.py:42-64,106-123`; `run-scored-007/execution-identity.json`; `run-scored-007/environment.json` |
| A6-W05 Current selectors and discovery high-water values have documented different meanings | reporting.select_observations, reporting.make_figure and playback.bestGroups independently rank by requested end then sample_step/max_step/rtol. They omit atol/method tie-breaking and use different traversal order, but current 007 has no tied top-preference group. A mismatch on the same declared quantity was not established. Human report instructions explicitly distinguish selected current S from historical maximum; viewer labels Recorded S and comparable best so far and includes endpoint in comparisonKey. | In scope. Duplicate selection logic is a maintenance risk, not a verified current disagreement by itself. Do not conflate max-interval/current display selection with root BestScoreCredit. The false export promise is F02; endpoint assignment authorization is Q01. | `reporting.py:28-65,109-124,227-250`; `templates/playback.html:157-221,445-453`; `credit.py:115-133` |
| A6-W06 Generic live/offline viewer uses saved records and includes the whole saved simulation-acquisition history by default | load_catalog reads any supplied run directory and index, with no hardcoded observed trajectories; server permits opening another run. Default progress starts at the first timeline observation and advances through all timeline positions, including repeats and comparison sides. Offline export defaults to all indexed observations. It draws source positions/orbits, collision surfaces, per-source attraction, modulation, rotating term, forcing and total-field overlays from the declared model and exact forcing interpolation. The recurrence display uses saved cycle endpoints; path decimation is labelled and does not change S. | Source behavior and existing browser records are in scope. Existing checkpoints grew from zero to 227 observations / 333 positions, with at most four loaded observations and 9,430,852 loaded bytes. That is prior recorded active-prefix evidence, not a fresh audit browser check or full end-to-end completion. Math-only actions/root child-return turns are not simulated trajectory observations and are not invented as trajectory playback items. | `visualization.py:35-88,98-143`; `viewer_server.py:15-78,85-125`; `storage.py:171-222`; `viewer_timeline.py:6-61`; `templates/playback.html:109-175,193-224,246-370,487-571`; `.artifacts/method-audit-20261018/fresh-live-viewer-007/checkpoints.json` |
| A6-W07 Actual method_loop and communication/accounting boundaries remain distinct | environment.json identifies OpenChia/method_loop as the actual imported implementation. Its parent-owned ChildEpisodeUnit separates machine projection and typed synthesis; controller advancement follows acquisition once, while stored child records/results are spooled and local controller/model state retired. Nano method_loop is a different source design with Episode.to_parent/parent_controller_input and optional bound; those fields are not evidence of hidden bounds in the actually imported OpenChia binding. | In scope. The orbital binding owns task scoring, schemas, simulator execution and report semantics; generic core does not own a scientific horizon metric. No raw-child model channel is authorized by a legitimate omitted fact. No archive hydration is required for live catalog or progress updates. | `run-scored-007/environment.json`; `bootstrap.py:7-17`; `archival.py:9-88`; `scientific.py:159-183,280-310`; `/home/chia/repos/OpenChia/method_loop/episode.py:1438-1573`; `/home/chia/repos/OpenChia/docs/openchia/episode_communication.md:38-75`; `/home/chia/repos/nano-graphrag/method_loop/episode.py:775-889,1104-1184` |
| A6-W08 The stopped prefix is not completed scientific or reporting evidence | STOPPED_STATE records 402 committed local units, 375 tool acquisitions, 27 returned children, 20 root turns, user interruption, root stop=false and no root summary. run_scientific writes record/findings/summary only after root returns. Existing run_state in viewer is completed only when summary exists; otherwise the UI waits at the end of its available timeline. root_credit is unused and no active-root credit chart is promised by that field. | In scope. The UI currently lacks a user-cancellation terminal state, but it does not assert scientific success for 007. A completed loop summary would mean execution ended, not goal fulfillment. The older browser-active-prefix-007.json 148-observation count is stale; current checkpoint data is used above. No model/tool/replay/estimator/test/launch was performed for this audit, and the paused goal was not resumed. | `STOPPED_STATE.json`; `scientific.py:413-429`; `visualization.py:50-72`; `templates/playback.html:470-472,558-562`; `.artifacts/method-audit-20261018/user-stop-007-processes.json` |
