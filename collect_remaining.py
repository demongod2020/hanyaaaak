from enrich_sources import *
from urllib.parse import quote
path=pathlib.Path('.sites-runtime/source-facts.json');raw=json.loads(path.read_text(encoding='utf-8'));rs=json.loads(pathlib.Path('dist/herbs.json').read_text(encoding='utf-8'));missing=[r['name'] for r in rs if not r['detail']['origins']]
def search(n):
    cache=CACHE/('search-'+hashlib.sha256(n.encode()).hexdigest()+'.html')
    if cache.exists():s=cache.read_text(encoding='utf-8')
    else:
        s=subprocess.check_output(['curl.exe','-f','-sS','-L','--max-time','30','--data-urlencode','search_text='+n,'--data','search_yn=y&row=100&page=1','https://oasis.kiom.re.kr/herblib/hminfo/hbmcod/hbmcodList.do']).decode('utf-8');cache.write_text(s,encoding='utf-8')
    out={}
    for i,row in re.findall(r'<tr onclick="fn_goHbmcodDetail\(\'(\d+)\'\)">(.*?)</tr>',s,re.S):
        cells=re.findall(r'<td\b[^>]*>(.*?)</td>',row,re.S)
        if len(cells)>1:out[i]=name(cells[1])
    return out
idx={}
for x in run(search,missing,'remaining search')[0]:idx.update(x)
known={r['url'].split('=')[-1] for r in raw['oasis']};items=[(i,n) for i,n in idx.items() if i not in known]
out,errors=run(oasis_detail,items,'remaining details');raw['oasis']+=out;raw['errors']+=errors;path.write_text(json.dumps(raw,ensure_ascii=False,indent=2),encoding='utf-8');print('additional source pages',len(out),'errors',errors)
