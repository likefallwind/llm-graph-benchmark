from __future__ import annotations

from llm_graph_benchmark.bundle import SubmissionBundle
from llm_graph_benchmark.metrics import submission_metrics


def test_metrics_capture_graph_structure(submission_path):
    result = submission_metrics(SubmissionBundle.load(submission_path))
    assert result["summary"]["entity_count"] == 2
    assert result["summary"]["assertion_count"] == 1
    assert result["summary"]["isolated_entity_rate"] == 0.0
    assert result["documents"][0]["largest_component_ratio"] == 1.0


def test_metrics_count_isolated_entity(submission_path, submission_payload):
    submission_payload["documents"][0]["entities"].append(
        {
            "id": "e3",
            "name": "Gamma",
            "definition": "An isolated entity.",
            "types": [],
            "evidence": [],
        }
    )
    import json

    submission_path.write_text(json.dumps(submission_payload), encoding="utf-8")
    result = submission_metrics(SubmissionBundle.load(submission_path))
    assert result["summary"]["isolated_entity_rate"] == 0.333333
