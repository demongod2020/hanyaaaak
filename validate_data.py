import json,pathlib
rs=json.loads(pathlib.Path('dist/herbs.json').read_text(encoding='utf-8'));assert len(rs)==601;assert len({r['id'] for r in rs})==601
for r in rs:
    d=r['detail'];sources={s['id'] for s in d['sources']};assert len(sources)==len(d['sources']),r['name']
    for k in ['origins','natures','effects','indications','doses','preparations','cautions','aliases']:
        for x in d[k]:assert x['source'] in sources,(r['name'],k)
    for i in d['images']:assert pathlib.Path('dist',i['path']).is_file()
byname={r['name']:r for r in rs}
assert byname['감초가루']['detail']['origins'] and not byname['감초가루']['detail']['doses']
assert byname['대황초탄']['detail']['origins'] and not byname['대황초탄']['detail']['effects']
assert any('ChP 2025' in x['reference'] and '5~10g' in x['value'] for x in byname['괴화']['detail']['doses'])
assert any(x['source']=='health' and '9∼15g' in x['value'] for x in byname['괴화']['detail']['doses'])
assert len(byname['괴화']['detail']['formulas'])==3
assert not any(i['type']=='slice' for i in byname['괴화']['detail']['images'])
assert len(byname['홉']['detail']['origins'])==1 and 'Humulus lupulus' in byname['홉']['detail']['origins'][0]['value']
print('Validated 601 record IDs, provenance, assets, processed-drug separation and source-specific doses.')
