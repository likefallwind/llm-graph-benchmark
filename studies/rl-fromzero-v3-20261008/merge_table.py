"""Put the from-zero graph's combined results beside the frozen RL comparison table.

Reads only finished report files; no API calls. Baseline columns come unchanged from
results/sutton-barto-semantic-duplicate-20260928 (same benchmark, seed, prompts).
"""
import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
NEW = ROOT / "outputs/rl-fromzero-v3-20261008-combined/comparison.csv"
OLD = ROOT / "results/sutton-barto-semantic-duplicate-20260928/comparison.csv"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "outputs/rl-fromzero-v3-20261008-combined/four-way.csv"
OLD_OURS = "我们的方法（强化学习）"


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        table = list(csv.reader(f))
    return table[0], {r[0]: r[1:] for r in table[1:]}, [r[0] for r in table[1:]]


new_head, new, order = rows(NEW)
old_head, old, old_order = rows(OLD)
assert len(new_head) == 2, new_head
if set(order) != set(old_order):
    raise ValueError(f"Metric rows differ: {set(order) ^ set(old_order)}")
head = ["指标", new_head[1], OLD_OURS + "·跨书增量（参考）"] + old_head[2:]
assert old_head[1] == OLD_OURS
with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(head)
    for metric in old_order:
        writer.writerow([metric, new[metric][0]] + old[metric])
md = OUT.with_suffix(".md")
lines = ["|" + "|".join(head) + "|", "|---|" + "---:|" * (len(head) - 1)]
lines += ["|" + "|".join([m, new[m][0]] + old[m]) + "|" for m in old_order]
md.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(OUT, md)
