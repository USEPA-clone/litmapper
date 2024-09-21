# Deployment Config

This directory contains extra configuration overrides and files/scripts to use when running in production.  See [the deployment README](../scripts/ci/README.md) for more info on the deployment process.

- `docker compose-override.yml`: Overrides specific configuration for certain services to run in production rather than development mode.
- `nginx.conf`: Configuration file for the nginx container serving the frontend for the systematic review app.

To run the project in "production" mode to test these config files, use the following (from the repository root) instead of `docker compose <command>`:

    docker compose -f docker compose.yml -f deploy/docker compose.override.yml <command>
