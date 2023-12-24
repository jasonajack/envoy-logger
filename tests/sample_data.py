from datetime import datetime, timezone
from typing import Any, Dict, List

from influxdb_client.client.flux_table import FluxRecord


def create_sample_data() -> Dict[str, Any]:
    return {
        "consumption": [
            _create_eim_sample("net-consumption"),
            _create_eim_sample("total-consumption"),
        ],
        "production": [
            _create_eim_sample("production"),
        ],
    }


def _create_eim_sample(measurement_type: str) -> Dict[str, Any]:
    return {
        "type": "eim",
        "readingTime": datetime.now(tz=timezone.utc).timestamp(),
        "measurementType": measurement_type,
        "lines": [
            _create_power_sample(),
            _create_power_sample(),
            _create_power_sample(),
        ],
    }


def _create_power_sample() -> Dict[str, float]:
    return {
        "wNow": 1.23,
        "rmsCurrent": 1.23,
        "rmsVoltage": 1.23,
        "reactPwr": 1.23,
        "apprntPwr": 1.23,
        "whToday": 1.23,
        "vahToday": 1.23,
        "varhLagToday": 1.23,
        "varhLeadToday": 1.23,
        "whLifetime": 1.23,
        "vahLifetime": 1.23,
        "varhLagLifetime": 1.23,
        "varhLeadLifetime": 1.23,
        "whLastSevenDays": 1.23,
    }


def create_inverter_data(serial_number: str = "foobar") -> Dict[str, Any]:
    return {
        "serialNumber": serial_number,
        "lastReportDate": datetime.now(tz=timezone.utc).timestamp(),
        "lastReportWatts": 123,
    }


def create_influxdb_records() -> List[Dict[str, Any]]:
    return [
        FluxRecord(
            {},
            {
                "measurement-type": "inverter",
                "serial": "foobar",
                "_value": 123.456,
            },
        ),
        FluxRecord(
            {},
            {
                "measurement-type": "consumption",
                "line-idx": 0,
                "_value": 123.456,
            },
        ),
        FluxRecord(
            {},
            {
                "measurement-type": "net",
                "line-idx": 0,
                "_value": 0.0,
            },
        ),
        FluxRecord(
            {},
            {
                "measurement-type": "production",
                "line-idx": 0,
                "_value": 123.456,
            },
        ),
    ]
