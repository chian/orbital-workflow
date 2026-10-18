# Episode storage and working memory

Closed Episode logs belong on disk. Active parents retain typed reports, disk
references and numerical accounting state; they do not retain a child's recursive
trace or its raw findings. The same storage format supplies the viewer during and
after a run.

## Version 1 layout

`episode-store/episodes/<episode_id>/manifest.json` is a versioned JSON record with
the format name `orbital.episode`, episode/run/parent identities, kind, path,
completion, and references to request, audit, result and typed parent-report files.
Its observation list contains references to observations owned directly by that
episode. Recursive simparts are separate episodes with their own manifests.

`episode-store/observations/<observation_id>/manifest.json` has format
`orbital.simulation`. It declares the owning episode and unit, physical request,
observed time interval, outcome, sample count, scalar recurrence summary and
references to the trajectory, stored forcing and full cycle measurements.
Original immutable JSON/NPZ artifacts remain authoritative. Numerical NPY files
provide arrays that can be read by time range without loading an entire run.

A compact observation index contains metadata and file references. It contains
neither trajectory samples nor detailed logs. Entries appear after tool completion,
so an active viewer can discover observations before their Episode closes. A
manifest is published atomically after its referenced files have been written.

## Episode closure

The existing method_loop still owns execution, typed report admission and parent
credit projection. The local binding writes the completed trace/result and typed
report, then replaces the in-memory child trace/result with compact disk-backed
records. Closed controller instances, model histories and child-only logging
references are released. Parent credit retains the numerical measurements it
needs, with raw cycle/solver diagnostics kept in the saved observation instead.

The repaired credit path retains machine-scored observations with their physical
scope, the best assigned score and per-turn marginal improvements. Yield inputs
are those real-valued improvements; they are not child scalar totals or artifact
identity counts. The estimator owns its history/window policy. Disk references
and compact numerical state do not authorize raw child logs as parent model input.

Report composition may read the closing child's evidence while completing the
parent contract. That temporary working set is released after delivery. Detailed
records remain available for audit or explicit reloading; eviction is not deletion.
No scientific gate, credit reset or child-scalar summation is introduced.

Whole-run crash replay reconstructs existing method/controller/report history.
It is not a closed-investigation reopening API: a completed stopped child remains
closed, and a new child invocation has a new local scope. The earlier promise to
reopen an investigation with its original Goal, numerical history and admitted
reports requires an explicit lifecycle design; simply replaying `ResumeUnit`
inputs would not restore the report history or override a terminal stop.

## Viewing fresh runs

The local viewer reads the index first and fetches selected observations on demand.
Server and browser caches have explicit bounds and evict unselected data. Closing
or changing a view does not require keeping all closed Episode arrays resident.
Time-range reads use numerical files rather than recursively loading Episode logs.

Fresh runs publish this format during execution. Backward compatibility is not
required. The revised workflow will be run end to end again and visualization
demonstrated using those fresh records. Changes to execution bindings are recorded
in new run fingerprints; historical scientific evidence stays under its original
identity.

Each new run also freezes `scenario.json` and copies the project and actual
method_loop source into `source-snapshot/`. This is executable provenance on disk,
not additional Episode memory. After execution code changes, restore from the
run's snapshot working directory with that snapshot as `--method-loop-source`;
the saved execution identity still checks all critical source hashes and numerical
library versions. Exact commands and scenario references are in
[SCENARIOS.md](SCENARIOS.md).

## Historical storage verification before the score/yield repair

The runs in this section were fresh when originally performed. They used the
removed anchor-support/EWMA binding. Their records remain useful historical
storage and replay evidence, but their credit numbers and test counts do not
verify the replacement score/yield estimator. New end-to-end verification must
be recorded separately.

The storage-era adaptive run was `.artifacts/adaptive-storage-first/`: six closed
Episodes, fourteen distinct observations, and eleven specified simulator tool
operations. Five simulation investigations delivered typed reports to the root.
Its final discovery credit is 0.06506422930986647. Restoring the completed run
reused twenty-one model responses and eleven tool operations with zero fresh calls;
all saved records and credit agreed. Fresh numerical replay reproduced every tool
finding and artifact reference exactly.

The diagnostic `.artifacts/viz-storage-smoke-second/` exercised both
branches and recursive simparts, six Episodes and three distinct observations.
The adaptive model chose simulation investigations only; no branch visitation
was forced to produce the demonstration.

The lifecycle tests observe weak references while parents remain active. Closed
nested tool observations and controllers become unreachable. A growing history of
twenty diagnostic children retained compact parent references while more than
three megabytes of detailed child logs remained on disk. Compaction preserved
parent credit and duplicate evidence identity. Fourteen provider-process retirement
records across scientific execution and reporting corresponded to no remaining
owned process groups at verification time.

The viewer has metadata catalogs and an LRU cache of serialized selected numerical
payloads. Its server payload budget is 16 MiB, separate from the metadata cache.
The browser estimates retained payload memory with a four-times-serialized-size
budget of 16 MiB. These are cache policies, not guarantees of constant process RSS.
Active requests, decoding, a selected observation's cycle measurements and compact
catalog metadata still need working memory. Offline exports embed the complete
run by default, or an explicitly selected subset, with shared saved forcing.

See `.artifacts/visualization-verification-first/` for browser interactions,
live empty-to-completed checkpoints, preserved-file hashes, tests and screenshots.
One type-valid report omitted available measurements; the run's
`communication-review.json` records that observation. Its original report,
downstream decisions and numerical accounting remain intact. Type enforcement
constrains communication format; it does not guarantee a model's factual content.

## Acquisition-history playback

The viewer additionally reads compact ownership files and Episode manifests to
reconstruct the completed simulation acquisition sequence. It preserves repeated
observations and both sides of comparisons without loading recursive audit logs.
The current ownership format supplies order through original file publication
timestamps; preserve file timestamps when copying or archiving a run. Index
metadata supplies each trajectory's saved request and scalar measurements.

Default playback decodes the current trajectory and at most three earlier
comparables, releasing numerical working sets as the tour proceeds. Offline
exports include all observations by default as saved JSON packets and shared
forcing packets; selected packets are decoded on demand. Embedded packet text
still occupies memory in a standalone file. Explicit exports may choose a subset.
