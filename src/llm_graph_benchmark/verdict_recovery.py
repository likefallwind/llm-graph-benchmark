"""Lossless recovery of unescaped quotes in a terminal JSON reason string.

This is a transport repair only. It cannot create or alter triples or labels.
Invalid structure anywhere before reason, truncated output, and embedded
object/array syntax in reason are deliberately outside the recovery contract.
"""
import json
import re

POLICY = 'terminal-reason-quotes-v1'
FIELDS = {'evaluated_triple', 'edge_label', 'description_label', 'condition_label', 'label'}


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def recover_reason_quotes(content):
    if not isinstance(content, str):
        raise ValueError('content must be text')
    text = re.sub(r'<think>.*?</think>', '', content, flags=re.S).strip()
    if text.startswith('```'):
        if not text.endswith('```'):
            raise ValueError('unclosed code fence')
        text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text).strip()
    try:
        json.loads(text, object_pairs_hook=unique_object)
    except json.JSONDecodeError:
        pass
    else:
        raise ValueError('recovery requires syntactically invalid JSON')
    matches = list(re.finditer(r'"reason"\s*:\s*"', text))
    if len(matches) != 1:
        raise ValueError('expected one terminal reason field')
    match = matches[0]
    end = re.search(r'"\s*}\s*$', text)
    if not end or end.start() < match.end():
        raise ValueError('missing complete terminal reason string')
    prefix = text[:match.end()]
    fields = json.loads(prefix + '"}', object_pairs_hook=unique_object)
    if set(fields) != FIELDS | {'reason'}:
        raise ValueError('unexpected or missing scoring fields')
    raw_reason = text[match.end():end.start()]
    # Refuse ambiguous object/member syntax rather than swallowing extra labels.
    if any(char in raw_reason for char in '{}') or re.search(r'"\s*:', raw_reason):
        raise ValueError('ambiguous structure inside reason')
    repaired = []
    added = 0
    slash_run = 0
    for char in raw_reason:
        if char == '"' and slash_run % 2 == 0:
            repaired.append('\\')
            added += 1
        repaired.append(char)
        slash_run = slash_run + 1 if char == '\\' else 0
    if not added:
        raise ValueError('no unescaped reason quotes to repair')
    corrected = prefix + ''.join(repaired) + text[end.start():]
    row = json.loads(corrected, object_pairs_hook=unique_object)
    if {k: row[k] for k in FIELDS} != {k: fields[k] for k in FIELDS}:
        raise ValueError('scoring fields changed')
    return corrected, {'policy': POLICY, 'inserted_escape_characters': added}
