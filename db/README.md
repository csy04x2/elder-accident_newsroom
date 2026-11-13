# MySQL DB (README의 5개 테이블)

`db/schema.sql`에는 기존 README에 설계된 **5개 테이블만** 정의한다. S02는 `analysis_snapshots`, `source_documents`, `story_ideas`를 사용하고, `articles`, `article_evidence`는 향후 S03~S05에서 사용한다.

## 로컬에서 처음 한 번

1. MySQL 8.x 서버와 데이터베이스를 준비한다. (Workbench는 서버가 아니다.)
2. `.env`에 `DATABASE_URL=mysql+pymysql://사용자:비밀번호@localhost:3306/elder_accident_newsroom?charset=utf8mb4`를 넣는다.
3. MySQL Workbench에서 `db/schema.sql`을 실행한다. 접속 계정은 테이블 생성 권한이 있어야 한다.
4. Streamlit S02에서 후보를 선택한 뒤 **DB 저장** 버튼을 누르면 선택한 후보의 분석 스냅샷·참조 출처·취재 질문이 하나의 트랜잭션으로 저장된다.

DB를 설정하지 않아도 검색·추천 기능은 계속 작동한다. 단, 추천 내용은 Streamlit 세션이 끝나면 사라진다. DB가 미설정되었거나 접속 오류가 나면 **저장 성공이라고 표시하지 않는다.**

### 원문 대조
현재 RSS는 제목·발행처·발행일·URL만 제공한다. S02에서 기자가 원문 링크를 직접 열어 발췌 문구를 대조하고 입력할 수 있다. 빈 발췌는 `METADATA_ONLY`, 대조 완료로 제출한 발췌는 `VERIFIED`로 저장한다. 이는 **입력한 발췌문을 사람이 확인했다는 표시**이며 원문 전체, 기사 주장, 인과관계가 검증되었다는 의미가 아니다.

동일 RSS 링크는 `content_hash`로 중복 등록을 피한다. 구글 뉴스 RSS 링크와 발행사 직접 URL은 다른 주소일 수 있다. 검색 대상 전체를 무조건 보관하지 않으며 선택 기사거리와 연결된 출처만 저장한다.
