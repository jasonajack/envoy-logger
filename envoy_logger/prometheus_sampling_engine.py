import logging
from typing import Dict

from prometheus_client import Info, start_http_server

from envoy_logger.config import Config
from envoy_logger.envoy import Envoy
from envoy_logger.model import InverterSample, PowerSample, SampleData
from envoy_logger.sampling_engine import SamplingEngine

LOG = logging.getLogger("prometheus_sampling_engine")


class PrometheusSamplingEngine(SamplingEngine):
    prometheus_info: Dict[str, Info] = {}

    def __init__(self, envoy: Envoy, config: Config, interval_seconds: int = 5) -> None:
        super().__init__(envoy=envoy, interval_seconds=interval_seconds)

        self.config = config

        start_http_server(config.prometheus_listening_port)
        LOG.info(f"Listening on port {config.prometheus_listening_port}")

    def run(self) -> None:
        while True:
            self.wait_for_next_cycle()

            power_data, inverter_data = self.collect_samples_with_retry()

            self._update_power_data_info(sample_data=power_data)
            self._update_inverter_data_info(inverter_data=inverter_data)

    def _update_power_data_info(self, sample_data: SampleData) -> None:
        if sample_data.net_consumption:
            for line_index, line_sample in enumerate(
                sample_data.net_consumption.eim_line_samples
            ):
                self._update_line_sample("net_consumption", line_index, line_sample)

        if sample_data.total_consumption:
            for line_index, line_sample in enumerate(
                sample_data.total_consumption.eim_line_samples
            ):
                self._update_line_sample("total_consumption", line_index, line_sample)

        if sample_data.total_production:
            for line_index, line_sample in enumerate(
                sample_data.total_production.eim_line_samples
            ):
                self._update_line_sample("total_production", line_index, line_sample)

    def _update_line_sample(
        self, measurement_type: str, line_index: int, line_sample: PowerSample
    ) -> None:
        name = f"envoy_{measurement_type}_line{line_index}"
        prometheus_info = self._get_prometheus_info(name, measurement_type, line_index)
        prometheus_info.info(line_sample.asdict())

    def _get_prometheus_info(
        self, name: str, measurement_type: str, line_index: int
    ) -> Info:
        prometheus_info = self.prometheus_info.get(name)
        if not prometheus_info:
            prometheus_info = Info(
                name=name,
                documentation=f"Envoy {measurement_type} samples for line {line_index}",
            )

        self.prometheus_info[name] = prometheus_info

        return prometheus_info

    def _update_inverter_data_info(
        self, inverter_data: Dict[str, InverterSample]
    ) -> None:
        pass
