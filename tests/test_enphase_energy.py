import base64
import json
import unittest

from unittest import mock

from requests import Response

from envoy_logger.enphase_energy import EnphaseEnergy


@mock.patch("requests.post")
class TestEnphaseEnergy(unittest.TestCase):
    def setUp(self):
        self.enphase_energy = EnphaseEnergy(
            email="foobar@test.com", password="password123", envoy_serial="serial123"
        )

    def test_get_token(self, mock_requests_post):
        mock_login_response = mock.Mock(Response)
        mock_login_response.json.return_value = {"session_id": "foobar123456"}

        token_segment = (
            base64.b64encode(bytes(json.dumps({"exp": 123456789}), "utf-8"))
        ).decode("utf-8")
        token = f"{token_segment}.{token_segment}.{token_segment}"

        mock_token_response = mock.Mock(Response)
        mock_token_response.text = token

        mock_requests_post.side_effect = [
            mock_login_response,
            mock_token_response,
            mock_login_response,
            mock_token_response,
        ]

        returned_token = self.enphase_energy.get_token()

        self.assertEqual(returned_token, token)


if __name__ == "__main__":
    unittest.main()
