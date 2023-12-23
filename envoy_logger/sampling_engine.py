import logging
from typing import Dict

from requests import ConnectTimeout, ReadTimeout

from .config import Config
from .enphase_energy import EnphaseEnergy
from .envoy import Envoy
from .model import InverterSample, SampleData, filter_new_inverter_data

LOG = logging.getLogger("sample_engine")


class SampleEngine:
    def __init__(self, enphase_energy: EnphaseEnergy, config: Config) -> None:
        self.config = config
        self.envoy = Envoy(self.config.envoy_url, enphase_energy)

    def collect_samples_with_retry(
        self, retries=10, wait=5
    ) -> SampleData | Dict[str, InverterSample]:
        for retry_loop in range(retries):
            try:
                power_data = self.get_power_data()
                inverter_data = self.get_inverter_data()
            except (ReadTimeout, ConnectTimeout):
                # Envoy gets REALLY MAD if you block it's access to enphaseenergy.com using a VLAN.
                # Its software gets hung up for some reason, and some requests will stall.
                # Allow envoy requests to timeout (and skip this sample iteration)
                logging.warning("Envoy request timed out (%d/10)", retry_loop + 1)
                pass
            else:
                return power_data, inverter_data

        # If we got this far it means we've timed out, raise an exception
        raise

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
