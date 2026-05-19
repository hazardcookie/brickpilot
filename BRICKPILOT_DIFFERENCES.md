# How Brickpilot Differs From openpilot and sunnypilot

Brickpilot is a private research and test fork for a 2022 Hyundai Tucson PHEV.
It inherits major pieces from openpilot and sunnypilot, but its own changes are
intentionally narrow: learn the PHEV-specific vehicle behavior, log the right
signals, and make bounded control changes that produce useful test data.

This is not a public-support statement. It is a working project note for keeping
the fork's purpose clear as Brickpilot moves toward 0.4.x and 0.5.x.

## Project Position

openpilot is the upstream driver-assistance stack and safety foundation. It is
the broad baseline for process architecture, car interfaces, safety models,
messaging, controls, logging, and official release discipline.

sunnypilot is the community fork Brickpilot currently builds on. It adds the
user-facing and driving features Brickpilot relies on, including MADS, richer
model/profile selection, sunnypilot longitudinal features, UI panels, and the
Hyundai community support context.

Brickpilot is the Tucson PHEV research fork. It is not trying to become a broad
car-support fork right now. It specializes the inherited stack for one vehicle
and uses route labels, voice bookmarks, PHEV CAN candidates, and replay/ML
analysis to decide what to change next.

## Vehicle Scope

Brickpilot's live custom behavior is scoped to:

- Hyundai Tucson 4th gen platform.
- Hyundai CAN-FD.
- openpilot longitudinal control enabled.
- The project owner's 2022 Tucson PHEV testing context.

The 2022 Tucson PHEV mostly works through the generic Tucson/Tucson Hybrid
platform path, but it has PHEV-specific mass, firmware, HV battery, inverter,
regen, engine-transition, and energy-flow behavior that generic Tucson support
does not fully model.

## Core Brickpilot Differences

### Tucson PHEV Vehicle Model

Brickpilot overrides the Tucson 4th-gen vehicle specs to match the tested PHEV
more closely:

- `mass=1960`
- `wheelbase=2.756`
- `steerRatio=13.7`
- `tireStiffnessFactor=0.385`

The mass correction is one of the most grounded Brickpilot changes: it follows
physical vehicle evidence and has correlated with better lateral metrics in the
local route analysis.

### PHEV CAN Candidate Logging

Brickpilot logs PHEV-specific candidate frames that are not yet public decoded
DBC truth. The current high-value set includes:

- `0x0FA` for PHEV/hybrid runtime and regen/charge candidates.
- `0x0E0` for likely quantitative motor/HV/regen companion signals.
- `0x0BA` for brake-blend, regen, or auto-hold companion state.
- `0x065` for extra brake-domain fields beyond the common decoded signals.
- `0x10A` and `0x120` for engine/HCU state candidates.
- `0x1C5` for PHEV mode or energy-flow candidates.
- `0x310` for ADAS/lateral/longitudinal gating candidates.
- `0x1A5` and `0x06F` as additional state candidates worth tracking.

These fields are logged into `carStateSP` and `brickpilotShadow` so external
DriveDB/ML tooling can compare them against voice-bookmark labels and route
events. They are candidates, not final decoded semantics.

### Brickpilot Longitudinal Assist

Brickpilot adds a Tucson-scoped longitudinal assist layer before LongControl.
It is designed to address lazy acceleration and catch-up behavior while staying
inside the normal actuator and safety path.

The assist only acts in clean cruise catch-up contexts. It refuses to add energy
when there is a lead vehicle, driver override, stop/creep context, FCW or model
brake risk, radar/model mismatch, high lateral demand, DEC/SCC turn behavior,
PHEV regen/brake activity, or stationary/auto-hold state.

In 0.4.1, Brickpilot promoted one data-backed change: a large clean speed
deficit can raise a weak planner acceleration request to a bounded
`0.42 m/s^2` floor.

In 0.4.2, Brickpilot made that experiment more visible on road: the clean
catch-up threshold is lower, the live floor is `0.56 m/s^2`, the bounded assist
delta is larger, and the short hold lasts longer. The intent is to collect
clearer data on whether the Tucson PHEV needs more energy in straight cruise
catch-up sections, not to bypass any inherited control or safety layer.

In 0.4.3, Brickpilot separates two cases that looked similar to the labeler:
accidental low-speed highway set-speed gaps and real interstate-ramp catch-up.
Set-speed-only demand is capped below 32 mph, while clean no-lead merge-speed
catch-up above 35 mph can use a stronger bounded assist delta. The intent is to
test the specific entry-ramp problem without making local-road cruise-speed
mistakes look like a valid acceleration request.

In 0.4.4, Brickpilot promotes the offline sweep result instead of making another
tiny manual tweak. Clean no-lead cruise catch-up is wider and stronger, and
ExperimentalMode/e2e can now receive a bounded high-speed catch-up bridge above
32 mph when speed deficit is large and the same hard vetoes are clear. This is
meant to create materially different data on entry ramps and exp-mode catch-up
without adding energy into stop, lead, braking, regen, or auto-hold contexts.

In 0.4.5, Brickpilot keeps the 0.4.4 longitudinal behavior and changes steering
texture based on the 2M VM replay sweep winner `road100k_1292674`. The promoted
candidate is causal and road-budgeted: two-stage output smoothing, mild torque
scale-down, weak zero-cross/reversal hold, and no Hyundai safety/rate-limit
changes. The intent is to make the steering feel clearly different so the next
test drive can compare blocky wheel texture against 0.4.4 directly.

In 0.4.6, Brickpilot uses the newest 0.4.x road data instead of only retuning the
previous build. A fresh 35-segment VM replay corpus and 2M road-budget sweep
promote `road046s406_0886848`; the live steering path also adds explicit
center-return unwind smoothing because the latest road feedback narrowed the
remaining blocky feel to curve exit and wheel return-to-center. For a separate
felt change, the Tucson CAN-FD steering command uses a scoped `Damping_Gain` of
`140` on this platform only. Longitudinal catch-up is also easier to exercise:
set-speed deficit uncaps above 30 mph, the ramp deficit threshold and
ExperimentalMode/e2e bridge thresholds are lower, while the same lead, stop,
brake, regen, auto-hold, and override vetoes remain hard.

In 0.4.7, Brickpilot keeps the 0.4.6 longitudinal and damping behavior and
changes only the Tucson CAN-FD steering unwind texture. The post-0.4.6 labels
showed the remaining blocky steering was concentrated when the wheel was coming
back toward center, not entering curves. A targeted return-phase sweep ranked
the natural two-stage glide above the 0.4.6 fast-unwind alpha, so 0.4.7 removes
that extra center-return acceleration while keeping the same 2M road-budget
filter, zero-cross hold, driver bypasses, and stock Hyundai safety/rate limits.

In 0.4.8, Brickpilot changes direction from final-output-only steering texture
to a root-cause steering experiment. Tucson CAN-FD torque control now softens
jerk-driven friction sign flips near center return before the torque friction
feedforward is applied, then uses a faster causal two-stage output texture with
smaller zero-cross holds and no extra pre-safety rate clamp. The scoped Tucson
CAN-FD steering `Damping_Gain` moves from `140` to `170`. Longitudinally, 0.4.8
adds a high-deficit ramp/merge branch that requires both set-speed demand and
planner trajectory confirmation, and the ExperimentalMode/e2e bridge starts at
27 mph with the same trajectory confirmation and hard vetoes.

### Low-Speed Steering Texture Smoothing

Brickpilot adds Tucson CAN-FD low-speed output-torque smoothing in the
sunnypilot torque extension path:

- Full smoothing below 34 mph in 0.4.4, widened from 26 mph.
- Fade-out to no smoothing by 62 mph in 0.4.4, widened from 50 mph.
- Extra damping on fast torque reversals, stronger in 0.4.4.
- Brief center hold on weak low-speed torque zero-crossings in 0.4.3, extended
  in 0.4.4.
- 0.4.5 replaces the 0.4.4 shape with the 2M sweep winner: stronger causal
  two-stage smoothing below the existing 62 mph cutoff, mild output scale-down,
  and a short reversal hold after weak zero-crossings.
- 0.4.6 promotes the next 2M sweep winner, adds center-return unwind smoothing,
  adds the candidate's bounded pre-safety torque rate limiter, and lengthens the
  weak zero-cross hold for low-amplitude reversals.
- 0.4.7 keeps the 0.4.6 winner but removes the fast center-return alpha, letting
  the same two-stage smoother unwind naturally after a curve.
- 0.4.8 adds Tucson-only friction/jerk shaping before output torque is
  calculated, then switches the final texture to a faster causal two-stage
  filter with a smaller zero-cross hold, speed fade-out by 70 mph, and no extra
  pre-safety torque rate clamp.
- Reset on driver steering override.
- Applied before stock CAN-FD safety and rate limits.

The goal is tactile steering texture, not stronger steering. It is judged by
route labels and metrics around low-speed jerk, torque-rate, lateral error, and
driver steering corrections.

### Steering Guard Policy

Brickpilot experimented with an extra Tucson CAN-FD MADS steering guard, then
removed it before 0.4.0-beta because it was too aggressive for testing. Current
0.4.x behavior leaves high-angle steering request suppression to upstream
Hyundai `common_fault_avoidance`.

Brickpilot still logs steering-guard shadow fields so later route review can
tell whether high-angle conditions were relevant without adding a separate live
guard.

### Labels and Research Telemetry

Brickpilot includes on-device bookmark tagging for drive, PHEV, and good-event
labels. The core repo writes lightweight tag records; external sibling repos
handle ingest, label normalization, manual review, ML analysis, and dashboards.

The important repo boundary is deliberate:

- `brickpilot`: on-device driving code and deployable runtime support.
- `brickpilot-tools`: ingest, DriveDB, replay, labeler, and ML utilities.
- `brickpilot-web-ui`: local operations UI and API.
- `/Users/brick/BrickpilotDriveDB`: logs, videos, labels, reports, databases,
  and generated analysis artifacts.

## What Brickpilot Does Not Change

Brickpilot does not bypass panda safety, Hyundai CAN-FD rate limits, or the
normal carcontroller actuator path.

Brickpilot does not claim public support for every Tucson, Tucson Hybrid, or
Tucson PHEV variant.

Brickpilot does not treat the current PHEV CAN candidates as final decoded DBC
signals. They are logged and used carefully until route evidence is strong
enough to promote a semantic interpretation.

Brickpilot does not put raw drive data, generated reports, model artifacts,
videos, audio, or DriveDB state in this repo.

## Release Documentation Habit

For every Brickpilot version bump:

- Update `CHANGELOG.md` with the user-facing behavior, telemetry, tests, and
  release intent.
- Update this file when Brickpilot's relationship to openpilot or sunnypilot
  materially changes.
- Keep generated data and private analysis artifacts outside the driving repo.
