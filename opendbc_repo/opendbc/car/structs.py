from dataclasses import dataclass as _dataclass, field, is_dataclass
from enum import Enum, StrEnum as _StrEnum, auto
from typing import dataclass_transform, get_origin

import os
import capnp
from opendbc.car.common.basedir import BASEDIR

# TODO: remove car from cereal/__init__.py and always import from opendbc
try:
  from cereal import car
except ImportError:
  capnp.remove_import_hook()
  car = capnp.load(os.path.join(BASEDIR, "car.capnp"))

CarState = car.CarState
RadarData = car.RadarData
CarControl = car.CarControl
CarParams = car.CarParams

CarStateT = capnp.lib.capnp._StructModule
RadarDataT = capnp.lib.capnp._StructModule
CarControlT = capnp.lib.capnp._StructModule
CarParamsT = capnp.lib.capnp._StructModule

# sunnypilot structs

AUTO_OBJ = object()


def auto_field():
  return AUTO_OBJ


@dataclass_transform()
def auto_dataclass(cls=None, /, **kwargs):
  cls_annotations = cls.__dict__.get('__annotations__', {})
  for name, typ in cls_annotations.items():
    current_value = getattr(cls, name)
    if current_value is AUTO_OBJ:
      origin_typ = get_origin(typ) or typ
      if isinstance(origin_typ, str):
        raise TypeError(f"Forward references are not supported for auto_field: '{origin_typ}'. Use a default_factory with lambda instead.")
      elif origin_typ in (int, float, str, bytes, list, tuple, bool) or is_dataclass(origin_typ):
        setattr(cls, name, field(default_factory=origin_typ))
      elif issubclass(origin_typ, Enum):  # first enum is the default
        setattr(cls, name, field(default=next(iter(origin_typ))))
      else:
        raise TypeError(f"Unsupported type for auto_field: {origin_typ}")

  # TODO: use slots, this prevents accidentally setting attributes that don't exist
  return _dataclass(cls, **kwargs)


class StrEnum(_StrEnum):
  @staticmethod
  def _generate_next_value_(name, *args):
    # auto() defaults to name.lower()
    return name


@auto_dataclass
class CarParamsSP:
  flags: int = auto_field()        # flags for car specific quirks
  safetyParam: int = auto_field()  # flags for custom safety flags
  pcmCruiseSpeed: bool = auto_field()
  intelligentCruiseButtonManagementAvailable: bool = auto_field()
  enableGasInterceptor: bool = auto_field()

  neuralNetworkLateralControl: 'CarParamsSP.NeuralNetworkLateralControl' = field(default_factory=lambda: CarParamsSP.NeuralNetworkLateralControl())

  @auto_dataclass
  class NeuralNetworkLateralControl:
    model: 'CarParamsSP.NeuralNetworkLateralControl.Model' = field(default_factory=lambda: CarParamsSP.NeuralNetworkLateralControl.Model())
    fuzzyFingerprint: bool = auto_field()

    @auto_dataclass
    class Model:
      path: str = auto_field()
      name: str = auto_field()


@auto_dataclass
class ModularAssistiveDrivingSystem:
  state: 'ModularAssistiveDrivingSystem.ModularAssistiveDrivingSystemState' = field(
    default_factory=lambda: ModularAssistiveDrivingSystem.ModularAssistiveDrivingSystemState.disabled
  )
  enabled: bool = auto_field()
  active: bool = auto_field()
  available: bool = auto_field()

  class ModularAssistiveDrivingSystemState(StrEnum):
    disabled = auto()
    paused = auto()
    enabled = auto()
    softDisabling = auto()
    overriding = auto()


@auto_dataclass
class IntelligentCruiseButtonManagement:
  state: 'IntelligentCruiseButtonManagement.IntelligentCruiseButtonManagementState' = field(
    default_factory=lambda: IntelligentCruiseButtonManagement.IntelligentCruiseButtonManagementState.inactive
  )
  sendButton: 'IntelligentCruiseButtonManagement.SendButtonState' = field(
    default_factory=lambda: IntelligentCruiseButtonManagement.SendButtonState.none
  )
  vTarget: float = auto_field()

  class IntelligentCruiseButtonManagementState(StrEnum):
    inactive = auto()
    preActive = auto()
    increasing = auto()
    decreasing = auto()
    holding = auto()

  class SendButtonState(StrEnum):
    none = auto()
    increase = auto()
    decrease = auto()


@auto_dataclass
class LeadData:
  dRel: float = auto_field()
  yRel: float = auto_field()
  vRel: float = auto_field()
  aRel: float = auto_field()
  vLead: float = auto_field()
  dPath: float = auto_field()
  vLat: float = auto_field()
  vLeadK: float = auto_field()
  aLeadK: float = auto_field()
  fcw: bool = auto_field()
  status: bool = auto_field()
  aLeadTau: float = auto_field()
  modelProb: float = auto_field()
  radar: bool = auto_field()
  radarTrackId: int = auto_field()

  aLeadDEPRECATED: float = auto_field()


@auto_dataclass
class CarControlSP:
  mads: 'ModularAssistiveDrivingSystem' = field(default_factory=lambda: ModularAssistiveDrivingSystem())
  params: list['CarControlSP.Param'] = auto_field()
  leadOne: 'LeadData' = field(default_factory=lambda: LeadData())
  leadTwo: 'LeadData' = field(default_factory=lambda: LeadData())
  intelligentCruiseButtonManagement: 'IntelligentCruiseButtonManagement' = field(default_factory=lambda: IntelligentCruiseButtonManagement())

  @auto_dataclass
  class Param:
    key: str = auto_field()
    value: bytes = auto_field()
    type: 'CarControlSP.ParamType' = field(
      default_factory=lambda: CarControlSP.ParamType.string
    )

  class ParamType(StrEnum):
    string = auto()
    bool = auto()
    int = auto()
    float = auto()
    time = auto()
    json = auto()
    bytes = auto()


@auto_dataclass
class CarStateSP:
  speedLimit: float = auto_field()
  brickpilotPhevCanLoggerVersion: int = auto_field()
  brickpilotPhevCanCandidatePresentMask: int = auto_field()
  brickpilotPhevCanFrameUpdateMask: int = auto_field()
  brickpilotPhevCanCandidateSourceMask: int = auto_field()
  brickpilotPhevFaSourceMask: int = auto_field()
  brickpilotPhevSelectedSource: int = auto_field()
  brickpilotPhevCanFrameCounter: int = auto_field()
  brickpilotPhevHybridFlagSet: bool = auto_field()
  brickpilotPhevCanfdLkaSteerMsg: bool = auto_field()
  brickpilotPhevCanfdEcanBus: int = auto_field()
  brickpilotPhevCanfdAcanBus: int = auto_field()
  brickpilotPhevCanfdCamBus: int = auto_field()
  brickpilotPhevFaB4U8: int = auto_field()
  brickpilotPhevFaB4S8: int = auto_field()
  brickpilotPhevFaB4U8Bus0: int = auto_field()
  brickpilotPhevFaB4S8Bus0: int = auto_field()
  brickpilotPhevFaB4U8Bus130: int = auto_field()
  brickpilotPhevFaB4S8Bus130: int = auto_field()
  brickpilotPhevFaB4MirrorConsistent: bool = auto_field()
  brickpilotPhevE0S16Byte08Le: int = auto_field()
  brickpilotPhevE0S16Byte10Le: int = auto_field()
  brickpilotPhevE0S16Byte16Le: int = auto_field()
  brickpilotPhevBaB11S8: int = auto_field()
  brickpilotPhev1C5B5U8: int = auto_field()
  brickpilotPhev10AB10U8: int = auto_field()
  brickpilotPhev10AB18U8: int = auto_field()
  brickpilotPhev120B3U8: int = auto_field()
  brickpilotBrake065B9U8: int = auto_field()
  brickpilotBrake065B10U8: int = auto_field()
  brickpilotAdas310B17U8: int = auto_field()
  brickpilotAdas310B18U8: int = auto_field()
  brickpilotPhev1A5B14U8: int = auto_field()
  brickpilotPhev1A5B15U8: int = auto_field()
  brickpilotPhev1A5B16U8: int = auto_field()
  brickpilotPhev1A5B17U8: int = auto_field()
  brickpilotPhevBaB14U8: int = auto_field()
  brickpilotPhev06FB4U8: int = auto_field()
  brickpilotPhev06FB4S8: int = auto_field()
  brickpilotPhevFaB7U8: int = auto_field()
  brickpilotPhevFaB7S8: int = auto_field()
  brickpilotPhevFaB7U8Bus0: int = auto_field()
  brickpilotPhevFaB7S8Bus0: int = auto_field()
  brickpilotPhevFaB7U8Bus130: int = auto_field()
  brickpilotPhevFaB7S8Bus130: int = auto_field()
  brickpilotBrake065B3U8: int = auto_field()
  brickpilotBrake065B14U8: int = auto_field()
  brickpilotBrake065B11U8: int = auto_field()
  brickpilotBrake065B12U8: int = auto_field()
