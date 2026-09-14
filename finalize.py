from pathlib import Path
p=Path('dist/index.html')
s=p.read_text(encoding='utf-8').replace('src="app.js"','src="app-v2.js"').replace('식약처 원문을 참고한 예시 자료입니다. 전체 한약재 DB는 아직 연결되지 않았습니다.','식약처 생약 목록 601건을 수록했습니다. 이름·기원은 원문을 바탕으로 하며, 상세 정보는 검토 상태를 확인하세요.').replace('연결 DB 및 전문 검토 후 제공','전문 문헌 검토 후 제공').replace('연결 DB 및 원문 확인 후 제공','상세 원문 확인 후 제공')
s=s.replace('<span>자료 안내</span>','<a href="https://www.nifds.go.kr/herb/m_442/list.do" target="_blank" rel="noopener">식약처 DB ↗</a>')
p.write_text(s,encoding='utf-8')
