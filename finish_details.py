import pathlib,json
P=pathlib.Path;p=P('dist/herbs.json');records=json.loads(p.read_text(encoding='utf-8'));d=next(r for r in records if r['id']=='sophorae-flos')['detail']
d['sources']=[s for s in d['sources'] if not s['id'].startswith('image')]
for r in records:r['detail']['aliases']=[x for x in r['detail']['aliases'] if x['source']!='encyclopedia']
d['images']=[{'type':'plant','path':'sophora-plant.jpg','caption':'회화나무 · 꽃과 잎','note':'촬영지: 충북 청주시 미동산수목원. 약재 생산지를 의미하지 않습니다.','credit':'Choi Goya · 한국한의학연구원','license':'공공누리 제1유형 · 출처표시','source':'https://oasis.kiom.re.kr/herblib/hminfo/mdhrpt/mdhrptDetail.do?mdhrpt_sn=3461'}, {'type':'herb','path':'sophora-herb.jpg','caption':'괴화 · 약재 표본','note':'원문 자원번호 2-17-0361. 꽃봉오리를 포함한 약재 표본입니다.','credit':'한국한의학연구원','license':'공공누리 제1유형 · 출처표시','source':'https://oasis.kiom.re.kr/herblib/hminfo/mdhrpt/mdhrptDetail.do?mdhrpt_sn=2050'}, {'type':'herb','path':'sophora-buds.jpg','caption':'괴미 · 꽃봉오리 생품','note':'원문에서 괴미·생품으로 구분한 표본입니다.','credit':'한국한의학연구원','license':'공공누리 제1유형 · 출처표시','source':'https://oasis.kiom.re.kr/herblib/hminfo/mdhrpt/mdhrptDetail.do?mdhrpt_sn=1203'}]
for i,image in enumerate(d['images']):d['sources'].append({'id':'image'+str(i),'label':image['credit']+' · '+image['caption'],'url':image['source']})
names=P('.sites-runtime/name-facts.json')
if names.exists():
    mapping={r['name']:r for r in json.loads(names.read_text(encoding='utf-8'))}
    for r in records:
        x=mapping.get(r['name'])
        if x and x.get('aliases'):r['detail']['aliases'].append({'value':x['aliases'],'source':'encyclopedia','reference':'OASIS · 약재 이명'})
p.write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
counts={k:sum(bool(r['detail'].get(k)) for r in records) for k in ['origins','natures','effects','indications','doses','preparations','cautions','formulas','aliases','images']}
counts['total']=len(records);counts['enriched']=sum(len(r['detail']['sources'])>1 for r in records)
P('dist/data-status.json').write_text(json.dumps(counts,ensure_ascii=False,indent=2),encoding='utf-8')
p=P('dist/index.html');s=p.read_text(encoding='utf-8')
if 'src="details.js"' not in s:s=s.replace('<script src="app-v2.js"></script>','<script src="app-v2.js"></script><script src="details.js"></script>')
import re
s=re.sub(r'식약처 목록 601건 · 상세 출처 연결 \d+건\.',f"식약처 목록 601건 · 상세 출처 연결 {counts['enriched']}건.",s);p.write_text(s,encoding='utf-8')
p=P('dist/app-v2.js');s=p.read_text(encoding='utf-8').replace("if(id&&records.some(r=>r.id===id))openHerb(id)","openHerb(id&&records.some(r=>r.id===id)?id:'sophorae-flos')");s=s.replace('[r.name,r.hanja,r.english,r.latin,r.plant]','[r.name,r.hanja,r.english,r.latin,r.plant,...(r.detail?.aliases||[]).map(a=>a.value)]');p.write_text(s,encoding='utf-8')
