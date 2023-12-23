import logging
import sys
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Optional

from requests import ConnectTimeout, ReadTimeout

from envoy_logger.envoy import Envoy
from envoy_logger.model import InverterSample, SampleData, filter_new_inverter_data

LOG = logging.getLogger("sampling_engine")


class SamplingEngine(ABC):
    prev_inverter_data: Optional[Dict[str, InverterSample]] = None

    def __init__(self, envoy: Envoy, interval_seconds: int = 5) -> None:
        self.envoy = envoy
        self.interval_seconds = interval_seconds

    @abstractmethod
    def run(self) -> None:
        pass

    def wait_for_next_cycle(self) -> None:
        # Determine how long until the next sample needs to be taken
        now = datetime.now()
        time_to_next = self.interval_seconds - (now.timestamp() % self.interval_seconds)

        try:
            time.sleep(time_to_next)
        except KeyboardInterrupt:
            print("Exiting with Ctrl-C")
            sys.exit(0)

    def collect_samples_with_retry(
        self, retries: int = 10, wait_seconds: float = 5.0
    ) -> SampleData | Dict[str, InverterSample]:
        for retry_loop in range(retries):
            try:
                power_data = self.get_power_data()
                inverter_data = self.get_inverter_data()

                LOG.debug(f"Sampled power data:\n{power_data}")
                LOG.debug(f"Sampled inverter data:\n{inverter_data}")
            except (ReadTimeout, ConnectTimeout):
                # Envoy gets REALLY MAD if you block it's access to enphaseenergy.com using a VLAN.
                # Its software gets hung up for some reason, and some requests will stall.
                # Allow envoy requests to timeout (and skip this sample iteration)
                LOG.warning("Envoy request timed out (%d/%d)", retry_loop + 1, retries)
                time.sleep(wait_seconds)
            else:
                return power_data, inverter_data

        # If we got this far it means we've timed out, raise an exception
        raise TimeoutError("Sample collection timed out.")

    def get_power_data(self) -> SampleData:
        return self.envoy.get_power_data()

    def get_inverter_data(self) -> Dict[str, InverterSample]:
        inverter_data = self.envoy.get_inverter_data()

        if self.prev_inverter_data is None:
            self.prev_inverter_data = inverter_data
            # Hard to know how stale inverter data is, so discard this sample
            # since I have nothing to compare to yet
            return {}

        # filter out stale inverter samples
        filtered_data = filter_new_inverter_data(inverter_data, self.prev_inverter_data)
        LOG.debug("Got %d unique inverter measurements", len(filtered_data))

        self.prev_inverter_data = inverter_data
        return filtered_data
