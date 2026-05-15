# Brickpilot Tucson PHEV 0.4.0 Audit and Plan

Date: 2026-05-15

Scope: Brickpilot core, `brickpilot-tools`, `brickpilot-web-ui`, local historical sunnypilot fork state, and local DriveDB analysis reports for Dan's 2022 Hyundai Tucson PHEV.

This report is intentionally about project state and engineering direction. It does not copy raw route data, videos, audio, labels, or model artifacts into the core repo.

## Executive Summary

Brickpilot is no longer just "sunnypilot with tweaks." The current project is a Tucson PHEV-specific driving stack built around three ideas:

1. The 2022 Tucson PHEV is materially different from the generic Tucson/Hybrid assumptions upstream sunnypilot inherited.
2. The early project used weak data and broad labels, so many early "ML" wins were actually proxy sweeps over noisy events, not validated trained models.
3. The newer infrastructure - voice bookmarks, manual labeler, DriveDB, label validation rides, route ingest, and repo separation - exists to fix that data quality problem before 0.4.0.

Driving-wise, the strongest current evidence is:

- The PHEV mass/spec correction was real and should stay. It made the vehicle model closer to the actual car and correlated with substantially better lateral metrics.
- Lateral/steering is in a better place than longitudinal, but low-speed texture and EPS-risk MADS behavior still need watchful telemetry.
- Longitudinal remains the main opportunity: catch-up, stop-and-go launch timing, "too lazy" speed holding, and timely braking/accel transitions.
- PHEV/CAN-specific signals are promising but not proven enough to drive live controls directly. They should be logged, labeled, and used as features after validation.
- The 0.3.25.0 Brickpilot build keeps the 0.3.9.7 live longitudinal behavior conservative and Tucson-scoped, while adding the telemetry/labeling needed to make pre-0.4.0 drives useful.

The next real Brickpilot update before 0.4.0 should not be another tiny live tuning bump. It should use the 0.3.25.0 instrumentation and label-quality update to make the next drive worth more: richer shadow fields, better PHEV label specificity, and a post-drive validation gate. If one live driving change is included after this, it should be small and bounded, while the 0.4.0 dynamic-router candidate runs in shadow first.

## 0.3.25.0 Implementation Status

This pass turns the report's no-drive prep into an installable pre-0.4.0 build.

Implemented:

- Core, tools, web UI, and the tools OpenClaw logdrive plugin are versioned as `0.3.25.0`.
- `brickpilotShadow` now logs longitudinal assist internals: vehicle scope, param/toggle state, active/shadow-candidate state, suppressor bitmask, version code, candidate hash, base/assisted accel target, assist delta, hold state, planner-floor shadow candidate, accel lag, lateral demand, lead closing, plan source, and `allowThrottle`.
- `brickpilotShadow` now logs the Tucson CAN-FD steering guard: Tucson/MADS scope, high-angle latch, temporary-fault cooldown, suppression/torque-zero state, cooldown frames, above-limit frames, current angle, recovery angle, and whether upstream delayed high-angle avoidance would also suppress.
- The duplicate `liveDelay` `SubMaster` entry is removed.
- On-device bookmark tags are schema v2, still written outside `realdata` at the sibling `brickpilot/bookmark_tags.jsonl` path unless explicitly overridden.
- On-device labels now distinguish `drive` and `phev`, add a `good` label, and replace broad generic PHEV tags with specific sublabels: `ev_launch_lag`, `engine_transition`, `hev_transition`, `regen_blend`, `brake_blend`, `stop_creep`, `no_lead_lazy`, `lead_resume_lazy`, `too_eager_surge`, `good_phev_transition`, and `phev_unspecified`.
- `brickpilot-tools` voice bookmark inference, manual labeler dropdowns, review queue dropdowns, and DriveDB ingest now understand the same label vocabulary.
- DriveDB/labeler/voice defaults continue to point under `/Users/brick/BrickpilotDriveDB`, not the repos. Raw logs, audio, videos, DB artifacts, reports, and training outputs remain out of the driving repo.

Intentionally not promoted live in 0.3.25.0:

- The 0.4.0 dynamic-router candidate is not live.
- The Tucson high-angle steering guard behavior is not relaxed yet. This build logs the guard clearly so the next test drive can prove whether it is causing the "gave up on turn" feel before changing steering behavior.

## Repositories and Boundaries

Current split:

- `/Users/brick/comma-dev/brickpilot`: on-device driving software, Tucson PHEV vehicle changes, controls changes, UI bookmark hook, core telemetry, versioning.
- `/Users/brick/comma-dev/brickpilot-tools`: off-device DriveDB tooling, route ingest, replay/analysis, manual labeler support, voice bookmark helper, ML/RL research utilities.
- `/Users/brick/comma-dev/brickpilot-web-ui`: standalone local React/Node UI/API/Telegram bot for voice, labeler, ML, ingest, rides, and ops workflows.
- `/Users/brick/BrickpilotDriveDB`: local data root. This is where route artifacts, reports, labels, voice sessions, DB state, and training artifacts live. It should stay out of the core driving repo.

The split was the right direction. Before the split, the fork was carrying driving code, web UI, labeler code, analysis scripts, generated reports, and local workflow code in one place. That made every driving update harder to reason about and made it too easy to mix private data artifacts with deployable comma code.

## Sunnypilot Comparison

I compared current `brickpilot` against upstream sunnypilot after fetching `upstream` on 2026-05-15.

Primary upstream comparison baseline:

- `upstream/staging`: `fbfdac781d`
- `upstream/master`: `c51ffe3808`, tagged `staging/2026.001.000/2026.05.14-4501`

There is no useful merge base between current Brickpilot `staging` and upstream because the current repo was imported as a source snapshot and then cleaned, not maintained as a normal fork history. So the comparison here is tree-based.

Against `upstream/staging`, the important Brickpilot-specific behavior/plumbing delta is concentrated in these files:

- `opendbc_repo/opendbc/car/hyundai/values.py`
- `opendbc_repo/opendbc/car/hyundai/carcontroller.py`
- `opendbc_repo/opendbc/car/hyundai/tests/test_tucson_mads_gating.py`
- `opendbc_repo/opendbc/sunnypilot/car/hyundai/longitudinal/config.py`
- `opendbc_repo/opendbc/sunnypilot/car/hyundai/tests/test_tuning_controller.py`
- `selfdrive/controls/controlsd.py`
- `selfdrive/controls/lib/brickpilot_longitudinal.py`
- `selfdrive/controls/tests/test_brickpilot_longitudinal.py`
- `selfdrive/controls/lib/latcontrol_torque.py`
- `selfdrive/controls/tests/test_tucson_low_speed_torque_smoothing.py`
- `sunnypilot/selfdrive/controls/lib/latcontrol_torque_ext.py`
- `cereal/log.capnp`
- `common/params_keys.h`
- `selfdrive/ui/feedback/bookmark_tags.py`
- `selfdrive/ui/feedback/bookmark_tag_prompt.py`
- `selfdrive/ui/tests/test_bookmark_tags.py`
- `selfdrive/ui/mici/onroad/augmented_road_view.py`
- `selfdrive/ui/mici/layouts/main.py`
- `system/version.py`

The selected core Brickpilot delta versus `upstream/staging` is about 894 insertions and 12 deletions across 12 main behavior/plumbing files. The larger full-tree diff includes restored build/release artifacts, generated files, package-lock/model artifacts, and packaging drift that are not the main Tucson customization story.

Current `brickpilot` versus local `/Users/brick/comma-dev/sunnypilot-src` is a different comparison. That local source snapshot was already the Brickpilot working fork. Current `brickpilot` differs from it mostly by repo cleanup:

- 2 common tracked files changed: `.gitignore`, `system/version.py`.
- 85 files were restored into the core repo, mostly native sunnypilot build/release/config files.
- 36 split-out tool/UI files were removed from the core repo and now belong in `brickpilot-tools` or `brickpilot-web-ui`.

Conclusion: use upstream sunnypilot for "what Brickpilot changed from sunnypilot," and use `sunnypilot-src` for "why and when Brickpilot added those changes."

## Change Timeline From the Old Fork

The meaningful old-fork commits show the project learning path:

- `b9a5b1d7b3` - `Research Tucson PHEV mass override on dev`: first explicit mass correction in Hyundai values.
- `e35bce76b5` - `Brickpilot 0.2.0-alpha integrate stop creep and steering`: combined early stop-creep and steering candidates, with the explicit note to keep stock CAN-FD steering safety rate limits.
- `405c12317f` - `Brickpilot 0.2.1-alpha bookmark tags`: added on-device bookmark reason tagging.
- `2117b67c46` - `Brickpilot 0.2.2-beta Tucson stop tuning`: adjusted Tucson-specific stopping/jerk config after stop-creep/launch feedback.
- `aa9a452665` - `Brickpilot 0.3.0-alpha Tucson catch-up assist`: introduced the first Tucson catch-up longitudinal assist.
- `73b1200945` - added the Brickpilot longitudinal assist kill switch.
- `ff16a5d867` - gated Brickpilot assist on sunnypilot longitudinal context.
- `79c1738f23` - `Brickpilot 0.3.7 e2e free-road longitudinal assist`: moved toward free-road longitudinal behavior instead of only stop/creep.
- `28907c715d` / `376cabbef2` - `Brickpilot 0.3.9.7 unification base`: carried the 0.3.9.6/0.3.9.7 assist plateau and bundled analysis output in the old fork.
- `d0098ca362` - `Brickpilot 0.3.9.8 manual drive labeler`: added the full-drive manual labeler into the old combined repo before the later split.
- Current core branch import/split commits: imported 0.3.16.0 core snapshot, pruned split-out tooling, restored native sunnypilot files, bumped Brickpilot to 0.3.20.0, and now prepared the 0.3.25.0 pre-0.4.0 instrumentation build.

That history matters because the project did not start with a clean theory. It started with broad driving complaints, weak labels, and generic upstream assumptions, then gradually found which changes were actually vehicle-specific.

## Core Driving Changes

### Vehicle Mass and Specs

Brickpilot overrides the upstream Tucson 4th-gen mass:

- Upstream: `mass=1630`
- Brickpilot: `mass=1960`
- Runtime mass after standard cargo allowance: about `2096 kg` instead of about `1766 kg`

The local spec audit used the door-jamb sticker:

- GVWR: `5247 lb`
- Payload: `926 lb`
- Estimated curb mass: `4321 lb`, about `1960 kg`

Why it was done:

Upstream treated the Tucson platform too generically. The PHEV is much heavier than the generic Tucson/Hybrid assumption, and openpilot vehicle dynamics depend directly on mass for inertia and tire stiffness calculations. A wrong mass makes the controller reason about a car that is physically lighter than the real one.

Evidence:

- `may6_phev_mass_patch_report.md` showed lateral RMS improved from `0.0708` to `0.0583`, about `17.7%`, with p95/p99 lateral error also improved.
- `may6_phev_mass_patch_dinner_report.md` put the patched drives in the top slots for lateral RMS/p95 among the compared runs.

Assessment:

This is the cleanest customization in the project. It is based on physical vehicle evidence, and the observed drive metrics moved in the expected direction. Keep it.

### Tucson CAN-FD MADS/EPS Guard

Brickpilot adds a Tucson CAN-FD-specific steering request guard in Hyundai `carcontroller.py`.

What changed:

- Adds `TUCSON_CANFD_ANGLE_RECOVERY = 80`.
- Adds `TUCSON_CANFD_STEER_FAULT_COOLDOWN_FRAMES = 100`.
- Preserves MADS always-steering behavior in normal cases.
- Suppresses steering request only during EPS-risk states: active/recent temporary steering fault or high steering angle.
- Keeps stock CAN-FD torque/rate safety limits.

Why it was done:

The goal was not to make steering stronger. It was to avoid the car/EPS faulting in edge states while keeping the useful MADS behavior alive during normal enabled, gas, brake, and override cases.

Assessment:

This is a reasonable guardrail, not a performance tune. It belongs in Brickpilot because it is Tucson CAN-FD scoped and tested. Continue to log fault/cooldown behavior so it can be audited against real drives.

Important 0.4.0 follow-up:

This guard may be too aggressive for the driving goal. Upstream already uses `common_fault_avoidance` to cut steering request only after the car has spent many frames above the high-angle threshold. Brickpilot's Tucson guard latches off immediately once steering angle reaches `MAX_ANGLE` and does not recover until angle drops to `80 deg`. In tight low-speed turns, especially with Experimental Mode attempting to complete a turn, this can feel like Brickpilot stops trying the turn earlier than sunnypilot did. For 0.4.0, this needs a direct audit:

- Keep temporary steering-fault cooldown if real Tucson EPS faults justify it.
- Reconsider or remove the immediate high-angle latch.
- Prefer upstream's delayed high-angle `common_fault_avoidance` unless route evidence proves the extra latch is needed.
- At minimum, log every high-angle latch/suppression event so label review can tie "gave up on turn" feedback to the guard.

### Low-Speed Torque Texture Smoothing

Brickpilot adds Tucson CAN-FD low-speed output-torque smoothing in `sunnypilot/selfdrive/controls/lib/latcontrol_torque_ext.py`.

What changed:

- Full smoothing below 20 mph.
- Fade-out to no smoothing by 35 mph.
- Smoothing alpha `0.25`.
- Reset on driver steering and above the smoothing band.
- 25-frame cooldown after driver steering override.
- Applied before stock CAN-FD safety/rate limits.

Why it was done:

The reported problem was low-speed steering texture: small multi-step jerks and correction feel, especially in turn/parking/low-speed regions. The implementation tries to smooth command texture without changing the underlying safety limits.

Assessment:

This is a plausible tactile improvement, but it is less physically grounded than the mass patch. It should remain Tucson-scoped and should be judged by driver labels plus objective metrics: torque-rate, output pinning, lateral error, steeringPressed after corrections, and low-speed route segments.

### Tucson Longitudinal Tuning

Brickpilot adds a Tucson PHEV-specific sunnypilot Hyundai longitudinal config:

- `v_ego_starting = 0.15`
- `v_ego_stopping = 0.75`
- `stopping_decel_rate = 0.65`
- custom upper/lower lookahead jerk tables

Why it was done:

After the 0.2.1.x stop-creep work, drive 3/4 feedback showed the tune could enter or hold stopping too aggressively while launches/catch-up still felt sluggish. The 0.2.2-beta direction backed off the sticky stopping threshold/decel ramp while preserving some anti-creep bias.

Assessment:

This is a reasonable local tune, but it was born from limited early labels. It should stay only if validated against newer manual-label data. Stop/creep is especially sensitive because "good" depends heavily on lead behavior, hill/grade, braking context, and whether the PHEV is in EV/HEV/regen transition.

### Brickpilot Longitudinal Assist

Brickpilot adds `selfdrive/controls/lib/brickpilot_longitudinal.py` and wires it into `controlsd.py`.

Current live version:

- `BRICKPILOT_LONGITUDINAL_VERSION = "0.3.25.0"`
- Live behavior baseline: 0.3.9.7 conservative assist shape
- Candidate id: `ultimate_micro_frontier_174_final0008_j19_h1.769_dc0.475_md0.649`

What it does:

- Only scopes to Tucson 4th-gen, CAN-FD, openpilot longitudinal.
- Nudges `long_plan.aTarget` before LongControl in clean cruise/no-lead catch-up contexts.
- Requires positive planner accel, throttle allowed, speed deficit, accel lag, low lateral demand, no driver override, no lead, no model/radar mismatch, no FCW/model brake, no DEC/SCC/map-turn risk.
- Does not create a live planner floor.
- Allows a short decaying hold only after clean activation and only through soft planner/target gaps.
- Aborts immediately on hard suppressors.

Why it was done:

The repeated driver complaint was lazy acceleration/catch-up and poor speed-hold behavior. The offline sweeps found the strongest deployable signal in positive acceleration/catch-up windows, not in stop-creep or lateral. The current assist is a conservative way to act on that signal while avoiding lead, curve, stop, and safety-risk contexts.

Assessment:

This is useful but should be called what it is: a safety-gated heuristic from replay sweeps, not a trained model. It is intentionally conservative and likely leaves performance on the table. Its main value before 0.4.0 is that it gives a live baseline and a set of suppressor concepts that the next ML/router candidate can learn around.

Concern:

`controlsd.py` defaults the assist enabled if the `BrickpilotLongitudinalAssist` param binding is missing. That made beta testing practical, but for 0.4.0 this should become explicit and logged. Silent default-enabled behavior is not the right release posture.

### Shadow Telemetry

Brickpilot adds `controlsState.brickpilotShadow` to `cereal/log.capnp` and fills it in `controlsd.py`.

Current fields include:

- accel command/output
- near standstill and standstill states
- lead status/distance
- `aEgo`
- speed deficit
- lateral error
- torque command/output/rate
- output pinned flag
- desired lateral jerk
- steeringPressed
- long/lat active
- stopping
- lazyCandidate

Why it was done:

The project needed route-level evidence that ties felt driver complaints to controller state. Without shadow telemetry, manual labels and bookmarks are too detached from what the controller was actually doing.

Assessment:

Good direction, but incomplete for 0.4.0. The current shadow state logs outcomes and some context, but not enough of the Brickpilot assist internals. It should log active/suppressor/version/delta/hold/source data so analysis can answer "why did Brickpilot act or not act?" without reconstructing it from code later.

### On-Device Bookmark Tags

Brickpilot adds a swipe/bookmark reason prompt on the comma UI:

- Accel
- Brake
- Steer
- PHEV

The PHEV reason currently stores a broad tag set:

- `ev`
- `hev`
- `engine`
- `regen`
- `stop_creep`
- `too_lazy`
- `too_eager`
- `mads_lfa`
- `steering_jerk`

Why it was done:

Early labels were too weak. The project needed a fast way to mark felt events while driving, especially PHEV-specific behavior that upstream openpilot/sunnypilot does not know about.

Assessment:

The idea is correct. The current implementation is too broad. A PHEV bookmark currently means "something PHEV-ish happened," not "engine started," "regen blended badly," "EV launch lag," or "brake blend mismatch." That is not a strong ML label. It is useful only as a pointer for later manual review unless paired with voice text or a second-level tag.

## Tools and UI Infrastructure

### Brickpilot Tools

`brickpilot-tools` owns the offline path:

- DriveDB schema and migration tooling.
- logdrive ingest/copy/verify automation.
- route analysis and drive-test reports.
- manual drive labeler support.
- voice bookmark helper.
- ML/replay/RL research scripts.

Important design:

- `test drive` and `normal drive` can be logs-only.
- `label validation` should include logs and video.
- The safe-to-turn-off gate verifies copied artifacts have nonzero matching sizes.
- Analysis outputs are written under DriveDB, not committed to core driving code.

Assessment:

This is the right architecture. The highest-value improvement is to make each label-validation ride automatically produce a "label quality" and "training eligibility" report before any model or tuning update is accepted.

### Brickpilot Web UI

`brickpilot-web-ui` owns the local operator workflow:

- Voice recorder with real-time preview.
- Manual Labeler iframe.
- ML progress page.
- Ingest page.
- RL page.
- Rides table.
- Telegram `/logdrive` bot.
- DriveDB-backed API for labels, rides, bookmarks, review inboxes, and artifacts.

Assessment:

The UI split is correct. The UI should now be used less as a dashboard of many possibilities and more as a release gate: ingest, validate labels, train/evaluate, compare, then decide whether the next drive gets a live change.

## What We Know From DriveDB Reports

### Mass Patch

The mass patch has the cleanest evidence:

- Physical door-jamb derivation supports the new mass.
- Early drive metrics improved lateral RMS/p95/p99.
- The top lateral results in the compared set were patched drives.

Conclusion: this is a foundational correction, not a speculative tune.

### Model/Baseline Comparisons

Early reports found:

- NNv2 was smoother laterally than OP10 v3.
- OP10 v3 could be better for no-lead deficit in some conditions, but steering was busier and had ping-pong/output-rate concerns.
- Experimental/DEC combinations changed metrics but could increase pinned output.

Conclusion: do not chase one metric. A candidate that improves speed deficit but makes steering busy is not a Tucson PHEV win.

### 0.3.9 and 0.3.9.6 Longitudinal Sweeps

The 100k and 0.3.9.6 sweeps repeatedly pointed to a narrow deployable shape:

- clean activation
- no live planner floor
- positive catch-up windows
- short hold
- no lead/stop/driver/curve risk
- hard safety vetoes

Conclusion: the current 0.3.9.7 live assist is consistent with the sweep plateau. It is not the final 0.4.0 strategy, but it is a defensible baseline.

### PHEV/CAN Research

The 0.3.9.5/0.4.0 research found:

- Broad PHEV labels are useful only when overlapped with objective events and normal labels.
- Candidate CAN correlations exist around accel-lazy, regen/decel, and braking windows.
- These are correlations, not decoded truth.
- The strongest implementation surface remains lazy/catch-up.
- Stop/creep and brake blend need better explicit good/bad labels.

Conclusion: do not wire CAN hypotheses directly into live controls yet. Use them as shadow features and candidate model inputs after label validation.

## Where Brickpilot Is Driving-Wise

### Lateral

Current state:

- Better than the start of the project.
- Mass correction likely did the most reliable work.
- Low-speed torque smoothing may improve tactile feel.
- MADS/EPS guard reduces risk around high-angle/fault states.

Remaining issues:

- Low-speed steering texture still needs labels.
- Pinned-output and steeringPressed-after-correction should be watched.
- Route comparisons must avoid declaring a win from a route that simply had easier curves or fewer interventions.

### Longitudinal

Current state:

- Main remaining opportunity.
- 0.3.9.7 is conservative and should avoid obvious unsafe contexts.
- The strongest known target is no-lead/free-road catch-up and speed holding.

Remaining issues:

- Stop-and-go launch timing is not solved.
- Brake timing and regen/brake blend are under-labeled.
- "Too lazy" is common but too broad; it must be split into release labels:
  - slow launch from stop
  - slow resume behind lead
  - slow no-lead catch-up
  - uphill/grade sluggishness
  - EV/engine transition hesitation
  - speed-hold decay
  - too-late brake
  - regen/brake blend mismatch

### PHEV-Specific Behavior

Current state:

- We know the PHEV has behavior upstream does not model directly.
- We have suggestive CAN correlations.
- We do not yet have enough validated labels to treat those correlations as truth.

Remaining issues:

- Current PHEV tag is not specific enough.
- Good/normal PHEV behavior is under-labeled.
- Voice/manual labels need to become the truth layer, not just notes.

## Critique of Prior Agent Choices

The good:

- The mass correction was exactly the kind of car-specific fix Brickpilot should make.
- Keeping stock CAN-FD steering safety/rate limits while smoothing texture was a responsible boundary.
- Tucson-scoping the live longitudinal assist was the right default.
- Adding suppressors/hard gates around leads, curves, model brake, SCC/DEC, and driver override was necessary.
- Splitting tools/UI/core repos was overdue and correct.
- Building label validation infrastructure was the right pivot once weak labels became the limiting factor.

The problems:

- Early work treated weak labels and proxy events with too much confidence. Some reports used "ML" language for sweeps/rankers that were not trained, validated models.
- The label system was too coarse. A PHEV bookmark that stores every PHEV tag is not a class label.
- Unknown/unlabeled windows were sometimes structurally close to being treated as negatives. They are not negatives.
- Too many candidate iterations were generated relative to the amount of validated driver truth.
- The current core logs do not expose enough internal assist reasoning to train or audit the next candidate cleanly.
- Default-enabling the assist when the param binding is missing was acceptable for a beta drive-test branch, but it should not survive as a quiet release behavior.
- The current 0.4.0 dynamic-router candidate appears promising in reports, but it is not implemented in core as a clean shadow/live comparison yet.

The blunt assessment:

Prior agents often did useful engineering but overproduced candidates before the data deserved it. The next phase should invert that: fewer live behavior changes, better labels, stronger shadow logging, and only promote a candidate when it beats the baseline on validated events.

## Immediate Improvements Worth Making Now

These are the highest-return core improvements before the next meaningful drive.

### 1. Expand Brickpilot Shadow Telemetry

Add fields to `BrickpilotShadowState` for:

- Brickpilot longitudinal version.
- candidate id or numeric candidate code.
- assist enabled param value.
- assist active.
- suppressor bitmask.
- raw planner `aTarget`.
- assisted `aTarget`.
- assist delta.
- hold timer.
- hold target.
- held activation.
- planner-floor shadow candidate.
- longitudinal plan source.
- allowThrottle.
- model hard-brake/mismatch flags.
- DEC/SCC/map-turn risk flags.

Why:

The next analysis should not need to re-run old code to understand why Brickpilot acted. The log should say what happened and why.

### 2. Make PHEV Labels Specific

Replace or extend the one-click PHEV tag with specific labels:

- EV launch lag
- engine start/transition
- HEV transition
- regen stronger than expected
- regen weaker than expected
- brake blend awkward
- stop creep
- no-lead too lazy
- lead resume too lazy
- too eager/surge
- good/normal PHEV behavior

Best practical version:

- Keep the big PHEV button.
- Immediately open a second-level compact prompt or require a voice phrase within a time window.
- Store exact subreason, not the full list.

### 3. Add Good/Normal Labels

The system needs positive examples of "this felt right," not only complaint bookmarks.

Minimum labels:

- good acceleration
- good braking
- good steering
- good stop-go
- good PHEV transition

Why:

Without good/normal labels, the model learns only where pain happened. It cannot learn the boundary between acceptable and unacceptable behavior.

### 4. Treat Label Validation as a Release Gate

For every label-validation ride, require:

- logs plus video copied and verified
- voice/bookmark import complete
- manual label review complete
- high-confidence labels exported
- weak/ambiguous labels marked non-training
- summary report generated
- candidate comparison against current baseline

No validated labels, no model promotion.

### 5. Shadow the 0.4.0 Dynamic Router Before Live Use

Reports point to `mac_router_frontier_micro_refine_0801_0e41eccac1f69416` as the best 0.4.0 implementation-frontier candidate. It should run in shadow first.

Do not replace the 0.3.25.0 live behavior baseline immediately. Log:

- current live 0.3.25.0/0.3.9.7-baseline output
- dynamic-router proposed output
- disagreement
- suppressor differences
- future driver gas/brake proxy after each proposal
- event overlap with labels

### 6. Clean Up Small Core Tech Debt

Observed issue:

- `controlsd.py` has duplicate `liveDelay` in the `SubMaster` service list.

This is low risk but noisy. Remove it when touching telemetry.

Observed release concern:

- `BrickpilotLongitudinalAssist` should be an explicit param/toggle state, not silently default-enabled due to missing generated bindings.

### 7. Audit the Tucson High-Angle Steering Guard

The Tucson CAN-FD MADS guard likely explains why Experimental Mode may feel like it stopped fully attempting some tight turns. The current Brickpilot guard can suppress steering request immediately at `85 deg` and hold it off until `80 deg`, while upstream's generic fault avoidance is delayed by frame counting.

For 0.4.0:

- Add shadow telemetry for high-angle steering suppression.
- Compare suppressed moments against labels like "gave up on turn", "understeered", "needed driver help", and "steering fault".
- Consider reverting the high-angle part to upstream behavior while keeping the temporary fault cooldown.
- Do not judge this only by "no EPS fault" success; the goal also includes completing turns smoothly when the car can do so.

## 0.4.0 Plan

### Phase 0: No-Drive Prep

Goal: make the next drive produce training-grade evidence.

Do:

- Keep `brickpilotShadow` assist internals enabled from 0.3.25.0.
- Keep steering-guard shadow telemetry enabled from 0.3.25.0 for high-angle latch, temporary fault cooldown, and torque-zeroed frames.
- Use the 0.3.25.0 specific PHEV sublabels.
- Use 0.3.25.0 good/normal labels.
- Confirm voice bookmarks and on-device bookmarks reconcile to the same DriveDB timeline after the route is ingested.
- Add a post-drive label-quality report.
- Add 0.4.0 dynamic-router shadow output, not live output.

Exit criteria:

- A route can be ingested.
- Labels can be reviewed.
- A report can say which labels are training-eligible.
- Shadow output can be compared to current live output.

### Phase 1: One Meaningful Test Drive

Goal: one drive with maximum information, not a tiny micro-tune loop.

Drive type:

- `label validation`, not just `test`.
- Must collect logs and video.
- Use a route with repeated known conditions: stop-go, no-lead catch-up, lead resume, low-speed turns, and normal cruising.

In-drive labeling:

- Use normal reason labels: accel, brake, steer.
- Use PHEV only when a PHEV state/transition is actually observed or strongly suspected.
- Add voice notes for exact subreason.
- Mark good behavior too.

Do not:

- Change multiple live behavior knobs before this drive.
- Treat every bookmark as training data.
- Train on unknown bookmarks as negatives.

### Phase 2: Post-Drive Validation

Goal: turn the drive into reliable labels.

Do:

- Sync route and artifacts.
- Import voice sessions.
- Review video in manual labeler.
- Convert after-the-fact bookmarks into event windows by looking backward from the marker.
- Mark ambiguous labels weak/non-training.
- Export high-confidence labels.
- Generate baseline vs shadow candidate report.

Metrics to compare:

- no-lead speed deficit
- lazy duration
- catch-up time
- stop-to-5-mph time
- future driver gas/brake within 2/5/8 seconds
- accel jerk/surge
- braking lateness
- output pinned
- torque-rate
- steeringPressed after corrections
- lead exposure and route confounds

### Phase 3: Train/Evaluate Against Validated Labels

Goal: use ML where it helps most.

Use:

- high-confidence manual labels
- objective events that overlap labels
- shadow telemetry
- candidate CAN features as features, not truth
- good/normal labels as counterexamples

Avoid:

- weak labels as positives
- unlabeled windows as negatives
- broad PHEV bookmarks as direct class labels
- optimizing one route metric without driver-feel validation

Candidate focus:

- no-lead catch-up
- lead resume if labels are strong enough
- stop-go launch only after better labels
- brake/regen blend only after specific PHEV/brake labels

### Phase 4: Promote a 0.4.0 Candidate

Promotion rule:

The candidate must create felt change in a known pain area without making another area worse.

Minimum gate:

- Beats 0.3.9.7 on validated lazy/catch-up labels.
- Does not increase future driver brake/gas proxy.
- Does not increase low-speed steering corrections.
- Does not increase pinned steering output.
- Does not act in lead/curve/stop/safety veto contexts unless that context is explicitly part of the candidate and validated.
- Has a kill switch.
- Logs version/candidate id and decision reasons.

## Recommended Next Brickpilot Update Before 0.4.0

Recommended update name: `0.3.25.0 label-shadow prep`.

Include:

- richer `brickpilotShadow` fields - done in 0.3.25.0
- high-angle steering guard telemetry - done in 0.3.25.0
- explicit assist enabled state logging - done in 0.3.25.0
- remove duplicate `liveDelay` - done in 0.3.25.0
- specific PHEV sublabels - done in 0.3.25.0
- good/normal labels - done in 0.3.25.0
- DriveDB import compatibility for the new labels - done in 0.3.25.0
- dynamic-router 0.4.0 candidate in shadow only

Optional live behavior change:

- Keep the 0.3.25.0 live assist baseline as-is for the next validation drive unless there is one clearly audited constant change with a strong reason.

Why:

The user cannot do many tiny adjustment drives. The next drive should produce both driver experience and training evidence. A shadow-heavy update gives the next drive much more value without gambling on an under-validated live model.

## Source Evidence Map

Core repo evidence:

- `/Users/brick/comma-dev/brickpilot/BRICKPILOT_PROJECT_ARCHITECTURE.md`
- `/Users/brick/comma-dev/brickpilot/BRICKPILOT_REPO_BOUNDARY.md`
- `/Users/brick/comma-dev/brickpilot/system/version.py`
- `/Users/brick/comma-dev/brickpilot/opendbc_repo/opendbc/car/hyundai/values.py`
- `/Users/brick/comma-dev/brickpilot/opendbc_repo/opendbc/car/hyundai/carcontroller.py`
- `/Users/brick/comma-dev/brickpilot/opendbc_repo/opendbc/sunnypilot/car/hyundai/longitudinal/config.py`
- `/Users/brick/comma-dev/brickpilot/selfdrive/controls/controlsd.py`
- `/Users/brick/comma-dev/brickpilot/selfdrive/controls/lib/brickpilot_longitudinal.py`
- `/Users/brick/comma-dev/brickpilot/sunnypilot/selfdrive/controls/lib/latcontrol_torque_ext.py`
- `/Users/brick/comma-dev/brickpilot/cereal/log.capnp`
- `/Users/brick/comma-dev/brickpilot/common/params_keys.h`
- `/Users/brick/comma-dev/brickpilot/selfdrive/ui/feedback/bookmark_tags.py`
- `/Users/brick/comma-dev/brickpilot/selfdrive/ui/feedback/bookmark_tag_prompt.py`

Sibling repo evidence:

- `/Users/brick/comma-dev/brickpilot-tools/README.md`
- `/Users/brick/comma-dev/brickpilot-tools/scripts/drive_tests/README.md`
- `/Users/brick/comma-dev/brickpilot-tools/scripts/drive_tests/VOICE_BOOKMARKS.md`
- `/Users/brick/comma-dev/brickpilot-tools/scripts/drive_tests/brickpilot_db/README.md`
- `/Users/brick/comma-dev/brickpilot-tools/scripts/drive_tests/brickpilot_db/schema.sql`
- `/Users/brick/comma-dev/brickpilot-tools/scripts/drive_tests/manual_drive_labeler.py`
- `/Users/brick/comma-dev/brickpilot-tools/scripts/drive_tests/logdrive_automation.py`
- `/Users/brick/comma-dev/brickpilot-web-ui/README.md`
- `/Users/brick/comma-dev/brickpilot-web-ui/src/client/src/main.tsx`
- `/Users/brick/comma-dev/brickpilot-web-ui/src/server/voice.ts`
- `/Users/brick/comma-dev/brickpilot-web-ui/src/server/telegramBot.ts`
- `/Users/brick/comma-dev/brickpilot-web-ui/src/server/db.ts`

Local DriveDB report evidence:

- `/Users/brick/BrickpilotDriveDB/analysis_exports/from_macmini_repo_20260514T202808Z/analysis/drive_tests/tucson_phev_spec_audit.md`
- `/Users/brick/BrickpilotDriveDB/analysis_exports/from_macmini_repo_20260514T202808Z/analysis/drive_tests/may6_phev_mass_patch_report.md`
- `/Users/brick/BrickpilotDriveDB/analysis_exports/from_macmini_repo_20260514T202808Z/analysis/drive_tests/may6_phev_mass_patch_dinner_report.md`
- `/Users/brick/BrickpilotDriveDB/analysis_exports/from_macmini_repo_20260514T202808Z/analysis/drive_tests/may6_baseline_models_report.md`
- `/Users/brick/BrickpilotDriveDB/analysis_exports/from_macmini_repo_20260514T202808Z/analysis/drive_tests/rnd_030_alpha/ml_research_report.md`
- `/Users/brick/BrickpilotDriveDB/analysis_exports/from_macmini_repo_20260514T202808Z/analysis/drive_tests/rnd_030_alpha/030_alpha_proposal.md`
- `/Users/brick/BrickpilotDriveDB/analysis_exports/from_macmini_repo_20260514T202808Z/analysis/drive_tests/may9_030_alpha_drive1/report.md`
- `/Users/brick/BrickpilotDriveDB/analysis_exports/from_macmini_repo_20260514T202808Z/analysis/drive_tests/may9_0211_alpha_drive4_with_drive3/0211_drive4_with_drive3_022_beta_recommendations.md`
- `/Users/brick/BrickpilotDriveDB/analysis_exports/from_macmini_repo_20260514T202808Z/analysis/drive_tests/may10_039_rnd/ultimate_sweep_100k/final_audit_8am.md`
- `/Users/brick/BrickpilotDriveDB/analysis_exports/from_macmini_repo_20260514T202808Z/analysis/drive_tests/may10_039_rnd/ultimate_sweep_100k/ultimate_final_039_plan.md`
- `/Users/brick/BrickpilotDriveDB/analysis_exports/from_macmini_repo_20260514T202808Z/analysis/drive_tests/ml_rnd/overnight_20260512_0396/final_report.md`
- `/Users/brick/BrickpilotDriveDB/analysis_exports/from_macmini_repo_20260514T202808Z/analysis/drive_tests/may11_03951_label_aware_deep_dive/report.md`
- `/Users/brick/BrickpilotDriveDB/analysis_exports/from_macmini_repo_20260514T202808Z/analysis/drive_tests/may11_03951_to_040_rnd/report.md`
- `/Users/brick/BrickpilotDriveDB/review_queue_0399_may13_selected/review_feedback_report.md`

Historical fork evidence:

- `/Users/brick/comma-dev/sunnypilot-src`
- `b9a5b1d7b3` - mass override
- `e35bce76b5` - stop creep and steering
- `405c12317f` - bookmark tags
- `2117b67c46` - Tucson stop tuning
- `aa9a452665` - Tucson catch-up assist
- `79c1738f23` - free-road longitudinal assist
- `28907c715d` / `376cabbef2` - 0.3.9.7 unification base
- `d0098ca362` - manual drive labeler

## Bottom Line

Brickpilot is close to 0.4.0 in architecture, not yet in validated driving intelligence.

The path forward is:

1. Keep the physical Tucson PHEV corrections.
2. Keep current live longitudinal conservative.
3. Improve labels and shadow telemetry immediately.
4. Use one high-quality label-validation drive to produce training-grade truth.
5. Promote the 0.4.0 dynamic-router style candidate only after it beats 0.3.9.7 on validated labels without steering or safety regressions.

That is how Brickpilot gets from "we learned by trying" to "we can make big, felt improvements without needing a million tiny drives."
