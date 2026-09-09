"""Authored rule checks, not independent human gold or held-out evaluation."""
from __future__ import annotations
import argparse
import json
from pathlib import Path


def cases():
    rows = []
    def add(source, subject, predicate, obj, text, label, category, scope='', polarity='positive'):
        rows.append(dict(case_id=f'check-{len(rows)+1:02d}', category=category,
            source=source, content=dict(subject=subject,predicate=predicate,object=obj,text=text,
                                       scope=scope,polarity=polarity), expected_label=label))
    def pair(source, good, bad, category):
        for triple, text, label in ((good[:3],good[3],'pass'),(bad[:3],bad[3],'fail')):
            add(source,*triple,text,label,category)
    pair('模块甲支持导出，也支持打印。',
         ('模块甲','支持','打印','模块甲支持打印。'),
         ('模块甲','仅支持','打印','模块甲仅支持打印。'),'independent_conjunct')
    pair('只有温度低于零度时，装置甲才启动。温度不低于零度时不启动。',
         ('装置甲','启动条件','温度低于零度','装置甲仅在温度低于零度时启动。'),
         ('装置甲','启动','运行','装置甲在任意温度下都启动。'),'necessary_condition')
    pair('该实验表明药剂甲不抑制酶乙。',
         ('药剂甲','不抑制','酶乙','该实验中药剂甲不抑制酶乙。'),
         ('药剂甲','抑制','酶乙','该实验中药剂甲抑制酶乙。'),'negation')
    pair('在试验中，处理甲可能提高指标乙，但并非每次都提高。',
         ('处理甲','可能提高','指标乙','在试验中处理甲可能提高指标乙。'),
         ('处理甲','必然提高','指标乙','在试验中处理甲必然提高指标乙。'),'modality')
    pair('在该流程中，泵甲给容器乙供水。',
         ('泵甲','供水给','容器乙','在该流程中泵甲给容器乙供水。'),
         ('容器乙','供水给','泵甲','在该流程中容器乙给泵甲供水。'),'direction')
    pair('观测中指标甲与指标乙正相关；没有证据表明任何一方引起另一方。',
         ('指标甲','正相关于','指标乙','观测中指标甲与指标乙正相关。'),
         ('指标甲','导致','指标乙','指标甲导致指标乙升高。'),'relation_strength')
    pair('本次测试中，十台设备里恰有两台出现故障。',
         ('本次测试的设备','故障数量','两台','本次测试的十台设备中两台故障。'),
         ('本次测试的设备','故障数量','十台','本次测试的十台设备全部故障。'),'quantity')
    pair('处理甲降低了模型乙的训练时间。',
         ('处理甲','降低','模型乙的训练时间','处理甲降低模型乙的训练时间。'),
         ('处理甲','降低','模型乙','处理甲降低模型乙。'),'endpoint_role')
    pair('部件甲包含在装置乙中。',
         ('装置乙','包含','部件甲','部件甲包含在装置乙中。'),
         ('部件甲','包含','装置乙','部件甲包含在装置乙中。'),'text_cannot_repair_edge')
    pair('记录明确指出：关闭阀门甲后，打开阀门乙。',
         ('关闭阀门甲','先于','打开阀门乙','关闭阀门甲先于打开阀门乙。'),
         ('打开阀门乙','先于','关闭阀门甲','打开阀门乙先于关闭阀门甲。'),'event_nodes')
    pair('在本实验中，改动甲提高速度，却降低准确率。',
         ('改动甲','提高','速度','在本实验中改动甲提高速度。'),
         ('改动甲','提高','准确率','在本实验中改动甲提高准确率。'),'local_benefit')
    pair('工具甲用于校验文件。',
         ('工具甲','用于','校验文件','工具甲用于用于校验文件。'),
         ('工具甲','用于','删除文件','工具甲用于删除文件。'),'surface_vs_semantics')
    add('', '甲','包含','乙','甲包含乙。','uncertain','missing_evidence')
    add('设备甲和设备乙并排放置。记录随后只说“它发生故障”，没有说明指哪台设备。',
        '设备甲','发生','故障','设备甲发生故障。','uncertain','ambiguous_reference')
    return rows


def assess(keys, judgments, judge_id):
    by_id={r['task_id']:r for r in keys}
    if not by_id or len(by_id)!=len(keys):
        raise ValueError('calibration keys must be nonempty and unique')
    votes={}
    for row in judgments:
        if row['task_id'] not in by_id: raise ValueError('unknown task')
        if row['judge_id']!=judge_id: continue
        if row['task_id'] in votes: raise ValueError('duplicate judgment')
        if row['label'] not in {'pass','fail','uncertain','error'}: raise ValueError('invalid label')
        votes[row['task_id']]=row['label']
    mismatches=[dict(task_id=tid,expected=k['expected_label'],actual=votes.get(tid),
                     category=k['category']) for tid,k in by_id.items()
                if votes.get(tid)!=k['expected_label']]
    errors=sum(v=='error' for v in votes.values())
    missing=len(by_id)-len(votes)
    return dict(status='incomplete' if errors or missing else 'complete',
        rule_check_gate='pass' if not mismatches else 'not_passed',
        expected=len(by_id),matched=len(by_id)-len(mismatches),errors=errors,missing=missing,
        mismatches=mismatches,judge_id=judge_id,
        independent_calibration=False, formal_rerun_ready=False,
        interpretation='Authored rule checks only. Passing does not establish natural-sample accuracy; independent held-out review is still required.')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--key',type=Path,required=True)
    parser.add_argument('--judgments',type=Path,required=True)
    parser.add_argument('--judge-id',required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    read=lambda p:[json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    result=assess(read(args.key),read(args.judgments),args.judge_id)
    with args.out.open('x') as stream: json.dump(result,stream,ensure_ascii=False,indent=2)
    print(json.dumps(result,ensure_ascii=False))
