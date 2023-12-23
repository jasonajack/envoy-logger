import unittest
from unittest import mock

from envoy_logger import cli


@mock.patch("envoy_logger.enphase_energy.EnphaseEnergy")
@mock.patch("envoy_logger.cli.InfluxdbSamplingEngine")
class TestCli(unittest.TestCase):
    def test_main_success(self, mock_sampling_loop, mock_enphase_energy):
        mock_sampling_loop.run.return_value = None
        cli.main(argv=["--config", "./docs/config.yml", "--db", "influxdb"])


if __name__ == "__main__":
    unittest.main()
