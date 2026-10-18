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

The root initially gives equal weight to orbital persistence and knowledge gained.
`study.toml` stores these root weights separately from implementation code so they
can be tuned after observing actual runs.

These are root weights only. Every Episode has its own task-specific credit
scheme, repeated unit, and continuation calculation. A parent assigns credit to
a child's contribution using the parent's own scheme. Child scalar credit is
not automatically added to parent credit, and the root weights are not propagated
to descendants.

The initial equal root weighting and Episode-local credit ownership are settled.
Detailed numerical formulas, parent projections, and component normalization are
implementation choices to make explicit and tune using observed behavior. Equal
coefficients alone do not give equal influence to quantities expressed in different
units. The existing OpenChia identity/incidence credit implementation must not be
assumed to implement continuous scientific credit without examining its semantics.

Run records should retain the root weighting configuration, both component
contributions, their weighted contributions, and each Episode's local accounting.
Changing weights must remain distinguishable from an improvement produced by an
iteration; historical records retain the configuration used to calculate them.

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

## Model routing

The user selected the existing model connection, with two configurable roles:
FAST = gpt-6-luna / reasoning effort none; REASONING = gpt-6-sol / medium.
The adapter uses the existing Codex login with per-conversation overrides.
The initial routing is REASONING for Episode decisions and FAST for report
synthesis. Both roles have completed a real structured-response connection probe;
scientific credit and numerical continuation remain outside the model adapter.
