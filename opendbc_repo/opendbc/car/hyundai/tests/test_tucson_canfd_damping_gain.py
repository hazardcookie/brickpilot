from types import SimpleNamespace

from opendbc.car.hyundai import hyundaicanfd
from opendbc.car.hyundai.values import CAR, HyundaiFlags


class FakePacker:
  def __init__(self):
    self.messages = []

  def make_can_msg(self, name, bus, values):
    self.messages.append((name, bus, values.copy()))
    return name, bus, b""


class FakeCan:
  ECAN = 0
  ACAN = 1


def make_cp(car_fingerprint=CAR.HYUNDAI_TUCSON_4TH_GEN):
  return SimpleNamespace(
    carFingerprint=car_fingerprint,
    flags=HyundaiFlags.CANFD | HyundaiFlags.CANFD_LKA_STEER_MSG,
    openpilotLongitudinalControl=True,
  )


def test_tucson_canfd_uses_brickpilot_damping_gain():
  packer = FakePacker()

  hyundaicanfd.create_steering_messages(packer, make_cp(), FakeCan(), True, True, 20, 2)

  assert packer.messages
  assert hyundaicanfd.BRICKPILOT_TUCSON_CANFD_DAMPING_GAIN == 170
  assert all(values["Damping_Gain"] == hyundaicanfd.BRICKPILOT_TUCSON_CANFD_DAMPING_GAIN
             for _, _, values in packer.messages)


def test_non_tucson_canfd_keeps_stock_damping_gain():
  packer = FakePacker()

  hyundaicanfd.create_steering_messages(packer, make_cp(CAR.HYUNDAI_IONIQ_5), FakeCan(), True, True, 20, 2)

  assert packer.messages
  assert all(values["Damping_Gain"] == 100 for _, _, values in packer.messages)
