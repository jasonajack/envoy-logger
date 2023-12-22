#!/usr/bin/env bash
set -eou pipefail
cd "$(dirname "${0}")"

poetry run python3 -m envoy_logger "${ENVOY_LOGGER_CFG_PATH}"
