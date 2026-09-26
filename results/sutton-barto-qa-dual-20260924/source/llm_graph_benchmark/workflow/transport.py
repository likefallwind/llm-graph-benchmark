"""Restartable official MiniMax transport with a shared six-request ceiling.

Only MINIMAX_API_KEY from the inherited environment supplies credentials. The
validator receives the provider response and must raise ValueError for an invalid
answer. Valid semantic labels (including negative labels) are cached unchanged.
"""
from __future__ import annotations

import contextlib
import fcntl
import hashlib
import http.client
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request
import uuid

MODEL = "MiniMax-M3"
ENDPOINT = "https://api.minimaxi.com/v1/text/chatcompletion_v2"
REQUEST_CONCURRENCY = 6
MAX_ATTEMPTS = 3
HTTP_TIMEOUT = 180
TERMINAL_CODES = {1004, 1008, 2013, 2049, 2067}
MODERATION_CODES = {1026, 1027}


class TerminalProviderError(RuntimeError):
    """Stop dispatching work for this run; intervention is required."""


class ContentRejected(RuntimeError):
    def __init__(self, record=None):
        self.record = record or {}
        super().__init__("Provider content moderation; recorded as skipped")


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_secret():
    value = os.environ.get("MINIMAX_API_KEY", "").strip()
    if value.lower().startswith("bearer "):
        value = value[7:].strip()
    if not value:
        raise TerminalProviderError("Inherited MINIMAX_API_KEY is unavailable")
    return value


@contextlib.contextmanager
def _lock(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _check_terminal(root):
    if (Path(root) / "terminal-error.json").exists():
        raise TerminalProviderError("Shared run stopped on a terminal provider failure")


@contextlib.contextmanager
def request_slot(root, limit=REQUEST_CONCURRENCY):
    """flock applies across threads, Client instances, and OS processes."""
    if not 1 <= limit <= REQUEST_CONCURRENCY:
        raise ValueError("concurrency must be in 1..6")
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    handle = None
    while handle is None:
        _check_terminal(root)
        for index in range(limit):
            candidate = (root / f"slot-{index}.lock").open("a")
            try:
                fcntl.flock(candidate, fcntl.LOCK_EX | fcntl.LOCK_NB)
                handle = candidate
                break
            except BlockingIOError:
                candidate.close()
        if handle is None:
            time.sleep(0.02)
    try:
        _check_terminal(root)
        yield
    finally:
        fcntl.flock(handle, fcntl.LOCK_UN)
        handle.close()


def _http_event(root, token, entering):
    """Record measured transport entry/exit under a cross-process audit lock."""
    root = Path(root)
    with _lock(root / "http-audit.lock"):
        path = root / "http-progress.json"
        state = read(path) if path.exists() else {
            "active": {}, "peak_http": 0, "http_attempts": 0,
            "abandoned_attempts": 0,
        }
        # A killed process cannot issue more HTTP calls. Clear its stale entry
        # when another process resumes; retain the historical peak and attempts.
        for old_token, old in list(state["active"].items()):
            try:
                os.kill(old["pid"], 0)
            except ProcessLookupError:
                del state["active"][old_token]
                state["abandoned_attempts"] += 1
        now = time.time()
        if entering:
            state["active"][token] = {"pid": os.getpid(), "started_at": now}
            state["http_attempts"] += 1
            state["peak_http"] = max(state["peak_http"], len(state["active"]))
        else:
            state["active"].pop(token, None)
        state["active_http"] = len(state["active"])
        state["updated_at"] = now
        event = {"at": now, "token": token, "event": "start" if entering else "end",
                 "pid": os.getpid(), "active_http": state["active_http"]}
        with (root / "http-events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(canonical(event) + "\n")
        write(path, state)


def validate_response(response):
    if not isinstance(response, dict):
        raise ValueError("Provider response must be an object")
    base = response.get("base_resp")
    if not isinstance(base, dict) or "status_code" not in base:
        raise ValueError("Missing provider status code")
    code = base["status_code"]
    if code in MODERATION_CODES:
        raise ContentRejected({"provider_code": code})
    if code in TERMINAL_CODES:
        raise TerminalProviderError(f"MiniMax terminal provider code {code}")
    if code != 0 or response.get("error"):
        raise ValueError("Provider error response")
    if response.get("model") != MODEL:
        raise ValueError("Unexpected provider model")
    choices = response.get("choices")
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        raise ValueError("Expected one completion choice")
    if choices[0].get("finish_reason") != "stop":
        raise ValueError("Non-stop completion")
    message = choices[0].get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Empty final answer")
    return response


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Client:
    def __init__(self, run, slots, *, concurrency=6):
        self.run = Path(run)
        self.slots = Path(slots)
        if not 1 <= concurrency <= 6:
            raise ValueError("concurrency must be in 1..6")
        self.concurrency = concurrency
        self._secret = load_secret()

    def _terminal(self, error):
        with _lock(self.run / "terminal-error.lock"):
            path = self.run / "terminal-error.json"
            if not path.exists():
                write(path, {"error": str(error), "at": time.time()})

    def complete(self, messages, max_tokens=4096, validator=None):
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]
        if not isinstance(max_tokens, int) or max_tokens <= 0:
            raise ValueError("max_tokens must be a positive integer")
        payload = {"model": MODEL, "messages": [dict(m) for m in messages],
                   "temperature": 0.0, "max_tokens": max_tokens, "stream": False}
        # Never permit the inherited credential to reach request/cache artifacts,
        # including if a caller mistakenly includes it in a prompt.
        if self._secret in canonical(payload):
            raise ValueError("Credential found in request payload")
        fingerprint = digest(payload)
        self.run.mkdir(parents=True, exist_ok=True)
        with _lock(self.run / "cache-locks" / (fingerprint + ".lock")):
            return self._complete_locked(payload, fingerprint, validator)

    def _complete_locked(self, payload, fingerprint, validator):
        _check_terminal(self.run)
        skipped_path = self.run / "skipped-requests" / (fingerprint + ".json")
        cache_path = self.run / "response-cache" / (fingerprint + ".json")
        if skipped_path.exists():
            raise ContentRejected(read(skipped_path))
        if cache_path.exists():
            try:
                response = validate_response(read(cache_path))
                if validator is not None:
                    validator(response)
            except (ValueError, TypeError, KeyError):
                rejected = self.run / "rejected-response-cache" / (fingerprint + "-" + uuid.uuid4().hex + ".json")
                rejected.parent.mkdir(parents=True, exist_ok=True)
                cache_path.replace(rejected)
            else:
                return response

        request_id = uuid.uuid4().hex
        request_dir = self.run / "requests" / request_id
        write(request_dir / "request.json", payload)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        for attempt in range(1, MAX_ATTEMPTS + 1):
            _check_terminal(self.run)
            started = time.monotonic()
            record = {"started_at": time.time(), "attempt": attempt,
                      "endpoint": ENDPOINT, "payload_sha256": fingerprint,
                      "status": "error"}
            try:
                request = urllib.request.Request(
                    ENDPOINT, data=canonical(payload).encode(), method="POST",
                    headers={"Authorization": "Bearer " + self._secret,
                             "Content-Type": "application/json"})
                with request_slot(self.slots, self.concurrency):
                    _check_terminal(self.run)
                    token = request_id + ":" + str(attempt)
                    _http_event(self.slots, token, True)
                    record["request_started_at"] = time.time()
                    http_start = time.monotonic()
                    try:
                        try:
                            with opener.open(request, timeout=HTTP_TIMEOUT) as handle:
                                record["http_status"] = handle.status
                                body = handle.read().decode("utf-8", errors="replace")
                        except urllib.error.HTTPError as error:
                            record["http_status"] = error.code
                            body = error.read().decode("utf-8", errors="replace")
                    finally:
                        record["request_finished_at"] = time.time()
                        record["http_elapsed_seconds"] = time.monotonic() - http_start
                        _http_event(self.slots, token, False)
                record["raw_body"] = body.replace(self._secret, "[REDACTED]")
                try:
                    response = json.loads(record["raw_body"])
                except ValueError:
                    if record["http_status"] in (401, 403):
                        raise TerminalProviderError(f"MiniMax HTTP {record['http_status']}") from None
                    raise
                if isinstance(response, dict):
                    base = response.get("base_resp")
                    reported_usage = response.get("usage")
                    record.update(usage=reported_usage if isinstance(reported_usage, dict) else {},
                                  model=response.get("model"),
                                  provider_code=base.get("status_code") if isinstance(base, dict) else None)
                if record["http_status"] in (401, 403):
                    raise TerminalProviderError(f"MiniMax HTTP {record['http_status']}")
                validate_response(response)
                if record["http_status"] != 200:
                    raise ValueError("Non-success HTTP status")
                if validator is not None:
                    validator(response)
                record["status"] = "done"
                write(cache_path, response)
                return response
            except ContentRejected as error:
                skipped = {"status": "skipped_content_moderation", "request_id": request_id,
                           "payload_sha256": fingerprint, **error.record}
                record.update(status="skipped_content_moderation", error_type="ContentRejected")
                write(skipped_path, skipped)
                raise ContentRejected(skipped) from None
            except TerminalProviderError as error:
                record["error_type"] = "TerminalProviderError"
                self._terminal(error)
                raise
            except (ValueError, TypeError, KeyError, OSError, urllib.error.URLError,
                    http.client.HTTPException) as error:
                # Error text may contain URLs/headers. Only store its type.
                record["error_type"] = type(error).__name__
            finally:
                record["elapsed_seconds"] = time.monotonic() - started
                write(request_dir / f"attempt-{attempt}.json", record)
            if attempt < MAX_ATTEMPTS:
                time.sleep(2 ** attempt)
        raise RuntimeError(f"MiniMax call exhausted {MAX_ATTEMPTS} attempts; see requests/{request_id}")

    def usage_summary(self):
        return usage_summary(self.run, self.slots)


def usage_summary(run, slots=None):
    """Count actual attempts, including failed/invalid responses and retries."""
    run = Path(run)
    slots = Path(slots) if slots is not None else run / "request-slots"
    attempts = [read(path) for path in run.glob("requests/*/attempt-*.json")]
    state_path = slots / "http-progress.json"
    state = read(state_path) if state_path.exists() else {}
    usages = [a.get("usage") or {} for a in attempts]
    return {
        "request_attempts": sum("request_started_at" in a for a in attempts),
        "recorded_attempts": len(attempts),
        "failed_attempts": sum(a["status"] == "error" and "request_started_at" in a for a in attempts),
        "skipped_attempts": sum(a["status"] == "skipped_content_moderation" for a in attempts),
        "input_tokens": sum(u.get("prompt_tokens", 0) or 0 for u in usages),
        "output_tokens": sum(u.get("completion_tokens", 0) or 0 for u in usages),
        "total_tokens": sum((u.get("total_tokens") if u.get("total_tokens") is not None
                             else (u.get("prompt_tokens", 0) or 0) + (u.get("completion_tokens", 0) or 0)) for u in usages),
        "http_elapsed_seconds": sum(a.get("http_elapsed_seconds", 0) for a in attempts),
        "peak_http": state.get("peak_http", 0),
        "active_http": state.get("active_http", 0),
        "http_attempts_shared": state.get("http_attempts", 0),
        "abandoned_attempts": state.get("abandoned_attempts", 0),
        "cost_usd": None,
    }
