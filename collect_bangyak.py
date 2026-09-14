from enrich_sources import *
def index(p):
    s=fetch(f'https://health.kr/researchInfo/herbalMedicine3.asp?inputField=&HVsearchTerm=a&HVpaging_value={p}&HVsetLine=100&HVsearchMode=&HV_Scroll=1');out={}
    for i,n in re.findall(r"href=['\"]herbalMedicine3_detail.asp\?idx=(\d+)['\"]>(.*?)</a>",s,re.S):
        if i not in out:out[i]=clean(n)
    return out
idx={}
for d in run(index,list(range(1,7)),'bangyak index')[0]:idx.update(d)
def detail(pair):
    i,n=pair;url='https://health.kr/researchInfo/herbalMedicine3_detail.asp?idx='+i;f=fields(fetch(url))
    return {'name':n,'url':url,'reference':'방약합편 · '+f.get('타입',''),'composition':f.get('造成','')}
out,errors=run(detail,list(idx.items()),'bangyak')
pathlib.Path('.sites-runtime/bangyak-facts.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8');print('bangyak',len(out),'errors',errors)
