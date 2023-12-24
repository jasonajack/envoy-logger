import unittest
from unittest import mock

from tests.sample_data import create_inverter_data, create_sample_data

from envoy_logger.model import SampleData, parse_inverter_data
from envoy_logger.prometheus_sampling_engine import PrometheusSamplingEngine


@mock.patch("envoy_logger.prometheus_sampling_engine.start_http_server")
@mock.patch("envoy_logger.envoy.Envoy")
@mock.patch("envoy_logger.config.Config")
class TestPrometheusSamplingEngine(unittest.TestCase):
    def test_collect_samples(
        self,
        mock_config,
        mock_envoy,
        mock_start_http_server,
    ):
        test_sample_data = SampleData.create(sample_data=create_sample_data())
        test_inverter_data = parse_inverter_data([create_inverter_data("foobar")])

        prometheus_sampling_engine = PrometheusSamplingEngine(
            envoy=mock_envoy, config=mock_config
        )

        prometheus_sampling_engine._update_power_data_info(sample_data=test_sample_data)
        prometheus_sampling_engine._update_inverter_data_info(
            inverter_data=test_inverter_data
        )


if __name__ == "__main__":
    unittest.main()
