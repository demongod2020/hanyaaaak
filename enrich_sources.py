"""Collect public reference facts; cache source pages outside published assets.
Exact name matches only. Keep each pharmacopoeia separately, never average doses.
Long application essays and pharmacological claims are not republished.
"""
import concurrent.futures as cf, subprocess, re, html, json, pathlib, hashlib, time, sys
sys.stdout.reconfigure(encoding='utf-8')
CACHE=pathlib.Path('.sites-runtime/source-cache');CACHE.mkdir(parents=True,exist_ok=True)
def fetch(url):
    p=CACHE/(hashlib.sha256(url.encode()).hexdigest()+'.html')
    if p.exists(): return p.read_text(encoding='utf-8')
    raw=subprocess.check_output(['curl.exe','-f','-sS','-L','--max-time','45','--retry','2',url])
    try: text=raw.decode('utf-8')
    except UnicodeDecodeError:text=raw.decode('cp949',errors='replace')
    if 'Page Not Found' in text:raise ValueError('Missing page '+url)
    p.write_text(text,encoding='utf-8');time.sleep(.12);return text
def clean(s):
    s=re.sub(r'<(script|style)\b.*?</\1>','',s,flags=re.S|re.I)
    s=re.sub(r'<br\s*/?>','\n',s,flags=re.I)
    return re.sub(r'[ \t\r\f\v]+',' ',html.unescape(re.sub('<[^>]+>','',s))).strip()
def fields(s):
    return {re.sub(r'\s+','',clean(k)):clean(v) for k,v in re.findall(r'<th\b[^>]*>(.*?)</th>\s*(?:<!--.*?-->\s*)?<td\b[^>]*>(.*?)</td>',s,re.S|re.I)}
def name(s):return re.split('[（(]',clean(s))[0].strip()
def health_list(page):
    url=f'https://health.kr/researchInfo/herbalMedicine1.asp?inputField=&HVsearchTerm=a&HVpaging_value={page}&HVsetLine=100&HVsearchMode=&HV_Scroll=1'
    s=fetch(url);result={}
    for idx,n in re.findall(r"href=['\"]herbalMedicine1_detail.asp\?idx=(\d+)['\"]>(.*?)</a>",s,re.S):
        if idx not in result:result[idx]=name(n)
    return result
def oasis_list(page):
    s=fetch(f'https://oasis.kiom.re.kr/herblib/hminfo/hbmcod/hbmcodList.do?search_yn=y&row=100&page={page}')
    result={}
    for idx,row in re.findall(r'<tr onclick="fn_goHbmcodDetail\(\'(\d+)\'\)">(.*?)</tr>',s,re.S):
        cells=re.findall(r'<td\b[^>]*>(.*?)</td>',row,re.S)
        if len(cells)>1:result[idx]=name(cells[1])
    return result
def health_detail(pair):
    idx,n=pair;url=f'https://health.kr/researchInfo/herbalMedicine1_detail.asp?idx={idx}';s=fetch(url);f=fields(s)
    # Store only compact reference facts, not the original essays.
    result={'name':n,'url':url,'fields':{}}
    for k in ['생약명','分類','基源','性味·歸經','效能','主治','用量·用法','禁忌','修治']:
        v=f.get(k,'')
        if v:result['fields'][k]=v
    result['formulas']=[]
    for line in f.get('處方例','').split('\n'):
        label=re.split(r'[:：;；]',line)[0].strip()
        if label and len(label)<110:result['formulas'].append(label)
    return result
def oasis_detail(pair):
    idx,n=pair;url=f'https://oasis.kiom.re.kr/herblib/hminfo/hbmcod/hbmcodDetail.do?drgnm_sn={idx}';s=fetch(url)
    result={'name':n,'url':url,'compendia':[]}
    for head,body in re.findall(r'<div class="compendia-item">(.*?)</div>\s*<table[^>]*>(.*?)</table>',s,re.S):
        f=fields(body);title=clean(head);f['reference']=title
        origin_html=re.search(r'<th[^>]*>기원</th>\s*<td[^>]*>(.*?)</td>',body,re.S)
        if origin_html:f['_taxa']=list(dict.fromkeys(clean(x) for x in re.findall(r'<i\b[^>]*>(.*?)</i>',origin_html[1],re.S|re.I)))
        if f.get('기원'):result['compendia'].append(f)
    result['toxic']='독성주의한약재' in clean(re.sub(r'<script.*?</script>','',s,flags=re.S))
    result['encyclopedia']=re.findall(r'href="(https://oasis.kiom.re.kr/oasis/herb/monoDetailView_M01.jsp\?idx=\d+)"',s)
    return result
def run(fn,items,label):
    out=[];errors=[]
    with cf.ThreadPoolExecutor(max_workers=3) as pool:
        futures={pool.submit(fn,x):x for x in items}
        for i,future in enumerate(cf.as_completed(futures),1):
            try:out.append(future.result())
            except Exception as e:errors.append(str(e))
            if i%50==0:print(label,i,'/',len(items),flush=True)
    return out,errors
if __name__=='__main__':
    catalog=json.loads(pathlib.Path('dist/herbs.json').read_text(encoding='utf-8'));names={r['name'] for r in catalog}
    hl={};ol={}
    for d in run(health_list,list(range(1,5)),'health index')[0]:hl.update(d)
    for d in run(oasis_list,list(range(1,12)),'oasis index')[0]:ol.update(d)
    print('indexes',len(hl),len(ol),'matching',sum(n in names for n in hl.values()),sum(n in names for n in ol.values()),flush=True)
    health,he=run(health_detail,[(i,n) for i,n in hl.items() if n in names],'health')
    oasis,oe=run(oasis_detail,[(i,n) for i,n in ol.items() if n in names],'oasis')
    pathlib.Path('.sites-runtime/source-facts.json').write_text(json.dumps({'health':health,'oasis':oasis,'errors':he+oe},ensure_ascii=False,indent=2),encoding='utf-8')
    print('collected',len(health),len(oasis),'errors',he+oe,flush=True)
