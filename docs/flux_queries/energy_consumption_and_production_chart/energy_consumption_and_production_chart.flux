grafanaTimeRange = (int(v: v.timeRangeStop) - int(v: v.timeRangeStart)) / 1000000000

aggregateWindowEvery = (t) =>
  if t <= 300 then
    5s
  else if t <= 900 then
    15s
  else if t <= 1800 then
    30s
  else if t <= 3600 then
    1m
  else if t <= 10800 then
    3m
  else if t <= 21600 then
    6m
  else if t <= 43200 then
    12m
  else
    24m

from(bucket: "envoy_high_rate")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["source"] == "power-meter")
  |> filter(fn: (r) => r["measurement-type"] == "consumption")
  |> filter(fn: (r) => r["_field"] == "P")
  |> aggregateWindow(every: aggregateWindowEvery(t: grafanaTimeRange), fn: mean, createEmpty: false)
  |> pivot(rowKey: ["_time"],
    columnKey: ["_measurement", "line-idx"],
    valueColumn: "_value")
  |> map(fn: (r) => ({ r with _value: r["consumption-line0_0"] + r["consumption-line1_1"] }))
  |> keep(columns: ["_time", "_value"])
  |> rename(columns: {_value: "consumption"})
  |> yield(name: "consumption")

from(bucket: "envoy_high_rate")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["source"] == "power-meter")
  |> filter(fn: (r) => r["measurement-type"] == "production")
  |> filter(fn: (r) => r["_field"] == "P")
  |> aggregateWindow(every: aggregateWindowEvery(t: grafanaTimeRange), fn: mean, createEmpty: false)
  |> pivot(rowKey: ["_time"],
    columnKey: ["_measurement", "line-idx"],
    valueColumn: "_value")
  |> map(fn: (r) => ({ r with _value: r["production-line0_0"] + r["production-line1_1"] }))
  |> keep(columns: ["_time", "_value"])
  |> rename(columns: {_value: "production"})
  |> yield(name: "production")
