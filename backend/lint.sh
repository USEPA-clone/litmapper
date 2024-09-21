#!/bin/bash

any_failed=0

echo "-- isort --"
isort -rc --check-only ./litmapper || any_failed=1
echo "-- black --"
black ./litmapper --check || any_failed=1
echo "-- mypy --"
mypy  -p litmapper --ignore-missing-imports || any_failed=1
echo "-- flake8 --"
flake8 ./litmapper --config setup.cfg || any_failed=1

if [[ "$any_failed" -eq 1 ]]; then
    echo "One or more linters failed."
    exit 1
fi
