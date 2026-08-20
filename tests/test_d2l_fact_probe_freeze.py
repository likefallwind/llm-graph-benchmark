from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path


FREEZE_DIR = Path(__file__).parents[1] / "examples" / "d2l-book-v1"


def test_d2l_fact_probe_freeze_is_balanced_and_pinned():
    manifest = json.loads((FREEZE_DIR / "freeze_manifest.json").read_text(encoding="utf-8"))
    probe_path = FREEZE_DIR / manifest["fact_probes_file"]
    probes = [json.loads(line) for line in probe_path.read_text(encoding="utf-8").splitlines()]

    digest = hashlib.sha256(probe_path.read_bytes()).hexdigest()
    assert digest == manifest["fact_probes_sha256"]
    assert len(probes) == manifest["counts"]["total"] == 48

    ids = [probe["probe_id"] for probe in probes]
    assert ids == [f"d2l-v1-f{index:03d}" for index in range(1, 49)]
    assert len(ids) == len(set(ids))

    position_counts = Counter(
        probe["metadata"]["position_band"] for probe in probes
    )
    complexity_counts = Counter(
        probe["metadata"]["complexity"] for probe in probes
    )
    assert dict(position_counts) == manifest["counts"]["by_position_band"]
    assert dict(complexity_counts) == manifest["counts"]["by_complexity"]

    for probe in probes:
        assert probe["document_id"] == manifest["document"]["document_id"]
        assert probe["importance"] == "core"
        assert probe["statement"].strip()
        assert probe["evidence_unit_ids"]
        assert all(re.fullmatch(r"P\d{6}", unit_id) for unit_id in probe["evidence_unit_ids"])


def test_d2l_qa_freeze_is_balanced_and_pinned():
    manifest = json.loads(
        (FREEZE_DIR / "qa_freeze_manifest.json").read_text(encoding="utf-8")
    )
    probe_path = FREEZE_DIR / manifest["qa_probes_file"]
    probes = [json.loads(line) for line in probe_path.read_text(encoding="utf-8").splitlines()]
    assert hashlib.sha256(probe_path.read_bytes()).hexdigest() == manifest[
        "qa_probes_sha256"
    ]
    assert len(probes) == manifest["count"] == 24
    assert Counter(probe["metadata"]["position_band"] for probe in probes) == Counter(
        manifest["position_bands"]
    )
    assert len({probe["qa_id"] for probe in probes}) == len(probes)
    assert all(probe["question"] and probe["reference_answer"] for probe in probes)
