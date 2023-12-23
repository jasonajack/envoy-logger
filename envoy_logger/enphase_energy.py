import base64
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import requests

LOG = logging.getLogger("enphaseenergy")


@dataclass
class EnphaseEnergy:
    email: str
    password: str
    envoy_serial: str
    token: Optional[str] = None

    def get_token(self) -> str:
        if self.token is None:
            self.token = self._get_new_token()

        exp = self._token_expiration_date()
        time_left = exp - datetime.now()
        if time_left < timedelta(days=1):
            LOG.info("Token will expire soon. Getting a new one")
            self.token = self._get_new_token()

        return self.token

    def _get_new_token(self) -> str:
        """
        Login to enphaseenergy.com and return an access token for the envoy.
        """
        session_id = self._login_enphaseenergy()

        LOG.info("Downloading new access token for envoy S/N: %s", self.envoy_serial)

        json_data = {
            "session_id": session_id,
            "serial_num": self.envoy_serial,
            "username": self.email,
        }

        response = requests.post(
            "https://entrez.enphaseenergy.com/tokens",
            json=json_data,
            timeout=30,
        )

        response.raise_for_status()
        return response.text

    def _login_enphaseenergy(self) -> str:
        LOG.info("Logging into enphaseenergy.com as %s", self.email)

        files = {
            "user[email]": (None, self.email),
            "user[password]": (None, self.password),
        }
        url = "https://enlighten.enphaseenergy.com/login/login.json?"

        response = requests.post(
            url,
            files=files,
            timeout=30,
        )

        response.raise_for_status()
        resp = response.json()
        return resp["session_id"]

    def _token_expiration_date(self) -> datetime:
        jwt = {}

        # The token is a string containing two base64 encoded segments delimited by '.', the third token
        # is not considered here.
        # The first two segments parse to JSON and contain information about the logged in user.
        #
        # Example response here:
        # {'kid': 'tokenid', 'typ': 'JWT', 'alg': 'ES256', 'aud': 'account#', 'iss': 'Entrez',
        #   'enphaseUser': 'owner', 'exp': 1732674920, 'iat': 1701138920, 'jti': 'something',
        #   'username': 'someuser@test.com'}
        #
        # We are specifically looking to extract 'exp'
        for token_segment in self.token.split(".")[0:2]:
            # Append equals to the end of the segment so it can be decoded properly by b64decode
            res = len(token_segment) % 4
            if res != 0:
                token_segment += "=" * (4 - res)

            segment_json = base64.b64decode(token_segment)
            jwt.update(json.loads(segment_json))

        exp = datetime.fromtimestamp(jwt["exp"])

        return exp
