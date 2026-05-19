from dataclasses import dataclass
from enum import IntFlag
from typing import Any

import numpy as np

from openpilot.common.constants import CV
from opendbc.car.hyundai.values import CAR, HyundaiFlags, CarControllerParams


class BrickpilotLongitudinalSuppressor(IntFlag):
  NONE = 0
  NOT_TUCSON_CANFD = 1 << 0
  INVALID = 1 << 1
  LONG_INACTIVE = 1 << 2
  PLANNER_NOT_POSITIVE = 1 << 3
  ALLOW_THROTTLE_FALSE = 1 << 4
  SHOULD_STOP = 1 << 5
  STOP_CREEP_BAND = 1 << 6
  DRIVER_OVERRIDE = 1 << 7
  STEERING_OVERRIDE = 1 << 8
  LEAD_PRESENT_OR_LIMITING = 1 << 9
  HIGH_LATERAL_DEMAND = 1 << 10
  NO_CATCHUP_DEMAND = 1 << 11
  ACCEL_LAG_TOO_SMALL = 1 << 12
  FCW_OR_MODEL_BRAKE = 1 << 13
  NOT_CRUISE_SOURCE = 1 << 14
  OPENPILOT_LONG_REQUIRED = 1 << 15
  RADAR_MODEL_MISMATCH = 1 << 16
  SUNNYPILOT_PLAN_INVALID = 1 << 17
  DEC_OR_SCC_ACTIVE = 1 << 18
  HIGH_PREDICTED_LATERAL_DEMAND = 1 << 19
  PHEV_REGEN_OR_BRAKE = 1 << 20
  PHEV_STATIONARY_OR_AUTO_HOLD = 1 << 21


@dataclass(frozen=True)
class BrickpilotLongitudinalAssistState:
  enabled_for_vehicle: bool = False
  active: bool = False
  shadow_candidate: bool = False
  planner_floor_shadow_candidate: bool = False
  suppressors: BrickpilotLongitudinalSuppressor = BrickpilotLongitudinalSuppressor.NONE
  a_target: float = 0.0
  assisted_a_target: float = 0.0
  assist_delta: float = 0.0
  hold_timer: float = 0.0
  hold_target: float = 0.0
  held_activation: bool = False
  speed_deficit: float = 0.0
  accel_lag: float = 0.0
  lateral_demand: float = 0.0
  lead_distance: float = 0.0
  lead_closing: bool = False


# Brickpilot 0.4.8 keeps the proven catch-up guards and adds a trajectory-
# confirmed high-deficit branch so road tests can separate ordinary set-speed
# mistakes from real ramp/merge under-acceleration.
BRICKPILOT_LONGITUDINAL_VERSION = "0.4.8"
BRICKPILOT_LONGITUDINAL_VERSION_CODE = 40800
ULTIMATE_100K_CANDIDATE_ID = "tucson_phev_048_friction_twostage_yololite_damp170"
ULTIMATE_100K_CANDIDATE_HASH = 3268147089
PHEV_CAN_REGEN_LOGGER_MIN_VERSION = 33000
PHEV_CAN_STATIONARY_LOGGER_MIN_VERSION = 40000
PHEV_FA_B4_REGEN_U8_THRESHOLD = 160
PHEV_BRAKE_065_B9_U8_THRESHOLD = 128
PHEV_BA_B14_AUTO_HOLD_VALUE = 1
MIN_POSITIVE_PLANNER_ACCEL = 0.25
MIN_ACCEL_LAG = 0.05
MIN_ASSIST_SPEED = 7.0 * CV.MPH_TO_MS
MIN_CATCHUP_SPEED_DEFICIT = 2.0 * CV.MPH_TO_MS
MIN_SET_SPEED_DEFICIT_SPEED = 30.0 * CV.MPH_TO_MS
LOW_SPEED_SET_SPEED_DEFICIT_CAP = 1.5 * CV.MPH_TO_MS
HOLD_GAP_SPEED_DEFICIT_MARGIN = 1.5 * CV.MPH_TO_MS
PLANNER_FLOOR_SHADOW_DEFICIT = 3.0 * CV.MPH_TO_MS
PLANNER_FLOOR_LIVE_DEFICIT = 3.0 * CV.MPH_TO_MS
PLANNER_FLOOR_LIVE_ACCEL = 0.72
PLANNER_FLOOR_LIVE_MIN_ATARGET = 0.0
MAX_LATERAL_ACCEL_FOR_ASSIST = 0.90
MAX_SCC_PREDICTED_LATERAL_ACCEL_FOR_ASSIST = 1.20
CURVE_SOFT_DECAY_LATERAL_ACCEL = 0.55
CURVE_SOFT_DELTA_DECAY = 0.84
MIN_ASSIST_DELTA = 0.145
DEFICIT_ASSIST_COEFF_PER_MPH = 0.046
LAG_ASSIST_COEFF = 0.220
MAX_ASSIST_DELTA = 0.980
RAMP_CATCHUP_MIN_SPEED = 24.0 * CV.MPH_TO_MS
RAMP_CATCHUP_MIN_DEFICIT = 4.0 * CV.MPH_TO_MS
RAMP_CATCHUP_MAX_ASSIST_DELTA = 1.080
RAMP_CATCHUP_ASSIST_BONUS = 0.260
HIGH_CONF_RAMP_MIN_SPEED = 38.0 * CV.MPH_TO_MS
HIGH_CONF_RAMP_MIN_DEFICIT = 7.0 * CV.MPH_TO_MS
HIGH_CONF_RAMP_MIN_TRAJECTORY_DEFICIT = 1.5 * CV.MPH_TO_MS
HIGH_CONF_RAMP_MAX_LATERAL_ACCEL = 0.48
HIGH_CONF_RAMP_MAX_ASSIST_DELTA = 1.140
HIGH_CONF_RAMP_ASSIST_BONUS = 0.340
MAX_ASSISTED_A_TARGET = 2.000
EXP_SOURCE_MIN_SPEED = 27.0 * CV.MPH_TO_MS
EXP_SOURCE_MIN_DEFICIT = 5.0 * CV.MPH_TO_MS
EXP_SOURCE_MIN_TRAJECTORY_DEFICIT = 1.0 * CV.MPH_TO_MS
EXP_SOURCE_MAX_LATERAL_ACCEL = 0.70
EXP_SOURCE_MAX_ASSIST_DELTA = 0.860
BRICKPILOT_HOLD_SECONDS = 2.050
BRICKPILOT_HOLD_DECAY = 0.550
LEAD_PRESENT_DISTANCE_UNKNOWN = 0.01
CRUISE_SOURCE_NAMES = {"", "0", "cruise"}
LEAD_SOURCE_NAMES = {"1", "2", "3", "lead0", "lead1", "lead2"}
EXPERIMENTAL_SOURCE_NAMES = {"4", "e2e"}
SOFT_HOLD_SUPPRESSORS = (BrickpilotLongitudinalSuppressor.PLANNER_NOT_POSITIVE |
                         BrickpilotLongitudinalSuppressor.NO_CATCHUP_DEMAND |
                         BrickpilotLongitudinalSuppressor.ACCEL_LAG_TOO_SMALL)


def _safe_float(value: Any, default: float = 0.0) -> float:
  try:
    ret = float(value)
  except (TypeError, ValueError):
    return default
  if not np.isfinite(ret):
    return default
  return ret


def _safe_enum_name(value: Any) -> str:
  raw = getattr(value, "raw", None)
  if raw is not None:
    value = raw
  return str(value).split(".")[-1].lower()


def _safe_int(value: Any, default: int = 0) -> int:
  try:
    return int(value)
  except (TypeError, ValueError):
    return default


def is_brickpilot_tucson_phev_scope(CP: Any) -> bool:
  """Tucson/CAN-FD scoped Brickpilot longitudinal research gate."""
  return bool(getattr(CP, "carFingerprint", None) == CAR.HYUNDAI_TUCSON_4TH_GEN and
              getattr(CP, "flags", 0) & HyundaiFlags.CANFD and
              getattr(CP, "openpilotLongitudinalControl", True))


def _phev_can_logger_has_phev_runtime(car_state_sp: Any | None, min_version: int) -> bool:
  if car_state_sp is None:
    return False
  logger_version = _safe_int(getattr(car_state_sp, "brickpilotPhevCanLoggerVersion", 0))
  present_mask = _safe_int(getattr(car_state_sp, "brickpilotPhevCanCandidatePresentMask", 0))
  return bool(logger_version >= min_version and
              (getattr(car_state_sp, "brickpilotPhevHybridFlagSet", False) or (present_mask & 0x1)))


def _phev_regen_or_brake_active(car_state_sp: Any | None) -> bool:
  if not _phev_can_logger_has_phev_runtime(car_state_sp, PHEV_CAN_REGEN_LOGGER_MIN_VERSION):
    return False

  fa_b4_values = (
    _safe_int(getattr(car_state_sp, "brickpilotPhevFaB4U8", 0)),
    _safe_int(getattr(car_state_sp, "brickpilotPhevFaB4U8Bus0", 0)),
    _safe_int(getattr(car_state_sp, "brickpilotPhevFaB4U8Bus130", 0)),
  )
  brake_b9 = _safe_int(getattr(car_state_sp, "brickpilotBrake065B9U8", 0))
  return bool(max(fa_b4_values) >= PHEV_FA_B4_REGEN_U8_THRESHOLD or
              brake_b9 >= PHEV_BRAKE_065_B9_U8_THRESHOLD)


def _phev_stationary_or_auto_hold_active(car_state_sp: Any | None) -> bool:
  if not _phev_can_logger_has_phev_runtime(car_state_sp, PHEV_CAN_STATIONARY_LOGGER_MIN_VERSION):
    return False
  return _safe_int(getattr(car_state_sp, "brickpilotPhevBaB14U8", 0)) == PHEV_BA_B14_AUTO_HOLD_VALUE


def _trajectory_speed_deficit(long_plan: Any, v_ego: float) -> float:
  speeds = list(getattr(long_plan, "speeds", []) or [])[:8]
  if not speeds:
    return 0.0
  return max(0.0, max(_safe_float(speed, v_ego) for speed in speeds) - v_ego)


def _set_speed_deficit(CS: Any, v_ego: float) -> float:
  v_cruise_kph = _safe_float(getattr(CS, "vCruise", 0.0))
  # openpilot commonly uses 255 kph as unavailable. Do not let that create a
  # bogus catch-up demand; the planner trajectory remains as a fallback.
  if v_cruise_kph <= 0.0 or v_cruise_kph >= 200.0:
    return 0.0
  return max(0.0, v_cruise_kph * CV.KPH_TO_MS - v_ego)


def _combined_speed_deficit(CS: Any, long_plan: Any, v_ego: float) -> float:
  trajectory_deficit = _trajectory_speed_deficit(long_plan, v_ego)
  set_speed_deficit = _set_speed_deficit(CS, v_ego)
  if v_ego < MIN_SET_SPEED_DEFICIT_SPEED:
    set_speed_deficit = min(set_speed_deficit, LOW_SPEED_SET_SPEED_DEFICIT_CAP)
  return max(trajectory_deficit, set_speed_deficit)


def _lead_present_or_limiting(long_plan: Any, radar_state: Any) -> tuple[bool, float, bool, bool]:
  lead = getattr(radar_state, "leadOne", None)
  radar_lead = bool(getattr(lead, "status", False))
  plan_has_lead = bool(getattr(long_plan, "hasLead", False))
  source_name = _safe_enum_name(getattr(long_plan, "longitudinalPlanSource", "cruise"))
  lead_source = source_name in LEAD_SOURCE_NAMES

  d_rel = _safe_float(getattr(lead, "dRel", 0.0)) if lead is not None else 0.0
  v_rel = _safe_float(getattr(lead, "vRel", 0.0)) if lead is not None else 0.0
  # 0.3.9.7 keeps the 0.3.9.6 road behavior: suppress all radar/plan-lead contexts. The replay
  # lab found far/low-lead promising but not proven enough for live promotion.
  present_or_limiting = radar_lead or plan_has_lead or lead_source
  return present_or_limiting, d_rel if radar_lead else 0.0, bool(radar_lead and v_rel < -0.1), radar_lead


def _max_prob(values: Any) -> float:
  return max((_safe_float(v) for v in (list(values) if values is not None else [])), default=0.0)


def _model_hard_brake_or_mismatch(model_v2: Any, radar_has_lead: bool) -> tuple[bool, bool]:
  if model_v2 is None:
    return False, False
  meta = getattr(model_v2, "meta", None)
  preds = getattr(meta, "disengagePredictions", None)
  hard_brake = bool(getattr(meta, "hardBrakePredicted", False)) or \
               bool(getattr(getattr(model_v2, "action", None), "shouldStop", False)) or \
               _max_prob(getattr(preds, "brakeDisengageProbs", [])) > 0.25 or \
               _max_prob(getattr(preds, "brake3MetersPerSecondSquaredProbs", [])) > 0.15 or \
               _max_prob(getattr(preds, "brake4MetersPerSecondSquaredProbs", [])) > 0.10

  leads = list(getattr(model_v2, "leadsV3", []) or [])
  lead0 = leads[0] if leads else None
  model_prob = _safe_float(getattr(lead0, "prob", 0.0)) if lead0 is not None else 0.0
  xs = list(getattr(lead0, "x", []) or []) if lead0 is not None else []
  model_x0 = _safe_float(xs[0], 999.0) if xs else 999.0
  # If model is confident about a lead while radar has none, do not add energy.
  # Even distant model-only leads were tagged as radar/model mismatch in the
  # replay corpus and are cheap to veto for this conservative candidate.
  mismatch = bool(not radar_has_lead and model_prob >= 0.60)
  return hard_brake, mismatch


def _sunnypilot_longitudinal_plan_risk(longitudinal_plan_sp: Any | None) -> tuple[bool, bool]:
  if longitudinal_plan_sp is None:
    return False, False

  dec = getattr(longitudinal_plan_sp, "dec", None)
  dec_active = bool(getattr(dec, "active", False))

  scc = getattr(longitudinal_plan_sp, "smartCruiseControl", None)
  vision = getattr(scc, "vision", None)
  vision_state = _safe_enum_name(getattr(vision, "state", "disabled"))
  vision_active = bool(getattr(vision, "active", False))
  scc_turning = vision_active and vision_state in {"entering", "turning", "leaving"}
  high_predicted_lateral = abs(_safe_float(getattr(vision, "maxPredictedLateralAccel", 0.0))) > MAX_SCC_PREDICTED_LATERAL_ACCEL_FOR_ASSIST

  map_plan = getattr(scc, "map", None)
  map_state = _safe_enum_name(getattr(map_plan, "state", "disabled"))
  map_active = bool(getattr(map_plan, "active", False))
  map_turning = map_active and map_state == "turning"

  return bool(dec_active or scc_turning or map_turning), high_predicted_lateral


def brickpilot_tucson_longitudinal_assist(CP: Any, CC: Any, CS: Any, long_plan: Any, radar_state: Any,
                                          current_curvature: float, accel_limits: tuple[float, float],
                                          valid: bool = True, model_v2: Any | None = None,
                                          longitudinal_plan_sp: Any | None = None,
                                          longitudinal_plan_sp_valid: bool = True,
                                          car_state_sp: Any | None = None,
                                          prev_state: BrickpilotLongitudinalAssistState | None = None,
                                          dt: float = 0.05) -> BrickpilotLongitudinalAssistState:
  """Conservative Tucson catch-up convergence assist with PHEV CAN-aware vetoes.

  This never creates a planner-side floor and never changes safety/rate limits.
  It nudges the aTarget passed into LongControl in clean catch-up contexts, and
  after clean activation it may briefly decay that target through non-safety
  planner/target gaps. Any hard safety veto aborts immediately.
  """
  enabled_for_vehicle = is_brickpilot_tucson_phev_scope(CP)
  v_ego = _safe_float(getattr(CS, "vEgo", 0.0))
  a_ego = _safe_float(getattr(CS, "aEgo", 0.0))
  a_target = _safe_float(getattr(long_plan, "aTarget", 0.0))
  trajectory_deficit = _trajectory_speed_deficit(long_plan, v_ego)
  speed_deficit = _combined_speed_deficit(CS, long_plan, v_ego)
  lateral_demand = abs(_safe_float(current_curvature)) * v_ego * v_ego
  accel_lag = max(0.0, a_target - a_ego)
  suppressors = BrickpilotLongitudinalSuppressor.NONE

  if not enabled_for_vehicle:
    suppressors |= BrickpilotLongitudinalSuppressor.NOT_TUCSON_CANFD
  if not getattr(CP, "openpilotLongitudinalControl", True):
    suppressors |= BrickpilotLongitudinalSuppressor.OPENPILOT_LONG_REQUIRED
  if not valid:
    suppressors |= BrickpilotLongitudinalSuppressor.INVALID
  if not longitudinal_plan_sp_valid:
    suppressors |= BrickpilotLongitudinalSuppressor.SUNNYPILOT_PLAN_INVALID
  if not bool(getattr(CC, "longActive", False)):
    suppressors |= BrickpilotLongitudinalSuppressor.LONG_INACTIVE
  if a_target < MIN_POSITIVE_PLANNER_ACCEL:
    suppressors |= BrickpilotLongitudinalSuppressor.PLANNER_NOT_POSITIVE
  if not bool(getattr(long_plan, "allowThrottle", True)):
    suppressors |= BrickpilotLongitudinalSuppressor.ALLOW_THROTTLE_FALSE
  if bool(getattr(long_plan, "shouldStop", False)):
    suppressors |= BrickpilotLongitudinalSuppressor.SHOULD_STOP
  model_hard_brake, radar_model_mismatch = _model_hard_brake_or_mismatch(model_v2, bool(getattr(getattr(radar_state, "leadOne", None), "status", False)))
  if bool(getattr(long_plan, "fcw", False)) or model_hard_brake:
    suppressors |= BrickpilotLongitudinalSuppressor.FCW_OR_MODEL_BRAKE
  if radar_model_mismatch:
    suppressors |= BrickpilotLongitudinalSuppressor.RADAR_MODEL_MISMATCH
  dec_or_scc_active, high_predicted_lateral = _sunnypilot_longitudinal_plan_risk(longitudinal_plan_sp)
  if dec_or_scc_active:
    suppressors |= BrickpilotLongitudinalSuppressor.DEC_OR_SCC_ACTIVE
  if high_predicted_lateral:
    suppressors |= BrickpilotLongitudinalSuppressor.HIGH_PREDICTED_LATERAL_DEMAND
  phev_regen_or_brake = enabled_for_vehicle and _phev_regen_or_brake_active(car_state_sp)
  phev_stationary_or_auto_hold = enabled_for_vehicle and _phev_stationary_or_auto_hold_active(car_state_sp)
  if phev_regen_or_brake:
    suppressors |= BrickpilotLongitudinalSuppressor.PHEV_REGEN_OR_BRAKE
  if phev_stationary_or_auto_hold:
    suppressors |= BrickpilotLongitudinalSuppressor.PHEV_STATIONARY_OR_AUTO_HOLD

  source_name = _safe_enum_name(getattr(long_plan, "longitudinalPlanSource", "cruise"))
  source_is_cruise = source_name in CRUISE_SOURCE_NAMES
  experimental_source_bridge = bool(source_name in EXPERIMENTAL_SOURCE_NAMES and
                                    v_ego >= EXP_SOURCE_MIN_SPEED and
                                    speed_deficit >= EXP_SOURCE_MIN_DEFICIT and
                                    trajectory_deficit >= EXP_SOURCE_MIN_TRAJECTORY_DEFICIT and
                                    lateral_demand <= EXP_SOURCE_MAX_LATERAL_ACCEL)
  if not source_is_cruise and not experimental_source_bridge:
    suppressors |= BrickpilotLongitudinalSuppressor.NOT_CRUISE_SOURCE

  stopped_or_creeping = (bool(getattr(CS, "standstill", False)) or
                         bool(getattr(getattr(CS, "cruiseState", None), "standstill", False)) or
                         v_ego < MIN_ASSIST_SPEED)
  if stopped_or_creeping:
    suppressors |= BrickpilotLongitudinalSuppressor.STOP_CREEP_BAND
  if bool(getattr(CS, "gasPressed", False)) or bool(getattr(CS, "brakePressed", False)):
    suppressors |= BrickpilotLongitudinalSuppressor.DRIVER_OVERRIDE
  if bool(getattr(CS, "steeringPressed", False)):
    suppressors |= BrickpilotLongitudinalSuppressor.STEERING_OVERRIDE

  suppress_lead, lead_distance, lead_closing, radar_has_lead = _lead_present_or_limiting(long_plan, radar_state)
  if suppress_lead:
    suppressors |= BrickpilotLongitudinalSuppressor.LEAD_PRESENT_OR_LIMITING
  if lateral_demand > MAX_LATERAL_ACCEL_FOR_ASSIST:
    suppressors |= BrickpilotLongitudinalSuppressor.HIGH_LATERAL_DEMAND
  if speed_deficit < MIN_CATCHUP_SPEED_DEFICIT:
    suppressors |= BrickpilotLongitudinalSuppressor.NO_CATCHUP_DEMAND
  if accel_lag < MIN_ACCEL_LAG:
    suppressors |= BrickpilotLongitudinalSuppressor.ACCEL_LAG_TOO_SMALL

  clean_shadow_context = bool(enabled_for_vehicle and valid and getattr(CC, "longActive", False) and
                              longitudinal_plan_sp_valid and not getattr(long_plan, "shouldStop", False) and
                              not getattr(long_plan, "fcw", False) and not model_hard_brake and not radar_model_mismatch and
                              not dec_or_scc_active and not high_predicted_lateral and
                              not phev_regen_or_brake and not phev_stationary_or_auto_hold and
                              not getattr(CS, "gasPressed", False) and not getattr(CS, "brakePressed", False) and
                              not getattr(CS, "steeringPressed", False) and not suppress_lead and
                              (source_is_cruise or experimental_source_bridge) and
                              lateral_demand <= MAX_LATERAL_ACCEL_FOR_ASSIST and not stopped_or_creeping and
                              speed_deficit >= MIN_CATCHUP_SPEED_DEFICIT)
  planner_floor_shadow_candidate = bool(clean_shadow_context and speed_deficit >= PLANNER_FLOOR_SHADOW_DEFICIT and
                                        (a_target < MIN_POSITIVE_PLANNER_ACCEL or not getattr(long_plan, "allowThrottle", True)))
  planner_floor_live_candidate = bool(planner_floor_shadow_candidate and
                                      getattr(long_plan, "allowThrottle", True) and
                                      a_target >= PLANNER_FLOOR_LIVE_MIN_ATARGET and
                                      speed_deficit >= PLANNER_FLOOR_LIVE_DEFICIT)

  hard_suppressors = suppressors & ~SOFT_HOLD_SUPPRESSORS
  soft_suppressors = suppressors & SOFT_HOLD_SUPPRESSORS
  if planner_floor_live_candidate:
    soft_suppressors &= ~(BrickpilotLongitudinalSuppressor.PLANNER_NOT_POSITIVE |
                          BrickpilotLongitudinalSuppressor.ACCEL_LAG_TOO_SMALL)
  prev_hold_timer = max(0.0, _safe_float(getattr(prev_state, "hold_timer", 0.0))) if prev_state is not None else 0.0
  prev_hold_target = _safe_float(getattr(prev_state, "hold_target", 0.0), a_target) if prev_state is not None else a_target
  hold_dt = max(0.0, min(_safe_float(dt, 0.05), 0.20))
  hold_demand_context = bool(speed_deficit >= max(0.0, MIN_CATCHUP_SPEED_DEFICIT - HOLD_GAP_SPEED_DEFICIT_MARGIN) and
                             v_ego >= MIN_ASSIST_SPEED and (source_is_cruise or experimental_source_bridge))
  held_activation = bool(hard_suppressors == BrickpilotLongitudinalSuppressor.NONE and
                         soft_suppressors != BrickpilotLongitudinalSuppressor.NONE and
                         prev_hold_timer > 0.0 and hold_demand_context)

  if hard_suppressors != BrickpilotLongitudinalSuppressor.NONE or (soft_suppressors != BrickpilotLongitudinalSuppressor.NONE and not held_activation):
    next_hold_timer = max(0.0, prev_hold_timer - hold_dt) if hard_suppressors == BrickpilotLongitudinalSuppressor.NONE else 0.0
    return BrickpilotLongitudinalAssistState(enabled_for_vehicle=enabled_for_vehicle,
                                             shadow_candidate=clean_shadow_context,
                                             planner_floor_shadow_candidate=planner_floor_shadow_candidate,
                                             suppressors=suppressors, a_target=a_target,
                                             assisted_a_target=a_target, hold_timer=next_hold_timer,
                                             hold_target=prev_hold_target if next_hold_timer > 0.0 else 0.0,
                                             speed_deficit=speed_deficit,
                                             accel_lag=accel_lag, lateral_demand=lateral_demand,
                                             lead_distance=lead_distance, lead_closing=lead_closing)

  high_confidence_ramp = bool(source_is_cruise and
                              v_ego >= HIGH_CONF_RAMP_MIN_SPEED and
                              speed_deficit >= HIGH_CONF_RAMP_MIN_DEFICIT and
                              trajectory_deficit >= HIGH_CONF_RAMP_MIN_TRAJECTORY_DEFICIT and
                              lateral_demand <= HIGH_CONF_RAMP_MAX_LATERAL_ACCEL and
                              not held_activation)
  ramp_catchup = bool(v_ego >= RAMP_CATCHUP_MIN_SPEED and speed_deficit >= RAMP_CATCHUP_MIN_DEFICIT and
                      lateral_demand <= CURVE_SOFT_DECAY_LATERAL_ACCEL and not held_activation)
  assist_delta_cap = RAMP_CATCHUP_MAX_ASSIST_DELTA if ramp_catchup else MAX_ASSIST_DELTA
  if high_confidence_ramp:
    assist_delta_cap = HIGH_CONF_RAMP_MAX_ASSIST_DELTA
  if experimental_source_bridge:
    assist_delta_cap = min(assist_delta_cap, EXP_SOURCE_MAX_ASSIST_DELTA)
  deficit_mph_over = max(0.0, (speed_deficit - MIN_CATCHUP_SPEED_DEFICIT) / CV.MPH_TO_MS)
  floor_target = max(a_target, PLANNER_FLOOR_LIVE_ACCEL) if planner_floor_live_candidate else a_target
  effective_accel_lag = max(accel_lag, floor_target - a_ego)
  lag_over = max(0.0, effective_accel_lag - MIN_ACCEL_LAG)
  assist_delta = min(assist_delta_cap,
                     max(MIN_ASSIST_DELTA,
                         DEFICIT_ASSIST_COEFF_PER_MPH * deficit_mph_over +
                         LAG_ASSIST_COEFF * min(lag_over, 1.0) +
                         (HIGH_CONF_RAMP_ASSIST_BONUS if high_confidence_ramp else
                          RAMP_CATCHUP_ASSIST_BONUS if ramp_catchup else 0.0)))
  if lateral_demand > CURVE_SOFT_DECAY_LATERAL_ACCEL:
    assist_delta *= CURVE_SOFT_DELTA_DECAY
  accel_max = min(_safe_float(accel_limits[1], CarControllerParams.ACCEL_MAX), MAX_ASSISTED_A_TARGET)
  # Do not clip upward to accel_limits[0] here. LongControl will still enforce
  # PID output limits, but the assisted target itself must never exceed the
  # explicit Brickpilot delta cap relative to the planner target.
  base_target = a_target + assist_delta
  if planner_floor_live_candidate:
    base_target = max(base_target, floor_target)
  if held_activation:
    base_target = a_target + max(0.0, prev_hold_target - a_target) * BRICKPILOT_HOLD_DECAY

  assisted_a_target = a_target if accel_max <= a_target else min(base_target, a_target + assist_delta_cap, accel_max)
  assist_delta = max(0.0, assisted_a_target - a_target)
  next_hold_timer = BRICKPILOT_HOLD_SECONDS if assist_delta > 0.0 and not held_activation else max(0.0, prev_hold_timer - hold_dt)
  next_hold_target = assisted_a_target if next_hold_timer > 0.0 else 0.0

  return BrickpilotLongitudinalAssistState(enabled_for_vehicle=enabled_for_vehicle,
                                           active=assist_delta > 0.0,
                                           shadow_candidate=True,
                                           planner_floor_shadow_candidate=planner_floor_shadow_candidate,
                                           suppressors=suppressors, a_target=a_target,
                                           assisted_a_target=assisted_a_target,
                                           assist_delta=assist_delta,
                                           hold_timer=next_hold_timer,
                                           hold_target=next_hold_target,
                                           held_activation=held_activation,
                                           speed_deficit=speed_deficit,
                                           accel_lag=accel_lag,
                                           lateral_demand=lateral_demand,
                                           lead_distance=lead_distance,
                                           lead_closing=lead_closing)
