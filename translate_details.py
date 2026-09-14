"""Add Korean display text without changing collected source facts or dosages.

Unihan is used only for readings, never as a medical translation dictionary.
Meanings come from the separately reviewed, explicit Korean glossary.
"""
import collections
import json
import re
import unicodedata
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent
HAN = r'[\u3400-\u9fff\uf900-\ufaff]'
PAIR = re.compile(r'([가-힣]+)\((' + HAN + r'+)\)')
def norm(s):
    return re.sub(HAN, lambda m: unicodedata.normalize('NFKC', m[0]), s)

records = json.loads((ROOT / 'dist/herbs.json').read_text(encoding='utf-8'))
glossary = dict(line.split('|', 1) for line in (ROOT / 'korean-glossary.txt').read_text(encoding='utf-8').splitlines() if line and not line.startswith('#'))
# Keep the authored glossary deterministic and free of duplicated entries.
(ROOT / 'korean-glossary.txt').write_text('# 한의학 문헌 용어의 학습용 풀이. 현대의학적 효능이나 진단과 동일시하지 않는다.\n' + '\n'.join(k+'|'+v for k,v in glossary.items())+'\n', encoding='utf-8')

def strings(x):
    if isinstance(x, str): yield x
    elif isinstance(x, list):
        for v in x: yield from strings(v)
    elif isinstance(x, dict):
        for k,v in x.items():
            if k not in ('ko', 'glosses', 'koLabel', 'koReference', 'koName', 'koClassification'): yield from strings(v)

pairs = collections.defaultdict(collections.Counter)
for s in strings(records):
    for korean,han in PAIR.findall(s): pairs[norm(han)][korean] += 1
terms = {han: counts.most_common(1)[0][0] for han,counts in pairs.items()}
for h in records:
    if h.get('hanja'): terms[norm(h['hanja'])] = h['name']

readings_path = ROOT / 'korean-readings.json'
if readings_path.exists():
    readings = json.loads(readings_path.read_text(encoding='utf-8'))
else:
    readings = {}
    with zipfile.ZipFile(ROOT / '.sites-runtime/Unihan-17.zip') as z:
        for line in z.read('Unihan_Readings.txt').decode().splitlines():
            if '\tkHangul\t' in line:
                point,_,value = line.split('\t')
                readings[chr(int(point[2:],16))] = value.split(':')[0]
    needed = set(norm(c) for s in strings(records) for c in re.findall(HAN,s))
    readings = {c: readings[c] for c in sorted(needed) if c in readings}
    readings_path.write_text(json.dumps(readings,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

terms.update({
    '性味':'성질·맛', '歸經':'관련 경락', '煎服':'달여 복용',
    '煎腹':'달여 복용', '外用時':'몸 겉에 사용할 때', '外用':'몸 겉에 사용',
    '內服':'먹는 용법', '每回':'매회', '散劑':'가루약', '散齊':'가루약', '散濟':'가루약', '散制':'가루약',
    '丸劑':'알약', '丸':'알약', '湯劑':'달인 약', '適量':'적당량', '使用':'사용',
    '服用':'복용', '呑服':'삼켜 복용', '沖服':'물 등에 타서 복용',
    '硏末':'곱게 가루 내기', '硏粉':'곱게 가루 내기', '後下':'달이기 마지막에 넣기',
    '先煎':'먼저 달이기', '包煎':'천 주머니에 싸서 달이기', '久煎':'오래 달이기',
    '鮮品':'신선한 약재', '鮮生地':'신선한 생지황', '生用':'가공하지 않고 사용',
    '炒用':'볶아서 사용', '加倍':'두 배로 늘림', '倍加':'두 배로 늘림', '倍用':'두 배로 사용',
    '大劑':'많은 용량', '大量':'많은 양', '少量':'적은 양', '減用':'양을 줄여 사용',
    '孕婦':'임신부', '姙婦':'임신부', '姙娠婦':'임신부', '姙娠':'임신',
    '妊娠':'임신', '姙産婦':'임신부·산모', '愼用':'신중히 사용', '禁用':'사용 금지',
    '有毒':'독성이 있음', '有小毒':'독성이 약하게 있다고 기록됨', '有少毒':'독성이 약하게 있다고 기록됨',
    '小毒':'독성이 약하게 있다고 기록됨', '無毒':'독성이 없다고 기록됨', '大毒':'독성이 강함',
    '身體虛弱者':'몸이 허약한 사람', '體虛者':'몸이 허약한 사람', '體弱者':'몸이 약한 사람',
    '虛弱性':'허약함에 따른', '月經過多':'월경량이 지나치게 많음', '月經時':'월경 중',
    '月經期':'월경 기간', '授乳期':'수유 기간', '胎前産後':'임신 중과 출산 후',
    '多汗者':'땀이 많은 사람', '多尿者':'소변이 많은 사람', '泄瀉者':'설사하는 사람',
    '體溫低者':'체온이 낮은 사람', '體溫':'체온', '者':'사람', '入':'연결된다고 설명',
    '斑疹透暢':'발진이 이미 충분히 돋은 상태', '表虛多汗':'몸 겉의 기운이 약해 땀이 많은 상태',
    '胃寒嘔吐':'위가 차서 생긴 것으로 보는 구토', '中滿者':'배가 더부룩하고 꽉 찬 듯한 사람',
    '嘔家':'평소 구토를 자주 하는 사람', '酒家':'평소 술을 많이 마시는 사람',
    '諸濕腫滿':'습기의 정체로 몸이 붓고 배가 팽팽한 상태', '脹滿者':'배가 팽팽하고 더부룩한 사람',
    '大便燥結':'변이 마르고 굳은 상태', '小便不利':'소변이 잘 나오지 않는 상태',
    '消化不良':'소화불량', '食欲不振':'식욕 저하', '不欲食':'먹고 싶지 않음',
    '口苦舌乾':'입이 쓰고 혀가 마름', '口乾舌燥':'입과 혀가 마름',
    '頭痛眩暈':'두통과 어지럼', '頭暈目眩':'어지럼', '頭暈':'어지럼', '耳聾':'잘 들리지 않음',
    '咳嗽':'기침', '嘔吐':'구토', '泄瀉':'설사', '便秘':'변비', '瘙痒':'가려움',
    '禁':'금함', '同用':'함께 사용', '留皮':'껍질을 남김', '去皮':'껍질을 제거함',
    '忌':'피해야 함', '減低':'낮출 수 있음',
})
term_pattern = re.compile('|'.join(re.escape(k) for k in sorted(terms,key=len,reverse=True)))

def read_han(s):
    s = PAIR.sub(lambda m: m[1], s)
    s = norm(s)
    s = term_pattern.sub(lambda m: terms[m[0]], s)
    s = re.sub(HAN, lambda m: readings.get(m[0],m[0]), s)
    for old,new in [('사람는','사람은'),('사람가','사람이'),('상태한','상태인'),('가루약로','가루약으로'),('오래 달이기하면','오래 달이면'),('독성을 낮출 수 있음할 수 있다','독성을 낮출 수 있다'),('와 반한다','와 함께 쓰면 안 된다고 기록한다'),('과 반한다','과 함께 쓰면 안 된다고 기록한다')]:
        s=s.replace(old,new)
    return s

NATURE = {
 '苦':'쓴맛','甘':'단맛','辛':'매운맛','酸':'신맛','鹹':'짠맛','澀':'떫은맛','澁':'떫은맛','淡':'담담한 맛',
 '微苦':'약간 쓴맛','微甘':'약간 단맛','微辛':'약간 매운맛','微酸':'약간 신맛',
 '微寒':'약간 찬 성질','微溫':'약간 따뜻한 성질','大寒':'매우 찬 성질','大熱':'매우 뜨거운 성질',
 '寒':'찬 성질','涼':'서늘한 성질','凉':'서늘한 성질','微凉':'약간 서늘한 성질',
 '溫':'따뜻한 성질','熱':'뜨거운 성질','平':'차갑거나 뜨겁지 않은 성질',
}
nature_pattern = re.compile('|'.join(sorted(NATURE,key=len,reverse=True)))
def nature(s):
    s = PAIR.sub(lambda m: norm(m[2]), s)
    # Only isolated property tokens, never characters inside names of syndromes.
    s = re.sub(r'(?<!'+HAN+r')('+nature_pattern.pattern+r')(?!'+HAN+r')',lambda m:NATURE[m[0]],norm(s))
    return read_han(s).replace('관련 경락 :\n','관련 경락 : ').strip()

def explain(s):
    # Whole terms only: 救逆 in 回陽救逆 is NOT nausea (嘔逆).
    return [{'term': k, 'meaning': v} for k,v in glossary.items() if re.search(r'(?<![가-힣])'+re.escape(k)+r'(?=$|[^가-힣]|한 |인 |으로|에 |과 |와 |은 |는 |이 |가 |을 |를 |하여)',s)]

stats=collections.Counter()
for herb in records:
    d=herb['detail']
    for key in ['origins','natures','effects','indications','doses','preparations','cautions','aliases']:
        for item in d.get(key,[]):
            raw=item['value']
            item['ko']=nature(raw) if key=='natures' else read_han(raw)
            if key=='cautions' and raw=='胃寒嘔吐 斑疹透暢한 者, 表虛多汗한 者는 적합하지 않다.':
                item['ko']='위가 차서 생긴 것으로 보는 구토가 있는 사람, 발진이 이미 충분히 돋은 사람, 몸 겉을 지키는 기운이 약해 땀이 많은 사람에게는 적합하지 않다고 기록되어 있습니다.'
            item['glosses']=explain(item['ko']) if key in ['effects','indications','cautions','doses'] else []
            if item.get('label'): item['koLabel']=read_han(item['label'])
            item['koReference']=read_han(item.get('reference',''))
            if item['ko'] != raw: stats[key]+=1
            stats['glossed']+=bool(item['glosses'])
    d['koClassification']=read_han(d.get('classification',''))
    for f in d['formulas']:
        f['koName']=read_han(f['name']);f['koReference']=read_han(f.get('reference',''))
    for source in d['sources']: source['koLabel']=read_han(source['label'])

(ROOT/'dist/herbs.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(stats),ensure_ascii=False))
unknown=collections.Counter(c for h in records for key in ['natures','effects','indications','doses','cautions'] for x in h['detail'][key] for c in re.findall(HAN,x['ko']))
print('Unmapped characters:',dict(unknown))
