from types import SimpleNamespace

from opendbc.car.hyundai.carcontroller import (
  CarController,
  MAX_ANGLE,
  TUCSON_CANFD_ANGLE_RECOVERY,
  TUCSON_CANFD_STEER_FAULT_COOLDOWN_FRAMES,
)
from opendbc.car.hyundai.values import CAR, HyundaiFlags
from opendbc.sunnypilot.car.hyundai.mads import MadsDataSP


class TestTucsonCanFdMadsGating:
  @staticmethod
  def controller(car_fingerprint=CAR.HYUNDAI_TUCSON_4TH_GEN, flags=HyundaiFlags.CANFD, mads_enabled=True):
    controller = CarController.__new__(CarController)
    controller.CP = SimpleNamespace(flags=flags, carFingerprint=car_fingerprint)
    controller.mads = MadsDataSP(mads_enabled, True, False, False)
    controller.tucson_canfd_angle_limited = False
    controller.tucson_canfd_steer_fault_cooldown_frames = 0
    return controller

  @staticmethod
  def car_control(enabled=False, lat_active=True, override=False):
    return SimpleNamespace(enabled=enabled, latActive=lat_active,
                           cruiseControl=SimpleNamespace(override=override))

  @staticmethod
  def car_state(gas=False, brake=False, steering_pressed=False, angle=0.0, steer_fault=False):
    return SimpleNamespace(out=SimpleNamespace(gasPressed=gas, brakePressed=brake,
                                               steeringPressed=steering_pressed,
                                               steeringAngleDeg=angle,
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

  def test_high_angle_latches_until_recovery_hysteresis(self):
    controller = self.controller()

    assert not controller.get_tucson_canfd_apply_steer_req(self.car_control(enabled=True), self.car_state(angle=MAX_ANGLE), True)
    assert not controller.get_tucson_canfd_apply_steer_req(self.car_control(enabled=True), self.car_state(angle=TUCSON_CANFD_ANGLE_RECOVERY + 1), True)
    assert controller.get_tucson_canfd_apply_steer_req(self.car_control(enabled=True), self.car_state(angle=TUCSON_CANFD_ANGLE_RECOVERY), True)

  def test_steer_fault_temporary_cooldown_suppresses_active_fault_plus_exact_subsequent_frames(self):
    controller = self.controller()

    # The fault frame is suppressed and starts a 100-frame cooldown for the
    # subsequent no-fault frames; recovery is allowed on frame 101 after fault.
    assert not controller.get_tucson_canfd_apply_steer_req(self.car_control(enabled=True), self.car_state(steer_fault=True), True)
    assert controller.tucson_canfd_steer_fault_cooldown_frames == TUCSON_CANFD_STEER_FAULT_COOLDOWN_FRAMES

    for remaining_before_call in range(TUCSON_CANFD_STEER_FAULT_COOLDOWN_FRAMES, 0, -1):
      assert not controller.get_tucson_canfd_apply_steer_req(self.car_control(enabled=True), self.car_state(), True)
      assert controller.tucson_canfd_steer_fault_cooldown_frames == remaining_before_call - 1

    assert controller.get_tucson_canfd_apply_steer_req(self.car_control(enabled=True), self.car_state(), True)
    assert controller.tucson_canfd_steer_fault_cooldown_frames == 0

  def test_non_tucson_or_non_mads_keeps_existing_request_state(self):
    assert self.controller(car_fingerprint=CAR.KIA_EV6).get_tucson_canfd_apply_steer_req(self.car_control(enabled=False), self.car_state(), True)
    assert not self.controller(car_fingerprint=CAR.KIA_EV6).get_tucson_canfd_apply_steer_req(self.car_control(enabled=False), self.car_state(), False)
    assert self.controller(mads_enabled=False).get_tucson_canfd_apply_steer_req(self.car_control(enabled=False), self.car_state(), True)
