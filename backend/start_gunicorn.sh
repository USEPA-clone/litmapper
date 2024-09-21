#!/bin/bash

exec gunicorn -k "uvicorn.workers.UvicornWorker" -c ./gunicorn_conf.py litmapper.main:app
