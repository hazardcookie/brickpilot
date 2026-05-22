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

In 0.4.9, Brickpilot keeps the 0.4.8 steering and longitudinal candidates but
adds a live MADS/manual-steering isolation path for the hard-turn symptom found
after the 0.4.8 drive. On Tucson CAN-FD, when MADS is available, lateral is
active, the driver is pressing the wheel, speed is below 30 mph, and steering
angle is at least 35 deg, Brickpilot cuts the CAN-FD steering request and zeros
the torque-extension output. After release, torque returns through a short
30-frame ramp. Existing shadow steering-guard fields now mark that isolation so
future routes can score manual high-angle turns without adding a new telemetry
schema.

In 0.5.0, Brickpilot freezes the 0.4.9 steering baseline and shifts the live
experiment toward braking attribution and lead-follow stop confidence. It
adds a Tucson PHEV stop-debt path that compares required lead/model/stop decel,
planner target decel, and measured vehicle decel, then can make a bounded
negative `aTarget` adjustment only when openpilot already has a lead, model, or
should-stop context. This is not a no-lead traffic-light or stop-sign feature.
PHEV regen/brake CAN activity may still block positive catch-up assist, but it
must not block required deceleration. `0x0BA.b14` is no longer treated as
stationary/auto-hold unless vehicle speed is near zero, and the logged brake
state now separates light coast regen, regen/brake blend, friction-brake
candidate, and stationary hold.

In 0.5.1, Brickpilot keeps the 0.5.0 steering baseline and makes the stop stack
more attribution-safe before moving toward 0.6.0. Invalid lead geometry, such as
far or non-closing lead contexts with huge TTC, no longer creates brake debt or
live stop assist. Stop debug logs now include source validity, required-decel
validity, TTC validity, debt bucket, invalid-geometry reason, and stop-profile
id. When the stop source is valid, Brickpilot uses a slightly larger low-speed
Tucson PHEV stopped-distance buffer and a stronger bounded negative `aTarget`
adjustment through the normal LongControl path.

In 0.5.2, Brickpilot keeps steering and broad catch-up frozen and promotes the
next stop-stack step. Valid controller-underbrake cases now get a stronger
bounded recovery target, crawl/final-stop lead `shouldStop` contexts commit to a
firmer decel target below 5 mph, and mild high-TTC lead contexts use a less
blunt stopped-distance buffer to reduce unnatural early stops. This remains a
lead/model/shouldStop braking assist only; it is not a no-lead stop-sign or
traffic-light feature.

In 0.5.3, Brickpilot keeps the same steering and general catch-up behavior while
making stop-stack attribution first-class. Active stop assist now logs a reason
code and stop-source persistence, and the firmer below-5-mph final-stop target
requires a persistent valid source, planner decel, and plausible close/closing
context before it can fire. The build also logs `0x065.b11` and `0x065.b12` as
read-only CAN candidates for stop-creep/hold event-card analysis.

In 0.5.3.1, Brickpilot's installed driving behavior remains unchanged from
0.5.3. The version marks the first voice-label telemetry calibration workflow:
explicit manual/driver brake and gas narration can be snapped to logged
telemetry edges in the tools pipeline, and enough high-confidence anchors can
produce a route-level voice timing offset for subjective labels.

In 0.5.4, Brickpilot uses the calibrated 0.5.3.1 stop-stack labels to target
final-stop behavior without changing steering or broad catch-up tuning.
Persistent valid stop context can now carry through lead/model/shouldStop/creep
source churn, and the bounded final-stop commit branch may begin below 6 mph so
the last few mph of lead/model stops get firmer commitment before weak PHEV
coast/creep behavior takes over. Generic braking authority is unchanged.

In 0.5.5, Brickpilot uses the accidental Alpha Long OFF/native longitudinal
routes as a reference for lead-stop finishing. The live stop branch now prefers
lead and creep/final-hold sources, lets lead-backed final-stop commitment begin
below 8 mph, and demotes broad model-only or generic `shouldStop` planner-debt
braking to shadow/diagnostic unless it inherits a valid lead/final-stop context.
This is meant to make Alpha Long ON behave more like the native SCC stops that
felt good, without adding no-lead stop-sign/traffic-light heroics.

In 0.5.6, Brickpilot keeps the 0.5.5 stop authority cap but adds rolling-traffic
arbitration. Low-speed lead traffic is split into rolling-follow,
final-stop-commit, urgent-recovery, and creep-hold modes. A lead that is still
rolling slowly blocks final-stop commit unless TTC, gap, or closing speed makes
the situation genuinely urgent; the rolling-follow branch uses a smaller
extra-decel cap and a relaxed rolling buffer. This targets the 0.5.5 stress
route failure mode where Alpha Long ON could overcommit to a full stop while
traffic was only creeping.

In 0.5.7, Brickpilot uses the 0.5.6 Alpha Long ON/OFF comparison routes to
target pacing instead of stronger braking. The Alpha Long OFF/native reference
felt much better at aggressive follow distance, while Alpha Long ON still felt
too far and bursty in rolling traffic. Brickpilot keeps the 0.5.6 final-stop
authority and adds a small signed radar-lead pacing branch: far rolling leads
can receive a bounded positive `aTarget` nudge, close or mildly closing leads
can receive a bounded negative nudge, and urgent stop/final-stop behavior still
wins. The new `brickpilotShadow` fields `leadPacingMode`,
`leadPacingTargetGap`, `leadPacingGapError`, `leadPacingVRel`,
`leadPacingAssistDelta`, and `leadPacingJerkLimited` make this behavior
auditable in the research UI and event-card reports.

In 0.5.8, Brickpilot keeps steering and stop authority frozen, then turns the
0.5.7 pacing classifier into a live native-style micro-pacing policy. The new
policy only runs for valid rolling radar leads, uses a speed-shaped target gap
and deadband, tapers out at higher speed, and applies very small signed
post-planner deltas through the normal LongControl path: up to `+0.10 m/s^2`
for smooth catch-up and `-0.16 m/s^2` for rolling/coast-down correction. Stop
priority, driver override, high lateral demand, clear `0x065` brake-blend
context, urgent TTC, and stationary/Auto Hold contexts block live pacing. Raw
high unsigned `0x0FA.b4` is no longer treated as brake magnitude; `0x0FA.b4/b7`
remain energy/regen context only. Additional telemetry records raw/live/rate
limited deltas, gate masks, block reasons, mode age, lead absolute speed, TTC,
regen/brake contexts, and whether the pacing delta actually reached `aTarget`.

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
- 0.4.9 leaves the 0.4.8 texture intact for normal assisted steering, but zeros
  and then ramps torque back during low-speed high-angle manual steering in
  MADS so the driver can own hard turns without controller torque texture.
- Reset on driver steering override.
- Applied before stock CAN-FD safety and rate limits.

The goal is tactile steering texture, not stronger steering. It is judged by
route labels and metrics around low-speed jerk, torque-rate, lateral error, and
driver steering corrections.

### Steering Guard Policy

Brickpilot experimented with an extra Tucson CAN-FD MADS steering guard, then
removed it before 0.4.0-beta because it was too aggressive for testing. Current
0.4.x behavior leaves high-angle steering request suppression to upstream
Hyundai `common_fault_avoidance` unless the driver is manually steering a
low-speed high-angle turn in MADS.

Brickpilot still logs steering-guard shadow fields so later route review can
tell whether high-angle conditions were relevant without adding a separate live
guard. In 0.4.9 those same fields also identify MADS manual-steering isolation.

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
