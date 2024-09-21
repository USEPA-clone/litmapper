#!/bin/bash

# Dump the database contents to a file for restore in another location.

docker compose up -d database
docker compose run --rm -v $PWD:/litmapper_data -w /litmapper_data database pg_dump -h database -U litmapper -d litmapper --file /litmapper_data/litmapper.pgdump -Fc
