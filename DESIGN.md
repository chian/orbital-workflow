# Orbital simulation: working decisions

This study is being designed and implemented directly with the user. The source
experiment is `../OpenChia/chia_orbit_test.md`. Demonstrating OpenChia's automated
construction process is outside this direct implementation's objective.

The current Episode design is in [EPISODES.md](EPISODES.md). It replaces the old
seven-Episode preparation/validation/reporting structure with two scientific
investigation branches under a trajectory-search root. Both branches can commission
an explicit simparts Episode for reduced-model, local, and comparative simulation
investigations. simparts has its own loop and credit scheme, calls the simulator
through explicit model/scope requests, and can commission a more focused simparts
child through declared self-nesting. Findings contribute on the invoking parent's
scale without scientific acceptance gates.

## Governing principle

Episodes exist to improve total credit. Each repeated unit pursues a marginal
increase in its Episode's credit. Attempts that yield no improvement remain in
the history and inform predictions of further yield; they must not receive
manufactured credit.

There are no scientific acceptance gates: no hidden gates, rejection thresholds,
or prerequisite checks before a result can contribute. Numerical discrepancies,
uncertainty, and independent comparisons supply measurements for iterative
improvement, rather than pass/fail admission of scientific results. This user
decision supersedes the original experiment's acceptance framing and the initial
proposal to gate results on numerical qualification.

## Root and local credit

Each Episode has an explicit score assignment, repeated unit, yield estimator and
continuation calculation. The simulator supplies the agreed recurrence score S;
credit records the best observed assigned score and each turn's improvement.
Worse measurements and zero improvements remain in the evidence. A parent applies
its own score assignment to projected machine-scored observations; it never adds
a child's scalar credit. Typed report synthesis is a separate communication path.

The earlier design gave persistence and knowledge equal root weights. The initial
implementation's anchor/coverage proxy did not establish a useful knowledge
metric and has been removed, along with its horizon-normalized persistence
aggregation. That historical 50/50 calculation is not the repaired live score
path. A replacement knowledge metric has not been invented as part of the repair.
Historical runs retain the original formulas and configuration that produced
their recorded numbers. See [CREDIT.md](CREDIT.md) for the current separation.

The yield estimator receives one real-valued marginal credit per Episode turn.
History selection, minimum-information windows, subsampling and fitting belong
inside that estimator. The replacement derives from nano-graphrag's numerical
template, preserves its fitting provenance, and reports approximate,
model-dependent prediction bands. The controller consumes the current estimate
without EWMA, memory, rounding, identity binning or artificial prediction decay.
Independent continuation consumes that estimate and explicit continuation costs.

## Proposed persistence measurement

Compare successive orbital cycles after aligning orbital phase, using position,
velocity, and cycle duration to obtain a dimensionless mismatch d_j. Measure
similarity continuously as q_j = exp(-d_j^2), and accumulate effective persistence
duration as S = sum(delta_t_j * q_j).

The user endorsed this starting metric. The implementation uses first-passage
angular alignment, configurable position/velocity/relative-period scales, and
partial overlap with the previous revolution. It records backward angular travel
and its limitations. The sum can reward separated stretches of repetition and
does not establish indefinite stability.

## Execution method

Use the actual generic method_loop semantics, including parent-owned child
invocations and reporting contracts, separate credit/report projections, and
controller-owned continuation. An exhausted source or a yield stop is an execution
fact, not a scientific success verdict. Scientific simulation horizons and sampling
checkpoints must not become arbitrary Episode iteration limits.

The runnable workflow is documented in [README.md](README.md). It uses the actual
OpenChia method_loop, explicit parent/child interfaces, and real simulator tools.
The finite diagnostic workload leaves scientific credit and yield estimates unset.
The scientific binding uses explicit formulas in [CREDIT.md](CREDIT.md), live
model proposals, separate FAST report synthesis, and numerical continuation.
Diagnostic source exhaustion does not assert scientific success.

Every `sim.run` is one scored integration. A comparison only analyses already-saved
observations; repeated simulation acquisition cannot be hidden inside one compare
turn. Explicit simparts remains the route for reduced or scoped investigations.

Whole-run interruption recovery restores the original cached execution through
the real method_loop. A newly commissioned child is a new local scope. Reopening
a previously completed, stopped investigation while preserving its Goal, numerical
history and admitted child reports is not implemented; the earlier promise of
that capability is an unresolved lifecycle design gap, not something the current
`resume` command supplies.

## Model routing

The user selected the existing model connection, with two configurable roles:
FAST = gpt-6-luna / reasoning effort none; REASONING = gpt-6-sol / medium.
The adapter uses the existing Codex login with per-conversation overrides.
The initial routing is REASONING for Episode decisions and FAST for report
synthesis. Both roles have completed a real structured-response connection probe;
scientific credit and numerical continuation remain outside the model adapter.


## Saved physical scenarios

The original single-source problem is scenario_01; scenario_02 is a planar circular
binary with a test spaceship. Each has a saved study configuration and separate
runs. Source trajectories are fixed physical inputs; two-source circular motion is
the exact mutual Newtonian solution. Bodies have physical collision surfaces, and
the binary barycenter is not an inner obstacle. The recurrence definition is retained;
the broken credit/forecast binding is replaced separately. Explicit source
force reductions, scoped score assignment and a binary reference calculation make
the new system usable through the same Episode/tool boundary. See SCENARIOS.md.
