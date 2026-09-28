# 统一评测工作流

当前协议：[PROTOCOL.md](PROTOCOL.md)。实现不依赖 studies 或 outputs 下的脚本。
运行环境：Linux / WSL，Python 3.11+；仅使用标准库。评测无需额外 Agent 或 Skill。

## 配置

路径相对于配置文件所在目录解释：

```json
{
  "benchmark": "/path/to/benchmark.json",
  "submissions": [
    {"path": "/path/to/submission.json", "name": "方法A"}
  ],
  "seed": 20260923,
  "samples": {"entities": 100, "assertions": 200, "aliases": 30},
  "workers": 6
}
```

没有原生描述时用 definition="" 并设置 metadata.definition_available=false；没有类型时用 types=[]。
当前自动裁判要求每个原文单元包含 text，纯图片需要先提供 OCR/转写文本。

submissions 也可直接列字符串路径。system.id 必须唯一；所有图谱使用同一 benchmark。
samples 是每文档上限，总体不足时取全部，禁止按得分或字段有无补换样本。workers 只能为1至6。
实体正确性、引用支持、类型与描述复用本轮同一实体样本；关系正确性与粒度复用同一断言样本。
别名从非平凡别名分配中抽样。事实探针不额外抽样。Book QA已移除，不生成相关任务或发出相关API调用。
实体拆分已退役，旧配置里的 samples.splits 会被拒绝；语义重复在主运行完成后作为单独阶段评测，见下文。

可选 submission 参数：

- structure_path：用于结构统计的完整图；path 是语义评测子集。必须同时提供 scope_note，且子集必须是完整图的未修改子集。
- construction_usage：独立 JSON 文件，包含 input_tokens、output_tokens 和 source（原始日志或冻结汇总的位置说明）；计数为非负整数或 null。未提供时使用完整图 submission.runtime，缺失保持 N/A。
- name：报告显示名；scope_note：报告中的输入范围说明。均不发送给裁判。

构图用量文件示例：
```json
{"input_tokens": 2500000, "output_tokens": 750000, "source": "construction-log.json"}
```

模型固定 MiniMax-M3，temperature=0。配置不接受额外指标、替代模型或任意自定义提示，以免同一版本的评测口径漂移。

## 运行

```bash
# 本地准备，绝不调用 API
llm-graph-benchmark workflow prepare --config workflow.json --run outputs/run-001

# 前台执行，或使用 launch 脱离当前会话后台执行
llm-graph-benchmark workflow run --run outputs/run-001
llm-graph-benchmark workflow launch --run outputs/run-001

llm-graph-benchmark workflow status --run outputs/run-001
llm-graph-benchmark workflow report --run outputs/run-001

# 中断后继续：成功结果不变，默认只执行尚未评的任务
llm-graph-benchmark workflow launch --run outputs/run-001

# 显式补技术失败：归档失败记录，只重试失败和 provider_error 项
llm-graph-benchmark workflow launch --run outputs/run-001 --retry-failed
```

只选择 run/launch 其中一种执行方式，同一目录有进程锁，不能重复启动。
run / launch 从 MINIMAX_API_KEY 环境变量读取密钥；prepare/status/report 不读取密钥。
后台日志在 worker.log；正常关闭终端或结束聊天不停止已分离的工作进程，但关闭 WSL/系统会中断进程。

每个请求最多3次技术尝试；成功的 pass/fail/uncertain 都缓存，不为了改变分数重跑。
provider 认证/余额错误停止派发；修复环境后显式 --retry-failed 恢复。
输入超350,000 UTF-8字节标记 unassessed_size，内容审核跳过标记 skipped_input_moderation，均不截断也不转为 fail；
这两类不会被 --retry-failed 自动反复尝试。原输入或规则需要改变时使用新版本和新运行目录。

退出码：0成功，2配置/校验错误，3存在未评，4供应商错误。
launch 只等待启动确认；后台的最终结果以 status 为准，不把“已启动”当作“已完成”。

## 语义重复阶段

主运行完成后，从它派生语义重复阶段，沿用主运行的实体样本。叫法与初筛由评测方离线写成 JSON 并冻结，只有终判调用裁判。

```bash
# 1. 导出盲化目标表（无方法、文档、实体 ID），本地运行
llm-graph-benchmark workflow semantic-targets --parent outputs/run-001 --out targets-sheet.json
# 2. 评测方写 expansions.json：{目标key: [等价叫法, ...]}，每个目标都要有，可为空列表
# 3. 在实体名和别名中检索前30个候选，输出盲化初筛表
llm-graph-benchmark workflow semantic-candidates --parent outputs/run-001 --expansions expansions.json --out screening-sheet.json
# 4. 评测方写 screening.json：{目标key: [候选key, ...]}，宽松保留可能同指的候选
# 5. 冻结逐对终判任务，随后与主运行一样 run/launch/status/report
llm-graph-benchmark workflow semantic-prepare --parent outputs/run-001 --expansions expansions.json --screening screening.json --run outputs/run-001-semantic
llm-graph-benchmark workflow launch --run outputs/run-001-semantic
# 6. 合成一张总表：主运行其余指标 + 语义重复（退役指标不列入）
llm-graph-benchmark workflow combine --parent outputs/run-001 --stage outputs/run-001-semantic --out outputs/run-001-combined
```

semantic-prepare 会用 expansions.json 重算候选，校验初筛只包含对应目标的候选，并核对主运行的配置、benchmark、提交和冻结文件哈希。
引用原文超过170KB的实体不进入样本和候选池，报告列出排除数。

## 并发与恢复

同一 OS 用户的所有工作流运行通过 ~/.cache/llm-graph-benchmark/minimax-m3-slots 的文件锁共享6个 HTTP槽；
每个运行还受 workers 限制，重试与断言第二步核对均占槽。此锁不约束旧独立 study 或其他程序。
各运行的供应商错误状态独立；一次错误不会永久阻塞其他工作流目录。

prepare 冻结原文/提交哈希、任务、私有映射、提示、样本、检索和执行代码哈希。
run/status/report 检查冻结文件和代码；程序更新后不能静默用新代码续跑旧任务，需要恢复当时代码或另建运行。
成功结果还绑定任务内容哈希及结果哈希。原始输入被迁移后，冻结任务仍可继续运行；报告保留原始路径和哈希供追溯。

## 产物

|文件|作用|
|---|---|
|REPORT.md / comparison.csv|当前全部选定指标的对照表|
|summary.json|分子、分母、实体宏平均、语义标签计数、技术状态、构图统计和评测用量|
|case-results.json|逐任务结果、对象映射、类型标签与整段描述判定、判定理由|
|tasks.json / private-key.json|固定任务与方法/文档/对象映射；只把白名单 payload 发送模型|
|sampling.json|抽样实体/断言 ID 与缺字段项|
|manifest.json / prompts.json|版本、输入/代码哈希、调用数量估计与冻结提示|
|systems.json / structure.json|方法范围、完整检索结果与选定结构统计|
|api/requests / api/response-cache|原请求、原响应、尝试与缓存；不保存认证头|
|state.json / progress.json / worker.log|运行状态和后台日志|

planned_calls_without_retries 是每任务调用数加断言第二步数，属于计划参考，不是精确费用；
超长跳过、缓存复用及失败会影响实际用量。评测 Token 在 evaluation_usage 中，与构图 million Token 分开。
evaluation_usage 中 peak_http 等共享槽统计覆盖同一 OS 用户的工作流运行，request_attempts 和 Token 只计本运行。

## 验证

```bash
pytest
```

测试覆盖合成输入全流程、宏平均与缺字段、失败恢复、类型文本绑定、整段描述三类判定与分母、跨文档 ID、
真实传输边界（模拟 HTTP）、跨进程6槽和后台启动。测试不访问真实 API，不产生模型费用。
旧历史报告保留原样，新工作流的正确性检查不构成对历史语义分数的再次确认。

描述采用整段单次判定，不再要求逐字分段。历史分段评测保留原结果；新口径另建运行目录，保留原样本、描述和证据，不能将旧分段分数直接转换为新结果。
