#!/bin/sh

. ./scripts/load_azd_env.sh

. ./scripts/load_python_env.sh

.venv/bin/python ./scripts/setup_for_external_id.py
