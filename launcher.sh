#!/usr/bin/env bash
set -eou pipefail
cd "$(dirname "${0}")"

python3 -m pip install --upgrade pip
python3 -m pip install poetry

poetry update
poetry run python3 -m envoy_logger "${ENVOY_LOGGER_CFG_PATH}"
