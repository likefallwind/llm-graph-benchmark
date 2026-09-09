"""Validate final artifacts and report joint precision, axes, pilot disagreement and lineage."""
from __future__ import annotations
import argparse,collections,datetime,hashlib,importlib.util,json,math
from pathlib import Path
from llm_graph_benchmark.aggregation import aggregate_judgments
from llm_graph_benchmark.verdict_recovery import recover_reason_quotes

LABELS={'pass','fail','uncertain'}
NAMES={'llm-knowledge-graph-full1105-vnext':'本方法（历史 vNext 图）',
       'autoschemakg-minimax-m3-semantic':'AutoSchemaKG（语义抽取子集）',
       'kggen-minimax-m3-exactdedup':'KGGen（精确去重对照）',
       'kggen-minimax-m3-official':'KGGen（semhash，未做 LLM 归一）',
       'graphrag-fast-default':'GraphRAG Fast（英文 NLP 配置）'}
def read(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write_new(p,value):
    with p.open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')

def audit_response(row, run, expected_model):
    attempts=row.get('attempts',[])
    if not attempts or attempts[-1].get('status')!='success':raise ValueError('accepted judgment lacks successful response')
    path=(run/attempts[-1]['response_file']).resolve()
    if run.resolve() not in path.parents:raise ValueError('response file outside run')
    response=json.loads(path.read_text())
    if response.get('model')!=expected_model:raise ValueError('returned model differs from configured judge')
    if (response.get('base_resp') or {}).get('status_code',0) not in (0,'0',None):raise ValueError('accepted provider error')
    if response['choices'][0].get('finish_reason')=='length':raise ValueError('accepted truncated response')
    return response['model']

def compare_review(review,results):
    votes={r['task_id']:r for r in results}
    if len(votes)!=len(results):raise ValueError('duplicate API task')
    if len({r['task_id'] for r in review})!=len(review):raise ValueError('duplicate review task')
    matched=0;transitions=collections.Counter();diff=[]
    for ref in review:
        if ref['task_id'] not in votes or votes[ref['task_id']]['label'] not in LABELS:raise ValueError('review panel incomplete')
        got=votes[ref['task_id']];transitions[ref['label']+'->'+got['label']]+=1
        matched+=ref['label']==got['label']
        if ref['label']!=got['label']:
            diff.append(dict(task_id=ref['task_id'],codex_label=ref['label'],minimax_label=got['label'],
                codex_reason=ref['reason'],minimax_reason=got['reason'],borderline=ref.get('borderline',False)))
    return dict(count=len(review),matched=matched,agreement=matched/len(review) if review else None,
        transitions=dict(transitions),disagreements=diff,
        minimax_pass_codex_fail=transitions['fail->pass'],minimax_fail_codex_pass=transitions['pass->fail'],
        interpretation='Relative disagreement with Codex, not true error rates. Same-corpus small panel, protocol author as reviewer, not independent human gold.')

def recover_failed_row(row, task, run, parse_verdict):
    if row.get('label') != 'error':
        raise ValueError('only failed rows may be recovered')
    # Chronological first valid response, without inspecting which label it has.
    for attempt in row.get('attempts', []):
        if attempt.get('status') != 'error' or not attempt.get('response_file'):
            continue
        candidate = {**attempt, 'status': 'success'}
        try:
            audit_response({'attempts': [candidate]}, run, 'MiniMax-M3')
            path = run / attempt['response_file']
            content = json.loads(path.read_text())['choices'][0]['message']['content']
            corrected, detail = recover_reason_quotes(content)
            verdict = parse_verdict(corrected, task)
        except (ValueError, KeyError, IndexError, OSError):
            continue
        note = dict(**detail, original_attempt=attempt['attempt'], response_file=attempt['response_file'],
                    response_sha256=sha(path), corrected_content_sha256=hashlib.sha256(corrected.encode()).hexdigest(),
                    selection='first chronologically recoverable response; no semantic label selection')
        # This is an offline parse event, with no new API request or token usage.
        event = dict(status='success', operation='local_syntax_recovery', response_file=attempt['response_file'])
        return {**row, **verdict, 'attempts': [*row['attempts'], event], 'syntax_recovery': note}
    raise ValueError('failed row has no safely recoverable complete response: ' + row['task_id'])


def analyze(run,prepared,previous,out,*,recover_reason=False):
    if out.exists():raise ValueError('fresh report directory required')
    summary=json.loads((run/'summary.json').read_text());launch=json.loads((run/'launch.json').read_text())
    raw_summary=dict(summary)
    if summary['status']!='complete' or summary['scored']!=summary['total'] or summary['errors'] or summary['missing']:
        if not (recover_reason and summary['status']=='incomplete' and summary['missing']==0
                and summary['scored']+summary['errors']==summary['total']
                and (run/'.exit').read_text().strip()=='1'):
            raise ValueError('run incomplete')
    elif (run/'.exit').read_text().strip()!='0' or not (run/'.finished').exists():
        raise ValueError('completion markers absent')
    for name,h in {**launch['source_sha256'],**launch['inputs_sha256']}.items():
        if sha(run/name)!=h:raise ValueError('snapshot changed: '+name)
    keys=read(run/'key.jsonl');tasks=read(run/'tasks.jsonl');rows=read(run/'judgments.jsonl')
    spec=importlib.util.spec_from_file_location('frozen_quality_judge',run/'source/judge.py')
    parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)
    if sum(r['label'] in LABELS for r in rows)!=raw_summary['scored'] or sum(r['label']=='error' for r in rows)!=raw_summary['errors']:
        raise ValueError('raw summary and row counts differ')
    task_lookup={t['task_id']:t for t in tasks}
    if recover_reason:
        rows=[recover_failed_row(r,task_lookup[r['task_id']],run,parser.parse_verdict) if r['label']=='error' else r for r in rows]
    recoveries=[dict(task_id=r['task_id'],**r['syntax_recovery']) for r in rows if 'syntax_recovery' in r]
    if any(r['label'] not in LABELS for r in rows):raise ValueError('unresolved rows remain')
    summary=dict(raw_summary,status='complete',scored=len(rows),errors=0,missing=0,local_syntax_recoveries=len(recoveries))
    bykey={k['task_id']:k for k in keys};bytask={t['task_id']:t for t in tasks};byrow={r['task_id']:r for r in rows}
    if len(keys)!=1000 or len(byrow)!=len(rows) or set(byrow)!=set(bykey):raise ValueError('expected exactly 1000 unique judgments')
    returned_models=collections.Counter()
    for r in rows:
        returned_models[audit_response(r,run,launch["model"])]+=1
        t=bytask[r['task_id']]
        raw=json.loads((run/r['attempts'][-1]['response_file']).read_text())['choices'][0]['message']['content']
        if 'syntax_recovery' in r:raw,_=recover_reason_quotes(raw)
        parsed=parser.parse_verdict(raw,t)
        if any(r.get(k)!=v for k,v in parsed.items()):raise ValueError('reported verdict differs from original response')
        if r['judge_id']!=launch['judge_id'] or r['label'] not in LABELS:raise ValueError('invalid final label or judge')
        if r['evaluated_triple']!={k:t['content'][k] for k in ('subject','predicate','object')}:raise ValueError('field echo mismatch')
        axes=[r[k] for k in ('edge_label','description_label','condition_label')]
        if any(v not in LABELS for v in axes):raise ValueError('invalid axis')
        derived='fail' if 'fail' in axes else 'uncertain' if 'uncertain' in axes else 'pass'
        if derived!=r['label']:raise ValueError('joint label mismatch')
    freeze=json.loads((prepared/'codex-review-freeze.json').read_text())
    if sha(prepared/'codex-blind-review.jsonl')!=freeze['review_sha256'] or launch['pre_api_review_sha256']!=freeze['review_sha256']:raise ValueError('review labels not frozen')
    if datetime.datetime.fromisoformat(freeze['frozen_at'])>=datetime.datetime.fromisoformat(launch['started_at']):raise ValueError('review was not frozen before API launch')
    metrics=aggregate_judgments(keys,rows)
    review=read(prepared/'codex-blind-review.jsonl');agreement=compare_review(review,rows)
    old={r['task_id']:r for r in read(previous/'judgments.jsonl')}
    transitions=collections.defaultdict(collections.Counter);axes=collections.defaultdict(lambda:collections.defaultdict(collections.Counter))
    retries=collections.Counter();repaired=0
    for r in rows:
        k=bykey[r['task_id']];system=k['system_id']
        transitions[system][old.get(k['previous_task_id'],{}).get('label','missing')+'->'+r['label']]+=1
        for axis in ('edge_label','description_label','condition_label'):axes[system][axis][r[axis]]+=1
        repaired+=len(r.get('attempts',[]))>1
        for a in r.get('attempts',[]):
            if a.get('status')=='error':retries[a.get('error','unknown')]+=1
    evidence_stats={}
    for system in sorted({k['system_id'] for k in keys}):
        selected=[bytask[k['task_id']] for k in keys if k['system_id']==system]
        lengths=sorted(sum(len(e.get('unit',e).get('text','')) for e in t['source_evidence']) for t in selected)
        evidence_stats[system]=dict(samples=len(lengths),without_evidence=sum(not t['source_evidence'] for t in selected),
            source_chars_p50=lengths[(len(lengths)-1)//2],source_chars_p90=lengths[int((len(lengths)-1)*.9)],source_chars_max=max(lengths))
    scope=json.loads((previous/'manifest.json').read_text())['baseline_scope']
    record=dict(status='complete',version='v2.2',run=str(run),prepared=str(prepared),summary=summary,raw_runner_summary=raw_summary,syntax_recoveries=recoveries,
        method_metrics=metrics['systems'],axes={s:{a:dict(c) for a,c in v.items()} for s,v in axes.items()},
        v1_to_v22_transitions={s:dict(c) for s,c in transitions.items()},review=agreement,
        tasks_with_retries=repaired,retry_errors=dict(retries),baseline_scope=scope,returned_models=dict(returned_models),evidence_stats=evidence_stats,
        output_truth='Complete same-model descriptive comparison; not a human-calibrated estimate of absolute accuracy, not proof of SOTA.',
        lineage_sha256={str(p):sha(p) for p in (run/'judgments.jsonl',run/'tasks.jsonl',run/'key.jsonl',prepared/'manifest.json',prepared/'codex-blind-review.jsonl')})
    lines=['# D2L 单条断言质量 v2.2 — 完成报告','',
      f"已完成 {summary['scored']}/{summary['total']} 条，错误 {summary['errors']}，缺失 {summary['missing']}；MiniMax-M3 官方 API，并发 4。",
      f"其中 {len(recoveries)} 条通过本地解释文字引号转义恢复；原始运行状态与失败响应保持不变，恢复审计见 syntax-recovery.json。",
      '联合通过要求显式关系、描述和真值必要条件均通过；程序核对返回的主谓宾与输入逐字一致。',
      'v1/v2/v2.1 的原始规则与结果均保留，本次不重写辅助事实恢复评分。','',
      '## 单条精度（全部样本为分母）','',
      '| 方法 | 通过/总数 | Pass/all | Fail | Uncertain | Pass/decided | Wilson 区间（decided） |',
      '|---|---:|---:|---:|---:|---:|---|']
    order=list(NAMES)
    for s in order:
        m=metrics['systems'][s]['assertion_quality_v2_2'];ci=m['pass_rate_95ci']
        lines.append(f"| {NAMES[s]} | {m['pass']}/{m['expected']} | {m['pass_rate_all']:.1%} | {m['fail']} | {m['uncertain']} | {m['pass_rate']:.1%} | [{ci[0]:.1%}, {ci[1]:.1%}] |")
    lines+=['','区间仅描述明确判定样本的二项抽样不确定性，不覆盖同书相关性、裁判偏差或跨材料泛化。',
       '各方法抽样的是各自输出，不是同一组原子事实；不能做跨方法配对 McNemar 或与旧恢复率直接拼接 F1。',
       'GraphRAG Fast 的共现边可在自身命题上正确，但不等同于有意义的实体关系抽取；它是低成本参照，不放入语义抽取方法的胜负结论。','',
       '## 三个分项（通过/200）','','| 方法 | 关系 | 描述 | 条件 |','|---|---:|---:|---:|']
    for s in order:lines.append('| '+NAMES[s]+' | '+' | '.join(str(axes[s][a]['pass']) for a in ('edge_label','description_label','condition_label'))+' |')
    lines+=['','分项错误可以重叠；分项通过率不能相乘当成联合通过率。','',
       '## 提供给裁判的证据长度','','| 方法 | 无证据条目 | 来源字符 P50 | P90 | 最大值 |','|---|---:|---:|---:|---:|']
    for system in order:
        e=evidence_stats[system]
        lines.append(f"| {NAMES[system]} | {e['without_evidence']} | {e['source_chars_p50']} | {e['source_chars_p90']} | {e['source_chars_max']} |")
    lines+=['','保留全部原始证据而未裁剪；长度和引用粒度并未跨方法统一。未显式提供系统名，但内容/证据风格仍可能透露系统来源。',
       '这些差异可能影响裁判难度，故当前分数不能直接视为无偏的真实精度。','',
       '## 不查看 MiniMax 标签的 25 条复核','','每个系统 5 条，排除此前 95 条开发复核材料和已展示案例；在调用前冻结 Codex 标签。',
       f"标签一致 {agreement['matched']}/{agreement['count']}（{agreement['agreement']:.1%}）。MiniMax pass / Codex fail：{agreement['minimax_pass_codex_fail']}；MiniMax fail / Codex pass：{agreement['minimax_fail_codex_pass']}。",
       '这是模型间的小规模复核；Codex 同时参与协议设计，不能称为独立人工金标准，也不能用 5 条/系统推断总体错误率。',
       '其中一个长证据任务使用全源词项检索与相关段落核对，四条边界例在查看 MiniMax 标签前已标注；不删掉分歧来提高一致率。','']
    for d in agreement['disagreements']:
        lines += [f"- `{d['task_id']}`：Codex={d['codex_label']}，MiniMax={d['minimax_label']}；预标记边界={d['borderline']}。",
                  '  - Codex：'+d['codex_reason'].replace('\n',' '), '  - MiniMax：'+d['minimax_reason'].replace('\n',' ')]
    lines+=['','## 相对 v1 的标签迁移','','| 方法 | fail→pass | pass→fail | error→有效标签 |','|---|---:|---:|---:|']
    for s in order:
        c=transitions[s];lines.append(f"| {NAMES[s]} | {c['fail->pass']} | {c['pass->fail']} | {sum(c['error->'+v] for v in LABELS)} |")
    lines+=['','版本同时改变测量规则和输出校验，迁移不是算法提升，不能当作新增实验增益。','',
       '## 费用、重试与证据完整性','',
       f"本次全量运行记录 {summary['usage_including_retries'].get('total_tokens',0):,} tokens（含记录到的重试）；{repaired} 条有重试。没有权威单价，未估算费用。",
       '缺失或语法/字段回填无效的响应可重试；有效 pass/fail/uncertain 不按是否符合预期重试。原始响应和尝试记录全部保留。',
       '已核对每条最终接受响应的模型标识：'+str(dict(returned_models))+'；无提供方错误或截断响应被接受。','',
       '## 结论边界','',
       '本轮完成了评测协议修订、规则检查、同一模型统一重评分与小规模交叉复核。规则检查是开发测试，不是测量效度证明。',
       'AutoSchemaKG 只测语义抽取子集；KGGen 未完成 LLM 归一；GraphRAG 为中文材料上的 Fast 英文配置；本方法也对应历史快照。',
       '下一步要验证算法贡献，应做同预算基线+校验对照与本方法消融，再扩展语料；不能由这一张表宣称全面或显著 SOTA。','']
    out.mkdir(parents=True);write_new(out/'analysis.json',record)
    write_new(out/'syntax-recovery.json',dict(policy='terminal-reason-quotes-v1',recoveries=recoveries,
        original_run_summary=raw_summary,original_run_unmodified=True,
        parser_sha256=sha(Path(__file__).parents[2]/'src/llm_graph_benchmark/verdict_recovery.py'),
        analysis_script_sha256=sha(Path(__file__))))
    (out/'judgments.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
    (out/'RESULTS.md').write_text('\n'.join(lines),encoding='utf-8')
    (out/'.finished').write_text(datetime.datetime.now().astimezone().isoformat()+'\n')
    print(json.dumps({'status':'complete','out':str(out),'agreement':agreement['agreement'],'methods':{s:metrics['systems'][s]['assertion_quality_v2_2']['pass_rate_all'] for s in order}},ensure_ascii=False))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--prepared',type=Path,required=True);p.add_argument('--previous',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--recover-reason-quotes',action='store_true',help='Offline terminal reason quote escaping only; raw run remains unchanged')
    a=p.parse_args();analyze(a.run,a.prepared,a.previous,a.out,recover_reason=a.recover_reason_quotes)
