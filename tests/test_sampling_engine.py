import unittest
from unittest import mock

from requests import ConnectTimeout

from envoy_logger.model import InverterSample, SampleData
from envoy_logger.sampling_engine import SamplingEngine


class SamplingEngineChildClass(SamplingEngine):
    def run(self) -> None:
        raise NotImplementedError("Not implemented")


@mock.patch("envoy_logger.envoy.Envoy")
class TestSamplingEngine(unittest.TestCase):
    def test_collect_samples_with_retry(self, mock_envoy):
        mock_sample_data = mock.Mock(SampleData)
        mock_inverter_sample = mock.Mock(InverterSample)

        mock_inverter_data = {"foobar": mock_inverter_sample}

        mock_envoy.get_power_data.return_value = mock_sample_data
        mock_envoy.get_inverter_data.return_value = mock_inverter_data

        sampling_engine = SamplingEngineChildClass(envoy=mock_envoy)

        sample_data, inverter_data = sampling_engine.collect_samples_with_retry()

        self.assertEqual(
            sample_data,
            mock_sample_data,
        )
        self.assertEqual(
            inverter_data,
            mock_inverter_data,
        )

    def test_collect_samples_with_retry_timeout(self, mock_envoy):
        mock_envoy.get_power_data.side_effect = mock.Mock(
            side_effect=ConnectTimeout("foobar")
        )

        sampling_engine = SamplingEngineChildClass(envoy=mock_envoy)

        with self.assertRaises(TimeoutError) as ex:
            sampling_engine.collect_samples_with_retry(retries=3, wait_seconds=0.1)

        self.assertEqual(str(ex.exception), "Sample collection timed out.")


if __name__ == "__main__":
    unittest.main()
