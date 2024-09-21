#!/bin/bash

### ADDS SPECTER EMBEDDINGS SAVED IN CSV FILE 
### TO DATABASE. CAN EASILY BE ADJUSTED TO BE
### USED FOR NEW BATCHES OF EMBEDDINGS.

set -eu

function log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

REQUIRED_FILE=("etl/data/$1")
EMBEDDINGS_FILE=("data/$1")

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
# 2. Upload existing embeddings from file.
#     File must have two columns:
#        article_id: int (litmapper id), 
#        embedding: stringified embedding
#       
#
log "Uploading specter embeddings"
docker compose run --rm etl python run.py generate_embeddings \
            --embed-model specter \
            --embeddings-file $EMBEDDINGS_FILE \
            --are-new-articles False
log "Embeddings generated"
