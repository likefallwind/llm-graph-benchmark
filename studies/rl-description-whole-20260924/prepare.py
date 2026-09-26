"""Prepare the fixed RL description-only trial; no API calls."""
from pathlib import Path
import json
import shlex
import shutil

from llm_graph_benchmark.workflow.description_reassessment import prepare_description_reassessment
from llm_graph_benchmark.workflow.preparation import sha, verify
from llm_graph_benchmark.workflow.transport import write


ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "outputs/rl-description-whole-m3-c6-20260924"
archives = [ROOT / "results/sutton-barto-20260923/archive.json"] + [
    ROOT / f"results/sutton-barto-baselines-20260923/{name}/archive.json"
    for name in ("graphrag", "autoschemakg", "kggen")]
parents = [json.loads(p.read_text())["run"] for p in archives]
result = prepare_description_reassessment(parents, RUN, workers=6)
shutil.copytree(ROOT / "src/llm_graph_benchmark", RUN / "source/llm_graph_benchmark",
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
q = shlex.quote
wrapper = f"""#!/usr/bin/env bash
set -u
cd {q(str(ROOT))}
exec >>{q(str(RUN / 'worker.log'))} 2>&1
trap 'rc=$?; echo "$rc" > {q(str(RUN / '.exit'))}; if [ "$rc" -eq 0 ]; then date -u +%FT%TZ > {q(str(RUN / '.finished'))}; fi' EXIT
date -u +%FT%TZ > {q(str(RUN / '.started'))}
export PYTHONPATH={q(str(RUN / 'source'))}
export PYTHONDONTWRITEBYTECODE=1
{q(str(ROOT / '.venv/bin/python'))} -m llm_graph_benchmark workflow run --run {q(str(RUN))}
exit $?
"""
(RUN / "background.sh").write_text(wrapper)
manifest = json.loads((RUN / "manifest.json").read_text())
manifest["frozen_files"]["background.sh"] = sha(RUN / "background.sh")
write(RUN / "manifest.json", manifest)
verify(RUN)
print(json.dumps(result, ensure_ascii=False))
