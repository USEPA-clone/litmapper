#!/bin/bash

set -eu

# Test deployment workflow locally
# See README for more details

function require_env_var() {
    env_var_name="$1"
    if [[ -z "$env_var_name" ]]; then
        echo "You must set the $env_var_name environment variable to run deployment."
        exit 1
    fi
}

for env_var in "AWS_ACCESS_KEY_ID" "AWS_SECRET_ACCESS_KEY" "AWS_DEFAULT_REGION" "AWS_EC2_INSTANCE_ID"; do
    require_env_var "$env_var"
done

act -b -e "$(dirname $0)/deploy_push.json" \
    -j push_images \
    -P ubuntu-latest=nektos/act-environments-ubuntu:18.04 \
    -s AWS_EC2_INSTANCE_ID="$AWS_EC2_INSTANCE_ID" \
    -s AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
    -s AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
    -s AWS_DEFAULT_REGION="$AWS_DEFAULT_REGION"

