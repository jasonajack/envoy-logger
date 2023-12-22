import logging
import argparse

from . import enphaseenergy
from .sampling_loop import SamplingLoop
from .config import load_config

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s]: %(message)s"
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config_path")
    args = parser.parse_args()

    config = load_config(args.config_path)

    envoy_token = enphaseenergy.get_token(
        config.enphase_email, config.enphase_password, config.envoy_serial
    )

    sampling_loop = SamplingLoop(envoy_token, config)

    sampling_loop.run()
