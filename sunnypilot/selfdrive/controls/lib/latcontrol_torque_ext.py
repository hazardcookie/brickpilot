"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""

from openpilot.sunnypilot.selfdrive.controls.lib.nnlc.nnlc import NeuralNetworkLateralControl
from openpilot.sunnypilot.selfdrive.controls.lib.latcontrol_torque_ext_override import LatControlTorqueExtOverride
from openpilot.common.realtime import DT_CTRL
from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.hyundai.values import CAR, HyundaiFlags


# Brickpilot 0.4.9 keeps the 0.4.8 friction-shaping + two-stage texture probe
# and adds manual high-angle MADS isolation. It keeps Hyundai CAN-FD safety/rate
# limits unchanged and fades texture out before highway speeds.
TUCSON_CANFD_TORQUE_TEXTURE_FULL_SMOOTH_SPEED = 38 * CV.MPH_TO_MS
TUCSON_CANFD_TORQUE_TEXTURE_NO_SMOOTH_SPEED = 70 * CV.MPH_TO_MS
TUCSON_CANFD_TORQUE_TEXTURE_ALPHA = 0.13000000
TUCSON_CANFD_TORQUE_TEXTURE_REVERSAL_ALPHA_SCALE = 0.40000000
TUCSON_CANFD_TORQUE_TEXTURE_DRIVER_OVERRIDE_COOLDOWN_FRAMES = 25
TUCSON_CANFD_TORQUE_TEXTURE_ZERO_CROSS_HOLD_FRAMES = 6
TUCSON_CANFD_TORQUE_TEXTURE_ZERO_CROSS_MAX_RAW = 0.48000000
TUCSON_CANFD_TORQUE_TEXTURE_ZERO_CROSS_MAX_SMOOTH = 0.48000000
TUCSON_CANFD_TORQUE_TEXTURE_SECOND_ALPHA = 0.24000000
TUCSON_CANFD_TORQUE_TEXTURE_DEADBAND = 0.01200000
TUCSON_CANFD_TORQUE_TEXTURE_SCALE = 0.95500000
TUCSON_CANFD_TORQUE_TEXTURE_REVERSAL_HOLD_FRAMES = 1
TUCSON_CANFD_TORQUE_TEXTURE_RATE_LIMIT_PER_SEC = None
TUCSON_CANFD_TORQUE_TEXTURE_CENTER_RETURN_ALPHA = 0.22000000
TUCSON_CANFD_TORQUE_TEXTURE_CENTER_RETURN_MAX_SMOOTH = 1.20
TUCSON_CANFD_MANUAL_STEER_ISOLATION_MIN_ANGLE = 35.0
TUCSON_CANFD_MANUAL_STEER_ISOLATION_MAX_SPEED = 30.0 * CV.MPH_TO_MS
TUCSON_CANFD_MANUAL_STEER_RELEASE_FRAMES = 30
TUCSON_CANFD_MANUAL_STEER_RELEASE_MAX_TORQUE = 0.35


class LatControlTorqueExt(NeuralNetworkLateralControl, LatControlTorqueExtOverride):
  def __init__(self, lac_torque, CP, CP_SP, CI):
    NeuralNetworkLateralControl.__init__(self, lac_torque, CP, CP_SP, CI)
    LatControlTorqueExtOverride.__init__(self, CP)
    self.tucson_canfd_output_torque_smoothing_initialized = False
    self.tucson_canfd_output_torque_smooth = 0.0
    self.tucson_canfd_output_torque_second_smooth = 0.0
    self.tucson_canfd_output_torque_smoothing_driver_override_cooldown = 0
    self.tucson_canfd_output_torque_zero_cross_hold = 0
    self.tucson_canfd_output_torque_reversal_hold = 0
    self.tucson_canfd_manual_steer_release_frames = 0

  def reset_tucson_canfd_low_speed_torque_smoothing(self) -> None:
    self.tucson_canfd_output_torque_smoothing_initialized = False
    self.tucson_canfd_output_torque_smooth = 0.0
    self.tucson_canfd_output_torque_second_smooth = 0.0
    self.tucson_canfd_output_torque_zero_cross_hold = 0
    self.tucson_canfd_output_torque_reversal_hold = 0

  @staticmethod
  def tucson_canfd_manual_steer_isolation_active(CS) -> bool:
    angle_deg = float(getattr(CS, "steeringAngleDeg", 0.0))
    return bool(CS.steeringPressed and
                CS.vEgo <= TUCSON_CANFD_MANUAL_STEER_ISOLATION_MAX_SPEED and
                abs(angle_deg) >= TUCSON_CANFD_MANUAL_STEER_ISOLATION_MIN_ANGLE)

  def apply_tucson_canfd_low_speed_torque_smoothing(self, CS, output_torque: float) -> float:
    # Brickpilot Tucson steering-texture candidate: smooth controller output
    # before stock CAN-FD safety/rate limits rather than lowering those limits.
    is_tucson_canfd = bool(self.CP.flags & HyundaiFlags.CANFD and
                           self.CP.carFingerprint == CAR.HYUNDAI_TUCSON_4TH_GEN)
    if not is_tucson_canfd or CS.vEgo >= TUCSON_CANFD_TORQUE_TEXTURE_NO_SMOOTH_SPEED:
      self.reset_tucson_canfd_low_speed_torque_smoothing()
      self.tucson_canfd_output_torque_smoothing_driver_override_cooldown = 0
      self.tucson_canfd_manual_steer_release_frames = 0
      return output_torque

    if self.tucson_canfd_manual_steer_isolation_active(CS):
      self.reset_tucson_canfd_low_speed_torque_smoothing()
      self.tucson_canfd_output_torque_smoothing_driver_override_cooldown = 0
      self.tucson_canfd_manual_steer_release_frames = TUCSON_CANFD_MANUAL_STEER_RELEASE_FRAMES
      return 0.0

    if self.tucson_canfd_manual_steer_release_frames > 0:
      self.tucson_canfd_manual_steer_release_frames -= 1
      self.reset_tucson_canfd_low_speed_torque_smoothing()
      release_scale = 1.0 - self.tucson_canfd_manual_steer_release_frames / max(1, TUCSON_CANFD_MANUAL_STEER_RELEASE_FRAMES)
      release_limit = TUCSON_CANFD_MANUAL_STEER_RELEASE_MAX_TORQUE * release_scale
      return max(-release_limit, min(release_limit, output_torque))

    if CS.steeringPressed:
      self.reset_tucson_canfd_low_speed_torque_smoothing()
      self.tucson_canfd_output_torque_smoothing_driver_override_cooldown = TUCSON_CANFD_TORQUE_TEXTURE_DRIVER_OVERRIDE_COOLDOWN_FRAMES
      return output_torque

    if self.tucson_canfd_output_torque_smoothing_driver_override_cooldown > 0:
      self.tucson_canfd_output_torque_smoothing_driver_override_cooldown -= 1
      self.reset_tucson_canfd_low_speed_torque_smoothing()
      return output_torque

    scaled_torque = output_torque * TUCSON_CANFD_TORQUE_TEXTURE_SCALE

    if self.tucson_canfd_output_torque_reversal_hold > 0:
      self.tucson_canfd_output_torque_reversal_hold -= 1
      self.tucson_canfd_output_torque_smoothing_initialized = True
      return self.tucson_canfd_output_torque_smooth

    if self.tucson_canfd_output_torque_zero_cross_hold > 0:
      if abs(scaled_torque) <= TUCSON_CANFD_TORQUE_TEXTURE_ZERO_CROSS_MAX_RAW:
        self.tucson_canfd_output_torque_zero_cross_hold -= 1
        self.tucson_canfd_output_torque_smoothing_initialized = True
        self.tucson_canfd_output_torque_smooth = 0.0
        self.tucson_canfd_output_torque_second_smooth = 0.0
        return 0.0
      self.tucson_canfd_output_torque_zero_cross_hold = 0

    if not self.tucson_canfd_output_torque_smoothing_initialized:
      self.tucson_canfd_output_torque_smoothing_initialized = True
      self.tucson_canfd_output_torque_smooth = scaled_torque
      self.tucson_canfd_output_torque_second_smooth = scaled_torque
      return scaled_torque

    weak_zero_cross = bool(scaled_torque * self.tucson_canfd_output_torque_smooth < 0.0 and
                           abs(scaled_torque) <= TUCSON_CANFD_TORQUE_TEXTURE_ZERO_CROSS_MAX_RAW and
                           abs(self.tucson_canfd_output_torque_smooth) <= TUCSON_CANFD_TORQUE_TEXTURE_ZERO_CROSS_MAX_SMOOTH)
    if weak_zero_cross:
      self.tucson_canfd_output_torque_zero_cross_hold = TUCSON_CANFD_TORQUE_TEXTURE_ZERO_CROSS_HOLD_FRAMES
      self.tucson_canfd_output_torque_reversal_hold = TUCSON_CANFD_TORQUE_TEXTURE_REVERSAL_HOLD_FRAMES
      self.tucson_canfd_output_torque_smooth = 0.0
      self.tucson_canfd_output_torque_second_smooth = 0.0
      return 0.0

    speed_blend = 1.0
    if CS.vEgo > TUCSON_CANFD_TORQUE_TEXTURE_FULL_SMOOTH_SPEED:
      denom = max(0.001, TUCSON_CANFD_TORQUE_TEXTURE_NO_SMOOTH_SPEED - TUCSON_CANFD_TORQUE_TEXTURE_FULL_SMOOTH_SPEED)
      speed_blend = max(0.0, min(1.0, (TUCSON_CANFD_TORQUE_TEXTURE_NO_SMOOTH_SPEED - CS.vEgo) / denom))

    alpha = 1.0 - speed_blend * (1.0 - TUCSON_CANFD_TORQUE_TEXTURE_ALPHA)
    if scaled_torque * self.tucson_canfd_output_torque_smooth < 0.0:
      alpha *= max(TUCSON_CANFD_TORQUE_TEXTURE_REVERSAL_ALPHA_SCALE, 1.0 - speed_blend)
    returning_to_center = bool(scaled_torque * self.tucson_canfd_output_torque_smooth > 0.0 and
                               abs(scaled_torque) < abs(self.tucson_canfd_output_torque_smooth) and
                               abs(self.tucson_canfd_output_torque_smooth) <= TUCSON_CANFD_TORQUE_TEXTURE_CENTER_RETURN_MAX_SMOOTH)
    if returning_to_center:
      alpha = max(alpha, 1.0 - speed_blend * (1.0 - TUCSON_CANFD_TORQUE_TEXTURE_CENTER_RETURN_ALPHA))

    next_value = self.tucson_canfd_output_torque_smooth + alpha * (scaled_torque - self.tucson_canfd_output_torque_smooth)
    if TUCSON_CANFD_TORQUE_TEXTURE_RATE_LIMIT_PER_SEC is not None:
      rate_limit = TUCSON_CANFD_TORQUE_TEXTURE_RATE_LIMIT_PER_SEC * DT_CTRL
      next_value = min(max(next_value, self.tucson_canfd_output_torque_smooth - rate_limit),
                       self.tucson_canfd_output_torque_smooth + rate_limit)
    if abs(next_value) < TUCSON_CANFD_TORQUE_TEXTURE_DEADBAND and abs(scaled_torque) < TUCSON_CANFD_TORQUE_TEXTURE_ZERO_CROSS_MAX_RAW:
      next_value = 0.0

    self.tucson_canfd_output_torque_smooth = next_value
    self.tucson_canfd_output_torque_second_smooth += TUCSON_CANFD_TORQUE_TEXTURE_SECOND_ALPHA * (
      self.tucson_canfd_output_torque_smooth - self.tucson_canfd_output_torque_second_smooth
    )
    return self.tucson_canfd_output_torque_second_smooth

  def update(self, CS, VM, pid, params, ff, pid_log, setpoint, measurement, calibrated_pose, roll_compensation,
             desired_lateral_accel, actual_lateral_accel, lateral_accel_deadzone, gravity_adjusted_lateral_accel,
             desired_curvature, actual_curvature, steer_limited_by_safety, output_torque):
    self._ff = ff
    self._pid = pid
    self._pid_log = pid_log
    self._setpoint = setpoint
    self._measurement = measurement
    self._roll_compensation = roll_compensation
    self._lateral_accel_deadzone = lateral_accel_deadzone
    self._desired_lateral_accel = desired_lateral_accel
    self._actual_lateral_accel = actual_lateral_accel
    self._desired_curvature = desired_curvature
    self._actual_curvature = actual_curvature
    self._gravity_adjusted_lateral_accel = gravity_adjusted_lateral_accel
    self._steer_limited_by_safety = steer_limited_by_safety
    self._output_torque = output_torque

    self.update_calculations(CS, VM, desired_lateral_accel)
    self.update_neural_network_feedforward(CS, params, calibrated_pose)
    self._output_torque = self.apply_tucson_canfd_low_speed_torque_smoothing(CS, self._output_torque)

    return self._pid_log, self._output_torque
