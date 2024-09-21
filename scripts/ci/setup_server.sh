#!/bin/bash

# Build Docker images, push to ECR, run data load, and restart app services.
# Intended to be run on the EC2 server containing the deployed app.
# Requires the environment to be properly setup to allow AWS authentication, ex. by setting
# the following environment variables:
# AWS_ACCESS_KEY_ID - AWS account ID
# AWS_SECRET_ACCESS_KEY - AWS account secret key

function prod_docker_compose() {
    # Properly apply the production overrides file to use the production configuration
    # for all services
    docker compose -f docker compose.yml -f ./deploy/docker compose.override.yml $@
}

set -eu

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <IMAGE_TAG>"
    exit 1
fi

export IMAGE_TAG="$1"

# Update PATH for the root account in EC2 so it can find the AWS CLI binary
export PATH="/usr/local/bin:$PATH"

cd /lit-mining/litmapper

prod_docker_compose build

account_id=$(aws sts get-caller-identity --query Account --output text)

# Log in to ECR
./scripts/ci/login_ecr.sh

for image in "backend" "frontend" "frontend-static" "etl" "lite-app" "specter" "specter_database"; do
    # Tag image appropriately for ECR
    repository="litmapper-${image}"

    # Region currently hardcoded to us-gov-east-1, since that contains the ECR used
    # for deployment
    full_tag="${account_id}.dkr.ecr.us-gov-east-1.amazonaws.com/${repository}:$IMAGE_TAG"
    docker tag "litmapper-$image:$IMAGE_TAG" "$full_tag"

    # Create the repository if it doesn't exist 
    aws ecr describe-repositories --region us-gov-east-1 --repository-names "$repository" \
        || aws ecr create-repository --region us-gov-east-1 --repository-name "$repository" \
               --tags "Key=project-number,Value=0216677.004.001.003.341.001"

    # Push image to the repository
    docker push "$full_tag"
done

# Restart app services
prod_docker_compose down
prod_docker_compose up -d

# Run data load -- assumes required source data already exists on the server
./scripts/load_data.sh
