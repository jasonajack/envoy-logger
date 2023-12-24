import logging
from typing import Any, Dict

from prometheus_client import Gauge, Info, start_http_server

from envoy_logger.config import Config
from envoy_logger.envoy import Envoy
from envoy_logger.model import InverterSample, PowerSample, SampleData
from envoy_logger.sampling_engine import SamplingEngine

LOG = logging.getLogger("prometheus_sampling_engine")


class PrometheusSamplingEngine(SamplingEngine):
    prometheus_info: Dict[str, Info] = {}
    prometheus_gauges: Dict[str, Gauge] = {}

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
        prometheus_info = self._get_prometheus_info(
            f"envoy_{measurement_type}", f"Envoy {measurement_type} samples."
        )

        prometheus_info.info(
            _convert_to_info_dict({"line": line_index} | line_sample.asdict())
        )

        self._update_prometheus_line_sample_gauge(
            measurement_type=measurement_type,
            line_index=line_index,
            measurement_name="true_power",
            value=line_sample.wNow,
        )

        self._update_prometheus_line_sample_gauge(
            measurement_type=measurement_type,
            line_index=line_index,
            measurement_name="rms_current",
            value=line_sample.rmsCurrent,
        )

        self._update_prometheus_line_sample_gauge(
            measurement_type=measurement_type,
            line_index=line_index,
            measurement_name="rms_voltage",
            value=line_sample.rmsVoltage,
        )

        self._update_prometheus_line_sample_gauge(
            measurement_type=measurement_type,
            line_index=line_index,
            measurement_name="reactive_power",
            value=line_sample.reactPwr,
        )

        self._update_prometheus_line_sample_gauge(
            measurement_type=measurement_type,
            line_index=line_index,
            measurement_name="apparent_power",
            value=line_sample.apprntPwr,
        )

    def _get_prometheus_info(self, name: str, documentation: str) -> Info:
        prometheus_info = self.prometheus_info.get(name)
        if not prometheus_info:
            prometheus_info = Info(
                name=name,
                documentation=documentation,
            )

        self.prometheus_info[name] = prometheus_info

        return prometheus_info

    def _update_prometheus_line_sample_gauge(
        self,
        measurement_type: str,
        line_index: int,
        measurement_name: str,
        value: float,
    ) -> None:
        prometheus_gauge = self._get_prometheus_gauge(
            name=f"envoy_{measurement_type}_line{line_index}_{measurement_name}",
            documentation=f"Envoy {measurement_type} {measurement_name} samples for line{line_index}",
        )

        prometheus_gauge.set(value)

    def _get_prometheus_gauge(self, name: str, documentation: str) -> Gauge:
        prometheus_gauge = self.prometheus_gauges.get(name)
        if not prometheus_gauge:
            prometheus_gauge = Gauge(
                name=name,
                documentation=documentation,
            )

        self.prometheus_gauges[name] = prometheus_gauge

        return prometheus_gauge

    def _update_inverter_data_info(
        self, inverter_data: Dict[str, InverterSample]
    ) -> None:
        for serial, inverter_sample in inverter_data.items():
            self._update_inverter_sample(serial, inverter_sample)

    def _update_inverter_sample(
        self, serial: str, inverter_sample: InverterSample
    ) -> None:
        prometheus_info = self._get_prometheus_info(
            "envoy_inverter_sample", "Envoy inverter data."
        )

        prometheus_info.info(_convert_to_info_dict(inverter_sample.asdict()))

        self._update_prometheus_inverter_gauge(
            measurement_name="power",
            serial=inverter_sample.serial,
            value=inverter_sample.watts,
        )

    def _update_prometheus_inverter_gauge(
        self,
        measurement_name: str,
        serial: str,
        value: float,
    ) -> None:
        prometheus_gauge = self._get_prometheus_gauge(
            name=f"envoy_inverter_{measurement_name}_{serial}",
            documentation=f"Envoy inverter {measurement_name} for SN#{serial} samples",
        )

        prometheus_gauge.set(value)


def _convert_to_info_dict(any_dict: Dict[str, Any]) -> Dict[str, str]:
    return {key: str(val) for key, val in any_dict.items()}
