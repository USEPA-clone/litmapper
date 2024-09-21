from typing import Callable, Tuple

import pytest
from pydantic import BaseModel
from redis import Redis
from sqlalchemy.orm import Session

from litmapper import errors, schemas
from litmapper.kv.util import (
    IN_PROGRESS_VAL,
    _make_blank_clustering_result,
    find_resource,
    get_resource_hash_key,
    is_in_progress,
    make_resource,
    reserve_resource,
)
from litmapper.test.util import (
    make_test_article_mesh_terms,
    make_test_articles,
    make_test_embeddings,
    make_test_mesh_terms,
)

# Function used to generate a resource's parameters and the expected output
# used for testing.  Function may perform additional needed database and/or key-value
# store setup as well.
ResourceFunc = Callable[[Session, Redis], Tuple[schemas.HashableBaseModel, BaseModel]]


def get_test_filter_set(
    db_txn: Session, kv: Redis
) -> Tuple[schemas.FilterSetParams, schemas.FilterSetResult]:
    # Construct a valid pair of params <-> result based on article-tag relationships in
    # the DB
    _ = make_test_articles(db_txn)

    params = schemas.FilterSetParams(full_text_search_query="TODO placeholder")

    result = schemas.FilterSetResult(article_ids=[0, 2])

    return params, result


def get_test_clustering(
    db_txn: Session, kv: Redis
) -> Tuple[schemas.ClusteringParams, schemas.ClusteringResult]:
    # Clustering with small datasets is error-prone and nearly impossible to
    # establish a known good result for.  Just make sure an empty clustering works.
    filter_set = schemas.FilterSetParams(full_text_search_query=None)
    make_resource(kv, db_txn, filter_set)

    params = schemas.ClusteringParams(filter_set=filter_set)
    result = _make_blank_clustering_result()
    return params, result


def get_test_article_group(
    db_txn: Session, kv: Redis, summary_terms: schemas.ArticleGroupSummaryTerms
) -> Tuple[schemas.ArticleGroupParams, schemas.ArticleGroupResult]:
    # Fake some clustering results and ensure there are some articles in the db.  Ask for
    # zero top terms back -- this should make most of the relevant code run without
    # creating a problem of determining what the actual numbers/order in the result should be
    articles = make_test_articles(db_txn)
    make_test_embeddings(db_txn, articles)

    # Create mesh terms if needed
    if summary_terms == schemas.ArticleGroupSummaryTerms.MESH_TERMS:
        mesh_terms = make_test_mesh_terms(db_txn)
        make_test_article_mesh_terms(db_txn, articles, mesh_terms)

    # This filter will include all articles
    filter_set = schemas.FilterSetParams(full_text_search_query=None)
    make_resource(kv, db_txn, filter_set)

    # Instead of creating a real clustering result, fake it so we have control over the clusters
    clustering_params = schemas.ClusteringParams(filter_set=filter_set)
    article_ids = [a["article_id"] for a in articles]
    group_ids = list(range(len(article_ids)))
    fake_clustering_result = schemas.ClusteringResult(
        article_ids=article_ids,
        labels=group_ids,
        coords=[[0, 0] for _ in articles],
        num_clusters=len(articles),
        metrics=schemas.ClusteringOverallMetrics(
            dbcv=None,
            silhouette_coefficient=None,
            davies_bouldin_index=None,
            dunn_index=None,
        ),
        label_info=schemas.ClusteringLabelInfo(
            n_per_cluster=[1 for _ in set(group_ids)],
            cluster_validity_indices=[0.0 for _ in range(len(set(group_ids)))],
            cluster_center_coords=[[0.0, 0.0] for _ in range(len(set(group_ids)))],
        ),
    )
    kv.hset(
        get_resource_hash_key(schemas.ClusteringParams),
        str(hash(clustering_params)),
        fake_clustering_result.json(),
    )

    article_groups = []
    for i, group_id in enumerate(group_ids):
        article_group = schemas.ArticleGroup(
            id=group_id,
            num_articles=1,
            article_ids=[article_ids[i]],
            top_terms=[],
        )
        article_groups.append(article_group)

    return (
        schemas.ArticleGroupParams(
            clustering=clustering_params, num_terms=0, summary_terms=summary_terms
        ),
        schemas.ArticleGroupResult(result=article_groups),
    )


def get_test_article_group_named_entities(
    db_txn: Session, kv: Redis
) -> Tuple[schemas.ArticleGroupParams, schemas.ArticleGroupResult]:
    return get_test_article_group(
        db_txn, kv, schemas.ArticleGroupSummaryTerms.NAMED_ENTITIES
    )


def get_test_article_group_mesh(
    db_txn: Session, kv: Redis
) -> Tuple[schemas.ArticleGroupParams, schemas.ArticleGroupResult]:
    return get_test_article_group(
        db_txn, kv, schemas.ArticleGroupSummaryTerms.MESH_TERMS
    )


@pytest.mark.parametrize(
    "resource_func",
    [
        get_test_filter_set,
        get_test_clustering,
        get_test_article_group_mesh,
        get_test_article_group_named_entities,
    ],
)
def test_find_resource(
    test_kv: Redis,
    db_txn: Session,
    resource_func: ResourceFunc,
):
    params, result = resource_func(db_txn, test_kv)
    resource_cls = params.__class__
    resource_hash_key = get_resource_hash_key(resource_cls)

    # Should raise not found error if resource doesn't exist
    with pytest.raises(errors.ResourceDoesNotExist):
        find_resource(test_kv, params)

    # Should raise in progress error if resource is in progress
    params_hash = str(hash(params))
    test_kv.hset(resource_hash_key, key=params_hash, value=IN_PROGRESS_VAL)

    with pytest.raises(errors.ResourceCreationInProgress):
        find_resource(test_kv, params)
    assert is_in_progress(test_kv.hget(resource_hash_key, params_hash))

    # Should return the result if it's been set
    test_kv.hset(
        resource_hash_key,
        key=params_hash,
        value=result.json(),
    )

    assert find_resource(test_kv, params) == result


def test_reserve_resource(test_kv: Redis, db_txn: Session):
    params, result = get_test_filter_set(db_txn, test_kv)
    params_hash = str(hash(params))
    resource_cls = params.__class__
    resource_hash_key = get_resource_hash_key(resource_cls)

    # Should fail if resource already exists
    test_kv.hset(resource_hash_key, key=params_hash, value=result.json())

    with pytest.raises(errors.ResourceExists):
        with reserve_resource(test_kv, params):
            pass

    # Shouldn't fail if resource exists and forcing
    with reserve_resource(test_kv, params, force=True):
        pass

    test_kv.hdel(resource_hash_key, params_hash)

    # Should fail if resource is already marked as in-progress
    test_kv.hset(resource_hash_key, key=params_hash, value=IN_PROGRESS_VAL)

    with pytest.raises(errors.ResourceCreationInProgress):
        with reserve_resource(test_kv, params):
            pass

    # Shouldn't fail if resource is already marked as in-progress and forcing
    with reserve_resource(test_kv, params, force=True):
        pass

    test_kv.hdel(resource_hash_key, params_hash)

    # Should handle errors appropriately by deleting in-progress value
    try:
        with reserve_resource(test_kv, params):
            raise RuntimeError
    except RuntimeError:
        assert not is_in_progress(test_kv.hget(resource_hash_key, params_hash))

    # Should run without an error during normal operation and mark the resource in-progress
    with reserve_resource(test_kv, params):
        assert is_in_progress(test_kv.hget(resource_hash_key, params_hash))


@pytest.mark.parametrize(
    "resource_func",
    [
        get_test_filter_set,
        get_test_clustering,
        get_test_article_group_mesh,
        get_test_article_group_named_entities,
    ],
)
def test_make_resource(
    test_kv: Redis,
    db_txn: Session,
    resource_func: ResourceFunc,
):
    params, result = resource_func(db_txn, test_kv)
    resource_cls = params.__class__
    resource_hash_key = get_resource_hash_key(resource_cls)
    params_hash = str(hash(params))

    # Should do nothing if resource is in progress
    test_kv.hset(resource_hash_key, key=params_hash, value=IN_PROGRESS_VAL)

    make_resource(test_kv, db_txn, params)
    # Make sure the KV store wasn't modified
    assert is_in_progress(test_kv.hget(resource_hash_key, params_hash))

    test_kv.hdel(resource_hash_key, params_hash)

    # Should create the resource if it didn't already exist
    make_resource(test_kv, db_txn, params)

    assert find_resource(test_kv, params) == result

    # Subsequent creation shouldn't modify the resource
    make_resource(test_kv, db_txn, params)

    assert find_resource(test_kv, params) == result
