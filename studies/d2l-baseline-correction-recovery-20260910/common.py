"""Audited transport and restartable artifacts for the corrected baselines."""
from __future__ import annotations

import contextlib
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import threading
import time
import urllib.request
import urllib.error
import uuid

MODEL = 'MiniMax-M3'
ENDPOINT = 'https://api.minimaxi.com/v1/text/chatcompletion_v2'
SEED = 20260909
BENCH = Path('/home/likefallwind/code/llm-graph-benchmark')
UPSTREAM = Path('/home/likefallwind/code/llm-graph-baselines')
CORPUS = BENCH / 'outputs/d2l-fullbook-open-baselines-20260826/corpus/chunks.jsonl'
if (Path(__file__).parent/'frozen-corpus/chunks.jsonl').exists():
    CORPUS=Path(__file__).parent/'frozen-corpus/chunks.jsonl'


def benchmark_path():
    frozen=Path(__file__).parent/'frozen-benchmark/benchmark.json'
    return frozen if frozen.exists() else BENCH/'outputs/d2l-full1105-vnext-20260826/benchmark.json'


class TerminalProviderError(RuntimeError):
    pass


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line]


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temp.replace(path)


def freeze(path, value):
    if Path(path).exists():
        if read(path) != value:
            raise ValueError(f'Frozen inputs changed: {path}')
    else:
        write(path, value)


def load_secret():
    names = ('MINIMAX_API_KEY', 'MINIMAX_API', 'minimax_api')
    value = next((os.environ[n].strip() for n in names if os.environ.get(n)), '')
    if not value:
        for line in Path('/home/likefallwind/.bashrc').read_text().splitlines():
            if not re.match(r'^\s*(?:export\s+)?(?:MINIMAX_API_KEY|MINIMAX_API|minimax_api)=', line):
                continue
            parts = shlex.split(line, comments=True)
            if parts and parts[0] == 'export':
                parts = parts[1:]
            if len(parts) == 1:
                candidate = parts[0].split('=', 1)[1]
                if not any(c in candidate for c in ('$','`','\n')):
                    value = candidate.strip()
                    break
    if value.lower().startswith('bearer '):
        value = value[7:].strip()
    if not value:
        raise RuntimeError('Static MiniMax API credential unavailable')
    return value


@contextlib.contextmanager
def request_slot(root, limit=6):
    """A shared six-slot cap across all baseline processes and their retries."""
    if not 1 <= limit <= 6:
        raise ValueError('concurrency must be in 1..6')
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    handle = None
    while handle is None:
        for i in range(limit):
            candidate = (root / f'slot-{i}.lock').open('a')
            try:
                fcntl.flock(candidate, fcntl.LOCK_EX | fcntl.LOCK_NB)
                handle = candidate
                break
            except BlockingIOError:
                candidate.close()
        if handle is None:
            time.sleep(0.05)
    try:
        yield
    finally:
        fcntl.flock(handle, fcntl.LOCK_UN)
        handle.close()


def validate_response(response):
    code=response.get('base_resp', {}).get('status_code',0)
    if code in (1004,1008,2013,2049,2067):
        raise TerminalProviderError(f'MiniMax terminal provider code {code}')
    if response.get('base_resp', {}).get('status_code', 0) != 0 or response.get('error'):
        raise ValueError('provider error response')
    if response.get('model', '').lower() != MODEL.lower():
        raise ValueError('unexpected provider model')
    choices = response.get('choices', [])
    if len(choices) != 1 or choices[0].get('finish_reason') != 'stop':
        raise ValueError('missing choice or non-stop completion')
    content = choices[0].get('message', {}).get('content')
    if not isinstance(content, str) or not content.strip():
        raise ValueError('empty final answer')
    return response


def openai_shape(response):
    """Drop provider-only envelope fields, preserving choices/model/usage verbatim.

    MiniMax emits service_tier='standard', absent from the OpenAI SDK enum.
    The original provider envelope is retained in the request audit.
    """
    result={k:response[k] for k in ('id','choices','created','model','object','usage') if k in response}
    result.setdefault('id','minimax-'+digest(response)[:20])
    result.setdefault('object','chat.completion')
    result.setdefault('created',int(time.time()))
    return result


class Client:
    def __init__(self, run, lock_root, secret=None):
        self.run = Path(run)
        self.lock_root = Path(lock_root)
        self.secret = secret if secret is not None else load_secret()

    def complete(self, messages, max_tokens=8192, cache=False, validator=None):
        if isinstance(messages, str):
            messages = [{'role':'user','content':messages}]
        messages = [m.model_dump(exclude_none=True) if hasattr(m, 'model_dump') else dict(m) for m in messages]
        payload = dict(model=MODEL, messages=messages, temperature=0.0,
                       max_tokens=max_tokens, stream=False)
        cache_path = self.run / 'response-cache' / (digest(payload) + '.json')
        if cache and cache_path.exists():
            response=validate_response(read(cache_path))
            try:
                if validator:validator(response)
            except ValueError:
                rejected=self.run/'rejected-response-cache'/cache_path.name
                rejected.parent.mkdir(parents=True,exist_ok=True)
                cache_path.replace(rejected)
            else:
                return response
        request_id = uuid.uuid4().hex
        request_dir = self.run / 'requests' / request_id
        write(request_dir / 'request.json', payload)
        last = None
        for attempt in range(1, 4):
            if (self.lock_root/'terminal-error.json').exists():
                raise TerminalProviderError('Shared run stopped on provider credential/quota error')
            started = time.time()
            record = {'started_at':started, 'attempt':attempt, 'endpoint':ENDPOINT}
            try:
                request = urllib.request.Request(ENDPOINT, data=canonical(payload).encode(),
                    headers={'Authorization':'Bearer '+self.secret,'Content-Type':'application/json'})
                class NoRedirect(urllib.request.HTTPRedirectHandler):
                    def redirect_request(self,req,fp,code,msg,headers,newurl):
                        return None
                opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
                with request_slot(self.lock_root):
                    if (self.lock_root/'terminal-error.json').exists():
                        raise TerminalProviderError('Shared terminal provider failure')
                    record['request_started_at']=time.time()
                    try:
                        try:
                            with opener.open(request, timeout=180) as handle:
                                body = handle.read().decode().replace(self.secret,'[REDACTED]')
                        except urllib.error.HTTPError as exc:
                            record['http_status']=exc.code
                            if exc.code in (401,403):
                                raise TerminalProviderError(f'MiniMax HTTP {exc.code}') from exc
                            raise
                    finally:
                        record['request_finished_at']=time.time()
                record['raw_body'] = body
                response = json.loads(body)
                record.update(usage=response.get('usage', {}),model=response.get('model'))
                validate_response(response)
                if validator:validator(response)
                record.update(status='done', usage=response.get('usage', {}), model=response['model'])
                if cache:
                    write(cache_path, response)
                return response
            except TerminalProviderError as exc:
                record.update(status='error',error_type=type(exc).__name__)
                try:
                    with (self.lock_root/'terminal-error.json').open('x') as handle:
                        json.dump(dict(error=str(exc),at=time.time()),handle)
                except FileExistsError:pass
                raise
            except Exception as exc:
                # Exception messages may embed provider URLs. Never serialize request headers.
                last = exc
                record.update(status='error', error_type=type(exc).__name__)
            finally:
                record['elapsed_seconds'] = time.time()-started
                write(request_dir / f'attempt-{attempt}.json', record)
            if attempt < 3:
                time.sleep(2**attempt)
        raise RuntimeError(f'MiniMax call failed; see requests/{request_id}') from last


def checkpoint(path, inputs, function, retries=3):
    path = Path(path)
    fingerprint = digest(inputs)
    if path.exists():
        result = read(path)
        if result['input_sha256'] != fingerprint:
            raise ValueError(f'Checkpoint input changed: {path}')
        if result['status'] == 'done':
            return result['value']
    for attempt in range(retries):
        started = time.time()
        try:
            value = function()
            # Round-trip to ensure first run and resumed runs have identical types.
            value = json.loads(canonical(value))
            write(path, dict(status='done', input_sha256=fingerprint, value=value))
            return value
        except Exception as exc:
            failure = dict(status='failed', input_sha256=fingerprint,
                           error_type=type(exc).__name__, error=str(exc), started_at=started)
            write(path.parent / 'failures' / (path.stem+'-'+uuid.uuid4().hex+'.json'), failure)
            write(path, failure)
            if isinstance(exc,TerminalProviderError) or attempt == retries-1:
                raise


def parallel(function,items,workers=6):
    """Keep only six work items pending; an error cannot start the entire corpus."""
    iterator=iter(items)
    pool=ThreadPoolExecutor(max_workers=workers)
    pending=set()
    try:
        for _ in range(workers):
            try:pending.add(pool.submit(function,next(iterator)))
            except StopIteration:break
        while pending:
            done,pending=wait(pending,return_when=FIRST_COMPLETED)
            values=[f.result() for f in done]
            for value in values:yield value
            for _ in done:
                try:pending.add(pool.submit(function,next(iterator)))
                except StopIteration:break
    finally:
        for f in pending:f.cancel()
        pool.shutdown(wait=True,cancel_futures=True)


def usage(run):
    attempts = [read(p) for p in Path(run).glob('requests/*/attempt-*.json')]
    return dict(request_attempts=len(attempts),
                failed_attempts=sum(x['status']!='done' for x in attempts),
                input_tokens=sum(x.get('usage',{}).get('prompt_tokens',0) for x in attempts),
                output_tokens=sum(x.get('usage',{}).get('completion_tokens',0) for x in attempts),
                cost_usd=None)


def validate_export(out):
    from llm_graph_benchmark.bundle import BenchmarkBundle, SubmissionBundle
    from llm_graph_benchmark.validation import validate_submission
    benchmark=BenchmarkBundle.load(benchmark_path())
    result=validate_submission(SubmissionBundle.load(Path(out)/'submission.json'),benchmark)
    write(Path(out)/'validation.json',result.as_dict())
    if not result.ok:
        raise ValueError('Submission validation failed; see validation.json')


def map_kggen_relations(raw_triples, graph):
    """Replay precisely upstream's mapping, preserving triple-specific evidence."""
    def mapped(item, names, clusters):
        if item in names:
            return item
        return next((rep for rep, members in clusters.items() if item in members), item)
    output = {}
    lineage = []
    for row in raw_triples:
        old = (row['subject'],row['predicate'],row['object'])
        new = (mapped(old[0],graph['entities'],graph.get('entity_clusters') or {}),
               mapped(old[1],graph['edges'],graph.get('edge_clusters') or {}),
               mapped(old[2],graph['entities'],graph.get('entity_clusters') or {}))
        output.setdefault(new,set()).update(row['evidence_unit_ids'])
        lineage.append(dict(original=list(old), canonical=list(new), unit_ids=row['evidence_unit_ids']))
    if set(output) != {tuple(x) for x in graph['relations']}:
        raise ValueError('Upstream relation transformation does not match lineage replay')
    triples = [dict(subject=s,predicate=p,object=o,evidence_unit_ids=sorted(units))
               for (s,p,o),units in sorted(output.items())]
    return triples, lineage
