from types import SimpleNamespace

from opendbc.car import structs
from opendbc.car.hyundai.carstate import (
  BRICKPILOT_PHEV_CAN_LOGGER_VERSION,
  CarState,
)
from opendbc.car.hyundai.values import CAR, HyundaiFlags


def make_state(flags=HyundaiFlags.CANFD | HyundaiFlags.HYBRID):
  state = CarState.__new__(CarState)
  state.CP = SimpleNamespace(
    flags=flags,
    carFingerprint=CAR.HYUNDAI_TUCSON_4TH_GEN,
    safetyConfigs=[object()],
  )
  state._init_brickpilot_phev_can_logger()
  return state


def test_phev_candidate_logger_decodes_signed_and_mirrored_fa_b4():
  state = make_state()
  fa_bus0 = bytearray(24)
  fa_bus130 = bytearray(24)
  fa_bus0[4] = 253
  fa_bus130[4] = 253

  e0 = bytearray(24)
  e0[8:10] = (-1000).to_bytes(2, "little", signed=True)
  e0[10:12] = (32000).to_bytes(2, "little", signed=True)
  e0[16:18] = (-39).to_bytes(2, "little", signed=True)

  ba = bytearray(24)
  ba[11] = 250
  ba[14] = 1
  c5 = bytearray(24)
  c5[5] = 7
  a5 = bytearray(24)
  a5[14] = 31
  a5[15] = 32
  a5[16] = 33
  a5[17] = 34
  a10 = bytearray(24)
  a10[10] = 241
  a10[18] = 12
  a120 = bytearray(24)
  a120[3] = 145
  brake = bytearray(24)
  brake[9] = 144
  brake[10] = 145
  adas = bytearray(24)
  adas[17] = 226
  adas[18] = 255
  f06f = bytearray(8)
  f06f[4] = 244

  state.update_can_packets([
    (123, [
      (0x0FA, bytes(fa_bus0), 0),
      (0x0FA, bytes(fa_bus130), 130),
      (0x0E0, bytes(e0), 0),
      (0x0BA, bytes(ba), 0),
      (0x1C5, bytes(c5), 0),
      (0x1A5, bytes(a5), 0),
      (0x10A, bytes(a10), 0),
      (0x120, bytes(a120), 0),
      (0x065, bytes(brake), 0),
      (0x310, bytes(adas), 1),
      (0x06F, bytes(f06f), 0),
    ]),
  ])

  ret_sp = structs.CarStateSP()
  state._populate_brickpilot_phev_can(ret_sp)

  assert ret_sp.brickpilotPhevCanLoggerVersion == BRICKPILOT_PHEV_CAN_LOGGER_VERSION
  assert ret_sp.brickpilotPhevCanCandidatePresentMask == 0x3FF
  assert ret_sp.brickpilotPhevCanFrameUpdateMask == 0x3FF
  assert ret_sp.brickpilotPhevFaSourceMask == (1 << 0) | (1 << 5)
  assert ret_sp.brickpilotPhevSelectedSource == 0
  assert ret_sp.brickpilotPhevHybridFlagSet

  assert ret_sp.brickpilotPhevFaB4U8 == 253
  assert ret_sp.brickpilotPhevFaB4S8 == -3
  assert ret_sp.brickpilotPhevFaB4U8Bus0 == 253
  assert ret_sp.brickpilotPhevFaB4S8Bus0 == -3
  assert ret_sp.brickpilotPhevFaB4U8Bus130 == 253
  assert ret_sp.brickpilotPhevFaB4S8Bus130 == -3
  assert ret_sp.brickpilotPhevFaB4MirrorConsistent

  assert ret_sp.brickpilotPhevE0S16Byte08Le == -1000
  assert ret_sp.brickpilotPhevE0S16Byte10Le == 32000
  assert ret_sp.brickpilotPhevE0S16Byte16Le == -39
  assert ret_sp.brickpilotPhevBaB11S8 == -6
  assert ret_sp.brickpilotPhevBaB14U8 == 1
  assert ret_sp.brickpilotPhev1C5B5U8 == 7
  assert ret_sp.brickpilotPhev1A5B14U8 == 31
  assert ret_sp.brickpilotPhev1A5B15U8 == 32
  assert ret_sp.brickpilotPhev1A5B16U8 == 33
  assert ret_sp.brickpilotPhev1A5B17U8 == 34
  assert ret_sp.brickpilotPhev06FB4U8 == 244
  assert ret_sp.brickpilotPhev06FB4S8 == -12
  assert ret_sp.brickpilotPhev10AB10U8 == 241
  assert ret_sp.brickpilotPhev10AB18U8 == 12
  assert ret_sp.brickpilotPhev120B3U8 == 145
  assert ret_sp.brickpilotBrake065B9U8 == 144
  assert ret_sp.brickpilotBrake065B10U8 == 145
  assert ret_sp.brickpilotAdas310B17U8 == 226
  assert ret_sp.brickpilotAdas310B18U8 == 255

  state.update_can_packets([])
  ret_sp = structs.CarStateSP()
  state._populate_brickpilot_phev_can(ret_sp)

  assert ret_sp.brickpilotPhevCanFrameUpdateMask == 0
  assert ret_sp.brickpilotPhevFaB4S8 == -3
