import sys
from types import ModuleType, SimpleNamespace

from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.hyundai.values import CAR, CarControllerParams, HyundaiFlags


class FakeNeuralNetworkLateralControl:
  pass


class FakeLatControlTorqueExtOverride:
  pass


fake_nnlc = ModuleType("openpilot.sunnypilot.selfdrive.controls.lib.nnlc.nnlc")
fake_nnlc.NeuralNetworkLateralControl = FakeNeuralNetworkLateralControl
sys.modules.setdefault("openpilot.sunnypilot.selfdrive.controls.lib.nnlc.nnlc", fake_nnlc)

fake_override = ModuleType("openpilot.sunnypilot.selfdrive.controls.lib.latcontrol_torque_ext_override")
fake_override.LatControlTorqueExtOverride = FakeLatControlTorqueExtOverride
sys.modules.setdefault("openpilot.sunnypilot.selfdrive.controls.lib.latcontrol_torque_ext_override", fake_override)

from openpilot.sunnypilot.selfdrive.controls.lib.latcontrol_torque_ext import (  # noqa: E402
  LatControlTorqueExt,
  TUCSON_CANFD_TORQUE_TEXTURE_SCALE,
)


def make_ext(car_fingerprint=CAR.HYUNDAI_TUCSON_4TH_GEN, flags=HyundaiFlags.CANFD):
  ext = LatControlTorqueExt.__new__(LatControlTorqueExt)
  ext.CP = SimpleNamespace(carFingerprint=car_fingerprint, flags=flags)
  ext.tucson_canfd_output_torque_smoothing_initialized = False
  ext.tucson_canfd_output_torque_smooth = 0.0
  ext.tucson_canfd_output_torque_second_smooth = 0.0
  ext.tucson_canfd_output_torque_smoothing_driver_override_cooldown = 0
  ext.tucson_canfd_output_torque_zero_cross_hold = 0
  ext.tucson_canfd_output_torque_reversal_hold = 0
  return ext


def car_state(speed_mph=10.0, steering_pressed=False):
  return SimpleNamespace(vEgo=speed_mph * CV.MPH_TO_MS, steeringPressed=steering_pressed)


def test_tucson_canfd_low_speed_smoothing_reduces_fast_output_reversal():
  ext = make_ext()

  assert ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(), 0.8) == 0.8 * TUCSON_CANFD_TORQUE_TEXTURE_SCALE
  smoothed = ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(), -0.8)

  assert abs(smoothed - 0.7053324562065397) < 1e-9


def test_smoothing_remains_active_at_suburban_speeds():
  ext = make_ext()

  assert ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(speed_mph=40.0), 0.8) == 0.8 * TUCSON_CANFD_TORQUE_TEXTURE_SCALE
  smoothed = ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(speed_mph=40.0), -0.8)

  assert abs(smoothed - 0.7053324562065397) < 1e-9


def test_weak_zero_cross_reversal_hold_reduces_ping_pong_texture():
  ext = make_ext()

  assert ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(), 0.3) == 0.3 * TUCSON_CANFD_TORQUE_TEXTURE_SCALE
  for _ in range(4):
    assert ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(), -0.3) == 0.0

  smoothed = ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(), -0.3)
  assert abs(smoothed + 0.0038991973744835835) < 1e-9


def test_smoothing_resets_for_driver_steering_and_inactive_lateral_control():
  ext = make_ext()
  ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(), 0.8)

  assert ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(steering_pressed=True), -0.5) == -0.5
  assert not ext.tucson_canfd_output_torque_smoothing_initialized
  assert ext.tucson_canfd_output_torque_smooth == 0.0
  assert ext.tucson_canfd_output_torque_second_smooth == 0.0

  assert ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(), 0.4) == 0.4
  assert not ext.tucson_canfd_output_torque_smoothing_initialized

  ext.tucson_canfd_output_torque_smoothing_driver_override_cooldown = 0
  assert ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(), 0.4) == 0.4 * TUCSON_CANFD_TORQUE_TEXTURE_SCALE

  ext.reset_tucson_canfd_low_speed_torque_smoothing()
  assert not ext.tucson_canfd_output_torque_smoothing_initialized
  assert ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(), -0.4) == -0.4 * TUCSON_CANFD_TORQUE_TEXTURE_SCALE


def test_driver_steering_bypasses_smoothing_briefly_after_release():
  ext = make_ext()

  ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(), 0.8)
  assert ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(steering_pressed=True), -0.8) == -0.8

  assert ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(), 0.8) == 0.8
  assert not ext.tucson_canfd_output_torque_smoothing_initialized

  for _ in range(24):
    assert ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(), -0.6) == -0.6

  assert ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(), 0.6) == 0.6 * TUCSON_CANFD_TORQUE_TEXTURE_SCALE
  smoothed = ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(), -0.6)
  assert abs(smoothed) < 1e-9


def test_non_tucson_and_high_speed_paths_keep_raw_output_and_reset_smoothing():
  non_tucson = make_ext(car_fingerprint=CAR.HYUNDAI_IONIQ_5)
  assert non_tucson.apply_tucson_canfd_low_speed_torque_smoothing(car_state(), -0.8) == -0.8
  assert not non_tucson.tucson_canfd_output_torque_smoothing_initialized

  non_canfd = make_ext(flags=0)
  assert non_canfd.apply_tucson_canfd_low_speed_torque_smoothing(car_state(), -0.8) == -0.8
  assert not non_canfd.tucson_canfd_output_torque_smoothing_initialized

  ext = make_ext()
  assert ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(), 0.8) == 0.8 * TUCSON_CANFD_TORQUE_TEXTURE_SCALE
  assert ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(speed_mph=65.0), -0.8) == -0.8
  assert not ext.tucson_canfd_output_torque_smoothing_initialized
  assert ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(), 0.5) == 0.5 * TUCSON_CANFD_TORQUE_TEXTURE_SCALE


def test_tucson_canfd_keeps_stock_canfd_safety_slew_limits():
  params = CarControllerParams(SimpleNamespace(carFingerprint=CAR.HYUNDAI_TUCSON_4TH_GEN, flags=HyundaiFlags.CANFD))

  assert params.STEER_MAX == 270
  assert params.STEER_DELTA_UP == 2
  assert params.STEER_DELTA_DOWN == 3
