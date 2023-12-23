#!/usr/bin/env bash
set -eou pipefail
cd "$(dirname "${0}")"

rm -rf ~/.cache/enphase-envoy/

poetry run black --check envoy_logger tests
poetry run isort --check envoy_logger tests
poetry run flake8 envoy_logger tests
poetry run yamllint -c .yamllint .
poetry run mdformat --check .

poetry run coverage run -m pytest -s
poetry run coverage report -m

if which shellcheck; then
  shellcheck ./*.sh
fi
