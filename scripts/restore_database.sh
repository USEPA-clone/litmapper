#!/bin/bash

# Restore the database from a dump.

docker compose up -d database
docker compose run --rm -v $PWD:/litmapper_data -w /litmapper_data database pg_restore -h database -U litmapper -d litmapper -c -e --if-exists /litmapper_data/litmapper.pgdump
