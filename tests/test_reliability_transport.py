"""Offline checks for the reliability study's real HTTP boundary and audit."""
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import io
import json
import multiprocessing
from pathlib import Path
import threading
import time
from types import SimpleNamespace
import urllib.error

import pytest


TRANSPORT = Path(__file__).resolve().parents[1] / "studies/d2l-reliability-20260920/transport.py"
SECRET = "fake-test-credential-never-write-this"


@pytest.fixture
def transport(monkeypatch):
    spec = importlib.util.spec_from_file_location("reliability_test_transport", TRANSPORT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setenv("MINIMAX_API_KEY", SECRET)
    # Prevent accidental network use even if a test forgets its fake opener.
    def unavailable(*args, **kwargs):
        raise AssertionError("Tests must not open network connections")
    monkeypatch.setattr(module.urllib.request, "build_opener", unavailable)
    return module


def response(content='{"label":"incorrect"}', **updates):
    value = {"base_resp": {"status_code": 0}, "model": "MiniMax-M3",
             "choices": [{"finish_reason": "stop", "message": {"content": content}}],
             "usage": {"prompt_tokens": 12, "completion_tokens": 3, "total_tokens": 15}}
    value.update(updates)
    return value


class Handle:
    status = 200

    def __init__(self, value):
        self.value = value

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.value).encode()


def fake_opener(monkeypatch, transport, values):
    calls = []
    values = iter(values)

    def open_request(request, timeout):
        calls.append(request)
        value = next(values)
        if isinstance(value, Exception):
            raise value
        return Handle(value)

    handlers = []
    def build(*args):
        handlers.extend(args)
        return SimpleNamespace(open=open_request)
    monkeypatch.setattr(transport.urllib.request, "build_opener", build)
    monkeypatch.setattr(transport, "time", SimpleNamespace(time=time.time, monotonic=time.monotonic,
                                                          sleep=lambda duration: None))
    return calls, handlers


def test_cache_preserves_negative_labels_and_keys_by_entire_payload(transport, monkeypatch, tmp_path):
    calls, handlers = fake_opener(monkeypatch, transport, [response()] * 3)
    client = transport.Client(tmp_path, tmp_path / "request-slots")
    checks = []
    def validate(value):
        checks.append(json.loads(value["choices"][0]["message"]["content"])["label"])
    first = client.complete("fact A", validator=validate)
    assert client.complete("fact A", validator=validate) == first
    client.complete("fact A", max_tokens=4095, validator=validate)
    client.complete("fact B", validator=validate)
    assert len(calls) == 3
    assert checks == ["incorrect"] * 4
    assert all(c.full_url == transport.ENDPOINT for c in calls)
    assert all(json.loads(c.data)["model"] == transport.MODEL for c in calls)
    assert any(isinstance(h, transport.NoRedirect) for h in handlers)
    assert transport.NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.test") is None
    assert client.usage_summary()["request_attempts"] == 3
    assert client.usage_summary()["total_tokens"] == 45
    assert client.usage_summary()["active_http"] == 0
    for path in tmp_path.rglob("*.json"):
        assert SECRET not in path.read_text()
        assert "Authorization" not in path.read_text()


def test_validator_failures_retry_and_invalid_cache_is_preserved(transport, monkeypatch, tmp_path):
    calls, _ = fake_opener(monkeypatch, transport, [response("bad"), response("bad"), response()])
    client = transport.Client(tmp_path, tmp_path / "request-slots")
    client.complete("fact")  # Previously cached without a schema validator.
    def validate(value):
        json.loads(value["choices"][0]["message"]["content"])
    client.complete("fact", validator=validate)
    assert len(calls) == 3
    assert len(list((tmp_path / "rejected-response-cache").glob("*.json"))) == 1
    summary = client.usage_summary()
    assert summary["failed_attempts"] == 1
    assert summary["request_attempts"] == 3
    assert summary["http_attempts_shared"] == 3
    assert summary["total_tokens"] == 45  # Includes invalid answers, not just success.


@pytest.mark.parametrize("bad", [
    response(model="MiniMax-M2"),
    response(choices=[{"finish_reason": "length", "message": {"content": "{}"}}]),
    response(base_resp={"status_code": 1001}),
    response(base_resp=None),
])
def test_model_truncation_and_provider_errors_never_become_labels(transport, monkeypatch, tmp_path, bad):
    calls, _ = fake_opener(monkeypatch, transport, [bad] * 3)
    client = transport.Client(tmp_path, tmp_path / "request-slots")
    with pytest.raises(RuntimeError, match="exhausted 3 attempts"):
        client.complete("fact")
    assert len(calls) == 3
    assert not list((tmp_path / "response-cache").glob("*.json"))
    assert client.usage_summary()["failed_attempts"] == 3


def test_quota_error_stops_other_clients_and_preserves_first_reason(transport, monkeypatch, tmp_path):
    calls, _ = fake_opener(monkeypatch, transport, [response(base_resp={"status_code": 2067})])
    slots = tmp_path / "request-slots"
    one = transport.Client(tmp_path / "one", slots)
    two = transport.Client(tmp_path / "two", slots)
    with pytest.raises(transport.TerminalProviderError, match="2067"):
        one.complete("A")
    with pytest.raises(transport.TerminalProviderError, match="Shared run"):
        two.complete("B")
    assert len(calls) == 1
    assert "2067" in transport.read(slots / "terminal-error.json")["error"]


@pytest.mark.parametrize("code", [1026, 1027])
def test_moderation_is_cached_skip_and_does_not_stop_run(transport, monkeypatch, tmp_path, code):
    calls, _ = fake_opener(monkeypatch, transport,
                           [response(base_resp={"status_code": code}), response()])
    client = transport.Client(tmp_path, tmp_path / "request-slots")
    for _ in range(2):
        with pytest.raises(transport.ContentRejected) as error:
            client.complete("moderated")
        assert error.value.record["provider_code"] == code
    client.complete("another fact")
    assert len(calls) == 2
    assert not (tmp_path / "request-slots/terminal-error.json").exists()
    assert client.usage_summary()["skipped_attempts"] == 1


def test_http_failure_body_is_saved_redacted_and_auth_is_terminal(transport, monkeypatch, tmp_path):
    body = json.dumps({"error": "credential " + SECRET}).encode()
    error = urllib.error.HTTPError(transport.ENDPOINT, 401, "Unauthorized", {}, io.BytesIO(body))
    calls, _ = fake_opener(monkeypatch, transport, [error])
    client = transport.Client(tmp_path, tmp_path / "request-slots")
    with pytest.raises(transport.TerminalProviderError, match="401"):
        client.complete("fact")
    assert len(calls) == 1
    attempt = transport.read(next(tmp_path.glob("requests/*/attempt-1.json")))
    assert attempt["http_status"] == 401
    assert "[REDACTED]" in attempt["raw_body"]
    assert SECRET not in json.dumps(attempt)
    assert attempt["http_elapsed_seconds"] >= 0


def test_missing_environment_credential_never_falls_back_to_files(transport, monkeypatch, tmp_path):
    monkeypatch.delenv("MINIMAX_API_KEY")
    monkeypatch.setenv("MINIMAX_API", SECRET)
    with pytest.raises(transport.TerminalProviderError, match="MINIMAX_API_KEY"):
        transport.Client(tmp_path, tmp_path / "request-slots")
    assert list(tmp_path.iterdir()) == []


def test_six_real_http_slots_shared_by_clients_with_measured_peak(transport, monkeypatch, tmp_path):
    guard = threading.Lock()
    barrier = threading.Barrier(6)
    counts = {"active": 0, "peak": 0, "calls": 0}

    class SlowHandle(Handle):
        def read(self):
            barrier.wait(timeout=5)
            return super().read()

        def __exit__(self, *args):
            with guard:
                counts["active"] -= 1

    def open_request(request, timeout):
        with guard:
            counts["active"] += 1
            counts["calls"] += 1
            counts["peak"] = max(counts["peak"], counts["active"])
        return SlowHandle(response())

    monkeypatch.setattr(transport.urllib.request, "build_opener",
                        lambda *args: SimpleNamespace(open=open_request))
    clients = [transport.Client(tmp_path / str(i), tmp_path / "request-slots") for i in range(12)]
    with ThreadPoolExecutor(max_workers=12) as pool:
        list(pool.map(lambda pair: pair[1].complete(str(pair[0])), enumerate(clients)))
    assert counts == {"active": 0, "peak": 6, "calls": 12}
    state = transport.read(tmp_path / "request-slots/http-progress.json")
    assert state["peak_http"] == 6
    assert state["active_http"] == 0
    assert state["http_attempts"] == 12
    events = [json.loads(line) for line in (tmp_path / "request-slots/http-events.jsonl").read_text().splitlines()]
    assert len(events) == 24
    assert max(event["active_http"] for event in events) == 6


def test_slot_ceiling_is_cross_process(transport, tmp_path):
    context = multiprocessing.get_context("fork")
    active = context.Value("i", 0)
    peak = context.Value("i", 0)
    guard = context.Lock()
    start = context.Event()

    def work():
        start.wait(timeout=5)
        with transport.request_slot(tmp_path / "slots"):
            with guard:
                active.value += 1
                peak.value = max(peak.value, active.value)
            time.sleep(0.08)
            with guard:
                active.value -= 1

    processes = [context.Process(target=work) for _ in range(12)]
    for process in processes:
        process.start()
    start.set()
    for process in processes:
        process.join(timeout=5)
        if process.is_alive():
            process.terminate()
            process.join()
        assert process.exitcode == 0
    assert 1 < peak.value <= 6
    assert active.value == 0
