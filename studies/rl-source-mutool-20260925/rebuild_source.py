"""Rebuild the frozen Sutton-Barto source text with mutool; no API calls.

Unit IDs, order, locations and section headings stay fixed so every existing
submission remains valid. Only the text of S2 (PDF) units changes:
  - mutool_span: the unit's ASCII-alphanumeric skeleton occurs verbatim in the
    mutool text of its pages, so the unit is replaced by that mutool span;
  - symbol_patch: no verbatim skeleton match (figure text, side-by-side layout,
    complex formulas); the pdftotext text is kept and only symbols that
    pdftotext drops are inserted between aligned characters;
  - unchanged / heading_kept.
Every rewritten unit keeps exactly the same alphanumeric skeleton.
"""
from pathlib import Path
import collections
import difflib
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import unicodedata


ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / "studies/rl-baselines-20260923/frozen-benchmark"
OUT = Path(__file__).resolve().parent
NEW = OUT / "frozen-benchmark"
PDF = Path("/home/likefallwind/code/llm-knowledge-graph/data/docs/sutton-barto.pdf")
PREFIX = "S2:"
# Symbols pdftotext drops for this PDF but mutool recovers from glyph names.
RECOVERABLE = set("−γλδσ≥≤βφθ∆πξ∗")
# mutool emits accents as spacing modifiers before the letter.
ACCENTS = {"ˆ": "̂", "¯": "̄", "´": "́", "¨": "̈",
           "˙": "̇", "¸": "̧", "˜": "̃", "˘": "̆"}


def mutool_pages(pdf):
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["mutool", "draw", "-F", "txt", "-o", f"{tmp}/p%d.txt", str(pdf)],
                       check=True, capture_output=True)
        count = len(list(Path(tmp).glob("p*.txt")))
        return {i: clean(Path(f"{tmp}/p{i}.txt").read_text()) for i in range(1, count + 1)}


def clean(text):
    text = text.replace("\ufffd", "").replace("휀", "ε")
    # Keep pdftotext's decomposed form (letter + combining mark), no NFC.
    return re.sub("([" + "".join(ACCENTS) + r"])\s?([^\W\d_])",
                  lambda m: m.group(2) + ACCENTS[m.group(1)], text)


def skeleton(text):
    idx = [i for i, c in enumerate(text) if c.isascii() and c.isalnum()]
    return "".join(text[i] for i in idx), idx


def pages_of(unit):
    m = re.search(r"pages? (\d+)(?:-(\d+))?", unit["location"]["description"])
    return int(m.group(1)), int(m.group(2) or m.group(1))


def window(pages, unit):
    first, last = pages_of(unit)
    parts, starts, pos = [], {}, 0
    for p in range(max(1, first - 1), min(len(pages), last + 1) + 1):
        starts[p] = pos
        parts.append(pages[p])
        pos += len(pages[p])
    return "".join(parts), starts.get(first, 0)


def span(text, unit_skel, win, page_start):
    win_skel, widx = skeleton(win)
    hits = [m.start() for m in re.finditer(re.escape(unit_skel), win_skel)]
    if not hits:
        return None
    pos = min(hits, key=lambda h: (widx[h] < page_start, abs(widx[h] - page_start)))
    s, e = widx[pos], widx[pos + len(unit_skel) - 1] + 1
    while s and not win[s - 1].isspace() and not (win[s - 1].isascii() and win[s - 1].isalnum()):
        s -= 1
    while e < len(win) and not win[e].isspace() and not (win[e].isascii() and win[e].isalnum()):
        e += 1
    return re.sub(r"\n[ \t]*\n+", "\n", win[s:e]).strip()


def core(gap):
    return "".join(c for c in gap if not c.isspace() and not unicodedata.combining(c))


def patch(text, win):
    """Insert recoverable symbols into gaps between aligned skeleton characters."""
    ts, tidx = skeleton(text)
    ws, widx = skeleton(win)
    edits = []
    for a, b, size in difflib.SequenceMatcher(None, ts, ws, autojunk=False).get_matching_blocks():
        for k in range(size - 1):
            t0, t1 = tidx[a + k] + 1, tidx[a + k + 1]
            w0, w1 = widx[b + k] + 1, widx[b + k + 1]
            tg, wg = text[t0:t1], win[w0:w1]
            tc, wc = core(tg), core(wg)
            if [c for c in tc if c not in RECOVERABLE] != [c for c in wc if c not in RECOVERABLE]:
                continue
            added = list((collections.Counter(c for c in wc if c in RECOVERABLE)
                          - collections.Counter(c for c in tc if c in RECOVERABLE)).elements())
            if not added:
                continue
            new = wg if "\n" in tg else re.sub(r"\s+", " ", wg)
            edits.append((t0, t1, new, added))
    for t0, t1, new, _ in reversed(edits):
        text = text[:t0] + new + text[t1:]
    return text, collections.Counter(c for *_, added in edits for c in added)


def main():
    pages = mutool_pages(PDF)
    doc = json.loads((OLD / "documents.jsonl").read_text().splitlines()[0])
    methods, added, samples = collections.Counter(), collections.Counter(), []
    for unit in doc["units"]:
        if not unit["unit_id"].startswith(PREFIX):
            continue
        old = unit["text"]
        if old.lstrip().startswith("#"):
            methods["heading_kept"] += 1
            continue
        old_skel = skeleton(old)[0]
        win, page_start = window(pages, unit)
        new = span(old, old_skel, win, page_start) if old_skel else None
        if new is not None:
            method = "mutool_span"
        else:
            new, counts = patch(old, win)
            method = "symbol_patch" if counts else "unchanged"
        if skeleton(new)[0] != old_skel:
            raise ValueError("Alphanumeric content changed: " + unit["unit_id"])
        methods[method] += 1
        if new != old:
            added.update(c for c in new if c in RECOVERABLE)
            added.subtract(c for c in old if c in RECOVERABLE)
            unit["text"] = new
            unit["content_hash"] = "sha256:" + hashlib.sha256(new.encode()).hexdigest()
            unit["metadata"] = {**unit.get("metadata", {}), "text_source": "mutool-" + method}
            samples.append({"unit_id": unit["unit_id"], "method": method, "old": old, "new": new})
    doc["metadata"] = {**doc["metadata"], "text_extractor": "mutool 1.23.10 draw -F txt (S2 units)",
                       "previous_content_hash": doc["content_hash"]}
    doc["content_hash"] = "sha256:" + hashlib.sha256(
        "\n".join(u["content_hash"] for u in doc["units"]).encode()).hexdigest()
    NEW.mkdir(parents=True, exist_ok=True)
    for name in ("fact_probes-reviewed.jsonl", "qa_probes-reviewed.jsonl", "rubric.json"):
        shutil.copy2(OLD / name, NEW / name)
    bench = json.loads((OLD / "benchmark.json").read_text())
    # Submissions pin benchmark_id; the source version lives in metadata and the benchmark hash.
    bench["metadata"] = {**bench["metadata"], "source_text": "mutool-rebuild-20260925; unit IDs unchanged"}
    (NEW / "benchmark.json").write_text(json.dumps(bench, ensure_ascii=False, indent=2) + "\n")
    (NEW / "documents.jsonl").write_text(json.dumps(doc, ensure_ascii=False) + "\n")
    report = {"units": sum(methods.values()), "methods": dict(methods),
              "changed_units": len(samples), "recovered_symbols": {k: v for k, v in added.items() if v},
              "document_content_hash": doc["content_hash"]}
    (OUT / "REBUILD.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    (OUT / "changes.jsonl").write_text("".join(json.dumps(s, ensure_ascii=False) + "\n" for s in samples))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
