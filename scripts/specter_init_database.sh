#!/bin/bash

# Initialize an empty database for specter_embeddings.

docker compose up -d specter_database
cat ./specter/init.sql | docker exec -i litmapper_specter_database_1 psql -U specter -d specter