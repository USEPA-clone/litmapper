import datetime as dt
import io
import math
import random
import shutil
from typing import Any, Callable, ContextManager, List, Tuple
from urllib.parse import urlencode

import pandas as pd
from redis import Redis
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from litmapper import models, schemas
from litmapper.db.literature import (
    find_article_litmapper_id,
    find_embedding,
    find_mesh_term,
)
from litmapper.kv.util import _make_blank_article_group_result, _make_blank_clustering_result
from litmapper.test.util import (
    JsonObj,
    make_test_article_article_sets,
    make_test_article_mesh_terms,
    make_test_article_sets,
    make_test_articles,
    make_test_embeddings,
    make_test_mesh_terms,
    require_response_code,
    verify_upsert,
)

random.seed(1)


def test_get_article(db_txn: Session, api_client: TestClient):
    res = api_client.get(f"/literature/article/?article_id=0")
    require_response_code(res, 404)

    res = api_client.get(f"/literature/article/?pmid=123")
    require_response_code(res, 404)

    test_articles = make_test_articles(db_txn)

    query_string = f"/literature/article/?article_id={test_articles[0]['article_id']}"
    res = api_client.get(query_string)
    require_response_code(res, 200)
    assert res.json() == test_articles[0]

    query_string = f"/literature/article/?pmid={test_articles[0]['pmid']}"
    res = api_client.get(query_string)
    require_response_code(res, 200)
    assert res.json() == test_articles[0]


def test_get_articles(db_txn: Session, api_client: TestClient):
    res = api_client.get("/literature/articles")
    require_response_code(res, 200)
    assert res.json() == []

    # Test returning all
    test_articles = make_test_articles(db_txn)
    res = api_client.get("/literature/articles")
    require_response_code(res, 200)
    assert res.json() == test_articles
    assert res.headers["X-Total-Count"] == "3"

    # Test returning by Article ID.
    test_article_ids = [article["article_id"] for article in test_articles]
    query = urlencode({"article_ids": test_article_ids}, doseq=True)
    id_url = f"/literature/articles?{query}"
    res = api_client.get(id_url)
    require_response_code(res, 200)
    assert res.json() == test_articles
    assert res.headers["X-Total-Count"] == "3"

    # Test pagination
    for page in range(len(test_articles)):
        res = api_client.get(f"/literature/articles?limit=1&page={page}")
        require_response_code(res, 200)
        assert res.json() == [test_articles[page]]
        assert res.headers["X-Total-Count"] == "3"

def test_upsert_articles(db_txn: Session, api_client: TestClient):
    test_data = make_test_articles(db_txn)
    modified_test_data = (
        {
            **test_data[0],
            "title": "title1_update",
        },
        {
            **test_data[1],
            "title": "title2_update",
        },
        {
            **test_data[2],
            "title": "title3_update",
        },
    )

    def key_func(json_obj: JsonObj) -> Any:
        return json_obj["article_id"]

    def find_func(db: Session, key: Any) -> Any:
        return find_article_litmapper_id(db, key)

    def compare_func(db_obj: Any, json_obj: JsonObj):
        for col in "title", "abstract", "publication_date":
            actual_val = json_obj[col]
            if col == "publication_date":
                actual_val = dt.datetime.strptime(actual_val, "%Y-%m-%d").date()
            assert (
                getattr(db_obj, col) == actual_val
            ), f"Mismatch for article ID {key_func(json_obj)}, column {col}"

    verify_upsert(
        api_client,
        db_txn,
        test_data,
        modified_test_data,
        "/literature/articles",
        key_func,
        find_func,
        compare_func,
    )


def test_get_mesh_terms(db_txn: Session, api_client: TestClient):
    res = api_client.get("/literature/mesh_terms")
    require_response_code(res, 200)
    assert res.json() == []

    test_mesh_terms = make_test_mesh_terms(db_txn)

    res = api_client.get("/literature/mesh_terms")
    require_response_code(res, 200)
    json = res.json()
    assert json == test_mesh_terms


def test_upsert_mesh_terms(db_txn: Session, api_client: TestClient):
    test_data = make_test_mesh_terms(db_txn)

    modified_test_data = (
        {**test_data[0], "name": "a2"},
        {**test_data[1], "name": "b2"},
        {**test_data[2], "name": "c2"},
    )

    def key_func(json_obj: JsonObj) -> Any:
        return json_obj["mesh_id"]

    def find_func(db: Session, key: Any) -> Any:
        return find_mesh_term(db, key)

    def compare_func(db_obj: Any, json_obj: JsonObj):
        assert db_obj.name == json_obj["name"]

    verify_upsert(
        api_client,
        db_txn,
        test_data,
        modified_test_data,
        "/literature/mesh_terms",
        key_func,
        find_func,
        compare_func,
    )


def test_upsert_article_mesh_terms(db_txn: Session, api_client: TestClient):
    test_articles = make_test_articles(db_txn)
    test_mesh_terms = make_test_mesh_terms(db_txn)
    test_data = make_test_article_mesh_terms(db_txn, test_articles, test_mesh_terms)

    # We don't have any other data to update based on the keys, so
    # just use the original test data
    modified_test_data = test_data

    def key_func(json_obj: JsonObj) -> Any:
        return (json_obj["article_id"], json_obj["mesh_id"])

    def find_func(db: Session, key: Any) -> Any:
        return db.execute(
            models.article_mesh_term.select()
            .where(models.article_mesh_term.c.article_id == key[0])
            .where(models.article_mesh_term.c.mesh_id == key[1])
        ).first()

    def compare_func(db_obj: Any, json_obj: JsonObj):
        assert (
            db_obj.article_id == json_obj["article_id"]
            and db_obj.mesh_id == json_obj["mesh_id"]
        )

    verify_upsert(
        api_client,
        db_txn,
        test_data,
        modified_test_data,
        "/literature/articles/mesh_terms",
        key_func,
        find_func,
        compare_func,
    )


def test_upsert_article_embeddings(db_txn: Session, api_client: TestClient):
    test_articles = make_test_articles(db_txn)
    test_data = make_test_embeddings(db_txn, test_articles)

    modified_test_data = [
        {**e, "embedding": [random.random() for _ in range(5)]} for e in test_data
    ]

    def key_func(json_obj: JsonObj) -> Any:
        return json_obj["article_id"]

    def find_func(db: Session, key: Any) -> Any:
        return find_embedding(db, key)

    def compare_func(db_obj: Any, json_obj: JsonObj):
        for db_val, json_val in zip(db_obj.embedding, json_obj["embedding"]):
            assert math.isclose(db_val, json_val)

    verify_upsert(
        api_client,
        db_txn,
        test_data,
        modified_test_data,
        "/literature/articles/embeddings",
        key_func,
        find_func,
        compare_func,
    )


def test_get_article_sets(db_txn: Session, api_client: TestClient):
    # If no data, the list endpoint should return an empty list
    # and the detail endpoint should return 404
    res = api_client.get("/literature/article_sets")
    require_response_code(res, 200)
    assert res.json() == []

    res = api_client.get("/literature/article_set/1")
    require_response_code(res, 404)

    test_article_sets = make_test_article_sets(db_txn)
    test_articles = make_test_articles(db_txn)
    test_article_article_sets = make_test_article_article_sets(
        db_txn, test_articles, test_article_sets
    )

    # Make sure the list endpoint returns the full list of article sets
    res = api_client.get("/literature/article_sets")
    require_response_code(res, 200)
    for res_article_set, article_set in zip(res.json(), test_article_sets):
        assert res_article_set == article_set

    for article_set, article_article_set in zip(
        test_article_sets, test_article_article_sets
    ):
        # Make sure the detail endpoint returns the article set data and all associated
        # articles
        res = api_client.get(
            f"/literature/article_set/{article_article_set['article_set_id']}"
        )
        require_response_code(res, 200)
        article_set_detail = res.json()
        for key in ("name", "meta_json"):
            assert article_set_detail[key] == article_set[key]

        res_article_ids = [a["article_id"] for a in article_set_detail["articles"]]
        assert len(res_article_ids) == 1
        assert res_article_ids[0] == article_article_set["article_id"]

        # Verify the CSV download endpoint for the set also works
        with api_client.get(
            f"/literature/article_set/{article_article_set['article_set_id']}/csv",
        ) as res:
            require_response_code(res, 200)
            res.raw.decode_content = True
            buf = io.BytesIO()
            shutil.copyfileobj(res.raw, buf)
            wrapper = io.TextIOWrapper(buf, encoding="utf-8")
            # Must seek back to the beginning after writing to the buffer...
            wrapper.seek(0)
            df = pd.read_csv(wrapper)
            # Should be one article associated with each article set
            assert len(df) == 1


def test_create_article_set(db_txn: Session, api_client: TestClient):
    # Blank article set should return a validation error
    blank: JsonObj = {}
    res = api_client.post("/literature/article_sets", json=blank)
    require_response_code(res, 422)

    test_articles = make_test_articles(db_txn)

    # Insert a valid article set with linked articles
    article_set = {"name": "test", "meta_json": {"param1": "val1"}}
    article_ids = [a["article_id"] for a in test_articles]
    res = api_client.post(
        "/literature/article_sets",
        json={
            "article_set": article_set,
            "article_ids": article_ids,
        },
    )
    require_response_code(res, 200)

    # Ensure returned data is correct
    api_article_set = res.json()
    for key in ("name", "meta_json"):
        assert api_article_set[key] == article_set[key]
        assert api_article_set.get("article_set_id") is not None

    # Ensure database data is correct
    db_article_set = db_txn.query(models.ArticleSet).first()
    for key in ("name", "meta_json"):
        assert getattr(db_article_set, key) == article_set[key]

    # Ensure all articles were linked correctly
    db_article_ids = set(a.article_id for a in db_article_set.articles)
    assert db_article_ids == set(article_ids)

    # Creating another set with the same name should raise an error
    dupe_article_set = {
        "name": "test",
        "meta_json": {},
    }

    res = api_client.post(
        "/literature/article_sets",
        json={"article_set": dupe_article_set, "article_ids": []},
    )
    require_response_code(res, 409)


def test_get_and_create_filter_set(
    db_txn: Session,
    test_kv: Redis,
    api_client: TestClient,
    task_await: Callable[[], ContextManager],
):
    # It's difficult to set up test database state in a way that's visible to
    # code running on the worker thread, so we won't try to end-to-end test
    # the filter logic here.  Just make sure the resource gets created.
    test_filter_set_params = schemas.FilterSetParams(
        full_text_search_query="TODO placeholder"
    )
    params_hash = str(hash(test_filter_set_params))

    # Should return 404 when object doesn't exist
    require_response_code(api_client.get(f"/literature/filter_set/{params_hash}"), 404)

    # Creating object should return 202
    # Await the async task to create the object to ensure it's created
    with task_await():
        create_res = api_client.post(
            "/literature/filter_sets", json=test_filter_set_params.dict()
        )
        require_response_code(create_res, 202)
        assert "Location" in create_res.headers

    status_res = api_client.get(create_res.headers["Location"])
    require_response_code(status_res, 200)
    status_obj = status_res.json()
    assert status_obj["status"] == schemas.JobStatus.SUCCESS.value

    created_res = api_client.get(status_obj["result_url"])
    require_response_code(created_res, 200)

    res_obj = schemas.FilterSetResult.parse_obj(created_res.json())
    assert res_obj == schemas.FilterSetResult(article_ids=[])

    # Make sure the article endpoint runs, although we can't test the logic with this
    articles_res = api_client.get(f"/literature/filter_set/{params_hash}/articles")
    require_response_code(articles_res, 200)
    assert articles_res.json() == []


def test_get_and_create_clustering(
    db_txn: Session,
    test_kv: Redis,
    api_client: TestClient,
    task_await: Callable[[], ContextManager],
):
    test_clustering_params = schemas.ClusteringParams(
        filter_set=schemas.FilterSetParams(
            full_text_search_query="TODO placeholder"
        ),
    )
    params_hash = str(hash(test_clustering_params))

    # Should return 404 when object doesn't exist
    require_response_code(api_client.get(f"/literature/clustering/{params_hash}"), 404)

    # Creating object should return 202
    # Await the async task to create the object to ensure it's created
    with task_await():
        create_res = api_client.post(
            "/literature/clustering", json=test_clustering_params.dict()
        )
        require_response_code(create_res, 202)
        assert "Location" in create_res.headers

    status_res = api_client.get(create_res.headers["Location"])
    require_response_code(status_res, 200)
    status_obj = status_res.json()
    assert status_obj["status"] == schemas.JobStatus.SUCCESS.value

    created_res = api_client.get(status_obj["result_url"])
    require_response_code(created_res, 200)

    res_obj = schemas.ClusteringResult.parse_obj(created_res.json())
    assert res_obj == _make_blank_clustering_result()


def test_get_and_create_article_group(
    db_txn: Session,
    test_kv: Redis,
    api_client: TestClient,
    task_await: Callable[[], ContextManager],
):
    test_article_group_params = schemas.ArticleGroupParams(
        clustering=schemas.ClusteringParams(
            filter_set=schemas.FilterSetParams(full_text_search_query="TODO placeholder")
        ),
    )
    params_hash = str(hash(test_article_group_params))

    # Should return 404 when object doesn't exist
    require_response_code(
        api_client.get(f"/literature/article_group/{params_hash}"), 404
    )

    # Creating object should return 202
    # Await the async task to create the object to ensure it's created
    with task_await():
        create_res = api_client.post(
            "/literature/article_groups", json=test_article_group_params.dict()
        )
        require_response_code(create_res, 202)
        assert "Location" in create_res.headers

    status_res = api_client.get(create_res.headers["Location"])
    require_response_code(status_res, 200)
    status_obj = status_res.json()
    assert status_obj["status"] == schemas.JobStatus.SUCCESS.value

    created_res = api_client.get(status_obj["result_url"])
    require_response_code(created_res, 200)

    res_obj = schemas.ArticleGroupResult.parse_obj(created_res.json())
    assert res_obj == _make_blank_article_group_result()
