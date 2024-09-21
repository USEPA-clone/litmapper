import io
import logging
from datetime import datetime
from typing import List, Optional, cast

import pandas as pd
import rispy
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from redis import Redis
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from litmapper import errors, models, schemas, tasks
from litmapper.db.literature import (
    add_temp_articles_pubmed,
    crosstab_article_tags,
    delete_article_set,
    filter_articles,
    find_article_litmapper_id,
    find_article_pmid,
    find_article_set,
    find_articles_litmapper_ids,
    find_articles_pmids,
    get_article_count,
    insert_article_set,
    process_article,
    remove_temp_article_batch,
    update_embeddings,
)
from litmapper.db.load_pubmed import load_pmids_from_file
from litmapper.db.pubmed import search_articles_count
from litmapper.db.util import do_bulk_upsert, fuzzy_match_titles, get_db_dep, paginate
from litmapper.kv.util import find_resource_hash, get_kv_dep
from litmapper.routers.util import raise_404_if_none

router = APIRouter()

LOGGER = logging.getLogger(__name__)


@router.get("/article", response_model=schemas.Article)
def get_article(
    article_id: int = Query(
        None,
        title="LitMapper Article ID",
        description="LitMapper database ID of article to filter on. If LitMapper Article "
        "ID is specified alongside PubMed ID, only LitMapper Article ID will be "
        "searched for.",
    ),
    pmid: int = Query(
        None,
        title="PubMed ID",
        description="PubMed ID of article to search for. If LitMapper Article "
        "ID is specified alongside PubMed ID, only LitMapper Article ID will be "
        "searched for.",
    ),
    db: Session = Depends(get_db_dep),
):
    if article_id is not None:
        return raise_404_if_none(find_article_litmapper_id(db, article_id))
    else:
        return raise_404_if_none(find_article_pmid(db, pmid))


@router.get("/articles", response_model=List[schemas.Article])
def get_articles(
    response: Response,
    article_ids: List[int] = Query(
        [],
        title="LitMapper Article IDs",
        description="IDs of articles to filter on. If Article IDs "
        "are specified alongside filter or exact tags, IDs will override tags--"
        "only articles matching a listed ID will be returned.",
    ),
    pmids: List[int] = Query(
        [],
        title="Pubmed ID",
        description="PubMed IDs of articles to filter on. If PubMed ID "
        "are specified alongside filter or exact tags, IDs will override tags--"
        "only articles matching a listed ID will be returned.",
    ),
    full_text_search_query: Optional[str] = None,
    db: Session = Depends(get_db_dep),
    page: int = Query(
        0,
        title="Page number",
        description="Page of results to return (starting with 0).",
    ),
    limit: int = Query(
        1000,
        title="Page limit",
        description="Max number of results to return per page.",
    ),
):
    articles = db.query(models.Article).order_by(models.Article.article_id)
    try:
        # If article IDs are specified, only return articles that match an article id.
        if article_ids is not None and article_ids:
            articles = find_articles_litmapper_ids(db, article_ids)
        elif pmids is not None and len(pmids) > 0:
            articles = find_articles_pmids(db, pmids)
        else:
            articles = filter_articles(
                db, articles, full_text_search_query
            )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    # Add total count (disregarding pagination) to the response
    paginated_articles, total_count = paginate(articles, page, limit)
    response.headers["X-Total-Count"] = str(total_count)
    return paginated_articles


@router.put("/articles")
def upsert_articles(
    articles: List[schemas.ArticleCreate], db: Session = Depends(get_db_dep)
):
    do_bulk_upsert(db, models.Article, articles, {"pmid"})

    return {"message": f"Successfully upserted {len(articles)} articles"}


@router.post("/articles/add_pubmed_ids")
def add_articles_pubmed_ids(
    articles_add_payload: schemas.ArticlesAddPubmedPayload,
    db: Session = Depends(get_db_dep),
):
    add_temp_articles_pubmed(db, articles_add_payload)


@router.post("/articles/upload", status_code=status.HTTP_201_CREATED)
def upload_articles(
    file: UploadFile = File(...),
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db_dep),
):
    search_query = ""
    articles_to_create = []

    LOGGER.debug(f"Processing {file.filename}...")

    # Check if the file is a CSV or RIS file
    if file.filename and file.filename.endswith(".csv"):
        df = pd.read_csv(file.file)

        df["id"] = df["id"].astype(int)
        df = df.sort_values(by="id", ascending=True, ignore_index=True)

        pubmed_ids = df["id"].tolist()

        LOGGER.debug("Getting article counts...")
        article_count = get_article_count(db, pubmed_ids, len(df))

        if (
            len(article_count["pmids_in_litmapper"]) > 0
            and article_count["pmids_in_litmapper"][0] == "More than 2,000 results"
        ) or (
            len(article_count["pmids_not_in_litmapper"]) > 0
            and article_count["pmids_not_in_litmapper"][0] == "More than 2,000 results"
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Too many articles requested. Please do not attempt to add more than 2,000 articles.",
            )

        LOGGER.debug("Fuzzy matching titles...")
        fuzzy_match_titles(df["title"].tolist(), pubmed_ids)

        articles = df.to_dict("records")

        LOGGER.debug("Parsing articles...")
        for article in articles:
            processed_article = process_article(article, "csv")
            articles_to_create.append(processed_article)
    elif file.filename and file.filename.endswith(".ris"):
        ris_content = file.file.read().decode("utf-8")
        articles = rispy.loads(ris_content)
        sorted_articles = sorted(articles, key=lambda x: int(x["id"]))

        pubmed_ids = []
        titles = []

        LOGGER.debug("Parsing articles...")
        for article in sorted_articles:
            pubmed_ids.append(int(article["id"]))
            titles.append(article["title"])

            processed_article = process_article(article, "ris")
            articles_to_create.append(processed_article)

        LOGGER.debug("Getting article counts...")
        article_count = get_article_count(db, pubmed_ids, len(pubmed_ids))

        if (
            len(article_count["pmids_in_litmapper"]) > 0
            and article_count["pmids_in_litmapper"][0] == "More than 2,000 results"
        ) or (
            len(article_count["pmids_not_in_litmapper"]) > 0
            and article_count["pmids_not_in_litmapper"][0] == "More than 2,000 results"
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Too many articles requested. Please do not attempt to add more than 2,000 articles.",
            )

        LOGGER.debug("Fuzzy matching titles...")
        fuzzy_match_titles(titles, pubmed_ids)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only CSV and RIS files are supported.",
        )

    LOGGER.debug(
        f"Loading {len(article_count['pmids_not_in_litmapper'])} articles from file..."
    )

    load_pmids_from_file.run(article_count["pmids_not_in_litmapper"], articles_to_create)  # type: ignore

    articles_add_payload = schemas.ArticlesAddPubmedPayload(
        date=datetime.now(),
        username=username,
        password=password,
        search_query=search_query,
        litmapper_pmids=article_count["pmids_in_litmapper"],
        temp_pmids=article_count["pmids_not_in_litmapper"],
    )
    LOGGER.debug("Adding articles to db...")
    add_temp_articles_pubmed(db, articles_add_payload, True)

    return {"message": "Articles uploaded successfully."}


@router.get("/articles/pmids")
def get_article_pmid_map(db: Session = Depends(get_db_dep)):
    """Returns a dictionary of {article_id : pmid} for all articles."""
    result = (
        db.query(models.Article)
        .with_entities(models.Article.article_id, models.Article.pmid)
        .all()
    )
    return dict(result)


@router.get("/pubmed_temp_requests", response_model=List[schemas.TemporaryRequest])
def get_temp_requests(db: Session = Depends(get_db_dep)):
    return db.query(models.TemporaryRequest).all()


@router.get("/pubmed_temp_request_articles", response_model=List)
def get_temp_request_articles(temp_request_id: int, db: Session = Depends(get_db_dep)):
    temp_request_articles = (
        db.query(models.ArticleTempRequest)
        .filter(models.ArticleTempRequest.temp_request_id == temp_request_id)
        .all()
    )
    return [article.article_id for article in temp_request_articles]


@router.post("/pubmed_temp_requests/remove")
def remove_temp_request(
    temp_request_payload: schemas.TempRequestPayload, db: Session = Depends(get_db_dep)
):
    remove_temp_article_batch(db, temp_request_payload.article_batch_id)


@router.get("/mesh_terms", response_model=List[schemas.MeSHTerm])
def get_mesh_terms(db: Session = Depends(get_db_dep)):
    return db.query(models.MeSHTerm).order_by(models.MeSHTerm.mesh_id).all()


@router.put("/mesh_terms")
def upsert_mesh_terms(
    mesh_terms: List[schemas.MeSHTerm], db: Session = Depends(get_db_dep)
):
    do_bulk_upsert(db, models.MeSHTerm, mesh_terms, {"mesh_id"})


@router.get("/article_sets", response_model=List[schemas.ArticleSet])
def get_article_sets(db: Session = Depends(get_db_dep)):
    return db.query(models.ArticleSet).order_by(models.ArticleSet.article_set_id).all()


@router.get("/article_set/{article_set_id}", response_model=schemas.ArticleSetDetail)
def get_article_set(article_set_id: int, db: Session = Depends(get_db_dep)):
    return raise_404_if_none(find_article_set(db, article_set_id))


@router.get(
    "/article_set/{article_set_id}/csv",
    response_class=StreamingResponse,
    responses={
        status.HTTP_200_OK: {
            "content": {"text/csv": {}},
            "description": "Returns all articles in the article set in CSV format.",
        }
    },
)
def get_article_set_csv(article_set_id: int, db: Session = Depends(get_db_dep)):
    article_set = raise_404_if_none(find_article_set(db, article_set_id))
    df_data = [
        {
            "article_id": article.article_id,
            "pmid": article.pmid,
            "title": article.title,
            "publication_date": article.publication_date,
            "abstract": article.abstract,
        }
        for article in article_set.articles
    ]
    article_df = pd.DataFrame(
        df_data, columns=["article_id", "pmid", "title", "publication_date", "abstract"]
    ).set_index("article_id")
    buf = io.StringIO()
    article_df.to_csv(buf)
    res = StreamingResponse(iter([buf.getvalue()]), media_type="text/csv")
    res.headers["Content-Disposition"] = (
        f'attachment; filename="{article_set.name}.csv"'
    )
    return res


@router.get(
    "/article_set/{article_set_id}/ris",
    response_class=StreamingResponse,
    responses={
        status.HTTP_200_OK: {
            "content": {"application/x-research-info-systems": {}},
            "description": "Returns all articles in the article set in RIS format.",
        }
    },
)
def get_article_set_ris(article_set_id: int, db: Session = Depends(get_db_dep)):
    article_set = raise_404_if_none(find_article_set(db, article_set_id))
    ris_data = [
        {
            "id": article.pmid,
            "primary_title": article.title,
            "year": article.publication_date,
            "abstract": article.abstract,
        }
        for article in article_set.articles
    ]
    buf = io.StringIO()
    rispy.dump(ris_data, buf)
    res = StreamingResponse(
        iter([buf.getvalue()]), media_type="application/x-research-info-systems"
    )
    res.headers["Content-Disposition"] = (
        f'attachment; filename="{article_set.name}.ris"'
    )
    return res


@router.post(
    "/article_sets",
    responses={
        status.HTTP_409_CONFLICT: {
            "model": None,
            "description": "Article set with the same name already exists.",
        }
    },
    response_model=schemas.ArticleSet,
)
def create_article_set(
    article_set_payload: schemas.ArticleSetCreatePayload,
    db: Session = Depends(get_db_dep),
):
    try:
        db_article_set = insert_article_set(db, article_set_payload.article_set)
    except IntegrityError:
        raise HTTPException(
            status_code=409, detail="An article set with this name already exists."
        )
    do_bulk_upsert(
        db,
        models.article_article_set,
        [
            schemas.ArticleArticleSet(
                article_set_id=db_article_set.article_set_id, article_id=article_id
            )
            for article_id in article_set_payload.article_ids
        ],
        {"article_set_id", "article_id"},
    )

    return db_article_set


@router.post(
    "/article_sets/remove",
)
def remove_article_set(
    article_set_payload: schemas.ArticleSetRemovePayload,
    db: Session = Depends(get_db_dep),
):
    delete_article_set(db, article_set_payload.article_set_id)


@router.get("/articles/tags/count", response_model=schemas.ArticleTagCount)
def get_article_tags_count(
    full_text_search_query: Optional[str] = None,
    db: Session = Depends(get_db_dep),
):
    articles = filter_articles(
        db, db.query(models.Article), full_text_search_query
    )
    count = articles.count()

    if full_text_search_query:
        return {
            "count": count,
            "full_text_search_pmids": [article.pmid for article in articles],
        }
    else:
        return {"count": count}


@router.get("/articles/tags/pubmed/count", response_model=schemas.ArticleTagPubmedCount)
def get_article_tags_pubmed_count(
    full_text_search_query: str,
    db: Session = Depends(get_db_dep),
):
    pubmed = search_articles_count.run(full_text_search_query)  # type: ignore

    return get_article_count(db, pubmed["pmids"], pubmed["count"])


@router.put("/articles/mesh_terms")
def upsert_article_mesh_terms(
    mesh_terms: List[schemas.ArticleMeSHTerm], db: Session = Depends(get_db_dep)
):
    do_bulk_upsert(db, models.article_mesh_term, mesh_terms, {"article_id", "mesh_id"})


@router.put("/articles/embeddings")
def upsert_article_embeddings(
    embeddings: List[dict], new_articles: bool, db: Session = Depends(get_db_dep)
):
    if new_articles:
        # Use article embedding schema to upload new article embedding pair
        formatted_embeddings = [
            schemas.ArticleEmbedding(**embed_obj) for embed_obj in embeddings
        ]
        do_bulk_upsert(
            db, models.ArticleEmbedding, formatted_embeddings, {"article_id"}
        )
    else:
        # If updating existing article, embedding set, update
        # only specific embedding type
        update_embeddings(db, embeddings)


@router.put("/articles/requesters")
def upsert_requesters(
    requesterInfo: List[schemas.ArticleRequester], db: Session = Depends(get_db_dep)
):
    do_bulk_upsert(db, models.ArticleRequester, requesterInfo, {"article_id"})


def _get_filter_set(params_hash: str, kv: Redis) -> schemas.FilterSetResult:
    try:
        return cast(
            schemas.FilterSetResult,
            find_resource_hash(kv, schemas.FilterSetParams, params_hash),
        )
    except errors.ResourceDoesNotExist:
        raise HTTPException(
            status_code=404, detail=f"Filter set does not exist with hash {params_hash}"
        )
    except errors.ResourceCreationInProgress:
        raise HTTPException(
            status_code=409, detail="Filter set creation is in progress"
        )


@router.get(
    "/filter_set/{params_hash}",
    response_model=schemas.FilterSetResult,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": None,
            "description": "Resource doesn't exist, although its creation may "
            "be in progress",
        },
        status.HTTP_409_CONFLICT: {
            "model": None,
            "description": "Resource currently being created",
        },
    },
)
def get_filter_set(
    params_hash: str,
    kv: Redis = Depends(get_kv_dep),
):
    return _get_filter_set(params_hash, kv)


@router.get(
    "/filter_set/{params_hash}/articles",
    response_model=List[schemas.Article],
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": None,
            "description": "Resource doesn't exist, although its creation may "
            "be in progress",
        },
        status.HTTP_409_CONFLICT: {
            "model": None,
            "description": "Resource currently being created",
        },
    },
)
def get_filter_set_articles(
    params_hash: str, kv: Redis = Depends(get_kv_dep), db: Session = Depends(get_db_dep)
):
    # TODO this isn't currently being used in the frontend, but it's prohibitively slow
    # as-is -- if any code needs to actually use it, we should add pagination and
    # potentially rework the query
    filter_set_result = _get_filter_set(params_hash, kv)
    return (
        db.query(models.Article)
        .filter(models.Article.article_id.in_(filter_set_result.article_ids))
        .order_by(models.Article.article_id)
        .all()
    )


@router.post(
    "/filter_sets",
    status_code=status.HTTP_202_ACCEPTED,
    response_class=Response,
    responses={
        status.HTTP_202_ACCEPTED: {
            "model": None,
            "description": "Triggered resource creation",
            "headers": {
                "Location": {
                    "description": "Path to the job status to query for resource "
                    "creation status"
                },
            },
        }
    },
)
def create_filter_set(
    params: schemas.FilterSetParams,
    response: Response,
    kv: Redis = Depends(get_kv_dep),
    force: bool = False,
):
    job = tasks.start_task(tasks.make_filter_set, params, force=force)
    response.headers["Location"] = f"/info/job/{job.job_id}"


@router.get(
    "/clustering/{params_hash}",
    response_model=schemas.ClusteringResult,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": None,
            "description": "Resource doesn't exist, although its creation may "
            "be in progress",
        },
        status.HTTP_409_CONFLICT: {
            "model": None,
            "description": "Resource currently being created",
        },
    },
)
def get_clustering(
    params_hash: str,
    kv: Redis = Depends(get_kv_dep),
):
    try:
        return find_resource_hash(kv, schemas.ClusteringParams, params_hash)
    except errors.ResourceDoesNotExist:
        raise HTTPException(
            status_code=404, detail=f"Clustering does not exist with hash {params_hash}"
        )
    except errors.ResourceCreationInProgress:
        raise HTTPException(
            status_code=409, detail="Clustering creation is in progress"
        )


@router.post(
    "/clustering",
    status_code=status.HTTP_202_ACCEPTED,
    response_class=Response,
    responses={
        status.HTTP_202_ACCEPTED: {
            "model": None,
            "description": "Triggered resource creation",
            "headers": {
                "Location": {
                    "description": "Path to the job status to query for resource "
                    "creation status"
                },
            },
        }
    },
)
def create_clustering(
    params: schemas.ClusteringParams,
    response: Response,
    kv: Redis = Depends(get_kv_dep),
):
    job = tasks.start_task(tasks.make_clustering, params)
    response.headers["Location"] = f"/info/job/{job.job_id}"


@router.get(
    "/article_group/{params_hash}",
    response_model=schemas.ArticleGroupResult,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": None,
            "description": "Resource doesn't exist, although its creation may "
            "be in progress",
        },
        status.HTTP_409_CONFLICT: {
            "model": None,
            "description": "Resource currently being created",
        },
    },
)
def get_article_group(
    params_hash: str,
    kv: Redis = Depends(get_kv_dep),
):
    try:
        return find_resource_hash(kv, schemas.ArticleGroupParams, params_hash)
    except errors.ResourceDoesNotExist:
        raise HTTPException(
            status_code=404,
            detail=f"Article group does not exist with hash {params_hash}",
        )
    except errors.ResourceCreationInProgress:
        raise HTTPException(
            status_code=409, detail="Article group creation is in progress"
        )


@router.post(
    "/article_groups",
    status_code=status.HTTP_202_ACCEPTED,
    response_class=Response,
    responses={
        status.HTTP_202_ACCEPTED: {
            "model": None,
            "description": "Triggered resource creation",
            "headers": {
                "Location": {
                    "description": "Path to the job status to query for resource "
                    "creation status"
                },
            },
        }
    },
)
def create_article_group(
    params: schemas.ArticleGroupParams,
    response: Response,
    kv: Redis = Depends(get_kv_dep),
):
    job = tasks.start_task(tasks.make_article_group, params)
    response.headers["Location"] = f"/info/job/{job.job_id}"
