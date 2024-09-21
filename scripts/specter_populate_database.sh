#!/bin/bash

if [ -f ./specter/data/$1 ]; then
    docker compose run specter python ./populate.py $1
else
	echo "FileNotFoundError: File ./specter/data/$1 does not exist. Please check if file is saved in ./specter/data/ directory"
fi
