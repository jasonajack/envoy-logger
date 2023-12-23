import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import requests
import urllib3

from .enphase_energy import EnphaseEnergy
from .model import InverterSample, SampleData, parse_inverter_data

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

        if not self.session_id or elapsed > timedelta(hours = 12):
            self._login()
            self.session_id_last_update = now

        return self.session_id

    def _wait_for_next_cycle(self) -> None:
        # Determine how long until the next sample needs to be taken

        try:
            time.sleep(time_to_next)
        except KeyboardInterrupt:
            print("Exiting with Ctrl-C")
            sys.exit(0)

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
        ts = datetime.now(timezone.utc)
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
        return SampleData(json_data, ts)

    def get_inverter_data(self) -> Dict[str, InverterSample]:
        LOG.debug("Fetching inverter data")
        ts = datetime.now(timezone.utc)
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
        data = parse_inverter_data(json_data, ts)
        return data

    def get_inventory(self):
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
