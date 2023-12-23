import argparse
import logging
import os

from .config import load_config
from .enphase_energy import EnphaseEnergy
from .envoy import Envoy
from .influxdb_sampling_engine import InfluxdbSamplingEngine

logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s [%(name)s]: %(message)s",
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config_path")
    args = parser.parse_args()

    config = load_config(args.config_path)

    enphase_energy = EnphaseEnergy(
        email=config.enphase_email,
        password=config.enphase_password,
        envoy_serial=config.envoy_serial,
    )

    envoy = Envoy(url=config.envoy_url, enphase_energy=enphase_energy)

    sampling_loop = InfluxdbSamplingEngine(envoy=envoy, config=config)

    sampling_loop.run()
