# Initial continuous credit binding

These are configurable starting formulas for tuning from observed behavior.
Every observation is retained. No observation needs to pass a scientific
qualification, and no proof or numerical agreement is required to contribute.
The numerical controller predicts further marginal credit; its stopping decision
does not label a scientific finding successful or unsuccessful.

## Persistence discovery

For each of the twelve environmental cases, retain the largest **observed**
duration-weighted recurrence S, divided by the physical horizon T. Average these
twelve components. This measures discoveries in the complete field from position
(1,0), with the original radial observation region. It does not measure survival
probability, expected performance over forcing, or indefinite stability. Cases
without observations contribute zero discovery credit; their results are unknown.
Keep the velocity, forcing realization, and scope with every observation.

The maximum is a discovery high water mark. A subsequent numerical refinement may
measure a lower S; that lower measurement is retained explicitly and never
replaced with the high water mark. Historical discovery credit and the current
physical estimate are different quantities. Selection over velocities and forcing
realizations makes the high water mark optimistic about general performance.

Reduced models and scoped observations contribute knowledge immediately. Their
longer persistence does not become persistence in the complete field.

## Knowledge support

The initial knowledge component is a **smooth evidence-support proxy**, not a
calibrated measure of truth or Bayesian uncertainty. A configurable reference
family contains velocity anchors, the twelve environments, and eight combinations
of modulation, rotation, and forcing with central attraction enabled. These are
coordinates at which evidence support is measured, not required simulations.

Each observed trajectory supplies Gaussian support in velocity and relevant
environment coordinates within its own model variant. Disabled terms remove
irrelevant environmental dimensions. Support grows continuously with observed
duration and nominal numerical resolution:

    q = (1-exp(-duration/duration_scale)) /
        (1+(sample_step/sample_scale)^2 + rtol/rtol_scale
           +(max_step/integration_step_scale)^2)
    support(anchor) = q * exp(-distance_squared/2)

These resolution factors describe declared numerical work, not a verified error
bound. Actual solver diagnostics and refinement differences remain separate
observations. Unobserved motion is never supplied by the support calculation.

For each forcing realization, take the maximum support at each anchor. Thus
repeats, overlapping requests, and refinements never earn independent-sample
credit. Combine independent forcing groups as `1-product(1-support)`. Deterministic
requests share one group irrespective of their nominal seed. An exact central
conic derivation provides central-reference support with its assumptions retained;
repeating or paraphrasing it provides no additional support. Average anchor support
for the component. Prose, suggestion counts, tool calls, and branch completion have
no automatic credit.

This proxy favors characterizing a declared input neighborhood. It does not yet
evaluate predictive calibration, causal understanding, or usefulness per token.
Those limitations are exposed for subsequent tuning, not hidden behind a score.

## Ownership and continuation

The root weights persistence and knowledge equally. Mathematical exploration
initially measures central-reference guidance support locally. Simulation and
simparts combine full-model persistence and broader support with their own
weights. `study.toml` holds all weights, scales, and continuation settings.

A child returns machine evidence and scientific findings. The parent independently
recomputes its components from projected evidence on the parent's scale. It never
adds the child's scalar credit. Parent-selected report synthesis is a separate
FAST model call and cannot assign numerical credit.

Every iteration pursues improved total credit. Zero-yield attempts remain in the
history. Duplicate evidence supplies zero extra credit. An exponentially weighted
moving average of observed marginal gains, initialized with an explicit prior
prediction, forecasts the next gain. Continue while that prediction exceeds the
Episode's configured continuation cost. This is a transparent initial heuristic,
not a statistically calibrated claim. Its prediction errors are recorded.
There are no iteration limits or scientific acceptance thresholds.


## Multiple-source scenarios

The same support calculation extends the declared source-model axis: scenario_01
has its one resolved source, while scenario_02 distinguishes a monopole reference,
body_1 only, body_2 only and both resolved sources. Each has the eight original
perturbation combinations. Model-variant labels are recorded explicitly. The root
and local weights and continuation costs are retained; no credit bonus rewards
visiting math or simparts. Absolute coverage values are normalized over different
model families and are not directly comparable across scenarios.

The root's full-model persistence component uses that run's saved gravity system,
all source forces, resolved mode, agreed insertion and declared observation domain.
Reduced-source evidence contributes knowledge immediately on its stated model
variant. The winding measurement remains barycentric; path novelty, planet-relative
recurrence and non-winding cycles have no new reward in this version. See
[SCENARIOS.md](SCENARIOS.md) for the exact reductions and initial results.
