import concurrent.futures, subprocess, re, html, json, pathlib
BASE='https://www.nifds.go.kr/herb/m_442/list.do'
def page(n):
    url=f'{BASE}?itm_seq_1=0&page={n}&srchFr=&srchTo=&srchTp=&srchWord='
    raw=subprocess.check_output(['curl.exe','-f','-sS','-L','--retry','2',url]).decode('utf-8')
    result=[]
    for row in re.findall(r'<tr\b[^>]*>(.*?)</tr>',raw,re.S):
        cells=re.findall(r'<td\b[^>]*>(.*?)</td>',row,re.S)
        if len(cells)!=3 or 'ofcmhbdc' not in row: continue
        clean=lambda s:html.unescape(re.sub('<[^>]+>','',s)).strip()
        label,plant,kind=map(clean,cells)
        name=label.split('(')[0]; hanja=label[len(name):].strip('()')
        result.append(dict(id='sophorae-flos' if name=='괴화' else 'nifds-'+name,name=name,hanja=hanja,plant=plant,category=kind,latin='Sophorae Flos' if name=='괴화' else '',english='Sophora Flower' if name=='괴화' else '',source=url,detailSource=html.unescape(re.search(r'href="([^"]+)"',cells[0])[1]),page=n))
    if len(result)!=(1 if n==61 else 10): raise ValueError(f'Unexpected record count: page {n}, {len(result)}')
    return result
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    rows=[r for result in pool.map(page,range(1,62)) for r in result]
assert len(rows)==601
seen=set()
for i,r in enumerate(rows):
    if r['id'] in seen: r['id']+='-'+str(i)
    seen.add(r['id'])
pathlib.Path('dist/herbs.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print(f'Imported {len(rows)} records from 61 pages')
