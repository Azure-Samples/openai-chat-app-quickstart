#!/bin/sh

echo 'Creating Python virtual environment "scripts/.venv"...'
python3 -m venv .venv

echo 'Installing dependencies from "requirements.txt" into virtual environment...'
.venv/bin/python -m pip --disable-pip-version-check install -r scripts/requirements.txt
