from pathlib import Path
p=Path('dist/index.html');s=p.read_text(encoding='utf-8')
s=s.replace('지혈약 <small>예시 분류</small>','지혈약 <small>전통 분류</small>')
s=s.replace('<td class="muted">전문 문헌 검토 후 제공</td>','<td>고(苦)·미한(微寒) / 간(肝)·대장(大腸) <span class="muted">[4]</span></td>')
s=s.replace('<h3>간화 완화</h3>','<h3>청간사화</h3>')
s=s.replace('제공된 화면에 있는 전통 효능 표현입니다. 원문 출처와 한의학적 근거는 검토 전이며, 임상 효과가 확인되었다는 의미가 아닙니다.','한국한의학연구원 OASIS는 전통 효능을 양혈지혈(涼血止血)·청간사화(淸肝瀉火)로 분류합니다. 혈열과 간화에 관한 한의학적 표현이며, 현대 임상에서 치료 효과가 확립되었다는 뜻은 아닙니다. [4]')
s=s.replace('문헌·전문가 검토 필요','전통 문헌 정보 · 전문 검토 전')
s=s.replace('</ol><div class="review-meta">','<li><a href="https://oasis.kiom.re.kr/oasis/herb/monoDetailView_M02.jsp?idx=44&amp;srch_menu_nix=&amp;tab=2" target="_blank" rel="noopener">한국한의학연구원 OASIS · 괴화 약성 ↗</a><p>전통 성미·귀경·효능 분류</p></li></ol><div class="review-meta">')
p.write_text(s,encoding='utf-8')
