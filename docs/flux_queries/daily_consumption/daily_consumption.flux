import "date"

from(bucket: "envoy_high_rate")
  |> range(start: date.sub(d: 24h, from: v.timeRangeStop), stop: v.timeRangeStop)
  |> filter(fn: (r) => r["source"] == "power-meter")
  |> filter(fn: (r) => r["measurement-type"] == "consumption")
  |> filter(fn: (r) => r["_field"] == "P")
  |> aggregateWindow(every: 1h, fn: mean)
  |> pivot(rowKey: ["_time"],
    columnKey: ["_measurement", "line-idx"],
    valueColumn: "_value")
  |> map(fn: (r) => ({ r with _value: r["consumption-line0_0"] + r["consumption-line1_1"] }))
  |> keep(columns: ["_time", "_start", "_stop", "_value"])
  |> integral(unit: 1h)
  |> yield(name: "daily consumption")
