import random
from typing import Any, List

from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from litmapper import models
from litmapper.db.concept_graph import (
    find_concept,
    find_concept_alias,
    find_semantic_type,
    find_source,
)
from litmapper.test.util import JsonObj, require_response_code, verify_upsert

random.seed(1)


def make_test_concepts(db_txn: Session) -> List[JsonObj]:
    test_concepts = [
        {
            "concept_id": "C1111",
            "name": "concept1",
            "aliases": [],
            "semantic_types": [],
        },
        {
            "concept_id": "C2222",
            "name": "concept2",
            "aliases": [],
            "semantic_types": [],
        },
        {
            "concept_id": "C3333",
            "name": "concept3",
            "aliases": [],
            "semantic_types": [],
        },
    ]
    for model_data in test_concepts:
        db_txn.add(models.Concept(**model_data))
    db_txn.commit()

    return test_concepts


def make_test_semantic_types(db_txn: Session) -> List[JsonObj]:
    test_semantic_types = [
        {
            "semantic_type_id": "T111",
            "name": "type",
        },
        {
            "semantic_type_id": "T222",
            "name": "type2",
        },
        {
            "semantic_type_id": "T333",
            "name": "type3",
        },
    ]
    for model_data in test_semantic_types:
        db_txn.add(models.SemanticType(**model_data))
    db_txn.commit()

    return test_semantic_types


def make_test_sources(db_txn: Session) -> List[JsonObj]:
    test_sources = [
        {
            "source_id": "S11",
            "name": "source",
        },
        {
            "source_id": "S22",
            "name": "source2",
        },
        {
            "source_id": "S33",
            "name": "source3",
        },
    ]
    for model_data in test_sources:
        db_txn.add(models.Source(**model_data))
    db_txn.commit()

    return test_sources


def make_test_concept_aliases(
    db_txn: Session, concepts: List[JsonObj], sources: List[JsonObj]
) -> List[JsonObj]:
    test_concept_aliases = []

    for i, (concept, source) in enumerate(zip(concepts, sources)):
        concept_alias = {
            "concept_alias_id": str(i),
            "alias_name": f"{concept['name']}{i}",
            "source_concept_id": f"{source['name']}{i}",
            "concept_id": concept["concept_id"],
            "source_id": source["source_id"],
        }
        db_txn.add(models.ConceptAlias(**concept_alias))
        test_concept_aliases.append(concept_alias)

    db_txn.commit()

    return test_concept_aliases


def make_test_concept_semantic_types(
    db_txn: Session, concepts: List[JsonObj], semantic_types: List[JsonObj]
) -> List[JsonObj]:
    test_concept_semantic_types = []

    for concept, semantic_type in zip(concepts, semantic_types):
        concept_semantic_type = {
            "concept_id": concept["concept_id"],
            "semantic_type_id": semantic_type["semantic_type_id"],
        }
        db_txn.execute(
            models.concept_semantic_type.insert(values=concept_semantic_type)
        )
        test_concept_semantic_types.append(concept_semantic_type)

    db_txn.commit()

    return test_concept_semantic_types


def test_get_concept(db_txn: Session, api_client: TestClient):
    res = api_client.get("/concept_graph/concept/0")
    require_response_code(res, 404)

    test_concepts = make_test_concepts(db_txn)

    res = api_client.get(f"/concept_graph/concept/{test_concepts[0]['concept_id']}")
    require_response_code(res, 200)
    assert res.json() == test_concepts[0]


def test_upsert_concepts(db_txn: Session, api_client: TestClient):
    test_data = make_test_concepts(db_txn)
    modified_test_data = (
        {**test_data[0], "name": "concept1_update"},
        {**test_data[1], "name": "concept2_update"},
        {**test_data[2], "name": "concept3_update"},
    )

    def key_func(json_obj: JsonObj) -> Any:
        return json_obj["concept_id"]

    def find_func(db: Session, key: Any) -> Any:
        return find_concept(db, key)

    def compare_func(db_obj: Any, json_obj: JsonObj):
        assert db_obj.name == json_obj["name"]

    verify_upsert(
        api_client,
        db_txn,
        test_data,
        modified_test_data,
        "/concept_graph/concepts",
        key_func,
        find_func,
        compare_func,
    )


def test_get_sources(db_txn: Session, api_client: TestClient):
    res = api_client.get("/concept_graph/sources")
    require_response_code(res, 200)
    assert res.json() == []

    test_sources = make_test_sources(db_txn)

    res = api_client.get("/concept_graph/sources")
    require_response_code(res, 200)
    assert res.json() == test_sources


def test_upsert_sources(db_txn: Session, api_client: TestClient):
    test_data = make_test_sources(db_txn)

    # We don't have any other data to update based on the keys, so
    # just use the original test data
    modified_test_data = test_data

    def key_func(json_obj: JsonObj) -> Any:
        return json_obj["source_id"]

    def find_func(db: Session, key: Any) -> Any:
        return find_source(db, key)

    def compare_func(db_obj: Any, json_obj: JsonObj):
        assert db_obj.name == json_obj["name"]

    verify_upsert(
        api_client,
        db_txn,
        test_data,
        modified_test_data,
        "/concept_graph/sources",
        key_func,
        find_func,
        compare_func,
    )


def test_get_semantic_types(db_txn: Session, api_client: TestClient):
    res = api_client.get("/concept_graph/semantic_types")
    require_response_code(res, 200)
    assert res.json() == []

    test_semantic_types = make_test_semantic_types(db_txn)

    res = api_client.get("/concept_graph/semantic_types")
    require_response_code(res, 200)
    assert res.json() == test_semantic_types


def test_upsert_semantic_types(db_txn: Session, api_client: TestClient):
    test_data = make_test_semantic_types(db_txn)

    # We don't have any other data to update based on the keys, so
    # just use the original test data
    modified_test_data = test_data

    def key_func(json_obj: JsonObj) -> Any:
        return json_obj["semantic_type_id"]

    def find_func(db: Session, key: Any) -> Any:
        return find_semantic_type(db, key)

    def compare_func(db_obj: Any, json_obj: JsonObj):
        assert db_obj.name == json_obj["name"]

    verify_upsert(
        api_client,
        db_txn,
        test_data,
        modified_test_data,
        "/concept_graph/semantic_types",
        key_func,
        find_func,
        compare_func,
    )


def test_get_concept_alias(db_txn: Session, api_client: TestClient):
    res = api_client.get("/concept_graph/alias/0")
    require_response_code(res, 404)

    test_concepts = make_test_concepts(db_txn)
    test_sources = make_test_sources(db_txn)
    test_concept_aliases = make_test_concept_aliases(
        db_txn, test_concepts, test_sources
    )

    res = api_client.get(
        f"/concept_graph/alias/{test_concept_aliases[0]['concept_alias_id']}"
    )
    require_response_code(res, 200)
    assert res.json() == test_concept_aliases[0]


def test_upsert_concept_aliases(db_txn: Session, api_client: TestClient):
    test_concepts = make_test_concepts(db_txn)
    test_sources = make_test_sources(db_txn)
    test_data = make_test_concept_aliases(db_txn, test_concepts, test_sources)

    modified_test_data = [
        {
            **a,
            "alias_name": f"{a['alias_name']}_updated",
        }
        for a in test_data
    ]

    def key_func(json_obj: JsonObj) -> Any:
        return json_obj["concept_alias_id"]

    def find_func(db: Session, key: Any) -> Any:
        return find_concept_alias(db, key)

    def compare_func(db_obj: Any, json_obj: JsonObj):
        for field in (
            "concept_alias_id",
            "concept_id",
            "source_id",
            "alias_name",
            "source_concept_id",
        ):
            assert getattr(db_obj, field) == json_obj[field]

    verify_upsert(
        api_client,
        db_txn,
        test_data,
        modified_test_data,
        "/concept_graph/aliases",
        key_func,
        find_func,
        compare_func,
    )


def test_upsert_concept_semantic_types(db_txn: Session, api_client: TestClient):
    test_concepts = make_test_concepts(db_txn)
    test_semantic_types = make_test_semantic_types(db_txn)
    test_data = make_test_concept_semantic_types(
        db_txn, test_concepts, test_semantic_types
    )

    # We don't have any other data to update based on the keys, so
    # just use the original test data
    modified_test_data = test_data

    def key_func(json_obj: JsonObj) -> Any:
        return (json_obj["concept_id"], json_obj["semantic_type_id"])

    def find_func(db: Session, key: Any) -> Any:
        return db.execute(
            models.concept_semantic_type.select()
            .where(models.concept_semantic_type.c.concept_id == key[0])
            .where(models.concept_semantic_type.c.semantic_type_id == key[1])
        ).first()

    def compare_func(db_obj: Any, json_obj: JsonObj):
        assert (
            db_obj.concept_id == json_obj["concept_id"]
            and db_obj.semantic_type_id == json_obj["semantic_type_id"]
        )

    verify_upsert(
        api_client,
        db_txn,
        test_data,
        modified_test_data,
        "/concept_graph/concepts/semantic_types",
        key_func,
        find_func,
        compare_func,
    )
