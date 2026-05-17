from collections import deque
import copy
import math

from opendbc.can import CANDefine, CANParser
from opendbc.car import Bus, create_button_events, structs
from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.hyundai.hyundaicanfd import CanBus
from opendbc.car.hyundai.values import HyundaiFlags, CAR, DBC, Buttons, CarControllerParams
from opendbc.car.interfaces import CarStateBase

from opendbc.sunnypilot.car.hyundai.carstate_ext import CarStateExt
from opendbc.sunnypilot.car.hyundai.escc import EsccCarStateBase
from opendbc.sunnypilot.car.hyundai.mads import MadsCarState
from opendbc.sunnypilot.car.hyundai.values import HyundaiFlagsSP

ButtonType = structs.CarState.ButtonEvent.Type

PREV_BUTTON_SAMPLES = 8
CLUSTER_SAMPLE_RATE = 20  # frames
STANDSTILL_THRESHOLD = 12 * 0.03125
BRICKPILOT_PHEV_CAN_LOGGER_VERSION = 33000

BRICKPILOT_PHEV_CANDIDATE_BITS = {
  0x0FA: 1 << 0,
  0x0E0: 1 << 1,
  0x0BA: 1 << 2,
  0x065: 1 << 3,
  0x10A: 1 << 4,
  0x120: 1 << 5,
  0x1C5: 1 << 6,
  0x310: 1 << 7,
  0x1A5: 1 << 8,
}
BRICKPILOT_PHEV_CANDIDATE_ADDRESSES = frozenset(BRICKPILOT_PHEV_CANDIDATE_BITS)

# Cancel button can sometimes be ACC pause/resume button, main button can also enable on some cars
ENABLE_BUTTONS = (Buttons.RES_ACCEL, Buttons.SET_DECEL, Buttons.CANCEL)
BUTTONS_DICT = {Buttons.RES_ACCEL: ButtonType.accelCruise, Buttons.SET_DECEL: ButtonType.decelCruise,
                Buttons.GAP_DIST: ButtonType.gapAdjustCruise, Buttons.CANCEL: ButtonType.cancel}


class CarState(CarStateBase, EsccCarStateBase, MadsCarState, CarStateExt):
  def __init__(self, CP, CP_SP):
    CarStateBase.__init__(self, CP, CP_SP)
    EsccCarStateBase.__init__(self)
    MadsCarState.__init__(self, CP, CP_SP)
    CarStateExt.__init__(self, CP, CP_SP)
    can_define = CANDefine(DBC[CP.carFingerprint][Bus.pt])

    self.cruise_buttons: deque = deque([Buttons.NONE] * PREV_BUTTON_SAMPLES, maxlen=PREV_BUTTON_SAMPLES)
    self.main_buttons: deque = deque([Buttons.NONE] * PREV_BUTTON_SAMPLES, maxlen=PREV_BUTTON_SAMPLES)
    self.lda_button = 0

    self.gear_msg_canfd = "ACCELERATOR" if CP.flags & HyundaiFlags.EV else \
                          "GEAR_ALT" if CP.flags & HyundaiFlags.CANFD_ALT_GEARS else \
                          "GEAR_ALT_2" if CP.flags & HyundaiFlags.CANFD_ALT_GEARS_2 else \
                          "GEAR_SHIFTER"
    if CP.flags & HyundaiFlags.CANFD:
      self.shifter_values = can_define.dv[self.gear_msg_canfd]["GEAR"]
    elif CP.flags & (HyundaiFlags.HYBRID | HyundaiFlags.EV):
      self.shifter_values = can_define.dv["ELECT_GEAR"]["Elect_Gear_Shifter"]
    elif self.CP.flags & HyundaiFlags.CLUSTER_GEARS:
      self.shifter_values = can_define.dv["CLU15"]["CF_Clu_Gear"]
    elif self.CP.flags & HyundaiFlags.TCU_GEARS:
      self.shifter_values = can_define.dv["TCU12"]["CUR_GR"]
    elif CP.flags & HyundaiFlags.FCEV:
      self.shifter_values = can_define.dv["EMS20"]["HYDROGEN_GEAR_SHIFTER"]
    else:
      self.shifter_values = can_define.dv["LVR12"]["CF_Lvr_Gear"]

    self.accelerator_msg_canfd = "ACCELERATOR" if CP.flags & HyundaiFlags.EV else \
                                 "ACCELERATOR_ALT" if CP.flags & HyundaiFlags.HYBRID else \
                                 "ACCELERATOR_BRAKE_ALT"
    self.cruise_btns_msg_canfd = "CRUISE_BUTTONS_ALT" if CP.flags & HyundaiFlags.CANFD_ALT_BUTTONS else \
                                 "CRUISE_BUTTONS"
    self.is_metric = False
    self.buttons_counter = 0

    self.cruise_info = {}

    # On some cars, CLU15->CF_Clu_VehicleSpeed can oscillate faster than the dash updates. Sample at 5 Hz
    self.cluster_speed = 0
    self.cluster_speed_counter = CLUSTER_SAMPLE_RATE

    self.params = CarControllerParams(CP)
    self._init_brickpilot_phev_can_logger()

  def _init_brickpilot_phev_can_logger(self) -> None:
    self.brickpilot_phev_candidate_data: dict[tuple[int, int], bytes] = {}
    self.brickpilot_phev_present_mask = 0
    self.brickpilot_phev_frame_update_mask = 0
    self.brickpilot_phev_candidate_source_mask = 0
    self.brickpilot_phev_fa_source_mask = 0
    self.brickpilot_phev_frame_counter = 0

  @staticmethod
  def _brickpilot_phev_source_bit(src: int) -> int:
    if src in (0, 1, 2):
      return 1 << src
    if src in (128, 129, 130):
      return 1 << (src - 125)
    return 1 << 7

  @staticmethod
  def _brickpilot_phev_u8(dat: bytes | None, idx: int) -> int:
    return int(dat[idx]) if dat is not None and len(dat) > idx else 0

  @classmethod
  def _brickpilot_phev_s8(cls, dat: bytes | None, idx: int) -> int:
    raw = cls._brickpilot_phev_u8(dat, idx)
    return raw - 256 if raw >= 128 else raw

  @staticmethod
  def _brickpilot_phev_s16_le(dat: bytes | None, idx: int) -> int:
    if dat is None or len(dat) <= idx + 1:
      return 0
    return int.from_bytes(dat[idx:idx + 2], byteorder="little", signed=True)

  def update_can_packets(self, can_packets) -> None:
    self.brickpilot_phev_frame_update_mask = 0
    for _, frames in can_packets:
      for address, dat, src in frames:
        if address not in BRICKPILOT_PHEV_CANDIDATE_ADDRESSES:
          continue

        bit = BRICKPILOT_PHEV_CANDIDATE_BITS[address]
        source_bit = self._brickpilot_phev_source_bit(int(src))
        payload = bytes(dat)
        self.brickpilot_phev_candidate_data[(int(address), int(src))] = payload
        self.brickpilot_phev_present_mask |= bit
        self.brickpilot_phev_frame_update_mask |= bit
        self.brickpilot_phev_candidate_source_mask |= source_bit
        if address == 0x0FA:
          self.brickpilot_phev_fa_source_mask |= source_bit
        self.brickpilot_phev_frame_counter += 1

  def _brickpilot_phev_can_buses(self) -> CanBus:
    return CanBus(self.CP)

  def _brickpilot_phev_select_candidate_frame(self, address: int) -> tuple[bytes | None, int]:
    CAN = self._brickpilot_phev_can_buses()
    if address == 0x310:
      source_priority = (1, 129, 0, 130, CAN.ECAN, CAN.ECAN + 128, 2, 128)
    else:
      source_priority = (0, 130, CAN.ECAN, CAN.ECAN + 128, 1, 129, 2, 128)

    seen: set[int] = set()
    for src in source_priority:
      if src in seen:
        continue
      seen.add(src)
      dat = self.brickpilot_phev_candidate_data.get((address, src))
      if dat is not None:
        return dat, src

    for (addr, src), dat in self.brickpilot_phev_candidate_data.items():
      if addr == address:
        return dat, src
    return None, 0

  def _populate_brickpilot_phev_can(self, ret_sp) -> None:
    CAN = self._brickpilot_phev_can_buses()
    ret_sp.brickpilotPhevCanLoggerVersion = BRICKPILOT_PHEV_CAN_LOGGER_VERSION
    ret_sp.brickpilotPhevCanCandidatePresentMask = int(self.brickpilot_phev_present_mask)
    ret_sp.brickpilotPhevCanFrameUpdateMask = int(self.brickpilot_phev_frame_update_mask)
    ret_sp.brickpilotPhevCanCandidateSourceMask = int(self.brickpilot_phev_candidate_source_mask)
    ret_sp.brickpilotPhevFaSourceMask = int(self.brickpilot_phev_fa_source_mask)
    ret_sp.brickpilotPhevCanFrameCounter = int(self.brickpilot_phev_frame_counter)
    ret_sp.brickpilotPhevHybridFlagSet = bool(self.CP.flags & HyundaiFlags.HYBRID)
    ret_sp.brickpilotPhevCanfdLkaSteerMsg = bool(self.CP.flags & HyundaiFlags.CANFD_LKA_STEER_MSG)
    ret_sp.brickpilotPhevCanfdEcanBus = int(CAN.ECAN)
    ret_sp.brickpilotPhevCanfdAcanBus = int(CAN.ACAN)
    ret_sp.brickpilotPhevCanfdCamBus = int(CAN.CAM)

    fa_dat, fa_src = self._brickpilot_phev_select_candidate_frame(0x0FA)
    ret_sp.brickpilotPhevSelectedSource = int(fa_src)
    ret_sp.brickpilotPhevFaB4U8 = self._brickpilot_phev_u8(fa_dat, 4)
    ret_sp.brickpilotPhevFaB4S8 = self._brickpilot_phev_s8(fa_dat, 4)

    fa_bus0 = self.brickpilot_phev_candidate_data.get((0x0FA, 0))
    fa_bus130 = self.brickpilot_phev_candidate_data.get((0x0FA, 130))
    ret_sp.brickpilotPhevFaB4U8Bus0 = self._brickpilot_phev_u8(fa_bus0, 4)
    ret_sp.brickpilotPhevFaB4S8Bus0 = self._brickpilot_phev_s8(fa_bus0, 4)
    ret_sp.brickpilotPhevFaB4U8Bus130 = self._brickpilot_phev_u8(fa_bus130, 4)
    ret_sp.brickpilotPhevFaB4S8Bus130 = self._brickpilot_phev_s8(fa_bus130, 4)
    ret_sp.brickpilotPhevFaB4MirrorConsistent = bool(fa_bus0 is not None and fa_bus130 is not None and
                                                     self._brickpilot_phev_u8(fa_bus0, 4) == self._brickpilot_phev_u8(fa_bus130, 4))

    e0_dat, _ = self._brickpilot_phev_select_candidate_frame(0x0E0)
    ba_dat, _ = self._brickpilot_phev_select_candidate_frame(0x0BA)
    c5_dat, _ = self._brickpilot_phev_select_candidate_frame(0x1C5)
    a5_dat, _ = self._brickpilot_phev_select_candidate_frame(0x1A5)
    a10_dat, _ = self._brickpilot_phev_select_candidate_frame(0x10A)
    a120_dat, _ = self._brickpilot_phev_select_candidate_frame(0x120)
    brake_dat, _ = self._brickpilot_phev_select_candidate_frame(0x065)
    adas_dat, _ = self._brickpilot_phev_select_candidate_frame(0x310)

    ret_sp.brickpilotPhevE0S16Byte08Le = self._brickpilot_phev_s16_le(e0_dat, 8)
    ret_sp.brickpilotPhevE0S16Byte10Le = self._brickpilot_phev_s16_le(e0_dat, 10)
    ret_sp.brickpilotPhevE0S16Byte16Le = self._brickpilot_phev_s16_le(e0_dat, 16)
    ret_sp.brickpilotPhevBaB11S8 = self._brickpilot_phev_s8(ba_dat, 11)
    ret_sp.brickpilotPhev1C5B5U8 = self._brickpilot_phev_u8(c5_dat, 5)
    ret_sp.brickpilotPhev10AB10U8 = self._brickpilot_phev_u8(a10_dat, 10)
    ret_sp.brickpilotPhev10AB18U8 = self._brickpilot_phev_u8(a10_dat, 18)
    ret_sp.brickpilotPhev120B3U8 = self._brickpilot_phev_u8(a120_dat, 3)
    ret_sp.brickpilotBrake065B9U8 = self._brickpilot_phev_u8(brake_dat, 9)
    ret_sp.brickpilotBrake065B10U8 = self._brickpilot_phev_u8(brake_dat, 10)
    ret_sp.brickpilotAdas310B17U8 = self._brickpilot_phev_u8(adas_dat, 17)
    ret_sp.brickpilotAdas310B18U8 = self._brickpilot_phev_u8(adas_dat, 18)
    ret_sp.brickpilotPhev1A5B14U8 = self._brickpilot_phev_u8(a5_dat, 14)
    ret_sp.brickpilotPhev1A5B15U8 = self._brickpilot_phev_u8(a5_dat, 15)
    ret_sp.brickpilotPhev1A5B16U8 = self._brickpilot_phev_u8(a5_dat, 16)
    ret_sp.brickpilotPhev1A5B17U8 = self._brickpilot_phev_u8(a5_dat, 17)

  def recent_button_interaction(self) -> bool:
    # On some newer model years, the CANCEL button acts as a pause/resume button based on the PCM state
    # To avoid re-engaging when openpilot cancels, check user engagement intention via buttons
    # Main button also can trigger an engagement on these cars
    return any(btn in ENABLE_BUTTONS for btn in self.cruise_buttons) or any(self.main_buttons)

  def update(self, can_parsers) -> tuple[structs.CarState, structs.CarStateSP]:
    cp = can_parsers[Bus.pt]
    cp_cam = can_parsers[Bus.cam]

    if self.CP.flags & HyundaiFlags.CANFD:
      return self.update_canfd(can_parsers)

    ret = structs.CarState()
    ret_sp = structs.CarStateSP()
    cp_cruise = cp_cam if self.CP.flags & HyundaiFlags.CAMERA_SCC else cp
    self.is_metric = cp.vl["CLU11"]["CF_Clu_SPEED_UNIT"] == 0
    speed_conv = CV.KPH_TO_MS if self.is_metric else CV.MPH_TO_MS

    ret.doorOpen = any([cp.vl["CGW1"]["CF_Gway_DrvDrSw"], cp.vl["CGW1"]["CF_Gway_AstDrSw"],
                        cp.vl["CGW2"]["CF_Gway_RLDrSw"], cp.vl["CGW2"]["CF_Gway_RRDrSw"]])

    ret.seatbeltUnlatched = cp.vl["CGW1"]["CF_Gway_DrvSeatBeltSw"] == 0

    self.parse_wheel_speeds(ret,
      cp.vl["WHL_SPD11"]["WHL_SPD_FL"],
      cp.vl["WHL_SPD11"]["WHL_SPD_FR"],
      cp.vl["WHL_SPD11"]["WHL_SPD_RL"],
      cp.vl["WHL_SPD11"]["WHL_SPD_RR"],
    )
    ret.standstill = cp.vl["WHL_SPD11"]["WHL_SPD_FL"] <= STANDSTILL_THRESHOLD and cp.vl["WHL_SPD11"]["WHL_SPD_RR"] <= STANDSTILL_THRESHOLD

    self.cluster_speed_counter += 1
    if self.cluster_speed_counter > CLUSTER_SAMPLE_RATE:
      self.cluster_speed = cp.vl["CLU15"]["CF_Clu_VehicleSpeed"]
      self.cluster_speed_counter = 0

      # Mimic how dash converts to imperial.
      # Sorento is the only platform where CF_Clu_VehicleSpeed is already imperial when not is_metric
      # TODO: CGW_USM1->CF_Gway_DrLockSoundRValue may describe this
      if not self.is_metric and self.CP.carFingerprint not in (CAR.KIA_SORENTO,):
        self.cluster_speed = math.floor(self.cluster_speed * CV.KPH_TO_MPH + CV.KPH_TO_MPH)

    ret.vEgoCluster = self.cluster_speed * speed_conv

    ret.steeringAngleDeg = cp.vl["SAS11"]["SAS_Angle"]
    ret.steeringRateDeg = cp.vl["SAS11"]["SAS_Speed"]
    ret.leftBlinker, ret.rightBlinker = self.update_blinker_from_lamp(
      50, cp.vl["CGW1"]["CF_Gway_TurnSigLh"], cp.vl["CGW1"]["CF_Gway_TurnSigRh"])
    ret.steeringTorque = cp.vl["MDPS12"]["CR_Mdps_StrColTq"]
    ret.steeringTorqueEps = cp.vl["MDPS12"]["CR_Mdps_OutTq"]
    ret.steeringPressed = self.update_steering_pressed(abs(ret.steeringTorque) > self.params.STEER_THRESHOLD, 5)
    ret.steerFaultTemporary = cp.vl["MDPS12"]["CF_Mdps_ToiUnavail"] != 0 or cp.vl["MDPS12"]["CF_Mdps_ToiFlt"] != 0

    # cruise state
    if self.CP.openpilotLongitudinalControl:
      # These are not used for engage/disengage since openpilot keeps track of state using the buttons
      ret.cruiseState.available = cp.vl["TCS13"]["ACCEnable"] == 0
      ret.cruiseState.enabled = cp.vl["TCS13"]["ACC_REQ"] == 1
      ret.cruiseState.standstill = False
      ret.cruiseState.nonAdaptive = False
    elif not self.CP_SP.flags & HyundaiFlagsSP.NON_SCC:
      ret.cruiseState.available = cp_cruise.vl["SCC11"]["MainMode_ACC"] == 1
      ret.cruiseState.enabled = cp_cruise.vl["SCC12"]["ACCMode"] != 0
      ret.cruiseState.standstill = cp_cruise.vl["SCC11"]["SCCInfoDisplay"] == 4.
      ret.cruiseState.nonAdaptive = cp_cruise.vl["SCC11"]["SCCInfoDisplay"] == 2.  # Shows 'Cruise Control' on dash
      ret.cruiseState.speed = cp_cruise.vl["SCC11"]["VSetDis"] * speed_conv

    # TODO: Find brake pressure
    ret.brake = 0
    ret.brakePressed = cp.vl["TCS13"]["DriverOverride"] == 2  # 2 includes regen braking by user on HEV/EV
    ret.brakeHoldActive = cp.vl["TCS15"]["AVH_LAMP"] == 2  # 0 OFF, 1 ERROR, 2 ACTIVE, 3 READY
    ret.parkingBrake = cp.vl["TCS13"]["PBRAKE_ACT"] == 1
    ret.espDisabled = cp.vl["TCS11"]["TCS_PAS"] == 1
    ret.espActive = cp.vl["TCS11"]["ABS_ACT"] == 1
    ret.accFaulted = cp.vl["TCS13"]["ACCEnable"] != 0  # 0 ACC CONTROL ENABLED, 1-3 ACC CONTROL DISABLED

    if self.CP.flags & (HyundaiFlags.HYBRID | HyundaiFlags.EV | HyundaiFlags.FCEV):
      if self.CP.flags & HyundaiFlags.FCEV:
        ret.gasPressed = cp.vl["FCEV_ACCELERATOR"]["ACCELERATOR_PEDAL"] > 0
      elif self.CP.flags & HyundaiFlags.HYBRID:
        ret.gasPressed = cp.vl["E_EMS11"]["CR_Vcu_AccPedDep_Pos"] > 0
      else:
        ret.gasPressed = cp.vl["E_EMS11"]["Accel_Pedal_Pos"] > 0
    else:
      ret.gasPressed = bool(cp.vl["EMS16"]["CF_Ems_AclAct"])

    # Gear Selection via Cluster - For those Kia/Hyundai which are not fully discovered, we can use the Cluster Indicator for Gear Selection,
    # as this seems to be standard over all cars, but is not the preferred method.
    if self.CP.flags & (HyundaiFlags.HYBRID | HyundaiFlags.EV):
      gear = cp.vl["ELECT_GEAR"]["Elect_Gear_Shifter"]
    elif self.CP.flags & HyundaiFlags.FCEV:
      gear = cp.vl["EMS20"]["HYDROGEN_GEAR_SHIFTER"]
    elif self.CP.flags & HyundaiFlags.CLUSTER_GEARS:
      gear = cp.vl["CLU15"]["CF_Clu_Gear"]
    elif self.CP.flags & HyundaiFlags.TCU_GEARS:
      gear = cp.vl["TCU12"]["CUR_GR"]
    else:
      gear = cp.vl["LVR12"]["CF_Lvr_Gear"]

    ret.gearShifter = self.parse_gear_shifter(self.shifter_values.get(gear))

    if (not self.CP.openpilotLongitudinalControl or self.CP.flags & HyundaiFlags.CAMERA_SCC) and not self.CP_SP.flags & HyundaiFlagsSP.NON_SCC:
      aeb_src = "FCA11" if self.CP.flags & HyundaiFlags.USE_FCA.value else "SCC12"
      aeb_sig = "FCA_CmdAct" if self.CP.flags & HyundaiFlags.USE_FCA.value else "AEB_CmdAct"
      aeb_warning = cp_cruise.vl[aeb_src]["CF_VSM_Warn"] != 0
      scc_warning = cp_cruise.vl["SCC12"]["TakeOverReq"] == 1  # sometimes only SCC system shows an FCW
      aeb_braking = cp_cruise.vl[aeb_src]["CF_VSM_DecCmdAct"] != 0 or cp_cruise.vl[aeb_src][aeb_sig] != 0
      ret.stockFcw = (aeb_warning or scc_warning) and not aeb_braking
      ret.stockAeb = aeb_warning and aeb_braking

    if self.CP.enableBsm:
      ret.leftBlindspot = cp.vl["LCA11"]["CF_Lca_IndLeft"] != 0
      ret.rightBlindspot = cp.vl["LCA11"]["CF_Lca_IndRight"] != 0

    # save the entire LKAS11 and CLU11
    self.lkas11 = copy.copy(cp_cam.vl["LKAS11"])
    self.clu11 = copy.copy(cp.vl["CLU11"])
    self.steer_state = cp.vl["MDPS12"]["CF_Mdps_ToiActive"]  # 0 NOT ACTIVE, 1 ACTIVE
    prev_cruise_buttons = self.cruise_buttons[-1]
    prev_main_buttons = self.main_buttons[-1]
    prev_lda_button = self.lda_button
    self.cruise_buttons.extend(cp.vl_all["CLU11"]["CF_Clu_CruiseSwState"])
    self.main_buttons.extend(cp.vl_all["CLU11"]["CF_Clu_CruiseSwMain"])
    if self.CP.flags & HyundaiFlags.HAS_LDA_BUTTON:
      self.lda_button = cp.vl["BCM_PO_11"]["LDA_BTN"]

    ret.buttonEvents = [*create_button_events(self.cruise_buttons[-1], prev_cruise_buttons, BUTTONS_DICT),
                        *create_button_events(self.main_buttons[-1], prev_main_buttons, {1: ButtonType.mainCruise}),
                        *create_button_events(self.lda_button, prev_lda_button, {1: ButtonType.lkas})]

    if self.CP.openpilotLongitudinalControl:
      ret.cruiseState.available = self.get_main_cruise(ret)

    CarStateExt.update(self, ret, ret_sp, can_parsers, speed_conv)

    ret.blockPcmEnable = not self.recent_button_interaction()

    # low speed steer alert hysteresis logic (only for cars with steer cut off above 10 m/s)
    if ret.vEgo < (self.CP.minSteerSpeed + 2.) and self.CP.minSteerSpeed > 10.:
      self.low_speed_alert = True
    if ret.vEgo > (self.CP.minSteerSpeed + 4.):
      self.low_speed_alert = False
    ret.lowSpeedAlert = self.low_speed_alert

    return ret, ret_sp

  def update_canfd(self, can_parsers) -> tuple[structs.CarState, structs.CarStateSP]:
    cp = can_parsers[Bus.pt]
    cp_cam = can_parsers[Bus.cam]

    ret = structs.CarState()
    ret_sp = structs.CarStateSP()

    self.is_metric = cp.vl["CRUISE_BUTTONS_ALT"]["DISTANCE_UNIT"] != 1
    speed_factor = CV.KPH_TO_MS if self.is_metric else CV.MPH_TO_MS

    if self.CP.flags & (HyundaiFlags.EV | HyundaiFlags.HYBRID):
      ret.gasPressed = cp.vl[self.accelerator_msg_canfd]["ACCELERATOR_PEDAL"] > 1e-5
    else:
      ret.gasPressed = bool(cp.vl[self.accelerator_msg_canfd]["ACCELERATOR_PEDAL_PRESSED"])

    ret.brakePressed = cp.vl["TCS"]["DriverBraking"] == 1

    ret.doorOpen = cp.vl["DOORS_SEATBELTS"]["DRIVER_DOOR"] == 1
    ret.seatbeltUnlatched = cp.vl["DOORS_SEATBELTS"]["DRIVER_SEATBELT"] == 0

    gear = cp.vl[self.gear_msg_canfd]["GEAR"]
    ret.gearShifter = self.parse_gear_shifter(self.shifter_values.get(gear))

    # TODO: figure out positions
    self.parse_wheel_speeds(ret,
      cp.vl["WHEEL_SPEEDS"]["WHL_SpdFLVal"],
      cp.vl["WHEEL_SPEEDS"]["WHL_SpdFRVal"],
      cp.vl["WHEEL_SPEEDS"]["WHL_SpdRLVal"],
      cp.vl["WHEEL_SPEEDS"]["WHL_SpdRRVal"],
    )
    ret.standstill = cp.vl["WHEEL_SPEEDS"]["WHL_SpdFLVal"] <= STANDSTILL_THRESHOLD and cp.vl["WHEEL_SPEEDS"]["WHL_SpdFRVal"] <= STANDSTILL_THRESHOLD and \
                     cp.vl["WHEEL_SPEEDS"]["WHL_SpdRLVal"] <= STANDSTILL_THRESHOLD and cp.vl["WHEEL_SPEEDS"]["WHL_SpdRRVal"] <= STANDSTILL_THRESHOLD

    ret.steeringRateDeg = cp.vl["STEERING_SENSORS"]["STEERING_RATE"]
    ret.steeringAngleDeg = cp.vl["STEERING_SENSORS"]["STEERING_ANGLE"]
    ret.steeringTorque = cp.vl["MDPS"]["MDPS_StrTqSnsrVal"]
    ret.steeringTorqueEps = cp.vl["MDPS"]["MDPS_OutTqVal"]
    ret.steeringPressed = self.update_steering_pressed(abs(ret.steeringTorque) > self.params.STEER_THRESHOLD, 5)
    ret.steerFaultTemporary = cp.vl["MDPS"]["MDPS_LkaFailSta"] != 0

    # TODO: alt signal usage may be described by cp.vl['BLINKERS']['USE_ALT_LAMP']
    left_blinker_sig, right_blinker_sig = "LEFT_LAMP", "RIGHT_LAMP"
    if self.CP.carFingerprint == CAR.HYUNDAI_KONA_EV_2ND_GEN:
      left_blinker_sig, right_blinker_sig = "LEFT_LAMP_ALT", "RIGHT_LAMP_ALT"
    ret.leftBlinker, ret.rightBlinker = self.update_blinker_from_lamp(50, cp.vl["BLINKERS"][left_blinker_sig],
                                                                      cp.vl["BLINKERS"][right_blinker_sig])
    if self.CP.enableBsm:
      ret.leftBlindspot = bool(cp.vl["ADAS_CMD_50_50ms"]["BCW_LtIndSta"])
      ret.rightBlindspot = bool(cp.vl["ADAS_CMD_50_50ms"]["BCW_RtIndSta"])

    # cruise state
    # CAN FD cars enable on main button press, set available if no TCS faults preventing engagement
    ret.cruiseState.available = cp.vl["TCS"]["ACCEnable"] == 0
    if self.CP.openpilotLongitudinalControl:
      # These are not used for engage/disengage since openpilot keeps track of state using the buttons
      ret.cruiseState.enabled = cp.vl["TCS"]["ACC_REQ"] == 1
      ret.cruiseState.standstill = False
    else:
      cp_cruise_info = cp_cam if self.CP.flags & HyundaiFlags.CANFD_CAMERA_SCC else cp
      ret.cruiseState.enabled = cp_cruise_info.vl["SCC_CONTROL"]["ACCMode"] in (1, 2)
      ret.cruiseState.standstill = cp_cruise_info.vl["SCC_CONTROL"]["CRUISE_STANDSTILL"] == 1
      ret.cruiseState.speed = cp_cruise_info.vl["SCC_CONTROL"]["VSetDis"] * speed_factor
      self.cruise_info = copy.copy(cp_cruise_info.vl["SCC_CONTROL"])

    # Manual Speed Limit Assist is a feature that replaces non-adaptive cruise control on EV CAN FD platforms.
    # It limits the vehicle speed, overridable by pressing the accelerator past a certain point.
    # The car will brake, but does not respect positive acceleration commands in this mode
    # TODO: find this message on ICE & HYBRID cars + cruise control signals (if exists)
    if self.CP.flags & HyundaiFlags.EV:
      ret.cruiseState.nonAdaptive = cp.vl["MANUAL_SPEED_LIMIT_ASSIST"]["MSLA_ENABLED"] == 1

    prev_cruise_buttons = self.cruise_buttons[-1]
    prev_main_buttons = self.main_buttons[-1]
    prev_lda_button = self.lda_button
    self.cruise_buttons.extend(cp.vl_all[self.cruise_btns_msg_canfd]["CRUISE_BUTTONS"])
    self.main_buttons.extend(cp.vl_all[self.cruise_btns_msg_canfd]["ADAPTIVE_CRUISE_MAIN_BTN"])
    self.lda_button = cp.vl[self.cruise_btns_msg_canfd]["LDA_BTN"]
    self.buttons_counter = cp.vl[self.cruise_btns_msg_canfd]["COUNTER"]
    ret.accFaulted = cp.vl["TCS"]["ACCEnable"] != 0  # 0 ACC CONTROL ENABLED, 1-3 ACC CONTROL DISABLED

    if self.CP.flags & HyundaiFlags.CANFD_LKA_STEER_MSG:
      self.lfa_block_msg = copy.copy(cp_cam.vl["CAM_0x362"] if self.CP.flags & HyundaiFlags.CANFD_LKA_STEER_MSG_ALT
                                          else cp_cam.vl["CAM_0x2a4"])

    MadsCarState.update_mads_canfd(self, ret, can_parsers)

    ret.buttonEvents = [*create_button_events(self.cruise_buttons[-1], prev_cruise_buttons, BUTTONS_DICT),
                        *create_button_events(self.main_buttons[-1], prev_main_buttons, {1: ButtonType.mainCruise}),
                        *create_button_events(self.lda_button, prev_lda_button, {1: ButtonType.lkas})]

    if self.CP.openpilotLongitudinalControl:
      ret.cruiseState.available = self.get_main_cruise(ret)

    CarStateExt.update_canfd_ext(self, ret, ret_sp, can_parsers, speed_factor)
    self._populate_brickpilot_phev_can(ret_sp)

    ret.blockPcmEnable = not self.recent_button_interaction()

    return ret, ret_sp

  def get_can_parsers_canfd(self, CP):
    msgs = []
    if not (CP.flags & HyundaiFlags.CANFD_ALT_BUTTONS):
      # TODO: this can be removed once we add dynamic support to vl_all
      msgs += [
        # this message is 50Hz but the ECU frequently stops transmitting for ~0.5s
        ("CRUISE_BUTTONS", 1)
      ]
    return {
      Bus.pt: CANParser(DBC[CP.carFingerprint][Bus.pt], msgs, CanBus(CP).ECAN),
      Bus.cam: CANParser(DBC[CP.carFingerprint][Bus.pt], [], CanBus(CP).CAM),
    }

  def get_can_parsers(self, CP, CP_SP):
    if CP.flags & HyundaiFlags.CANFD:
      return self.get_can_parsers_canfd(CP)

    return {
      Bus.pt: CANParser(DBC[CP.carFingerprint][Bus.pt], [], 0),
      Bus.cam: CANParser(DBC[CP.carFingerprint][Bus.pt], [], 2),
    }
