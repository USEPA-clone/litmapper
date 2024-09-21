#!/bin/bash

docker compose run --rm -w /code/litmapper/alembic backend alembic revision --autogenerate $@
