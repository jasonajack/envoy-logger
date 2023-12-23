# Enphase Envoy data logging service

![docker-ci](https://github.com/jasonajack/envoy-logger/actions/workflows/docker-build-ci.yml/badge.svg)

![docker-push](https://github.com/jasonajack/envoy-logger/actions/workflows/build-and-push.yml/badge.svg)

Log your solar production locally and feed it into an InfluxDB time-series database.

This Python-based logging application handles the following:

- Automatically fetch the Envoy authentication token from enphaseenergy.com
- Authenticate a session with your local Envoy hardware
- Scrape solar production data:
  - Per-phase production, consumption, and net
  - Per-phase voltage, phase angle, etc.
  - Per-panel production

Once in InfluxDB, you can display the data on a Grafana dashboard.

## Screenshots

Dashboard Live:
![daily](docs/dashboard-live.png)

Dashboard Daily Totals:
![daily](docs/dashboard-daily-totals.png)

## InfluxDB

This is where your time-series data gets stored. The logging script featured in this repository writes into this database, and the Grafana front-end reads from it.

You can pull the InfluxDB docker image from here: https://hub.docker.com/\_/influxdb/

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
      - 1086:8086
    restart: unless-stopped

volumes:
  influxdb-config:
  influxdb-data:
```

Once running, log in and configure your organization. Configure two buckets:

- envoy_low_rate
- envoy_high_rate

Create an access token for the logging script so that it is able to read/write the database. Optionally you may create an additional, separate read-only access token for Grafana to read from the database or simply reuse the read/write access token.

## Build config.yml

Create a config file that describes your Envoy, how to connect to InfluxDB, and a few other things. Use this example file as a starting point: [/docs/config.yml](/docs/config.yml)

Locally test that the logging script can read from your Envoy, and push data to InfluxDB:

```bash
./install_python_deps.sh
ENVOY_LOGGER_CFG_PATH=path/tp/your/config.yml ./launcher.sh
```

If you've configured everything correctly you should see logs indicating authentication succeeded with both your Envoy and InfluxDB, and no error messages from the script. Login to your InfluxDB server and start exploring the data using their "Data Explorer" tool. If it's working properly, you should start seeing the data flow in. I recommend that you poke around and get familiar with how the data is structured, since it will help you build queries for your dashboard later.

## Docker-compose

Once you have verified your configuration, create a `docker-compose.yml` as below:

```yaml
version: '3'

services:
  envoy_logger:
    image: jasonajack/envoy-logger:latest
    container_name: envoy_logger
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

## 3. Set up Grafana

Grafana is the front-end visualization tool where you can design dashboards to display your data. When you view a dashboard, Grafana pulls data from the InfluxDB database to display it.

Follow the guide here to setup Grafana: https://grafana.com/docs/grafana/latest/setup-grafana/installation/docker/

Once configured, add a connection to InfluxDB using the authentication token created earlier.

Start building dashboards from your data! You will need to define some Flux queries to tell Grafana what data to fetch and how to organize it.

I have shared the queries I use as a reference: [/docs/flux_queries](/docs/flux_queries)
