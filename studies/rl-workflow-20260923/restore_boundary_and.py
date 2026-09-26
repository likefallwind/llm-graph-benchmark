"""Restore only a missing boundary 'and' from source; never change judgments."""
import copy
import re

def restore_boundary_and(description, value):
    result=copy.deepcopy(value)
    positions=[i for i,c in enumerate(description) if not c.isspace()]
    source=''.join(description[i] for i in positions)
    cursor=0; edits=[]
    for index,row in enumerate(result['claims']):
        text=''.join(row['text'].split());start=source.find(text,cursor)
        if not text or start<0:raise ValueError('Changed or reordered text')
        original_start=positions[cursor] if cursor<len(positions) else len(description)
        gap=description[original_start:positions[start]]
        # Only an explicitly present coordinating word between verbatim spans.
        # Never discard not/or/but/conditions or invent any source text.
        match=re.fullmatch(r'[\s,;:，；：。.—]*\b(and)\s+',gap)
        if cursor and match:
            prefix=gap[match.start(1):]
            before=row['text'];row['text']=prefix+before
            edits.append({'claim_index':index,'before':before,'after':row['text'],'source_gap':gap})
        cursor=start+len(text)
    return result,edits
