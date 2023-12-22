import unittest

from unittest import mock

from envoy_logger import cli


@mock.patch("envoy_logger.enphase_energy.EnphaseEnergy")
@mock.patch("envoy_logger.cli.SamplingLoop")
@mock.patch("sys.argv", ["--config", "./docs/config.yml"])
class TestCli(unittest.TestCase):
    def test_main_success(self, mock_sampling_loop, mock_get_token):
        mock_get_token.return_value = "foobar123456"
        mock_sampling_loop.run.return_value = None
        cli.main()


if __name__ == "__main__":
    unittest.main()
