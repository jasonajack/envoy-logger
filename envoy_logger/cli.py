import logging
import os
from argparse import ArgumentParser, FileType, Namespace

from .config import load_config
from .enphase_energy import EnphaseEnergy
from .envoy import Envoy
from .influxdb_sampling_engine import InfluxdbSamplingEngine

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s [%(name)s]: %(message)s",
)


def parse_args() -> Namespace:
    parser = ArgumentParser()

    parser.add_argument(
        "--config",
        type=FileType('r'),
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

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    config = load_config(args.config.name)

    enphase_energy = EnphaseEnergy(
        email=config.enphase_email,
        password=config.enphase_password,
        envoy_serial=config.envoy_serial,
    )

    envoy = Envoy(url=config.envoy_url, enphase_energy=enphase_energy)

    if args.db == 'influxdb':
        sampling_loop = InfluxdbSamplingEngine(envoy=envoy, config=config)
        sampling_loop.run()
    elif args.db == 'prometheus':
        raise NotImplementedError(f"Database backend not yet implemented: {args.db}")
    else:
        raise NotImplementedError(f"Database backend not yet implemented: {args.db}")
