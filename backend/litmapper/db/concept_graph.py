from typing import Optional

from sqlalchemy.orm import Session

from litmapper import models


def find_concept(db: Session, concept_id: str) -> Optional[models.Concept]:
    return (
        db.query(models.Concept).filter(models.Concept.concept_id == concept_id).first()
    )


def find_source(db: Session, source_id: str) -> Optional[models.Source]:
    return db.query(models.Source).filter(models.Source.source_id == source_id).first()


def find_semantic_type(
    db: Session, semantic_type_id: str
) -> Optional[models.SemanticType]:
    return (
        db.query(models.SemanticType)
        .filter(models.SemanticType.semantic_type_id == semantic_type_id)
        .first()
    )


def find_concept_alias(
    db: Session, concept_alias_id: str
) -> Optional[models.ConceptAlias]:
    return (
        db.query(models.ConceptAlias)
        .filter(models.ConceptAlias.concept_alias_id == concept_alias_id)
        .first()
    )
