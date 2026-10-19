# Episode design: searching for quasi-stable spaceship trajectories

## Scientific task and simulation capability

The environment supplies the gravitational sources, varying attractive field,
rotating noncentral field, and correlated random forcing. The simulation implements
those fixed equations.
It is a tool used during investigation; constructing the simulator is development
work rather than the scientific Episode's objective.

The search chooses a spaceship's initial velocity vector. The starting position
is initially the original (1, 0). Mass is omitted from the initial search because
gravitational acceleration is independent of spaceship mass, even with moving
sources. The ship is a test particle and does not perturb the source orbits.
Environment parameters describe the problem being studied rather than adjustable
spaceship parameters. Store forcing realizations and reuse them when comparing
spaceship configurations and numerical refinements.

Saved `scenario_01` retains the original fixed attractor. `scenario_02` uses two
mutually orbiting attractors with fixed masses and separation. Both use the same
Episode topology and typed communication boundary; neither requires a visit to
math or simparts. Source physics, reduced models, saved inputs and replay commands
are defined in [SCENARIOS.md](SCENARIOS.md).

The objective is to find trajectories with longer approximately repeating motion
and improve knowledge of their behavior. The starting persistence measurement is
the phase-aligned cycle similarity and effective duration described in DESIGN.md.
Approximate recurrence during an observation does not assert indefinite stability.

## Episode topology

```text
spaceship_trajectory_search
├── mathematical_exploration
│   └── simparts
└── simulation_investigation
    └── simparts

simparts may commission a more focused simparts child.
```

Each Episode type is a repeated acquisition loop with its own goal, units, score
assignment, yield estimator and numerical continuation calculation. Both branches
can perform their own tool operations and commission an explicit simparts child for
a smaller simulation investigation. These are declared parent/child edges. The
simparts-to-simparts edge is explicitly declared as self-nesting in EpisodeTree;
it is not an implicit tool recursion or an undeclared execution path. Each child
invocation has its own controller, linked goal, and parent reporting contract.

The root may use either branch according to the predicted opportunity to improve
its credit. It can obtain mathematical guidance or investigate a candidate
directly, including a new investigation informed by earlier contracted findings.
Mathematical guidance and formal proof are never prerequisites for simulation.
These branches are not a compulsory sequence.

## Root: spaceship_trajectory_search

**Goal:** discover and characterize quasi-stable spaceship trajectories in the
specified environment.

**Repeated unit:** commission a mathematical exploration or simulation
investigation, then measure that child's contribution using the root's scheme.
Each newly commissioned child is a new local scope. Whole-run crash recovery
preserves the original cached execution; reopening an already completed,
stopped child as the same logical investigation is not implemented. Preserving
its original Goal, controller history and admitted reports across reopening
requires an explicit lifecycle design rather than silently resetting accounting.

**Credit:** project actual scored observations from the fixed complete scenario
onto the root's own target. Retain the best observed assigned recurrence score S
and each turn's marginal improvement; do not add the child's scalar credit.
The earlier equal persistence/knowledge design and broken anchor-support proxy
are historical. This repair does not invent a replacement knowledge metric or
claim that the live score implements that earlier 50/50 objective. Reduced-model
scores retain their scope and are not counted as complete-model recurrence.

**Inputs to decisions:** the fixed problem, current candidates and trajectory
measurements, the root's credit history, and the contracted findings of its
children. Simulation findings can motivate a new mathematical investigation;
mathematical findings can motivate a new simulation investigation.

**Child contracts:** before invocation, specify the child's objective, requested
measurements, information needed for the root's next decision, and relevant
existing findings. Keep the parent's credit projection separate from the child's
requested report synthesis.

The parent defines a type schema for every requested report field before the
child starts. Closed records, typed arrays, numeric values and declared string
types carry findings and trends; unrestricted prose slots are prohibited. The
copied/adapted boundary guards and exact examples are in COMMUNICATION.md.
The child planner receives its inherited root task context and exact parent
report contract along with its local objective and assignment.

## Branch: mathematical_exploration

**Goal:** develop useful mathematical guidance that improves trajectory search
and understanding of the fixed dynamics.

**Repeated unit:** develop or revise an approximation, prediction, or candidate
selection argument and perform a concrete symbolic, numerical, or formal
operation, or commission a simparts investigation of a focused computational
question. Measure the contribution and record findings for the next iteration.

**Initial tool capabilities:**

- Scalar arithmetic through `math.arithmetic`: calculate differences, ratios,
  convergence orders and extrapolations from supplied measurements. This bounded
  operation is also available to simulation and simparts Episodes. When existing
  measurements suffice, calculate locally rather than delegating the identical
  arithmetic question to another child.
- Symbolic calculation through SymPy: derive the explicit central conic
  relationships supplied by `central_conic`, with their unit-mass assumptions.
- Numerical calculation through NumPy/SciPy: central circular/conic reference
  calculations and local affine fits to supplied measured velocity/score points.
  These can guide candidate velocities. `binary_reference` supplies source states and
  period, individual gravitational vectors, and explicitly approximate velocity
  references; these are guidance, not stable-orbit predictions.
- Optional formal reasoning through Lean: formulate precise statements with
  explicit assumptions, attempt proofs, and use proof states and diagnostics to
  guide further work. Lean is an additional operation, not a prerequisite for
  other mathematical work or simulation.
- Commission simparts through the parent-owned child invocation boundary when
  a mathematical investigation needs reduced-model or scoped simulation evidence.

**Local credit:** the explicit score assignment can use machine-scored observations
of its assigned problem, including observations returned by simparts. Credit tracks
the best assigned score and its improvement. Mathematical prose, reference
calculations and theorem counts have no automatic credit. Useful mathematical
information still returns through typed reports; the repair does not pretend
to have supplied a new quantitative measure of understanding.

**Report to root:** return the requested velocity suggestions, quantitative
predictions, mathematical relationships, assumptions, applicability to the full
simulation, uncertainty, and limitations. The invoking root selects the exact
information fields through its reporting contract.

A formal proof concerns its stated mathematical model and assumptions. A proof
about a simplified model does not automatically describe the full randomly forced
simulation. An unsuccessful proof attempt supplies feedback; it does not reject
a trajectory or prohibit its investigation.

## Branch: simulation_investigation

**Goal:** reveal and characterize the quasi-stable behavior of a selected
spaceship configuration in the fixed environment.

**Repeated unit:** perform another specified integration observation, such as
advancing the observed trajectory within the physical horizon or refining the
numerical resolution of an existing observation, or commission a simparts child
to investigate a particular feature, disruption, or sensitivity. Compute the
measurements or project the child's contribution into the local credit scheme.

**Tool capabilities:** execute the fixed simulator, evaluate the agreed
persistence measurement, calculate numerical differences and uncertainty, and
retain or restore trajectory state and stored forcing. Numerical refinement uses
the identical forcing realization and spaceship initial conditions.
`math.arithmetic` provides direct scalar calculations over existing measurements;
it performs no new integration and supplies no automatic score credit.
Reduced-model and scoped comparative investigations are commissioned through the
explicit simparts Episode described below.

**Local credit:** retain the best measured S assigned to this investigation and
each turn's actual improvement. Numerical refinement can change the measured
score; integration duration and nominal resolution receive no separate controller
bonus. Discrepancies remain observations without a scientific pass/fail threshold.

**Report to root:** return the requested persistence findings, cycle behavior,
numerical uncertainty, sensitivity observations, and limitations. The invoking
root selects the exact information fields through its reporting contract.

## Parts Episode: simparts

**Goal:** investigate a smaller simulation question assigned by its parent and
return findings that help the parent improve its search or understanding.

Possible assignments include the effect of one force term, the interaction of
two terms, a segment where cycle similarity deteriorates, or sensitivity to
initial velocity near a promising trajectory. The parent supplies the question
and relevant existing findings, rather than merely requesting a collection of
tool calls.

Every commissioned child owns an iterative sub-investigation. The parent assigns
its scientific question; the child chooses successive observations, comparisons,
refinements and subdivisions within that investigation. A single prescribed
experiment or calculation belongs in a declared local tool call when that
capability is available. When reduced work requires simparts, commission an
iterative reduced-model investigation rather than a one-run child task.
Full-model velocity search belongs in a child only when its assigned
investigation includes that question.

**Repeated unit:** select and execute a specified reduced or scoped simulation
observation or matched comparison, or commission a more focused simparts child.
Interpret the contribution to the assigned question and advance this Episode's
own numerical controller. Subsequent observations, comparisons, refinements, and
subdivision remain Episode decisions.

**Simulator tool calls:**

| Proposed call | Explicit request | Returned observations |
| --- | --- | --- |
| `sim.run` | Spaceship initial state or saved continuation state; environment case; stored forcing reference; model variant; observation scope; numerical settings. | One integration's motion, recurrence score S, termination information and numerical diagnostics. |
| `sim.compare` | References to already-saved observations and their comparison scope. | Quantitative differences in saved motion, recurrence and numerical behavior; no new integrations. |

A tool call executes the requested numerical operation. It does not choose a
sequence of additional investigations, run an adaptive scientific search, or
decide Episode continuation. Obtain each comparison case through a separate
scored `sim.run` turn, then compare those saved observations. A compare call must
not hide multiple integrations from the Episode's per-turn yield history.

**Model variants:** the simulator exposes explicit switches for central
attraction, its periodic modulation, the rotating noncentral term, and random
forcing. Disabling modulation leaves the constant central attraction when that
term is enabled. This supports central-only motion, deterministic combinations,
matched runs with and without a term, and investigations of interacting terms.
These are declared approximations to the same problem; the original full-model
definition remains the reference. Retain the exact enabled terms for every run.
For the binary, `active_bodies` can isolate one source's force, and `gravity_mode`
can use a barycentric monopole approximation. Both retain the original physical
body motion and collision surfaces. Record these as scoped force reductions.

**Observation scopes:** tool requests can select a time interval, a portion of a
stored trajectory, a neighborhood of initial velocities, or a spatial region.
This workflow fixes the physical observation domain to `[0, study.horizon]`,
including reduced models. Publish that exact interval in the tool context;
continuations and shorter observations remain within it. This makes the original
finite experiment explicit at the tool boundary; generic method_loop does not
choose simulation domains. A public outside-window request returns typed
`action_failure` feedback before integration, with no acquired unit, simulation
score, completed-run index or estimator observation. The responsible Episode
chooses its next ordinary action at the same controller state. The private
complete-engine interface retains `sim.request_diagnostic` for explicit diagnostic
fixtures; when actually returned, that diagnostic is an acquired, unscored
observation with zero marginal credit. The numerical controller still owns
continuation with no turn cap.
Comparisons over a velocity neighborhood name the configurations to evaluate;
simparts chooses further configurations in subsequent iterations. Continuing a
trajectory preserves its absolute simulation time, position, velocity, and forcing
alignment. Restricting an observation to a spatial region does not silently remove
external field contributions or alter the dynamics. Record any region boundary
and the requested stop/observation behavior explicitly. A locally approximated
field is a declared model variant with its reference state and assumptions.

For matched comparisons, reuse the spaceship configuration and stored forcing
where relevant, and record which model terms, inputs, or numerical settings were
changed. Numerical refinement of one model is distinguishable from changing that
model. Short observations, spatial scopes, and simplified dynamics are tools for
learning rather than substitutes for the parent Episode's continuation rule.

**Local credit:** apply the explicit score assignment to observations of the
assigned subproblem, retaining the best measured S and marginal improvements.
The parent independently assigns credit from projected scored observations on
its own target; it does not import the child's total. Longer recurrence in an
easier model is not automatically recurrence in the complete problem. Reduced
findings contribute typed scientific information immediately, with scope and
uncertainty retained; no subsequent full simulation must approve their report.
This repair supplies no separate numerical knowledge bonus for those findings.

**Parent request and report:** before invocation, the parent declares the smaller
question, requested measurements, and information needed for its next decision.
The report synthesizes those findings, including the model/scope assumptions,
measured differences, uncertainty, limitations, and implications for the parent's
work as requested. Keep credit projection and report synthesis separate. A
simparts child receives the same kind of contract from its immediate parent.

**Evidence:** retain tool requests and outputs, enabled force terms, observation
scopes, initial/continuation states, forcing identity, numerical settings, and
comparison relationships for replay and audit. The parent receives its contracted
findings through the normal method_loop boundary. No reduced-model investigation
or child report creates a scientific acceptance gate.

## Method ownership, continuation, and evidence

Episodes exist to improve total credit. Each iteration pursues a marginal increase.
Zero-yield attempts remain observable and inform predicted further yield; do not
manufacture positive credit to make every attempt look productive.

Use method_loop for acquisition, controller advancement, recording, child
invocation, and report delivery. Each Episode's selected numerical controller owns
its continuation decision based on predicted further credit.

Score assignment, yield estimation and continuation are independent numerical
functions. A turn is one acquired unit in the current Episode: a local tool,
including math or saved-observation comparison, or one completed child
investigation. A child's internal turns belong to that child's history; its
completion advances the parent only once. Planning and report-synthesis model
calls are not additional acquired units. Pass one actual real-valued marginal
credit per local acquired unit, including legitimate zeros for non-improving
math/compare work, to the template-derived estimator. Its `window_size` and
`subsample_size` control its minimum-information behavior; the template cold-fits the complete
credit history rather than applying a rolling average. Fitting stays inside it.
Record the current estimate, unavailable state and approximate model-dependent
bands as returned. The controller adds no memory, EWMA or artificial prediction
decay. See [CREDIT.md](CREDIT.md) for the current score and estimation boundaries.

Repeated mathematical search must remain exposed as Episode units. Do not hide
an entire optimizer search in one tool call and show only its final answer to the
controller. Tool-level arithmetic and bounded numerical operations implement an
acquisition; choosing further scientific search belongs to the Episode loop.
Likewise, do not conceal a refine-until-qualified investigation inside a single
simulation acquisition. simparts is itself an Episode with this same obligation;
it is not a wrapper that hides a complete adaptive subproblem inside a tool call.

There are no scientific acceptance gates, hidden rejection thresholds, or proof
requirements before findings can contribute. Numerical discrepancies, uncertainty,
formal-tool feedback, and independent calculations are observations used to
improve credit and guide subsequent work. The original experiment's pass/fail
qualification and gate-closure credit rules are superseded.

Physical simulation horizons and terminal events describe observations in the
problem. They do not replace Episode continuation. Completing an experiment,
characterizing a question or filling the parent's report form does not end a
scientific Episode. Further useful uncertainty or refinement stays within its
assigned investigation, and its numerical controller's yield estimate alone
governs continuation. Execution failures remain execution failures. Finite
diagnostic probes may exhaust their sources; that behavior supplies no
completion or scope-exhaustion stopping rule for scientific Episodes.

Retain each unit's action, measurements, local marginal credit, parent contribution,
controller calculation, and configuration. Keep full tool outputs, proof attempts,
forcing arrays, numerical settings, and execution provenance available for replay
and audit. Deliver findings upward through the parent's reporting contract rather
than automatically copying the full child history into its input.

## Tool references

- SymPy equation solving: https://docs.sympy.org/latest/guides/solving/index.html
- SciPy numerical optimization: https://docs.scipy.org/doc/scipy/reference/optimize.html
- Lean language reference: https://lean-lang.org/doc/reference/latest/Introduction/

## Model connection and roles

Use the current authenticated Codex connection through a project-owned app-server
transport. Store no credentials in the project and apply settings per conversation.

| Role | Model | Reasoning effort |
| --- | --- | --- |
| FAST | gpt-6-luna | none |
| REASONING | gpt-6-sol | medium |

Both roles and task routing are editable in study.toml. Episode action selection
and its own final interpretation form use REASONING in the same conversation.
Recorded factual form fields are projected from actual saved observations;
FAST is reserved for the separate human report. These are model roles,
not additional Episodes. Separate conversations retain each Episode/role's history
and fixed instructions. The numerical credit and continuation calculations remain
explicit program functions. Models propose structured data; the workflow executes
its declared actions. A model-call failure is an execution diagnostic and does not
stand in for a physical simulation observation.

The project-local model adapter, live role probe, adaptive Episode decision policy,
and contracted scientific report synthesis are implemented. Both requested models
and efforts were confirmed by the server. Numerical credit and continuation remain
outside the model, with explicit formulas and initial limitations in CREDIT.md.

The runnable workflow is described in [README.md](README.md). The declared tree,
real simulation and mathematical tools, recursive simparts boundary, continuous
persistence measurement, scientific credit/continuation, adaptive policies, report
synthesis, and whole-run cached interruption recovery are implemented. Closed-child
reopening is the unresolved lifecycle gap described above. Fresh end-to-end
verification of the repaired score/yield binding is separate from historical runs.
Lean remains optional
and reports availability/diagnostics. The separate finite diagnostic workload does
not claim to execute the scientific search or its credit scheme.
