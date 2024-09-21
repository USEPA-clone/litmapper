import datetime as dt
import itertools
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, Iterator, List, NamedTuple, Optional, TypeVar

import prefect
import requests
import tensorflow_hub as hub
from Bio import Entrez
from prefect import Flow, task

from .secret import (
    get_api_base_url,
    get_entrez_api_key,
    get_entrez_email,
    get_entrez_tool,
)
from .util import (
    article_batch_iter,
    check_response_status,
    do_batch,
    fetch_pmid_to_litmapper_id_key,
    get_article_path,
    stringify_xml_elem,
)

T = TypeVar("T")

# This is a hard limit enforced by PubMed/Entrez
MAX_ARTICLES_PER_FETCH = 10000
LOGGER = logging.getLogger(__name__)


def download_pubmed(
    pmids: list,
):
    with Flow("download_pubmed") as flow:
        entrez_email = get_entrez_email().run()
        entrez_tool = get_entrez_tool().run()
        entrez_api_key = get_entrez_api_key().run()

        data_dir = Path("./data/").resolve()
        pubmed_cache_dir = data_dir / "pubmed"
        pubmed_cache_dir.mkdir(exist_ok=True, parents=True)
        pubmed_cache_path = Path(pubmed_cache_dir)

        downloaded_articles = download_articles(
            entrez_api_key, entrez_email, entrez_tool, pmids, pubmed_cache_path
        )
        load_pmids(
            downloaded_articles,
            pubmed_cache_path,
        )

    flow.run()


def generate_embeddings(pmids: list):
    with Flow("generate_embeddings") as flow:
        api_base_url = get_api_base_url()

        embed_articles(api_base_url, pmids)

    flow.run()


# The API can be flaky, so set up retries
@task(max_retries=5, retry_delay=dt.timedelta(minutes=5))
def download_articles(
    entrez_api_key: str,
    entrez_email: str,
    entrez_tool: str,
    pmids: list,
    cache_dir: Path,
) -> List[int]:
    Entrez.email = entrez_email
    Entrez.api_key = entrez_api_key
    Entrez.tool = entrez_tool

    unique_pmids = list(set(pmids))
    num_to_download = len(unique_pmids)
    LOGGER.debug(f"Reduced {len(pmids)} PMIDs to {num_to_download} unique PMIDs")
    LOGGER.debug(f"Checking whether {num_to_download} articles are cached...")
    existing_pmids = {
        pmid for pmid in unique_pmids if get_article_path(cache_dir, pmid).exists()
    }
    num_existing = len(existing_pmids)
    LOGGER.debug(f"Found {num_existing} articles in cache")
    download_pmids = [str(pmid) for pmid in unique_pmids if pmid not in existing_pmids]
    num_to_download = len(download_pmids)

    if num_to_download == 0:
        LOGGER.debug("All articles already exist in cache.")
        return pmids

    LOGGER.info(
        f"Attempting to fetch {num_to_download} articles from the Entrez API..."
    )

    downloaded_pmids: List[int] = []

    def fetch_pmids(pmids: List[str]):
        LOGGER.debug(f"Fetching {len(pmids)} articles...")
        if len(pmids) > MAX_ARTICLES_PER_FETCH:
            raise ValueError(
                f"Entrez only allows for fetching {MAX_ARTICLES_PER_FETCH} "
                "articles at a time."
            )

        results = Entrez.efetch("pubmed", id=pmids, rettype=None, retmode="xml")

        LOGGER.debug("Parsing result XML...")
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
            LOGGER.debug(f"Wrote article XML to {article_path}")
            downloaded_pmids.append(pmid_int)

    batch_pmids: List[str] = []
    for pmid in download_pmids:
        batch_pmids.append(pmid)
        if len(batch_pmids) >= MAX_ARTICLES_PER_FETCH:
            fetch_pmids(batch_pmids)
            batch_pmids = []

    if len(batch_pmids) > 0:
        fetch_pmids(batch_pmids)

    LOGGER.info(
        f"Downloaded {len(downloaded_pmids)} new articles ({num_existing} were already cached)"
    )

    return pmids


def parse_articles(cache_dir: Path, pmids: List[int]) -> Iterator[Dict[str, Any]]:
    """
    Generator returning parsed articles from a list of Pubmed IDs.
    """
    logger = prefect.context.get("logger")

    for pmid in pmids:
        article = ET.parse(str(get_article_path(cache_dir, pmid)))

        abstract = "".join(
            abstract_section.text + "\n"
            for abstract_section in article.findall(".//AbstractText")
            if abstract_section.text
        )
        date_elem = article.find(".//PubMedPubDate[@PubStatus='entrez']")
        if date_elem is None:
            raise ValueError(
                "Failed to find date element in XML:\n"
                f"{stringify_xml_elem(article.getroot())}"
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
                    "Failed to find descriptor in MeSH Heading:"
                    f"\n{stringify_xml_elem(mesh_term)}"
                )
            mesh_id = descriptor_elem.attrib.get("UI")
            if mesh_id is None:
                raise ValueError(
                    "Failed to find UI in MeSH Heading:"
                    f"\n{stringify_xml_elem(descriptor_elem)}"
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


class ArticleTagRow(NamedTuple):
    pmid: int
    tag_name: str
    tag_value: str


def load_articles(articles: List[Dict[str, Any]]):
    api_base_url = get_api_base_url().run()
    LOGGER.info(f"API base URL: {api_base_url}")

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

        LOGGER.debug(f"Sending {num_articles} articles to the API.")
        check_response_status(
            requests.put(f"{api_base_url}/literature/articles", json=articles_only)
        )

        num_mesh_terms = len(mesh_terms_only)
        if num_mesh_terms > 0:
            LOGGER.debug(f"Sending {num_mesh_terms} MeSH terms to the API...")
            check_response_status(
                requests.put(
                    f"{api_base_url}/literature/mesh_terms",
                    json=list(mesh_terms_only.values()),
                )
            )

            LOGGER.debug(
                f"Sending {len(article_mesh_terms)} article-MeSH term "
                "relationships to the API."
            )

            litmapper_lookup = fetch_pmid_to_litmapper_id_key(api_base_url)

            article_id_mesh_terms = [
                {
                    "article_id": int(litmapper_lookup[int(mesh_term["pmid"])]),
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


@task
def load_pmids(
    pmids: list,
    cache_dir: Path,
    batch_size: int = 1000,
):
    print(pmids)

    pmids = list(set(pmids))
    do_batch(parse_articles(cache_dir, pmids), load_articles, batch_size)


@task
def load_pmids_from_file(
    pmids: list,
    articles: List[Dict[str, Any]],
    batch_size: int = 1000,
):
    print(pmids)

    pmids = list(set(pmids))
    do_batch(articles, load_articles, batch_size)  # type: ignore


@task
def embed_articles(
    api_base_url: str,
    pmids: list,
):
    logger = prefect.context.get("logger")

    logger.info("Loading embedding module from TF Hub")
    embed = hub.load("https://tfhub.dev/google/universal-sentence-encoder/4")
    logger.info("Embedding module loaded")

    for articles in article_batch_iter(api_base_url, {"pmids": pmids}):
        logger.info(f"Generating embeddings for {len(articles)} texts")

        def format_article(article: Dict[str, Any]) -> str:
            return f"{article['title']}\n{article['abstract']}"

        embeddings = embed([format_article(a) for a in articles]).numpy()

        article_embeddings = [
            {"article_id": article["article_id"], "use_embedding": embedding.tolist()}
            for article, embedding in zip(articles, embeddings)
        ]

        check_response_status(
            requests.put(
                f"{api_base_url}/literature/articles/embeddings",
                params={"new_articles": True},
                json=article_embeddings,
            )
        )
