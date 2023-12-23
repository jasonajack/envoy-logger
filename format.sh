#!/usr/bin/env bash
set -eou pipefail
cd "$(dirname "${0}")"

poetry run black envoy_logger tests
poetry run isort envoy_logger tests
