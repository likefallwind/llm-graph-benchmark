from pathlib import Path
import importlib.util,json,sys,copy
import pytest
ROOT=Path('/home/likefallwind/code/llm-graph-benchmark');STUDY=ROOT/'studies/d2l-consolidated-reeval-20260922'
sys.path.insert(0,str(STUDY))
spec=importlib.util.spec_from_file_location('consolidated_eval',STUDY/'evaluate.py');ev=importlib.util.module_from_spec(spec);spec.loader.exec_module(ev)
def task(metric='entity_typing'):
 return {'metric':metric,'payload':{'metric':metric,'target':{'name':'A','types':['方法','算法']},'segments':[{'id':'s0','text':'方法'},{'id':'s1','text':'算法'}],'sources':[{'id':'P1','text':'A是一种算法方法。'}]}}
def response(t,verdicts=('supported','supported')):
 v={'target_copy':t['payload']['target'],'items':[{'segment_id':'s'+str(i),'verdict':v,'evidence':['P1'],'reason':'具体依据'} for i,v in enumerate(verdicts)]}
 return {'choices':[{'message':{'content':json.dumps(v)}}]}
def mutate_response(r,func):
 v=json.loads(r['choices'][0]['message']['content']);func(v);r['choices'][0]['message']['content']=json.dumps(v);return r

def test_complete_supported():
 t=task();v=ev.parse(response(t),t);assert v['label']=='correct';assert v['items'][0]['source_quotes'][0]['text']=='A是一种算法方法。'
def test_one_bad_type_not_averaged():
 t=task();assert ev.parse(response(t,('supported','contradicted')),t)['label']=='incorrect'
def test_unsupported_type_is_uncertain():
 t=task();assert ev.parse(response(t,('supported','not_established')),t)['label']=='uncertain'
def test_unsupported_definition_not_supported():
 t=task('entity_definition');assert ev.parse(response(t,('supported','not_established')),t)['label']=='not_supported'
def test_qa_reference_not_source():
 t=task('book_qa');r=response(t);r=mutate_response(r,lambda v:v['items'][0].update(evidence=['reference_answer']))
 with pytest.raises(ValueError):ev.parse(r,t)
@pytest.mark.parametrize('bad',['target','missing','duplicate','unknown_source','no_evidence'])
def test_schema_failures(bad):
 t=task();r=response(t)
 def change(v):
  if bad=='target':v['target_copy']['name']='B'
  elif bad=='missing':v['items'].pop()
  elif bad=='duplicate':v['items'][1]['segment_id']='s0'
  elif bad=='unknown_source':v['items'][0]['evidence']=['P999']
  elif bad=='no_evidence':v['items'][0]['evidence']=[]
 r=mutate_response(r,change)
 with pytest.raises(ValueError):ev.parse(r,t)

def ledger_value(verdict='supported',alignment='asserted',coverage='complete'):
 return {'label':'correct','claims':[{'verdict':verdict}],'checks':{'participants':{'verdict':'supported'},'claim_coverage':{'verdict':'supported'}},'alignment':{'claims':[{'index':0,'status':alignment}],'coverage':coverage}}
def test_assertion_unsupported_actual_claim():assert ev.assertion_value(ledger_value('not_established'))['label']=='not_supported'
def test_assertion_extra_explanation_not_target_error():assert ev.assertion_value(ledger_value('contradicted','contains_target'))['label']=='uncertain'
def test_assertion_missing_coverage_not_pass():assert ev.assertion_value(ledger_value(coverage='incomplete'))['label']=='uncertain'
def test_assertion_preserves_truth_label():assert ev.assertion_value(ledger_value())['source_truth_label']=='correct'
def test_six_slot_transport():assert ev.transport.REQUEST_CONCURRENCY==6

def test_long_source_scan_preserves_all_units(tmp_path):
 t=task('alias_identity');t['id']='long';t['requires_source_shards']=True
 t['payload']['candidate_context']={};t['payload']['sources']=[{'id':'P'+str(i),'text':str(i)+'x'*65000} for i in range(10)]
 class Client:
  calls=0
  def complete(self,msgs,max_tokens,validator):
   self.calls+=1;p=json.loads(msgs[1]['content']);v={'target_copy':p['target'],'items':[{'segment_id':s['id'],'verdict':'supported','evidence':[p['sources'][0]['id']],'reason':'来自此段'} for s in p['segments']]};r={'choices':[{'message':{'content':json.dumps(v)}}]};validator(r);return r
 c=Client();v=ev.generic_judgment(c,t,tmp_path);assert v['source_sharding']['source_units_scanned']==10;assert v['source_sharding']['shards']>=3
 covered=[i for p in (tmp_path/'source-shards'/'long').glob('*.json') for i in json.loads(p.read_text())['source_ids']]
 assert len(covered)==10 and set(covered)=={x['id'] for x in t['payload']['sources']}
 count=c.calls;ev.generic_judgment(c,t,tmp_path);assert c.calls==count+1

def test_fenced_json_and_encoded_target_only_format():
 t=task();r=response(t);v=json.loads(r['choices'][0]['message']['content']);v['target_copy']=json.dumps(v['target_copy']);r['choices'][0]['message']['content']='```json\n'+json.dumps(v)+'\n```'
 assert ev.parse(r,t)['label']=='correct'
def test_free_text_target_copy_still_rejected():
 t=task();r=mutate_response(response(t),lambda v:v.update(target_copy='A的类型是方法和算法'))
 with pytest.raises(ValueError):ev.parse(r,t)

def test_qa_exact_answer_echo_records_partial_echo():
 t=task('book_qa');t['payload']['target']={'question':'A做什么？','reference_answer':'A不抑制B。'}
 r=mutate_response(response(t),lambda v:v.update(target_copy='A不抑制B。'))
 v=ev.parse(r,t);assert v['verified_target_fields']==['reference_answer'];assert v['target_copy']=='A不抑制B。'
 r=mutate_response(response(t),lambda v:v.update(target_copy='A抑制B。'))
 with pytest.raises(ValueError):ev.parse(r,t)
def test_single_entity_name_exact_scalar():
 t=task('entity_correctness');t['payload']['target']={'name':'A'};r=mutate_response(response(t),lambda v:v.update(target_copy='A'));assert ev.parse(r,t)['label']=='correct'
def test_qa_altered_question_object_rejected():
 t=task('book_qa');t['payload']['target']={'question':'A做什么？','reference_answer':'A不抑制B。'}
 r=mutate_response(response(t),lambda v:v['target_copy'].update(question='C做什么？'))
 with pytest.raises(ValueError):ev.parse(r,t)
