# User-requested audit of the stopped orbital workflow

This audit is authorized by the user's latest message, “Consume many agents to
perform a detailed audit,” with 25 supplied audit principles. This brief is an
index/paraphrase of that message, not evidence that historical project documents
were approved. The conversation is the authority for user requirements.

The central invariant, quoted from the user, is:

> Actual progress, recorded state, communication to the responsible episode, and credit assignment must describe the same work.

## Scope and constraints

- Repository: `/home/chia/repos/orbital_workflow`.
- Stopped evidence: `.artifacts/scenario_02/run-scored-007`.
- The user explicitly stopped the scientific workflow for this audit. The
  persistent end-to-end completion goal is paused. Do not resume it.
- Writer PID203816/session25138, queued validation PID204554/session52140 and
  live watcher PID203452/session47321 exited130 after user-requested SIGINT.
  There is no completed root summary. The viewer remains read-only and available.
- No source/configuration/scientific record changes, launches, model calls,
  simulator calls, tool replays, estimator fits, broad tests, or repairs. Read
  files and saved numerical arrays; write only assigned audit artifacts here.
  A read-only accounting verifier may be run by the primary agent.
- Use Python `-B` for audit scripts to avoid bytecode writes. Do not alter other
  checkouts. Read applicable AGENTS.md instructions before their files.
- Read complete relevant files/functions and their consumers. File discovery is
  allowed; snippets and naming are not sufficient evidence.
- Read actual source designs in BOTH `/home/chia/repos/OpenChia/method_loop` and
  `/home/chia/repos/nano-graphrag/method_loop`, relevant numeric libraries and
  episode communication docs. Orbital imports OpenChia's actual implementation;
  distinguish obligations in generic core from this binding's project choices.
- Current implementation commits: `0f6f8fb` and `29f5cda`; origin baseline
  `d1545122ea3dddb6970ddd17488d1bc93ac58700`. Check current files and frozen007
  source as authoritative. Prior audits are leads, not conclusions to inherit.
- All prior source and per-report evidence is preserved under
  `.artifacts/method-audit-20261018/`. Do not overwrite earlier reviews.
- The actual interrupted counters may exceed earlier progress messages. Read
  final stopped state, not stale WORK_STATE/progress counters.

## Earlier direct user requirements relevant to authorization

- Fixed problem simulation; search spaceship insertion trajectories. Source
  masses, source motion, field terms and forcing belong to the problem. Explicit
  simparts can study reduced dynamics, spatial/time pieces and matched variants.
- Use actual method_loop, not a substitute private iterative optimizer. Math and
  simulation are optional branches; math may use calculation/checking tools.
- “There are NO GATE. No hidden gates, no rejections, no checks before accepting
  results.” Interpret with the user's separately explicit type/identity boundary
  enforcement: representation checks are required; invented scientific approval
  mechanisms are not authorized.
- “The simulation produces a score. period”; each completed simulation is one
  local run turn. Duration/solver steps must not become extra estimator exposure.
  Preserve the agreed duration-weighted recurrence measurement itself.
- Score assignment, yield estimation, and continuation are separate. Use the
  supplied rarefaction templates. Estimator owns its history/window/fitting;
  remove controller memory/EWMA/artificial turn-yield modifications.
- Parent predeclares exact structured fields/types/meanings. JSON-wrapped prose
  is insufficient. Typed strings are permitted; no unrestricted freeform upward
  report fields or child audit identities/raw recursive trace extra channels.
- Closed Episode logging data goes to disk and is ejected from active memory.
  Standard saved simulation records power a generic live/offline viewer with
  default chronological playback and source/forcing overlays.
- FAST=gpt-6-luna/none; REASONING=gpt-6-sol/medium via the existing connection.
- Earlier equal root persistence/knowledge weighting is historical. User later
  explicitly rejected the existing orbital credit implementation. Do not treat
  its support proxy as authorized knowledge credit. Trace exact authorization
  rather than accepting documentation's “approved” label.

## The 25 principles to audit

1. **Requirement provenance:** identify the source of every review, gate,
   threshold, default, retry, stop and completion rule. Separate user instruction,
   source design, implementer interpretation and historical conflict.
2. **Ownership:** identify who owns decisions and who actually makes them;
   infrastructure must not silently substitute, expand or cancel actions.
3. **Iterative structure:** feedback reaches later decisions; real ownership tree
   matches execution; no forced sequence, ordinary-op child explosion or private
   nested scientific search loop.
4. **Single responsibility:** validation, assessment, execution, recording,
   projection, communication, continuation and completion remain separate.
5. **No redundant processes:** trace competing registration/assessment/selection/
   reporting paths and repeated decisions; determine whether answers can diverge.
6. **Assessment semantics:** define every output, consumer and permitted state,
   credit/controller effect. Distinguish unused, informational and control fields.
7. **Individual gates:** exact trigger, authority and category; which component
   is blocked, whether partial results survive and whether feedback is useful.
8. **Authoritative state:** proposed/executing/returned/committed distinctions,
   explicit transitions and derived views; identify stale competing copies.
9. **Provenance/identity:** source vs target, actual observation vs inference,
   references/indices, semantic meaning and stable dependency identity.
10. **Configuration ownership:** effective defaults, authorized overrides,
    duplicate defaults and silent replacement/rejection across layers.
11. **Credit and actual progress:** eligible goal scope, inherited vs new gains,
    duplicate projection/rewording/retargeting and different meanings of progress.
12. **Explainable decreases:** identify genuinely invalidated/current-lost
    contributions; do not erase earlier valid work or clamp genuine corrections.
13. **Shared progress:** where shared/global state is designed, relevant ancestor
    score/input refresh must not await child return; preserve local ownership.
    Establish whether that shared-state design actually applies here.
14. **Refresh vs yield observation:** a child can do many operations but complete
    one parent action; refreshes must not manufacture ancestor yield observations.
15. **Faithful continuation:** correct episode history/current defined rule,
    root vs local scope, committed inputs, no hidden budgets/alternative chooser.
16. **Termination vs completion:** goal fulfillment, yield stop, source exhaustion,
    operational failure, external interruption and authorized budget exhaustion.
17. **Actionable failures:** preserve valid partial work, exact affected input/
    output/reference, structured feedback and honest failure/complete states.
18. **Meaningful retries:** transient vs deterministic; changed dependency/input,
    attempt relationship, no hidden repeated invalid work or accounting escape.
19. **Dependency-aware reuse:** exact invalidation dependencies; freshness is not
    quality or wording; reuse unchanged work, invalidate only affected progress.
20. **Child-to-parent contract:** exact parent-owned types/meaning, existing work
    call vs additional summarizer, identifiers/enums/relationships and no prose
    or raw audit-identity instruction channel.
21. **Synchronized integration:** recording, responsible-episode information,
    progress displays and credit must describe the same committed contribution.
22. **Runtime vs archive:** release closed full traces, retain rightful active
    state and durable provenance; don't load archives just for progress updates.
23. **Complete removal:** follow removed mechanisms through callers, schemas,
    prompts, registration, persistence, projections, freshness, credit, controller,
    reports, closure and startup interfaces; no fake placeholders.
24. **Proportional verification:** distinguish inspection, existing tests,
    saved-record evidence, replays, started/reached-path/completed-task runs.
    This stopped prefix is not completed end-to-end evidence.
25. **Precise findings:** code permits vs necessarily does vs actual occurrence
    vs hypothesis; validate old examples still exist after fixes; correct earlier
    conclusions when primary evidence changes them.

## Mandatory format for every finding

Write an assigned Markdown report and a JSON companion. Every finding must have:

1. Requirement, including exact authority and explicit-vs-inferred status.
2. Owner.
3. Trigger (exact condition).
4. Code path (functions and current line numbers).
5. State effect.
6. Communication effect (what the responsible Episode actually receives).
7. Credit effect.
8. Controller effect.
9. Run evidence (actual occurrence, or explicitly not established).
10. Proposed correction (smallest coherent change through affected consumers;
    proposed only, no edits).
11. Verification (what would establish the correction works, not a claim it ran).

Also record severity, principle numbers, evidence classification, uncertainty and
references to actual code/records. Keep factual report errors distinct from
generic runtime defects; a complete correct input does not imply the synthesized
output is accurate. A legitimate unrequested child fact absent from a typed report
is not authorization to add a raw-child bypass. A hypothesis test is not an
asserted wrong measurement.

Conclude EACH report and the consolidated audit with exactly these three groups:

1. Verified defects
2. Unresolved questions
3. Mechanisms checked and working correctly

An unresolved question is not authorization to introduce a new restriction.

