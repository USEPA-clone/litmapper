#!/bin/bash

# Execute a docker login command to authenticate to the project ECR in AWS
# Assumes the following env vars are set appropriately:
# AWS_ACCESS_KEY_ID
# AWS_SECRET_ACCESS_KEY
account_id=$(aws sts get-caller-identity --query Account --output text)
ecr_uri="${account_id}.dkr.ecr.us-gov-east-1.amazonaws.com"

aws ecr get-login-password --region us-gov-east-1 | docker login --username AWS --password-stdin "$ecr_uri"
