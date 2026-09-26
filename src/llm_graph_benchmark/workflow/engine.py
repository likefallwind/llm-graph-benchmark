"""Execute frozen tasks with bounded concurrency, persistence, and background mode."""
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import contextlib
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

from ..bundle import canonical_hash
from . import alignment, protocol, transport
from .preparation import read, verify, MAX_INPUT_BYTES
from .reporting import report, result_for


def slots_path():
    # All workflow runs under this OS user share these six locks.
    return Path.home() / ".cache" / "llm-graph-benchmark" / "minimax-m3-slots"


@contextlib.contextmanager
def run_lock(run, name=".run.lock"):
    with (Path(run) / name).open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("This run already has an active worker/launcher") from None
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def active(run):
    try:
        with run_lock(run):
            return False
    except ValueError:
        return True


def status(run):
    run = Path(run).resolve()
    verify(run)
    tasks = read(run / "tasks.json")
    from collections import Counter
    counts = Counter(result_for(run, t)["status"] for t in tasks)
    state = read(run / "state.json") if (run / "state.json").exists() else {"phase": "prepared"}
    running = active(run)
    phase = state["phase"]
    if phase == "running" and not running:
        phase = "interrupted"
    return {"run": str(run), "phase": phase, "active": running,
            "done": counts["done"], "total": len(tasks), "statuses": dict(counts),
            "complete": counts["done"] == len(tasks)}


def execute(run, *, retry_failed=False, client_factory=None):
    run = Path(run).resolve()
    manifest = verify(run)
    with run_lock(run):
        tasks = read(run / "tasks.json")
        queue = []
        for task in tasks:
            r = result_for(run, task)
            if r["status"] == "pending":
                queue.append(task)
            elif retry_failed and r["status"] in {"failed", "terminal_provider_error"}:
                path = run / "results" / (task["id"] + ".json")
                archive = run / "technical-retries" / (str(time.time_ns()) + "-" + path.name)
                archive.parent.mkdir(parents=True, exist_ok=True)
                path.replace(archive)
                queue.append(task)
        terminal_path = run / "api" / "terminal-error.json"
        if terminal_path.exists() and retry_failed:
            terminal_path.replace(terminal_path.with_name("terminal-error-" + uuid.uuid4().hex + ".json"))
        started = time.time()
        transport.write(run / "state.json", {"phase": "running", "pid": os.getpid(), "started_at": started})
        try:
            if not queue:
                summary = report(run)
                phase = "complete" if summary["complete"] else "incomplete"
                return 0 if summary["complete"] else 3
            factory = client_factory or transport.Client
            client = factory(run / "api", slots_path(), concurrency=manifest["workers"])

            def one(task):
                record = {"task_id": task["id"], "task_hash": canonical_hash(task),
                          "started_at": time.time()}
                try:
                    if task["oversized"]:
                        record["status"] = "unassessed_size"
                    else:
                        raw = client.complete(task["messages"], max_tokens=task["max_tokens"],
                                              validator=lambda response: protocol.parse(response, task))
                        value = protocol.parse(raw, task)
                        if task["metric"] == "assertion_correctness":
                            followup = alignment.messages(task, value)
                            if len(json.dumps(followup, ensure_ascii=False).encode()) > MAX_INPUT_BYTES:
                                record["status"] = "unassessed_size"
                            else:
                                checked = client.complete(followup, max_tokens=8192,
                                    validator=lambda response: alignment.parse(response, len(value["claims"])))
                                value = alignment.combine(value, alignment.parse(checked, len(value["claims"])))
                        if "status" not in record:
                            record.update(status="done", value=value, value_hash=canonical_hash(value))
                except transport.TerminalProviderError:
                    record["status"] = "terminal_provider_error"
                except transport.ContentRejected:
                    record["status"] = "skipped_input_moderation"
                except Exception as error:
                    # Do not persist exception messages, which can contain credentials.
                    record.update(status="failed", error_type=type(error).__name__)
                record["finished_at"] = time.time()
                transport.write(run / "results" / (task["id"] + ".json"), record)
                return record

            terminal, processed, last_report = False, 0, time.monotonic()
            pending_tasks = iter(queue)
            with ThreadPoolExecutor(max_workers=manifest["workers"]) as pool:
                futures = {}

                def fill():
                    while len(futures) < manifest["workers"] and not terminal:
                        task = next(pending_tasks, None)
                        if task is None:
                            break
                        futures[pool.submit(one, task)] = task["id"]

                fill()
                while futures:
                    done, _ = wait(futures, return_when=FIRST_COMPLETED)
                    for future in done:
                        futures.pop(future)
                        value = future.result()
                        terminal |= value["status"] == "terminal_provider_error"
                        processed += 1
                    transport.write(run / "progress.json", {
                        "processed_this_invocation": processed, "queued_this_invocation": len(queue),
                        "terminal_provider_error": terminal, "updated_at": time.time(),
                    })
                    if time.monotonic() - last_report > 30:
                        report(run)
                        last_report = time.monotonic()
                    fill()
            summary = report(run)
            phase = "complete" if summary["complete"] else "provider_error" if terminal else "incomplete"
            return 0 if summary["complete"] else 4 if terminal else 3
        except BaseException as error:
            phase = "interrupted" if isinstance(error, (KeyboardInterrupt, SystemExit)) else "startup_error"
            transport.write(run / "error.json", {"error_type": type(error).__name__, "at": time.time()})
            raise
        finally:
            transport.write(run / "state.json", {
                "phase": locals().get("phase", "interrupted"), "pid": os.getpid(),
                "started_at": started, "finished_at": time.time(),
            })


def launch(run, *, retry_failed=False):
    run = Path(run).resolve()
    verify(run)
    # Validate the inherited environment before detaching; never print the secret.
    transport.load_secret()
    with run_lock(run, ".launch.lock"):
        if active(run):
            raise ValueError("This run already has an active worker")
        command = [sys.executable, "-m", "llm_graph_benchmark", "workflow", "run", "--run", str(run)]
        if retry_failed:
            command.append("--retry-failed")
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        # Also supports running from source without an editable install.
        source = str(Path(__file__).resolve().parents[2])
        env["PYTHONPATH"] = source + os.pathsep + env.get("PYTHONPATH", "")
        with (run / "worker.log").open("ab") as log:
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log,
                                       stderr=subprocess.STDOUT, start_new_session=True, env=env)
        transport.write(run / "launch.json", {"pid": process.pid, "started_at": time.time()})
        # Wait only for the worker's startup acknowledgement, not for judging.
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if process.poll() is not None:
                return {**status(run), "worker_exit_code": process.returncode}
            state = read(run / "state.json") if (run / "state.json").exists() else {}
            if state.get("pid") == process.pid and state.get("phase") == "running":
                return {**status(run), "pid": process.pid}
            time.sleep(0.05)
        return {"run": str(run), "phase": "starting", "pid": process.pid}

