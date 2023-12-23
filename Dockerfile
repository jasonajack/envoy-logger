FROM python:3.11-slim-bullseye

COPY . /opt/envoy_logger/
WORKDIR /opt/envoy_logger/

RUN \
  # Install poetry dependencies
  python3 -m pip install --upgrade pip && \
  python3 -m pip install poetry && \
  python3 -m pip cache purge && \
  # Configure poetry for localized install
  poetry config virtualenvs.path /opt/envoy_logger/.cache && \
  poetry config virtualenvs.create false && \
  # Install dependencies
  poetry install

ENTRYPOINT ["./launcher.sh"]
