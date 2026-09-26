"""Launch the authorized second-book evaluation detached from the terminal."""
from pathlib import Path
import importlib.util
import json
import os
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("rl_pipeline", HERE / "run_pipeline.py")
pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)
assert os.environ.get("MINIMAX_API_KEY"), "MINIMAX_API_KEY must be inherited"
pipeline.engine.status(pipeline.RUN)
if pipeline.engine.active(pipeline.RUN):
    raise SystemExit("Evaluation already running")
with (pipeline.OUT / "pipeline-evaluation.log").open("ab") as log:
    child = subprocess.Popen(
        [sys.executable, str(HERE / "run_pipeline.py"), *(["--retry-failed"] if "--retry-failed" in sys.argv else [])],
        cwd=pipeline.ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
        start_new_session=True,
    )
pipeline.transport.write(pipeline.OUT / "evaluation-launch.json",
                         {"pid": child.pid, "started_at": time.time(), "run": str(pipeline.RUN),
                          "model": "MiniMax-M3", "max_http_concurrency": 6})
print(json.dumps({"pid": child.pid, "run": str(pipeline.RUN),
                  "model": "MiniMax-M3", "max_http_concurrency": 6}))

