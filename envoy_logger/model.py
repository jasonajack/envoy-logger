from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class PowerSample:
    """
    A generic power sample
    """

    ts: datetime

    # Instantaneous measurements
    wNow: float
    rmsCurrent: float
    rmsVoltage: float
    reactPwr: float
    apprntPwr: float

    # Historical measurements (Today)
    whToday: float
    vahToday: float
    varhLagToday: float
    varhLeadToday: float

    # Historical measurements (Lifetime)
    whLifetime: float
    vahLifetime: float
    varhLagLifetime: float
    varhLeadLifetime: float

    # Historical measurements (Other)
    whLastSevenDays: float

    @staticmethod
    def create(power_data: Dict[str, float], ts: datetime) -> PowerSample:
        return PowerSample(
            ts=ts,
            # Instantaneous measurements
            wNow=power_data["wNow"],
            rmsCurrent=power_data["rmsCurrent"],
            rmsVoltage=power_data["rmsVoltage"],
            reactPwr=power_data["reactPwr"],
            apprntPwr=power_data["apprntPwr"],
            # Historical measurements (Today)
            whToday=power_data["whToday"],
            vahToday=power_data["vahToday"],
            varhLagToday=power_data["varhLagToday"],
            varhLeadToday=power_data["varhLeadToday"],
            # Historical measurements (Lifetime)
            whLifetime=power_data["whLifetime"],
            vahLifetime=power_data["vahLifetime"],
            varhLagLifetime=power_data["varhLagLifetime"],
            varhLeadLifetime=power_data["varhLeadLifetime"],
            # Historical measurements (Other)
            whLastSevenDays=power_data["whLastSevenDays"],
        )

    def __str__(self) -> str:
        return json.dumps(asdict(self), indent=1, default=str)

    def asdict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def pwrFactor(self) -> float:
        # calculate power factor locally for better precision
        if self.apprntPwr < 10.0:
            return 1.0
        return self.wNow / self.apprntPwr


@dataclass(frozen=True)
class SampleData:
    net_consumption: Optional[EIMSample]
    total_consumption: Optional[EIMSample]
    total_production: Optional[EIMSample]

    @staticmethod
    def create(sample_data: Dict[str, Any]) -> SampleData:
        net_consumption: Optional[EIMSample]
        total_consumption: Optional[EIMSample]
        total_production: Optional[EIMSample]

        for consumption_data in sample_data["consumption"]:
            if consumption_data["type"] == "eim":
                if consumption_data["measurementType"] == "net-consumption":
                    net_consumption = EIMSample.create(consumption_data)
                elif consumption_data["measurementType"] == "total-consumption":
                    total_consumption = EIMSample.create(consumption_data)

        for production_data in sample_data["production"]:
            if production_data["type"] == "eim":
                if production_data["measurementType"] == "production":
                    total_production = EIMSample.create(production_data)
            elif production_data["type"] == "inverters":
                # TODO: Parse this data too
                pass

        return SampleData(
            net_consumption=net_consumption,
            total_consumption=total_consumption,
            total_production=total_production,
        )

    def __str__(self) -> str:
        return json.dumps(asdict(self), indent=1, default=str)


@dataclass(frozen=True)
class EIMSample:
    """
    "EIM" measurement.

    Intentionally discard all total measurements.
    Envoy firmware has a bug where it miscalculates apparent power.
    Better to recalculate the values locally
    """

    eim_line_samples: List[PowerSample]

    @staticmethod
    def create(line_data: Dict[str, Any]) -> EIMSample:
        assert line_data["type"] == "eim"

        ts = datetime.fromtimestamp(line_data["readingTime"], tz=timezone.utc)

        eim_line_samples = [
            PowerSample.create(power_data=power_data, ts=ts)
            for power_data in line_data["lines"]
        ]

        return EIMSample(
            eim_line_samples=eim_line_samples,
        )

    def __str__(self) -> str:
        return json.dumps(asdict(self), indent=1, default=str)


@dataclass(frozen=True)
class InverterSample:
    ts: datetime
    serial: str
    watts: int

    @staticmethod
    def create(inverter_data: Dict[str, Any]) -> InverterSample:
        return InverterSample(
            ts=datetime.fromtimestamp(inverter_data["lastReportDate"], tz=timezone.utc),
            serial=inverter_data["serialNumber"],
            watts=inverter_data["lastReportWatts"],
        )

    def __str__(self) -> str:
        return json.dumps(asdict(self), indent=1, default=str)

    def asdict(self) -> Dict[str, Any]:
        return asdict(self)


def parse_inverter_data(data) -> Dict[str, InverterSample]:
    """
    Parse inverter JSON list and return a dictionary of inverter samples, keyed
    by their serial number.
    """
    inverters = {}

    for inverter_data in data:
        inverter = InverterSample.create(inverter_data)
        inverters[inverter.serial] = inverter

    return inverters


def filter_new_inverter_data(
    inverter_data: Dict[str, InverterSample], last_sample_timestamp: Optional[datetime]
) -> Dict[str, InverterSample]:
    """
    Inverter measurements only update if inverter actually sends a reported value.
    """
    filtered_inverter_data: Dict[str, InverterSample] = {}
    for serial, inverter_sample in inverter_data.items():
        if not last_sample_timestamp or inverter_sample.ts > last_sample_timestamp:
            filtered_inverter_data[serial] = inverter_sample

    return filtered_inverter_data
