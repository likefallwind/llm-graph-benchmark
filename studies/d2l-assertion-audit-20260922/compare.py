"""Compare fixed old/new samples and join frozen granularity; no API calls."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path


def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def build(run, granularity):
    tasks = read(run / 'tasks.json'); key = read(run / 'private-key.json')
    gkey = read(granularity / 'private-key.json'); groups = defaultdict(Counter); layers = defaultdict(Counter); changes = []; attention = []
    for t in tasks:
        id = t['id']; k = key[id]; group = groups[k['system']]; group['total'] += 1
        if id not in gkey or any(k[f] != gkey[id][f] for f in ('system', 'item_id')):
            raise ValueError('Granularity join identity mismatch: ' + id)
        p = run / 'results' / (id + '.json'); result = read(p) if p.exists() else {'status': 'pending'}
        label = result['value']['label'] if result['status'] == 'done' else 'unassessed'
        group[label] += 1
        old = k['old_correctness']; old_label = old.get('value', {}).get('label', 'unassessed'); group['old_' + old_label] += 1
        gp = granularity / 'results' / (id + '.json'); gr = read(gp) if gp.exists() else {'status': 'pending'}
        layer = gr.get('value', {}).get('label') if gr['status'] == 'done' else 'unassessed'
        layer = layer if layer in {'L1', 'L2', 'L3', 'uncertain'} else 'unassessed'
        layers[(k['system'], layer)]['total'] += 1; layers[(k['system'], layer)][label] += 1
        if result['status'] == 'done' and label != old_label:
            changes.append({'task_id': id, 'system': k['system'], 'item_id': k['item_id'], 'old': old_label, 'new': label, 'target': t['payload']['target']})
        if label != 'correct':
            v = result.get('value', {})
            attention.append({'task_id': id, 'system': k['system'], 'item_id': k['item_id'], 'status': result['status'], 'label': label, 'target': t['payload']['target'],
                'problem_claims': [dict(c, claim_index=i, excluded_as_not_asserted=i in v.get('excluded_claim_indices', [])) for i, c in enumerate(v.get('claims', [])) if c['verdict'] != 'supported'],
                'alignment': v.get('alignment'), 'pre_alignment_label': v.get('pre_alignment_label'),
                'problem_checks': {n: c for n, c in v.get('checks', {}).items() if c['verdict'] != 'supported'}})
    complete = all(g['unassessed'] == 0 for g in groups.values())
    report = {'complete': complete, 'independent_validation': False, 'groups': dict(groups), 'changes': changes,
        'granularity_source': str(granularity), 'granularity_summary_sha256': hashlib.sha256((granularity / 'summary.json').read_bytes()).hexdigest(),
        'layers': [{'system': s, 'granularity': l, **dict(c)} for (s, l), c in sorted(layers.items())]}
    (run / 'comparison.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (run / 'review-items.json').write_text(json.dumps(attention, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    lines = ['# 完整断言重评对比', '', '探索性模型评测；开发题通过不代表独立人工验证。' + ('全部样本获得有效判断。' if complete else '尚有技术未判定，不能当作完整结果。'), '',
        '旧、新列是同800条输出在不同评分协议下的确认比例，不是构图算法的性能改进。', '',
        '|方法|旧确认正确|新确认正确|明确错误|未确认|技术未判定|', '|---|---:|---:|---:|---:|---:|']
    for s, g in sorted(groups.items()):
        n = g['total']; lines.append(f"|{s}|{g['old_correct']}/{n}|{g['correct']}/{n} ({g['correct']/n:.1%})|{g['incorrect']}|{g['uncertain']}|{g['unassessed']}|")
    lines += ['', '## 既有粒度 × 新正确性', '', '不重跑粒度标签；粒度未判定项仍保留，分层确认比例分母为该层全部样本。', '',
        '|方法|粒度|确认正确/层内总数|明确错误|未确认|技术未判定|', '|---|---|---:|---:|---:|---:|']
    for (s, layer), g in sorted(layers.items()):
        lines.append(f"|{s}|{layer}|{g['correct']}/{g['total']}|{g['incorrect']}|{g['uncertain']}|{g['unassessed']}|")
    lines += ['', '新旧标签变化记录在comparison.json；非确认正确项及具体命题依据在review-items.json。技术未判定不等于事实错误；依据不足也不等于现实中必假。']
    (run / 'COMPARISON.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser();p.add_argument('--run', type=Path, required=True);p.add_argument('--granularity', type=Path, required=True);a=p.parse_args();build(a.run, a.granularity)

