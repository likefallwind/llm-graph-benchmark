# D2L 粗粒度可靠性补评

现有结果已经显示本方法单条断言通过率较高，本研究用于补足引用充分性和小样本不确定性，不重新构图，不保证本方法获胜。协议见 [RELIABILITY_PROTOCOL.md](../../docs/RELIABILITY_PROTOCOL.md)。

当前状态见 [RUN.md](RUN.md)：两轮MiniMax-M3开发检查均停止，存在重复的方向误判。用户随后确认继续发送，已启动显式探索性后台运行，结果将保留并突出裁判限制；尚未获得可靠的新比较结论。

主问题只有内容正确性和原提交引用充分性；实体只评名称所指，Assertion整条评判。四方法各100实体、200断言，2400次独立维度调用。新样本排除可识别的历史已评项目，具体总体和排除材料在 sampling.json 中披露；不是未见书籍实验。

先准备并冻结：

```bash
.venv/bin/python studies/d2l-reliability-20260920/evaluate.py prepare \
  --run outputs/d2l-reliability-m3-c6-YYYYMMDDTHHMMSS
```

后台运行冻结代码（全部方法与重试共用6个HTTP槽位）：

```bash
.venv/bin/python outputs/d2l-reliability-m3-c6-YYYYMMDDTHHMMSS/background.py launch \
  --run outputs/d2l-reliability-m3-c6-YYYYMMDDTHHMMSS
```

入口需要继承 MINIMAX_API_KEY。外层启动脚本负责 .started / run.log / .exit / 成功时 .finished；脚本锁拒绝同一运行的重复进程。判定逐条落盘，已有记录不覆盖；运行冻结代码可以接续未处理队列，不会重新抽样或重试已落盘的有效语义标签。技术失败记录也保留，不能以后台结束代替判断完整。

- `REPORT.md`：粗粒度主表、完整分母与限制。
- `summary.json` / `progress.json`：判定数量、状态和评测调用成本。
- `sampling.json` / `private-key.json`：随机抽样、排除与原生数据审计。
- `legacy-coverage.json`：旧48探针结果及来源，非本轮新结果。
- `api/` / `request-slots/`：原始响应、所有重试与实际HTTP并发证据。
- `calibration-report.json`：通用开发检查，非独立人工金标。

退出0表示主评测每题都有有效标签；2表示开发检查需复核；3表示存在未判定项；4表示提供方终止错误。缺失不会被当成语义错误或从分母中消失。
