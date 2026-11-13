# 데이터 연결 위치

분석의 원본·가공 데이터는 [elder_accident](https://github.com/csy04x2/elder_accident)의 `data/processed/`를 기준으로 사용합니다.

이번 뼈대 단계에서는 CSV·GeoJSON 파일을 복사하지 않습니다. 로컬 `.env`의 `DATA_DIR`에 기존 저장소의 `data/processed` 경로를 지정하세요. 상대 경로는 이 저장소의 루트를 기준으로 해석합니다.

향후 실제 분석 화면은 기존 파일의 출처·기준연도·좌표계·해석상 한계를 유지하면서 연결합니다. 수집 시각과 통계 기준일도 구분합니다.
