import logging
import sys
from typing import Any, Dict, Optional

import yaml
from influxdb_client import Point

LOG = logging.getLogger("config")


class Config:
    def __init__(self, data: Dict[str, Any], database: str) -> None:
        try:
            self.enphase_email: str = data["enphaseenergy"]["email"]
            self.enphase_password: str = data["enphaseenergy"]["password"]

            self.envoy_serial = str(data["envoy"]["serial"])
            self.envoy_url: str = data["envoy"].get("url", "https://envoy.local")
            self.source_tag: str = data["envoy"].get("tag", "envoy")

            match database:
                case "influxdb":
                    self.influxdb_url: str = data["influxdb"]["url"]
                    self.influxdb_token: str = data["influxdb"]["token"]
                    self.influxdb_org: str = data["influxdb"].get("org", "home")
                case "prometheus":
                    self.prometheus_listening_port: int = data["prometheus"][
                        "listening_port"
                    ]
                case _:
                    raise NotImplementedError(
                        f"Database backend not yet implemented: {database}"
                    )

            bucket: Optional[str] = data["influxdb"].get("bucket", None)
            bucket_lr: Optional[str] = data["influxdb"].get("bucket_lr", None)
            bucket_hr: Optional[str] = data["influxdb"].get("bucket_hr", None)
            self.influxdb_bucket_lr: str = bucket_lr or bucket
            self.influxdb_bucket_hr: str = bucket_hr or bucket

            self.inverters: Dict[str, InverterConfig] = {}
            for serial, inverter_data in data.get("inverters", {}).items():
                serial = str(serial)
                self.inverters[serial] = InverterConfig(inverter_data, serial)

        except KeyError as e:
            LOG.error("Missing required config key: %s", e.args[0])
            sys.exit(1)

    def apply_tags_to_inverter_point(self, p: Point, serial: str) -> None:
        if serial in self.inverters.keys():
            self.inverters[serial].apply_tags_to_point(p)


class InverterConfig:
    def __init__(self, data, serial) -> None:
        self.serial = serial
        self.tags = data.get("tags", {})

    def apply_tags_to_point(self, p: Point) -> None:
        for k, v in self.tags.items():
            p.tag(k, v)


def load_config(path: str, database: str):
    LOG.info("Loading config %s for %s database", path, database)

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.load(f.read(), Loader=yaml.FullLoader)

    return Config(data, database)
