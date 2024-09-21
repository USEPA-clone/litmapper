import datetime as dt
import itertools
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, Iterator, List, NamedTuple, Optional, Tuple, TypeVar

import pandas as pd
import prefect
import requests
import tensorflow_hub as hub
from Bio import Entrez
from prefect import task
from transformers import AutoModel, AutoTokenizer

from util import (
    article_batch_iter,
    check_response_status,
    do_batch,
    fetch_pmid_to_litmapper_id_key,
    get_article_path,
    stringify_xml_elem,
)

T = TypeVar("T")


@task
def read_pmids(
    id_file: Path,
    id_field_name: str,
    delimiter: str,
    limit: Optional[int],
) -> List[int]:
    logger = prefect.context.get("logger")

    pmids_tags = pd.read_csv(
        id_file,
        usecols=[id_field_name],
        delimiter=delimiter,
        nrows=limit,
    )
    pmids_tags = pmids_tags.rename(
        {
            id_field_name: "pmid",
        },
        axis=1,
    )
    num_pmids = pmids_tags["pmid"].nunique()

    logger.info(f"Read {num_pmids} PMIDs from '{id_file}'.")
    return pmids_tags


# This is a hard limit enforced by PubMed/Entrez
MAX_ARTICLES_PER_FETCH = 10_000


# The API can be flaky, so set up retries
@task(max_retries=5, retry_delay=dt.timedelta(minutes=5))
def download_articles(
    entrez_api_key: str,
    entrez_email: str,
    entrez_tool: str,
    pmids_tags: pd.DataFrame,
    cache_dir: Path,
) -> List[int]:
    logger = prefect.context.get("logger")

    Entrez.email = entrez_email
    Entrez.api_key = entrez_api_key
    Entrez.tool = entrez_tool

    pmids = pmids_tags["pmid"]

    unique_pmids = list(set(pmids))
    num_to_download = len(unique_pmids)
    logger.debug(f"Reduced {len(pmids)} PMIDs to {num_to_download} unique PMIDs")
    logger.debug(f"Checking whether {num_to_download} articles are cached")
    existing_pmids = set(
        pmid for pmid in unique_pmids if get_article_path(cache_dir, pmid).exists()
    )
    num_existing = len(existing_pmids)
    logger.debug(f"Found {num_existing} articles in cache")
    download_pmids = [str(pmid) for pmid in unique_pmids if pmid not in existing_pmids]
    num_to_download = len(download_pmids)

    if num_to_download == 0:
        logger.debug(f"All articles already exist in cache.")
        return pmids_tags

    logger.info(f"Attempting to fetch {num_to_download} articles from the Entrez API")

    downloaded_pmids: List[int] = []

    def fetch_pmids(pmids: List[str]):
        logger.debug(f"Fetching {len(pmids)} articles")
        if len(pmids) > MAX_ARTICLES_PER_FETCH:
            raise ValueError(
                f"Entrez only allows for fetching {MAX_ARTICLES_PER_FETCH} articles at a time."
            )

        results = Entrez.efetch("pubmed", id=pmids, rettype=None, retmode="xml")

        logger.debug("Parsing result XML")
        xml = ET.fromstring(results.read())

        for article in list(
            itertools.chain(
                xml.findall("./PubmedArticle"), xml.findall("./PubmedBookArticle")
            )
        ):
            pmid = article.findtext("*/PMID")
            if pmid is None:
                raise ValueError(
                    f"Failed to find PMID in XML:\n{stringify_xml_elem(article)}"
                )
            pmid_int = int(pmid)
            article_path = get_article_path(cache_dir, pmid_int)
            ET.ElementTree(element=article).write(
                str(article_path),
                encoding="utf-8",
                xml_declaration=True,
            )
            logger.debug(f"Wrote article XML to {article_path}")
            downloaded_pmids.append(pmid_int)

    batch_pmids: List[str] = []
    for pmid in download_pmids:
        batch_pmids.append(pmid)
        if len(batch_pmids) >= MAX_ARTICLES_PER_FETCH:
            fetch_pmids(batch_pmids)
            batch_pmids = []

    if len(batch_pmids) > 0:
        fetch_pmids(batch_pmids)

    logger.info(
        f"Downloaded {len(downloaded_pmids)} new articles ({num_existing} were already cached)"
    )
    to_load_pmids = list(existing_pmids) + downloaded_pmids
    return pmids_tags[pmids_tags["pmid"].isin(to_load_pmids)]


def parse_articles(cache_dir: Path, pmids: List[int]) -> Iterator[Dict[str, Any]]:
    """
    Generator returning parsed articles from a list of Pubmed IDs.
    """
    logger = prefect.context.get("logger")

    for pmid in pmids:
        article = ET.parse(str(get_article_path(cache_dir, pmid)))

        abstract = ""
        for abstract_section in article.findall(".//AbstractText"):
            if abstract_section.text:
                abstract += abstract_section.text + "\n"

        date_elem = article.find(".//PubMedPubDate[@PubStatus='entrez']")
        if date_elem is None:
            raise ValueError(
                f"Failed to find date element in XML:\n{stringify_xml_elem(article.getroot())}"
            )

        try:
            year = date_elem.findtext("./Year")
            month = date_elem.findtext("./Month")
            day = date_elem.findtext("./Day")
            if year is None or month is None or day is None:
                raise ValueError("Missing date element.")

            date: Optional[str] = dt.date(int(year), int(month), int(day)).isoformat()
        except (TypeError, ValueError):
            logger.warn(
                f"Failed to parse date element:\n{stringify_xml_elem(date_elem)}"
            )
            date = None

        mesh_terms = []
        for mesh_term in article.findall(".//MeshHeading"):
            descriptor_elem = mesh_term.find("./DescriptorName")
            if descriptor_elem is None:
                raise ValueError(
                    f"Failed to find descriptor in MeSH Heading:\n{stringify_xml_elem(mesh_term)}"
                )
            mesh_id = descriptor_elem.attrib.get("UI")
            if mesh_id is None:
                raise ValueError(
                    f"Failed to find UI in MeSH Heading:\n{stringify_xml_elem(descriptor_elem)}"
                )
            mesh_terms.append(
                {
                    "mesh_id": descriptor_elem.attrib["UI"],
                    "name": descriptor_elem.text,
                }
            )

        yield {
            "pmid": pmid,
            "title": article.findtext(
                "./MedlineCitation/Article/ArticleTitle", default=""
            ),
            "abstract": abstract,
            "publication_date": date,
            "mesh_terms": mesh_terms,
        }


@task
def load_pmids_tags(
    api_base_url: str,
    pmids_tags: pd.DataFrame,
    cache_dir: Path,
    id_file: Path,
    batch_size: int = 1000,
):
    logger = prefect.context.get("logger")

    def load_articles(articles: List[Dict[str, Any]]):
        num_articles = len(articles)
        if num_articles > 0:
            articles_only: List[Dict[str, Any]] = []
            mesh_terms_only: Dict[str, Dict[str, Any]] = {}
            article_mesh_terms: List[Dict[str, Any]] = []

            for article in articles:
                mesh_terms = article.pop("mesh_terms")
                articles_only.append(article)
                for mesh_term in mesh_terms:
                    # Deduplicate mesh terms via this assignment
                    mesh_terms_only[mesh_term["mesh_id"]] = mesh_term
                    article_mesh_terms.append(
                        {"pmid": article["pmid"], "mesh_id": mesh_term["mesh_id"]}
                    )

            logger.info(f"Sending {num_articles} articles to the API.")
            check_response_status(
                requests.put(f"{api_base_url}/literature/articles", json=articles_only)
            )

            num_mesh_terms = len(mesh_terms_only)
            if num_mesh_terms > 0:
                logger.info(f"Sending {num_mesh_terms} MeSH terms to the API.")
                check_response_status(
                    requests.put(
                        f"{api_base_url}/literature/mesh_terms",
                        json=list(mesh_terms_only.values()),
                    )
                )

                logger.info(
                    f"Sending {len(article_mesh_terms)} article-MeSH term relationships to the API."
                )

                litmapper_lookup = fetch_pmid_to_litmapper_id_key(api_base_url)
                article_id_mesh_terms = [
                    {
                        "article_id": int(litmapper_lookup[mesh_term["pmid"]]),
                        "mesh_id": mesh_term["mesh_id"],
                    }
                    for mesh_term in article_mesh_terms
                ]

                check_response_status(
                    requests.put(
                        f"{api_base_url}/literature/articles/mesh_terms",
                        json=article_id_mesh_terms,
                    )
                )

    pmids = pmids_tags["pmid"].unique().tolist()
    do_batch(parse_articles(cache_dir, pmids), load_articles, batch_size)

    def load_article_requester_data(requested_articles):
        litmapper_lookup = fetch_pmid_to_litmapper_id_key(api_base_url)
        article_requester_rels = []
        for article in requested_articles:
            article = article._asdict()
            article_requester_rels.append(
                {
                    "article_id": int(litmapper_lookup[article["PMID"]]),
                    "requester": article["requester"],
                    "upload_date": article["upload_date"],
                }
            )
        logger.info(
            f"Sending {len(requested_articles)} article-requester relationships to the API."
        )
        check_response_status(
            requests.put(
                f"{api_base_url}/literature/articles/requesters",
                json=article_requester_rels,
            )
        )

    requester_data = pd.read_csv(id_file)
    if "requester" in list(
        requester_data.columns
    ):  # Only add to table if "requester" column present
        do_batch(requester_data.itertuples(), load_article_requester_data, batch_size)


@task
def embed_articles(
    api_base_url: str,
    embed_model: str,
    id_file: str,
    id_field_name: str,
    embeddings_file: str,
    are_new_articles: bool,
    batch_size: int = 500,
):
    # If file is included, only generate embeddings for articles in file
    pmids = list(pd.read_csv(id_file)[id_field_name]) if id_file else []

    def format_article(article: Dict[str, Any]) -> str:
        return f"{article['title']}\n{article['abstract']}"

    logger = prefect.context.get("logger")

    # If embeddings are being imported from a file, simply upload these embeddings
    # for the appropriate article id
    if embeddings_file is not None:
        article_embeddings = []
        embeddings_from_file = pd.read_csv(embeddings_file).to_dict(orient="records")
        for article in embeddings_from_file[:10]:
            article_embeddings.append(
                {
                    "article_id": article["article_id"],
                    f"{embed_model}_embedding": eval(article[f"embedding"]),
                }
            )

        def upload_embeds(embeds_list):
            check_response_status(
                requests.put(
                    f"{api_base_url}/literature/articles/embeddings",
                    params={"new_articles": are_new_articles},
                    json=embeds_list,
                )
            )

        do_batch(iter(article_embeddings), upload_embeds, batch_size)

    # Otherwise, generate embeddings from scratch, then upload
    else:
        if embed_model == "use":
            logger.info("Loading embedding module from TF Hub")
            embed = hub.load("https://tfhub.dev/google/universal-sentence-encoder/4")
            logger.info("Embedding module loaded")

            def gen_embeds(article_array):
                embeddings = embed([format_article(a) for a in article_array]).numpy()
                return [embedding.tolist() for embedding in embeddings]

        elif embed_model == "specter":
            logger.info("Loading embedding module from Transformers")
            tokenizer = AutoTokenizer.from_pretrained("allenai/specter")
            model = AutoModel.from_pretrained("allenai/specter")
            logger.info("Embedding module loaded")

            def gen_embeds(article_array):
                formatted_arts = [format_article(a) for a in article_array]

                # Separate title_abs into article chunks to prevent OOM issues
                chunk_size = 3
                chunks = [
                    formatted_arts[x : x + chunk_size]
                    for x in range(0, len(formatted_arts), chunk_size)
                ]

                # Create embeddings
                all_embeds = []
                for chunk in chunks:
                    inputs = tokenizer(
                        chunk,
                        padding=True,
                        truncation=True,
                        return_tensors="pt",
                        max_length=512,
                    )
                    result = model(**inputs)
                    chunk_embeds = result.last_hidden_state[:, 0, :].tolist()
                    all_embeds = all_embeds + chunk_embeds
                return all_embeds

        # Upload newly generated embeddings
        batch_count = 0
        for articles in article_batch_iter(api_base_url, {"pmids": pmids}):
            logger.info(
                f"Generating embeddings for {len(articles)} texts. Batch {batch_count}."
            )

            embeddings = gen_embeds(articles)

            article_embeddings = [
                {
                    "article_id": article["article_id"],
                    f"{embed_model}_embedding": embedding,
                }
                for article, embedding in zip(articles, embeddings)
            ]

            logger.info(f"Embeddings generated for {batch_count}.")

            check_response_status(
                requests.put(
                    f"{api_base_url}/literature/articles/embeddings",
                    params={"new_articles": are_new_articles},
                    json=article_embeddings,
                )
            )

            batch_count += 1
