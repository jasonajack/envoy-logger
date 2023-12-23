import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional

import requests
import urllib3

from envoy_logger.enphase_energy import EnphaseEnergy
from envoy_logger.model import InverterSample, SampleData, parse_inverter_data

# Local envoy access uses self-signed certificate. Ignore the warning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

LOG = logging.getLogger("envoy")


@dataclass
class Envoy:
    url: str
    enphase_energy: EnphaseEnergy
    session_id: Optional[str] = None
    session_id_last_update: datetime = datetime.now()

    def get_session_id(self) -> str:
        now = datetime.now()
        elapsed = now - self.session_id_last_update

        if not self.session_id or elapsed > timedelta(hours=12):
            self._login()
            self.session_id_last_update = now

        return self.session_id

    def _login(self) -> None:
        """
        Login to local envoy and return the session id
        """
        enphase_token = self.enphase_energy.get_token()
        headers = {
            "Authorization": f"Bearer {enphase_token}",
        }

        response = requests.get(
            f"{self.url}/auth/check_jwt",
            headers=headers,
            verify=False,
            timeout=30,
        )

        response.raise_for_status()
        self.session_id = response.cookies["sessionId"]
        LOG.info("Logged into envoy. SessionID: %s", self.session_id)

    def get_power_data(self) -> SampleData:
        LOG.debug("Fetching power data")
        cookies = {
            "sessionId": self.get_session_id(),
        }

        response = requests.get(
            f"{self.url}/production.json?details=1",
            cookies=cookies,
            verify=False,
            timeout=30,
        )

        response.raise_for_status()
        json_data = response.json()
        return SampleData.create(sample_data=json_data)

    def get_inverter_data(self) -> Dict[str, InverterSample]:
        LOG.debug("Fetching inverter data")
        cookies = {
            "sessionId": self.get_session_id(),
        }

        response = requests.get(
            f"{self.url}/api/v1/production/inverters",
            cookies=cookies,
            verify=False,
            timeout=30,
        )

        response.raise_for_status()
        json_data = response.json()
        data = parse_inverter_data(json_data)
        return data

    def get_inventory(self):
        LOG.debug("Fetching inventory")
        cookies = {
            "sessionId": self.get_session_id(),
        }

        response = requests.get(
            f"{self.url}/inventory.json?deleted=1",
            cookies=cookies,
            verify=False,
            timeout=30,
        )

        response.raise_for_status()
        json_data = response.json()
        # TODO: Convert to objects
        return json_data
