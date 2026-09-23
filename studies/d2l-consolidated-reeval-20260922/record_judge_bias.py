from pathlib import Path
import json,datetime,hashlib
R=Path('/home/likefallwind/code/llm-graph-benchmark'); study=R/'studies/d2l-consolidated-reeval-20260922';run=R/'outputs/d2l-baseline-only-m3-c6-20260922'
audit='''# 裁判开发偏差检查（2026-09-22）

用户指出：不得靠大量细粒度、针对已见案例的提示词规则使裁判过拟合。

## 已确认的风险

1. 在查看真实 pilot 判定后，新增了关于跨框架 API、概念与实现、混杂节点和事件实例的身份细则。即使这些规则可解释，也属于使用已见样本调整裁判，不能把同批样本的通过当泛化证据。
2. 早期开发集中一条别名题在看到判定后被替换为无歧义题。旧题和分歧已保留，但后续“全部通过”不能解释为独立校准准确率。
3. 原任务范围曾被扩大到四方法，并改变了裁判、上下文与统计口径；这不是只替换复现产物的受控比较。已经收窄，不应悄悄重评我们的方法来追求整齐。
4. JSON 围栏、完全相同的对象编码等格式修复属于执行修复，和语义规则改动分别记录。它们也不能证明模型语义判定准确。

## 当前处置

- 本轮 baseline-only 与 v6 均无启动记录，正式补测尚未启动。
- baseline-only 中准备的细则版本撤出正式执行；RUN_HOLD.json 阻止误启动。历史文件和试判原样保留，不覆盖。
- 已见真实样本和已调试开发题统一标为开发/诊断数据，不当作独立验证集。
- 不按方法名称、预期排名或分数修改规则；GraphRAG 得分高本身不是判错证据。
- 本次补测仅针对复现修正后仍缺结果的基线指标。我们的方法、已用正确产物评测的结果原样保留。
- 简化裁判草案见 GENERAL_RUBRIC_DRAFT.md；尚未执行，不用既有裁判输出当作该草案结果。
- 下一步应先确认原通用 rubric 可沿用的范围；确需修复的评估问题与复现修正分开记录。任何新版本须在判分前冻结，独立留出样本不能同时用于修改提示和证明可靠性。同一模型自评不等于人工金标准。
'''
(study/'JUDGE_BIAS_AUDIT.md').write_text(audit)
(study/'GENERAL_RUBRIC_DRAFT.md').write_text('''# 通用裁判标准草案（未执行）

共享规则：只根据给出的证据判断待评内容，不使用方法身份或预期排名。允许等价表述。区分有证据支持、被证据反驳、证据不足，简述理由并引用真实证据编号。输入中的候选描述和参考答案不是证明自身正确的证据。

每项指标仅保留必要定义：

| 指标 | 判定问题 |
|---|---|
| 实体类型 | 提交的类型是否与实体在来源中的含义兼容？ |
| 实体描述 | 提交描述的全部实质内容是否得到来源支持？ |
| 别名同一性 | 别名与规范名在来源语境中是否指向同一实体？ |
| 实体拆分 | 来源是否支持这两个节点表示不同实体或不同义项？ |
| Book QA | 给定图谱候选是否足以支撑问题所需的完整答案？ |

不加入方法名、真实测试案例、框架/API特例、事件特例或期望分数。字段有效性和 JSON 格式由程序检查，不堆进语义规则。

本草案不自动替换历史协议；必须先明确其与原通用 rubric 的差别，分母、输入上下文、抽样和检索范围不得在补测中暗改。验证数据必须与已用于开发的数据区分。裁判版本冻结后不根据各方法得分改提示。
''')
hold={'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reason':'Case-adaptive identity rules withdrawn after user raised judge-overfitting concern. No formal evaluation was launched. Freeze general rubric and resolve protocol comparability before running.','requires_user_permission':False,'superseded_evaluator_sha256':hashlib.sha256((run/'evaluate.py').read_bytes()).hexdigest()};(run/'RUN_HOLD.json').write_text(json.dumps(hold,ensure_ascii=False,indent=2)+'\n')
p=run/'driver.py';s=p.read_text();s=s.replace('def launch(run,phase):\n','def launch(run,phase):\n if (run/\'RUN_HOLD.json\').exists():raise RuntimeError(\'Evaluator withdrawn: see RUN_HOLD.json and JUDGE_BIAS_AUDIT.md\')\n');p.write_text(s)
(study/'RUN.md').write_text('# 当前状态\n\n正式补测尚未启动。此前针对真实案例补充的裁判细则已撤出执行，详见 JUDGE_BIAS_AUDIT.md。补测范围保持 baseline-only/SCOPE.json 的用户限定；先解决裁判过拟合与新旧协议可比性，不能把已见 pilot 当独立验证。无新增 API 调用。\n')
print('Recorded development bias; case-adaptive prepared run blocked from accidental launch; no API calls.')
