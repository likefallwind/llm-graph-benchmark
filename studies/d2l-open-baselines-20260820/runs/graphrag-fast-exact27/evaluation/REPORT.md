# LLM Graph Benchmark Report

结构规模不是质量分数；Entity 与 Assertion 的裁判结果分别报告。

| System | Entities | Assertions | Entity evidence | Assertion evidence | Isolated rate | Cost (USD) |
|---|---:|---:|---:|---:|---:|---:|
| graphrag-fast-default | 8 | 1 | 0.875 | 1.000 | 0.750 | 0.000 |

## Blind judgments

`uncertain` 和投票平局不进入 pass rate 分母。

| System | Dimension | Pass | Fail | Uncertain | Unjudged | Pass rate | 95% CI |
|---|---|---:|---:|---:|---:|---:|---:|
| graphrag-fast-default | assertion_grounding | 1 | 0 | 0 | 0 | 1.000 | [0.207, 1.000] |
| graphrag-fast-default | book_qa | 0 | 1 | 0 | 0 | 0.000 | [0.000, 0.793] |
| graphrag-fast-default | entity_admission | 4 | 4 | 0 | 0 | 0.500 | [0.215, 0.785] |
| graphrag-fast-default | entity_definition_grounding | 0 | 8 | 0 | 0 | 0.000 | [0.000, 0.324] |
| graphrag-fast-default | entity_typing | 0 | 8 | 0 | 0 | 0.000 | [0.000, 0.324] |
| graphrag-fast-default | fact_recovery | 0 | 1 | 0 | 0 | 0.000 | [0.000, 0.793] |
