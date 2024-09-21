import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import and_, case
from sqlalchemy.orm import Query, Session, aliased
from sqlalchemy.sql import exists
from sqlalchemy.sql.functions import count
from sqlalchemy_searchable import search

from litmapper import models, schemas
from litmapper.db.load_pubmed import download_pubmed, generate_embeddings
from litmapper.db.util import do_bulk_upsert


def find_article_litmapper_id(db: Session, article_id: int) -> Optional[models.Article]:
    return (
        db.query(models.Article).filter(models.Article.article_id == article_id).first()
    )


def find_article_pmid(db: Session, pmid: int) -> Optional[models.Article]:
    return db.query(models.Article).filter(models.Article.pmid == pmid).first()


def find_articles_litmapper_ids(db: Session, article_ids: Sequence[int]) -> Query:
    return (
        db.query(models.Article)
        .order_by(models.Article.article_id)
        .filter(models.Article.article_id.in_(article_ids))
    )


def find_articles_pmids(db: Session, pmids: Sequence[int]) -> Query:
    return (
        db.query(models.Article)
        .order_by(models.Article.pmid)
        .filter(models.Article.pmid.in_(pmids))
    )


def add_temp_articles_pubmed(
    db: Session, temp_request: schemas.ArticlesAddPubmedPayload, from_file: bool = False
) -> models.TemporaryRequest:
    if not from_file:
        download_pubmed(temp_request.temp_pmids)
    generate_embeddings(temp_request.temp_pmids)

    temp_articles = find_articles_pmids(db, temp_request.temp_pmids).all()
    temp_article_ids = [article.article_id for article in temp_articles]
    litmapper_articles = find_articles_pmids(db, temp_request.litmapper_pmids).all()
    litmapper_article_ids = [article.article_id for article in litmapper_articles]

    db_temp_request = add_temp_article_batch_entry(db, temp_request)

    do_bulk_upsert(
        db,
        models.article_temp_request,
        [
            schemas.ArticleTempRequest(
                temp_request_id=db_temp_request.temp_request_id,
                article_id=article_id,
                is_article_temp=True,
            )
            for article_id in temp_article_ids
        ],
        {"temp_request_id", "article_id"},
    )
    do_bulk_upsert(
        db,
        models.article_temp_request,
        [
            schemas.ArticleTempRequest(
                temp_request_id=db_temp_request.temp_request_id,
                article_id=article_id,
                is_article_temp=False,
            )
            for article_id in litmapper_article_ids
        ],
        {"temp_request_id", "article_id"},
    )

    return db_temp_request


def filter_articles(
    db: Session,
    articles: Query,
    full_text_search_query: Optional[str],
) -> Query:

    articles = articles.filter(
        # Ensures only articles formally included in corpus are being queried
        ~exists().where(
            and_(
                models.Article.article_id == models.ArticleTempRequest.article_id,
                models.ArticleTempRequest.is_article_temp == True,  # noqa
            )
        )
    )

    print(f"pre-filter total articles: {articles.count()}")

    if full_text_search_query:
        # Use boolean operators properly regardless of case
        full_text_search_query = re.sub(
            r"\band\b", "and", full_text_search_query, flags=re.IGNORECASE
        )
        full_text_search_query = re.sub(
            r"\bor\b", "or", full_text_search_query, flags=re.IGNORECASE
        )
        full_text_search_query = re.sub(
            r"\bnot \b", "-", full_text_search_query, flags=re.IGNORECASE
        )

        articles = search(articles, full_text_search_query)

    print(f"post-filter total articles: {articles.count()}")

    return articles


def update_embeddings(db: Session, embeddings: List[dict]):
    # Update one embedding type, leave others untouched
    db.bulk_update_mappings(models.ArticleEmbedding, embeddings)
    db.commit()


def find_mesh_term(db: Session, mesh_id: str) -> Optional[models.MeSHTerm]:
    return db.query(models.MeSHTerm).filter(models.MeSHTerm.mesh_id == mesh_id).first()


def find_embedding(db: Session, article_id: int) -> Optional[models.ArticleEmbedding]:
    return (
        db.query(models.ArticleEmbedding)
        .filter(models.ArticleEmbedding.article_id == article_id)
        .first()
    )


def insert_article_set(
    db: Session, article_set: schemas.ArticleSetCreate
) -> models.ArticleSet:
    db_article_set = models.ArticleSet(
        name=article_set.name, meta_json=article_set.meta_json
    )
    db.add(db_article_set)
    db.commit()
    return db_article_set


def add_temp_article_batch_entry(
    db: Session, pubmed_request: schemas.ArticlesAddPubmedPayload
):

    db_temp_request = models.TemporaryRequest(
        requester=pubmed_request.username,
        date=pubmed_request.date,
        search_query=pubmed_request.search_query,
    )
    db.add(db_temp_request)
    db.commit()
    return db_temp_request


def remove_temp_article_batch(db: Session, article_batch_id: int):
    # Go ahead and delete references to articles that exist in the main litmapper database
    temp_article_batch_litmapper_articles = db.query(models.ArticleTempRequest).filter(
        models.ArticleTempRequest.temp_request_id == article_batch_id,
        models.ArticleTempRequest.is_article_temp == False,  # noqa
    )
    temp_article_batch_litmapper_articles.delete(synchronize_session="fetch")
    db.commit()

    # Get all remaining temp_request_articles in the article batch
    temp_article_batch_articles = db.query(models.ArticleTempRequest).filter(
        models.ArticleTempRequest.temp_request_id == article_batch_id
    )

    temp_article_batch_articles_ids = [
        article.article_id for article in temp_article_batch_articles
    ]
    # Find which articles are exclusive to the temp_request being deleted
    # These will be deleted from article, article embedding, etc
    exclusive_temp_article_batch_articles_ids = temp_article_batch_articles_ids.copy()
    for article in db.query(models.ArticleTempRequest):
        if (
            article.article_id in temp_article_batch_articles_ids
            and article.article_id in exclusive_temp_article_batch_articles_ids
            and article.temp_request_id != article_batch_id
        ):
            exclusive_temp_article_batch_articles_ids.remove(article.article_id)

    temp_article_batch_articles.delete()
    db.commit()

    for article_id in exclusive_temp_article_batch_articles_ids:
        db.query(models.ArticleArticleSet).filter(
            models.ArticleArticleSet.article_id == article_id
        ).delete()
        db.commit()

        db.query(models.ArticleEmbedding).filter(
            models.ArticleEmbedding.article_id == article_id
        ).delete(synchronize_session="fetch")
        db.commit()

        db.query(models.ArticleMeshTerm).filter(
            models.ArticleMeshTerm.article_id == article_id
        ).delete(synchronize_session="fetch")
        db.commit()

        db.query(models.ArticleRequester).filter(
            models.ArticleRequester.article_id == article_id
        ).delete()
        db.commit()

        db.query(models.Article).filter(
            models.Article.article_id == article_id
        ).delete()
        db.commit()

    db.query(models.TemporaryRequest).filter(
        models.TemporaryRequest.temp_request_id == article_batch_id
    ).delete()
    db.commit()


def find_article_set(db: Session, article_set_id: int) -> Optional[models.ArticleSet]:
    return (
        db.query(models.ArticleSet)
        .filter(models.ArticleSet.article_set_id == article_set_id)
        .first()
    )


def delete_article_set(db: Session, article_set_id: int):
    db.query(models.ArticleArticleSet).filter(
        models.ArticleArticleSet.article_set_id == article_set_id
    ).delete()
    db.commit()
    db.query(models.ArticleSet).filter(
        models.ArticleSet.article_set_id == article_set_id
    ).delete()
    db.commit()


def crosstab_article_tags(
    db: Session, articles: Query, row_tag_name: str, column_tag_name: str
) -> List[Tuple[str, str, str, str, int]]:
    articles_subquery = articles.subquery()

    row_tags = aliased(models.Tag)
    row_tag_name_col = models.Tag.name.label("row_tag_name")
    row_tag_value_col = models.Tag.value.label("row_tag_value")
    row_tag_query = (
        db.query(row_tags)
        .filter(row_tag_name_col == row_tag_name)
        .with_entities(models.Tag.tag_id, row_tag_name_col, row_tag_value_col)
        .subquery()
    )
    column_tags = aliased(models.Tag)
    column_tag_name_col = models.Tag.name.label("column_tag_name")
    column_tag_value_col = models.Tag.value.label("column_tag_value")
    column_tag_query = (
        db.query(column_tags)
        .filter(column_tag_name_col == column_tag_name)
        .with_entities(models.Tag.tag_id, column_tag_name_col, column_tag_value_col)
        .subquery()
    )

    # Cross join to get all combinations of row/column
    all_tags = db.query(row_tag_query, column_tag_query).subquery()

    # Calculate the counts for all combinations of our row/column tags
    row_article_tags = aliased(models.article_tag)
    column_article_tags = aliased(models.article_tag)

    # The nature of the join below means it won't return rows for any cells having
    # count = 0
    group_cols = (
        row_tag_query.c.row_tag_name,
        row_tag_query.c.row_tag_value,
        column_tag_query.c.column_tag_name,
        column_tag_query.c.column_tag_value,
    )
    cell_count_col = count().label("count")
    nonzero_counts = (
        db.query(row_tag_query)
        .join(row_article_tags, row_tag_query.c.tag_id == row_article_tags.c.tag_id)
        .join(
            articles_subquery,
            row_article_tags.c.article_id == articles_subquery.c.article_id,
            isouter=True,
        )
        .join(
            column_article_tags,
            articles_subquery.c.article_id == column_article_tags.c.article_id,
        )
        .join(
            column_tag_query, column_article_tags.c.tag_id == column_tag_query.c.tag_id
        )
        .with_entities(*group_cols, cell_count_col)
        .group_by(*group_cols)
    ).subquery()

    # Left join starting with the cross join generated first to return counts for all
    # cells (even if the value is 0)
    crosstab_query = (
        db.query(all_tags)
        .join(
            nonzero_counts,
            (all_tags.c.row_tag_name == nonzero_counts.c.row_tag_name)
            & (all_tags.c.row_tag_value == nonzero_counts.c.row_tag_value)
            & (all_tags.c.column_tag_name == nonzero_counts.c.column_tag_name)
            & (all_tags.c.column_tag_value == nonzero_counts.c.column_tag_value),
            isouter=True,
        )
        .with_entities(
            all_tags.c.row_tag_name,
            all_tags.c.row_tag_value,
            all_tags.c.column_tag_name,
            all_tags.c.column_tag_value,
            case([(nonzero_counts.c.count.is_(None), 0)], else_=nonzero_counts.c.count),
        )
    )

    return crosstab_query.all()


def get_article_count(
    db: Session, pubmed_ids: list[int], article_count: int
) -> Dict[str, Any]:
    litmapper_articles = find_articles_pmids(db, pubmed_ids).filter(
        # Ensures only articles formally included in corpus are queried
        ~exists().where(
            and_(
                models.Article.article_id == models.ArticleTempRequest.article_id,
                models.ArticleTempRequest.is_article_temp == True,  # noqa
            )
        )
    )
    count = litmapper_articles.count()

    # Only adding new articles if the request is less than 2,000 articles
    if article_count < 2000:
        pubmed_in_litmapper = []
        pubmed_not_in_litmapper = pubmed_ids
        for article in litmapper_articles:
            if article.pmid in pubmed_not_in_litmapper:
                pubmed_not_in_litmapper.remove(article.pmid)
                pubmed_in_litmapper.append(article.pmid)
    else:
        pubmed_not_in_litmapper = ["More than 2,000 results"]  # type: ignore
        pubmed_in_litmapper = ["More than 2,000 results"]  # type: ignore

    return {
        "count": article_count,
        "litmapper_count": count,
        "pmids_in_litmapper": pubmed_in_litmapper,
        "pmids_not_in_litmapper": pubmed_not_in_litmapper,
    }


def process_article(article: Dict[str, Any], file_type: str) -> Dict[str, Any]:
    mesh_term_field = "mesh_terms" if file_type == "csv" else "custom8"
    date_field = "publication_date" if file_type == "csv" else "date"
    full_mesh_terms = []
    if mesh_term_field in article:
        mesh_terms = article[mesh_term_field].split("|")
        mesh_terms = [
            mesh_term.lstrip("(").rstrip(")").split(",", maxsplit=1)
            for mesh_term in mesh_terms
        ]
        full_mesh_terms = [
            schemas.MeSHTerm(mesh_id=mesh_term[0], name=mesh_term[1]).dict()
            for mesh_term in mesh_terms
        ]

    return {
        "pmid": article["id"],
        "title": article["title"],
        "mesh_terms": full_mesh_terms,
        "abstract": article["abstract"],
        "publication_date": article[date_field],
    }
