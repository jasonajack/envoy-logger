from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timedelta
import json
import base64
import os
import logging

import requests
from appdirs import user_cache_dir

LOG = logging.getLogger("enphaseenergy")


@dataclass(frozen=True)
class EnphaseEnergy:
    email: str
    password: str
    envoy_serial: str

    def get_token(self) -> str:
        """
        Do whatever it takes to get a token
        """
        token = self._get_cached_token()
        if token is None:
            # cached token does not exist. Get a new one
            token = self._get_new_token()
            self._save_token_to_cache(token)

        exp = self._token_expiration_date(token)
        time_left = exp - datetime.now()
        if time_left < timedelta(days=1):
            # token will expire soon. get a new one
            LOG.info("Token will expire soon. Getting a new one")
            token = self._get_new_token()
            self._save_token_to_cache(token)

        return token

    def _get_cached_token(self) -> Optional[str]:
        path = self._get_token_cache_path()
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            LOG.info("Using cached token from: %s", path)
            return f.read()

    def _get_token_cache_path(self) -> str:
        return os.path.join(
            user_cache_dir("enphase-envoy"), f"{self.envoy_serial}.token"
        )

    def _get_new_token(self) -> str:
        """
        Login to enphaseenergy.com and return an access token for the envoy.
        """
        session_id = self._login_enphaseenergy()

        LOG.info("Downloading new access token for envoy S/N: %s", self.envoy_serial)
        # Get the token
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
        # Login and get session ID
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

    def _save_token_to_cache(self, token: str) -> None:
        path = self._get_token_cache_path()
        LOG.info("Caching token to: %s", path)
        parent_dir = os.path.dirname(path)
        if not os.path.exists(parent_dir):
            os.mkdir(parent_dir)
        with open(path, "w", encoding="utf-8") as f:
            f.write(token)

    def _token_expiration_date(self, token: str) -> datetime:
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
        for token_segment in token.split(".")[0:2]:
            # Append equals to the end of the segment so it can be decoded properly by b64decode
            res = len(token_segment) % 4
            if res != 0:
                token_segment += "=" * (4 - res)

            segment_json = base64.b64decode(token_segment)
            jwt.update(json.loads(segment_json))

        exp = datetime.fromtimestamp(jwt["exp"])

        return exp
