# Enphase Envoy data logging service

![docker-ci](https://github.com/jasonajack/envoy-logger/actions/workflows/docker-build-ci.yml/badge.svg)

![docker-push](https://github.com/jasonajack/envoy-logger/actions/workflows/build-and-push.yml/badge.svg)

**This is a fork of https://github.com/amykyta3/envoy-logger**

Log your solar production locally and feed it into an InfluxDB or Prometheus time-series database.

This Python-based logging application handles the following:

- Automatically fetch the Envoy authentication token from enphaseenergy.com
- Authenticate a session with your local Envoy hardware
- Scrape solar production data:
  - Per-phase production, consumption, and net
  - Per-phase voltage, phase angle, etc.
  - Per-panel production

Once in the database, you can display the data on a Grafana dashboard.

## Screenshots

Dashboard Live:
![daily](docs/dashboard-live.png)

Dashboard Daily Totals:
![daily](docs/dashboard-daily-totals.png)

## Configure your database

Envoy data is written to a time-series database. This logger currently supports the following databases:

- InfluxDb
- Prometheus

This is where your time-series data gets stored. The logging script featured in this repository writes into this database, and the Grafana front-end reads from it.

### InfluxDB

You can pull the InfluxDB docker image from here: [influxdb](https://hub.docker.com/_/influxdb/)

An example compose:

```yaml
version: '3'

services:
  influxdb:
    image: influxdb:alpine
    container_name: influxdb
    volumes:
      - influxdb-data:/var/lib/influxdb2
      - influxdb-config:/etc/influxdb2
    ports:
      - 8086:8086
    restart: unless-stopped

volumes:
  influxdb-config:
  influxdb-data:
```

Once running, log in and configure your organization. Configure two buckets:

- envoy_low_rate
- envoy_high_rate

Create an access token for the logging script so that it is able to read/write the database. Optionally you may create an additional, separate read-only access token for Grafana to read from the database or simply reuse the read/write access token.

### Prometheus

You can pull the Prometheus docker image from here: [prom/prometheus](https://hub.docker.com/r/prom/prometheus/)

An example compose:

```yaml
version: '3'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    volumes:
      - prometheus-config:/etc/prometheus
      - prometheus-data:/prometheus
    ports:
      - 9090:9090
    restart: unless-stopped

volumes:
  prometheus-config:
  prometheus-data:
```

Unlike InfluxDB where the logger pushes data to the database, when configured for `prometheus` it listens on a port and the Prometheus database pulls data from the logger instead. You will need to make sure that wherever you are running your Prometheus database has connectivity to whatever server you are hosting the logger on, specifically on the port you define in your `config.yml`.

You will need to update your `prometheus.yml` configuration to add a new scraper:

```yaml
scrape_configs:
  - job_name: envoy-logger
    static_configs:
      - targets:
          - envoy_logger_hostname:1234
        labels:
          instance: envoy-logger
```

Update the target and change `envoy_logger_hostname:1234` to point to the server you are running the `envoy-logger` container and the port that it is listening on. Prometheus will periodically pull data (based on your configuration in `prometheus.yml`) from your logger.

## Build config.yml

Create a config file that describes your Envoy, how to connect to your database, and a few other things. Use this example file as a starting point: [/docs/config.yml](/docs/config.yml)

Locally test that the logging script can read from your Envoy, and push data to your database:

```bash
./install_python_deps.sh
./launcher.sh --config /path/to/your/config.yml --db influxdb|prometheus
```

If you've configured everything correctly you should see logs indicating authentication succeeded with both your Envoy and your database, and no error messages from the script. Login to your database server and start exploring the data using their "Data Explorer" tool. If it's working properly, you should start seeing the data flow in. I recommend that you poke around and get familiar with how the data is structured, since it will help you build queries for your dashboard later.

## Docker-compose

Once you have verified your configuration, create a `docker-compose.yml` as below:

```yaml
version: '3'

services:
  envoy_logger:
    image: ghcr.io/jasonajack/envoy-logger:latest
    container_name: envoy_logger
    environment:
      #ENVOY_LOGGER_CFG_PATH: /etc/envoy_logger/config.yml
      #ENVOY_LOGGER_DB: influxdb
      #ENVOY_LOGGER_DB: prometheus
    # Only needed if using prometheus
    #ports:
    #  - 1234:1234
    volumes:
      - /path/to/config.yml:/etc/envoy_logger/config.yml
      - /etc/localtime:/etc/localtime:ro
      - /etc/timezone:/etc/timezone:ro
    restart: unless-stopped
```

Run in your container service of choice or manually:

```bash
docker compose up -d
```

## Set up Grafana

Grafana is the front-end visualization tool where you can design dashboards to display your data. When you view a dashboard, Grafana pulls data from the database to display it.

Follow the guide here to setup Grafana: https://grafana.com/docs/grafana/latest/setup-grafana/installation/docker/

Once configured, add a connection to your database using the authentication token created earlier.

Start building dashboards from your data!

### InfluxDB

You will need to define some Flux queries to tell Grafana what data to fetch and how to organize it.

I have shared the queries I use as a reference: [/docs/flux_queries](/docs/flux_queries)

### Prometheus

You will need to configure your time series plots to combine lines as applicable.

For combined consumption, here is an example query that can yield total power consumption readings:
![daily](docs/prometheus_total_consumption_true_power_combined.png)

Look for the following metrics:

- envoy_net_consumption_line0_true_power
- envoy_net_consumption_line1_true_power
- envoy_total_consumption_line0_true_power
- envoy_total_consumption_line1_true_power
- envoy_total_production_line0_true_power
- envoy_total_production_line1_true_power

These metrics track the power consumed and produced by your solar system. Take some time to explore some of the other metrics available to understand what you can report back to your dashboard.
