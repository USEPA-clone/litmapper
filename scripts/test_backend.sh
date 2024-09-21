#!/bin/bash
docker compose up -d

echo "Sleeping 5 Seconds" && sleep 5
docker compose run --rm \
               -e "DRAMATIQ_TEST_BROKER=1" \
               -e "POSTGRES_URI=postgresql://litmapper:litmapper@database:5432/litmapper_test" \
               -e "REDIS_URI=redis://redis:6379/litmapper_test" \
               backend \
               py.test ./litmapper/test $@

docker compose down