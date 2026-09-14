from enrich_sources import *
def detail(pair):
    i,n=pair;url='https://health.kr/researchInfo/herbalMedicine2_detail.asp?idx='+i;f=fields(fetch(url))
    return {'name':n,'url':url,'reference':f.get('出典',''),'composition':f.get('造成','')}
url='https://health.kr/researchInfo/herbalMedicine2.asp?inputField=&HVsearchTerm=a&HVpaging_value=1&HVsetLine=100&HVsearchMode=&HV_Scroll=1'
s=fetch(url);idx={}
for i,n in re.findall(r"href=['\"]herbalMedicine2_detail.asp\?idx=(\d+)['\"]>(.*?)</a>",s,re.S):
    if i not in idx:idx[i]=clean(n)
out,errors=run(detail,list(idx.items()),'formulas')
pathlib.Path('.sites-runtime/formula-facts.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8');print('formulas',len(out),'errors',errors)
