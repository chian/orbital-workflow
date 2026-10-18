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

Each Episode type is a repeated acquisition loop with its own goal, units, credit
scheme, and numerical continuation calculation. Both scientific branches can
perform their own tool operations and commission an explicit simparts child for
a smaller simulation investigation. These are declared parent/child edges. The
simparts-to-simparts edge is explicitly declared as self-nesting in EpisodeTree;
it is not an implicit tool recursion or an undeclared execution path. Each child
invocation has its own controller, linked goal, and parent reporting contract.

The root may use either branch according to the predicted opportunity to improve
its credit. It can obtain mathematical guidance, investigate a candidate directly,
or continue a previous investigation. Mathematical guidance and formal proof are
never prerequisites for simulation. These branches are not a compulsory sequence.

## Root: spaceship_trajectory_search

**Goal:** discover and characterize quasi-stable spaceship trajectories in the
specified environment.

**Repeated unit:** commission a mathematical exploration or simulation
investigation, then measure that child's contribution using the root's scheme.
When continuing an investigation, preserve its prior scientific evidence and
controller history rather than restarting its accounting.

**Credit:** initially weight orbital persistence and knowledge gained equally,
using the adjustable root weights in study.toml. Retain the separate component
measurements, their normalization, and their weighted contributions. Evaluate a
child's contribution on this root scale; do not add the child's scalar credit.

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

## Branch: mathematical_exploration

**Goal:** develop useful mathematical guidance that improves trajectory search
and understanding of the fixed dynamics.

**Repeated unit:** develop or revise an approximation, prediction, or candidate
selection argument and perform a concrete symbolic, numerical, or formal
operation, or commission a simparts investigation of a focused computational
question. Measure the contribution and record findings for the next iteration.

**Initial tool capabilities:**

- Symbolic calculation through SymPy: manipulate expressions, derive simplified
  relationships, and solve tractable equations or approximations.
- Numerical calculation through Python, NumPy, and SciPy: calculate sensitivities,
  fit approximations to observed trajectories, explore prediction errors, and
  propose initial velocities. `binary_reference` supplies exact source states and
  period, individual gravitational vectors, and explicitly approximate velocity
  references; these are guidance, not stable-orbit predictions.
- Optional formal reasoning through Lean: formulate precise statements with
  explicit assumptions, attempt proofs, and use proof states and diagnostics to
  guide further work. Lean is an additional operation, not a prerequisite for
  other mathematical work or simulation.
- Commission simparts through the parent-owned child invocation boundary when
  a mathematical investigation needs reduced-model or scoped simulation evidence.

**Local credit:** measure improvements in the guidance and understanding produced
by the investigation, such as improved quantitative predictions, better-supported
relationships, or useful resolution of uncertainty. Express these through an
explicit local credit function. Suggestion counts, prose volume, tool-call counts,
and theorem counts do not automatically constitute scientific improvement.

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
Reduced-model and scoped comparative investigations are commissioned through the
explicit simparts Episode described below.

**Local credit:** measure useful increases in the characterization, including
additional quasi-stable duration revealed, improved cycle measurements, and
reduced numerical uncertainty. The local scheme remains distinct from the root's
equally weighted scheme. Discrepancies guide further investigation without a
pass/fail threshold for contributing scientific information.

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

**Repeated unit:** select and execute a specified reduced or scoped simulation
observation or matched comparison, or commission a more focused simparts child.
Interpret the contribution to the assigned question and advance this Episode's
own numerical controller. Subsequent observations, comparisons, refinements, and
subdivision remain Episode decisions.

**Simulator tool calls:**

| Proposed call | Explicit request | Returned observations |
| --- | --- | --- |
| `sim.run` | Spaceship initial state or saved continuation state; environment case; stored forcing reference; model variant; observation scope; numerical settings. | Motion, cycle/persistence measurements, termination information, and numerical diagnostics. |
| `sim.compare` | Explicit runs to compare or explicit matched requests; quantities and comparison scope. | Quantitative differences in motion, persistence, sensitivity, and numerical behavior. |

A tool call executes the requested numerical operation. It does not choose a
sequence of additional investigations, run an adaptive scientific search, or
decide Episode continuation. A matched comparison can execute its explicitly
specified cases without hiding an open-ended sweep inside one acquisition.

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

**Local credit:** measure improvements in resolving the assigned question, such
as better characterization of a term's effect, an interaction, a local sensitivity,
or uncertainty about a disruption. The local credit scheme belongs to simparts;
the invoking parent independently measures the contribution on its own scale.
More runs, smaller subproblems, removed terms, and longer persistence in an easier
model do not automatically constitute improvement in the original environment.
An insight from a reduced model can contribute knowledge immediately, with its
scope and uncertainty retained; there is no requirement that a subsequent full
simulation first approve it.

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
problem. They do not replace Episode continuation. Source exhaustion, execution
failure, and yield stopping remain distinguishable in the record.

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

Both roles and task routing are editable in study.toml. Initially, Episode action
selection uses REASONING and report synthesis uses FAST. These are model roles,
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
synthesis, and cached-history resumption are implemented. Lean remains optional
and reports availability/diagnostics. The separate finite diagnostic workload does
not claim to execute the scientific search or its credit scheme.
