import logging
import os
import sys
import time
from collections import Counter
from contextlib import contextmanager
from functools import lru_cache
from itertools import chain
from typing import Any, Callable, Dict, List, Type, cast

import numpy as np
import numpy.typing as npt
import pandas as pd
import spacy
import tensorflow_hub as hub
from dramatiq.middleware import Shutdown
from hdbscan import HDBSCAN, validity_index
from jqmcvi.base import dunn_fast as dunn_index_score
from pydantic import BaseModel
from redis import ConnectionPool, Redis
from scipy.spatial.distance import cosine as cosine_distance
from sklearn.metrics import davies_bouldin_score, silhouette_score
from sqlalchemy import String, case
from sqlalchemy import cast as sql_cast
from sqlalchemy.dialects.postgresql import ARRAY, array
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import array_agg
from umap import UMAP

from litmapper import errors, models, schemas
from litmapper.db.literature import filter_articles

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

REDIS_URI = os.environ["REDIS_URI"]
LOGGER = logging.getLogger()

pool = ConnectionPool.from_url(REDIS_URI)


@contextmanager
def get_kv():
    try:
        kv = Redis(connection_pool=pool)
        yield kv
    finally:
        kv.close()


def get_kv_dep():
    # Convert context manager to a generator for use with FastAPI
    with get_kv() as kv:
        yield kv


# This module uses a dynamic approach to avoid boilerplate retrieving and creating
# resources of different classes. A "resource" is loosely defined as a concept which has
# a hashable parameters object and some result object.  Ex. FilterSetParams, FilterSetResult
# We can then store the result in a hashset in the key-value store keyed by the hash of the
# parameters.  This approach is suitable for results of long-running computations which should
# be cached at the application level but whose schema is too fluid to store in the database.

# Use find_resource() to retrieve the resource of a given type
# (you will probably need to cast() the result to the desired result class for mypy to approve)
# and use make_resource() to create the resource of a given type.

# To implement a new resource type, do the following:
#  1. Create a hash key name for that resource in RESOURCE_HASH_KEYS below
#  2. Record the link between param class and result class in RESOURCE_RESULT_CLASSES below
#  2. Create an implementation to make the resource in RESOURCE_CREATION_FUNCS further below
# The rest of the logic (checking for existence, throwing the appropriate error during
# creation, converting to JSON and back for storage in Redis, etc.) will carry over for
# the new resource.  You'll also want to add a new set of parameters to the tests in
# `test_literature_kv.py` corresponding to the new resource type.


RESOURCE_HASH_KEYS = {
    schemas.FilterSetParams: "filter_sets",
    schemas.ClusteringParams: "clusterings",
    schemas.ArticleGroupParams: "article_groups",
}

RESOURCE_RESULT_CLASSES = {
    schemas.FilterSetParams: schemas.FilterSetResult,
    schemas.ClusteringParams: schemas.ClusteringResult,
    schemas.ArticleGroupParams: schemas.ArticleGroupResult,
}


def get_resource_hash_key(resource_cls: Type[schemas.HashableBaseModel]) -> str:
    # Return the hash key used in Redis to store resources of the given class.
    hash_key = RESOURCE_HASH_KEYS.get(resource_cls)
    if hash_key is None:
        raise TypeError(f"unsupported resource class: {resource_cls}")
    return hash_key


def get_resource_result_cls(
    resource_cls: Type[schemas.HashableBaseModel],
) -> Type[schemas.BaseModel]:
    # Return the result class for parameters of the given class
    result_cls = RESOURCE_RESULT_CLASSES.get(resource_cls)
    if result_cls is None:
        raise TypeError(f"unsupported resource class: {resource_cls}")
    return result_cls


IN_PROGRESS_VAL = ""


def is_in_progress(resource_val: Any) -> bool:
    # Result may be a bytestring, so we need to check the length rather
    # than compare directly
    return resource_val is not None and len(resource_val) == 0


def find_resource_hash(
    kv: Redis, resource_cls: Type[schemas.HashableBaseModel], params_hash: str
) -> BaseModel:
    """
    Find a resource of the given class using the given hash. Raise appropriate
    errors if the resource doesn't exist or is being created.

    Args:
      kv: Key-value store connection
      resource_cls: Type of resource to find
      params_hash: Hash of the resource to look up

    Returns:
      The resource object, if found.
    """
    hash_key = get_resource_hash_key(resource_cls)
    result_cls = get_resource_result_cls(resource_cls)

    val = kv.hget(hash_key, params_hash)
    if val is None:
        raise errors.ResourceDoesNotExist(f"{resource_cls} with hash {params_hash}")
    elif is_in_progress(val):
        raise errors.ResourceCreationInProgress(
            f"{resource_cls} with hash {params_hash}"
        )
    else:
        return result_cls.parse_raw(val)


def find_resource(kv: Redis, params: schemas.HashableBaseModel) -> BaseModel:
    """
    Find the results for the given parameters if they exist. Raise appropriate
    errors if the resource doesn't exist or is being created.

    Args:
      kv: Key-value store connection
      params: Parameters for the resource to find

    Returns:
      The resource object, if found.
    """
    resource_cls = params.__class__
    params_hash = str(hash(params))
    params_repr = repr(params)

    try:
        return find_resource_hash(kv, resource_cls, params_hash)
    except errors.ResourceDoesNotExist:
        raise errors.ResourceDoesNotExist(params_repr)
    except errors.ResourceCreationInProgress:
        raise errors.ResourceCreationInProgress(params_repr)


def _make_filter_set(
    db: Session, kv: Redis, params: schemas.FilterSetParams
) -> schemas.FilterSetResult:
    article_ids = filter_articles(
        db,
        db.query(models.Article.article_id),
        params.full_text_search_query,
    )
    if params.limit is not None:
        article_ids = article_ids.limit(params.limit)
    article_ids = article_ids.all()

    # Have to unpack SQLAlchemy collection of tuples into a list
    return schemas.FilterSetResult(article_ids=[i[0] for i in article_ids])


def _make_blank_clustering_result():
    """
    Returns:
      An empty clustering result suitable when 0 articles were found.
    """
    return schemas.ClusteringResult(
        article_ids=[],
        labels=[],
        coords=[],
        num_clusters=0,
        metrics=schemas.ClusteringOverallMetrics(
            dbcv=None,
            silhouette_coefficient=None,
            davies_bouldin_index=None,
            dunn_index=None,
        ),
        label_info=schemas.ClusteringLabelInfo(
            n_per_cluster=[],
            cluster_center_coords=[],
            cluster_validity_indices=[],
        ),
    )


def _make_clustering(
    db: Session, kv: Redis, params: schemas.ClusteringParams
) -> schemas.ClusteringResult:
    """
    Run a clustering algorithm with the given parameters.  Will retrieve high-dimensional
    article embeddings, reduce to 2 dimensions using UMAP, cluster using HDBSCAN, and
    return the results with some evaluation metrics.

    Args:
      db: Database connection for retrieving articles
      kv: KV store connection for retrieving filter set results
      params: Clustering algorithm parameters

    Returns:
      Results of clustering
    """
    LOGGER.info(f"Starting clustering with params {params}")

    # Poll for creation of the filter set, in case it's in progress
    while True:
        try:
            filtered_article_ids = cast(
                schemas.FilterSetResult, find_resource(kv, params.filter_set)
            ).article_ids
            LOGGER.info("Found filter set resource")
            break
        except errors.ResourceCreationInProgress:
            LOGGER.debug(
                f"Waiting for filter set resource to be created with params: {params.filter_set}"
            )
        time.sleep(1)

    # Used when running clustering for temporary pubmed articles
    if params.filter_set.temp_article_ids:
        temp_article_ids = list(params.filter_set.temp_article_ids)
        if params.filter_set.full_text_search_query is None:
            # If no other filters are specified, use only selected temporary pubmed articles
            filtered_article_ids = temp_article_ids
        else:
            # Otherwise, use articles that match filters + selected temporary pubmed articles
            filtered_article_ids = filtered_article_ids + temp_article_ids

    if len(filtered_article_ids) == 0:
        # Can't cluster 0 articles, so return a blank result
        return _make_blank_clustering_result()

    filtered_article_data = (
        db.query(models.Article)
        .filter(models.Article.article_id.in_(filtered_article_ids))
        .join(models.Article.embeddings)
        .with_entities(models.Article.article_id, models.ArticleEmbedding)
        .all()
    )

    article_ids, article_embeddings = zip(*filtered_article_data)
    article_embeddings = [embed_obj.use_embedding for embed_obj in article_embeddings]
    LOGGER.info(f"Retrieved {len(article_ids)} filtered articles to cluster")

    umap = UMAP(
        n_neighbors=params.umap_n_neighbors,
        metric=params.umap_metric,
        min_dist=params.umap_min_dist,
        random_state=np.random.RandomState(params.umap_seed),
    )
    umap_data = umap.fit_transform(article_embeddings)
    LOGGER.info("Reduced dimensionality")

    clusterer = HDBSCAN(
        min_cluster_size=params.hdbscan_min_cluster_size,
        min_samples=params.hdbscan_min_samples,
        cluster_selection_epsilon=params.hdbscan_cluster_selection_epsilon,
    )
    try:
        clusterer.fit(umap_data)
        if params.hdbscan_do_flat_clustering:
            # Get the clustering from the single linkage tree directly, so we can
            # manually cut up and down the hierarchy to get a specific level of aggregation
            raw_labels = clusterer.single_linkage_tree_.get_clusters(
                params.hdbscan_cluster_flattening_epsilon,
                params.hdbscan_min_cluster_size,
            )
        else:
            raw_labels = clusterer.labels_
    except ValueError as e:
        LOGGER.warning(str(e))
        raise ValueError(
            "Clustering Failed. Likely due to too few articles. Try again with additional articles."
        )

    # 0-indexed labels - add 1 to get the count
    num_clusters = raw_labels.max() + 1
    LOGGER.info(f"Generated {num_clusters} clusters")

    # The clustering output will report -1 for a point that doesn't have a cluster
    # That's a little confusing, potentially, so just convert to None
    labels = [None if cluster_id == -1 else cluster_id for cluster_id in raw_labels]

    # Calculate metrics
    if params.hdbscan_min_cluster_size <= 2 or params.hdbscan_min_samples <= 2:
        dbcv = None
        cluster_validity_indices: npt.NDArray[np.float64] = np.array([])
        LOGGER.warning(
            "Validity index cannot be calculated when HDBSCAN min cluster size or min samples are 2 or less."
        )
    else:
        # Cast required here to avoid dtype error
        dbcv, cluster_validity_indices = validity_index(
            umap_data.astype(np.float64), raw_labels, per_cluster_scores=True
        )
        cluster_validity_indices = cluster_validity_indices.tolist()
        outliers = -1 in raw_labels
        if outliers:  # index only calculated for non-outlier clusters
            cluster_validity_indices = [0.0] + cluster_validity_indices

    silhouette = silhouette_score(umap_data, raw_labels)
    davies_bouldin = davies_bouldin_score(umap_data, raw_labels)
    dunn = dunn_index_score(umap_data, raw_labels)

    n_per_cluster = np.unique(raw_labels, return_counts=True)[1].tolist()
    cluster_center_coords = (
        pd.DataFrame(
            np.hstack((umap_data, raw_labels.reshape(-1, 1))),
            columns=["d1", "d2", "label"],
        )
        .groupby("label")
        .mean()
        .values.tolist()
    )
    result = schemas.ClusteringResult(
        article_ids=article_ids,
        labels=labels,
        coords=umap_data.tolist(),
        num_clusters=num_clusters,
        metrics=schemas.ClusteringOverallMetrics(
            dbcv=dbcv,
            silhouette_coefficient=silhouette,
            davies_bouldin_index=davies_bouldin,
            dunn_index=dunn,
        ),
        label_info=schemas.ClusteringLabelInfo(
            n_per_cluster=n_per_cluster,
            cluster_center_coords=cluster_center_coords,
            cluster_validity_indices=cluster_validity_indices,
        ),
    )
    return result


@lru_cache(maxsize=1)
def _load_embedding_module():
    """
    Load the module used for generating embeddings.  This is slow and will be
    used multiple times across the lifetime of a worker, so cache the result.
    """
    return hub.load("https://tfhub.dev/google/universal-sentence-encoder/4")


@lru_cache(maxsize=1)
def _load_nlp(disable: str = ""):
    """
    Load the spaCy language model used for parsing text.  This is slow and
    will be used multiple times across the lifetime of a worker, so cache the
    result.
    """
    disable_parsed = [component for component in disable.split(",") if component]
    return spacy.load("en_core_sci_md", disable=disable_parsed)


def _make_blank_article_group_result() -> schemas.ArticleGroupResult:
    """
    Returns:
      A blank ArticleGroupResult suitable when no articles were clustered.
    """
    return schemas.ArticleGroupResult(
        result=[
            schemas.ArticleGroup(id=0, num_articles=0, article_ids=[], top_terms=[])
        ]
    )


def _make_article_groups(
    db: Session, kv: Redis, params: schemas.ArticleGroupParams
) -> schemas.ArticleGroupResult:
    # Poll for the clustering result, in case it's in progress
    while True:
        try:
            clustering_result = cast(
                schemas.ClusteringResult, find_resource(kv, params.clustering)
            )
            LOGGER.info("Found clustering result")
            break
        except errors.ResourceCreationInProgress:
            LOGGER.debug(
                f"Waiting for clustering resource to be created with params: {params.clustering}"
            )
        time.sleep(1)

    filtered_article_ids = clustering_result.article_ids
    # Can't run the below SQL queries if we don't have any articles to group
    if len(filtered_article_ids) == 0:
        return _make_blank_article_group_result()

    articles = db.query(models.Article)
    filtered_articles = articles.filter(
        models.Article.article_id.in_(filtered_article_ids)
    )
    joined_articles = filtered_articles.join(models.Article.embeddings)
    filtered_article_data = joined_articles.with_entities(
        models.Article.article_id,
        models.Article.all_text,
        models.ArticleEmbedding,
    )

    # filtered_article_data = (
    #     db.query(models.Article)
    #     .filter(models.Article.article_id.in_(filtered_article_ids))
    #     .join(models.Article.embeddings)
    #     .with_entities(
    #         models.Article.article_id,
    #         models.Article.all_text,
    #         models.ArticleEmbedding,
    #     )
    # )

    embed = _load_embedding_module()
    article_cluster_df = pd.DataFrame(
        {"cluster": clustering_result.labels}, index=filtered_article_ids
    )

    if params.summary_terms == schemas.ArticleGroupSummaryTerms.MESH_TERMS:
        mesh_terms = (
            db.query(
                models.Article.article_id,
                array_agg(models.MeSHTerm.name).label("mesh_term_array"),
            )
            .join(
                models.article_mesh_term,
                models.Article.article_id == models.article_mesh_term.c.article_id,
                isouter=True,
            )
            .join(
                models.MeSHTerm,
                models.article_mesh_term.c.mesh_id == models.MeSHTerm.mesh_id,
            )
            .group_by(models.Article.article_id)
            .subquery()
        )

        filtered_article_data = filtered_article_data.join(
            mesh_terms,
            models.Article.article_id == mesh_terms.c.article_id,
            isouter=True,
        ).with_entities(
            models.Article.article_id,
            models.Article.all_text,
            models.ArticleEmbedding,
            case(
                [
                    (
                        mesh_terms.c.mesh_term_array.is_(None),
                        # Looks like incorrect mypy stubs here
                        sql_cast(array([]), ARRAY(String)),  # type: ignore
                    )
                ],
                else_=mesh_terms.c.mesh_term_array,
            ),
        )

        (
            mesh_term_article_ids,
            article_texts,
            full_article_embeddings,
            mesh_term_arrays,
        ) = zip(*filtered_article_data.all())

        article_embeddings = [
            embed_obj.use_embedding for embed_obj in full_article_embeddings
        ]

        article_df = article_cluster_df.join(
            pd.DataFrame(
                {
                    "text": article_texts,
                    "embedding": article_embeddings,
                    "summary_terms": mesh_term_arrays,
                },
                index=mesh_term_article_ids,
            )
        )
    elif params.summary_terms == schemas.ArticleGroupSummaryTerms.NAMED_ENTITIES:
        nlp = _load_nlp(disable="tagger,parser")

        (
            named_entity_article_ids,
            article_texts,
            article_embeddings,
        ) = zip(*filtered_article_data.all())

        article_embeddings = [
            embed_obj.use_embedding for embed_obj in article_embeddings
        ]

        # Save named entities keyed by article ID for later use displaying to user
        # They'll be sorted and filtered later for articles in a cluster
        article_named_entities = []
        for article in nlp.pipe(article_texts):
            named_entities = set()
            for ent in article.ents:
                ent_text = ent.text.lower()
                named_entities.add(ent_text)
            article_named_entities.append(list(named_entities))

        article_df = article_cluster_df.join(
            pd.DataFrame(
                {
                    "text": article_texts,
                    "embedding": article_embeddings,
                    "summary_terms": article_named_entities,
                },
                index=named_entity_article_ids,
            )
        )

    else:
        raise ValueError(f"Unsupported summary term type: {params.summary_terms}")

    LOGGER.info(f"Generating group summaries for {article_df.shape[0]} articles")

    result = []
    # Generate final results
    group_ids: List[int] = []
    group_num_articles: List[int] = []
    group_article_ids: List[List[int]] = []
    group_top_terms: List[List[str]] = []
    num_clusters = 0

    for cluster, cluster_articles in article_df.groupby("cluster", sort=False):
        num_clusters += 1
        group_ids.append(cluster)
        group_num_articles.append(cluster_articles.shape[0])
        group_article_ids.append(cluster_articles.index.tolist())

        # Get summary term counts for each cluster along with counts and embeddings
        summary_term_counts = Counter(
            chain.from_iterable((cluster_articles["summary_terms"]))
        )

        # Exclude any terms not found more than once across the cluster
        # from candidacy for being centroid terms
        candidates = [c for c in summary_term_counts if summary_term_counts[c] > 1]

        # Calculate embeddings for all candidates
        if candidates:
            unmapped_candidate_embeddings = embed(candidates).numpy()

            candidate_embeddings = dict(zip(candidates, unmapped_candidate_embeddings))

            # Get article embeddings and calculate the cluster centroid
            cluster_embeddings = np.vstack(cluster_articles["embedding"].tolist())
            cluster_centroid_embedding = np.average(cluster_embeddings, axis=0)

            summary_term_distances = {
                term: cosine_distance(embedding, cluster_centroid_embedding)
                for term, embedding in candidate_embeddings.items()
            }

            top_terms = []
            for i, term in enumerate(
                sorted(summary_term_distances, key=lambda k: summary_term_distances[k])
            ):
                top_terms.append(term)
                if i >= (params.num_terms - 1):
                    break

            group_top_terms.append(top_terms)
        else:
            top_terms = []
            group_top_terms.append(top_terms)
        article_group = schemas.ArticleGroup(
            id=cluster,
            num_articles=cluster_articles.shape[0],
            article_ids=cluster_articles.index.tolist(),
            top_terms=top_terms,
        )
        result.append(article_group)
    LOGGER.info(f"Generated {num_clusters} group summaries")
    article_group_result = schemas.ArticleGroupResult(result=result)
    return article_group_result


RESOURCE_CREATION_FUNCS: Dict[
    Type[schemas.HashableBaseModel],
    Callable[[Session, Redis, Any], Any],
] = {
    schemas.FilterSetParams: _make_filter_set,
    schemas.ClusteringParams: _make_clustering,
    schemas.ArticleGroupParams: _make_article_groups,
}


def get_resource_creation_func(
    resource_cls: Type[schemas.HashableBaseModel],
) -> Callable[[Session, Redis, Any], Any]:
    # Return the function used to create resources of the given class
    func = RESOURCE_CREATION_FUNCS.get(resource_cls)
    if func is None:
        raise TypeError(f"unsupported resource class: {resource_cls}")
    return func


@contextmanager
def reserve_resource(kv: Redis, params: schemas.HashableBaseModel, force: bool = False):
    """
    Atomically record in the key-value store that the given resource is being created.
    Prevents other workers from attempting to create the same resource.
    If the value was already present in the store, raise an appropriate
    exception to allow the caller to decide how to handle it.

    Args:
      kv: Redis client to store the in-progress data
      params: Parameters for the resource being created
      force: If True, reserve the resource even if it's already in-progress or doesn't exist
    """
    hash_key = get_resource_hash_key(params.__class__)
    params_hash = str(hash(params))

    # Use a pipeline to make these operations atomic
    pipe = kv.pipeline()
    result = (
        pipe.hget(hash_key, params_hash)
        .hsetnx(hash_key, params_hash, IN_PROGRESS_VAL)
        .execute()
    )
    prev_val = result[0]

    if prev_val is None or force:
        if force:
            # We may not have reset the in-progress status above if it was already
            # in-progress
            kv.hset(hash_key, params_hash, IN_PROGRESS_VAL)
            LOGGER.info("Forcing resource creation")

        # The resource didn't already exist -- we're clear to create it
        try:
            yield
        except (Exception, Shutdown):
            LOGGER.info("Cleaning up resource reservation due to error/shutdown")
            # If we encounter an error during creation or are part of a worker thread
            # which is being shut down, remove the in-progress
            # key so it doesn't get stuck
            kv.hdel(hash_key, params_hash)
            raise

    elif is_in_progress(prev_val):
        # The resource is already being created by another worker
        raise errors.ResourceCreationInProgress(
            f"resource creation in-progress for params {params}"
        )
    else:
        # Someone else has already finished creating the resource
        raise errors.ResourceExists(f"resource already created for params {params}")


def make_resource(
    kv: Redis, db: Session, params: schemas.HashableBaseModel, force: bool = False
):
    """
    Create some kind of resource based on the given parameters and store the
    result in the key-value store.

    NOTE: Calling code is responsible for ensuring the resource is marked as in-progress
    during creation, since it may have dependencies which calling code is also
    creating.

    Args:
      kv: Redis client for retrieving/storing data
      db: Database connection for retrieving data during creation
      params: Parameters for the resource to create
      force: If True, create the resource even if it already exists or is in-progress
    """
    resource_cls = params.__class__
    result_cls = get_resource_result_cls(resource_cls)

    # Make sure the resource isn't being created before we try to create it,
    # and don't recreate it if it already exists
    try:

        with reserve_resource(kv, params, force=force):
            param_hash = str(hash(params))
            hash_key = get_resource_hash_key(resource_cls)
            LOGGER.info(f"Creating {result_cls} with params {params}")

            # Now do the work to create the resource
            resource_creation_func = get_resource_creation_func(resource_cls)
            result = resource_creation_func(db, kv, params)
            kv.hset(
                hash_key,
                key=param_hash,
                value=result.json(),
            )
            LOGGER.info(f"Resource {result_cls} created with params {params}")

    except errors.ResourceCreationInProgress:
        LOGGER.info(
            f"Stopping creation: {result_cls} creation in-progress with params {params}"
        )
    except errors.ResourceExists:
        LOGGER.info(
            f"Stopping creation: {result_cls} already exists with params {params}"
        )
