from __future__ import annotations

from llm_graph_benchmark.bundle import SubmissionBundle
from llm_graph_benchmark.stability import compare_submissions


def test_identical_submissions_have_perfect_stability(submission_path):
    submission = SubmissionBundle.load(submission_path)
    result = compare_submissions(submission, submission, document_id="doc-1")
    assert result["entity_canonical_name_jaccard"] == 1.0
    assert result["assertion_triplet_jaccard"] == 1.0
    assert result["counts"]["reference_entities"] == 2
