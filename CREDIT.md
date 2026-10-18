# Scores, credit, yield estimation and continuation

The numerical binding has three separate responsibilities: assign credit from
measured scores, estimate future marginal yield, and decide whether to continue.
The controller connects those functions to the real method_loop. It does not
smooth or decay either measured credit or the estimator's returned prediction.

Every observation is retained. There are no scientific acceptance gates, proof
prerequisites, numerical agreement thresholds or required branch visits.

## Measured score and assigned credit

The simulator returns the agreed recurrence score

```text
S = sum(observed_cycle_duration * phase_aligned_similarity)
```

Its physical definition is unchanged: compare successive winding cycles using
position, velocity and relative-period mismatch; the first revolution supplies
the reference. Partial subsequent revolutions contribute their observed duration
and similarity. This score is neither residence time nor proof of indefinite
stability. Its duration weighting belongs to the agreed simulator measurement,
not an additional controller reward for running an integration longer.

Each Episode's explicit score assignment determines which machine-scored
observations belong to its objective and scope. Credit retains the best observed
assigned score; a turn's marginal credit is the improvement over the previous
best. A worse observation remains in the evidence with its actual score and
contributes zero improvement. The recorded observation is never replaced with
the historical best. Repeats cannot manufacture additional improvement.

The root assignment uses observations of its fixed complete physical scenario.
Parts and math can use scored observations of their assigned subproblem locally.
A reduction retains its own measured score and declared scope; its easier motion
does not silently become a complete-model root result. Typed findings can still
inform the parent's next decision without a numerical knowledge bonus.

The initial non-root assignment includes all trajectories acquired in that
Episode, including explicitly reduced observations returned by children. Their
scope remains attached. A high-scoring reduction can therefore prolong a local
investigation; its local credit is not a complete-target score. Only the root
applies the fixed complete-target projection, and no parent imports a child total.

One completed `sim.run` performs one integration and returns its score. A comparison analyses
already-saved observations; it does not execute two new integrations inside one
Episode turn. Comparison-only or mathematical work without a newly improved
assigned score can honestly have zero marginal credit. Tool-call counts, prose,
proof attempts and branch visitation do not receive automatic bonuses.

The workflow's physical observation window is `[0, study.horizon]`. A request
outside that domain returns typed `sim.request_diagnostic` feedback before
integration. This is one acquired feedback unit with zero marginal credit and
no simulation score; it does not stop the Episode or alter any existing score.
The standalone simulator can omit this workflow-owned window. Stored forcing
must cover an integration only when the forcing term is enabled.

`math.arithmetic` calculates a single scalar expression over supplied finite
measurements. Math, simulation and simparts Episodes can use it directly. It
retains its value or typed numerical diagnostic as one acquired unit, with zero
marginal credit unless actual projected scored evidence improves the assignment.
It neither simulates new evidence nor substitutes an arithmetic value for S.

A turn is one acquired unit in the currently executing Episode. Its own math
tool, saved-observation comparison or `sim.run` each advances that local controller
once. Acquiring a complete child investigation advances the parent once,
regardless of the child's internal turn count. Those internal acquisitions belong
to the child's own estimator history. Planning/report model calls do not
independently advance a controller. Every acquired unit contributes one actual
marginal-credit value; a non-improving math or comparison unit contributes zero.

A malformed encoded planning proposal has no acquired unit. Typed parser
feedback asks the model for a well-formed proposal at the same controller state;
the original and corrected proposals stay in the model cache. No marginal-credit
observation enters the estimator for that formatting attempt. Once a declared
arithmetic tool executes, its numerical diagnostic is an acquired unit as above.
The deterministic planning `proposal_index` serves cache identity and has no
role in credit, yield fitting or continuation.

The parent projects actual machine-scored observations and applies its own score
assignment. It does not add a child's scalar total, nor does it trust a model to
write numerical credit. Parent report synthesis remains a separate typed FAST
model operation.

## Yield estimator

The estimator receives exactly one real-valued marginal-credit observation per
local acquired unit, including zeros; not every such unit is a simulation run.
It does not receive observation identities, simulation duration, velocity
anchors or discrete bins. Credits are not rounded,
thresholded into discoveries, or converted into repeated identity events.

The replacement estimator is derived from nano-graphrag's numerical rarefaction
template at revision `60a167f9eeda0c9ea2ca294724174948947baf3f`, source SHA-256
`02af19652d69f368ee8875d3b27cad0bb2bbc8d1f8274344b72a4437092cdd35`.
The [vendored source and license](orbital_workflow/vendor/README.md) preserve that
provenance; [score_yield.py](orbital_workflow/score_yield.py) declares the adaptations. It fits
the observed credit history afresh using the template's curve/fitting structure,
adapted to fractional responses through a quasi-likelihood. Its prediction bands
are approximate and depend on the fitted model; they are not calibrated
confidence guarantees.

`window_size` and `subsample_size` retain the template's minimum-information
semantics: minimum completed turns and minimum evaluated/scored turns before
fitting. Neither is a rolling-average length in this template. Each fit uses all
observed turn credits. They belong to yield estimation, not a controller smoothing
layer or a forecast horizon. Insufficient information is represented explicitly by the
estimator rather than an invented decaying prediction. There is no `memory` or
`forecast_memory` parameter in the repaired binding.

Each Episode's settings declare `continuation_cost` and nested `yield` settings.
The starting estimator values are `window_size = 8`, `subsample_size = 4`, and
`uncertainty_alpha = 0.05`. These are estimator/continuation settings, not a
scientific acceptance threshold or a fixed Episode length.

## Continuation

An independent numerical continuation function consumes the estimator's current
band and the Episode's declared continuation cost. It stops only when the band
is ready and its upper bound is at or below that cost. Unavailable predictions
continue. Its outcome concerns
the expected usefulness of another acquisition, never whether an observation is
accepted or whether the scientific objective has been solved. An unavailable or
unstable estimate remains distinguishable from a numerical prediction of zero.

The chosen estimator owns all history selection, subsampling, averaging and
fitting. The controller records its current output as returned. There is no
additional EWMA, prediction multiplication, hidden grace period or arbitrary
Episode iteration cap.

The fit uses a declining-rank yield model; a late discovery can violate that
assumption. Credit units also affect the working quasi-likelihood's effective
information and must remain fixed within an Episode. These limitations and fit
diagnostics are recorded with the estimate.

The inherited numerical fitter uses one local optimization path, without a
global optimum or convergence certificate. Different history lengths can lead
to different local solutions and abrupt changes in the approximate band, even
after zero-credit turns. This is a limitation of the retained fitter, not a
reason for a controller to edit turn credits or smooth its predictions.

## Removed historical binding

Runs made before this repair used a different binding: horizon-normalized
persistence plus a velocity/environment-anchor support proxy, separate forcing
support unions, and an EWMA forecast initialized with a prior prediction. The
binary expanded that proxy from 8 to 32 model variants. That machinery is removed
from the live credit path. Its coverage values did not measure knowledge, and a
confirmed indexing error further invalidated its environmental support mapping.

The user's earlier equal weighting of persistence and knowledge is preserved as
design history. Removing the broken support proxy does not supply a replacement
knowledge metric. The repaired executable score path uses the explicit measured
score assignment; it must not be described as an implemented 50/50 knowledge
objective. Defining a useful additional knowledge score remains separate work.

Historical run records retain their original credit and stopping provenance.
They are not rewritten under the replacement estimator. New end-to-end runs and
their verification must be reported separately from the old demonstrations.
