import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, TypeVar
from urllib.parse import urlencode

import requests

T = TypeVar("T")


def get_article_path(cache_dir: Path, pmid: int) -> Path:
    """
    Returns:
      The path to the article file with the PMID.
    """
    return cache_dir / f"{pmid}.xml"


def stringify_xml_elem(elem: ET.Element) -> str:
    """
    Returns:
      String representation of the XML element.
    """
    return ET.tostring(elem, encoding="unicode")


def check_response_status(res: requests.Response):
    if res.status_code >= 400:
        error_text = (
            f"Error requesting API: {res.status_code} {res.reason} - {res.text}"
        )
        raise RuntimeError(error_text)
    return res


def fetch_pmid_to_litmapper_id_key(api_base_url: str):
    litmapper_to_pmid_key = check_response_status(
        requests.get(f"{api_base_url}/literature/articles/pmids")
    ).content
    litmapper_to_pmid_key = json.loads(litmapper_to_pmid_key)

    pmid_to_litmapper_key: Dict[int, str] = dict(map(reversed, litmapper_to_pmid_key.items()))  # type: ignore

    return pmid_to_litmapper_key


def article_batch_iter(
    api_base_url: str, filters: Dict[str, Any]
) -> Iterable[List[Dict[str, Any]]]:
    """
    Args:
      api_base_url: Base URL for the API server
      filters: Querystring dict containing additional filters to be applied to the paged
        article search

    Returns:
      An iterator over pages of JSON-formatted PubMed articles returned from the API.
    """
    page = 0

    while True:
        query = urlencode({**filters, "page": page}, doseq=True)

        res = requests.get(f"{api_base_url}/literature/articles?{query}")
        check_response_status(res)
        articles = res.json()
        if len(articles) == 0:
            break

        yield articles

        page += 1


def do_batch(obj_iter: Iterable[T], batch_func: Callable[[List[T]], None], batch_size):
    """
    Call a function on batches of objects returned by the passed iterator.

    Args:
      obj_iter: Iterator over the objects to batch.
      batch_func: Callable to call over batches (lists) of the objects from the
        iterator
      batch_size: Number of objects to put in each batch
    """
    batch_objs: List[T] = []

    for obj in obj_iter:
        batch_objs.append(obj)

        if len(batch_objs) >= batch_size:
            batch_func(batch_objs)
            batch_objs = []

    if len(batch_objs) > 0:
        batch_func(batch_objs)
