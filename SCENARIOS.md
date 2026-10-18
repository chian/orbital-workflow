# Saved orbital scenarios

Each scenario has an independent `scenarios/<id>/study.toml`. Every adaptive run
copies those settings into its own directory, writes `scenario.json`, and saves
its execution identity, source snapshot, typed Episode reports, observations and
numerical files. Changing a scenario starts a new run; it does not rewrite earlier
inputs or results.

| Scenario | Gravitational problem | Source parameters | Observation domain |
| --- | --- | --- | --- |
| `scenario_01` | Original fixed point mass | G=1, M=1 at (0,0) | 0.5 < barycentric radius < 2 |
| `scenario_02` | Circular binary plus a test spaceship | G=1, masses 0.75 and 0.25, separation 0.8 | radius < 4, with physical surfaces around both bodies |

The ship starts at (1,0) and the search chooses its initial velocity. It has
negligible gravitational influence on the massive sources. Ship mass cancels out
of gravitational acceleration, including in the time-dependent binary field.
This is a planar restricted three-body system with the existing external terms.
It is not a simulation of three comparably massive objects perturbing each other.

The binary primaries follow the exact circular Newtonian two-body solution about
their shared barycenter. Their orbital radii are 0.2 and 0.6; their angular speed
is sqrt((0.75+0.25)/0.8^3). Their positions and velocities are evaluated analytically
at absolute time, including during a continued observation. Source masses and
orbits belong to the fixed problem and cannot be optimized by the ship workflow.

The ship's resolved acceleration is

```text
g(r,t) = -sum_i M_i (r-R_i(t)) / |r-R_i(t)|^3
a_ship = (1 + a*sin(0.7*t))*g(r,t)
       + 0.02*[[cos(0.4*t), sin(0.4*t)], [sin(0.4*t), -cos(0.4*t)]]*r
       + sigma*eta(t)
```

The modulation, extra rotating term and stored random forcing act on the ship.
They do not alter the primaries' exact circular orbit. Original perturbation
settings, forcing generation, root/local weights and EWMA continuation parameters
are retained. The extra rotating term is distinct from the primaries' orbital
motion and from their individual physical spins, which are not modelled.

The binary has collision radii 0.05 and 0.035 about the moving sources. There is
no inner obstacle at the barycenter: it is not a physical body. Horizons, radial
exits, source-surface collisions and scoped region exits are recorded observation
endpoints, without scientific acceptance/rejection decisions.

## Choose, run and view

```bash
.venv/bin/python -m orbital_workflow scenarios
.venv/bin/python -m orbital_workflow run --scenario scenario_01
.venv/bin/python -m orbital_workflow run --scenario scenario_02
.venv/bin/python -m orbital_workflow run --scenario scenario_02 --output .artifacts/scenario_02/my-run
.venv/bin/python -m orbital_workflow visualize .artifacts/scenario_02/run-002 --serve
```

Default output directories are `.artifacts/<scenario>/run-<timestamp>`. Each run
has its own frozen configuration and cache. `resume RUN_DIRECTORY` uses that run's
own configuration. The live viewer's Saved scenario selector returns to the latest
saved run of either scenario. Any older run is also selectable by its directory.
The tour includes every saved acquisition appearance and preserves repeats.
Moving source markers, orbit rings and individual gravity arrows identify the
attractors. Fit paths shows close encounters; Whole region shows the entire domain.

## Explicit tools and smaller investigations

Both simulator tools accept the following declared reductions:

- `active_bodies: ["body_1"]` or `["body_2"]` retains one source's gravitational
  contribution. The other physical source keeps its original motion and collision
  surface. This isolates a force contribution; it does not solve a new binary.
- `gravity_mode: "monopole"` puts the retained total mass at the barycenter for
  the force calculation. Original body motion and physical collision surfaces
  remain declared. This is an approximation, not a full binary observation.
- Existing perturbation switches, absolute-time continuation, spatial scopes and
  numerical refinements remain available. Numerical refinement changes neither
  the source system nor the saved forcing realization.

`math.numeric` additionally supports `binary_reference`: source states, individual
attraction vectors, exact binary period, a kinematic corotation velocity and a
monopole circular-speed reference. These reference velocities are not predictions
of stable full-model trajectories. Central conic relationships describe the unit
monopole reduction, not the resolved binary. Optional Lean remains available.

The parent still chooses whether math or simparts is useful. No visit to a branch
is required, and numerical reference tools receive no new credit bonus.

## Credit and measurement scope

The persistence metric remains inertial, barycentric winding recurrence. It may
miss a planet-relative loop, a non-winding path or other interesting structure.
No novelty or path-complexity reward has been added. A zero recurrence measurement
is retained and is distinct from an unobserved case.

The knowledge-support formula is unchanged. Its declared model family now
separates the binary's monopole approximation, either individual source force,
and both source forces, each with the original eight perturbation combinations.
That gives 32 reference variants for scenario_02, versus 8 in scenario_01. The
variant labels are stored with controller state. Absolute coverage scores therefore
refer to different declared model families across scenarios; root weights remain
0.5 persistence / 0.5 knowledge. A reduced model contributes scoped knowledge
immediately. Only the specified full scenario contributes to its full-model
persistence component. This is target accounting, not result qualification.

## Returning to earlier work

`scenario_01` is also a Git tag preserving the original source revision, including
its original execution binding. Its original completed run remains unchanged at
`.artifacts/adaptive-storage-first/`. `scenarios/scenario_01/archive.json` records
the source revision, run identity and source snapshot. Three original trajectories
reproduced bit for bit with the new single-source simulator. The complete original
run also replayed from its preserved source with no fresh model or tool calls.

The first binary pilot remains at `.artifacts/scenario_02/run-first/`. It used a
0.05 inner observation radius before that boundary was removed. Its source and
frozen input are retained; its complete replay from that snapshot also used no
fresh model or tool calls. It is a valid record of that earlier declared scope.
The revised scenario is `.artifacts/scenario_02/run-002/`.

For source-bound restoration after code changes, execute the saved run from its
source snapshot with the project environment. For example, from the snapshot
working directory:

```bash
# Working directory: .artifacts/scenario_02/run-first/source-snapshot
/home/chia/repos/orbital_workflow/.venv/bin/python -m orbital_workflow \
  --method-loop-source "$PWD" resume /home/chia/repos/orbital_workflow/.artifacts/scenario_02/run-first
```

Snapshots include the real method_loop source used by the run. They preserve its
implementation for reproducibility, rather than introduce a separate loop binding.
Numerical library versions must match the saved execution identity for exact
replay. Configurations, source tags and reference summaries are tracked in Git;
large arrays, provider logs and run snapshots remain local under `.artifacts/`.

## Initial binary results

Both runs used the configured live FAST and REASONING connections and the real
method_loop. Neither had required branch visits, a scientific result threshold,
or a fixed episode count. Their numerical continuation forecasts ended the runs.

| Run | Episodes used | Distinct saved paths | Observed result |
| --- | --- | --- | --- |
| `run-first` | Root, 2 simulation investigations, 1 math exploration, 1 simparts child of math | 6 | Early collisions or exits through the pilot's inner radius; zero accumulated recurrence score |
| `run-002` | Root, 3 simulation investigations | 4 | Three collisions and one outer exit; no useful quasi-stable recurrence found |

The pilot chose `binary_reference` and used its corotation calculation to guide a
simparts probe and numerical refinement. This demonstrates an actual math-to-parts
interaction, but it did not improve recurrence in that observation scope. The
revised run chose direct simulation without math or parts. These two short runs
do not establish that the extra branches improve search efficiency.

The revised run's longest observation was initial velocity (0, 1.63), which exited
at t=6.149440023903001. The highest recurrence score belonged to (0, 1.45): one
complete winding and part of the next, followed by collision with body 1 at
t=3.1621698. Its effective recurrence duration was 1.250956796753967e-207, a tiny
positive number retained exactly rather than rounded to zero. The other three
paths accumulated zero recurrence. Velocities that were not observed remain
unknown. Residence time and recurrence credit are distinct measurements.

The root consumed 3 investigation units and ended with total discovery credit
0.00011186492618047019. This was almost entirely knowledge support; its persistence
component was 8.295664908241555e-211. Its predicted next marginal credit was
0.015013983115772558 against continuation cost 0.02. These are the existing
heuristic credit and continuation calculations, not a success declaration.

Verification includes 36 unit tests, exact original single-source trajectory
regressions, fresh replay of all five unique revised-run tool operations, cached
workflow restoration, and Chromium checks of chronological playback, source
motion, individual gravitational vectors, reductions, scenario switching and
bounded loading. `parts-demo` contains three explicitly scripted finite simparts
observations for software and viewer verification; it is not an adaptive search
and has no scientific credit. Local evidence is under
`.artifacts/scenario_02/verification/`; the revised run's `completion-evidence.json`
and `latest-report.json` identify the detailed records.
