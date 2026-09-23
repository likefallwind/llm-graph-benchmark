from pathlib import Path
p=Path('/home/likefallwind/code/llm-graph-benchmark/studies/d2l-consolidated-reeval-20260922/evaluate.py');s=p.read_text();helper='''
def parse_granularity(response):
 raw=response['choices'][0]['message']['content'].strip();plain=re.sub(r'^```(?:json)?\\s*|\\s*```$', '', raw)
 copied=copy.deepcopy(response);copied['choices'][0]['message']['content']=plain
 value=granularity.parse(copied)
 if plain!=raw:value['format_repair']='stripped_json_fence'
 return value

''';s=s.replace('\ndef assertion_value(v):','\n'+helper+'def assertion_value(v):');s=s.replace('validator=granularity.parse);r.update(status=\'done\',value=granularity.parse(response))','validator=parse_granularity);r.update(status=\'done\',value=parse_granularity(response))');p.write_text(s)
