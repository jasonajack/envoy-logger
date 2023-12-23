import argparse
import logging

from .config import load_config
from .enphase_energy import EnphaseEnergy
from .influxdb_sampling_engine import InfluxdbSamplingEngine

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s]: %(message)s"
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

    sampling_loop = InfluxdbSamplingEngine(enphase_energy, config)

    sampling_loop.run()
