from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional
import logging

LOG = logging.getLogger("model")


@dataclass
class PowerSample:
    """
    A generic power sample
    """

    def __init__(self, data, ts: datetime) -> None:
        self.ts = ts

        # Instantaneous measurements
        self.wNow: float = data["wNow"]
        self.rmsCurrent: float = data["rmsCurrent"]
        self.rmsVoltage: float = data["rmsVoltage"]
        self.reactPwr: float = data["reactPwr"]
        self.apprntPwr: float = data["apprntPwr"]

        # Historical measurements (Today)
        self.whToday: float = data["whToday"]
        self.vahToday: float = data["vahToday"]
        self.varhLagToday: float = data["varhLagToday"]
        self.varhLeadToday: float = data["varhLeadToday"]

        # Historical measurements (Lifetime)
        self.whLifetime: float = data["whLifetime"]
        self.vahLifetime: float = data["vahLifetime"]
        self.varhLagLifetime: float = data["varhLagLifetime"]
        self.varhLeadLifetime: float = data["varhLeadLifetime"]

        # Historical measurements (Other)
        self.whLastSevenDays: float = data["whLastSevenDays"]

    @property
    def pwrFactor(self) -> float:
        # calculate power factor locally for better precision
        if self.apprntPwr < 10.0:
            return 1.0
        return self.wNow / self.apprntPwr


@dataclass
class EIMSample:
    """
    "EIM" measurement.

    Intentionally discard all total measurements.
    Envoy firmware has a bug where it miscalculates apparent power.
    Better to recalculate the values locally
    """

    def __init__(self, data, ts: datetime) -> None:
        assert data["type"] == "eim"

        # Do not use JSON data's timestamp. Envoy's clock is wrong
        self.ts = ts

        self.lines = []
        for line_data in data["lines"]:
            line = EIMLineSample(self, line_data)
            self.lines.append(line)

        LOG.debug(
            f"Sampled {len(self.lines)} power lines of type: {data['measurementType']}"
        )


@dataclass
class EIMLineSample(PowerSample):
    """
    Sample for a Single "EIM" line sensor
    """

    def __init__(self, parent: EIMSample, data) -> None:
        self.parent = parent
        super().__init__(data, parent.ts)


@dataclass
class SampleData:
    def __init__(self, data, ts: datetime) -> None:
        # Do not use JSON data's timestamp. Envoy's clock is wrong
        self.ts = ts

        self.net_consumption: Optional[EIMSample] = None
        self.total_consumption: Optional[EIMSample] = None
        self.total_production: Optional[EIMSample] = None

        for consumption_data in data["consumption"]:
            if consumption_data["type"] == "eim":
                if consumption_data["measurementType"] == "net-consumption":
                    self.net_consumption = EIMSample(consumption_data, self.ts)
                if consumption_data["measurementType"] == "total-consumption":
                    self.total_consumption = EIMSample(consumption_data, self.ts)

        for production_data in data["production"]:
            if production_data["type"] == "eim":
                if production_data["measurementType"] == "production":
                    self.total_production = EIMSample(production_data, self.ts)
            if production_data["type"] == "inverters":
                # TODO: Parse this data too
                pass


@dataclass
class InverterSample:
    def __init__(self, data, ts: datetime) -> None:
        # envoy time is not particularly accurate. Use my own ts
        self.ts = ts

        self.serial: str = data["serialNumber"]
        self.report_ts: int = data["lastReportDate"]
        self.watts: int = data["lastReportWatts"]


def parse_inverter_data(data, ts: datetime) -> Dict[str, InverterSample]:
    """
    Parse inverter JSON list and return a dictionary of inverter samples, keyed
    by their serial number
    """
    inverters = {}

    for inverter_data in data:
        inverter = InverterSample(inverter_data, ts)
        inverters[inverter.serial] = inverter

    return inverters


def filter_new_inverter_data(
    new_data: Dict[str, InverterSample], prev_data: Dict[str, InverterSample]
) -> Dict[str, InverterSample]:
    """
    Inverter measurements only update if inverter actually sends a reported
    value.
    Compare against a prior sample, and return a new dict of inverters samples
    that only contains the unique measurements
    """
    unique_inverters: Dict[str, InverterSample] = {}
    for serial, inverter in new_data.items():
        if serial not in prev_data.keys():
            unique_inverters[serial] = inverter
            continue

        if inverter.report_ts != prev_data[serial].report_ts:
            unique_inverters[serial] = inverter
            continue

    return unique_inverters
