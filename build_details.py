from enrich_sources import clean,name
import json,re,pathlib,unicodedata,collections,sys
sys.stdout.reconfigure(encoding='utf-8')
P=pathlib.Path;raw=json.loads(P('.sites-runtime/source-facts.json').read_text(encoding='utf-8'));catalog=json.loads(P('dist/herbs.json').read_text(encoding='utf-8'));formulas=json.loads(P('.sites-runtime/formula-facts.json').read_text(encoding='utf-8'))
if P('.sites-runtime/last-candidates.json').exists():
    known={r['url'] for r in raw['oasis']}
    raw['oasis'] += [r for r in json.loads(P('.sites-runtime/last-candidates.json').read_text(encoding='utf-8')) if r['url'] not in known]
health={x['name']:x for x in raw['health']};oasis={x['name']:x for x in raw['oasis']}
# A parent page may contain separately named official entries (e.g. 감초가루).
# Index these exact subheadings, without inheriting the parent drug's properties.
for parent in raw['oasis']:
    for entry in parent['compendia']:
        subname=name(entry['reference'].split('[출전')[0].strip())
        if subname not in oasis:
            oasis[subname]={'name':subname,'url':parent['url'],'compendia':[entry],'toxic':False,'encyclopedia':[]}
        elif oasis[subname].get('url')==parent['url'] and oasis[subname] is not parent and entry not in oasis[subname]['compendia']:
            oasis[subname]['compendia'].append(entry)
# Explicitly verified KHP synonym, not a fuzzy name match.
if '호프' in oasis:
    hop=oasis['호프'];oasis['홉']={**hop,'compendia':[c for c in hop['compendia'] if c.get('이명')=='홉'],'encyclopedia':[]}
def ref(c):
    m=re.search(r'\[출전\s*:\s*(.*?)\]',c['reference'],re.S)
    return re.sub(r'\s+',' ',m[1]) if m else c['reference']
def notes(s):return {k.strip():v.strip() for k,v in re.findall(r'\[([^\]]+)\]\s*([^\[]*)',s,re.S)}
def norm(s):return unicodedata.normalize('NFKC',s)
def dose(s):
    # Keep full reference dose including qualifications. No recomputation or inferred frequency.
    return s.strip() if 0<len(s.strip())<350 else ''
def terms(s):
    # Short conventional terms, exclude therapeutic essays and sentences.
    lines=re.split(r'[\n;；]',s)
    out=[]
    for l in lines:
        l=re.split(r'\s*[-–—]\s*',l)[0].strip()
        if l and len(l)<110:out.append(l)
    return out[:6]
for r in catalog:
    n=r['name'];d={'sources':[{'id':'nifds','label':'식약처 · 생약종합정보','url':r['source']}],'origins':[],'natures':[],'effects':[],'indications':[],'doses':[],'preparations':[],'cautions':[],'formulas':[],'aliases':[],'images':[],'updated':'2026-09-14','reviewer':'전문 검토 전'}
    h=health.get(n);o=oasis.get(n)
    if o:
        d['sources'].append({'id':'oasis','label':'한국한의학연구원 · 한약기원사전','url':o['url']})
        comps=[c for c in o['compendia'] if name(c['reference'].split('[출전')[0].strip())==n or (n=='홉' and c.get('이명')=='홉')]
        # Domestic definition first; keep each foreign compendium's metadata attached.
        comps.sort(key=lambda c:0 if ref(c).startswith(('KP ','KHP')) else 1)
        for c in comps:
            reference=ref(c);note=notes(c.get('비고',''));origin=c.get('기원','');domestic=reference.startswith(('KP ','KHP'))
            d['origins'].append({'value':re.sub(r'^(이 약은|본품은|이 약재는)\s*','',origin),'reference':reference,'source':'oasis','latin':c.get('생약명',''),'english':c.get('영문명',''),'taxa':c.get('_taxa',[])})
            if domestic or not r.get('latin'):r['latin']=c.get('생약명',r.get('latin',''));r['english']=c.get('영문명',r.get('english',''))
            if c.get('이명'):d['aliases'].append({'value':c['이명'],'reference':reference,'source':'oasis'})
            nature=' / '.join(note.get(k,'') for k in ['성미','귀경','성미와 귀경'] if note.get(k))
            if nature:d['natures'].append({'value':nature,'reference':reference,'source':'oasis'})
            for group,keys in [('doses',['용법·용량','용법용량','용량','용법 및 용량']),('cautions',['주의','주의사항','금기','금기증'])]:
                for k in keys:
                    v=note.get(k,'')
                    if v and len(v)<350:d[group].append({'value':v,'reference':reference,'source':'oasis'})
            for k in ['효능','용도분류']:
                if note.get(k):d['effects'].append({'value':note[k],'reference':reference,'source':'oasis'})
            if note.get('주치'):d['indications'].append({'value':note['주치'],'reference':reference,'source':'oasis'})
            for k in ['포제','제법','채취','저장','저장법','보관']:
                if note.get(k) and len(note[k])<500:d['preparations'].append({'label':k,'value':note[k],'reference':reference,'source':'oasis'})
        if o['toxic']:d['cautions'].insert(0,{'value':'한약기원사전에서 독성주의한약재로 표시한 항목입니다. 원문 표시는 해당 사전의 기준에 따릅니다. 자가 사용하지 마세요.','source':'oasis','reference':'독성주의 표시'})
        if o['encyclopedia']:d['sources'].append({'id':'encyclopedia','label':'OASIS · 약재백과','url':o['encyclopedia'][0]})
    if h:
        f=h['fields'];d['sources'].append({'id':'health','label':'약학정보원 · 본초정보','url':h['url']})
        if not r.get('latin'):r['latin']=f.get('생약명','')
        if not d['origins'] and f.get('基源'):d['origins'].append({'value':f['基源'],'reference':'약학정보원','source':'health','latin':f.get('생약명',''),'english':''})
        d['classification']=f.get('分類','')
        for group,key in [('natures','性味·歸經'),('doses','用量·用法'),('cautions','禁忌')]:
            v=f.get(key,'')
            if v and len(v)<350:d[group].append({'value':v,'reference':'약학정보원','source':'health'})
        if not d['effects']:
            for t in terms(f.get('效能','')):d['effects'].append({'value':t,'reference':'약학정보원 · 전통 효능','source':'health'})
        # Do not combine claims about related medicinal parts into this entry.
        if not d['indications'] and f.get('主治') and n!='괴화' and len(f['主治'])<200:d['indications'].append({'value':f['主治'],'reference':'약학정보원 · 전통 주치','source':'health'})
        if f.get('修治') and len(f['修治'])<200:d['preparations'].append({'label':'수치·포제','value':f['修治'],'reference':'약학정보원','source':'health'})
        for label in h['formulas']:d['formulas'].append({'name':label,'url':h['url'],'reference':'약학정보원 · 해당 약재의 처방 예시'})
    for f in formulas:
        # Match whole Korean ingredient tokens, not substrings (e.g. 지황 != 숙지황).
        if re.search(r'(?<![가-힣])'+re.escape(n)+r'(?![가-힣])',f['composition']):
            d['formulas'].append({'name':f['name'],'url':f['url'],'reference':f['reference'],'match':'구성 약재명 일치 · 포제·배합은 처방 원문 확인'})
    bangyak_path=P('.sites-runtime/bangyak-facts.json')
    if bangyak_path.exists():
        for f in json.loads(bangyak_path.read_text(encoding='utf-8')):
            comp=norm(f['composition']);hanja=norm(r['hanja'])
            # Exclude subtraction/derived formulations rather than interpreting them.
            if '去' in comp:continue
            korean=re.search(r'(?<![가-힣])'+re.escape(n)+r'(?![가-힣])',comp)
            chinese=hanja and re.search(r'(?<![\u3400-\u9fff])'+re.escape(hanja)+r'(?=$|[\s,，.（(0-9]|炒|炙|炭)',comp)
            if korean or chinese:d['formulas'].append({'name':f['name'],'url':f['url'],'reference':f['reference'],'match':'방약합편 구성 약재명 대조'})
    if d['origins']:
        first=d['origins'][0]['value'];d['taxa']=[x for x in d['origins'][0].get('taxa',[]) if ' ' in x] or [x for x in dict.fromkeys(re.findall(r'\b[A-Z][a-z]+ [a-z][a-z-]+\b',first)) if x.split()[1] not in ['et','var','subsp','f']]
        fam=re.search(r'([가-힣]+과)\s+([A-Z][a-z]+)',first);d['family']=fam[0] if fam else ''
        part=re.search(r'의\s+([^\n.]{1,100}?)(?:이다|를 말린|을 말린)',first);d['part']=part[1] if part else ''
    r['detail']=d
# Curated, source-checked Sophora facts. Bud vs flower distinction is retained.
r=next(x for x in catalog if x['id']=='sophorae-flos');d=r['detail'];d['part']='꽃봉오리와 꽃';d['classification']='양혈지혈약(涼血止血藥)'
d['sources'].append({'id':'processing','label':'OASIS · 괴화 생산가공','url':'https://oasis.kiom.re.kr/oasis/herb/monoDetailView_M08.jsp?idx=44&tab=8'})
d['preparations']=[{'label':'채취·기초가공','value':'여름에 수확하며, 개화한 꽃은 괴화, 피기 전 꽃봉오리는 괴미로 구분합니다. 수확 후 건조하고 가지·꽃대·이물을 골라냅니다.','reference':'OASIS 약재백과','source':'processing'},{'label':'포제 형태','value':'선별한 생품 외에 볶아서 가공한 초괴화, 탄화 가공한 괴화탄이 문헌에 구분되어 있습니다. 포제품마다 성상이 달라 동일한 형태로 취급하지 않습니다.','reference':'OASIS 약재백과 · 포제 항목 요약','source':'processing'}]+[x for x in d['preparations'] if x['label'] in ['저장','저장법','보관']]
for c in d['cautions']:
    if c['source']=='health':c['value']='약학정보원은 허한(虛寒)에 따른 설사를 금기 항목으로 제시합니다. 개인의 해당 여부는 한의사의 판단이 필요합니다.'
d['aliases']=[{'value':'괴미(槐米)는 꽃봉오리를 구분하는 이름으로, 개화한 꽃과 동일한 성상으로 취급하지 않습니다.','source':'oasis','reference':'KP 12 · 약용 부위 구분'}]
d['sources'].append({'id':'mfds-pdf','label':'식약처 · 괴화 규격 자료','url':'https://www.mfds.go.kr/files/upload/herbmed/photo_data/KP_24.pdf'})
P('dist/herbs.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
counts={k:sum(bool(r['detail'].get(k)) for r in catalog) for k in ['origins','natures','effects','indications','doses','preparations','cautions','formulas']}
counts['total']=len(catalog);counts['enriched']=sum(len(r['detail']['sources'])>1 for r in catalog)
P('dist/data-status.json').write_text(json.dumps(counts,ensure_ascii=False,indent=2),encoding='utf-8');print(counts)
