import json
import logging
import os
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Sequence,
    Set,
    Tuple,
    TypeVar,
    Union,
)
from urllib.parse import urlencode

import requests
import sqlalchemy.sql.functions as func
from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy import Table, create_engine
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Query, Session, sessionmaker
from thefuzz import fuzz

from litmapper.db.pubmed import search_pumbed_ids

POSTGRES_URI = os.environ["POSTGRES_URI"]
DB_ENGINE = create_engine(POSTGRES_URI)
SessionLocal = sessionmaker(bind=DB_ENGINE)
LOGGER = logging.getLogger(__name__)


@contextmanager
def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


def get_db_dep():
    # Convert the context manager to a generator for use with FastAPI
    with get_db() as db:
        yield db


def do_bulk_upsert(
    db: Session,
    model: Any,
    objs: Union[BaseModel, Sequence[BaseModel]],
    unique_keys: Set[str],
):
    """
    Do a performant upsert on the given model using the given objects and
    unique key columns.  Objects which don't already exist according to the
    unique keys will be created.  Objects which do already exist will have all
    fields (minus the unique keys and primary key) updated.

    Args:
      db: Database connection
      model: Model for which to upsert data
      objs: Single object or list of objects to upsert
      unique_keys: Columns which should be counted as unique for the upsert
       (i.e., if a row in the database already exists for a given combination of these
       keys, it should be updated instead of inserted)
    """
    _objs = [objs] if isinstance(objs, BaseModel) else objs
    # Don't try to insert an empty list, since this will confuse SQLAlchemy and cause
    # an error
    if isinstance(_objs, list) and len(_objs) == 0:
        return

    table = model if isinstance(model, Table) else model.__table__
    insert_stmt = insert(table)

    # Update everything with the new row except for the unique keys (including the
    # user-given unique keys and the table's primary key, in case it's an autoincrementing
    # surrogate key)
    update_cols = {
        c.name: c
        for c in insert_stmt.excluded
        if c.name not in unique_keys and c.name not in table.primary_key
    }

    # We'll get an error if we try to "on conflict do update" with an empty set of
    # update columns, so do nothing instead of updating in that case
    if not update_cols:
        final_stmt = insert_stmt.on_conflict_do_nothing(index_elements=unique_keys)
    else:
        final_stmt = insert_stmt.on_conflict_do_update(
            index_elements=unique_keys, set_=update_cols
        )
    db.execute(final_stmt, params=[o.dict() for o in _objs])
    db.commit()


def paginate(query: Query, page: int, limit: int) -> Tuple[List[Any], int]:
    """
    Paginate the given query, returning the given page for the given limit and offset.
    Adds and returns a special column named "__count__" which has the total row count, excluding
    limit and offset, for all rows.

    Args:
      query: Existing query.
      page: Page number to return (0-based)
      limit: Max number of results to return per-page.

    Returns:
      2-tuple: list of ORM objects resulting from running the query and the total row count.
    """
    objs = (
        query.limit(limit)
        .offset(page * limit)
        .add_columns((func.count().over()).label("__count__"))
        .all()
    )

    # Results will be (obj, total_count) tuples
    # Pull out the first total count and return only the
    # objects from the list
    total_count = 0
    if len(objs) > 0:
        total_count = objs[0][1]

    return [tup[0] for tup in objs], total_count


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


def do_batch(obj_iter: Iterator[T], batch_func: Callable[[List[T]], None], batch_size):
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


def fuzzy_match_titles(titles: list[str], pubmed_ids: List[int]):
    """
    Check the titles of the uploaded articles against the titles of the articles from the PubMed API.

    Parameters:
    ----------
    titles: list[str]
        List of titles of the uploaded articles.
    """
    pubmed_results = search_pumbed_ids.run(pubmed_ids)  # type: ignore
    pubmed_results = sorted(pubmed_results, key=lambda x: x["id"])

    mismatched_titles = []
    for index, (title, pubmed_title) in enumerate(
        zip(titles, [result["title"] for result in pubmed_results])
    ):
        if fuzz.ratio(title, pubmed_title) < 90:
            mismatched_titles.append(
                {
                    "uploaded_title": title,
                    "pubmed_title": pubmed_title,
                    "pubmed_id": pubmed_results[index]["id"],
                }
            )

    if mismatched_titles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Mismatched titles found in uploaded articles: {mismatched_titles}",
        )
