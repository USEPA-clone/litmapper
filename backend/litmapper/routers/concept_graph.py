from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from litmapper import models, schemas
from litmapper.db.concept_graph import find_concept, find_concept_alias
from litmapper.db.util import do_bulk_upsert, get_db_dep
from litmapper.routers.util import raise_404_if_none

router = APIRouter()


@router.get("/concept/{concept_id}", response_model=schemas.Concept)
def get_concept(concept_id: str, db: Session = Depends(get_db_dep)):
    """
    Retrieve information on a concept.  Concepts in this system correspond
    directly to UMLS concepts, and the concept ID corresponds to a UMLS CUI.
    """
    return raise_404_if_none(find_concept(db, concept_id))


@router.put("/concepts")
def upsert_concepts(concepts: List[schemas.Concept], db: Session = Depends(get_db_dep)):
    do_bulk_upsert(db, models.Concept, concepts, {"concept_id"})


@router.get("/sources", response_model=List[schemas.Source])
def get_sources(db: Session = Depends(get_db_dep)):
    """
    Retrieve information on a source vocabulary.  Sources correspond to UMLS source
    vocabularies, and the source ID corresponds to the root source abbreviation in UMLS.
    """
    return db.query(models.Source).all()


@router.put("/sources")
def upsert_sources(sources: List[schemas.Source], db: Session = Depends(get_db_dep)):
    do_bulk_upsert(db, models.Source, sources, {"source_id"})


@router.get("/semantic_types", response_model=List[schemas.SemanticType])
def get_semantic_types(db: Session = Depends(get_db_dep)):
    """
    Retrieve information on a semantic type.  Semantic types directly correspond to UMLS
    semantic types, and the semantic type ID corresponds to a UMLS TUI.
    """
    return db.query(models.SemanticType).all()


@router.put("/semantic_types")
def upsert_semantic_types(
    semantic_types: List[schemas.SemanticType], db: Session = Depends(get_db_dep)
):
    do_bulk_upsert(db, models.SemanticType, semantic_types, {"semantic_type_id"})


@router.get("/alias/{concept_alias_id}", response_model=schemas.ConceptAlias)
def get_concept_alias(concept_alias_id: str, db: Session = Depends(get_db_dep)):
    """
    Retrieve information on a concept alias (atom in UMLS).  The concept alias ID corresponds
    to an AUI in UMLS.
    """
    return raise_404_if_none(find_concept_alias(db, concept_alias_id))


@router.put("/aliases")
def upsert_concept_aliases(
    concept_aliases: List[schemas.ConceptAlias], db: Session = Depends(get_db_dep)
):
    do_bulk_upsert(db, models.ConceptAlias, concept_aliases, {"concept_alias_id"})


@router.put("/concepts/semantic_types")
def upsert_concept_semantic_types(
    concept_semantic_types: List[schemas.ConceptSemanticType],
    db: Session = Depends(get_db_dep),
):
    do_bulk_upsert(
        db,
        models.concept_semantic_type,
        concept_semantic_types,
        {"concept_id", "semantic_type_id"},
    )
