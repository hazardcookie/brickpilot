from types import SimpleNamespace

from opendbc.car.hyundai.carcontroller import (
  CarController,
  MAX_ANGLE,
  TUCSON_CANFD_MADS_MANUAL_STEER_MAX_SPEED,
  TUCSON_CANFD_MADS_MANUAL_STEER_MIN_ANGLE,
)
from opendbc.car.hyundai.values import CAR, HyundaiFlags
from opendbc.car.common.conversions import Conversions as CV
from opendbc.sunnypilot.car.hyundai.mads import MadsDataSP


class TestTucsonCanFdMadsGating:
  @staticmethod
  def controller(car_fingerprint=CAR.HYUNDAI_TUCSON_4TH_GEN, flags=HyundaiFlags.CANFD, mads_enabled=True):
    controller = CarController.__new__(CarController)
    controller.CP = SimpleNamespace(flags=flags, carFingerprint=car_fingerprint)
    controller.mads = MadsDataSP(mads_enabled, True, False, False)
    return controller

  @staticmethod
  def car_control(enabled=False, lat_active=True, override=False):
    return SimpleNamespace(enabled=enabled, latActive=lat_active,
                           cruiseControl=SimpleNamespace(override=override))

  @staticmethod
  def car_state(gas=False, brake=False, steering_pressed=False, angle=0.0, steer_fault=False, speed_mph=10.0):
    return SimpleNamespace(out=SimpleNamespace(gasPressed=gas, brakePressed=brake,
                                               steeringPressed=steering_pressed,
                                               steeringAngleDeg=angle,
                                               vEgo=speed_mph * CV.MPH_TO_MS,
                                               steerFaultTemporary=steer_fault))

  def test_normal_mads_always_steering_states_keep_request(self):
    states = (
      (self.car_control(enabled=False), self.car_state()),
      (self.car_control(enabled=True, override=True), self.car_state()),
      (self.car_control(enabled=True), self.car_state(gas=True)),
      (self.car_control(enabled=True), self.car_state(brake=True)),
      (self.car_control(enabled=True), self.car_state(steering_pressed=True)),
    )

    for car_control, car_state in states:
      controller = self.controller()
      assert controller.get_tucson_canfd_apply_steer_req(car_control, car_state, True)
      assert not controller.get_tucson_canfd_apply_steer_req(car_control, car_state, False)

  def test_tucson_guard_restores_normal_upstream_request_state(self):
    controller = self.controller()

    # The old local guard suppressed immediately here. 0.4.x keeps only
    # the upstream common_fault_avoidance result that was passed in.
    assert controller.get_tucson_canfd_apply_steer_req(self.car_control(enabled=True), self.car_state(angle=MAX_ANGLE), True)
    assert controller.get_tucson_canfd_apply_steer_req(self.car_control(enabled=True), self.car_state(steer_fault=True), True)
    assert not controller.get_tucson_canfd_apply_steer_req(self.car_control(enabled=True), self.car_state(angle=MAX_ANGLE), False)
    assert not controller.get_tucson_canfd_apply_steer_req(self.car_control(enabled=True), self.car_state(steer_fault=True), False)

  def test_tucson_mads_manual_high_angle_turn_cuts_request_only_when_driver_is_steering(self):
    controller = self.controller()
    car_control = self.car_control(enabled=True)

    assert not controller.get_tucson_canfd_apply_steer_req(
      car_control,
      self.car_state(steering_pressed=True, angle=TUCSON_CANFD_MADS_MANUAL_STEER_MIN_ANGLE + 1.0),
      True,
    )
    assert controller.get_tucson_canfd_apply_steer_req(
      car_control,
      self.car_state(steering_pressed=False, angle=TUCSON_CANFD_MADS_MANUAL_STEER_MIN_ANGLE + 1.0),
      True,
    )
    assert controller.get_tucson_canfd_apply_steer_req(
      car_control,
      self.car_state(steering_pressed=True, angle=TUCSON_CANFD_MADS_MANUAL_STEER_MIN_ANGLE - 1.0),
      True,
    )
    assert controller.get_tucson_canfd_apply_steer_req(
      car_control,
      self.car_state(steering_pressed=True, angle=TUCSON_CANFD_MADS_MANUAL_STEER_MIN_ANGLE + 1.0,
                     speed_mph=(TUCSON_CANFD_MADS_MANUAL_STEER_MAX_SPEED / CV.MPH_TO_MS) + 1.0),
      True,
    )

  def test_non_tucson_or_non_mads_keeps_existing_request_state(self):
    assert self.controller(car_fingerprint=CAR.KIA_EV6).get_tucson_canfd_apply_steer_req(self.car_control(enabled=False), self.car_state(), True)
    assert not self.controller(car_fingerprint=CAR.KIA_EV6).get_tucson_canfd_apply_steer_req(self.car_control(enabled=False), self.car_state(), False)
    assert self.controller(mads_enabled=False).get_tucson_canfd_apply_steer_req(self.car_control(enabled=False), self.car_state(), True)
