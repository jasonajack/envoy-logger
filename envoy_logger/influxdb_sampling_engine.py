import logging
from datetime import date, datetime
from typing import Dict, List

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from envoy_logger.config import Config
from envoy_logger.envoy import Envoy
from envoy_logger.model import InverterSample, PowerSample, SampleData
from envoy_logger.sampling_engine import SamplingEngine

LOG = logging.getLogger("influxdb_sampling_engine")


class InfluxdbSamplingEngine(SamplingEngine):
    def __init__(self, envoy: Envoy, config: Config, interval_seconds: int = 5) -> None:
        super().__init__(envoy=envoy, interval_seconds=interval_seconds)

        self.config = config

        influxdb_client = InfluxDBClient(
            url=config.influxdb_url,
            token=config.influxdb_token,
            org=config.influxdb_org,
        )

        self.influxdb_write_api = influxdb_client.write_api(write_options=SYNCHRONOUS)
        self.influxdb_query_api = influxdb_client.query_api()

        # Used to track the transition to the next day for daily measurements
        self.todays_date = date.today()

    def run(self) -> None:
        while True:
            self.wait_for_next_cycle()
            self._collect_samples()

    def _collect_samples(self) -> None:
        power_data, inverter_data = self.collect_samples_with_retry()
        self._write_to_influxdb(power_data, inverter_data)

    def _write_to_influxdb(
        self, sample_data: SampleData, inverter_data: Dict[str, InverterSample]
    ) -> None:
        hr_points = self._get_high_rate_points(sample_data, inverter_data)
        lr_points = self._low_rate_points(sample_data)
        self.influxdb_write_api.write(
            bucket=self.config.influxdb_bucket_hr, record=hr_points
        )
        if lr_points:
            self.influxdb_write_api.write(
                bucket=self.config.influxdb_bucket_lr, record=lr_points
            )

    def _get_high_rate_points(
        self, sample_data: SampleData, inverter_data: Dict[str, InverterSample]
    ) -> List[Point]:
        points = []
        for line_index, line_sample in enumerate(
            sample_data.total_consumption.eim_line_samples
        ):
            p = self._idb_point_from_line("consumption", line_index, line_sample)
            points.append(p)
        for line_index, line_sample in enumerate(
            sample_data.total_production.eim_line_samples
        ):
            p = self._idb_point_from_line("production", line_index, line_sample)
            points.append(p)
        for line_index, line_sample in enumerate(
            sample_data.net_consumption.eim_line_samples
        ):
            p = self._idb_point_from_line("net", line_index, line_sample)
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

    def _low_rate_points(self, sample_data: SampleData) -> List[Point]:
        # First check if the day rolled over
        new_date = date.today()
        if self.todays_date == new_date:
            # still the same date. No summary
            return []

        # it is a new day!
        self.todays_date = new_date

        # Collect points that summarize prior day
        points = self._compute_daily_Wh_points(sample_data.ts)

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
