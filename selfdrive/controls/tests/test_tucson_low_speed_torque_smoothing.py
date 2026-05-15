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

from openpilot.sunnypilot.selfdrive.controls.lib.latcontrol_torque_ext import LatControlTorqueExt  # noqa: E402


def make_ext(car_fingerprint=CAR.HYUNDAI_TUCSON_4TH_GEN, flags=HyundaiFlags.CANFD):
  ext = LatControlTorqueExt.__new__(LatControlTorqueExt)
  ext.CP = SimpleNamespace(carFingerprint=car_fingerprint, flags=flags)
  ext.tucson_canfd_output_torque_smoothing_initialized = False
  ext.tucson_canfd_output_torque_smooth = 0.0
  ext.tucson_canfd_output_torque_smoothing_driver_override_cooldown = 0
  return ext


def car_state(speed_mph=10.0, steering_pressed=False):
  return SimpleNamespace(vEgo=speed_mph * CV.MPH_TO_MS, steeringPressed=steering_pressed)


def test_tucson_canfd_low_speed_smoothing_reduces_fast_output_reversal():
  ext = make_ext()

  assert ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(), 0.8) == 0.8
  smoothed = ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(), -0.8)

  assert abs(smoothed - 0.4) < 1e-9


def test_smoothing_blends_out_between_20_and_35_mph():
  ext = make_ext()

  assert ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(speed_mph=30.0), 0.8) == 0.8
  smoothed = ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(speed_mph=30.0), -0.8)

  # At 30 mph the smoother is mostly faded out: alpha = 0.75.
  assert abs(smoothed + 0.4) < 1e-9


def test_smoothing_resets_for_driver_steering_and_inactive_lateral_control():
  ext = make_ext()
  ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(), 0.8)

  assert ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(steering_pressed=True), -0.5) == -0.5
  assert not ext.tucson_canfd_output_torque_smoothing_initialized
  assert ext.tucson_canfd_output_torque_smooth == 0.0

  assert ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(), 0.4) == 0.4
  assert not ext.tucson_canfd_output_torque_smoothing_initialized

  ext.tucson_canfd_output_torque_smoothing_driver_override_cooldown = 0
  assert ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(), 0.4) == 0.4

  ext.reset_tucson_canfd_low_speed_torque_smoothing()
  assert not ext.tucson_canfd_output_torque_smoothing_initialized
  assert ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(), -0.4) == -0.4


def test_driver_steering_bypasses_smoothing_briefly_after_release():
  ext = make_ext()

  ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(), 0.8)
  assert ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(steering_pressed=True), -0.8) == -0.8

  assert ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(), 0.8) == 0.8
  assert not ext.tucson_canfd_output_torque_smoothing_initialized

  for _ in range(24):
    assert ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(), -0.6) == -0.6

  assert ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(), 0.6) == 0.6
  smoothed = ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(), -0.6)
  assert abs(smoothed - 0.3) < 1e-9


def test_non_tucson_and_high_speed_paths_keep_raw_output_and_reset_smoothing():
  non_tucson = make_ext(car_fingerprint=CAR.HYUNDAI_IONIQ_5)
  assert non_tucson.apply_tucson_canfd_low_speed_torque_smoothing(car_state(), -0.8) == -0.8
  assert not non_tucson.tucson_canfd_output_torque_smoothing_initialized

  non_canfd = make_ext(flags=0)
  assert non_canfd.apply_tucson_canfd_low_speed_torque_smoothing(car_state(), -0.8) == -0.8
  assert not non_canfd.tucson_canfd_output_torque_smoothing_initialized

  ext = make_ext()
  assert ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(), 0.8) == 0.8
  assert ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(speed_mph=40.0), -0.8) == -0.8
  assert not ext.tucson_canfd_output_torque_smoothing_initialized
  assert ext.apply_tucson_canfd_low_speed_torque_smoothing(car_state(), 0.5) == 0.5


def test_tucson_canfd_keeps_stock_canfd_safety_slew_limits():
  params = CarControllerParams(SimpleNamespace(carFingerprint=CAR.HYUNDAI_TUCSON_4TH_GEN, flags=HyundaiFlags.CANFD))

  assert params.STEER_MAX == 270
  assert params.STEER_DELTA_UP == 2
  assert params.STEER_DELTA_DOWN == 3
