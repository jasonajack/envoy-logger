#!/usr/bin/env bash
set -eou pipefail
cd "$(dirname "${0}")"

exec poetry run python3 -m envoy_logger "${@}"
