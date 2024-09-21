from sqlalchemy import (
    DDL,
    Column,
    Date,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    UniqueConstraint,
    event,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Boolean
from sqlalchemy_searchable import make_searchable
from sqlalchemy_utils.types import TSVectorType

CONCEPT_GRAPH_SCHEMA = "concept_graph"

Base = declarative_base()
make_searchable(Base.metadata)

# This is unnecessary for alembic migrations but will be used in the tests,
# when we create all the tables directly through SQLAlchemy
event.listen(
    Base.metadata,
    "before_create",
    DDL(f"CREATE SCHEMA IF NOT EXISTS {CONCEPT_GRAPH_SCHEMA}"),
)

article_mesh_term = Table(
    "article_mesh_term",
    Base.metadata,
    Column("article_id", Integer, ForeignKey("article.article_id"), index=True),
    Column("mesh_id", String, ForeignKey("mesh_term.mesh_id")),
    UniqueConstraint("article_id", "mesh_id"),
)

article_article_set = Table(
    "article_article_set",
    Base.metadata,
    Column("article_id", Integer, ForeignKey("article.article_id"), index=True),
    Column("article_set_id", Integer, ForeignKey("article_set.article_set_id")),
    UniqueConstraint("article_id", "article_set_id"),
)
article_temp_request = Table(
    "article_temp_request",
    Base.metadata,
    Column("article_id", Integer, ForeignKey("article.article_id"), index=True),
    Column("temp_request_id", Integer, ForeignKey("temp_request.temp_request_id")),
    Column("is_article_temp", Boolean),
    UniqueConstraint("article_id", "temp_request_id"),
)


class Article(Base):
    __tablename__ = "article"

    article_id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    pmid = Column(Integer, unique=True, nullable=True)
    title = Column(String, nullable=False)
    abstract = Column(String, nullable=False)
    publication_date = Column(Date, nullable=True)
    mesh_terms = relationship(
        "MeSHTerm", secondary=article_mesh_term, back_populates="articles"
    )
    embeddings = relationship(
        "ArticleEmbedding", uselist=False, back_populates="article"
    )
    article_sets = relationship(
        "ArticleSet", secondary=article_article_set, back_populates="articles"
    )
    temp_requests = relationship(
        "TemporaryRequest", secondary=article_temp_request, back_populates="articles"
    )
    search_vector = Column(TSVectorType("title", "abstract"))

    @hybrid_property
    def all_text(self) -> str:
        return self.title + " " + self.abstract


class MeSHTerm(Base):
    __tablename__ = "mesh_term"

    mesh_id = Column(String, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    articles = relationship(
        "Article", secondary=article_mesh_term, back_populates="mesh_terms"
    )


class ArticleMeshTerm(Base):
    __tablename__ = "article_mesh_term"

    article_id = Column(
        Integer,
        ForeignKey("article.article_id"),
        primary_key=True,
        autoincrement=False,
        index=True,
    )
    mesh_id = Column(String, ForeignKey("mesh_term.mesh_id"))

    __table_args__ = (
        UniqueConstraint("article_id", "mesh_id"),
        {"extend_existing": True},
    )


class ArticleEmbedding(Base):
    __tablename__ = "article_embedding"

    article_id = Column(
        Integer,
        ForeignKey("article.article_id"),
        primary_key=True,
        autoincrement=False,
        index=True,
    )
    use_embedding = Column(postgresql.ARRAY(Float, dimensions=1), nullable=False)
    specter_embedding = Column(postgresql.ARRAY(Float, dimensions=1), nullable=True)

    article = relationship("Article", uselist=False, back_populates="embeddings")

    __table_args__ = (UniqueConstraint("article_id", name="ucon_ae"),)


class ArticleRequester(Base):
    __tablename__ = "article_requester"

    article_id = Column(Integer, primary_key=True, autoincrement=False, index=True)
    requester = Column(String)
    upload_date = Column(Date)

    __table_args__ = (UniqueConstraint("article_id", name="ucon_ar"),)


class TemporaryRequest(Base):
    __tablename__ = "temp_request"

    temp_request_id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    requester = Column(String)
    date = Column(Date)
    search_query = Column(String)
    articles = relationship(
        "Article", secondary=article_temp_request, back_populates="temp_requests"
    )
    __table_args__ = (UniqueConstraint("temp_request_id", name="ucon_tr"),)


class ArticleTempRequest(Base):
    __tablename__ = "article_temp_request"

    article_id = Column(
        Integer, ForeignKey("article.article_id"), primary_key=True, index=True
    )
    temp_request_id = Column(
        Integer, ForeignKey("temp_request.temp_request_id"), primary_key=True
    )
    is_article_temp = Column(Boolean)
    __table_args__ = (
        UniqueConstraint("article_id", "temp_request_id"),
        {"extend_existing": True},
    )


class ArticleSet(Base):
    __tablename__ = "article_set"

    article_set_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    meta_json = Column(postgresql.JSONB, nullable=False)
    articles = relationship(
        "Article",
        # This shouldn't be necessary, but the mypy types aren't being inferred
        # correctly without it
        uselist=True,
        secondary=article_article_set,
        back_populates="article_sets",
    )


class ArticleArticleSet(Base):
    __tablename__ = "article_article_set"

    article_id = Column(
        Integer, ForeignKey("article.article_id"), primary_key=True, index=True
    )
    article_set_id = Column(
        Integer, ForeignKey("article_set.article_set_id"), primary_key=True
    )
    __table_args__ = (
        UniqueConstraint("article_id", "article_set_id"),
        {"extend_existing": True},
    )


#
# Concept Graph
#

concept_semantic_type = Table(
    "concept_semantic_type",
    Base.metadata,
    Column(
        "concept_id", String, ForeignKey(f"{CONCEPT_GRAPH_SCHEMA}.concept.concept_id")
    ),
    Column(
        "semantic_type_id",
        String,
        ForeignKey(f"{CONCEPT_GRAPH_SCHEMA}.semantic_type.semantic_type_id"),
    ),
    UniqueConstraint("concept_id", "semantic_type_id"),
    schema=CONCEPT_GRAPH_SCHEMA,
)


class ConceptAlias(Base):
    __tablename__ = "concept_alias"
    concept_alias_id = Column(
        String,
        primary_key=True,
        comment="Unique key for the alias in the graph.",
    )
    concept_id = Column(
        String, ForeignKey(f"{CONCEPT_GRAPH_SCHEMA}.concept.concept_id")
    )
    concept = relationship("Concept", back_populates="aliases")

    source_id = Column(String, ForeignKey(f"{CONCEPT_GRAPH_SCHEMA}.source.source_id"))
    source = relationship("Source", back_populates="aliases")
    alias_name = Column(
        String,
        nullable=False,
        comment="Name of the alias from the source vocabulary.",
    )
    source_concept_id = Column(
        String,
        nullable=False,
        comment="The source's ID for this concept alias (ex MeSH ID for MeSH).",
    )
    __table_args__ = {"schema": CONCEPT_GRAPH_SCHEMA}


class Concept(Base):
    __tablename__ = "concept"

    concept_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    semantic_types = relationship(
        "SemanticType", secondary=concept_semantic_type, back_populates="concepts"
    )
    sources = relationship(
        "Source", secondary=ConceptAlias.__table__, back_populates="concepts"
    )
    aliases = relationship("ConceptAlias", back_populates="concept")

    __table_args__ = {"schema": CONCEPT_GRAPH_SCHEMA}


class SemanticType(Base):
    __tablename__ = "semantic_type"

    semantic_type_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    concepts = relationship(
        "Concept", secondary=concept_semantic_type, back_populates="semantic_types"
    )

    __table_args__ = {"schema": CONCEPT_GRAPH_SCHEMA}


class Source(Base):
    __tablename__ = "source"

    source_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    concepts = relationship(
        "Concept", secondary=ConceptAlias.__table__, back_populates="sources"
    )
    aliases = relationship("ConceptAlias", back_populates="source")

    __table_args__ = {"schema": CONCEPT_GRAPH_SCHEMA}
