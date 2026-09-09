# D2L assertion-quality v2

协议见 ../../docs/QUALITY_PROTOCOL_V2.md。复用原有五系统各 200 条断言；旧事实恢复仅作为辅助诊断。

```bash
PYTHONPATH=src python studies/d2l-quality-v2-20260908/prepare.py \
  --previous outputs/d2l-quality-m3-official-c4-20260907-174524 \
  --out outputs/d2l-quality-v2-20260908
```

输出 tasks/key（1000 条）、checks-tasks/checks-key（26 条合成规则检查）、review-tasks/review-key
（按系统和历史标签分层的开发复核集）。manifest 记录版本、输入/输出哈希及未完成门槛。
公开 tasks 不含系统、旧标签或合成样例预期答案，私有 key 不得发送给裁判。
所有输出留在忽略的 outputs/，不提交教材证据。

可使用上一轮 studies/d2l-quality-protocol-20260907/judge.py，显式指定
`--workers 4 --judge-id minimax-m3-official-quality-v2-t0-8192`；只发送 checks-tasks.jsonl
运行最小规则检查。1000 条任务尚需独立留出复核，不能以合成样例通过代替。

规则检查完成后：

```bash
python studies/d2l-quality-v2-20260908/calibration.py \
  --key outputs/d2l-quality-v2-20260908/checks-key.jsonl \
  --judgments /path/to/check-run/judgments.jsonl \
  --judge-id minimax-m3-official-quality-v2-t0-8192 \
  --out /path/to/check-run/rule-check-report.json
```

脚本拒绝覆盖已有结果。API 错误与有效但不符合预期的判断区分；后者不能挑选重试直到通过。

实际执行结果与分歧说明见 [STATUS.md](STATUS.md)：规则检查已完成，25/26 与预期一致，尚未通过门槛。
