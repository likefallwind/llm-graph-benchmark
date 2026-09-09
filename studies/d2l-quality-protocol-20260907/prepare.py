"""Prepare new judgments for the existing 200-assertion/48-fact samples, offline."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from llm_graph_benchmark.io import write_json, write_jsonl
from llm_graph_benchmark.quality import prepare_quality_tasks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('output already exists; use a fresh directory')
    root = args.repo / 'outputs'
    hashes = {}

    def read(path):
        data = path.read_bytes()
        hashes[str(path.relative_to(args.repo))] = hashlib.sha256(data).hexdigest()
        return [json.loads(line) for line in data.splitlines() if line.strip()]

    tasks, keys = [], []
    for dirname in ('d2l-fullbook-axes-20260827', 'd2l-fullbook-axes-askg-20260828'):
        directory = root / dirname
        axis_keys = {r['task_id']: r for r in read(directory / 'axis-task-key.jsonl')}
        for row in read(directory / 'axis-tasks.jsonl'):
            if row['kind'] != 'assertion_grounding_v3':
                continue
            key = axis_keys[row['task_id']]
            # Recover the existing sampled assertion, not a new sample or old verdict.
            source_id = row['source_task_id']
            tasks.append({**row, 'task_id': source_id, 'kind': 'assertion_grounding'})
            keys.append({**key, 'task_id': source_id, 'kind': 'assertion_grounding'})
    baselines = root / 'd2l-fullbook-open-baselines-20260826' / 'runs'
    directories = [root / 'd2l-full1105-vnext-20260826' / 'evaluation']
    directories += [baselines / name / evaluation for name, evaluation in (
        ('kggen-minimax-m3-official-full1105', 'evaluation'),
        ('kggen-minimax-m3-official-full1105-exactdedup', 'evaluation'),
        ('graphrag-fast-full1105', 'evaluation'),
        ('autoschemakg-minimax-m3-official-full1105', 'evaluation-semantic'))]
    for directory in directories:
        facts = read(directory / 'probe-tasks.jsonl')
        fact_keys = read(directory / 'probe-task-key.jsonl')
        retrieval = {(r['system_id'], r['probe_id']): r for r in read(directory / 'retrieval-lexical.jsonl')}
        for key in fact_keys:
            retrieved = retrieval[key['system_id'], key['item_id']]
            assert retrieved['retriever'] == key['retriever']
            key['retriever_params'] = retrieved['retriever_params']
        tasks.extend(facts)
        keys.extend(fact_keys)
    output = prepare_quality_tasks(tasks, keys)
    counts = Counter((r['system_id'], r['kind']) for r in output.key)
    systems = sorted({s for s, _ in counts})
    assert len(systems) == 5
    for system in systems:
        assert counts[system, 'assertion_quality_v1'] == 200
        assert counts[system, 'fact_recovery_strict_v1'] == 48
        assert counts[system, 'fact_recovery_core_v1'] == 48
    # These flags describe the frozen runs, not the full upstream methods.
    scope = {
        'llm-knowledge-graph-full1105-vnext': 'historical completed graph; not a fresh current-code evaluation',
        'kggen-minimax-m3-official': 'extraction plus semhash; LLM normalization not run',
        'kggen-minimax-m3-exactdedup': 'extraction plus local exact union control; LLM normalization not run',
        'graphrag-fast-default': 'Fast NLP English configuration on Chinese corpus; low-cost reference',
        'autoschemakg-minimax-m3-semantic': 'semantic extraction subset; conceptualization incomplete',
    }
    args.out.mkdir(parents=True)
    write_jsonl(args.out / 'tasks.jsonl', output.tasks)
    write_jsonl(args.out / 'key.jsonl', output.key)
    manifest = dict(status='prepared-not-judged', model_calls=0, tasks=len(output.tasks),
                    source_sample='existing 200 assertions and 48 frozen probes per system',
                    source_sha256=hashes, baseline_scope=scope,
                    counts={s: {k: n for (system, k), n in counts.items() if system == s} for s in systems})
    write_json(args.out / 'manifest.json', manifest)
    print(json.dumps({'status': manifest['status'], 'tasks': len(output.tasks), 'out': str(args.out)}))


if __name__ == '__main__':
    main()
