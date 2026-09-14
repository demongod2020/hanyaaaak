from enrich_sources import *
raw=json.loads(pathlib.Path('.sites-runtime/source-facts.json').read_text(encoding='utf-8'))
def collect(r):
    url=r['encyclopedia'][0];s=fetch(url);result={'name':r['name'],'url':url}
    m=re.search(r'<h4[^>]*>약재 이명</h4>\s*<p>(.*?)</p>',s,re.S)
    if m:result['aliases']=clean(m[1])
    return result
items=[r for r in raw['oasis'] if r['encyclopedia']]
out,errors=run(collect,items,'names')
pathlib.Path('.sites-runtime/name-facts.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8');print('names',len(out),'errors',len(errors))
