import unittest
from dataclasses import dataclass, field

from opendbc.car.hyundai.values import CAR, HyundaiFlags
from openpilot.selfdrive.controls.lib.brickpilot_longitudinal import (
  BRICKPILOT_HOLD_SECONDS,
  BRICKPILOT_LONGITUDINAL_VERSION,
  BRICKPILOT_LONGITUDINAL_VERSION_CODE,
  BrickpilotLongitudinalSuppressor,
  EXP_SOURCE_MIN_DEFICIT,
  EXP_SOURCE_MIN_SPEED,
  EXP_SOURCE_MAX_ASSIST_DELTA,
  MAX_ASSIST_DELTA,
  MAX_ASSISTED_A_TARGET,
  MIN_CATCHUP_SPEED_DEFICIT,
  MIN_SET_SPEED_DEFICIT_SPEED,
  PLANNER_FLOOR_LIVE_ACCEL,
  RAMP_CATCHUP_ASSIST_BONUS,
  RAMP_CATCHUP_MAX_ASSIST_DELTA,
  RAMP_CATCHUP_MIN_DEFICIT,
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
  brickpilotPhevCanLoggerVersion: int = 40400
  brickpilotPhevCanCandidatePresentMask: int = 0x1
  brickpilotPhevHybridFlagSet: bool = True
  brickpilotPhevFaB4U8: int = 0
  brickpilotPhevFaB4U8Bus0: int = 0
  brickpilotPhevFaB4U8Bus130: int = 0
  brickpilotBrake065B9U8: int = 0
  brickpilotPhevBaB14U8: int = 0


class TestBrickpilotLongitudinalAssist(unittest.TestCase):
  def run_assist(self, *, cp=CP(), cc=CC(), cs=CS(), plan=LongPlan(), radar=RadarState(), curvature=0.0,
                 accel_limits=(-3.5, 2.0), valid=True, model_v2=None, plan_sp=None, plan_sp_valid=True,
                 car_state_sp=None, prev_state=None, dt=0.05):
    return brickpilot_tucson_longitudinal_assist(cp, cc, cs, plan, radar, curvature, accel_limits, valid=valid,
                                                 model_v2=model_v2, longitudinal_plan_sp=plan_sp,
                                                 longitudinal_plan_sp_valid=plan_sp_valid,
                                                 car_state_sp=car_state_sp, prev_state=prev_state, dt=dt)

  def test_047_keeps_ramp_exp_behavior_and_marks_return_glide_build(self):
    self.assertEqual(BRICKPILOT_LONGITUDINAL_VERSION, "0.4.7")
    self.assertEqual(BRICKPILOT_LONGITUDINAL_VERSION_CODE, 40700)
    self.assertEqual(ULTIMATE_100K_CANDIDATE_ID, "tucson_phev_047_ramp4_exp5_returnglide_damp140")
    self.assertEqual(ULTIMATE_100K_CANDIDATE_HASH, 4214335218)
    self.assertAlmostEqual(MIN_CATCHUP_SPEED_DEFICIT, 2.0 * 0.44704, places=5)
    self.assertAlmostEqual(MIN_SET_SPEED_DEFICIT_SPEED, 30.0 * 0.44704, places=5)
    self.assertAlmostEqual(MAX_ASSIST_DELTA, 0.980)
    self.assertAlmostEqual(RAMP_CATCHUP_MIN_DEFICIT, 4.0 * 0.44704, places=5)
    self.assertAlmostEqual(RAMP_CATCHUP_MAX_ASSIST_DELTA, 1.080)
    self.assertAlmostEqual(RAMP_CATCHUP_ASSIST_BONUS, 0.260)
    self.assertAlmostEqual(EXP_SOURCE_MIN_SPEED, 30.0 * 0.44704, places=5)
    self.assertAlmostEqual(EXP_SOURCE_MIN_DEFICIT, 5.0 * 0.44704, places=5)
    self.assertAlmostEqual(EXP_SOURCE_MAX_ASSIST_DELTA, 0.860)
    self.assertAlmostEqual(MAX_ASSISTED_A_TARGET, 2.000)
    self.assertAlmostEqual(BRICKPILOT_HOLD_SECONDS, 2.050)
    self.assertAlmostEqual(PLANNER_FLOOR_LIVE_ACCEL, 0.72)

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
    self.assertLessEqual(state.assist_delta, RAMP_CATCHUP_MAX_ASSIST_DELTA + 1e-9)

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

  def test_e2e_high_deficit_bridge_gets_live_bounded_assist(self):
    ramp = CS(vEgo=45.0 * 0.44704, vCruise=115.0)
    e2e_plan = LongPlan(aTarget=0.10, longitudinalPlanSource="e2e",
                        speeds=[45.0 * 0.44704, 47.0 * 0.44704])

    state = self.run_assist(cs=ramp, plan=e2e_plan)

    self.assertTrue(state.active)
    self.assertNotIn(BrickpilotLongitudinalSuppressor.NOT_CRUISE_SOURCE, state.suppressors)
    self.assertLessEqual(state.assist_delta, EXP_SOURCE_MAX_ASSIST_DELTA + 1e-9)
    self.assertGreaterEqual(state.assisted_a_target, PLANNER_FLOOR_LIVE_ACCEL)

  def test_e2e_bridge_reaches_30_mph_exp_ramp_threshold(self):
    ramp = CS(vEgo=31.0 * 0.44704, vCruise=95.0)
    e2e_plan = LongPlan(aTarget=0.10, longitudinalPlanSource="e2e",
                        speeds=[31.0 * 0.44704, 32.0 * 0.44704])

    state = self.run_assist(cs=ramp, plan=e2e_plan)

    self.assertTrue(state.active)
    self.assertNotIn(BrickpilotLongitudinalSuppressor.NOT_CRUISE_SOURCE, state.suppressors)
    self.assertLessEqual(state.assist_delta, EXP_SOURCE_MAX_ASSIST_DELTA + 1e-9)

  def test_e2e_bridge_keeps_low_speed_or_weak_deficit_shadow_only(self):
    weak_e2e = LongPlan(longitudinalPlanSource="e2e", speeds=[20.0, 20.5])
    local = CS(vEgo=25.0 * 0.44704, vCruise=75.0)

    state = self.run_assist(cs=local, plan=weak_e2e)

    self.assertFalse(state.active)
    self.assertIn(BrickpilotLongitudinalSuppressor.NOT_CRUISE_SOURCE, state.suppressors)

  def test_far_low_lead_is_not_live_promoted_in_0396(self):
    state = self.run_assist(radar=RadarState(Lead(status=True, dRel=80.0, vRel=0.2)))
    self.assertFalse(state.active)
    self.assertIn(BrickpilotLongitudinalSuppressor.LEAD_PRESENT_OR_LIMITING, state.suppressors)
    self.assertEqual(state.assisted_a_target, state.a_target)

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

  def test_phev_auto_hold_can_state_suppresses_live_assist(self):
    state = self.run_assist(car_state_sp=CarStateSP(brickpilotPhevBaB14U8=1))
    self.assertFalse(state.active)
    self.assertIn(BrickpilotLongitudinalSuppressor.PHEV_STATIONARY_OR_AUTO_HOLD, state.suppressors)
    self.assertEqual(state.assisted_a_target, state.a_target)

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
      (dict(radar=RadarState(Lead(status=True, dRel=90.0, vRel=0.0))), BrickpilotLongitudinalSuppressor.LEAD_PRESENT_OR_LIMITING),
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
