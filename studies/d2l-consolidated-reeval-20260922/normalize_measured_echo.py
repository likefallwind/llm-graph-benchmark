from pathlib import Path
p=Path('/home/likefallwind/code/llm-graph-benchmark/studies/d2l-consolidated-reeval-20260922/evaluate.py');s=p.read_text();old="if not isinstance(v,dict) or v.get('target_copy')!=p['target']:raise ValueError('target copy changed')";new="""if not isinstance(v,dict):raise ValueError('response object')
 copied=v.get('target_copy');expected_target=p['target'];matches=copied==expected_target
 v['verified_target_fields']=sorted(expected_target)
 if isinstance(copied,str) and set(expected_target)=={'name'} and copied==expected_target['name']:
  matches=True;v['target_echo_format']='exact_name_scalar'
 elif t['metric']=='book_qa' and isinstance(copied,str) and copied==expected_target['reference_answer']:
  # QA grades these immutable answer segments; the original question stays in the input.
  # Do not pretend the model echoed the question or synthesize a target_copy object.
  matches=True;v['verified_target_fields']=['reference_answer'];v['target_echo_format']='exact_reference_answer_scalar'
 elif isinstance(copied,dict) and set(copied)==set(expected_target)|{'segments'} and copied['segments']==p['segments'] and {k:copied[k] for k in expected_target}==expected_target:
  matches=True;v['target_echo_format']='object_with_identical_segments'
 if not matches:raise ValueError('target copy changed')"""
assert old in s;s=s.replace(old,new);p.write_text(s)
