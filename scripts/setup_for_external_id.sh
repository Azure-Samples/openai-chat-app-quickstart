#!/bin/sh

# Check if tenant-id is provided
if [ -z "$1" ]
then
    echo "usage: $0 tenant-id"
    echo "`basename $0`:  error: the following arguments are required: tenant-id"
    exit 1
fi

. ./scripts/load_azd_env.sh

. ./scripts/load_python_env.sh

./scripts/.venv/bin/python ./scripts/setup_for_external_id.py $1
