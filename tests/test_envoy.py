import unittest
from datetime import datetime, timezone
from unittest import mock

from requests import Response
from tests.sample_data import create_inverter_data, create_sample_data

from envoy_logger.envoy import Envoy
from envoy_logger.model import SampleData, parse_inverter_data


@mock.patch("envoy_logger.enphase_energy.EnphaseEnergy")
@mock.patch("requests.get")
@mock.patch("requests.post")
class TestEnvoy(unittest.TestCase):
    def test_get_session_id(
        self, mock_requests_post, mock_requests_get, mock_enphase_energy
    ):
        envoy = Envoy(url="http://envoy.local", enphase_energy=mock_enphase_energy)

        mock_enphase_energy.get_token.return_value = "foobar"

        mock_login_response = mock.Mock(Response)
        mock_login_response.cookies = {"sessionId": "foobar"}

        mock_requests_get.side_effect = [mock_login_response]

        session_id = envoy.get_session_id()

        self.assertEqual(session_id, "foobar")

    def test_get_power_data(
        self, mock_requests_post, mock_requests_get, mock_enphase_energy
    ):
        envoy = Envoy(url="http://envoy.local", enphase_energy=mock_enphase_energy)

        mock_enphase_energy.get_token.return_value = "foobar"

        mock_login_response = mock.Mock(Response)
        mock_login_response.cookies = {"sessionId": "foobar"}

        power_data = create_sample_data()
        mock_power_data_response = mock.Mock(Response)
        mock_power_data_response.json.return_value = power_data

        mock_requests_get.side_effect = [mock_login_response, mock_power_data_response]

        sample_data = envoy.get_power_data()
        expected_sample_data = SampleData(power_data, datetime.now(timezone.utc))

        self.assertEqual(
            len(sample_data.net_consumption.lines),
            len(expected_sample_data.net_consumption.lines),
        )
        self.assertEqual(
            len(sample_data.total_consumption.lines),
            len(expected_sample_data.total_consumption.lines),
        )
        self.assertEqual(
            len(sample_data.total_production.lines),
            len(expected_sample_data.total_production.lines),
        )

    def test_get_inverter_data(
        self, mock_requests_post, mock_requests_get, mock_enphase_energy
    ):
        envoy = Envoy(url="http://envoy.local", enphase_energy=mock_enphase_energy)

        mock_enphase_energy.get_token.return_value = "foobar"

        mock_login_response = mock.Mock(Response)
        mock_login_response.cookies = {"sessionId": "foobar"}

        test_inverter_data = [
            create_inverter_data(),
            create_inverter_data(),
        ]
        mock_inverter_data_response = mock.Mock(Response)
        mock_inverter_data_response.json.return_value = test_inverter_data

        mock_requests_get.side_effect = [
            mock_login_response,
            mock_inverter_data_response,
        ]

        inverter_data = envoy.get_inverter_data()
        expected_inverter_data = parse_inverter_data(
            test_inverter_data, datetime.now(timezone.utc)
        )

        self.assertEqual(
            len(inverter_data),
            len(expected_inverter_data),
        )
        self.assertEqual(
            inverter_data["foobar"].watts,
            expected_inverter_data["foobar"].watts,
        )


if __name__ == "__main__":
    unittest.main()
