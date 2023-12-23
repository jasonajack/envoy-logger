import logging
import os
from argparse import ArgumentParser, FileType, Namespace
from typing import List, Optional

from envoy_logger.config import load_config
from envoy_logger.enphase_energy import EnphaseEnergy
from envoy_logger.envoy import Envoy
from envoy_logger.influxdb_sampling_engine import InfluxdbSamplingEngine
from envoy_logger.prometheus_sampling_engine import PrometheusSamplingEngine

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s [%(name)s]: %(message)s",
)


def parse_args(argv: Optional[List[str]] = None) -> Namespace:
    parser = ArgumentParser()

    parser.add_argument(
        "--config",
        type=FileType("r"),
        default=os.environ.get("ENVOY_LOGGER_CFG_PATH", "/etc/envoy-logger/config.yml"),
        help="Path to the configuration file.",
    )

    parser.add_argument(
        "--db",
        type=str,
        choices=["influxdb", "prometheus"],
        default=os.environ.get("ENVOY_LOGGER_DB", "influxdb"),
        help="The database backend to use.",
    )

    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)

    config = load_config(path=args.config.name, database=args.db)

    enphase_energy = EnphaseEnergy(
        email=config.enphase_email,
        password=config.enphase_password,
        envoy_serial=config.envoy_serial,
    )

    envoy = Envoy(url=config.envoy_url, enphase_energy=enphase_energy)

    match args.db:
        case "influxdb":
            sampling_loop = InfluxdbSamplingEngine(envoy=envoy, config=config)
            sampling_loop.run()
        case "prometheus":
            sampling_loop = PrometheusSamplingEngine(envoy=envoy, config=config)
            sampling_loop.run()
        case _:
            raise NotImplementedError(
                f"Database backend not yet implemented: {args.db}"
            )
