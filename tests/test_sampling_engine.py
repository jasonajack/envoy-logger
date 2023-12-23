import unittest
from unittest import mock

from requests import ConnectTimeout

from envoy_logger.model import InverterSample, SampleData
from envoy_logger.sampling_engine import SampleEngine


@mock.patch("envoy_logger.envoy.Envoy")
class TestSamplingEnginer(unittest.TestCase):
    def test_collect_samples_with_retry(self, mock_envoy):
        mock_sample_data = mock.Mock(SampleData)
        mock_inverter_sample = mock.Mock(InverterSample)

        mock_inverter_data = {"foobarA": mock_inverter_sample}

        mock_envoy.get_power_data.return_value = mock_sample_data
        mock_envoy.get_inverter_data.return_value = mock_inverter_data

        sample_engine = SampleEngine(envoy=mock_envoy)

        # Grab first sample; inverter_data will be empty here because it only returns on the second scan from start
        sample_data, inverter_data = sample_engine.collect_samples_with_retry()

        self.assertEqual(
            sample_data,
            mock_sample_data,
        )
        self.assertEqual(
            len(inverter_data),
            0,
        )

        # Grab second sample; this should return the inverter sample
        mock_inverter_data = {"foobarB": mock_inverter_sample}
        mock_envoy.get_inverter_data.return_value = mock_inverter_data

        sample_data, inverter_data = sample_engine.collect_samples_with_retry()

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

        sample_engine = SampleEngine(envoy=mock_envoy)

        with self.assertRaises(TimeoutError) as ex:
            sample_engine.collect_samples_with_retry(retries=3, wait_seconds=0.1)

        self.assertEqual(str(ex.exception), "Sample collection timed out.")


if __name__ == "__main__":
    unittest.main()
