from llm_graph_benchmark.adapters.triples import (
    MISSING_DEFINITION,
    submission_from_triples,
)


def test_submission_from_triples_merges_provenance_without_inventing_fields():
    submission, report = submission_from_triples(
        [
            {
                "subject": "A",
                "predicate": "uses",
                "object": "B",
                "evidence_unit_ids": ["p1"],
            },
            {
                "subject": "A",
                "predicate": "uses",
                "object": "B",
                "evidence_unit_ids": ["p2"],
                "subject_definition": "Entity A",
                "subject_types": ["concept"],
            },
            {"subject": "", "predicate": "bad", "object": "B"},
        ],
        entity_records=[
            {"name": "isolated", "evidence_unit_ids": ["p3"]},
        ],
        benchmark_id="bench",
        document_id="book",
        system_id="method",
        system_name="Method",
        system_version="1",
    )

    document = submission["documents"][0]
    by_name = {entity["name"]: entity for entity in document["entities"]}
    assert by_name["A"]["definition"] == "Entity A"
    assert by_name["A"]["types"] == ["concept"]
    assert by_name["B"]["definition"] == MISSING_DEFINITION
    assert by_name["isolated"]["definition"] == MISSING_DEFINITION
    assert [item["unit_id"] for item in by_name["B"]["evidence"]] == ["p1", "p2"]
    assert len(document["assertions"]) == 1
    assert [item["unit_id"] for item in document["assertions"][0]["evidence"]] == [
        "p1",
        "p2",
    ]
    assert report["rejected_records"] == 1


def test_submission_from_triples_preserves_method_text_and_scope():
    submission, _ = submission_from_triples(
        [
            {
                "subject": "优化器",
                "predicate": "related_to",
                "object": "学习率",
                "text": "优化器按照学习率更新参数。",
                "scope": "训练阶段",
                "evidence_unit_ids": ["P000001"],
            }
        ],
        benchmark_id="bench",
        document_id="doc",
        system_id="system",
        system_name="System",
        system_version="1",
    )

    assertion = submission["documents"][0]["assertions"][0]
    assert assertion["text"] == "优化器按照学习率更新参数。"
    assert assertion["scope"] == "训练阶段"
