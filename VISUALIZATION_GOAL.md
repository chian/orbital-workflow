# Goal: watch and compare any orbital workflow run, including active runs

Build a generic visualization of observations produced by this episodic workflow.
Open it on request for any run directory, including while that run is still
executing. Refresh as observations arrive, preserving the user's selection and
playback controls. The existing thirteen-observation run is a development dataset,
not a fixed input, fixed capacity or special-case implementation.
Work persistently through implementation and observed defects until the viewer
and its interactions have been exercised against real saved and active-run data.

## Experience

- Default to automatic playback of the entire acquisition history, retaining
  repeated observations and both sides of comparisons. Show earlier comparable
  trajectories and recurrence history. Keep individual playback and comparisons.
- Play, pause, reset, change playback speed and scrub absolute simulation time.
- Select a primary observation and overlay other saved trajectories. Include
  complete-model cases, reduced models and individual numerical refinements.
- Show the spaceship's current position, velocity direction and observed trail.
- Show the changing acceleration field for the primary observation, using its
  actual model terms, environmental inputs and stored forcing realization.
- Synchronize radius, speed and recurrence plots with the time cursor.
- Display the selected insertion velocity, environment, active model terms,
  forcing seed, numerical settings and physical observation outcome.
- Open any run by directory and show newly completed observations during execution.
  An empty run has an explicit waiting state. The default tour waits for more data
  and continues in order. New data preserves deliberate individual inspection. Provide a live refresh control and an
  optional follow-latest mode.

## Data and interpretation

Use saved trajectory samples and cycle measurements with their artifact identities
retained. Linear interpolation may move the display marker between saved states;
label that behavior. Stop motion at each observation's saved endpoint, including
early exits. Distinguish observations that have not started or have ended from
currently observed motion. Display recurrence as completed cycle measurements,
without inventing a continuously measured score between cycle endpoints.

The field overlay evaluates the same stated acceleration equation with the stored
forcing interpolation. Field arrows communicate direction and relative magnitude;
their display scale is not a new physical quantity. Reduced and complete models
remain explicitly labelled, and longer observation is distinct from recurrence.

## Delivery

Keep all code, tests, dependencies and generated artifacts inside this directory.
Provide a generic local viewer command for a chosen run and a live viewing URL,
as well as a standalone HTML export that works offline. Preserve the existing
scientific records, credit, typed Episode
communications, source-bound resume identity and exportable scientific plots.
The viewer is a separate read-only presentation of those observations.

## Closed episodes and memory

Each simulation_investigation and simparts episode publishes a versioned standard
manifest on disk. It identifies the episode, parent, declared scope and inputs,
completion state, compact typed report, simulation observations, trajectory/forcing
files and detailed audit/log files. Array data stays in numerical files referenced
by the manifest, rather than copied into JSON logging records.

After closure and parent report delivery, release the closed episode's controller,
model conversation history, raw findings and detailed logging objects from memory.
Retain compact typed reports, disk references and the numerical accounting state
needed by active parents. Audit data remains reloadable from disk. Preserve parent
credit ownership, typed report admission and durable replay while changing storage.

The live viewer reads a small run/episode index, loads selected observations on
demand and bounds its data cache. Opening or refreshing a long run does not load
every closed episode's arrays or logs into either server or browser memory.
Target the new format directly. Backward compatibility is not required. Keep old
run files as historical evidence, execute the revised workflow end to end again,
and visualize only fresh runs produced with this storage lifecycle. Demonstrate
eviction and on-demand reloading with growing/nested episode histories.

## Demonstration

Exercise the viewer in a real browser using the saved adaptive run, another
workflow run and observations arriving in an initially empty active-run directory:

- Playback changes time; pause holds it; reset and scrubbing position it correctly.
- Observation selection and comparison update the displayed trajectories and data.
- Early exits and horizon endpoints do not extrapolate physical motion.
- Field direction and magnitude use the declared terms and the saved forcing at
  the selected absolute time.
- Representative early, middle and terminal times render without browser errors.
- Refresh discovers new observations while the workflow continues; selections and
  time remain stable unless follow-latest is explicitly enabled. Partially written
  files are handled as pending acquisitions, not interpreted as completed data.

Retain screenshots and concise interaction evidence. Document any remaining
visualization limits and explain how to open it. A mock-up or unexercised HTML
file does not complete this goal.

## Completion — 2026-10-17

Completed against fresh data produced with the revised storage lifecycle:

- Adaptive run: `.artifacts/adaptive-storage-first/`, 14 observations and 6 closed
  Episodes. The viewer was opened before the run directory existed and discovered
  observations while live model decisions continued.
- The same browser preserved its primary selection, time and paused state during
  catalog growth; explicit follow-latest changed the primary. A deliberate
  interruption resumed the same fresh run with 17 saved evidence files unchanged.
- The completed replay used zero fresh model or tool calls and retained identical
  records and credit. All 11 tool operations also reproduced exactly on fresh
  numerical replay.
- Fresh diagnostic: `.artifacts/viz-storage-smoke-second/`, 3 observations including
  central-only, modulated and complete dynamics, with nested simparts on disk.
- Automated suite: 28 passing tests, including nested/growing memory release,
  accounting identity and on-demand exact numerical range reads.
- Browser: 43 interaction checks on the adaptive run, 20 on the fresh diagnostic,
  plus 5 run-switch/cache/export checks. Independent field calculations matched
  saved forcing and each observation's declared terms. No browser errors occurred.
- Live service: http://127.0.0.1:8767/ . The run path picker opens any fresh run.
- Offline comparison: `.artifacts/adaptive-storage-first/visualizations/playback.html`
  initially embedded 6 chosen observations. The requested extension below now
  exports the entire run by default; explicit subset exports remain available.
- Evidence and screenshots: `.artifacts/visualization-verification-first/`.
- Standard format/lifecycle: `STORAGE.md`. Complete scientific findings and the
  exportable figure are linked from `.artifacts/adaptive-storage-first/REPORT.md`.

Limits: live refresh exposes completed tool observations, not in-progress solver
steps. Display trajectories use at most 10,000 saved states each and labelled
linear interpolation; authoritative arrays remain on disk. Cached numerical data
has an explicit budget; compact catalog/accounting metadata still grows with a
run. Offline exports retain embedded saved packets and decode current selections on demand; the embedded file itself still occupies memory. Native hidden
reasoning is not restorable; visible model exchanges and deterministic acquisitions
are restored from disk. One typed child report omitted supplied measurements;
that report-composition limitation is preserved in communication-review.json for
behavior tuning. It does not alter the raw viewer observations or parent credit.


## Requested extension — run progress and forcing terms

The default is now an automatically playing acquisition-history tour. The fresh
adaptive run has 17 observation appearances across 11 acquisitions, with 14 distinct
trajectories. Repeats and matched-comparison sides remain visible. Previous/Next,
a history slider, clickable recurrence history, pause, reset and full-run looping
coexist with individual trajectory playback and explicit comparison selections.
Each observation receives the selected screen duration; physical time is labelled.
Earlier paths and best-so-far measurements use matching declared conditions only.
Live tours wait at the end of available work and continue as new entries arrive.

The field now separates exact central, modulation, rotating and stored random
contributions. Orange/purple/pink arrows and per-term controls expose their spatial
and temporal structure. Display magnification is explicit and does not affect
numeric values. The random push has no spatial source: it is uniform in space at
a given time; the rotating term depends on position, and modulation remains radial.

The offline file was rebuilt for the entire fresh run, with packets decoded on
demand. Numerical working sets remain bounded during the tour. Individual playback
passed 43 browser checks; the complete automatic tour and overlays passed 9 more,
including waiting/continuing under an explicitly labelled live-prefix fixture.
All 30 automated tests passed. Browser evidence and screenshots are in
`.artifacts/progress-forcing-verification/`. These presentation changes preserve
the scientific execution fingerprint and stored credit.
