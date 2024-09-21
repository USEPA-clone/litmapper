import logging

from fastapi import FastAPI

from litmapper.routers import admin, concept_graph, info, literature

# Avoid a bunch of unneeded info logs every time we start a dramatiq actor
logging.getLogger("pika").setLevel(logging.WARNING)

tags_metadata = [
    {
        "name": "literature",
        "description": "Operations related to importing and searching/filtering literature.",
    },
    {
        "name": "concept_graph",
        "description": "Operations related to importing and searching/filtering a concept graph based on a controlled vocabulary (e.g. UMLS).",
    },
    {
        "name": "info",
        "description": "Information about the application itself, including background job status.",
    },
]

app = FastAPI(
    title="LitMapper Systematic Review App API",
    description="Backend API driving all functionality in the LitMapper systematic review app.",
    openapi_tags=tags_metadata,
)

app.include_router(literature.router, prefix="/literature", tags=["literature"])
app.include_router(
    concept_graph.router, prefix="/concept_graph", tags=["concept_graph"]
)
app.include_router(info.router, prefix="/info", tags=["info"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
