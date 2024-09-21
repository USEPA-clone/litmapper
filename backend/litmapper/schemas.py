import datetime as dt
from enum import Enum, unique
from typing import Any, Dict, List, Optional, Tuple

import colorcet as cc
from pydantic import BaseModel, Field, validator

JsonObj = Dict[str, Any]


class HashableBaseModel(BaseModel):
    def __hash__(self) -> int:
        # NOTE: PYTHONHASHSEED environment variable MUST be set to the same value
        # between API and all worker processes for this hash to match up and
        # function correctly
        # Use the name of the type object instead of the object itself to ensure
        # hashes are consistent across interpreter sessions (which isn't the case
        # with the type object even if the seeds are set appropriately)
        return hash((type(self).__name__,) + tuple(self.__dict__.values()))


# Inherit enum classes from str for full compatibility with FastAPI
@unique
class JobStatus(str, Enum):
    FAILED = "failed"
    IN_PROGRESS = "in progress"
    SUCCESS = "success"


class JobBase(BaseModel):
    status: JobStatus
    status_detail: Optional[str]
    result_url: Optional[str]

    @validator("result_url")
    @classmethod
    def successful_job_has_url(cls, v, values):
        if values.get("status", JobStatus.IN_PROGRESS) == JobStatus.SUCCESS:
            if v is None:
                raise ValueError("successful jobs must have a result_url")
        return v


class JobCreate(JobBase):
    pass


class Job(JobBase):
    job_id: str


class MeSHTerm(BaseModel):
    mesh_id: str
    name: str

    class Config:
        orm_mode = True


class ArticleEmbedding(BaseModel):
    article_id: int
    use_embedding: Optional[List[float]]
    specter_embedding: Optional[List[float]]

    class Config:
        orm_mode = True\


class ArticleBase(BaseModel):
    pmid: int
    title: str
    abstract: str
    publication_date: Optional[dt.date] = None
    mesh_terms: List[MeSHTerm] = []
    embeddings: Optional[ArticleEmbedding] = None


class ArticleCreate(ArticleBase):
    pass


class Article(ArticleBase):
    article_id: int

    class Config:
        orm_mode = True


class ArticleMeSHTerm(BaseModel):
    article_id: int
    mesh_id: str

    class Config:
        orm_mode = True


class ArticleRequester(BaseModel):
    article_id: int
    requester: str
    upload_date: dt.date

    class Config:
        orm_mode = True


class ArticlesAddPubmedPayload(BaseModel):
    date: Any
    password: str
    litmapper_pmids: List[int]
    temp_pmids: List[int]
    username: str
    search_query: str


class ArticleTempRequest(BaseModel):
    article_id: int
    temp_request_id: int
    is_article_temp: bool

    class Config:
        orm_mode = True


class TemporaryRequest(BaseModel):
    search_query: str
    requester: str
    temp_request_id: int
    date: Any

    class Config:
        orm_mode = True


class TempRequestPayload(BaseModel):
    article_batch_id: int


class ArticleSetBase(BaseModel):
    name: str
    meta_json: JsonObj


class ArticleSetCreate(ArticleSetBase):
    pass


class ArticleSetCreatePayload(BaseModel):
    article_set: ArticleSetCreate
    article_ids: List[int]


class ArticleSetRemovePayload(BaseModel):
    article_set_id: int


class ArticleSet(ArticleSetBase):
    article_set_id: int

    class Config:
        orm_mode = True


class ArticleSetDetail(ArticleSet):
    articles: List[Article]

    class Config:
        orm_mode = True


class ArticleArticleSet(BaseModel):
    article_id: int
    article_set_id: int

    class Config:
        orm_mode = True


class FilterSetParams(HashableBaseModel):
    full_text_search_query: Optional[str]
    temp_article_ids: Optional[Tuple[int, ...]]
    limit: Optional[int] = None


class FilterSetResult(BaseModel):
    article_ids: List[int]


class PlotlyScatter(BaseModel):
    """
    docs:
      https://plotly.com/javascript/bubble-charts/
      https://plotly.com/javascript/line-and-scatter/
    """

    x: List[float]
    y: List[float]
    mode: str = "markers"
    extra: Dict[Any, Any] = {}
    marker: Dict[Any, Any] = {}


class PlotlyHeatmap(BaseModel):
    """docs: https://plotly.com/javascript/heatmaps/"""

    type: str = "heatmap"
    x: List[str]
    y: List[str]
    z: List[List[Optional[float]]]
    labels: Optional[Dict[str, str]]  # {"x" : "x label", ...}
    hoverongaps: bool = False
    extra: Dict[Any, Any] = {}


class ArticleTagCrosstabCell(BaseModel):
    row_tag_name: str
    row_tag_value: str
    column_tag_name: str
    column_tag_value: str
    count: int


class ArticleTagCount(BaseModel):
    count: int
    full_text_search_pmids: Optional[list]


class ArticleTagPubmedCount(BaseModel):
    count: int
    litmapper_count: int
    pmids_in_litmapper: List
    pmids_not_in_litmapper: List


class ClusteringParams(HashableBaseModel):
    filter_set: FilterSetParams
    umap_seed: int = 1
    umap_n_neighbors: int = 30
    umap_metric: str = "cosine"
    umap_min_dist: float = 0.00
    hdbscan_min_cluster_size: int = 3
    hdbscan_min_samples: int = 3
    hdbscan_cluster_selection_epsilon: float = 0.0
    hdbscan_do_flat_clustering: bool = False
    hdbscan_cluster_flattening_epsilon: float = 0.05

    class Config:
        schema_extra = {
            "example": {
                "filter_set": {"full_text_search_query": "example search query"},
                "umap_seed": 1,
                "umap_n_neighbors": 5,
                "umap_metric": "cosine",
                "umap_min_dist": 0.1,
                "hdbscan_min_cluster_size": 3,
                "hdbscan_cluster_selection_epsilon": 0.0,
                "hdbscan_do_flat_clustering": False,
                "hdbscan_cluster_flattening_epsilon": 0.05,
            }
        }


class ClusteringOverallMetrics(BaseModel):
    dbcv: Optional[float]
    silhoutte_coefficient: Optional[float]
    davies_bouldin_index: Optional[float]
    dunn_index: Optional[float]


class ClusteringLabelInfo(BaseModel):
    n_per_cluster: List[int]
    cluster_validity_indices: List[float]
    cluster_center_coords: List[Tuple[float, float]]
    plotly_data: Optional[PlotlyScatter]

    @validator("cluster_center_coords")
    @classmethod
    def list_lengths_match(cls, v, values):
        num_clusters = len(values.get("n_per_cluster", []))
        num_indices = len(values.get("cluster_validity_indices", []))
        num_coords = len(v)

        if not (num_clusters == num_indices == num_coords):
            raise ValueError(
                f"must have same number of clusters ({num_clusters}), "
                f"index values ({num_indices}), and coords ({num_coords})"
            )

        return v

    @validator("plotly_data", pre=True, always=True)
    def to_plotly(cls, v, values):
        if len(values.get("cluster_center_coords")) == 0:
            return PlotlyScatter(x=[], y=[])
        extra = {
            "n_per_cluster": values.get("n_per_cluster"),
            "cluster_validity_indices": values.get("cluster_validity_indices"),
        }
        x, y = zip(*values.get("cluster_center_coords"))
        return PlotlyScatter(x=x, y=y, extra=extra)


class ClusteringResult(BaseModel):
    article_ids: List[int]
    labels: List[Optional[int]]
    coords: List[Tuple[float, float]]
    num_clusters: int
    metrics: ClusteringOverallMetrics
    label_info: ClusteringLabelInfo
    plotly_data: Optional[PlotlyScatter]

    @validator("coords")
    @classmethod
    def list_lengths_match(cls, v, values):
        num_article_ids = len(values.get("article_ids", []))
        num_labels = len(values.get("labels", []))
        num_coords = len(v)

        if not (num_article_ids == num_labels == num_coords):
            raise ValueError(
                f"must have same number of article IDs ({num_article_ids}), "
                f"labels ({num_labels}), and coords ({num_coords})"
            )

        return v

    @validator("plotly_data", pre=True, always=True)
    def to_plotly(cls, v, values):
        if len(values.get("coords")) == 0:
            return PlotlyScatter(x=[], y=[])
        # Remove articles not assigned to a cluster before
        # generating plotly chart.
        points_with_cluster = []
        point_properties = zip(
            values.get("labels"), values.get("coords"), values.get("article_ids")
        )
        for cluster_id, coords, article_id in point_properties:
            if cluster_id is not None:
                points_with_cluster.append((cluster_id, coords, article_id))
        labels, coords, article_ids = zip(*points_with_cluster)

        x, y = zip(*coords)
        marker = {
            "size": [10 for i in range(len(article_ids))],
            "opacity": [0.8 for i in range(len(article_ids))],
            "color": [
                cc.glasbey_dark[cluster % len(cc.glasbey_dark)] for cluster in labels
            ],
        }
        extra = {
            "article_ids": article_ids,
            "labels": labels,
        }

        return PlotlyScatter(x=x, y=y, extra=extra, marker=marker)


@unique
class ArticleGroupSummaryTerms(str, Enum):
    NAMED_ENTITIES = "named entities"
    MESH_TERMS = "mesh terms"


class ArticleGroupParams(HashableBaseModel):
    clustering: ClusteringParams
    num_terms: int = 10
    summary_terms: ArticleGroupSummaryTerms = ArticleGroupSummaryTerms.MESH_TERMS


class ArticleGroup(BaseModel):
    id: int
    num_articles: int
    article_ids: List[int]
    top_terms: List[str]


class ArticleGroupResult(BaseModel):
    result: List[ArticleGroup]
    plotly_data: Optional[PlotlyHeatmap]

    @validator("plotly_data", pre=True, always=True)
    def to_plotly(cls, v, values):
        cluster_ids = list(sorted(group.id for group in values.get("result")))
        terms = []
        for r in values.get("result"):
            terms.extend(r.top_terms)
        terms = list(sorted(list(set(terms))))
        x = cluster_ids
        y = terms
        z = []
        for cluster in cluster_ids:
            article_group = next(c for c in values.get("result") if c.id == cluster)
            terms_in_cluster = []
            for term in terms:
                present = 1.0 if term in article_group.top_terms else None
                terms_in_cluster.append(present)
            z.append(terms_in_cluster)
        return PlotlyHeatmap(
            x=x, y=y, z=z, labels={"x": "Cluster", "y": "Term", "z": "Present"}
        )


class SemanticType(BaseModel):
    semantic_type_id: str = Field(
        ..., description="UMLS equivalent: type unique ID (TUI)"
    )
    name: str

    class Config:
        orm_mode = True


class Source(BaseModel):
    source_id: str = Field(
        ..., description="UMLS equivalent: root source abbreviation (RSAB)"
    )
    name: str

    class Config:
        orm_mode = True


class ConceptAlias(BaseModel):
    concept_alias_id: str = Field(
        ..., description="UMLS equivalent: atom unique ID (AUI)"
    )
    alias_name: str
    source_concept_id: str = Field(
        ..., description="ID for the atom in the source vocabulary"
    )
    concept_id: str
    source_id: str

    class Config:
        orm_mode = True


class Concept(BaseModel):
    concept_id: str = Field(..., description="UMLS equivalent: concept unique ID (CUI)")
    name: str
    aliases: List["ConceptAlias"] = []
    semantic_types: List[SemanticType] = []

    class Config:
        orm_mode = True


class ConceptSemanticType(BaseModel):
    concept_id: str
    semantic_type_id: str

    class Config:
        orm_mode = True
