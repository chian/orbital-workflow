# Simulator parameter ownership

Status: ownership repair implemented, 2026-10-18, after the user authorized the
fix and a fresh launch. `ScenarioSimulator` now freezes the complete definition,
owns one forcing realization, and resolves both scientific and public CLI calls.
The tables below retain the inspected pre-repair paths as the reason for this
change. Focused verification is described at the end; a fresh scientific launch
is separate from these component tests.
The original audit missed this ownership violation; its frozen reports are not
being rewritten to imply otherwise.

The user requires that the forcing and all simulator parameters other than the
spaceship belong to the scenario. Episodes investigate spaceship trajectories.
They do not redefine the simulator. Earlier authorization also allows explicit
simparts investigations of reductions, regions, segments and numerical
refinements. These operations must derive an experiment from the fixed scenario
without acquiring ownership of its base settings.

## One authority and its consumers

The scenario configuration supplies one immutable resolved problem, including
its forcing realization, observation and numerical recipe. A scenario-bound
simulator owns that definition and constructs private execution requests.

The trajectory-search Episode chooses the authorized ship insertion velocity
`vx, vy`. The scenario currently fixes insertion position and initial time. A
reference velocity is guidance, not another source of defaults.

A simparts Episode chooses an investigation and an explicit derived experiment.
Its request can identify a term to omit, source contribution, region, recorded
segment or refinement operation, including the coordinates, endpoints and
refinement values needed for that experiment. The simulator applies that operation
to its scenario without changing the base settings. A derived-operation interface
must not silently restrict these authorized investigations to a preset catalog.

The mathematical tools query the same scenario and perform stated calculations.
Credit projects recorded scores. The yield estimator and controller manage
continuation. None of those mechanisms supplies simulator parameters.

Private execution records retain the full resolved specification and provenance
for replay. Their completeness is not permission to expose those settings as
Episode tool arguments, child assignments or required upward report fields.

## Complete request-field map

The following covers every current `SimulationRequest` field and the extra
model-facing arguments translated by `ScientificBindings`.

| Parameter | Owner and legitimate use | Inspected pre-repair path and ownership risk |
| --- | --- | --- |
| `vx`, `vy` | Episode: authorized spaceship insertion velocity. | Binding has independent omitted-value defaults `0,1`; explicit `initial_state` can supersede the proposed velocity. |
| `initial_state` | Host composes fixed scenario position with selected velocity. A continuation operation uses an actual saved state. | Episode can supply all four components directly. |
| `forcing_id` | Scenario-bound simulator: private reference to the one saved realization. | Binding rejects direct Episode references but lets `trial` select another realization. Raw dispatcher callers supply the reference directly. |
| `trial` | Scenario configuration only; not an Episode argument. | `simulation_arguments` accepts it per call and selects/generates another forcing pattern. |
| `a` | Scenario: fixed modulation amplitude. | Episode can override the engine default `.15`; complete-model classification allows any member of `study.a`. |
| `sigma` | Scenario: fixed forcing amplitude. | Episode can override the engine default `.03`; complete-model classification allows any member of `study.sigma`. |
| `terms` | Scenario: complete physics. An explicit simparts operation derives a mask. | Complete SIM requires all enabled. Simparts masks are authorized; their derived scope must remain distinct from the base scenario. |
| `scenario_id` | Scenario host: immutable identity. | Scientific binding checks/installs it correctly; standalone dispatcher bypasses that binding. |
| `gravity` | Scenario: kind, masses, separation, initial orbital phase and collision radii. | Scientific binding checks/installs it correctly; engine and raw tools also have independent complete-specification inputs/defaults. |
| `active_bodies` | Simulator derives source isolation from an explicit simparts experiment. | Choosing source contributions is authorized in simparts; it must not redefine the source system or the base run. |
| `gravity_mode` | Simulator derives an approximation from an explicit simparts experiment. | Choosing the monopole approximation is authorized in simparts; it remains a derived experiment. |
| `start`, `end` | Scenario evaluation interval. An explicit derived segment/continuation operation may request other endpoints. | Inputs must be finite, ordered and inside the window, but this does not distinguish a derived segment from the full scenario evaluation. Shortened observations currently enter root score projection. |
| `observation_window` | Scenario host: fixed evaluation domain. | Scientific binding installs/checks it, but standalone requests can omit it. |
| `radial_limits` | Scenario: observation/terminal boundaries. | Binding supplies a default rather than owning the value; complete-model classification subsequently checks equality. |
| `spatial_box` | Simulator derives a regional observation from an explicit simparts experiment. | Region coordinates are legitimate simparts choices. Their derived observation scope must not overwrite the base boundary. |
| `method` | Scenario numerical recipe; simulator executes it. | Episode can override default `DOP853` and pass the method to SciPy. |
| `max_step` | Scenario numerical recipe or simulator-defined refinement operation. | Episode can override `.05`. |
| `rtol` | Scenario numerical recipe or simulator-defined refinement operation. | Episode can override `1e-7`. |
| `atol` | Scenario numerical recipe or simulator-defined refinement operation. | Episode can override `1e-9`. |
| `sample_step` | Scenario numerical/measurement recipe or simulator-defined refinement operation. | Episode can override `.02`, changing the recorded sampling used for measurement. |

The pre-repair `scenario_problem()` only resolved identity/name, insertion position,
reference velocity, radial limits, suggested amplitudes and gravity. It does not
resolve fixed amplitudes, forcing, solver or complete evaluation settings.
`study.a` and `study.sigma` are arrays, while `suggested_a` and `suggested_sigma`
are recommendations. They do not define one fixed physical problem.

## Other settings and constants

| Setting | Responsible component |
| --- | --- |
| `G=1` and the gravitational equations | Simulator's declared physical model and units. Scenario supplies source-system parameters. |
| Modulation frequency `.7`, rotating amplitude `.02` and frequency `.4` | Fixed scenario physics; currently constants in `integrate`, also repeated in model-facing explanatory text. |
| Forcing grid `.1`, AR coefficient `exp(-.2)`, seed rule `20261005 + trial` | Scenario forcing recipe; currently constants in `generate_forcing`. The resulting arrays are generated once and retained. |
| `PCG64DXSM`, normal sampler, float64, linear interpolation, knot segmentation | Simulator implementation/provenance. Episodes do not select these. |
| Persistence position/velocity/relative-period scales and phase samples | Fixed measurement configuration, loaded by the host into the evaluator. |
| Recurrence formula and reference-cycle semantics | Measurement implementation; the score is recorded as produced. |
| Episode credit target and inherited baseline | Episode assignment and numerical credit binding; no authority over simulator configuration. |
| Yield window/subsample/uncertainty and continuation cost | Episode controller configuration; no authority over simulator configuration. |
| Model choice, effort and routing | Workflow/model configuration; no authority over simulator configuration. |
| Observation identity, cache key, array paths and ownership index | Runtime/storage; derived from actual execution, not Episode-selected physics. |

## Caller paths that must remain coherent

- Scientific work currently translates model arguments in
  `ScientificBindings.simulation_arguments`, then sends a complete `ToolAction`
  through `CachedTools` and `ToolDispatcher` to the engine. The scenario binding
  should live at the simulator capability boundary, with one resolver.
- The CLI `tool` command currently sends a request file directly to the raw
  dispatcher, bypassing scientific scenario binding. A public scenario tool must
  use the same resolver; an explicitly internal replay interface may accept a
  saved complete specification without treating it as an Episode proposal.
- Smoke/demo sources construct explicit engine specifications as diagnostic
  fixtures. They must remain labeled diagnostics, not a competing scientific
  scenario resolver.
- Replay consumes the saved resolved specification, including saved forcing. It
  must not reinterpret old work using new defaults.
- Comparison consumes existing observations and performs no simulation.
- Credit's `physical` representation intentionally canonicalizes inactive terms
  and omits solver/end details. It is a derived accounting view and cannot serve
  as the simulator's authoritative execution specification.
- Child forms carry requested trajectory measurements and interpretations.
  Scenario-owned settings need no parent-to-child forwarding or upward recopying.
  A derived experiment's meaning must remain identifiable without promoting its
  result to the complete scenario.

## Observed evidence, not only permitted behavior

A read-only inspection of all 227 successful saved `sim.run` cache entries in
`.artifacts/scenario_02/run-scored-007` found:

- Every raw request used `a=.15` and `sigma=.03`. The code permits variation, but
  variation of these two amplitudes was not observed in this run.
- Three forcing seeds were actually used: `20261006`, `20261007`, `20261008`.
- Among entries with complete force terms, resolved gravity, all sources and no
  spatial box, 186 used the first seed, 17 the second, and 5 the third. These are
  distinct saved cache entries, not Episode-turn counts.
- Every requested start was `0`; requested ends included `7.4`, `39.5`, `41.5`,
  `45` and `125.66370614359172`. The original saved records identify which were
  derived observations. An early physical exit is distinct from a requested
  shorter interval.

The audit had identified false trial labels and omitted interval provenance. It
failed to apply the fixed-scenario ownership requirement to the underlying ability
to change those inputs. Reporting them more accurately alone would not fix that.

## Implemented repair

1. Define one immutable scenario specification containing fixed scalar physics,
   one saved forcing realization, and numerical/measurement/evaluation settings.
2. Bind the simulator to that specification once. Expose ship velocity for a
   complete-scenario run. Remove scenario-owned arguments from Episode calls and
   parent/child assignments instead of forwarding and rechecking them downstream.
3. Keep explicit simparts operations as derivations from that same specification,
   with provenance identifying the experiment. Preserve their authorized choices
   of masks, source subsets, coordinates, endpoints and refinement settings. Do
   not mutate the base scenario or add a preset-only restriction.
4. Generate trajectory/score facts for the parent form from the actual saved
   observation. Preserve child-owned typed interpretations and parent field
   selection. Keep form admission separate from numerical credit and stopping.
5. Use temporary software fixtures to verify that all public entry paths use the
   same scenario, ordinary ship trials reuse identical forcing, derived work
   cannot overwrite the base, and replay consumes the saved resolved request.

The reference case already used `.15`, `.03`, seed `20261006`, horizon
`125.66370614359172`, `DOP853`, max step `.05`, tolerances `1e-7/1e-9`, and sample
step `.02`. Those are the concrete existing values available for a fixed
definition; moving them into configuration must be explicit, rather than
pretending the existing arrays/suggestions already establish that definition.

The executable implementation is in `scenario.py`, with fixed scalar settings
in all three study configurations and the same physical constants recorded in
private `SimulationRequest` objects. Public ordinary runs require exactly `vx`
and `vy`. Explicit simparts descriptors retain arbitrary authorized mask, source,
scope and numerical-refinement values. Continuation takes an actual saved run's
terminal state, never a model-supplied replacement state. The shared pure scope
predicate distinguishes full-interval base observations from derived segments;
same-physics full-interval numerical refinements remain base measurements.

Nine focused scenario tests passed, including immutable ownership, one forcing
allocation, ordinary parameter rejection, arbitrary derived values, pure scope
projection, exact reference forcing/RHS/trajectory preservation, saved-state
continuation, complete private replay specifications, and public CLI parity.
Thirteen existing private-engine numerical/scope contracts also passed. These
component checks made no model/provider calls and launched no scientific
workflow. Historical run data and frozen snapshots were not changed.
