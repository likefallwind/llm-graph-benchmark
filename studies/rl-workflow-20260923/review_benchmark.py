"""Source-only editorial review before any graph judgment; preserve the draft."""
from pathlib import Path
import json
import hashlib

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/rl-book2-20260923"
def rd(path):return json.loads(path.read_text(encoding="utf-8-sig"))
def wr(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n")
facts=[json.loads(x) for x in (OUT/"fact_probes.jsonl").read_text().splitlines()]
qas=[json.loads(x) for x in (OUT/"qa_probes.jsonl").read_text().splitlines()]
provenance=rd(OUT/"benchmark-provenance.json")
items={x["id"]:x for x in provenance["items"]}
jobs={j["chapter"]:j for j in rd(OUT/"probe-jobs.json")}
revisions={
"rl-fact-ch01-1":({"statement":"In reinforcement learning, state is an input to the policy and value function, and is both an input to and an output from the model."},["S2:P000035"],"Replace a claim about the book's excluded scope with the substantive state-role statement in the same paragraph."),
"rl-fact-ch01-2":({"statement":"Reinforcement learning emphasizes goal-directed learning from interaction with the environment."},["S2:P000003","S2:P000004"],"Replace authorial perspective with the explicit learning principle in the same source window."),
"rl-fact-ch02-2":({"statement":"Epsilon-greedy action selection behaves greedily most of the time, but with a small exploration probability selects uniformly from all actions independently of their action-value estimates."},["S2:P000118","S2:P000119"],"Use the directly defined rule; avoid generalizing a contextual convergence statement without its estimation assumptions."),
"rl-qa-ch02-2":({"question":"How can optimistic initial action-value estimates encourage exploration even when actions are selected greedily?","reference_answer":"Rewards lower than the optimistic starting estimates disappoint the learner, which switches to other actions. Actions are therefore tried several times before estimates converge, producing exploration even with greedy action selection."},["S2:P000157","S2:P000158"],"The original 'why nonstationary' answer was incomplete because its source window ended mid-explanation; ask a fully supported question within the unchanged window."),
"rl-qa-ch05-1":({"question":"In the 100-step importance-sampling example where the return is determined by the first reward alone, why do the importance-sampling factors after the first add variance without changing the expected update?","reference_answer":"The later factors are independent of the already determined return and each has expected value one. They do not change the expected update but can add enormous, even infinite, variance."},["S2:P000625","S2:P000626"],"State the special first-reward-return condition instead of presenting it as a property of all off-policy returns."),
"rl-qa-ch06-2":({"question":"In the bandit discussion of maximization bias, what problem arises when the same noisy samples are used both to select the maximizing action and to estimate its value?","reference_answer":"Using the same samples for action selection and value estimation produces positive maximization bias: the maximum of noisy action-value estimates can overestimate the maximum of the true action values."},["S2:P000759"],"Replace a figure-dependent question and an answer containing missing PDF symbols with a self-contained question explicitly supported in the same source window."),
"rl-fact-ch07-2":({"statement":"N-step TD methods span a spectrum between one-step temporal-difference and Monte Carlo methods, allowing bootstrapping to occur over multiple time steps."},None,"Remove authorial chapter-description wording; preserve the substantive principle."),
"rl-fact-ch09-2":({"statement":"A value-prediction update shifts the estimated value of a state toward an update target, which can be interpreted as an example of the desired input-output behavior of the value function."},["S2:P001077"],"Avoid a copied TD formula with a missing discount symbol; retain the explicit prose meaning."),
"rl-fact-ch09-3":({"statement":"With general function approximation, there is no clear notion of a number of experiences with a single state, because states can be similar to or dissimilar from other states to varying degrees."},["S2:P001235"],"Avoid the draft's incorrect 'outer product' interpretation of a damaged scalar step-size formula; use intact substantive prose from the same window."),
"rl-fact-ch10-1":({"statement":"Semi-gradient Sarsa extends semi-gradient TD(0) from state values to action values and to on-policy control."},["S2:P001335"],"Use the substantive algorithm relationship instead of a chapter overview."),
"rl-qa-ch10-1":({"question":"What limitation does the chapter identify for local policy improvement guarantees in action-value methods once function approximation is introduced?","reference_answer":"The chapter states that local policy improvement is no longer guaranteed for these action-value methods, including the total-episodic and average-reward settings. Epsilon-greedification can sometimes yield an inferior policy, and policies may chatter rather than converge."},["S2:P001423"],"The draft asked about an unspecified proposed discounted objective; use a self-contained statement whose full conditions are present in the unchanged window."),
}
audit=[]
for row in facts+qas:
 iid=row.get("probe_id",row.get("qa_id"))
 if iid not in revisions:continue
 fields,refs,reason=revisions[iid]
 original=json.loads(json.dumps(row))
 item=items[iid]
 chapter=row["metadata"]["chapter"]
 block=next(b for b in jobs[chapter]["blocks"] if b["block_id"]==item["block_id"])
 sources={u["id"]:u["text"] for u in block["evidence"]}
 refs=refs or row["evidence_unit_ids"]
 assert set(refs)<=set(sources)
 row.update(fields);row["evidence_unit_ids"]=refs
 item.update(fields);item["evidence_ids"]=refs
 item["quotes"]=[{"id":uid,"text":sources[uid],"materialized_from_source":True} for uid in refs]
 item["editorial_reason"]=reason
 audit.append({"id":iid,"before":original,"after":row,"reason":reason,"same_source_window":True})
for name,rows in [("fact_probes-reviewed.jsonl",facts),("qa_probes-reviewed.jsonl",qas)]:
 assert not (OUT/name).exists(),"Reviewed benchmark already exists"
 (OUT/name).write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in rows))
benchmark=rd(OUT/"benchmark.json")
benchmark.update(fact_probes_file="fact_probes-reviewed.jsonl",qa_probes_file="qa_probes-reviewed.jsonl")
benchmark["metadata"]={"probe_version":"source-reviewed-v1","draft_retained":True,"graph_judgments_seen":False}
wr(OUT/"benchmark-reviewed.json",benchmark)
provenance.update(editorial_review="Assistant source-only review before graph judging; not independent human gold",
                  changes=audit,graph_scores_available_during_review=False)
wr(OUT/"benchmark-provenance-reviewed.json",provenance)
wr(OUT/"benchmark-editorial-audit.json",{"items_changed":len(audit),"source_only":True,
 "original_windows_unchanged":True,"model_judge_prompts_unchanged":True,"changes":audit})
lines=["# 强化学习来源基准（评分前复核版）","","48条事实，24道QA；17章来源窗口不变。原稿与修改记录均保留，没有查看图谱评分。",""]
for row in facts:
 lines += ["## "+row["probe_id"],"",row["statement"],"","来源："+", ".join(row["evidence_unit_ids"]),""]
for row in qas:
 lines += ["## "+row["qa_id"],"",row["question"],"","参考答案："+row["reference_answer"],"","来源："+", ".join(row["evidence_unit_ids"]),""]
(OUT/"BENCHMARK_REVIEWED.md").write_text("\n".join(lines))
config=rd(OUT/"workflow.json");config["benchmark"]="benchmark-reviewed.json"
wr(OUT/"workflow-reviewed.json",config)
# Only study orchestration changes: the common evaluator and its prompts stay frozen.
p=Path(__file__).with_name("run_pipeline.py");s=p.read_text(encoding="utf-8-sig")
s=s.replace('RUN = OUT / "evaluation"','RUN = OUT / "evaluation-reviewed-v1"')
s=s.replace('OUT / "workflow.json"','OUT / "workflow-reviewed.json"')
s=s.replace('"benchmark": "benchmark.json"','"benchmark": "benchmark-reviewed.json"')
s=s.replace('("source-freeze.json", "benchmark-provenance.json", "BENCHMARK_REVIEW.md")',
            '("source-freeze.json", "benchmark-provenance-reviewed.json", "BENCHMARK_REVIEWED.md", "benchmark-editorial-audit.json", "fact_probes-reviewed.jsonl", "qa_probes-reviewed.jsonl")')
p.write_text(s)
print(json.dumps({"facts":len(facts),"qa":len(qas),"editorial_changes":len(audit),"judge_api_calls":0}))

