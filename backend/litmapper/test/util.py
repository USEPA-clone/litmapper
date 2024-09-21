import random
from typing import Any, Callable, Dict, List, Sequence

import requests
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from litmapper import models

JsonObj = Dict[str, Any]


def require_response_code(res: requests.Response, status_code: int):
    assert res.status_code == status_code, "\n".join(
        (
            "Response code mismatch.",
            f"  Expected Code: {status_code}",
            f"  Actual Code: {res.status_code}",
            f"  Text: {res.text}",
        )
    )


def verify_upsert(
    client: TestClient,
    db: Session,
    test_data: Sequence[Dict[str, Any]],
    modified_test_data: Sequence[Dict[str, Any]],
    api_url: str,
    key_func: Callable[[Dict[str, Any]], Any],
    find_func: Callable[[Session, Any], Any],
    compare_func: Callable[[Any, Dict[str, Any]], None],
):
    """
    Test an API endpoint which provides a bulk upsert for some object.
    Provide a hook to find objects that should have been inserted in the database
    and a hook to compare the found objects with the expected data.

    Args:
      client: REST API client to use for sending API requests.
      db: Session connected to the test database.
      test_data: JSON representation of 3 distinct objects -- used to test various configurations
        of upserting.
      modified_test_data: JSON representation of the same 3 objects (same primary key) with
        at least one attribute modified.  Used to verify updates work as expected.
      api_url: URL to the API endpoint to test.  Assumed to be an endpoint that performs an
        upsert on a model in response to a PUT request.
      key_func: Function that returns a unique key for an object given its JSON
        representation.
      find_func: Function used to find the database object for a given primary key.
      compare_func: Given a SQLAlchemy ORM instance and the "true" JSON representation of
        an object, this function should run assertions verifying they match.
    """
    assert len(test_data) == 3, "Must have 3 test observations to test upsert"
    assert (
        len(modified_test_data) == 3
    ), "Must have 3 modified test observations to test upsert"

    for original_obj, modified_obj in zip(test_data, modified_test_data):
        assert key_func(original_obj) == key_func(modified_obj)

    def sync_objs(json_objs: List[Dict[str, Any]]):
        res = client.put(api_url, json=json_objs)
        require_response_code(res, 200)

        for i, json_obj in enumerate(json_objs):
            key = key_func(json_obj)
            db_obj = find_func(db, key)
            assert db_obj is not None, f"Result for key {key} was None"
            compare_func(db_obj, json_obj)

    # Test single insert
    sync_objs([test_data[0]])

    # Test multiple insert
    sync_objs([test_data[1], test_data[2]])

    # Test single update
    sync_objs([modified_test_data[0]])

    # Test multiple update
    sync_objs([modified_test_data[1], modified_test_data[2]])


def make_test_articles(db_txn: Session) -> List[JsonObj]:
    test_articles = [
        {
            "article_id": 0,
            "pmid": 123,
            "title": "title",
            "abstract": "abstract",
            "publication_date": "2020-01-01",
            "tags": [],
            "mesh_terms": [],
            "embedding": None,
        },
        {
            "article_id": 2,
            "pmid": 124,
            "title": "title2",
            "abstract": "abstract2",
            "publication_date": "2020-01-02",
            "tags": [],
            "mesh_terms": [],
            "embedding": None,
        },
        {
            "article_id": 3,
            "pmid": 125,
            "title": "title3",
            "abstract": "abstract3",
            "publication_date": "2020-01-03",
            "tags": [],
            "mesh_terms": [],
            "embedding": None,
        },
    ]
    for model_data in test_articles:
        db_txn.add(models.Article(**model_data))
    db_txn.commit()

    return test_articles


def make_test_tags(db_txn: Session) -> List[JsonObj]:
    test_tags = [
        {"tag_id": 0, "name": "tag1", "value": "a"},
        {"tag_id": 1, "name": "tag2", "value": "b"},
        {"tag_id": 2, "name": "tag3", "value": "c"},
    ]
    for model_data in test_tags:
        db_txn.add(models.Tag(**model_data))

    db_txn.commit()

    return test_tags


def make_test_article_tags(
    db_txn: Session, articles: List[JsonObj], tags: List[JsonObj]
) -> List[JsonObj]:
    test_article_tags = []

    for article, tag in zip(articles, tags):
        article_tag = {
            "article_id": article["article_id"],
            "tag_id": tag["tag_id"],
        }

        db_txn.execute(models.article_tag.insert(values=article_tag))
        test_article_tags.append(article_tag)

    db_txn.commit()

    return test_article_tags


def make_test_mesh_terms(db_txn: Session) -> List[JsonObj]:
    test_mesh_terms = [
        {"mesh_id": "D001", "name": "mesh 1"},
        {"mesh_id": "D002", "name": "mesh 2"},
        {"mesh_id": "D003", "name": "mesh 3"},
    ]
    for model_data in test_mesh_terms:
        db_txn.add(models.MeSHTerm(**model_data))
    db_txn.commit()

    return test_mesh_terms


def make_test_article_mesh_terms(
    db_txn: Session, articles: List[JsonObj], mesh_terms: List[JsonObj]
) -> List[JsonObj]:
    test_article_mesh_terms = []

    for article, mesh_term in zip(articles, mesh_terms):
        article_mesh_term = {
            "article_id": article["article_id"],
            "mesh_id": mesh_term["mesh_id"],
        }

        db_txn.execute(models.article_mesh_term.insert(values=article_mesh_term))
        test_article_mesh_terms.append(article_mesh_term)

    db_txn.commit()

    return test_article_mesh_terms


def make_test_embeddings(db_txn: Session, articles: List[JsonObj]) -> List[JsonObj]:
    test_embeddings = []

    for article in articles:
        article_embedding = {
            "article_id": article["article_id"],
            "embedding": [random.random() for _ in range(10)],
        }
        db_txn.add(models.ArticleEmbedding(**article_embedding))
        test_embeddings.append(article_embedding)
    db_txn.commit()

    return test_embeddings


def make_test_article_sets(
    db_txn: Session,
) -> List[JsonObj]:
    test_article_sets = [
        {"article_set_id": 1, "name": "set1", "meta_json": {"param1": "val1"}},
        {"article_set_id": 2, "name": "set2", "meta_json": {"param2": "val2"}},
        {"article_set_id": 3, "name": "set3", "meta_json": {"param3": "val3"}},
    ]

    for model_data in test_article_sets:
        db_txn.add(models.ArticleSet(**model_data))

    db_txn.commit()
    return test_article_sets


def make_test_article_article_sets(
    db_txn: Session, articles: List[JsonObj], article_sets: List[JsonObj]
) -> List[JsonObj]:
    test_article_article_sets = []

    for article, article_set in zip(articles, article_sets):
        article_article_set = {
            "article_id": article["article_id"],
            "article_set_id": article_set["article_set_id"],
        }
        db_txn.execute(models.article_article_set.insert(values=article_article_set))
        test_article_article_sets.append(article_article_set)

    db_txn.commit()

    return test_article_article_sets
