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


STOP_SOURCE_NONE = 0
STOP_SOURCE_LEAD = 1
STOP_SOURCE_MODEL = 2
STOP_SOURCE_SHOULD_STOP = 3
STOP_SOURCE_CREEP = 4

STOP_PROFILE_STOCKISH_SHADOW = 0
STOP_PROFILE_TUCSON_PHEV_STABLE = 1
STOP_PROFILE_TUCSON_PHEV_TRAFFIC_SHADOW = 2

STOP_MODE_NONE = 0
STOP_MODE_ROLLING_FOLLOW = 1
STOP_MODE_FINAL_STOP_COMMIT = 2
STOP_MODE_URGENT_BRAKE_RECOVERY = 3
STOP_MODE_CREEP_HOLD = 4

LEAD_PACING_MODE_NONE = 0
LEAD_PACING_MODE_SHADOW = 1
LEAD_PACING_MODE_ACCEL = 2
LEAD_PACING_MODE_DECEL = 3
LEAD_PACING_MODE_COAST = 4

FINAL_STOP_BLOCK_NONE = 0
FINAL_STOP_BLOCK_NO_FINAL_SOURCE = 1
FINAL_STOP_BLOCK_GEOMETRY_INVALID = 2
FINAL_STOP_BLOCK_PLANNER_NOT_BRAKING = 3
FINAL_STOP_BLOCK_SOURCE_NOT_PERSISTENT = 4
FINAL_STOP_BLOCK_ROLLING_LEAD = 5
FINAL_STOP_BLOCK_GAP_NOT_URGENT = 6
FINAL_STOP_BLOCK_STANDSTILL = 7
FINAL_STOP_BLOCK_SPEED_RANGE = 8

STOP_INVALID_NONE = 0
STOP_INVALID_NO_SOURCE = 1
STOP_INVALID_NO_LEAD_GEOMETRY = 2
STOP_INVALID_FAR_NONCLOSING_LEAD = 3
STOP_INVALID_SPEED_RANGE = 4

STOP_DEBT_BUCKET_NONE = 0
STOP_DEBT_BUCKET_INVALID_GEOMETRY = 1
STOP_DEBT_BUCKET_LEAD_CLOSE_CLOSING = 2
STOP_DEBT_BUCKET_PLANNER_LATE = 3
STOP_DEBT_BUCKET_CONTROLLER_UNDERBRAKE = 4
STOP_DEBT_BUCKET_CREEP_HOLD = 5
STOP_DEBT_BUCKET_REGEN_LIGHT_CONTEXT = 6
STOP_DEBT_BUCKET_DRIVER_OVERRIDE = 7
STOP_DEBT_BUCKET_STATIONARY_HOLD = 8

STOP_ASSIST_REASON_NONE = 0
STOP_ASSIST_REASON_BRAKE_DEBT = 1
STOP_ASSIST_REASON_PLANNER_DEBT = 2
STOP_ASSIST_REASON_CONTROLLER_UNDERBRAKE = 3
STOP_ASSIST_REASON_FINAL_STOP_COMMIT = 4
STOP_ASSIST_REASON_REGEN_LIGHT_NOT_ENOUGH = 5

PHEV_BRAKE_STATE_NONE = 0
PHEV_BRAKE_STATE_REGEN_LIGHT_COAST = 1
PHEV_BRAKE_STATE_REGEN_BRAKE_BLEND = 2
PHEV_BRAKE_STATE_FRICTION_BRAKE_CANDIDATE = 3
PHEV_BRAKE_STATE_STATIONARY_HOLD = 4


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
  stop_active: bool = False
  stop_shadow_candidate: bool = False
  stop_source: int = STOP_SOURCE_NONE
  stop_brake_state: int = PHEV_BRAKE_STATE_NONE
  stop_required_decel: float = 0.0
  stop_planner_debt: float = 0.0
  stop_controller_debt: float = 0.0
  stop_brake_debt: float = 0.0
  stop_ttc: float = 0.0
  stop_assist_delta: float = 0.0
  stop_distance_buffer: float = 0.0
  stop_source_valid: bool = False
  stop_required_decel_valid: bool = False
  stop_ttc_valid: bool = False
  stop_lead_distance: float = 0.0
  stop_lead_v_rel: float = 0.0
  stop_requested_decel: float = 0.0
  stop_actual_decel: float = 0.0
  stop_debt_bucket: int = STOP_DEBT_BUCKET_NONE
  stop_geometry_invalid_reason: int = STOP_INVALID_NONE
  stop_profile: int = STOP_PROFILE_TUCSON_PHEV_STABLE
  stop_assist_reason: int = STOP_ASSIST_REASON_NONE
  stop_source_persist_sec: float = 0.0
  stop_mode: int = STOP_MODE_NONE
  lead_abs_speed: float = 0.0
  lead_near_stopped_persist_sec: float = 0.0
  rolling_lead_confidence: float = 0.0
  final_stop_allowed: bool = False
  final_stop_blocked_reason: int = FINAL_STOP_BLOCK_NONE
  lead_pacing_mode: int = LEAD_PACING_MODE_NONE
  lead_pacing_target_gap: float = 0.0
  lead_pacing_gap_error: float = 0.0
  lead_pacing_v_rel: float = 0.0
  lead_pacing_assist_delta: float = 0.0
  lead_pacing_jerk_limited: bool = False


# Brickpilot 0.5.7 keeps the 0.5.6 final-stop arbitration and adds a separate
# native-SCC mimic path for lead pacing. Lead pacing is small, signed, and
# rate-limited so it can reduce "distance 4" feel without becoming broad brake
# authority or no-lead stop logic.
BRICKPILOT_LONGITUDINAL_VERSION = "0.5.7"
BRICKPILOT_LONGITUDINAL_VERSION_CODE = 50700
ULTIMATE_100K_CANDIDATE_ID = "tucson_phev_057_native_lead_pacing"
ULTIMATE_100K_CANDIDATE_HASH = 777057000
PHEV_CAN_REGEN_LOGGER_MIN_VERSION = 33000
PHEV_CAN_STATIONARY_LOGGER_MIN_VERSION = 40000
PHEV_FA_B4_REGEN_U8_THRESHOLD = 160
PHEV_BRAKE_065_B9_U8_THRESHOLD = 128
PHEV_BA_B14_AUTO_HOLD_VALUE = 1
PHEV_STATIONARY_HOLD_MAX_SPEED = 0.5 * CV.MPH_TO_MS
PHEV_FA_B4_LIGHT_REGEN_MIN_U8 = 16
PHEV_FA_B7_LIGHT_REGEN_MIN_U8 = 1
PHEV_BRAKE_065_B3_FRICTION_MIN_U8 = 20
PHEV_BRAKE_065_B14_FRICTION_MIN_U8 = 64
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
STOP_ASSIST_MAX_SPEED = 25.0 * CV.MPH_TO_MS
STOP_ASSIST_MIN_SPEED = 0.6 * CV.MPH_TO_MS
STOP_ASSIST_MAX_LATERAL_ACCEL = 0.75
STOP_ASSIST_MIN_REQUIRED_DECEL = 0.35
STOP_ASSIST_MIN_BRAKE_DEBT = 0.15
STOP_ASSIST_MAX_EXTRA_DECEL = 0.68
STOP_ASSIST_CONTROLLER_DEBT_MIN = 0.35
STOP_ASSIST_CONTROLLER_RECOVERY_MIN_EXTRA_DECEL = 0.26
STOP_ASSIST_CONTROLLER_RECOVERY_GAIN = 0.55
STOP_ASSIST_CONTROLLER_RECOVERY_MAX_EXTRA_DECEL = 0.98
STOP_ASSIST_FINAL_COMMIT_MAX_EXTRA_DECEL = 1.26
STOP_ASSIST_FINAL_COMMIT_MAX_SPEED = 8.0 * CV.MPH_TO_MS
STOP_ASSIST_FINAL_COMMIT_SOURCE_PERSIST_SEC = 0.35
STOP_ASSIST_FINAL_COMMIT_NEAR_STOPPED_PERSIST_SEC = 0.60
STOP_ASSIST_FINAL_COMMIT_TARGET_DECEL = 1.22
STOP_ASSIST_FINAL_COMMIT_GAP_MARGIN = 2.00
STOP_ASSIST_MAX_TARGET_DECEL = 1.85
STOP_ASSIST_CRAWL_MAX_SPEED = 5.0 * CV.MPH_TO_MS
STOP_ASSIST_CRAWL_TARGET_DECEL = 0.72
STOP_ASSIST_LEAD_NEAR_STOPPED_SPEED = 0.8 * CV.MPH_TO_MS
STOP_ASSIST_ROLLING_LEAD_MIN_SPEED = 1.2 * CV.MPH_TO_MS
STOP_ASSIST_ROLLING_LEAD_MAX_SPEED = 10.0 * CV.MPH_TO_MS
STOP_ASSIST_ROLLING_EGO_MAX_SPEED = 12.0 * CV.MPH_TO_MS
STOP_ASSIST_ROLLING_BUFFER_RELAX_AMOUNT = 1.20
STOP_ASSIST_ROLLING_FOLLOW_MAX_EXTRA_DECEL = 0.38
STOP_ASSIST_URGENT_TTC = 3.2
STOP_ASSIST_URGENT_CLOSING_VREL = -1.20
STOP_ASSIST_LOW_SPEED_BUFFER = 6.25
STOP_ASSIST_MID_SPEED_BUFFER = 4.75
STOP_ASSIST_HIGH_SPEED_BUFFER = 3.25
STOP_ASSIST_BUFFER_RELAX_TTC = 5.5
STOP_ASSIST_BUFFER_RELAX_MAX_CLOSING_VREL = -1.0
STOP_ASSIST_BUFFER_RELAX_AMOUNT = 0.85
STOP_ASSIST_MIN_STOP_DISTANCE = 1.0
STOP_ASSIST_MAX_VALID_TTC = 10.0
STOP_ASSIST_MIN_VALID_CLOSING_VREL = -0.25
LEAD_PACING_MIN_SPEED = 3.0 * CV.MPH_TO_MS
LEAD_PACING_MAX_SPEED = 45.0 * CV.MPH_TO_MS
LEAD_PACING_TARGET_TIME_GAP = 1.05
LEAD_PACING_TARGET_MIN_GAP = 5.0
LEAD_PACING_TARGET_MAX_GAP = 24.0
LEAD_PACING_GAP_DEADBAND = 2.2
LEAD_PACING_VREL_DEADBAND = 0.25
LEAD_PACING_MAX_ACCEL_DELTA = 0.26
LEAD_PACING_MAX_DECEL_DELTA = 0.30
LEAD_PACING_GAP_GAIN = 0.030
LEAD_PACING_VREL_GAIN = 0.145
LEAD_PACING_JERK_LIMIT_UP = 0.75
LEAD_PACING_JERK_LIMIT_DOWN = 1.00
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
  brake_b3 = _safe_int(getattr(car_state_sp, "brickpilotBrake065B3U8", 0))
  brake_b9 = _safe_int(getattr(car_state_sp, "brickpilotBrake065B9U8", 0))
  brake_b14 = _safe_int(getattr(car_state_sp, "brickpilotBrake065B14U8", 0))
  return bool(max(fa_b4_values) >= PHEV_FA_B4_REGEN_U8_THRESHOLD or
              brake_b9 >= PHEV_BRAKE_065_B9_U8_THRESHOLD or
              brake_b3 >= PHEV_BRAKE_065_B3_FRICTION_MIN_U8 or
              brake_b14 >= PHEV_BRAKE_065_B14_FRICTION_MIN_U8)


def _phev_stationary_or_auto_hold_active(car_state_sp: Any | None, v_ego: float = 0.0,
                                         standstill: bool = False) -> bool:
  if not _phev_can_logger_has_phev_runtime(car_state_sp, PHEV_CAN_STATIONARY_LOGGER_MIN_VERSION):
    return False
  return bool((standstill or v_ego <= PHEV_STATIONARY_HOLD_MAX_SPEED) and
              _safe_int(getattr(car_state_sp, "brickpilotPhevBaB14U8", 0)) == PHEV_BA_B14_AUTO_HOLD_VALUE)


def _phev_brake_state(car_state_sp: Any | None, v_ego: float, standstill: bool = False) -> int:
  if not _phev_can_logger_has_phev_runtime(car_state_sp, PHEV_CAN_REGEN_LOGGER_MIN_VERSION):
    return PHEV_BRAKE_STATE_NONE
  if _phev_stationary_or_auto_hold_active(car_state_sp, v_ego, standstill):
    return PHEV_BRAKE_STATE_STATIONARY_HOLD

  fa_b4_values = (
    _safe_int(getattr(car_state_sp, "brickpilotPhevFaB4U8", 0)),
    _safe_int(getattr(car_state_sp, "brickpilotPhevFaB4U8Bus0", 0)),
    _safe_int(getattr(car_state_sp, "brickpilotPhevFaB4U8Bus130", 0)),
  )
  fa_b7_values = (
    _safe_int(getattr(car_state_sp, "brickpilotPhevFaB7U8", 0)),
    _safe_int(getattr(car_state_sp, "brickpilotPhevFaB7U8Bus0", 0)),
    _safe_int(getattr(car_state_sp, "brickpilotPhevFaB7U8Bus130", 0)),
  )
  brake_b3 = _safe_int(getattr(car_state_sp, "brickpilotBrake065B3U8", 0))
  brake_b9 = _safe_int(getattr(car_state_sp, "brickpilotBrake065B9U8", 0))
  brake_b10 = _safe_int(getattr(car_state_sp, "brickpilotBrake065B10U8", 0))
  brake_b14 = _safe_int(getattr(car_state_sp, "brickpilotBrake065B14U8", 0))

  if (brake_b9 >= PHEV_BRAKE_065_B9_U8_THRESHOLD or
      brake_b3 >= PHEV_BRAKE_065_B3_FRICTION_MIN_U8 or
      brake_b14 >= PHEV_BRAKE_065_B14_FRICTION_MIN_U8):
    return PHEV_BRAKE_STATE_FRICTION_BRAKE_CANDIDATE
  if max(fa_b4_values) >= PHEV_FA_B4_REGEN_U8_THRESHOLD or brake_b10 >= PHEV_BRAKE_065_B9_U8_THRESHOLD:
    return PHEV_BRAKE_STATE_REGEN_BRAKE_BLEND
  if max(fa_b4_values) >= PHEV_FA_B4_LIGHT_REGEN_MIN_U8 or max(fa_b7_values) >= PHEV_FA_B7_LIGHT_REGEN_MIN_U8:
    return PHEV_BRAKE_STATE_REGEN_LIGHT_COAST
  return PHEV_BRAKE_STATE_NONE


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
  # Lead presence still suppresses broad catch-up assist. 0.5.7 has a separate,
  # smaller lead-pacing path below so lead contexts can be handled explicitly.
  present_or_limiting = radar_lead or plan_has_lead or lead_source
  return present_or_limiting, d_rel if radar_lead else 0.0, bool(radar_lead and v_rel < -0.1), radar_lead


def _stop_distance_buffer(v_ego: float, lead_v_rel: float = 0.0, ttc: float = 0.0,
                          should_stop: bool = False, model_hard_brake: bool = False) -> float:
  if v_ego < 15.0 * CV.MPH_TO_MS:
    base_buffer = STOP_ASSIST_LOW_SPEED_BUFFER
  elif v_ego < 35.0 * CV.MPH_TO_MS:
    base_buffer = STOP_ASSIST_MID_SPEED_BUFFER
  else:
    base_buffer = STOP_ASSIST_HIGH_SPEED_BUFFER

  # 0.5.1 proved that the larger low-speed buffer helps missed/late stops, but
  # the first 0.5.1 route also produced some "too early but eventually good"
  # stops. Relax the buffer only for mild, high-TTC lead contexts that are not
  # already shouldStop/model-brake situations.
  if (not should_stop and not model_hard_brake and
      ttc > STOP_ASSIST_BUFFER_RELAX_TTC and
      lead_v_rel >= STOP_ASSIST_BUFFER_RELAX_MAX_CLOSING_VREL):
    return max(STOP_ASSIST_HIGH_SPEED_BUFFER, base_buffer - STOP_ASSIST_BUFFER_RELAX_AMOUNT)
  return base_buffer


def _lead_pacing_target_gap(v_ego: float, lead_abs_speed: float) -> float:
  reference_speed = max(0.0, min(max(v_ego, lead_abs_speed), LEAD_PACING_MAX_SPEED))
  return float(np.clip(LEAD_PACING_TARGET_MIN_GAP + LEAD_PACING_TARGET_TIME_GAP * reference_speed,
                       LEAD_PACING_TARGET_MIN_GAP,
                       LEAD_PACING_TARGET_MAX_GAP))


def _rate_limit_signed_delta(target: float, previous: float, dt: float) -> tuple[float, bool]:
  step_up = LEAD_PACING_JERK_LIMIT_UP * max(0.0, dt)
  step_down = LEAD_PACING_JERK_LIMIT_DOWN * max(0.0, dt)
  if target > previous + step_up:
    return previous + step_up, True
  if target < previous - step_down:
    return previous - step_down, True
  return target, False


def _required_lead_stop_decel(v_ego: float, lead_distance: float, distance_buffer: float) -> float:
  if v_ego <= 0.0 or lead_distance <= 0.0:
    return 0.0
  usable_distance = max(STOP_ASSIST_MIN_STOP_DISTANCE, lead_distance - distance_buffer)
  return -min(STOP_ASSIST_MAX_TARGET_DECEL, max(0.0, v_ego * v_ego / (2.0 * usable_distance)))


def _stop_source(long_plan: Any, radar_state: Any, model_hard_brake: bool) -> int:
  source_name = _safe_enum_name(getattr(long_plan, "longitudinalPlanSource", "cruise"))
  radar_lead = bool(getattr(getattr(radar_state, "leadOne", None), "status", False))
  if radar_lead or bool(getattr(long_plan, "hasLead", False)) or source_name in LEAD_SOURCE_NAMES:
    return STOP_SOURCE_LEAD
  if model_hard_brake:
    return STOP_SOURCE_MODEL
  if bool(getattr(long_plan, "shouldStop", False)):
    return STOP_SOURCE_SHOULD_STOP
  return STOP_SOURCE_NONE


def _same_persistent_stop_source(current_source: int, prev_source: int) -> bool:
  if current_source == STOP_SOURCE_NONE or prev_source == STOP_SOURCE_NONE:
    return False
  if current_source == prev_source:
    return True
  final_stop_sources = {STOP_SOURCE_LEAD, STOP_SOURCE_MODEL, STOP_SOURCE_SHOULD_STOP, STOP_SOURCE_CREEP}
  return bool(current_source in final_stop_sources and prev_source in final_stop_sources)


def _safe_ttc(lead_distance: float, lead_v_rel: float) -> float:
  if lead_distance <= 0.0 or lead_v_rel >= -0.05:
    return 0.0
  return min(99.0, lead_distance / max(0.05, -lead_v_rel))


def _stop_debug_fields(stop_source: int, brake_state: int, required_decel: float, required_decel_valid: bool,
                       a_target: float, a_ego: float, ttc: float, ttc_valid: bool,
                       distance_buffer: float) -> dict[str, float | int | bool]:
  required_abs = abs(min(0.0, required_decel)) if required_decel_valid else 0.0
  target_abs = abs(min(0.0, a_target))
  actual_abs = abs(min(0.0, a_ego))
  return {
    "source": int(stop_source),
    "brake_state": int(brake_state),
    "required_decel": float(required_decel),
    "required_decel_valid": bool(required_decel_valid),
    "planner_debt": float(max(0.0, required_abs - target_abs)),
    "controller_debt": float(max(0.0, target_abs - actual_abs)),
    "brake_debt": float(max(0.0, required_abs - actual_abs)),
    "ttc": float(ttc),
    "ttc_valid": bool(ttc_valid),
    "distance_buffer": float(distance_buffer),
    "requested_decel": float(min(0.0, a_target)),
    "actual_decel": float(min(0.0, a_ego)),
  }


def _lead_stop_geometry(lead_distance: float, lead_v_rel: float, a_target: float, should_stop: bool,
                        model_hard_brake: bool, ttc: float) -> tuple[bool, bool, int]:
  if lead_distance <= 0.0:
    return False, False, STOP_INVALID_NO_LEAD_GEOMETRY

  closing = lead_v_rel <= STOP_ASSIST_MIN_VALID_CLOSING_VREL
  ttc_valid = bool(ttc > 0.0 and ttc <= STOP_ASSIST_MAX_VALID_TTC)
  planner_already_braking = a_target < -0.05
  valid = bool(should_stop or model_hard_brake or planner_already_braking or closing or ttc_valid)
  if not valid:
    return False, False, STOP_INVALID_FAR_NONCLOSING_LEAD
  return True, ttc_valid, STOP_INVALID_NONE


def _stop_debt_bucket(stop_source: int, required_valid: bool, invalid_reason: int, brake_state: int,
                      planner_debt: float, controller_debt: float, stop_debt: float,
                      driver_override: bool, stationary_hold: bool) -> int:
  if driver_override:
    return STOP_DEBT_BUCKET_DRIVER_OVERRIDE
  if stationary_hold:
    return STOP_DEBT_BUCKET_STATIONARY_HOLD
  if stop_source == STOP_SOURCE_NONE:
    return STOP_DEBT_BUCKET_NONE
  if not required_valid:
    return STOP_DEBT_BUCKET_INVALID_GEOMETRY if invalid_reason != STOP_INVALID_NONE else STOP_DEBT_BUCKET_NONE
  if stop_source == STOP_SOURCE_CREEP:
    return STOP_DEBT_BUCKET_CREEP_HOLD
  if controller_debt >= STOP_ASSIST_CONTROLLER_DEBT_MIN:
    return STOP_DEBT_BUCKET_CONTROLLER_UNDERBRAKE
  if planner_debt >= STOP_ASSIST_MIN_BRAKE_DEBT:
    return STOP_DEBT_BUCKET_PLANNER_LATE
  if brake_state == PHEV_BRAKE_STATE_REGEN_LIGHT_COAST and stop_debt >= STOP_ASSIST_MIN_BRAKE_DEBT:
    return STOP_DEBT_BUCKET_REGEN_LIGHT_CONTEXT
  if stop_source == STOP_SOURCE_LEAD:
    return STOP_DEBT_BUCKET_LEAD_CLOSE_CLOSING
  return STOP_DEBT_BUCKET_NONE


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
  cs_standstill = bool(getattr(CS, "standstill", False))
  cruise_standstill = bool(getattr(getattr(CS, "cruiseState", None), "standstill", False))
  phev_brake_state = _phev_brake_state(car_state_sp, v_ego, cs_standstill or cruise_standstill) if enabled_for_vehicle else PHEV_BRAKE_STATE_NONE
  phev_regen_or_brake = enabled_for_vehicle and _phev_regen_or_brake_active(car_state_sp)
  phev_stationary_or_auto_hold = enabled_for_vehicle and _phev_stationary_or_auto_hold_active(
    car_state_sp, v_ego, cs_standstill or cruise_standstill)
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

  stopped_or_creeping = (cs_standstill or cruise_standstill or v_ego < MIN_ASSIST_SPEED)
  if stopped_or_creeping:
    suppressors |= BrickpilotLongitudinalSuppressor.STOP_CREEP_BAND
  if bool(getattr(CS, "gasPressed", False)) or bool(getattr(CS, "brakePressed", False)):
    suppressors |= BrickpilotLongitudinalSuppressor.DRIVER_OVERRIDE
  if bool(getattr(CS, "steeringPressed", False)):
    suppressors |= BrickpilotLongitudinalSuppressor.STEERING_OVERRIDE

  suppress_lead, lead_distance, lead_closing, radar_has_lead = _lead_present_or_limiting(long_plan, radar_state)
  lead = getattr(radar_state, "leadOne", None)
  lead_v_rel = _safe_float(getattr(lead, "vRel", 0.0)) if lead is not None else 0.0
  if suppress_lead:
    suppressors |= BrickpilotLongitudinalSuppressor.LEAD_PRESENT_OR_LIMITING
  if lateral_demand > MAX_LATERAL_ACCEL_FOR_ASSIST:
    suppressors |= BrickpilotLongitudinalSuppressor.HIGH_LATERAL_DEMAND
  if speed_deficit < MIN_CATCHUP_SPEED_DEFICIT:
    suppressors |= BrickpilotLongitudinalSuppressor.NO_CATCHUP_DEMAND
  if accel_lag < MIN_ACCEL_LAG:
    suppressors |= BrickpilotLongitudinalSuppressor.ACCEL_LAG_TOO_SMALL

  hold_dt = max(0.0, min(_safe_float(dt, 0.05), 0.20))
  source_for_stop = _stop_source(long_plan, radar_state, model_hard_brake)
  if source_for_stop == STOP_SOURCE_LEAD and bool(getattr(long_plan, "shouldStop", False)) and v_ego <= STOP_ASSIST_CRAWL_MAX_SPEED:
    source_for_stop = STOP_SOURCE_CREEP
  ttc = _safe_ttc(lead_distance, lead_v_rel)
  lead_abs_speed = max(0.0, v_ego + lead_v_rel) if radar_has_lead and lead_distance > 0.0 else 0.0
  lead_near_stopped_now = bool(radar_has_lead and lead_abs_speed <= STOP_ASSIST_LEAD_NEAR_STOPPED_SPEED)
  prev_lead_near_stopped_persist_sec = max(
    0.0, _safe_float(getattr(prev_state, "lead_near_stopped_persist_sec", 0.0))
  ) if prev_state is not None else 0.0
  lead_near_stopped_persist_sec = min(5.0, prev_lead_near_stopped_persist_sec + hold_dt) if lead_near_stopped_now else 0.0
  lead_rolling_slow = bool(radar_has_lead and
                           v_ego <= STOP_ASSIST_ROLLING_EGO_MAX_SPEED and
                           lead_abs_speed >= STOP_ASSIST_ROLLING_LEAD_MIN_SPEED and
                           lead_abs_speed <= STOP_ASSIST_ROLLING_LEAD_MAX_SPEED)
  ttc_urgent = bool(ttc > 0.0 and ttc <= STOP_ASSIST_URGENT_TTC)
  lead_closing_urgent = bool(lead_v_rel <= STOP_ASSIST_URGENT_CLOSING_VREL)
  stop_distance_buffer = _stop_distance_buffer(v_ego, lead_v_rel, ttc,
                                               bool(getattr(long_plan, "shouldStop", False)),
                                               model_hard_brake)
  rolling_distance_buffer = max(STOP_ASSIST_HIGH_SPEED_BUFFER,
                                stop_distance_buffer - STOP_ASSIST_ROLLING_BUFFER_RELAX_AMOUNT)
  provisional_gap_urgent = bool(lead_distance > 0.0 and
                                lead_distance <= stop_distance_buffer + STOP_ASSIST_FINAL_COMMIT_GAP_MARGIN)
  rolling_gap_urgent = bool(lead_distance > 0.0 and lead_distance <= rolling_distance_buffer)
  rolling_lead_confidence = 0.0
  if lead_rolling_slow:
    rolling_lead_confidence = 1.0
    if ttc_urgent or lead_closing_urgent or provisional_gap_urgent:
      rolling_lead_confidence = 0.45
  rolling_lead_not_urgent = bool(lead_rolling_slow and
                                 not lead_near_stopped_now and
                                 not ttc_urgent and
                                 not lead_closing_urgent and
                                 not rolling_gap_urgent and
                                 not model_hard_brake)
  if rolling_lead_not_urgent:
    stop_distance_buffer = rolling_distance_buffer
  required_lead_decel = _required_lead_stop_decel(v_ego, lead_distance, stop_distance_buffer)
  stop_source_valid = source_for_stop != STOP_SOURCE_NONE
  stop_speed_valid = bool(v_ego >= STOP_ASSIST_MIN_SPEED and v_ego <= STOP_ASSIST_MAX_SPEED)
  stop_geometry_invalid_reason = STOP_INVALID_NONE if stop_source_valid else STOP_INVALID_NO_SOURCE
  lead_required_valid = False
  ttc_valid = False
  if source_for_stop in (STOP_SOURCE_LEAD, STOP_SOURCE_CREEP):
    lead_required_valid, ttc_valid, stop_geometry_invalid_reason = _lead_stop_geometry(
      lead_distance, lead_v_rel, a_target, bool(getattr(long_plan, "shouldStop", False)), model_hard_brake, ttc)

  required_decel_valid = bool(stop_source_valid and stop_speed_valid)
  required_decel = 0.0
  if source_for_stop == STOP_SOURCE_LEAD:
    required_decel_valid = bool(required_decel_valid and lead_required_valid)
    required_decel = required_lead_decel if required_decel_valid else 0.0
  if source_for_stop in (STOP_SOURCE_MODEL, STOP_SOURCE_SHOULD_STOP, STOP_SOURCE_CREEP):
    if source_for_stop == STOP_SOURCE_CREEP:
      required_decel_valid = bool(required_decel_valid and (lead_required_valid or bool(getattr(long_plan, "shouldStop", False))))
    required_decel = min(required_decel if required_decel < 0.0 else 0.0,
                         a_target if a_target < 0.0 else 0.0,
                         -STOP_ASSIST_MIN_REQUIRED_DECEL)
  if source_for_stop == STOP_SOURCE_CREEP:
    required_decel = min(required_decel, -STOP_ASSIST_CRAWL_TARGET_DECEL)
  if not stop_speed_valid and stop_source_valid:
    stop_geometry_invalid_reason = STOP_INVALID_SPEED_RANGE
  if required_decel_valid:
    stop_geometry_invalid_reason = STOP_INVALID_NONE
  prev_stop_source = _safe_int(getattr(prev_state, "stop_source", STOP_SOURCE_NONE)) if prev_state is not None else STOP_SOURCE_NONE
  prev_required_valid = bool(getattr(prev_state, "stop_required_decel_valid", False)) if prev_state is not None else False
  prev_source_persist_sec = max(0.0, _safe_float(getattr(prev_state, "stop_source_persist_sec", 0.0))) if prev_state is not None else 0.0
  same_valid_stop_source = bool(source_for_stop != STOP_SOURCE_NONE and required_decel_valid and
                                prev_required_valid and
                                _same_persistent_stop_source(source_for_stop, prev_stop_source))
  if same_valid_stop_source:
    stop_source_persist_sec = min(5.0, prev_source_persist_sec + hold_dt)
  elif source_for_stop != STOP_SOURCE_NONE and required_decel_valid:
    stop_source_persist_sec = hold_dt
  else:
    stop_source_persist_sec = 0.0
  stop_debug = _stop_debug_fields(source_for_stop, phev_brake_state, required_decel, required_decel_valid,
                                  a_target, a_ego, ttc, ttc_valid, stop_distance_buffer)
  stop_shadow_candidate = bool(enabled_for_vehicle and getattr(CC, "longActive", False) and valid and
                               source_for_stop != STOP_SOURCE_NONE and
                               v_ego >= STOP_ASSIST_MIN_SPEED and v_ego <= STOP_ASSIST_MAX_SPEED)
  stop_hard_blocked = bool(lateral_demand > STOP_ASSIST_MAX_LATERAL_ACCEL or
                           (suppressors & (BrickpilotLongitudinalSuppressor.NOT_TUCSON_CANFD |
                                           BrickpilotLongitudinalSuppressor.INVALID |
                                           BrickpilotLongitudinalSuppressor.LONG_INACTIVE |
                                           BrickpilotLongitudinalSuppressor.OPENPILOT_LONG_REQUIRED |
                                           BrickpilotLongitudinalSuppressor.DRIVER_OVERRIDE |
                                           BrickpilotLongitudinalSuppressor.STEERING_OVERRIDE |
                                           BrickpilotLongitudinalSuppressor.HIGH_LATERAL_DEMAND |
                                           BrickpilotLongitudinalSuppressor.HIGH_PREDICTED_LATERAL_DEMAND |
                                           BrickpilotLongitudinalSuppressor.RADAR_MODEL_MISMATCH |
                                           BrickpilotLongitudinalSuppressor.DEC_OR_SCC_ACTIVE)) != BrickpilotLongitudinalSuppressor.NONE)
  stop_debt = float(stop_debug["brake_debt"])
  planner_debt = float(stop_debug["planner_debt"])
  controller_debt = float(stop_debug["controller_debt"])
  regen_light_not_enough = bool(phev_brake_state == PHEV_BRAKE_STATE_REGEN_LIGHT_COAST and stop_debt >= STOP_ASSIST_MIN_BRAKE_DEBT)
  driver_override = bool(getattr(CS, "gasPressed", False)) or bool(getattr(CS, "brakePressed", False))
  stop_debt_bucket = _stop_debt_bucket(source_for_stop, required_decel_valid, stop_geometry_invalid_reason,
                                       phev_brake_state, planner_debt, controller_debt, stop_debt,
                                       driver_override, phev_stationary_or_auto_hold)
  controller_underbrake_recovery = bool(controller_debt >= STOP_ASSIST_CONTROLLER_DEBT_MIN and
                                        stop_debt_bucket == STOP_DEBT_BUCKET_CONTROLLER_UNDERBRAKE)
  source_is_lead_backed = source_for_stop in (STOP_SOURCE_LEAD, STOP_SOURCE_CREEP)
  previous_lead_backed_stop = bool(prev_required_valid and prev_stop_source in (STOP_SOURCE_LEAD, STOP_SOURCE_CREEP))
  inherited_lead_backed_stop = bool(source_for_stop in (STOP_SOURCE_MODEL, STOP_SOURCE_SHOULD_STOP) and
                                    previous_lead_backed_stop and
                                    v_ego <= STOP_ASSIST_FINAL_COMMIT_MAX_SPEED)
  close_gap_urgent = bool(lead_distance > 0.0 and
                          lead_distance <= stop_distance_buffer + STOP_ASSIST_FINAL_COMMIT_GAP_MARGIN)
  final_stop_urgency = bool(ttc_urgent or lead_closing_urgent or close_gap_urgent or model_hard_brake)
  lead_stop_live_urgent = bool(source_for_stop == STOP_SOURCE_LEAD and
                               (final_stop_urgency or
                                bool(getattr(long_plan, "shouldStop", False)) or
                                lead_near_stopped_persist_sec >= STOP_ASSIST_FINAL_COMMIT_NEAR_STOPPED_PERSIST_SEC))
  creep_stop_live_urgent = bool(source_for_stop == STOP_SOURCE_CREEP and
                                (final_stop_urgency or
                                 lead_near_stopped_persist_sec >= STOP_ASSIST_FINAL_COMMIT_NEAR_STOPPED_PERSIST_SEC or
                                 stop_source_persist_sec >= STOP_ASSIST_FINAL_COMMIT_SOURCE_PERSIST_SEC))
  inherited_model_stop_live_urgent = bool(inherited_lead_backed_stop and
                                          (model_hard_brake or
                                           bool(getattr(long_plan, "shouldStop", False)) or
                                           stop_source_persist_sec >= STOP_ASSIST_FINAL_COMMIT_SOURCE_PERSIST_SEC))
  stop_live_urgent = bool(lead_stop_live_urgent or creep_stop_live_urgent or inherited_model_stop_live_urgent)
  planner_already_braking = bool(a_target <= -0.05)
  final_stop_source = bool(source_is_lead_backed or inherited_lead_backed_stop)
  final_stop_lead_ready = bool(lead_near_stopped_persist_sec >= STOP_ASSIST_FINAL_COMMIT_NEAR_STOPPED_PERSIST_SEC)
  final_stop_gap_valid = bool(final_stop_urgency or final_stop_lead_ready)
  final_stop_blocked_reason = FINAL_STOP_BLOCK_NONE
  if not final_stop_source:
    final_stop_blocked_reason = FINAL_STOP_BLOCK_NO_FINAL_SOURCE
  elif not required_decel_valid:
    final_stop_blocked_reason = FINAL_STOP_BLOCK_GEOMETRY_INVALID
  elif not planner_already_braking:
    final_stop_blocked_reason = FINAL_STOP_BLOCK_PLANNER_NOT_BRAKING
  elif stop_source_persist_sec < STOP_ASSIST_FINAL_COMMIT_SOURCE_PERSIST_SEC:
    final_stop_blocked_reason = FINAL_STOP_BLOCK_SOURCE_NOT_PERSISTENT
  elif rolling_lead_not_urgent:
    final_stop_blocked_reason = FINAL_STOP_BLOCK_ROLLING_LEAD
  elif not final_stop_gap_valid:
    final_stop_blocked_reason = FINAL_STOP_BLOCK_GAP_NOT_URGENT
  elif cs_standstill:
    final_stop_blocked_reason = FINAL_STOP_BLOCK_STANDSTILL
  elif v_ego > STOP_ASSIST_FINAL_COMMIT_MAX_SPEED:
    final_stop_blocked_reason = FINAL_STOP_BLOCK_SPEED_RANGE
  final_stop_allowed = bool(final_stop_blocked_reason == FINAL_STOP_BLOCK_NONE)
  final_stop_commit = bool(v_ego <= STOP_ASSIST_FINAL_COMMIT_MAX_SPEED and final_stop_allowed)
  rolling_follow_candidate = bool(source_for_stop in (STOP_SOURCE_LEAD, STOP_SOURCE_CREEP) and
                                  required_decel_valid and
                                  rolling_lead_not_urgent and
                                  v_ego <= STOP_ASSIST_ROLLING_EGO_MAX_SPEED)
  rolling_follow_should_activate = bool(rolling_follow_candidate and
                                        not stop_hard_blocked and
                                        not phev_stationary_or_auto_hold and
                                        not final_stop_commit and
                                        (planner_debt >= STOP_ASSIST_MIN_BRAKE_DEBT or
                                         stop_debt >= STOP_ASSIST_MIN_BRAKE_DEBT or
                                         regen_light_not_enough))
  stop_should_activate = bool(stop_shadow_candidate and not stop_hard_blocked and not phev_stationary_or_auto_hold and
                              required_decel_valid and
                              ((stop_debt >= STOP_ASSIST_MIN_BRAKE_DEBT and stop_live_urgent) or
                               (planner_debt >= STOP_ASSIST_MIN_BRAKE_DEBT and stop_live_urgent) or
                               (controller_underbrake_recovery and stop_live_urgent) or
                               (regen_light_not_enough and stop_live_urgent) or
                               final_stop_commit or
                               rolling_follow_should_activate))
  stop_mode = STOP_MODE_NONE
  if final_stop_commit:
    stop_mode = STOP_MODE_FINAL_STOP_COMMIT
  elif controller_underbrake_recovery and stop_live_urgent:
    stop_mode = STOP_MODE_URGENT_BRAKE_RECOVERY
  elif rolling_follow_candidate:
    stop_mode = STOP_MODE_ROLLING_FOLLOW
  elif source_for_stop == STOP_SOURCE_CREEP and required_decel_valid:
    stop_mode = STOP_MODE_CREEP_HOLD
  stop_assist_reason = STOP_ASSIST_REASON_NONE
  if stop_should_activate:
    if final_stop_commit:
      stop_assist_reason = STOP_ASSIST_REASON_FINAL_STOP_COMMIT
    elif controller_underbrake_recovery:
      stop_assist_reason = STOP_ASSIST_REASON_CONTROLLER_UNDERBRAKE
    elif regen_light_not_enough and stop_live_urgent:
      stop_assist_reason = STOP_ASSIST_REASON_REGEN_LIGHT_NOT_ENOUGH
    elif planner_debt >= STOP_ASSIST_MIN_BRAKE_DEBT and (stop_live_urgent or rolling_follow_should_activate):
      stop_assist_reason = STOP_ASSIST_REASON_PLANNER_DEBT
    elif stop_debt >= STOP_ASSIST_MIN_BRAKE_DEBT and (stop_live_urgent or rolling_follow_should_activate):
      stop_assist_reason = STOP_ASSIST_REASON_BRAKE_DEBT
  stop_assist_target = a_target
  stop_assist_delta = 0.0
  if stop_should_activate:
    if final_stop_commit:
      max_extra_decel = STOP_ASSIST_FINAL_COMMIT_MAX_EXTRA_DECEL
    elif controller_underbrake_recovery:
      max_extra_decel = STOP_ASSIST_CONTROLLER_RECOVERY_MAX_EXTRA_DECEL
    elif rolling_follow_should_activate:
      max_extra_decel = STOP_ASSIST_ROLLING_FOLLOW_MAX_EXTRA_DECEL
    else:
      max_extra_decel = STOP_ASSIST_MAX_EXTRA_DECEL
    desired_stop_target = min(a_target, required_decel)
    if controller_underbrake_recovery:
      recovery_extra_decel = min(STOP_ASSIST_CONTROLLER_RECOVERY_MAX_EXTRA_DECEL,
                                 STOP_ASSIST_CONTROLLER_RECOVERY_MIN_EXTRA_DECEL +
                                 STOP_ASSIST_CONTROLLER_RECOVERY_GAIN *
                                 max(0.0, controller_debt - STOP_ASSIST_CONTROLLER_DEBT_MIN))
      desired_stop_target = min(desired_stop_target, a_target - recovery_extra_decel)
    if final_stop_commit:
      desired_stop_target = min(desired_stop_target, -STOP_ASSIST_FINAL_COMMIT_TARGET_DECEL)
    desired_stop_target = max(desired_stop_target, -STOP_ASSIST_MAX_TARGET_DECEL)
    stop_assist_target = max(desired_stop_target, a_target - max_extra_decel)
    stop_assist_target = max(stop_assist_target, _safe_float(accel_limits[0], -STOP_ASSIST_MAX_TARGET_DECEL))
    stop_assist_delta = min(0.0, stop_assist_target - a_target)
    stop_should_activate = bool(stop_assist_delta < -0.01)

  lead_pacing_target_gap = _lead_pacing_target_gap(v_ego, lead_abs_speed) if radar_has_lead and lead_distance > 0.0 else 0.0
  lead_pacing_gap_error = lead_distance - lead_pacing_target_gap if lead_pacing_target_gap > 0.0 else 0.0
  lead_pacing_shadow_candidate = bool(enabled_for_vehicle and getattr(CC, "longActive", False) and valid and
                                      longitudinal_plan_sp_valid and radar_has_lead and lead_distance > 0.0 and
                                      not cs_standstill and not cruise_standstill and
                                      v_ego >= LEAD_PACING_MIN_SPEED and v_ego <= LEAD_PACING_MAX_SPEED and
                                      lead_abs_speed > STOP_ASSIST_LEAD_NEAR_STOPPED_SPEED and
                                      not getattr(long_plan, "fcw", False) and not model_hard_brake and
                                      not radar_model_mismatch and not dec_or_scc_active and
                                      not high_predicted_lateral and not phev_regen_or_brake and
                                      not phev_stationary_or_auto_hold and
                                      not getattr(CS, "gasPressed", False) and not getattr(CS, "brakePressed", False) and
                                      not getattr(CS, "steeringPressed", False) and
                                      lateral_demand <= STOP_ASSIST_MAX_LATERAL_ACCEL)
  lead_pacing_mode = LEAD_PACING_MODE_NONE
  raw_lead_pacing_delta = 0.0
  if lead_pacing_shadow_candidate:
    lead_pacing_mode = LEAD_PACING_MODE_COAST
    too_far_gap = max(0.0, lead_pacing_gap_error - LEAD_PACING_GAP_DEADBAND)
    too_close_gap = max(0.0, -lead_pacing_gap_error - LEAD_PACING_GAP_DEADBAND)
    lead_pulling_away = max(0.0, lead_v_rel - LEAD_PACING_VREL_DEADBAND)
    lead_closing_mild = max(0.0, -lead_v_rel - LEAD_PACING_VREL_DEADBAND)
    if too_far_gap > 0.0 and lead_v_rel >= -LEAD_PACING_VREL_DEADBAND and a_target >= -0.05 and not stop_live_urgent:
      raw_lead_pacing_delta = min(LEAD_PACING_MAX_ACCEL_DELTA,
                                  LEAD_PACING_GAP_GAIN * too_far_gap +
                                  LEAD_PACING_VREL_GAIN * lead_pulling_away)
      lead_pacing_mode = LEAD_PACING_MODE_ACCEL if raw_lead_pacing_delta > 0.01 else LEAD_PACING_MODE_SHADOW
    elif (too_close_gap > 0.0 or lead_closing_mild > 0.0) and not stop_live_urgent:
      raw_lead_pacing_delta = -min(LEAD_PACING_MAX_DECEL_DELTA,
                                   LEAD_PACING_GAP_GAIN * too_close_gap +
                                   LEAD_PACING_VREL_GAIN * lead_closing_mild)
      lead_pacing_mode = LEAD_PACING_MODE_DECEL if raw_lead_pacing_delta < -0.01 else LEAD_PACING_MODE_SHADOW

  lead_pacing_allowed_suppressors = (BrickpilotLongitudinalSuppressor.LEAD_PRESENT_OR_LIMITING |
                                     BrickpilotLongitudinalSuppressor.STOP_CREEP_BAND |
                                     BrickpilotLongitudinalSuppressor.PLANNER_NOT_POSITIVE |
                                     BrickpilotLongitudinalSuppressor.NO_CATCHUP_DEMAND |
                                     BrickpilotLongitudinalSuppressor.ACCEL_LAG_TOO_SMALL)
  lead_pacing_hard_suppressors = suppressors & ~lead_pacing_allowed_suppressors
  prev_lead_pacing_delta = _safe_float(getattr(prev_state, "lead_pacing_assist_delta", 0.0)) if prev_state is not None else 0.0
  lead_pacing_delta, lead_pacing_jerk_limited = _rate_limit_signed_delta(raw_lead_pacing_delta, prev_lead_pacing_delta, hold_dt)
  lead_pacing_live = bool(lead_pacing_shadow_candidate and not stop_should_activate and
                          lead_pacing_hard_suppressors == BrickpilotLongitudinalSuppressor.NONE and
                          abs(lead_pacing_delta) > 0.01)

  stop_arbitration_fields = {
    "stop_mode": stop_mode,
    "lead_abs_speed": lead_abs_speed,
    "lead_near_stopped_persist_sec": lead_near_stopped_persist_sec,
    "rolling_lead_confidence": rolling_lead_confidence,
    "final_stop_allowed": final_stop_allowed,
    "final_stop_blocked_reason": final_stop_blocked_reason,
    "lead_pacing_mode": lead_pacing_mode,
    "lead_pacing_target_gap": lead_pacing_target_gap,
    "lead_pacing_gap_error": lead_pacing_gap_error,
    "lead_pacing_v_rel": lead_v_rel if radar_has_lead else 0.0,
    "lead_pacing_assist_delta": lead_pacing_delta if lead_pacing_live else 0.0,
    "lead_pacing_jerk_limited": bool(lead_pacing_live and lead_pacing_jerk_limited),
  }

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
  hold_demand_context = bool(speed_deficit >= max(0.0, MIN_CATCHUP_SPEED_DEFICIT - HOLD_GAP_SPEED_DEFICIT_MARGIN) and
                             v_ego >= MIN_ASSIST_SPEED and (source_is_cruise or experimental_source_bridge))
  held_activation = bool(hard_suppressors == BrickpilotLongitudinalSuppressor.NONE and
                         soft_suppressors != BrickpilotLongitudinalSuppressor.NONE and
                         prev_hold_timer > 0.0 and hold_demand_context)

  if stop_should_activate:
    return BrickpilotLongitudinalAssistState(enabled_for_vehicle=enabled_for_vehicle,
                                             active=True, shadow_candidate=bool(clean_shadow_context or stop_shadow_candidate),
                                             planner_floor_shadow_candidate=planner_floor_shadow_candidate,
                                             suppressors=suppressors, a_target=a_target,
                                             assisted_a_target=stop_assist_target, assist_delta=0.0,
                                             hold_timer=0.0, hold_target=0.0,
                                             speed_deficit=speed_deficit,
                                             accel_lag=accel_lag, lateral_demand=lateral_demand,
                                             lead_distance=lead_distance, lead_closing=lead_closing,
                                             stop_active=True, stop_shadow_candidate=stop_shadow_candidate,
                                             stop_source=source_for_stop, stop_brake_state=phev_brake_state,
                                             stop_required_decel=float(stop_debug["required_decel"]),
                                             stop_planner_debt=planner_debt,
                                             stop_controller_debt=controller_debt,
                                             stop_brake_debt=stop_debt,
                                             stop_ttc=ttc,
                                             stop_assist_delta=stop_assist_delta,
                                             stop_distance_buffer=stop_distance_buffer,
                                             stop_source_valid=stop_source_valid,
                                             stop_required_decel_valid=required_decel_valid,
                                             stop_ttc_valid=ttc_valid,
                                             stop_lead_distance=lead_distance,
                                             stop_lead_v_rel=lead_v_rel,
                                             stop_requested_decel=float(stop_debug["requested_decel"]),
                                             stop_actual_decel=float(stop_debug["actual_decel"]),
                                             stop_debt_bucket=stop_debt_bucket,
                                             stop_geometry_invalid_reason=stop_geometry_invalid_reason,
                                             stop_profile=STOP_PROFILE_TUCSON_PHEV_STABLE,
                                             stop_assist_reason=stop_assist_reason,
                                             stop_source_persist_sec=stop_source_persist_sec,
                                             **stop_arbitration_fields)

  if lead_pacing_live:
    lead_pacing_target = a_target + lead_pacing_delta
    lead_pacing_target = max(lead_pacing_target, _safe_float(accel_limits[0], -STOP_ASSIST_MAX_TARGET_DECEL))
    lead_pacing_target = min(lead_pacing_target,
                             _safe_float(accel_limits[1], CarControllerParams.ACCEL_MAX),
                             MAX_ASSISTED_A_TARGET)
    applied_lead_pacing_delta = lead_pacing_target - a_target
    stop_arbitration_fields["lead_pacing_assist_delta"] = applied_lead_pacing_delta
    return BrickpilotLongitudinalAssistState(enabled_for_vehicle=enabled_for_vehicle,
                                             active=True, shadow_candidate=True,
                                             planner_floor_shadow_candidate=planner_floor_shadow_candidate,
                                             suppressors=suppressors, a_target=a_target,
                                             assisted_a_target=lead_pacing_target,
                                             assist_delta=applied_lead_pacing_delta,
                                             hold_timer=0.0, hold_target=0.0,
                                             speed_deficit=speed_deficit,
                                             accel_lag=accel_lag, lateral_demand=lateral_demand,
                                             lead_distance=lead_distance, lead_closing=lead_closing,
                                             stop_shadow_candidate=stop_shadow_candidate,
                                             stop_source=source_for_stop, stop_brake_state=phev_brake_state,
                                             stop_required_decel=float(stop_debug["required_decel"]),
                                             stop_planner_debt=planner_debt,
                                             stop_controller_debt=controller_debt,
                                             stop_brake_debt=stop_debt,
                                             stop_ttc=ttc,
                                             stop_distance_buffer=stop_distance_buffer,
                                             stop_source_valid=stop_source_valid,
                                             stop_required_decel_valid=required_decel_valid,
                                             stop_ttc_valid=ttc_valid,
                                             stop_lead_distance=lead_distance,
                                             stop_lead_v_rel=lead_v_rel,
                                             stop_requested_decel=float(stop_debug["requested_decel"]),
                                             stop_actual_decel=float(stop_debug["actual_decel"]),
                                             stop_debt_bucket=stop_debt_bucket,
                                             stop_geometry_invalid_reason=stop_geometry_invalid_reason,
                                             stop_profile=STOP_PROFILE_TUCSON_PHEV_STABLE,
                                             stop_assist_reason=STOP_ASSIST_REASON_NONE,
                                             stop_source_persist_sec=stop_source_persist_sec,
                                             **stop_arbitration_fields)

  if hard_suppressors != BrickpilotLongitudinalSuppressor.NONE or (soft_suppressors != BrickpilotLongitudinalSuppressor.NONE and not held_activation):
    next_hold_timer = max(0.0, prev_hold_timer - hold_dt) if hard_suppressors == BrickpilotLongitudinalSuppressor.NONE else 0.0
    return BrickpilotLongitudinalAssistState(enabled_for_vehicle=enabled_for_vehicle,
                                             shadow_candidate=bool(clean_shadow_context or stop_shadow_candidate),
                                             planner_floor_shadow_candidate=planner_floor_shadow_candidate,
                                             suppressors=suppressors, a_target=a_target,
                                             assisted_a_target=a_target, hold_timer=next_hold_timer,
                                             hold_target=prev_hold_target if next_hold_timer > 0.0 else 0.0,
                                             speed_deficit=speed_deficit,
                                             accel_lag=accel_lag, lateral_demand=lateral_demand,
                                             lead_distance=lead_distance, lead_closing=lead_closing,
                                             stop_shadow_candidate=stop_shadow_candidate,
                                             stop_source=source_for_stop, stop_brake_state=phev_brake_state,
                                             stop_required_decel=float(stop_debug["required_decel"]),
                                             stop_planner_debt=planner_debt,
                                             stop_controller_debt=controller_debt,
                                             stop_brake_debt=stop_debt,
                                             stop_ttc=ttc,
                                             stop_distance_buffer=stop_distance_buffer,
                                             stop_source_valid=stop_source_valid,
                                             stop_required_decel_valid=required_decel_valid,
                                             stop_ttc_valid=ttc_valid,
                                             stop_lead_distance=lead_distance,
                                             stop_lead_v_rel=lead_v_rel,
                                             stop_requested_decel=float(stop_debug["requested_decel"]),
                                             stop_actual_decel=float(stop_debug["actual_decel"]),
                                             stop_debt_bucket=stop_debt_bucket,
                                             stop_geometry_invalid_reason=stop_geometry_invalid_reason,
                                             stop_profile=STOP_PROFILE_TUCSON_PHEV_STABLE,
                                             stop_assist_reason=STOP_ASSIST_REASON_NONE,
                                             stop_source_persist_sec=stop_source_persist_sec,
                                             **stop_arbitration_fields)

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
                                           lead_closing=lead_closing,
                                           stop_shadow_candidate=stop_shadow_candidate,
                                           stop_source=source_for_stop,
                                           stop_brake_state=phev_brake_state,
                                           stop_required_decel=float(stop_debug["required_decel"]),
                                           stop_planner_debt=planner_debt,
                                           stop_controller_debt=controller_debt,
                                           stop_brake_debt=stop_debt,
                                           stop_ttc=ttc,
                                           stop_distance_buffer=stop_distance_buffer,
                                           stop_source_valid=stop_source_valid,
                                           stop_required_decel_valid=required_decel_valid,
                                           stop_ttc_valid=ttc_valid,
                                           stop_lead_distance=lead_distance,
                                           stop_lead_v_rel=lead_v_rel,
                                           stop_requested_decel=float(stop_debug["requested_decel"]),
                                           stop_actual_decel=float(stop_debug["actual_decel"]),
                                           stop_debt_bucket=stop_debt_bucket,
                                           stop_geometry_invalid_reason=stop_geometry_invalid_reason,
                                           stop_profile=STOP_PROFILE_TUCSON_PHEV_STABLE,
                                           stop_assist_reason=STOP_ASSIST_REASON_NONE,
                                           stop_source_persist_sec=stop_source_persist_sec,
                                           **stop_arbitration_fields)
