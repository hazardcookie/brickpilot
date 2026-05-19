import math
import numpy as np
from collections import deque

from cereal import log
from opendbc.car.lateral import FRICTION_THRESHOLD, get_friction
from opendbc.car.hyundai.values import CAR, HyundaiFlags
from openpilot.common.constants import ACCELERATION_DUE_TO_GRAVITY
from openpilot.common.constants import CV
from openpilot.common.filter_simple import FirstOrderFilter
from openpilot.selfdrive.controls.lib.latcontrol import LatControl
from openpilot.common.pid import PIDController

from openpilot.sunnypilot.selfdrive.controls.lib.latcontrol_torque_ext import LatControlTorqueExt

# At higher speeds (25+mph) we can assume:
# Lateral acceleration achieved by a specific car correlates to
# torque applied to the steering rack. It does not correlate to
# wheel slip, or to speed.

# This controller applies torque to achieve desired lateral
# accelerations. To compensate for the low speed effects the
# proportional gain is increased at low speeds by the PID controller.
# Additionally, there is friction in the steering wheel that needs
# to be overcome to move it at all, this is compensated for too.

KP = 0.8
KI = 0.15

INTERP_SPEEDS = [1, 1.5, 2.0, 3.0, 5, 7.5, 10, 15, 30]
KP_INTERP = [250, 120, 65, 30, 11.5, 5.5, 3.5, 2.0, KP]

LP_FILTER_CUTOFF_HZ = 1.2
JERK_LOOKAHEAD_SECONDS = 0.19
JERK_GAIN = 0.3
TUCSON_CANFD_FRICTION_SHAPING_SPEED = 62.0 * CV.MPH_TO_MS
TUCSON_CANFD_FRICTION_RETURN_ACCEL = 0.75
TUCSON_CANFD_FRICTION_NEAR_ZERO_ACCEL = 0.30
TUCSON_CANFD_FRICTION_RETURN_JERK_SCALE = 0.45
TUCSON_CANFD_FRICTION_NEAR_ZERO_JERK_SCALE = 0.30
TUCSON_CANFD_FRICTION_RETURN_INPUT_SCALE = 0.70
TUCSON_CANFD_FRICTION_NEAR_ZERO_INPUT_SCALE = 0.50
LAT_ACCEL_REQUEST_BUFFER_SECONDS = 1.0
VERSION = 1


def is_tucson_canfd_torque_texture_scope(CP) -> bool:
  return bool(getattr(CP, "carFingerprint", None) == CAR.HYUNDAI_TUCSON_4TH_GEN and
              getattr(CP, "flags", 0) & HyundaiFlags.CANFD)


def tucson_canfd_friction_input(CP, v_ego: float, error: float, desired_lateral_jerk: float,
                                setpoint: float, future_desired_lateral_accel: float) -> float:
  jerk_term = JERK_GAIN * desired_lateral_jerk
  if not is_tucson_canfd_torque_texture_scope(CP) or v_ego >= TUCSON_CANFD_FRICTION_SHAPING_SPEED:
    return error + jerk_term

  same_direction = setpoint * future_desired_lateral_accel >= 0.0
  returning_to_center = same_direction and abs(future_desired_lateral_accel) < abs(setpoint)
  near_center = abs(future_desired_lateral_accel) <= TUCSON_CANFD_FRICTION_NEAR_ZERO_ACCEL

  jerk_scale = 1.0
  input_scale = 1.0
  if returning_to_center and abs(future_desired_lateral_accel) <= TUCSON_CANFD_FRICTION_RETURN_ACCEL:
    jerk_scale = min(jerk_scale, TUCSON_CANFD_FRICTION_RETURN_JERK_SCALE)
    input_scale = min(input_scale, TUCSON_CANFD_FRICTION_RETURN_INPUT_SCALE)
  if near_center and abs(setpoint) <= TUCSON_CANFD_FRICTION_RETURN_ACCEL:
    jerk_scale = min(jerk_scale, TUCSON_CANFD_FRICTION_NEAR_ZERO_JERK_SCALE)
    input_scale = min(input_scale, TUCSON_CANFD_FRICTION_NEAR_ZERO_INPUT_SCALE)

  shaped = error + jerk_term * jerk_scale
  if input_scale < 1.0:
    # Near center, do not let the jerk feedforward flip friction direction while
    # the lateral error is tiny; that creates visible step-release texture.
    if abs(error) < TUCSON_CANFD_FRICTION_NEAR_ZERO_ACCEL and error != 0.0 and shaped * error < 0.0:
      shaped = error
    shaped *= input_scale
  return shaped

class LatControlTorque(LatControl):
  def __init__(self, CP, CP_SP, CI, dt):
    super().__init__(CP, CP_SP, CI, dt)
    self.torque_params = CP.lateralTuning.torque.as_builder()
    self.torque_from_lateral_accel = CI.torque_from_lateral_accel()
    self.lateral_accel_from_torque = CI.lateral_accel_from_torque()
    self.pid = PIDController([INTERP_SPEEDS, KP_INTERP], KI, rate=1/self.dt)
    self.update_limits()
    self.steering_angle_deadzone_deg = self.torque_params.steeringAngleDeadzoneDeg
    self.lat_accel_request_buffer_len = int(LAT_ACCEL_REQUEST_BUFFER_SECONDS / self.dt)
    self.lat_accel_request_buffer = deque([0.] * self.lat_accel_request_buffer_len , maxlen=self.lat_accel_request_buffer_len)
    self.lookahead_frames = int(JERK_LOOKAHEAD_SECONDS / self.dt)
    self.jerk_filter = FirstOrderFilter(0.0, 1 / (2 * np.pi * LP_FILTER_CUTOFF_HZ), self.dt)

    self.extension = LatControlTorqueExt(self, CP, CP_SP, CI)

  def update_live_torque_params(self, latAccelFactor, latAccelOffset, friction):
    self.torque_params.latAccelFactor = latAccelFactor
    self.torque_params.latAccelOffset = latAccelOffset
    self.torque_params.friction = friction
    self.update_limits()

  def update_limits(self):
    self.pid.set_limits(self.lateral_accel_from_torque(self.steer_max, self.torque_params),
                        self.lateral_accel_from_torque(-self.steer_max, self.torque_params))

  def update(self, active, CS, VM, params, steer_limited_by_safety, desired_curvature, calibrated_pose, curvature_limited, lat_delay):
    # Override torque params from extension
    if self.extension.update_override_torque_params(self.torque_params):
      self.update_limits()

    pid_log = log.ControlsState.LateralTorqueState.new_message()
    pid_log.version = VERSION
    measured_curvature = -VM.calc_curvature(math.radians(CS.steeringAngleDeg - params.angleOffsetDeg), CS.vEgo, params.roll)
    measurement = measured_curvature * CS.vEgo ** 2
    future_desired_lateral_accel = desired_curvature * CS.vEgo ** 2
    self.lat_accel_request_buffer.append(future_desired_lateral_accel)

    roll_compensation = params.roll * ACCELERATION_DUE_TO_GRAVITY
    curvature_deadzone = abs(VM.calc_curvature(math.radians(self.steering_angle_deadzone_deg), CS.vEgo, 0.0))
    lateral_accel_deadzone = curvature_deadzone * CS.vEgo ** 2

    delay_frames = int(np.clip(lat_delay / self.dt + 1, 1, self.lat_accel_request_buffer_len))
    expected_lateral_accel = self.lat_accel_request_buffer[-delay_frames]
    setpoint = expected_lateral_accel
    error = setpoint - measurement

    lookahead_idx = int(np.clip(-delay_frames + self.lookahead_frames, -self.lat_accel_request_buffer_len+1, -2))
    raw_lateral_jerk = (self.lat_accel_request_buffer[lookahead_idx+1] - self.lat_accel_request_buffer[lookahead_idx-1]) / (2 * self.dt)
    desired_lateral_jerk = self.jerk_filter.update(raw_lateral_jerk)
    gravity_adjusted_future_lateral_accel = future_desired_lateral_accel - roll_compensation
    ff = gravity_adjusted_future_lateral_accel
    # latAccelOffset corrects roll compensation bias from device roll misalignment relative to car roll
    ff -= self.torque_params.latAccelOffset
    friction_input = tucson_canfd_friction_input(self.CP, CS.vEgo, error, desired_lateral_jerk, setpoint, future_desired_lateral_accel)
    ff += get_friction(friction_input, lateral_accel_deadzone, FRICTION_THRESHOLD, self.torque_params)

    if not active:
      output_torque = 0.0
      self.extension.reset_tucson_canfd_low_speed_torque_smoothing()
      pid_log.active = False
    else:
      # do error correction in lateral acceleration space, convert at end to handle non-linear torque responses correctly
      pid_log.error = float(error)

      freeze_integrator = steer_limited_by_safety or CS.steeringPressed or CS.vEgo < 5
      output_lataccel = self.pid.update(pid_log.error, speed=CS.vEgo, feedforward=ff, freeze_integrator=freeze_integrator)
      output_torque = self.torque_from_lateral_accel(output_lataccel, self.torque_params)

      # Lateral acceleration torque controller extension updates
      # Overrides pid_log.error and output_torque
      pid_log, output_torque = self.extension.update(CS, VM, self.pid, params, ff, pid_log, setpoint, measurement, calibrated_pose, roll_compensation,
                                                     future_desired_lateral_accel, measurement, lateral_accel_deadzone, gravity_adjusted_future_lateral_accel,
                                                     desired_curvature, measured_curvature, steer_limited_by_safety, output_torque)

      pid_log.active = True
      pid_log.p = float(self.pid.p)
      pid_log.i = float(self.pid.i)
      pid_log.d = float(self.pid.d)
      pid_log.f = float(self.pid.f)
      pid_log.output = float(-output_torque) # TODO: log lat accel?
      pid_log.actualLateralAccel = float(measurement)
      pid_log.desiredLateralAccel = float(setpoint)
      pid_log.desiredLateralJerk = float(desired_lateral_jerk)
      pid_log.saturated = bool(self._check_saturation(self.steer_max - abs(output_torque) < 1e-3, CS, steer_limited_by_safety, curvature_limited))

    # TODO left is positive in this convention
    return -output_torque, 0.0, pid_log
