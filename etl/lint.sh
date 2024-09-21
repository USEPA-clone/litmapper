#!/bin/bash

any_failed=0

echo "-- isort --"
isort -rc --check-only . || any_failed=1
echo "-- black --"
black . --check || any_failed=1
echo "-- mypy --"
mypy . --ignore-missing-imports || any_failed=1
echo "-- flake8 --"
flake8 . --config setup.cfg || any_failed=1

if [[ "$any_failed" -eq 1 ]]; then
    echo "One or more linters failed."
    exit 1
fi
