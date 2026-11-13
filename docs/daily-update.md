# 정기 갱신: 설치와 확인

현재 PC에서 Streamlit과 MySQL을 실행하는 구조이므로 Windows 작업 스케줄러를 활용합니다. 새 서버·MySQL 테이블·API 키가 필요하지 않습니다.

## 1. 첫 실행

뉴스룸 루트 폴더에서 PowerShell:

```powershell
git pull origin main
python scripts/run_daily_update.py
```

정상 실행 시 정책·보도 SUCCESS/PARTIAL/FAILED와 로컬 CSV UNCHANGED/CHANGED/MISSING을 출력합니다. `FAILED`는 '관련 기사 없음'이 아니라 수집 실패입니다. S02에 마지막 확인 시각과 상태가 표시됩니다.

## 2. 매일 실행 등록

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/install_daily_task.ps1 -At 09:00
```

기본은 매일 한국 현지 PC 시간 오전 9시입니다. PC가 꺼져 있으면 실행할 수 없고, 재기동/로그인 등 운영체제 설정에 따라 놓친 작업의 재실행 시점이 달라질 수 있습니다. Windows에서 '작업 스케줄러' → `ElderAccidentNewsroomDailyUpdate`로 등록 여부를 확인합니다. 중지·삭제도 작업 스케줄러에서 합니다.

## 자동화 범위

- 정책·보도: RSS 제목, 발행처, 발행일, 검색 링크를 정기 검색. 마지막 정상 목록과 비교해 새 항목 수 기록. 실패해도 기존 정상 자료 유지
- 데이터: 기존 분석 CSV 4개 내용 해시와 최신 사고연도 확인. CSV 파일이 변경되면 다음 앱 실행 때 새 파일을 읽음
- 미구현: TAAS 등 기관에서 새로운 연도 데이터 자동 다운로드, 각 원자료 검증, 공간/인구 교차 가공, 신규 Fact Sheet 확정. 이 기능이 없으므로 '데이터 최신화 완료'라고 표시하지 않음
- 기사: 자동 생성·자동 검수·자동 승인·자동 공개 **하지 않음**
