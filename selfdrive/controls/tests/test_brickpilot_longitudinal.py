import unittest
from dataclasses import dataclass, field

from opendbc.car.hyundai.values import CAR, HyundaiFlags
from openpilot.selfdrive.controls.lib.brickpilot_longitudinal import (
  BRICKPILOT_HOLD_SECONDS,
  BRICKPILOT_LONGITUDINAL_VERSION,
  BRICKPILOT_LONGITUDINAL_VERSION_CODE,
  BrickpilotLongitudinalSuppressor,
  EXP_SOURCE_MIN_DEFICIT,
  EXP_SOURCE_MIN_TRAJECTORY_DEFICIT,
  EXP_SOURCE_MIN_SPEED,
  EXP_SOURCE_MAX_ASSIST_DELTA,
  FINAL_STOP_BLOCK_NONE,
  FINAL_STOP_BLOCK_ROLLING_LEAD,
  HIGH_CONF_RAMP_MAX_ASSIST_DELTA,
  HIGH_CONF_RAMP_MIN_DEFICIT,
  HIGH_CONF_RAMP_MIN_SPEED,
  HIGH_CONF_RAMP_MIN_TRAJECTORY_DEFICIT,
  LEAD_PACING_MAX_ACCEL_DELTA,
  LEAD_PACING_MAX_DECEL_DELTA,
  LEAD_PACING_MODE_ACCEL,
  LEAD_PACING_MODE_DECEL,
  LEAD_PACING_TARGET_TIME_GAP,
  MAX_ASSIST_DELTA,
  MAX_ASSISTED_A_TARGET,
  MIN_CATCHUP_SPEED_DEFICIT,
  MIN_SET_SPEED_DEFICIT_SPEED,
  PHEV_BRAKE_STATE_FRICTION_BRAKE_CANDIDATE,
  PHEV_BRAKE_STATE_REGEN_LIGHT_COAST,
  PHEV_BRAKE_STATE_STATIONARY_HOLD,
  PLANNER_FLOOR_LIVE_ACCEL,
  RAMP_CATCHUP_ASSIST_BONUS,
  RAMP_CATCHUP_MAX_ASSIST_DELTA,
  RAMP_CATCHUP_MIN_DEFICIT,
  STOP_ASSIST_BUFFER_RELAX_AMOUNT,
  STOP_ASSIST_CONTROLLER_RECOVERY_MAX_EXTRA_DECEL,
  STOP_ASSIST_FINAL_COMMIT_MAX_SPEED,
  STOP_ASSIST_FINAL_COMMIT_NEAR_STOPPED_PERSIST_SEC,
  STOP_ASSIST_FINAL_COMMIT_SOURCE_PERSIST_SEC,
  STOP_ASSIST_FINAL_COMMIT_TARGET_DECEL,
  STOP_ASSIST_ROLLING_FOLLOW_MAX_EXTRA_DECEL,
  STOP_ASSIST_REASON_CONTROLLER_UNDERBRAKE,
  STOP_ASSIST_REASON_FINAL_STOP_COMMIT,
  STOP_ASSIST_REASON_NONE,
  STOP_ASSIST_REASON_PLANNER_DEBT,
  STOP_DEBT_BUCKET_CONTROLLER_UNDERBRAKE,
  STOP_DEBT_BUCKET_INVALID_GEOMETRY,
  STOP_DEBT_BUCKET_PLANNER_LATE,
  STOP_INVALID_FAR_NONCLOSING_LEAD,
  STOP_MODE_FINAL_STOP_COMMIT,
  STOP_MODE_ROLLING_FOLLOW,
  STOP_SOURCE_CREEP,
  STOP_SOURCE_LEAD,
  STOP_SOURCE_MODEL,
  STOP_SOURCE_SHOULD_STOP,
  ULTIMATE_100K_CANDIDATE_ID,
  ULTIMATE_100K_CANDIDATE_HASH,
  brickpilot_tucson_longitudinal_assist,
  is_brickpilot_tucson_phev_scope,
)


@dataclass
class CP:
  carFingerprint: str = CAR.HYUNDAI_TUCSON_4TH_GEN
  flags: int = HyundaiFlags.CANFD
  openpilotLongitudinalControl: bool = True


@dataclass
class CC:
  longActive: bool = True


@dataclass
class CruiseState:
  standstill: bool = False


@dataclass
class CS:
  vEgo: float = 20.0
  aEgo: float = 0.0
  vCruise: float = 115.0
  standstill: bool = False
  gasPressed: bool = False
  brakePressed: bool = False
  steeringPressed: bool = False
  canValid: bool = True
  cruiseState: CruiseState = field(default_factory=CruiseState)


@dataclass
class LongPlan:
  aTarget: float = 0.55
  shouldStop: bool = False
  allowThrottle: bool = True
  hasLead: bool = False
  fcw: bool = False
  longitudinalPlanSource: str = "cruise"
  speeds: list[float] = field(default_factory=lambda: [20.0, 21.5, 22.8, 24.0])


@dataclass
class Lead:
  status: bool = False
  dRel: float = 0.0
  vRel: float = 0.0


@dataclass
class RadarState:
  leadOne: Lead = field(default_factory=Lead)


@dataclass
class Predictions:
  brakeDisengageProbs: list[float] = field(default_factory=list)
  brake3MetersPerSecondSquaredProbs: list[float] = field(default_factory=list)
  brake4MetersPerSecondSquaredProbs: list[float] = field(default_factory=list)


@dataclass
class Meta:
  hardBrakePredicted: bool = False
  disengagePredictions: Predictions = field(default_factory=Predictions)


@dataclass
class Action:
  shouldStop: bool = False


@dataclass
class ModelLead:
  prob: float = 0.0
  x: list[float] = field(default_factory=list)


@dataclass
class ModelV2:
  meta: Meta = field(default_factory=Meta)
  action: Action = field(default_factory=Action)
  leadsV3: list[ModelLead] = field(default_factory=list)


@dataclass
class Dec:
  active: bool = False


@dataclass
class SccVision:
  state: str = "disabled"
  active: bool = False
  maxPredictedLateralAccel: float = 0.0


@dataclass
class SccMap:
  state: str = "disabled"
  active: bool = False


@dataclass
class SmartCruiseControl:
  vision: SccVision = field(default_factory=SccVision)
  map: SccMap = field(default_factory=SccMap)


@dataclass
class LongitudinalPlanSP:
  dec: Dec = field(default_factory=Dec)
  smartCruiseControl: SmartCruiseControl = field(default_factory=SmartCruiseControl)


@dataclass
class CarStateSP:
  brickpilotPhevCanLoggerVersion: int = 50000
  brickpilotPhevCanCandidatePresentMask: int = 0x1
  brickpilotPhevHybridFlagSet: bool = True
  brickpilotPhevFaB4U8: int = 0
  brickpilotPhevFaB4U8Bus0: int = 0
  brickpilotPhevFaB4U8Bus130: int = 0
  brickpilotPhevFaB7U8: int = 0
  brickpilotPhevFaB7U8Bus0: int = 0
  brickpilotPhevFaB7U8Bus130: int = 0
  brickpilotBrake065B3U8: int = 0
  brickpilotBrake065B9U8: int = 0
  brickpilotBrake065B10U8: int = 0
  brickpilotBrake065B11U8: int = 0
  brickpilotBrake065B12U8: int = 0
  brickpilotPhevBaB14U8: int = 0
  brickpilotBrake065B14U8: int = 0


class TestBrickpilotLongitudinalAssist(unittest.TestCase):
  def run_assist(self, *, cp=CP(), cc=CC(), cs=CS(), plan=LongPlan(), radar=RadarState(), curvature=0.0,
                 accel_limits=(-3.5, 2.0), valid=True, model_v2=None, plan_sp=None, plan_sp_valid=True,
                 car_state_sp=None, prev_state=None, dt=0.05):
    return brickpilot_tucson_longitudinal_assist(cp, cc, cs, plan, radar, curvature, accel_limits, valid=valid,
                                                 model_v2=model_v2, longitudinal_plan_sp=plan_sp,
                                                 longitudinal_plan_sp_valid=plan_sp_valid,
                                                 car_state_sp=car_state_sp, prev_state=prev_state, dt=dt)

  def test_057_marks_native_pacing_mimic_build(self):
    self.assertEqual(BRICKPILOT_LONGITUDINAL_VERSION, "0.5.7")
    self.assertEqual(BRICKPILOT_LONGITUDINAL_VERSION_CODE, 50700)
    self.assertEqual(ULTIMATE_100K_CANDIDATE_ID, "tucson_phev_057_native_lead_pacing")
    self.assertEqual(ULTIMATE_100K_CANDIDATE_HASH, 777057000)
    self.assertAlmostEqual(MIN_CATCHUP_SPEED_DEFICIT, 2.0 * 0.44704, places=5)
    self.assertAlmostEqual(MIN_SET_SPEED_DEFICIT_SPEED, 30.0 * 0.44704, places=5)
    self.assertAlmostEqual(MAX_ASSIST_DELTA, 0.980)
    self.assertAlmostEqual(RAMP_CATCHUP_MIN_DEFICIT, 4.0 * 0.44704, places=5)
    self.assertAlmostEqual(RAMP_CATCHUP_MAX_ASSIST_DELTA, 1.080)
    self.assertAlmostEqual(RAMP_CATCHUP_ASSIST_BONUS, 0.260)
    self.assertAlmostEqual(HIGH_CONF_RAMP_MIN_SPEED, 38.0 * 0.44704, places=5)
    self.assertAlmostEqual(HIGH_CONF_RAMP_MIN_DEFICIT, 7.0 * 0.44704, places=5)
    self.assertAlmostEqual(HIGH_CONF_RAMP_MIN_TRAJECTORY_DEFICIT, 1.5 * 0.44704, places=5)
    self.assertAlmostEqual(HIGH_CONF_RAMP_MAX_ASSIST_DELTA, 1.140)
    self.assertAlmostEqual(EXP_SOURCE_MIN_SPEED, 27.0 * 0.44704, places=5)
    self.assertAlmostEqual(EXP_SOURCE_MIN_DEFICIT, 5.0 * 0.44704, places=5)
    self.assertAlmostEqual(EXP_SOURCE_MIN_TRAJECTORY_DEFICIT, 1.0 * 0.44704, places=5)
    self.assertAlmostEqual(EXP_SOURCE_MAX_ASSIST_DELTA, 0.860)
    self.assertAlmostEqual(MAX_ASSISTED_A_TARGET, 2.000)
    self.assertAlmostEqual(BRICKPILOT_HOLD_SECONDS, 2.050)
    self.assertAlmostEqual(PLANNER_FLOOR_LIVE_ACCEL, 0.72)
    self.assertAlmostEqual(STOP_ASSIST_FINAL_COMMIT_TARGET_DECEL, 1.22)
    self.assertAlmostEqual(STOP_ASSIST_FINAL_COMMIT_MAX_SPEED, 8.0 * 0.44704, places=5)
    self.assertAlmostEqual(STOP_ASSIST_FINAL_COMMIT_SOURCE_PERSIST_SEC, 0.35)
    self.assertAlmostEqual(STOP_ASSIST_FINAL_COMMIT_NEAR_STOPPED_PERSIST_SEC, 0.60)
    self.assertAlmostEqual(STOP_ASSIST_CONTROLLER_RECOVERY_MAX_EXTRA_DECEL, 0.98)
    self.assertAlmostEqual(STOP_ASSIST_ROLLING_FOLLOW_MAX_EXTRA_DECEL, 0.38)
    self.assertAlmostEqual(LEAD_PACING_TARGET_TIME_GAP, 1.05)
    self.assertAlmostEqual(LEAD_PACING_MAX_ACCEL_DELTA, 0.26)
    self.assertAlmostEqual(LEAD_PACING_MAX_DECEL_DELTA, 0.30)

  def test_scope_is_tucson_canfd_openpilot_long_only(self):
    self.assertTrue(is_brickpilot_tucson_phev_scope(CP()))
    self.assertFalse(is_brickpilot_tucson_phev_scope(CP(carFingerprint=CAR.KIA_NIRO_EV)))
    self.assertFalse(is_brickpilot_tucson_phev_scope(CP(flags=0)))
    self.assertFalse(is_brickpilot_tucson_phev_scope(CP(openpilotLongitudinalControl=False)))

  def test_active_assist_is_bounded_and_clipped_to_pid_and_brickpilot_caps(self):
    state = self.run_assist(accel_limits=(-3.5, 0.62))
    self.assertTrue(state.active)
    self.assertEqual(state.suppressors, BrickpilotLongitudinalSuppressor.NONE)
    self.assertGreater(state.assisted_a_target, state.a_target)
    self.assertLessEqual(state.assist_delta, MAX_ASSIST_DELTA)
    self.assertLessEqual(state.assisted_a_target, 0.62)
    self.assertLessEqual(state.assisted_a_target, MAX_ASSISTED_A_TARGET)
    self.assertGreater(state.hold_timer, 0.0)
    self.assertEqual(state.hold_target, state.assisted_a_target)

  def test_lower_accel_limit_does_not_inflate_assist_delta(self):
    local_catchup = CS(vEgo=30.0 * 0.44704, vCruise=90.0)
    plan = LongPlan(speeds=[30.0 * 0.44704, 34.0 * 0.44704, 37.0 * 0.44704])
    state = self.run_assist(cs=local_catchup, plan=plan, accel_limits=(1.40, 2.0))
    self.assertTrue(state.active)
    self.assertLessEqual(state.assist_delta, MAX_ASSIST_DELTA)
    self.assertLessEqual(state.assisted_a_target, state.a_target + MAX_ASSIST_DELTA)
    self.assertLess(state.assisted_a_target, 1.40)

  def test_large_clean_deficit_promotes_live_planner_floor(self):
    state = self.run_assist(plan=LongPlan(aTarget=0.10, speeds=[20.0, 23.5, 25.0, 27.0]))
    self.assertTrue(state.active)
    self.assertTrue(state.planner_floor_shadow_candidate)
    self.assertIn(BrickpilotLongitudinalSuppressor.PLANNER_NOT_POSITIVE, state.suppressors)
    self.assertGreaterEqual(state.assisted_a_target, PLANNER_FLOOR_LIVE_ACCEL)
    self.assertLessEqual(state.assist_delta, HIGH_CONF_RAMP_MAX_ASSIST_DELTA + 1e-9)

  def test_planner_floor_does_not_override_braking_planner(self):
    state = self.run_assist(plan=LongPlan(aTarget=-0.05, speeds=[20.0, 23.5, 25.0, 27.0]))
    self.assertFalse(state.active)
    self.assertTrue(state.planner_floor_shadow_candidate)
    self.assertIn(BrickpilotLongitudinalSuppressor.PLANNER_NOT_POSITIVE, state.suppressors)
    self.assertEqual(state.assisted_a_target, state.a_target)

  def test_allow_throttle_false_is_shadow_only(self):
    state = self.run_assist(plan=LongPlan(allowThrottle=False, speeds=[20.0, 23.5, 25.0, 27.0]))
    self.assertFalse(state.active)
    self.assertTrue(state.planner_floor_shadow_candidate)
    self.assertIn(BrickpilotLongitudinalSuppressor.ALLOW_THROTTLE_FALSE, state.suppressors)
    self.assertEqual(state.assisted_a_target, state.a_target)

  def test_low_speed_highway_set_speed_mistake_does_not_create_live_assist(self):
    local_road = CS(vEgo=25.0 * 0.44704, vCruise=115.0)
    weak_plan = LongPlan(aTarget=0.55, speeds=[25.0 * 0.44704, 25.5 * 0.44704])

    state = self.run_assist(cs=local_road, plan=weak_plan)

    self.assertFalse(state.active)
    self.assertIn(BrickpilotLongitudinalSuppressor.NO_CATCHUP_DEMAND, state.suppressors)
    self.assertEqual(state.assisted_a_target, state.a_target)

  def test_merge_speed_set_speed_gap_gets_ramp_catchup_delta(self):
    ramp = CS(vEgo=40.0 * 0.44704, vCruise=115.0)
    weak_plan = LongPlan(aTarget=0.55, speeds=[40.0 * 0.44704, 41.0 * 0.44704])

    state = self.run_assist(cs=ramp, plan=weak_plan)

    self.assertTrue(state.active)
    self.assertGreater(state.assist_delta, MAX_ASSIST_DELTA)
    self.assertLessEqual(state.assist_delta, RAMP_CATCHUP_MAX_ASSIST_DELTA + 1e-9)
    self.assertLessEqual(state.assisted_a_target, MAX_ASSISTED_A_TARGET)

  def test_high_deficit_ramp_requires_trajectory_confirmation(self):
    ramp = CS(vEgo=40.0 * 0.44704, vCruise=115.0)
    set_speed_only = LongPlan(aTarget=0.55, speeds=[40.0 * 0.44704, 40.8 * 0.44704])
    confirmed = LongPlan(aTarget=0.55, speeds=[40.0 * 0.44704, 42.2 * 0.44704, 43.0 * 0.44704])

    set_speed_state = self.run_assist(cs=ramp, plan=set_speed_only)
    confirmed_state = self.run_assist(cs=ramp, plan=confirmed)

    self.assertTrue(set_speed_state.active)
    self.assertLessEqual(set_speed_state.assist_delta, RAMP_CATCHUP_MAX_ASSIST_DELTA + 1e-9)
    self.assertTrue(confirmed_state.active)
    self.assertGreater(confirmed_state.assist_delta, RAMP_CATCHUP_MAX_ASSIST_DELTA)
    self.assertLessEqual(confirmed_state.assist_delta, HIGH_CONF_RAMP_MAX_ASSIST_DELTA + 1e-9)

  def test_e2e_high_deficit_bridge_gets_live_bounded_assist(self):
    ramp = CS(vEgo=45.0 * 0.44704, vCruise=115.0)
    e2e_plan = LongPlan(aTarget=0.10, longitudinalPlanSource="e2e",
                        speeds=[45.0 * 0.44704, 47.0 * 0.44704])

    state = self.run_assist(cs=ramp, plan=e2e_plan)

    self.assertTrue(state.active)
    self.assertNotIn(BrickpilotLongitudinalSuppressor.NOT_CRUISE_SOURCE, state.suppressors)
    self.assertLessEqual(state.assist_delta, EXP_SOURCE_MAX_ASSIST_DELTA + 1e-9)
    self.assertGreaterEqual(state.assisted_a_target, PLANNER_FLOOR_LIVE_ACCEL)

  def test_e2e_bridge_reaches_27_mph_exp_ramp_threshold(self):
    ramp = CS(vEgo=28.0 * 0.44704, vCruise=95.0)
    e2e_plan = LongPlan(aTarget=0.10, longitudinalPlanSource="e2e",
                        speeds=[28.0 * 0.44704, 34.0 * 0.44704])

    state = self.run_assist(cs=ramp, plan=e2e_plan)

    self.assertTrue(state.active)
    self.assertNotIn(BrickpilotLongitudinalSuppressor.NOT_CRUISE_SOURCE, state.suppressors)
    self.assertLessEqual(state.assist_delta, EXP_SOURCE_MAX_ASSIST_DELTA + 1e-9)

  def test_e2e_bridge_requires_trajectory_confirmation(self):
    ramp = CS(vEgo=35.0 * 0.44704, vCruise=115.0)
    set_speed_only = LongPlan(aTarget=0.30, longitudinalPlanSource="e2e",
                              speeds=[35.0 * 0.44704, 35.4 * 0.44704])

    state = self.run_assist(cs=ramp, plan=set_speed_only)

    self.assertFalse(state.active)
    self.assertIn(BrickpilotLongitudinalSuppressor.NOT_CRUISE_SOURCE, state.suppressors)

  def test_e2e_bridge_keeps_low_speed_or_weak_deficit_shadow_only(self):
    weak_e2e = LongPlan(longitudinalPlanSource="e2e", speeds=[20.0, 20.5])
    local = CS(vEgo=25.0 * 0.44704, vCruise=75.0)

    state = self.run_assist(cs=local, plan=weak_e2e)

    self.assertFalse(state.active)
    self.assertIn(BrickpilotLongitudinalSuppressor.NOT_CRUISE_SOURCE, state.suppressors)

  def test_far_rolling_lead_gets_small_native_pacing_accel(self):
    state = self.run_assist(radar=RadarState(Lead(status=True, dRel=80.0, vRel=0.2)))

    self.assertTrue(state.active)
    self.assertIn(BrickpilotLongitudinalSuppressor.LEAD_PRESENT_OR_LIMITING, state.suppressors)
    self.assertEqual(state.lead_pacing_mode, LEAD_PACING_MODE_ACCEL)
    self.assertGreater(state.lead_pacing_target_gap, 0.0)
    self.assertGreater(state.lead_pacing_gap_error, 0.0)
    self.assertGreater(state.lead_pacing_assist_delta, 0.0)
    self.assertLessEqual(state.lead_pacing_assist_delta, LEAD_PACING_MAX_ACCEL_DELTA)
    self.assertAlmostEqual(state.assisted_a_target, state.a_target + state.lead_pacing_assist_delta)
    self.assertFalse(state.stop_active)

  def test_close_rolling_lead_gets_small_native_pacing_decel(self):
    cruising = CS(vEgo=10.0, aEgo=0.0, vCruise=70.0)
    plan = LongPlan(aTarget=0.10, speeds=[10.0, 10.2, 10.4])
    radar = RadarState(Lead(status=True, dRel=7.0, vRel=-0.5))

    state = self.run_assist(cs=cruising, plan=plan, radar=radar)

    self.assertTrue(state.active)
    self.assertEqual(state.lead_pacing_mode, LEAD_PACING_MODE_DECEL)
    self.assertLess(state.lead_pacing_gap_error, 0.0)
    self.assertLess(state.lead_pacing_assist_delta, 0.0)
    self.assertGreaterEqual(state.lead_pacing_assist_delta, -LEAD_PACING_MAX_DECEL_DELTA)
    self.assertLess(state.assisted_a_target, state.a_target)
    self.assertFalse(state.stop_active)

  def test_urgent_stop_takes_priority_over_native_pacing(self):
    weak_plan = LongPlan(aTarget=0.05, longitudinalPlanSource="lead0", speeds=[7.0, 6.0, 4.0])
    closing = CS(vEgo=6.0, aEgo=-0.10, vCruise=45.0)
    radar = RadarState(Lead(status=True, dRel=13.0, vRel=-2.2))

    state = self.run_assist(cs=closing, plan=weak_plan, radar=radar)

    self.assertTrue(state.stop_active)
    self.assertLess(state.stop_assist_delta, 0.0)
    self.assertEqual(state.lead_pacing_assist_delta, 0.0)

  def test_native_pacing_rate_limited_from_previous_delta(self):
    previous = self.run_assist(radar=RadarState(Lead(status=True, dRel=80.0, vRel=0.2)), dt=0.20)
    self.assertTrue(previous.lead_pacing_jerk_limited)

    next_state = self.run_assist(radar=RadarState(Lead(status=True, dRel=80.0, vRel=0.2)),
                                 prev_state=previous, dt=0.20)

    self.assertGreater(next_state.lead_pacing_assist_delta, previous.lead_pacing_assist_delta)
    self.assertLessEqual(next_state.lead_pacing_assist_delta, LEAD_PACING_MAX_ACCEL_DELTA)

  def test_native_pacing_obeys_hard_safety_vetoes(self):
    cases = [
      dict(cs=CS(gasPressed=True)),
      dict(cs=CS(brakePressed=True)),
      dict(cs=CS(steeringPressed=True)),
      dict(curvature=0.004),
      dict(car_state_sp=CarStateSP(brickpilotPhevFaB4U8=220)),
    ]
    for kwargs in cases:
      with self.subTest(kwargs=kwargs):
        state = self.run_assist(radar=RadarState(Lead(status=True, dRel=80.0, vRel=0.2)), **kwargs)
        self.assertFalse(state.active)
        self.assertEqual(state.lead_pacing_assist_delta, 0.0)

  def test_short_non_safety_planner_gap_holds_only_after_clean_activation(self):
    gap_plan = LongPlan(aTarget=0.10, speeds=[20.0, 20.4, 20.6])
    gap_cs = CS(vCruise=74.0)

    first_gap = self.run_assist(cs=gap_cs, plan=gap_plan)
    self.assertFalse(first_gap.active)
    self.assertIn(BrickpilotLongitudinalSuppressor.PLANNER_NOT_POSITIVE, first_gap.suppressors)

    clean = self.run_assist()
    held = self.run_assist(cs=gap_cs, plan=gap_plan, prev_state=clean, dt=0.05)
    self.assertTrue(held.active)
    self.assertTrue(held.held_activation)
    self.assertIn(BrickpilotLongitudinalSuppressor.PLANNER_NOT_POSITIVE, held.suppressors)
    self.assertGreater(held.assisted_a_target, held.a_target)
    self.assertLess(held.hold_timer, clean.hold_timer)

  def test_hold_aborts_immediately_on_hard_safety_veto(self):
    clean = self.run_assist()
    state = self.run_assist(plan=LongPlan(shouldStop=True), prev_state=clean)
    self.assertFalse(state.active)
    self.assertIn(BrickpilotLongitudinalSuppressor.SHOULD_STOP, state.suppressors)
    self.assertEqual(state.hold_timer, 0.0)
    self.assertEqual(state.assisted_a_target, state.a_target)

  def test_dec_and_scc_turn_contexts_are_shadow_only(self):
    cases = [
      (LongitudinalPlanSP(dec=Dec(active=True)), BrickpilotLongitudinalSuppressor.DEC_OR_SCC_ACTIVE),
      (LongitudinalPlanSP(smartCruiseControl=SmartCruiseControl(vision=SccVision(state="entering", active=True))), BrickpilotLongitudinalSuppressor.DEC_OR_SCC_ACTIVE),
      (LongitudinalPlanSP(smartCruiseControl=SmartCruiseControl(vision=SccVision(maxPredictedLateralAccel=1.4))), BrickpilotLongitudinalSuppressor.HIGH_PREDICTED_LATERAL_DEMAND),
      (LongitudinalPlanSP(), BrickpilotLongitudinalSuppressor.SUNNYPILOT_PLAN_INVALID),
    ]
    for plan_sp, suppressor in cases:
      with self.subTest(suppressor=int(suppressor)):
        state = self.run_assist(plan_sp=plan_sp, plan_sp_valid=suppressor != BrickpilotLongitudinalSuppressor.SUNNYPILOT_PLAN_INVALID)
        self.assertFalse(state.active)
        self.assertIn(suppressor, state.suppressors)
        self.assertEqual(state.assisted_a_target, state.a_target)

  def test_phev_regen_or_brake_can_state_suppresses_live_assist(self):
    for car_state_sp in (
      CarStateSP(brickpilotPhevFaB4U8=220),
      CarStateSP(brickpilotPhevFaB4U8Bus0=220),
      CarStateSP(brickpilotPhevFaB4U8Bus130=220),
      CarStateSP(brickpilotBrake065B9U8=144),
    ):
      with self.subTest(car_state_sp=car_state_sp):
        state = self.run_assist(car_state_sp=car_state_sp)
        self.assertFalse(state.active)
        self.assertIn(BrickpilotLongitudinalSuppressor.PHEV_REGEN_OR_BRAKE, state.suppressors)
        self.assertEqual(state.assisted_a_target, state.a_target)

  def test_phev_regen_veto_does_not_block_required_stop_decel(self):
    lead_stop = LongPlan(aTarget=-0.05, shouldStop=True, longitudinalPlanSource="lead0", speeds=[4.0, 2.0, 0.0])
    creeping = CS(vEgo=3.0, aEgo=-0.05, vCruise=45.0)
    radar = RadarState(Lead(status=True, dRel=9.0, vRel=-2.0))

    state = self.run_assist(cs=creeping, plan=lead_stop, radar=radar,
                            car_state_sp=CarStateSP(brickpilotPhevFaB4U8=220))

    self.assertTrue(state.active)
    self.assertTrue(state.stop_active)
    self.assertEqual(state.stop_source, STOP_SOURCE_LEAD)
    self.assertIn(BrickpilotLongitudinalSuppressor.PHEV_REGEN_OR_BRAKE, state.suppressors)
    self.assertLess(state.assisted_a_target, state.a_target)
    self.assertLess(state.stop_assist_delta, 0.0)

  def test_light_regen_is_logged_as_not_enough_when_stop_debt_exists(self):
    lead_stop = LongPlan(aTarget=0.0, shouldStop=True, longitudinalPlanSource="lead0", speeds=[5.0, 3.0, 0.0])
    creeping = CS(vEgo=4.0, aEgo=-0.04, vCruise=45.0)
    radar = RadarState(Lead(status=True, dRel=11.0, vRel=-1.0))

    state = self.run_assist(cs=creeping, plan=lead_stop, radar=radar,
                            car_state_sp=CarStateSP(brickpilotPhevFaB7U8=4))

    self.assertTrue(state.stop_active)
    self.assertEqual(state.stop_brake_state, PHEV_BRAKE_STATE_REGEN_LIGHT_COAST)
    self.assertGreater(state.stop_brake_debt, 0.0)
    self.assertLess(state.assisted_a_target, state.a_target)

  def test_lead_stop_debt_can_lower_weak_planner_target(self):
    weak_plan = LongPlan(aTarget=0.05, longitudinalPlanSource="lead0", speeds=[7.0, 6.0, 4.0])
    closing = CS(vEgo=6.0, aEgo=-0.10, vCruise=45.0)
    radar = RadarState(Lead(status=True, dRel=13.0, vRel=-2.2))

    state = self.run_assist(cs=closing, plan=weak_plan, radar=radar)

    self.assertTrue(state.stop_active)
    self.assertEqual(state.stop_source, STOP_SOURCE_LEAD)
    self.assertGreater(state.stop_planner_debt, 0.0)
    self.assertLess(state.assisted_a_target, state.a_target)
    self.assertTrue(state.stop_required_decel_valid)
    self.assertTrue(state.stop_ttc_valid)
    self.assertEqual(state.stop_debt_bucket, STOP_DEBT_BUCKET_PLANNER_LATE)
    self.assertEqual(state.stop_assist_reason, STOP_ASSIST_REASON_PLANNER_DEBT)

  def test_far_nonclosing_lead_does_not_create_stop_debt_or_live_braking(self):
    far_plan = LongPlan(aTarget=0.05, longitudinalPlanSource="lead0", speeds=[7.0, 7.2, 7.5])
    cruising = CS(vEgo=7.0, aEgo=-0.02, vCruise=45.0)
    radar = RadarState(Lead(status=True, dRel=32.0, vRel=-0.05))

    state = self.run_assist(cs=cruising, plan=far_plan, radar=radar)

    self.assertFalse(state.stop_active)
    self.assertTrue(state.stop_shadow_candidate)
    self.assertFalse(state.stop_required_decel_valid)
    self.assertFalse(state.stop_ttc_valid)
    self.assertEqual(state.stop_geometry_invalid_reason, STOP_INVALID_FAR_NONCLOSING_LEAD)
    self.assertEqual(state.stop_debt_bucket, STOP_DEBT_BUCKET_INVALID_GEOMETRY)
    self.assertEqual(state.stop_brake_debt, 0.0)
    self.assertEqual(state.assisted_a_target, state.a_target)

  def test_controller_underbrake_bucket_is_logged_for_valid_stop_response_gap(self):
    braking_plan = LongPlan(aTarget=-0.80, longitudinalPlanSource="lead0", speeds=[6.0, 4.0, 1.0])
    weak_response = CS(vEgo=6.0, aEgo=-0.10, vCruise=45.0)
    radar = RadarState(Lead(status=True, dRel=12.0, vRel=-1.8))

    state = self.run_assist(cs=weak_response, plan=braking_plan, radar=radar)

    self.assertTrue(state.stop_active)
    self.assertTrue(state.stop_required_decel_valid)
    self.assertGreater(state.stop_controller_debt, 0.35)
    self.assertEqual(state.stop_debt_bucket, STOP_DEBT_BUCKET_CONTROLLER_UNDERBRAKE)
    self.assertLessEqual(state.stop_assist_delta, -0.75)
    self.assertGreaterEqual(abs(state.stop_assist_delta), STOP_ASSIST_CONTROLLER_RECOVERY_MAX_EXTRA_DECEL - 1e-9)
    self.assertEqual(state.stop_assist_reason, STOP_ASSIST_REASON_CONTROLLER_UNDERBRAKE)

  def test_should_stop_without_lead_gets_diagnostic_floor_not_stoplight_heroics(self):
    stop_plan = LongPlan(aTarget=-0.05, shouldStop=True, longitudinalPlanSource="cruise", speeds=[5.0, 2.0, 0.0])
    state = self.run_assist(cs=CS(vEgo=5.0, aEgo=-0.02, vCruise=45.0), plan=stop_plan)

    self.assertFalse(state.stop_active)
    self.assertEqual(state.stop_source, STOP_SOURCE_SHOULD_STOP)
    self.assertTrue(state.stop_shadow_candidate)
    self.assertGreaterEqual(abs(state.stop_required_decel), 0.35)
    self.assertEqual(state.assisted_a_target, state.a_target)
    self.assertEqual(state.stop_assist_reason, STOP_ASSIST_REASON_NONE)

  def test_crawl_stop_gets_final_stop_completion_target(self):
    crawl_plan = LongPlan(aTarget=-0.05, shouldStop=True, longitudinalPlanSource="lead0", speeds=[1.0, 0.2, 0.0])
    crawl = CS(vEgo=1.0, aEgo=-0.03, vCruise=25.0)
    radar = RadarState(Lead(status=True, dRel=6.0, vRel=-0.5))

    state = None
    for _ in range(4):
      state = self.run_assist(cs=crawl, plan=crawl_plan, radar=radar, prev_state=state, dt=0.20)

    assert state is not None
    self.assertTrue(state.stop_active)
    self.assertEqual(state.stop_source, STOP_SOURCE_CREEP)
    self.assertGreaterEqual(state.stop_source_persist_sec, STOP_ASSIST_FINAL_COMMIT_SOURCE_PERSIST_SEC)
    self.assertEqual(state.stop_assist_reason, STOP_ASSIST_REASON_FINAL_STOP_COMMIT)
    self.assertLessEqual(state.assisted_a_target, -STOP_ASSIST_FINAL_COMMIT_TARGET_DECEL)

  def test_crawl_final_stop_commit_requires_persistent_valid_source(self):
    crawl_plan = LongPlan(aTarget=-0.05, shouldStop=True, longitudinalPlanSource="lead0", speeds=[1.0, 0.2, 0.0])
    crawl = CS(vEgo=1.0, aEgo=-0.03, vCruise=25.0)
    radar = RadarState(Lead(status=True, dRel=6.0, vRel=-0.5))

    state = self.run_assist(cs=crawl, plan=crawl_plan, radar=radar)

    self.assertTrue(state.stop_active)
    self.assertEqual(state.stop_source, STOP_SOURCE_CREEP)
    self.assertLess(state.stop_source_persist_sec, STOP_ASSIST_FINAL_COMMIT_SOURCE_PERSIST_SEC)
    self.assertNotEqual(state.stop_assist_reason, STOP_ASSIST_REASON_FINAL_STOP_COMMIT)

  def test_final_stop_persistence_survives_lead_model_source_churn(self):
    lead_plan = LongPlan(aTarget=-0.20, shouldStop=True, longitudinalPlanSource="lead0", speeds=[2.0, 1.0, 0.0])
    model_plan = LongPlan(aTarget=-0.20, shouldStop=True, longitudinalPlanSource="cruise", speeds=[2.0, 1.0, 0.0])
    crawl = CS(vEgo=2.0, aEgo=-0.03, vCruise=25.0)
    radar = RadarState(Lead(status=True, dRel=6.0, vRel=-0.8))

    lead_state = None
    for _ in range(2):
      lead_state = self.run_assist(cs=crawl, plan=lead_plan, radar=radar, prev_state=lead_state, dt=0.20)
    assert lead_state is not None
    model_state = self.run_assist(cs=crawl, plan=model_plan, radar=RadarState(),
                                  model_v2=ModelV2(action=Action(shouldStop=True)),
                                  prev_state=lead_state, dt=0.20)

    self.assertEqual(lead_state.stop_source, STOP_SOURCE_CREEP)
    self.assertGreaterEqual(model_state.stop_source_persist_sec, STOP_ASSIST_FINAL_COMMIT_SOURCE_PERSIST_SEC)
    self.assertEqual(model_state.stop_assist_reason, STOP_ASSIST_REASON_FINAL_STOP_COMMIT)
    self.assertLessEqual(model_state.assisted_a_target, -STOP_ASSIST_FINAL_COMMIT_TARGET_DECEL)

  def test_final_stop_commit_can_start_below_eight_mph_when_source_persists(self):
    lead_plan = LongPlan(aTarget=-0.20, longitudinalPlanSource="lead0", speeds=[3.2, 1.5, 0.0])
    approach = CS(vEgo=3.2, aEgo=-0.04, vCruise=30.0)
    radar = RadarState(Lead(status=True, dRel=8.0, vRel=-2.5))

    state = None
    for _ in range(3):
      state = self.run_assist(cs=approach, plan=lead_plan, radar=radar, prev_state=state, dt=0.20)

    assert state is not None
    self.assertGreater(approach.vEgo, 5.0 * 0.44704)
    self.assertGreater(approach.vEgo, 6.0 * 0.44704)
    self.assertLessEqual(approach.vEgo, STOP_ASSIST_FINAL_COMMIT_MAX_SPEED)
    self.assertEqual(state.stop_source, STOP_SOURCE_LEAD)
    self.assertEqual(state.stop_assist_reason, STOP_ASSIST_REASON_FINAL_STOP_COMMIT)
    self.assertLessEqual(state.assisted_a_target, -STOP_ASSIST_FINAL_COMMIT_TARGET_DECEL)

  def test_rolling_lead_blocks_final_stop_commit_and_uses_gentle_rolling_follow(self):
    rolling_plan = LongPlan(aTarget=-0.20, longitudinalPlanSource="lead0", speeds=[3.0, 2.8, 2.6])
    rolling = CS(vEgo=3.0, aEgo=-0.05, vCruise=30.0)
    radar = RadarState(Lead(status=True, dRel=15.0, vRel=-0.6))

    state = None
    for _ in range(3):
      state = self.run_assist(cs=rolling, plan=rolling_plan, radar=radar, prev_state=state, dt=0.20)

    assert state is not None
    self.assertTrue(state.stop_active)
    self.assertEqual(state.stop_mode, STOP_MODE_ROLLING_FOLLOW)
    self.assertFalse(state.final_stop_allowed)
    self.assertEqual(state.final_stop_blocked_reason, FINAL_STOP_BLOCK_ROLLING_LEAD)
    self.assertGreater(state.rolling_lead_confidence, 0.9)
    self.assertLessEqual(abs(state.stop_assist_delta), STOP_ASSIST_ROLLING_FOLLOW_MAX_EXTRA_DECEL + 1e-9)
    self.assertNotEqual(state.stop_assist_reason, STOP_ASSIST_REASON_FINAL_STOP_COMMIT)

  def test_rolling_lead_should_stop_creep_source_still_uses_rolling_follow_cap(self):
    rolling_creep_plan = LongPlan(aTarget=-0.20, shouldStop=True, longitudinalPlanSource="lead0", speeds=[2.0, 1.8, 1.6])
    rolling = CS(vEgo=2.0, aEgo=-0.05, vCruise=25.0)
    radar = RadarState(Lead(status=True, dRel=14.0, vRel=-0.5))

    state = None
    for _ in range(3):
      state = self.run_assist(cs=rolling, plan=rolling_creep_plan, radar=radar, prev_state=state, dt=0.20)

    assert state is not None
    self.assertEqual(state.stop_source, STOP_SOURCE_CREEP)
    self.assertEqual(state.stop_mode, STOP_MODE_ROLLING_FOLLOW)
    self.assertEqual(state.final_stop_blocked_reason, FINAL_STOP_BLOCK_ROLLING_LEAD)
    self.assertLessEqual(abs(state.stop_assist_delta), STOP_ASSIST_ROLLING_FOLLOW_MAX_EXTRA_DECEL + 1e-9)

  def test_near_stopped_lead_persistence_allows_final_stop_commit(self):
    stopped_lead_plan = LongPlan(aTarget=-0.20, longitudinalPlanSource="lead0", speeds=[1.0, 0.5, 0.0])
    low_speed = CS(vEgo=1.0, aEgo=-0.04, vCruise=25.0)
    radar = RadarState(Lead(status=True, dRel=10.0, vRel=-0.8))

    state = None
    for _ in range(4):
      state = self.run_assist(cs=low_speed, plan=stopped_lead_plan, radar=radar, prev_state=state, dt=0.20)

    assert state is not None
    self.assertEqual(state.stop_mode, STOP_MODE_FINAL_STOP_COMMIT)
    self.assertEqual(state.final_stop_blocked_reason, FINAL_STOP_BLOCK_NONE)
    self.assertTrue(state.final_stop_allowed)
    self.assertGreaterEqual(state.lead_near_stopped_persist_sec, STOP_ASSIST_FINAL_COMMIT_NEAR_STOPPED_PERSIST_SEC)
    self.assertEqual(state.stop_assist_reason, STOP_ASSIST_REASON_FINAL_STOP_COMMIT)

  def test_model_only_stop_remains_shadow_without_prior_lead_context(self):
    model_stop = LongPlan(aTarget=-0.10, longitudinalPlanSource="cruise", speeds=[3.0, 1.5, 0.0])
    model_v2 = ModelV2(action=Action(shouldStop=True))

    state = self.run_assist(cs=CS(vEgo=3.0, aEgo=-0.02, vCruise=30.0), plan=model_stop, model_v2=model_v2)

    self.assertFalse(state.stop_active)
    self.assertTrue(state.stop_shadow_candidate)
    self.assertEqual(state.stop_source, STOP_SOURCE_MODEL)
    self.assertTrue(state.stop_required_decel_valid)
    self.assertEqual(state.stop_assist_reason, STOP_ASSIST_REASON_NONE)

  def test_model_source_can_inherit_valid_lead_final_stop_context(self):
    lead_plan = LongPlan(aTarget=-0.20, shouldStop=True, longitudinalPlanSource="lead0", speeds=[2.0, 1.0, 0.0])
    model_plan = LongPlan(aTarget=-0.20, longitudinalPlanSource="cruise", speeds=[2.0, 1.0, 0.0])
    crawl = CS(vEgo=2.0, aEgo=-0.03, vCruise=25.0)
    radar = RadarState(Lead(status=True, dRel=6.0, vRel=-0.8))

    lead_state = None
    for _ in range(2):
      lead_state = self.run_assist(cs=crawl, plan=lead_plan, radar=radar, prev_state=lead_state, dt=0.20)
    assert lead_state is not None

    model_state = self.run_assist(cs=crawl, plan=model_plan, radar=RadarState(),
                                  model_v2=ModelV2(action=Action(shouldStop=True)),
                                  prev_state=lead_state, dt=0.20)

    self.assertEqual(model_state.stop_source, STOP_SOURCE_MODEL)
    self.assertTrue(model_state.stop_active)
    self.assertEqual(model_state.stop_assist_reason, STOP_ASSIST_REASON_FINAL_STOP_COMMIT)

  def test_mild_high_ttc_lead_uses_less_blunt_buffer(self):
    mild_plan = LongPlan(aTarget=-0.10, longitudinalPlanSource="lead0", speeds=[6.0, 5.8, 5.5])
    cruising = CS(vEgo=6.0, aEgo=-0.08, vCruise=45.0)
    radar = RadarState(Lead(status=True, dRel=26.0, vRel=-0.5))

    state = self.run_assist(cs=cruising, plan=mild_plan, radar=radar)

    self.assertTrue(state.stop_shadow_candidate)
    self.assertTrue(state.stop_required_decel_valid)
    self.assertAlmostEqual(state.stop_distance_buffer, 6.25 - STOP_ASSIST_BUFFER_RELAX_AMOUNT)
    self.assertFalse(state.stop_active)
    self.assertEqual(state.assisted_a_target, state.a_target)
    self.assertEqual(state.stop_assist_reason, STOP_ASSIST_REASON_NONE)

  def test_no_lead_no_stop_intent_does_not_create_braking_assist(self):
    coast_plan = LongPlan(aTarget=-0.35, shouldStop=False, longitudinalPlanSource="cruise", speeds=[8.0, 7.5, 7.0])
    state = self.run_assist(cs=CS(vEgo=8.0, aEgo=-0.1, vCruise=40.0), plan=coast_plan)

    self.assertFalse(state.stop_active)
    self.assertEqual(state.assisted_a_target, state.a_target)

  def test_stop_debt_assist_blocks_on_high_lateral_demand(self):
    weak_plan = LongPlan(aTarget=0.05, longitudinalPlanSource="lead0", speeds=[7.0, 6.0, 4.0])
    closing = CS(vEgo=6.0, aEgo=-0.10, vCruise=45.0)
    radar = RadarState(Lead(status=True, dRel=13.0, vRel=-2.2))

    state = self.run_assist(cs=closing, plan=weak_plan, radar=radar, curvature=0.03)

    self.assertFalse(state.stop_active)
    self.assertTrue(state.stop_shadow_candidate)
    self.assertEqual(state.assisted_a_target, state.a_target)

  def test_phev_auto_hold_can_state_suppresses_live_assist(self):
    state = self.run_assist(cs=CS(vEgo=0.2, vCruise=35.0), car_state_sp=CarStateSP(brickpilotPhevBaB14U8=1))
    self.assertFalse(state.active)
    self.assertIn(BrickpilotLongitudinalSuppressor.PHEV_STATIONARY_OR_AUTO_HOLD, state.suppressors)
    self.assertEqual(state.assisted_a_target, state.a_target)
    self.assertEqual(state.stop_brake_state, PHEV_BRAKE_STATE_STATIONARY_HOLD)

  def test_auto_hold_candidate_requires_near_zero_speed(self):
    state = self.run_assist(car_state_sp=CarStateSP(brickpilotPhevBaB14U8=1))
    self.assertTrue(state.active)
    self.assertNotIn(BrickpilotLongitudinalSuppressor.PHEV_STATIONARY_OR_AUTO_HOLD, state.suppressors)

  def test_brake065_friction_candidate_is_logged_and_suppresses_positive_assist(self):
    state = self.run_assist(car_state_sp=CarStateSP(brickpilotBrake065B3U8=25))
    self.assertFalse(state.active)
    self.assertIn(BrickpilotLongitudinalSuppressor.PHEV_REGEN_OR_BRAKE, state.suppressors)
    self.assertEqual(state.stop_brake_state, PHEV_BRAKE_STATE_FRICTION_BRAKE_CANDIDATE)

  def test_phev_can_guard_requires_logger_and_phev_runtime(self):
    cases = [
      CarStateSP(brickpilotPhevCanLoggerVersion=0, brickpilotPhevFaB4U8=220, brickpilotPhevBaB14U8=1),
      CarStateSP(brickpilotPhevCanCandidatePresentMask=0, brickpilotPhevHybridFlagSet=False,
                 brickpilotPhevFaB4U8=220, brickpilotPhevBaB14U8=1),
    ]
    for car_state_sp in cases:
      with self.subTest(car_state_sp=car_state_sp):
        state = self.run_assist(car_state_sp=car_state_sp)
        self.assertTrue(state.active)
        self.assertNotIn(BrickpilotLongitudinalSuppressor.PHEV_REGEN_OR_BRAKE, state.suppressors)
        self.assertNotIn(BrickpilotLongitudinalSuppressor.PHEV_STATIONARY_OR_AUTO_HOLD, state.suppressors)

  def test_safety_and_conservative_suppressors(self):
    cases = [
      (dict(cp=CP(carFingerprint=CAR.KIA_NIRO_EV)), BrickpilotLongitudinalSuppressor.NOT_TUCSON_CANFD),
      (dict(cp=CP(openpilotLongitudinalControl=False)), BrickpilotLongitudinalSuppressor.OPENPILOT_LONG_REQUIRED),
      (dict(cc=CC(longActive=False)), BrickpilotLongitudinalSuppressor.LONG_INACTIVE),
      (dict(valid=False), BrickpilotLongitudinalSuppressor.INVALID),
      (dict(plan=LongPlan(shouldStop=True)), BrickpilotLongitudinalSuppressor.SHOULD_STOP),
      (dict(plan=LongPlan(fcw=True)), BrickpilotLongitudinalSuppressor.FCW_OR_MODEL_BRAKE),
      (dict(model_v2=ModelV2(meta=Meta(hardBrakePredicted=True))), BrickpilotLongitudinalSuppressor.FCW_OR_MODEL_BRAKE),
      (dict(model_v2=ModelV2(meta=Meta(disengagePredictions=Predictions(brake4MetersPerSecondSquaredProbs=[0.2])))), BrickpilotLongitudinalSuppressor.FCW_OR_MODEL_BRAKE),
      (dict(model_v2=ModelV2(leadsV3=[ModelLead(prob=0.8, x=[25.0])])), BrickpilotLongitudinalSuppressor.RADAR_MODEL_MISMATCH),
      (dict(cs=CS(vEgo=25.0 * 0.44704, vCruise=75.0),
            plan=LongPlan(longitudinalPlanSource="e2e", speeds=[25.0 * 0.44704, 25.5 * 0.44704])),
       BrickpilotLongitudinalSuppressor.NOT_CRUISE_SOURCE),
      (dict(plan=LongPlan(longitudinalPlanSource="lead0")), BrickpilotLongitudinalSuppressor.LEAD_PRESENT_OR_LIMITING),
      (dict(cs=CS(vEgo=1.5, vCruise=45.0)), BrickpilotLongitudinalSuppressor.STOP_CREEP_BAND),
      (dict(cs=CS(gasPressed=True)), BrickpilotLongitudinalSuppressor.DRIVER_OVERRIDE),
      (dict(cs=CS(brakePressed=True)), BrickpilotLongitudinalSuppressor.DRIVER_OVERRIDE),
      (dict(cs=CS(steeringPressed=True)), BrickpilotLongitudinalSuppressor.STEERING_OVERRIDE),
      (dict(curvature=0.004), BrickpilotLongitudinalSuppressor.HIGH_LATERAL_DEMAND),
      (dict(cs=CS(vCruise=75.0), plan=LongPlan(speeds=[20.0, 20.5])), BrickpilotLongitudinalSuppressor.NO_CATCHUP_DEMAND),
      (dict(cs=CS(aEgo=0.53)), BrickpilotLongitudinalSuppressor.ACCEL_LAG_TOO_SMALL),
    ]
    for kwargs, suppressor in cases:
      with self.subTest(suppressor=int(suppressor)):
        state = self.run_assist(**kwargs)
        self.assertFalse(state.active)
        self.assertIn(suppressor, state.suppressors)
        self.assertEqual(state.assisted_a_target, state.a_target)


if __name__ == "__main__":
  unittest.main()
