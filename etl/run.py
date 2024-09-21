from pathlib import Path
from typing import Optional

import click
from prefect import Flow
from pubmed import download_articles, embed_articles, load_pmids_tags, read_pmids
from secret import (
    get_api_base_url,
    get_entrez_api_key,
    get_entrez_email,
    get_entrez_tool,
)

DATA_DIR = Path("./data/").resolve()

PUBMED_CACHE_DIR = DATA_DIR / "pubmed"
PUBMED_CACHE_DIR.mkdir(exist_ok=True, parents=True)


@click.group("main")
def main():
    pass


@main.command("download_pubmed")
@click.option(
    "--pubmed-cache-dir",
    default=str(PUBMED_CACHE_DIR),
    type=click.Path(exists=True, file_okay=False, writable=True, resolve_path=True),
    help="Base directory to cache Pubmed downloads so they can be reread from disk if "
    "data needs to be reloaded without querying Pubmed.",
    show_default=True,
)
@click.option(
    "--id-file",
    type=click.Path(exists=True, dir_okay=False, readable=True, resolve_path=True),
    help="Delimited text file containing Pubmed IDs to load.",
    required=True,
)
@click.option(
    "--id-field-name",
    required=True,
    help="Name of the field containing Pubmed IDs in the ID file.",
)
@click.option(
    "--delimiter",
    type=str,
    default=",",
    help="Field delimiter to use for parsing the ID file.",
)
@click.option(
    "--limit",
    type=int,
    default=None,
    help="Limit the number of rows loaded from the ID file for testing.",
)
def download_pubmed(
    pubmed_cache_dir: str,
    id_file: str,
    id_field_name: str,
    delimiter: str,
    limit: Optional[int],
):
    with Flow("download_pubmed") as flow:
        api_base_url = get_api_base_url().run()
        entrez_email = get_entrez_email().run()
        entrez_tool = get_entrez_tool().run()
        entrez_api_key = get_entrez_api_key().run()

        print(f"API base URL: {api_base_url}")

        pubmed_cache_path = Path(pubmed_cache_dir)

        pmids_tags = read_pmids(
            Path(id_file),
            id_field_name,
            delimiter,
            limit,
        )
        pmids_tags = download_articles(
            entrez_api_key, entrez_email, entrez_tool, pmids_tags, pubmed_cache_path
        )
        load_pmids_tags(
            api_base_url,
            pmids_tags,
            pubmed_cache_path,
            Path(id_file),
        )

    flow.run()


@main.command("generate_embeddings")
@click.option(
    "--embed-model",
    multiple=False,
    default="use",
    help="Generate embeddings using this model; Acceptable parameters are 'use' "
    "for universal sentence encoder, or 'specter' for the model Specter by AllenAI.",
)
@click.option(
    "--id-file",
    default=None,
    required=False,
    help="If specified, generate embeddings for only articles in this file, "
    "rather than the full dataset.",
)
@click.option(
    "--id-field-name",
    default=None,
    required=False,
    help="Name of the field containing Pubmed IDs in the ID file.",
)
@click.option(
    "--embeddings-file",
    default=None,
    required=False,
    help="Name of the file containing existing embeddings for the articles.",
)
@click.option(
    "--are-new-articles",
    default=None,
    required=False,
    help="Whether article already exists in database or not. Determines whether to "
    " add new entry to embeddings table, or update a column.",
)
def generate_embeddings(
    embed_model: str,
    id_file: str,
    id_field_name: str,
    embeddings_file: str,
    are_new_articles: bool,
):
    with Flow("generate_embeddings") as flow:
        api_base_url = get_api_base_url().run()

        embed_articles(
            api_base_url,
            embed_model,
            id_file,
            id_field_name,
            embeddings_file,
            are_new_articles,
        )

    flow.run()


if __name__ == "__main__":
    main()
