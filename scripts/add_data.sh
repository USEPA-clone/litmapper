#!/bin/bash

set -eu

function log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

REQUIRED_FILE=("etl/data/$1")
ID_FILE=("data/$1")

if [[ ! -e $REQUIRED_FILE ]]; then
    log "Missing expected file/directory $REQUIRED_FILE"
    exit
fi

CKPT_DIR="etl/data/.ckpt-add-data"
mkdir -p "$CKPT_DIR"

#
# 0. Create a dump of the current database in case of issues
#
log "Creating dump of existing database in checkpoint directory"
docker compose up -d database
docker compose run --rm -v $PWD:/litmapper_data -w /litmapper_data database pg_dump -h database -U litmapper -d litmapper --file "$CKPT_DIR/litmapper_$(date +"%Y_%m_%d_%I_%M_%p").pgdump" -Fc

#
# 1. Migrate the database (unconditionally)
#
log "Running migrations"
./scripts/migrate.sh
log "Migrations finished"


#
# 2. Upsert articles, tags, and upload metadata
# Downloads articles from PubMed API, formats,
# and adds articles, mesh terms, and tags to our db

article_tag_ckpt="$CKPT_DIR/articles_tags"
if [[ ! -f "$article_tag_ckpt" ]]; then
    log "Loading articles and tags"
    docker compose run --rm etl python run.py download_pubmed \
                --id-file $ID_FILE \
                --id-field-name PMID \
                --tag-name-field-name tag_name \
                --tag-value-field-name tag_value

    touch "$article_tag_ckpt"
    log "Articles and tags loaded"
else
    log "Articles and tags already exist"
fi

#
# 3. Generate embeddings
#

embedding_ckpt="$CKPT_DIR/embeddings"
if [[ ! -f "$embedding_ckpt" ]]; then
    log "Generating embeddings"
    docker compose run --rm etl python run.py generate_embeddings \
                --embed-model use \
                --id-file $ID_FILE \
                --are-new-articles True \
                --id-field-name PMID
    docker compose run --rm etl python run.py generate_embeddings \
            --embed-model specter \
            --id-file $ID_FILE \
            --are-new-articles False \
            --id-field-name PMID


    touch "$embedding_ckpt"
    log "Embeddings generated"
else
    log "Embeddings already exist"
fi
