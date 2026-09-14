"""Check source preservation, numbers, homographs, and Korean display coverage."""
import json
import re
import subprocess
from pathlib import Path

root=Path(__file__).parent
data=json.loads((root/'dist/herbs.json').read_text(encoding='utf-8'))
before=json.loads(subprocess.check_output(['git','-c',f'safe.directory={root.as_posix()}','show','3b7b8e091feaf65f19ba11ec0943a9d636862cd7:dist/herbs.json'],cwd=root).decode('utf-8'))
ADDITIONS={'ko','glosses','koLabel','koReference','koName','koClassification'}
def source_only(x):
    if isinstance(x,dict): return {k:source_only(v) for k,v in x.items() if k not in ADDITIONS}
    if isinstance(x,list): return [source_only(v) for v in x]
    return x
assert source_only(data)==before,'An original source fact was changed'
for h in data:
    for key in ['natures','effects','indications','doses','cautions']:
        for x in h['detail'][key]:
            assert x['ko'].strip()
            assert not re.search(r'[\u3400-\u9fff\uf900-\ufaff]',x['ko']),(h['name'],key)
            if key=='doses':
                assert re.findall(r'\d+(?:\.\d+)?',x['value'])==re.findall(r'\d+(?:\.\d+)?',x['ko']),h['name']
buja=next(h for h in data if h['name']=='부자')
for x in buja['detail']['effects']:
    assert all(g['term']!='구역' for g in x['glosses']), '救逆 must not mean nausea'
sophora=next(h for h in data if h['name']=='괴화')
assert '쓴맛, 약간 찬 성질' in sophora['detail']['natures'][0]['ko']
assert any(g['term']=='양혈지혈' for g in sophora['detail']['effects'][0]['glosses'])
galgeun=next(h for h in data if h['name']=='갈근')
assert '적합하지 않다' in galgeun['detail']['cautions'][0]['ko']
print('601 source records unchanged; all descriptive Han text has Korean display; dose numbers and homograph checks passed.')
