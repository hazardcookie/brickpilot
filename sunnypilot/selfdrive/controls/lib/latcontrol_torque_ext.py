"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""

from openpilot.sunnypilot.selfdrive.controls.lib.nnlc.nnlc import NeuralNetworkLateralControl
from openpilot.sunnypilot.selfdrive.controls.lib.latcontrol_torque_ext_override import LatControlTorqueExtOverride
from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.hyundai.values import CAR, HyundaiFlags


TUCSON_CANFD_TORQUE_TEXTURE_FULL_SMOOTH_SPEED = 34 * CV.MPH_TO_MS
TUCSON_CANFD_TORQUE_TEXTURE_NO_SMOOTH_SPEED = 62 * CV.MPH_TO_MS
TUCSON_CANFD_TORQUE_TEXTURE_ALPHA = 0.16
TUCSON_CANFD_TORQUE_TEXTURE_REVERSAL_ALPHA_SCALE = 0.50
TUCSON_CANFD_TORQUE_TEXTURE_DRIVER_OVERRIDE_COOLDOWN_FRAMES = 25
TUCSON_CANFD_TORQUE_TEXTURE_ZERO_CROSS_HOLD_FRAMES = 5
TUCSON_CANFD_TORQUE_TEXTURE_ZERO_CROSS_MAX_RAW = 0.42
TUCSON_CANFD_TORQUE_TEXTURE_ZERO_CROSS_MAX_SMOOTH = 0.42


class LatControlTorqueExt(NeuralNetworkLateralControl, LatControlTorqueExtOverride):
  def __init__(self, lac_torque, CP, CP_SP, CI):
    NeuralNetworkLateralControl.__init__(self, lac_torque, CP, CP_SP, CI)
    LatControlTorqueExtOverride.__init__(self, CP)
    self.tucson_canfd_output_torque_smoothing_initialized = False
    self.tucson_canfd_output_torque_smooth = 0.0
    self.tucson_canfd_output_torque_smoothing_driver_override_cooldown = 0
    self.tucson_canfd_output_torque_zero_cross_hold = 0

  def reset_tucson_canfd_low_speed_torque_smoothing(self) -> None:
    self.tucson_canfd_output_torque_smoothing_initialized = False
    self.tucson_canfd_output_torque_smooth = 0.0
    self.tucson_canfd_output_torque_zero_cross_hold = 0

  def apply_tucson_canfd_low_speed_torque_smoothing(self, CS, output_torque: float) -> float:
    # Brickpilot Tucson steering-texture candidate: smooth controller output
    # before stock CAN-FD safety/rate limits rather than lowering those limits.
    # 0.4.4 widens the smoothing band to normal suburban speeds and holds weak
    # zero-crossings longer, targeting ping-pong texture without changing
    # Hyundai CAN-FD safety/rate limits.
    is_tucson_canfd = bool(self.CP.flags & HyundaiFlags.CANFD and
                           self.CP.carFingerprint == CAR.HYUNDAI_TUCSON_4TH_GEN)
    if not is_tucson_canfd or CS.vEgo >= TUCSON_CANFD_TORQUE_TEXTURE_NO_SMOOTH_SPEED:
      self.reset_tucson_canfd_low_speed_torque_smoothing()
      self.tucson_canfd_output_torque_smoothing_driver_override_cooldown = 0
      return output_torque

    if CS.steeringPressed:
      self.reset_tucson_canfd_low_speed_torque_smoothing()
      self.tucson_canfd_output_torque_smoothing_driver_override_cooldown = TUCSON_CANFD_TORQUE_TEXTURE_DRIVER_OVERRIDE_COOLDOWN_FRAMES
      return output_torque

    if self.tucson_canfd_output_torque_smoothing_driver_override_cooldown > 0:
      self.tucson_canfd_output_torque_smoothing_driver_override_cooldown -= 1
      self.reset_tucson_canfd_low_speed_torque_smoothing()
      return output_torque

    if self.tucson_canfd_output_torque_zero_cross_hold > 0:
      if abs(output_torque) <= TUCSON_CANFD_TORQUE_TEXTURE_ZERO_CROSS_MAX_RAW:
        self.tucson_canfd_output_torque_zero_cross_hold -= 1
        self.tucson_canfd_output_torque_smoothing_initialized = True
        self.tucson_canfd_output_torque_smooth = 0.0
        return 0.0
      self.tucson_canfd_output_torque_zero_cross_hold = 0

    if not self.tucson_canfd_output_torque_smoothing_initialized:
      self.tucson_canfd_output_torque_smoothing_initialized = True
      self.tucson_canfd_output_torque_smooth = output_torque
      return output_torque

    speed_blend = 1.0
    if CS.vEgo > TUCSON_CANFD_TORQUE_TEXTURE_FULL_SMOOTH_SPEED:
      speed_blend = ((TUCSON_CANFD_TORQUE_TEXTURE_NO_SMOOTH_SPEED - CS.vEgo) /
                     (TUCSON_CANFD_TORQUE_TEXTURE_NO_SMOOTH_SPEED - TUCSON_CANFD_TORQUE_TEXTURE_FULL_SMOOTH_SPEED))

    alpha = 1.0 - speed_blend * (1.0 - TUCSON_CANFD_TORQUE_TEXTURE_ALPHA)
    weak_zero_cross = bool(output_torque * self.tucson_canfd_output_torque_smooth < 0.0 and
                           abs(output_torque) <= TUCSON_CANFD_TORQUE_TEXTURE_ZERO_CROSS_MAX_RAW and
                           abs(self.tucson_canfd_output_torque_smooth) <= TUCSON_CANFD_TORQUE_TEXTURE_ZERO_CROSS_MAX_SMOOTH)
    if weak_zero_cross:
      self.tucson_canfd_output_torque_zero_cross_hold = TUCSON_CANFD_TORQUE_TEXTURE_ZERO_CROSS_HOLD_FRAMES
      self.tucson_canfd_output_torque_smooth = 0.0
      return 0.0

    if output_torque * self.tucson_canfd_output_torque_smooth < 0.0 and abs(output_torque - self.tucson_canfd_output_torque_smooth) > 0.35:
      alpha *= TUCSON_CANFD_TORQUE_TEXTURE_REVERSAL_ALPHA_SCALE

    self.tucson_canfd_output_torque_smooth += alpha * (output_torque - self.tucson_canfd_output_torque_smooth)
    return self.tucson_canfd_output_torque_smooth

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
