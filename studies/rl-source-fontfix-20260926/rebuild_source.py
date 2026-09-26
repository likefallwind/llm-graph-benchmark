"""Re-extract the Sutton-Barto source with corrected font mappings; no API calls.

The PDF was written by macOS Quartz. Its TeX math fonts carry correct glyph
names in /Differences (/pi, /alpha, /theta, /nabla, /prime ...), but the
/ToUnicode CMaps generated beside them are wrong: /pi -> U+21E1, /alpha and the
/ff ligature -> U+21B5, /nabla -> "r", /element -> "2", /prime -> "0",
/summationdisplay -> "X", and /minus, /lambda, /gamma ... -> U+0000 (dropped).

This script rewrites every such CMap from the glyph names, runs the original
extractor (`pdftotext -layout`, as in llm-knowledge-graph kg/sources.py) on the
original and the corrected PDF, aligns the two outputs page by page, and maps
each frozen S2 unit onto the corrected text. Unit IDs, order, locations,
section headings and layout stay fixed; only characters produced by the wrong
font mappings change. D2L (S1) units are not touched.

Run with an interpreter that has PyMuPDF and fontTools, e.g.
    /home/likefallwind/miniconda3/bin/python studies/rl-source-fontfix-20260926/rebuild_source.py
"""
from pathlib import Path
import bisect
import collections
import difflib
import hashlib
import json
import re
import shutil
import subprocess
import tempfile

import fitz
from fontTools.agl import toUnicode


ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / "studies/rl-baselines-20260923/frozen-benchmark"
OUT = Path(__file__).resolve().parent
NEW = OUT / "frozen-benchmark"
PDF = Path("/home/likefallwind/code/llm-knowledge-graph/data/docs/sutton-barto.pdf")
PREFIX = "S2:"

# TeX glyph names outside the Adobe Glyph List, plus ligatures spelled out.
# Extension pieces of tall delimiters become spaces so a brace spanning three
# lines reads "{" rather than "{{{".
TEX_NAMES = {
    "ff": "ff", "fi": "fi", "fl": "fl", "ffi": "ffi", "ffl": "ffl",
    "prime": "′", "latticetop": "⊤", "star": "⋆", "square": "□",
    "lessmuch": "≪", "greatermuch": "≫", "bardbl": "‖", "mapsto": "|",
    "negationslash": "/", "angbracketleft": "⟨", "angbracketright": "⟩",
    "summationtext": "∑", "summationdisplay": "∑", "producttext": "∏",
    "productdisplay": "∏", "integraltext": "∫", "integraldisplay": "∫",
    "hatwide": "ˆ", "hatwider": "ˆ", "hatwidest": "ˆ",
    "tildewide": "˜", "tildewider": "˜", "tildewidest": "˜",
    "epsilon1": "ε", "vextendsingle": "|", "vextenddouble": "‖", "squiggleright": "⇝",
}
DELIMITERS = {"parenleft": "(", "parenright": ")", "bracketleft": "[",
              "bracketright": "]", "braceleft": "{", "braceright": "}"}
# Letters the wrong CMaps emitted for math glyphs (CMEX "P" = sum, CMSY "r" =
# nabla ...) and letters the ligature fixes add; all other ASCII letters must
# survive the rebuild unchanged in every unit.
UNSTABLE_LETTERS = set("ABPQXYbdefhiklpqrsz")
PATCH_MARGIN = 400
WRONG_GLYPHS = set("↵⇡✓⌧⇢⇤⇥⇠⇣⌘◆\uf8ff⇧⌦✏")
PROBE_GLYPHS = str.maketrans({"⇡": "π", "⇤": "∗", "↵": "α"})


def glyph_text(name):
    if name in TEX_NAMES:
        return TEX_NAMES[name]
    if name.startswith("radical"):
        return "√"
    if name.startswith("bracehtip"):
        return " "
    for stem, char in DELIMITERS.items():
        if name.startswith(stem):
            rest = name[len(stem):]
            if rest in ("", "big", "Big", "bigg", "Bigg", "tp"):
                return char
            if rest in ("bt", "ex", "mid"):
                return " "
    return toUnicode(name) or None


def parse_differences(text):
    codes, code = {}, None
    for token in re.findall(r"/[^\s/\[\]]+|\d+", text.split("Differences", 1)[1]):
        if token.isdigit():
            code = int(token)
        else:
            codes[code] = token[1:]
            code += 1
    return codes


def parse_cmap(data):
    mapping = {}
    for block in re.findall(r"beginbfchar(.*?)endbfchar", data, re.S):
        for src, dst in re.findall(r"<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]*)>", block):
            mapping[int(src, 16)] = dst
    for block in re.findall(r"beginbfrange(.*?)endbfrange", data, re.S):
        for lo, hi, dst in re.findall(r"<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]+)>", block):
            for code in range(int(lo, 16), int(hi, 16) + 1):
                mapping[code] = format(int(dst, 16) + code - int(lo, 16), "0%dx" % len(dst))
    return {code: "".join(chr(int(v[i:i + 4], 16)) for i in range(0, len(v), 4))
            for code, v in mapping.items()}


def write_cmap(mapping):
    lines = ["/CIDInit /ProcSet findresource begin", "12 dict begin", "begincmap",
             "/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def",
             "/CMapName /Adobe-Identity-UCS def", "/CMapType 2 def",
             "1 begincodespacerange", "<00> <FF>", "endcodespacerange"]
    items = sorted(mapping.items())
    for start in range(0, len(items), 100):
        chunk = items[start:start + 100]
        lines.append("%d beginbfchar" % len(chunk))
        for code, text in chunk:
            hexed = "".join(format(b, "02X") for b in text.encode("utf-16-be"))
            lines.append("<%02X> <%s>" % (code, hexed))
        lines.append("endbfchar")
    lines += ["endcmap", "CMapName currentdict /CMap defineresource pop", "end", "end"]
    return "\n".join(lines).encode()


def fix_pdf(src, dst):
    """Rewrite ToUnicode CMaps of /Differences fonts from their glyph names."""
    doc = fitz.open(src)
    fixes, unknown = collections.Counter(), collections.Counter()
    for xref in range(1, doc.xref_length()):
        try:
            if doc.xref_get_key(xref, "Type") != ("name", "/Font"):
                continue
        except Exception:
            continue
        kind, value = doc.xref_get_key(xref, "ToUnicode")
        etype, evalue = doc.xref_get_key(xref, "Encoding")
        if etype == "xref":
            evalue = doc.xref_object(int(evalue.split()[0]))
        if kind != "xref" or "Differences" not in evalue:
            continue
        stream = int(value.split()[0])
        font = doc.xref_get_key(xref, "BaseFont")[1].split("+")[-1]
        cmap = parse_cmap(doc.xref_stream(stream).decode("latin-1"))
        new = dict(cmap)
        for code, name in parse_differences(evalue).items():
            text = glyph_text(name)
            if text is None:
                unknown[(font, name)] += 1
                continue
            if cmap.get(code) != text:
                fixes[(font, name, cmap.get(code, ""), text)] += 1
                new[code] = text
        if new != cmap:
            doc.update_stream(stream, write_cmap(new))
    doc.save(dst)
    return fixes, unknown


def pdftotext(path):
    out = subprocess.run(["pdftotext", "-layout", str(path), "-"],
                         check=True, capture_output=True, text=True).stdout
    return out


def align(old, new):
    """Opcodes between the two extractions in global offsets: lines first, then characters."""
    old_lines, new_lines = old.splitlines(keepends=True), new.splitlines(keepends=True)
    old_at, new_at = [0], [0]
    for line in old_lines:
        old_at.append(old_at[-1] + len(line))
    for line in new_lines:
        new_at.append(new_at[-1] + len(line))
    ops = []
    lines = difflib.SequenceMatcher(None, old_lines, new_lines, autojunk=False)
    for tag, i1, i2, j1, j2 in lines.get_opcodes():
        oi, ni = old_at[i1], new_at[j1]
        if tag == "equal":
            ops.append(("equal", oi, old_at[i2], ni, new_at[j2]))
            continue
        # Layout padding makes spaces far too common to anchor matches on.
        chars = difflib.SequenceMatcher(lambda c: c == " ", old[oi:old_at[i2]], new[ni:new_at[j2]],
                                        autojunk=False)
        for ctag, c1, c2, d1, d2 in chars.get_opcodes():
            ops.append((ctag, oi + c1, oi + c2, ni + d1, ni + d2))
    return ops


def mapper(ops):
    starts = [op[1] for op in ops]

    def locate(pos, side):
        k = bisect.bisect_right(starts, pos) - 1
        tag, i1, i2, j1, j2 = ops[k]
        if tag == "equal":
            return j1 + pos - i1
        if side == "start":
            if pos == i1:
                return j1
            return j2 if pos >= i2 else j1
        if pos == i1:
            return j1
        return j2
    return locate


def core(text):
    return "".join(c for c in text if not c.isspace())


def letters(text):
    """ASCII letters that no CMap fix can create or remove."""
    return collections.Counter(c for c in text if c.isascii() and c.isalpha() and c not in UNSTABLE_LETTERS)


def patch(old, window, allowed, restored):
    """Keep the old text and layout; apply only known glyph fixes at aligned positions."""
    out, count = [], 0
    matcher = difflib.SequenceMatcher(lambda c: c == " ", old, window, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        seg_old, seg_new = old[i1:i2], window[j1:j2]
        co, cn = core(seg_old), core(seg_new)
        new = None
        if tag == "equal" or not cn:
            pass
        elif not co and set(cn) <= restored:
            if "\n" in seg_old:
                new = " " + cn + seg_old
            else:
                new = seg_new if "\n" not in seg_new else " " + cn + " "
        elif co in seg_old and (co, cn) in allowed:
            new = seg_old.replace(co, cn, 1)
        elif len(co) == len(cn) and all(pair in allowed for pair in zip(co, cn)):
            fixed = iter(cn)
            new = "".join(c if c.isspace() else next(fixed) for c in seg_old)
        if new is None:
            out.append(seg_old)
        else:
            out.append(new)
            count += 1
    return "".join(out), count


def fix_probes(src, dst):
    """Probes were generated from the old text and copied three wrong glyphs;
    in their statements these are all CMMI/CMSY math, so no ligature arises."""
    fixed, lines = [], []
    for line in src.read_text().splitlines():
        item = json.loads(line)
        new = json.loads(json.dumps(item, ensure_ascii=False).translate(PROBE_GLYPHS))
        if any(c in WRONG_GLYPHS for c in json.dumps(new, ensure_ascii=False)):
            raise ValueError("unexpected glyph in probe: " + str(item.get("probe_id", item.get("qa_id"))))
        if new != item:
            fixed.append(item.get("probe_id") or item.get("qa_id") or item.get("id"))
        lines.append(json.dumps(new, ensure_ascii=False))
    dst.write_text("\n".join(lines) + "\n")
    return fixed


def main():
    with tempfile.TemporaryDirectory() as tmp:
        fixed_pdf = Path(tmp) / "fixed.pdf"
        fixes, unknown = fix_pdf(PDF, fixed_pdf)
        old_full, new_full = pdftotext(PDF), pdftotext(fixed_pdf)
    allowed = {(core(o), core(n)) for _, _, o, n in fixes if core(o.replace("\x00", ""))}
    # Only symbols may be inserted where the old CMap dropped a glyph; letters
    # from dropped ligatures are left alone rather than guessed into place.
    restored = {c for _, _, o, n in fixes if not core(o.replace("\x00", "")) for c in core(n)
                if not (c.isascii() and c.isalnum())}
    ops = align(old_full, new_full)
    inserted = [False] * len(new_full)
    for tag, i1, i2, j1, j2 in ops:
        if tag != "equal":
            for j in range(j1, j2):
                inserted[j] = True
    locate = mapper(ops)

    doc = json.loads((OLD / "documents.jsonl").read_text().splitlines()[0])
    methods, samples, edits = collections.Counter(), [], collections.Counter()
    cursor = 0
    for unit in doc["units"]:
        if not unit["unit_id"].startswith(PREFIX):
            continue
        location = unit["location"]["description"]
        unit["location"]["description"] = re.sub(r"(?<=[A-Za-z])↵", "ff", location)
        old = unit["text"]
        if old.lstrip().startswith("#"):
            # Headings are set in text fonts, where the wrong CMap only broke the ff ligature.
            new = re.sub(r"(?<=[A-Za-z])↵", "ff", old)
            if any(c in "⇡✓⌧⇢⇤⇥⇠⇣⌘◆⇧⌦✏↵" for c in new):
                raise ValueError("unexpected glyph in heading: " + unit["unit_id"])
            if new == old:
                methods["heading_kept"] += 1
                continue
            method = "heading_ff"
            methods[method] += 1
            edits[("↵", "ff")] += old.count("↵")
            unit["text"] = new
            unit["content_hash"] = "sha256:" + hashlib.sha256(new.encode()).hexdigest()
            unit["metadata"] = {**unit.get("metadata", {}), "text_source": "pdftotext-layout-" + method}
            samples.append({"unit_id": unit["unit_id"], "method": method, "old": old, "new": new})
            continue
        start = old_full.find(old, cursor)
        if start < 0:
            raise ValueError("unit not found in original extraction: " + unit["unit_id"])
        cursor = start + len(old)
        a, b = locate(start, "start"), locate(start + len(old), "end")
        # Symbols the old CMap dropped at a unit edge belong to the unit.
        while a > 0 and inserted[a - 1] and not new_full[a - 1].isspace():
            a -= 1
        while b < len(new_full) and inserted[b] and not new_full[b].isspace():
            b += 1
        new = new_full[a:b]
        if new[:1].isspace() and not old[:1].isspace() or new[-1:].isspace() and not old[-1:].isspace():
            new = new.strip()
        method = "fontfix_span"
        if letters(new) != letters(old):
            # Restored glyphs regrouped formula lines across this unit's edges:
            # keep the old text and layout, fix glyphs in place.
            window = new_full[max(0, a - PATCH_MARGIN):b + PATCH_MARGIN]
            new, _ = patch(old, window, allowed, restored)
            method = "fontfix_patch"
        if letters(new) != letters(old):
            raise ValueError("letters changed: " + unit["unit_id"])
        if new == old:
            methods["unchanged"] += 1
            continue
        methods[method] += 1
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
            if tag != "equal":
                edits[(old[i1:i2], new[j1:j2])] += 1
        unit["text"] = new
        unit["content_hash"] = "sha256:" + hashlib.sha256(new.encode()).hexdigest()
        unit["metadata"] = {**unit.get("metadata", {}), "text_source": "pdftotext-layout-" + method}
        samples.append({"unit_id": unit["unit_id"], "method": method, "old": old, "new": new})

    doc["metadata"] = {**doc["metadata"],
                       "text_extractor": "pdftotext -layout on PDF with ToUnicode rebuilt from glyph names (S2 units)",
                       "previous_content_hash": doc["content_hash"]}
    doc["content_hash"] = "sha256:" + hashlib.sha256(
        "\n".join(u["content_hash"] for u in doc["units"]).encode()).hexdigest()
    NEW.mkdir(parents=True, exist_ok=True)
    shutil.copy2(OLD / "rubric.json", NEW / "rubric.json")
    probe_fixes = {name: fix_probes(OLD / name, NEW / name)
                   for name in ("fact_probes-reviewed.jsonl", "qa_probes-reviewed.jsonl")}
    bench = json.loads((OLD / "benchmark.json").read_text())
    # Submissions pin benchmark_id; the source version lives in metadata and the benchmark hash.
    bench["metadata"] = {**bench["metadata"],
                         "source_text": "fontfix-rebuild-20260926; unit IDs unchanged"}
    (NEW / "benchmark.json").write_text(json.dumps(bench, ensure_ascii=False, indent=2) + "\n")
    (NEW / "documents.jsonl").write_text(json.dumps(doc, ensure_ascii=False) + "\n")

    report = {
        "units": sum(methods.values()),
        "methods": dict(methods),
        "cmap_fixes": [{"font": f, "glyph": g, "old": o, "new": n, "fonts": c}
                       for (f, g, o, n), c in sorted(fixes.items())],
        "unmapped_glyphs": [{"font": f, "glyph": g, "fonts": c} for (f, g), c in sorted(unknown.items())],
        "probe_fixes": probe_fixes,
        "unit_edits": [{"old": o, "new": n, "count": c} for (o, n), c in edits.most_common()],
        "document_content_hash": doc["content_hash"],
    }
    (OUT / "REBUILD.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    (OUT / "changes.jsonl").write_text("".join(json.dumps(s, ensure_ascii=False) + "\n" for s in samples))
    print(json.dumps({k: report[k] for k in ("units", "methods", "document_content_hash")},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
