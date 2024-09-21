#!/bin/bash

cmd="upgrade head"
if [[ $# -ge 1 ]]; then
    cmd=$@
fi

docker compose run --rm -w /code/litmapper/alembic backend alembic $cmd
