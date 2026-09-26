"""Regression checks for answer leakage, full assertions and dual QA scoring."""
import copy
import json

import pytest

from llm_graph_benchmark.workflow import qa_support as qa


def wire(value):
    return {"choices": [{"message": {"content": json.dumps(value)}}]}


@pytest.fixture
def case():
    task = {"payload": {"content": {"question": "What is the cost and its condition?",
            "reference_answer": "Quadratic; only for finite state spaces.",
            "candidate_graph_assertions": [{"subject": "A", "predicate": "costs", "object": "quadratic",
                "text": "x" * 600 + "Quadratic cost.", "scope": "finite state spaces", "polarity": "negative"}]},
            "source_evidence": [{"unit_id": "P1", "text": "Quadratic; only for finite state spaces."}]}}
    rubric = {"requirements": [{"id": "R1", "text": "Quadratic", "core": True, "source_ids": ["P1"]},
                               {"id": "R2", "text": "Finite state spaces", "core": False, "source_ids": ["P1"]}],
              "source_caveat": ""}
    return task, rubric


def response(labels):
    return {"judgments": [{"requirement_id": f"R{i+1}", "label": label, "reason": "fixture",
             "assertion_evidence": [{"assertion_id": "C1", "field": "text", "quote": "Quadratic cost."}]
             if label == "pass" else []} for i, label in enumerate(labels)]}


@pytest.mark.parametrize("labels,expected", [
    (("pass", "fail"), ("pass", "fail")),
    (("pass", "uncertain"), ("pass", "uncertain")),
    (("pass", "pass"), ("pass", "pass")),
    (("fail", "pass"), ("fail", "fail")),
    (("uncertain", "pass"), ("uncertain", "uncertain")),
])
def test_dual_labels_have_fixed_denominators_and_nested_support(case, labels, expected):
    task, rubric = case
    value = qa.parse_support(wire(response(labels)), task, rubric)
    assert (value["core_label"], value["complete_label"]) == expected
    assert value["label"] == value["complete_label"]


def test_source_requirements_are_blind_and_full_assertions_reach_judge(case):
    task, rubric = case
    source_messages = qa.rubric_messages(task["payload"])
    other = copy.deepcopy(task)
    other["payload"]["content"]["candidate_graph_assertions"] = []
    assert source_messages == qa.rubric_messages(other["payload"])
    assert "candidate_graph_assertions" not in source_messages[1]["content"]
    payload = json.loads(qa.support_messages(task, rubric)[1]["content"])
    assert "reference_answer" not in payload and "reference_sources" not in payload
    assertion = payload["candidate_assertions"][0]
    assert assertion["text"].endswith("Quadratic cost.") and len(assertion["text"]) > 600
    assert assertion["polarity"] == "negative" and assertion["scope"] == "finite state spaces"


@pytest.mark.parametrize("corruption", ["answer_quote", "source_id", "no_quote", "missing_requirement"])
def test_reference_answer_cannot_substitute_for_graph_evidence(case, corruption):
    task, rubric = case
    value = response(("pass", "fail"))
    if corruption == "answer_quote":
        value["judgments"][0]["assertion_evidence"][0]["quote"] = task["payload"]["content"]["reference_answer"]
    elif corruption == "source_id":
        value["judgments"][0]["assertion_evidence"][0]["assertion_id"] = "P1"
    elif corruption == "no_quote":
        value["judgments"][0]["assertion_evidence"] = []
    else:
        value["judgments"].pop()
    with pytest.raises(ValueError):
        qa.parse_support(wire(value), task, rubric)


def test_source_rubric_requires_real_sources_and_nonempty_core(case):
    task, rubric = case
    assert qa.parse_rubric(wire(rubric), task["payload"]) == rubric
    rubric["requirements"][0]["source_ids"] = ["invented"]
    with pytest.raises(ValueError):
        qa.parse_rubric(wire(rubric), task["payload"])


def test_retired_qa_trial_cannot_start_new_work(tmp_path):
    from llm_graph_benchmark.workflow.qa_reassessment import prepare_qa_reassessment
    with pytest.raises(ValueError, match="retired"):
        prepare_qa_reassessment([], tmp_path / "run")
    assert not (tmp_path / "run").exists()
