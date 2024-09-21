#!/bin/bash

set -eu

# Master script used to load all data in the database via the ETL process.
# Creates checkpoints to mark completed steps so they aren't repeated (although
# checkpoints can be manually removed to trigger a rerun).

function log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

REQUIRED_FILES=("etl/data/pilot.csv")

any_missing=""
for required_file in ${REQUIRED_FILES[@]}; do
    if [[ ! -e $required_file ]]; then
        log "Missing expected file/directory $required_file"
        any_missing="yes"
    fi
done

if [[ ! -z "$any_missing" ]]; then
    log "One or more required files are missing -- can't load data."
fi

CKPT_DIR="etl/data/.ckpt"
mkdir -p "$CKPT_DIR"

#
# 0. Migrate the database (unconditionally)
#
log "Running migrations"
./scripts/migrate.sh
log "Migrations finished"

#
# 1. Upsert articles
# NOTE: This will be much faster if the Pubmed articles have already been downloaded.
# If you can, bring over the `etl/data/pubmed` directory from somewhere this has already been
# run to speed it up.
#
article_tag_ckpt="$CKPT_DIR/articles"
if [[ ! -f "$article_tag_ckpt" ]]; then
    log "Loading articles"
    docker compose run --rm etl python run.py download_pubmed \
                --id-file data/pilot.csv \
                --id-field-name PMID

    touch "$article_tag_ckpt"
    log "Articles loaded"
else
    log "Articles already exist"
fi

#
# 2. Generate embeddings
#
embedding_ckpt="$CKPT_DIR/embeddings"
if [[ ! -f "$embedding_ckpt" ]]; then
    log "Generating embeddings"
    docker compose run --rm etl python run.py generate_embeddings \
        --embed-model use \
        --are-new-articles True
    docker compose run --rm etl python run.py generate_embeddings \
        --embed-model specter \
        --are-new-articles False
    touch "$embedding_ckpt"
    log "Embeddings generated"
else
    log "Embeddings already exist"
fi
