from datetime import datetime, date
import time
from typing import List, Dict
import logging
import sys

from influxdb_client import WritePrecision, InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from .sampling_engine import SampleEngine

from .envoy import Envoy

from .enphase_energy import EnphaseEnergy


from .model import (
    SampleData,
    PowerSample,
    InverterSample,
)
from .config import Config

LOG = logging.getLogger("sampling_loop")


class InfluxdbSamplingEngine(SampleEngine):
    interval: int = 5

    def __init__(self, enphase_energy: EnphaseEnergy, config: Config) -> None:
        self.config = config
        self.envoy = Envoy(self.config.envoy_url, enphase_energy)

        influxdb_client = InfluxDBClient(
            url=config.influxdb_url,
            token=config.influxdb_token,
            org=config.influxdb_org,
        )
        self.influxdb_write_api = influxdb_client.write_api(write_options=SYNCHRONOUS)
        self.influxdb_query_api = influxdb_client.query_api()

        # Used to track the transition to the next day for daily measurements
        self.todays_date = date.today()

        self.prev_inverter_data = None

    def run(self):
        while True:
            self._wait_for_next_cycle()
            LOG.debug("Collecting samples.")

            power_data, inverter_data = self.collect_samples_with_retry()

            self._write_to_influxdb(power_data, inverter_data)

    def _wait_for_next_cycle(self) -> None:
        # Determine how long until the next sample needs to be taken
        now = datetime.now()
        time_to_next = self.interval - (now.timestamp() % self.interval)

        try:
            time.sleep(time_to_next)
        except KeyboardInterrupt:
            print("Exiting with Ctrl-C")
            sys.exit(0)

    def _write_to_influxdb(
        self, data: SampleData, inverter_data: Dict[str, InverterSample]
    ) -> None:
        hr_points = self._get_high_rate_points(data, inverter_data)
        lr_points = self._low_rate_points(data)
        self.influxdb_write_api.write(
            bucket=self.config.influxdb_bucket_hr, record=hr_points
        )
        if lr_points:
            self.influxdb_write_api.write(
                bucket=self.config.influxdb_bucket_lr, record=lr_points
            )

    def _get_high_rate_points(
        self, data: SampleData, inverter_data: Dict[str, InverterSample]
    ) -> List[Point]:
        points = []
        for i, line in enumerate(data.total_consumption.lines):
            p = self._idb_point_from_line("consumption", i, line)
            points.append(p)
        for i, line in enumerate(data.total_production.lines):
            p = self._idb_point_from_line("production", i, line)
            points.append(p)
        for i, line in enumerate(data.net_consumption.lines):
            p = self._idb_point_from_line("net", i, line)
            points.append(p)

        for inverter in inverter_data.values():
            p = self._point_from_inverter(inverter)
            points.append(p)

        return points

    def _idb_point_from_line(
        self, measurement_type: str, idx: int, data: PowerSample
    ) -> Point:
        p = Point(f"{measurement_type}-line{idx}")
        p.time(data.ts, WritePrecision.S)
        p.tag("source", self.config.source_tag)
        p.tag("measurement-type", measurement_type)
        p.tag("line-idx", idx)

        p.field("P", data.wNow)
        p.field("Q", data.reactPwr)
        p.field("S", data.apprntPwr)

        p.field("I_rms", data.rmsCurrent)
        p.field("V_rms", data.rmsVoltage)

        return p

    def _point_from_inverter(self, inverter: InverterSample) -> Point:
        p = Point(f"inverter-production-{inverter.serial}")
        p.time(inverter.ts, WritePrecision.S)
        p.tag("source", self.config.source_tag)
        p.tag("measurement-type", "inverter")
        p.tag("serial", inverter.serial)
        self.config.apply_tags_to_inverter_point(p, inverter.serial)

        p.field("P", inverter.watts)

        return p

    def _low_rate_points(self, data: SampleData) -> List[Point]:
        # First check if the day rolled over
        new_date = date.today()
        if self.todays_date == new_date:
            # still the same date. No summary
            return []

        # it is a new day!
        self.todays_date = new_date

        # Collect points that summarize prior day
        points = self._compute_daily_Wh_points(data.ts)

        return points

    def _compute_daily_Wh_points(self, ts: datetime) -> List[Point]:
        # Not using integral(interpolate:"linear") since it does not do what you
        # think it would mean. Without the "interoplation" arg, it still does
        # linear interpolation correctly.
        # https://github.com/influxdata/flux/issues/4782
        query = f"""
        from(bucket: "{self.config.influxdb_bucket_hr}")
            |> range(start: -24h, stop: 0h)
            |> filter(fn: (r) => r["source"] == "{self.config.source_tag}")
            |> filter(fn: (r) => r["_field"] == "P")
            |> integral(unit: 1h)
            |> keep(columns: ["_value", "line-idx", "measurement-type", "serial"])
            |> yield(name: "total")
        """
        result = self.influxdb_query_api.query(query=query)
        unreported_inverters = set(self.config.inverters.keys())
        points = []
        for table in result:
            for record in table.records:
                measurement_type = record["measurement-type"]
                if measurement_type == "inverter":
                    serial = record["serial"]
                    unreported_inverters.discard(serial)
                    p = Point(f"inverter-daily-summary-{serial}")
                    p.tag("serial", serial)
                    self.config.apply_tags_to_inverter_point(p, serial)
                else:
                    idx = record["line-idx"]
                    p = Point(f"{measurement_type}-daily-summary-line{idx}")
                    p.tag("line-idx", idx)

                p.time(ts, WritePrecision.S)
                p.tag("source", self.config.source_tag)
                p.tag("measurement-type", measurement_type)
                p.tag("interval", "24h")

                p.field("Wh", record.get_value())
                points.append(p)

        # If any inverters did not report in for the day, fill in a 0wh measurement
        for serial in unreported_inverters:
            p = Point(f"inverter-daily-summary-{serial}")
            p.tag("serial", serial)
            self.config.apply_tags_to_inverter_point(p, serial)
            p.time(ts, WritePrecision.S)
            p.tag("source", self.config.source_tag)
            p.tag("measurement-type", measurement_type)
            p.tag("interval", "24h")
            p.field("Wh", 0.0)
            points.append(p)

        return points
