# Orbital Episode workflow

All project source, configuration, dependencies, and artifacts live here.
The workflow imports the actual `method_loop` from the sibling OpenChia checkout;
it does not modify OpenChia or replace its execution loop. Run snapshots retain the
used source for reproducibility. The revised scientific design is in
[EPISODES.md](EPISODES.md), decisions in [DESIGN.md](DESIGN.md), and the score,
yield-estimation and continuation boundaries in [CREDIT.md](CREDIT.md).

The 2026-10-18 repair replaces the anchor-support credit proxy and EWMA forecast
with explicit measured-score assignment, a template-derived scalar yield
estimator, and independent continuation. Old run numbers below are historical
evidence from the removed binding; they do not verify the repaired estimator.
Fresh end-to-end verification must be recorded separately.
The active repair goal is [GOAL.md](GOAL.md); the source-based findings and repair
boundaries are in [METHOD_AUDIT.md](METHOD_AUDIT.md).

Run artifacts under `.artifacts/` and the local `.venv/` are ignored by Git.
Links to `.artifacts/` below refer to locally generated demonstrations; generate
your own run and viewer using the commands below after cloning.

## Run

From this directory, use the project-local Python environment:

```bash
.venv/bin/python -m orbital_workflow describe
.venv/bin/python -m orbital_workflow simulator-demo --output .artifacts/my-simulator-example
.venv/bin/python -m orbital_workflow run --output .artifacts/my-study
.venv/bin/python -m orbital_workflow resume .artifacts/my-study
.venv/bin/python -m orbital_workflow report .artifacts/my-study
.venv/bin/python -m orbital_workflow replay-tools .artifacts/my-study
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tests/verify_scored_run.py .artifacts/my-study --output .artifacts/my-study-verification.json
```

The last command inspects a saved run without changing its records or executing
models, simulations or estimator fits. It checks recorded numerical accounting,
typed reports, frozen sources, model roles and closed-Episode storage. An active
or interrupted run is reported as an incomplete prefix, never as completed evidence.

`run` requires a new directory. `resume` uses that run's frozen study.toml and
reconstructs its source/controller history from cached decisions and acquisitions.
It also supports replaying a completed run. No restored scalar total is added to
replayed contributions. Completed calls and recorded failed attempts are reused;
an interrupted tool operation with no recorded outcome can be recomputed.
Visible model conversation exchanges are restored;
native hidden reasoning state is not persisted. A run lock prevents concurrent
scientific writers. Errors remain inspectable and are never physical outcomes.
This restores interrupted whole-run execution; it does not reopen a completed
stopped child investigation. A new child invocation is a new local scope.
Resume checks the frozen execution sources, configuration and numerical libraries
before opening a model connection. Changed bindings require a new run; historical
evidence remains intact. Stored artifact bytes are verified before tool replay.
`replay-tools` freshly executes the finite saved tool history using the same forcing
and records exact differences without updating any Episode credit. This checks
reproducibility on the same machine; it is not an independent equation solver.

The `.venv` uses this machine's existing NumPy/SciPy and installs project-local
plotting/symbolic dependencies. A fresh Python 3.12+ environment can install this
project with `pip install -e .`. Nothing installs into or changes Hermes.
Use `--method-loop-source /path/to/OpenChia` before a subcommand if needed.

## Saved scenarios

[SCENARIOS.md](SCENARIOS.md) documents the fixed physical systems and returning to
saved runs. `scenario_01` preserves the original single attractor, including its
original Git tag and completed run. `scenario_02` adds two mutually orbiting massive
attractors (0.75 and 0.25, separation 0.8) with the spaceship as a test particle.
Masses and source orbits are fixed; the workflow chooses ship velocity. Each run
keeps its own configuration, data, source snapshot and execution identity.

```bash
.venv/bin/python -m orbital_workflow scenarios
.venv/bin/python -m orbital_workflow run --scenario scenario_01
.venv/bin/python -m orbital_workflow run --scenario scenario_02
```

The viewer's Saved scenario selector opens either case. Individual attractor fields
and moving source markers show the binary dynamics; Fit paths and Whole region
control framing. Explicit single-source force omissions and a monopole approximation
are available to scoped investigations. The existing math and simparts branches
remain optional. No new path-interest reward or forced branch visitation was added.

## Live viewer and closed Episode storage

Open any fresh run, including an active or not-yet-created run directory:

```bash
.venv/bin/python -m orbital_workflow visualize .artifacts/my-study --serve
```

Open http://127.0.0.1:8767/ . **Run progress** starts automatically at the first
saved acquisition and plays through the work in order, including refinements,
repeated observations and both sides of matched comparisons. Choose 2, 4 or 8
seconds per observation. The separate simulation-time cursor always uses the
observation's actual saved time. Previous/Next, the history slider and clicking the
history plot let you pause at any point; Reset returns to the beginning of the run.

Faint earlier trajectories show comparable past observations. The history plot
shows each measured recurrence and the best so far within matching environment,
forcing, model terms and observation scope. Changes between environments remain
labelled; this plot displays recurrence measurements rather than root credit.
An active tour waits at the current end and continues when new observations arrive.

Choose **Individual / compare**, or select a trajectory or comparison, for detailed
inspection with physical-time speed controls. Play/pause, the time slider and
clickable time plots control that view. Auto refresh preserves deliberate
inspection. Follow new observations is available in individual mode. Use the Run
directory field to switch runs without restarting the service.

Colored arrows distinguish the added acceleration terms: orange is periodic
modulation of gravitational attraction, purple is the position-dependent rotating term,
and pink is the saved random push. These terms act throughout the displayed region.
The random push is spatially uniform at a given time. Toggle each layer and choose
1×, 10× or 30× display magnification. Numerical contributions at the spaceship
retain their true values; toggles and magnification never change the simulation.
The total field uses the primary observation's equation and exact saved forcing.

The viewer reads only index metadata initially and loads selected numerical data
on demand. Deselecting an observation releases its browser arrays. The server's
numerical payload cache and the browser's estimated payload budget are each
16 MiB; comparison selections may be removed to fit. Catalog entries are compact
metadata and still grow with the number of observations. These budgets describe
cached data, not a hard bound on total process RSS or active request working sets.

Offline HTML exports include the entire run by default. Repeat
`--observation OBSERVATION_ID` to export a subset:

```bash
.venv/bin/python -m orbital_workflow visualize .artifacts/my-study
.venv/bin/python -m orbital_workflow visualize .artifacts/my-study \
  --observation artifact_FIRST --observation artifact_SECOND --output comparison.html
```

Offline files embed saved packets and complete forcing for the exported observations,
then decode current selections on demand. The embedded file itself still occupies
memory. Display paths retain at most 10,000 states per observation, including
both endpoints. Motion uses labelled linear interpolation between display states;
no motion is extrapolated after an endpoint. Recurrence changes at recorded cycle
endpoints. Display sampling does not modify the full numerical evidence on disk.

Every closed Episode writes its detailed audit, result and typed parent report
before the parent retains compact references. Closed controllers, local model
histories and owned provider processes are retired. Parent credit keeps its
numerical accounting evidence, with detailed cycle and solver logs stored on disk.
The standard JSON manifests and memory-mappable numerical files are documented in
[STORAGE.md](STORAGE.md); the visualization goal is [VISUALIZATION_GOAL.md](VISUALIZATION_GOAL.md).
Fresh runs publish this format directly; no historical-run compatibility is needed.

## Simulator tool interface

The public `sim.run` request supplies only spaceship insertion velocity `vx, vy`.
The scenario owns the fixed physics, forcing realization, observation domain,
numerical recipe and measurement settings. One specified integration returns its
recurrence score S. `sim.compare` analyses already-saved
observations and reports differences without executing another integration.
Obtain each comparison case in its own scored turn. Both tools are available to
simulation_investigation and recursive simparts; reduced/scoped investigations
use explicit simparts rather than bypassing that Episode boundary.
Scientific comparison findings identify both sides through local `run_indices`
arrays; repeated acquisitions of an identical saved observation can share
several indices. Raw artifact references remain in audit storage rather than
entering model decision inputs.
Math, simulation and simparts Episodes also have `math.arithmetic` for one bounded
scalar calculation from supplied measurements. Differences, ratios, convergence
orders and extrapolations can be computed locally without another simulation or
an identical child assignment. The operation returns a number or typed diagnostic
and advances the invoking Episode once; it supplies no automatic score bonus.
A public tool request is independently callable from the command line. Save this
as `insertion-request.json`:

```json
{"tool":"sim.run","arguments":{"vx":0,"vy":1}}
```

```bash
.venv/bin/python -m orbital_workflow tool \
  --config scenarios/scenario_02/study.toml \
  --artifacts .artifacts/my-tool/objects --request insertion-request.json
```

An explicit simparts experiment derives a reduction, region, segment or numerical
refinement from the same scenario. For example, save this as `parts-request.json`:

```json
{"tool":"sim.run","arguments":{"vx":0,"vy":1,"experiment":{"terms":{"rotating":false},"interval":[0,20],"refinement":{"max_step":0.025}}}}
```

Pass `--parts` with that request. A derived experiment retains the fixed forcing
and records its scope; it does not replace the base scenario. A continuation uses
`experiment.continuation` with a local saved `run_index` and absolute `end`, taking
the initial state from that observation. For the CLI, repeat `--saved-run` in index
order. Complete saved engine specifications are an internal replay interface;
they are not public tool proposals.

The historical standalone simulator example is `.artifacts/simulator-second/`, including
requests, observations, forcing, trajectory arrays, summary, and trajectories.png.
It compares central-only, full-environment, and finer full-environment integrations
with the same insertion and stored forcing. It assigns no Episode credit.

The simulator integrates the fixed stated dynamics. Explicit simparts experiments
can isolate central attraction, modulation, rotating field or forcing. It segments solves
at forcing interpolation knots, detects radial exits during integration, supports
absolute-time continuation, and can stop observation at an explicit spatial box.
A spatial scope does not silently remove field contributions. Numerical refinement
uses the identical stored forcing. Solver errors are distinct from physical exits.

The adaptive workflow fixes the evaluation domain to `[0, study.horizon]` for
complete and derived observations. An invalid public parameter or outside-domain
derived interval returns basic typed feedback to the responsible Episode before
acquisition; it creates no score, run index or estimator turn. An unfinished tool
operation similarly supplies limited failure feedback without fabricating a
completed observation. Its next ordinary decision uses the same numerical state.
The private engine's `sim.request_diagnostic` remains an acquired unscored feedback
observation when that operation actually returns, including in finite diagnostic
fixtures. The evaluation domain is a physical problem input, not an Episode turn
limit. Recorded request diagnostics, physical exits and solver errors remain
distinct outcomes.

Recurrence aligns successive revolutions by first passage through orbital phases,
compares position/velocity/relative period continuously, and sums similarity
weighted by duration. Partial revolutions contribute. The first revolution is a
reference. This winding measurement does not cover libration or prove indefinite
stability. Smooth scales are configurable in study.toml.

## Episodes and model roles

The root commissions mathematical_exploration and simulation_investigation; both
can commission simparts, which can commission a smaller simparts. The real method
loop enforces topology, goal linkage, controller routing, and the separation of
parent credit projection from contracted report synthesis. Each Episode owns its
controller, explicit score assignment, yield estimator and continuation settings.
The root scores observations of its fixed complete physical problem; smaller
models retain their own scores and scope. No scalar child credit is added to a
parent's credit. The earlier 0.5 persistence / 0.5 knowledge implementation used
the removed support proxy; this repair does not invent a new knowledge metric.

Parents now declare a typed schema for each requested return field. Copied and
adapted guards from episodic_workflow enforce closed nested records and declared
string types at contract construction, report delivery, and parent model dispatch.
The exact examples and source provenance are in [COMMUNICATION.md](COMMUNICATION.md).
The historical storage-lifecycle demonstration is `.artifacts/adaptive-storage-first/`:
[findings and plots](.artifacts/adaptive-storage-first/REPORT.md),
[offline run playback](.artifacts/adaptive-storage-first/visualizations/playback.html),
and [completion evidence](.artifacts/adaptive-storage-first/completion-evidence.json).
It completed five root investigations and fourteen distinct saved observations.
Interruption/resumption, completed replay and fresh reproduction of all eleven
simulator operations passed. The live viewer discovered its observations while
the workflow ran. A type-valid report omitted available measurements; the saved
communication review records that limitation without changing the scientific run.

The earlier typed-boundary demonstration is `.artifacts/adaptive-typed-first/`:
[findings and plots](.artifacts/adaptive-typed-first/REPORT.md) and
[execution evidence](.artifacts/adaptive-typed-first/completion-evidence.json).
It completed four root investigations with typed child reports, deliberate
interruption/resumption, completed replay without fresh calls or changed credit,
and exact fresh reproduction of all eight tool operations. The earlier
`.artifacts/adaptive-first/` predates this boundary and remains historical.

Models propose one next tool or child action. Actual declared tools execute it.
Each turn's credit is the improvement in the best assigned measured score. The
yield estimator receives that real-valued improvement, including zeros, and owns
its history/window/subsampling/fitting policy. The controller records the current
estimate without EWMA or artificial decay. Independent continuation consumes its
estimate and approximate model-dependent bands. There are no arbitrary Episode
iteration limits or scientific acceptance gates. Full semantics are in CREDIT.md.

REASONING = `gpt-6-sol` / `medium` selects actions and fills the child's remaining
interpretation fields in the same conversation after its final result. Explicit
recorded form fields copy the actual saved observation and need no model call.
FAST = `gpt-6-luna` / `none` is reserved for the separate human report. Both have completed
live connection probes with the exact model and effort confirmed by the server.
The adapter starts a project-owned Codex app-server using the existing login;
credentials and personal configuration are unchanged. Native coding/research and
delegation capabilities are disabled for these structured reasoning conversations.

Mathematical tools provide bounded scalar arithmetic, SymPy central conic relationships, numerical central
candidate predictions, and local affine fits to supplied measurements. Lean is
optional; availability, proof diagnostics, and execution errors are observations,
never prerequisites for other work or scientific contribution.

## Diagnostic versus scientific execution

`smoke` executes a finite diagnostic tree, including recursive simparts and real
simulation tools. It deliberately leaves scientific credit unset; source exhaustion
does not establish scientific completion. `model-probe` exercises model roles only.
`run` uses live adaptive model proposals, projected numerical evidence, independent
local credit schemes, parent reporting contracts, and numerical yield stopping.

Artifacts retain frozen configuration and source/runtime provenance, all prompts
and responses, provider/execution errors, exact forcing and tool requests, numerical
observations, each unit's marginal credit and forecast, and disk-backed recursive audit records.
`report` summarizes the fixed scalar scenario, candidate/refinement measurements,
plots, and a concise FAST interpretation. Its CSV includes every distinct recorded
observation and numerical refinement. The displayed complete-model row selects
the best displayed candidate in that fixed scenario; an unobserved case remains
unknown rather than becoming a zero score.
Reports are versioned under each run's `reports/` directory. Physical comparisons
retain the changed terms/inputs, while numerical comparisons retain their solver
settings; physical effects are not labelled integration discrepancies.
An optional `editorial-review.json` records reviewed human-report replacements;
the unedited FAST draft is retained in the report version's `interpretation.json`.
This review changes neither upward child reports nor scientific credit.
This revised study searches trajectories; it does not claim the old builder
workflow's survival-probability map or sampling/qualification criteria.

The historical `.artifacts/communication-live-first/` demonstration used the former
independent composer. Current communication regressions use actual nested method
loops with labelled synthetic saved observations and fake models, verifying the
child's final form, exact next-parent input, credit-source association and retirement.

Browser verification uses the optional `verification` dependency and the installed
Chromium executable `/snap/bin/chromium`:

```bash
.venv/bin/python tests/viewer_browser_check.py .artifacts/adaptive-storage-first \
  --output .artifacts/browser-check
.venv/bin/python tests/progress_browser_check.py .artifacts/adaptive-storage-first \
  --output .artifacts/progress-check
```

`tests/live_viewer_demo.py --run NEW_DIRECTORY --output EVIDENCE_DIRECTORY` can
exercise a new adaptive run with the local viewer already running, including
interruption/resumption. It intentionally requires a fresh run directory.
