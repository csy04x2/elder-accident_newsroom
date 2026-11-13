# MySQL DB (README의 5개 테이블)

`db/schema.sql`에는 기존 README에 설계된 **5개 테이블만** 정의한다. S02는 `analysis_snapshots`, `source_documents`, `story_ideas`를 사용하고, `articles`, `article_evidence`는 향후 S03~S05에서 사용한다.

## 로컬에서 처음 한 번

1. MySQL Workbench에서 실행 중인 MySQL 8.x 서버에 접속한다. 별도 데이터베이스는 수동 생성하지 않아도 된다.
2. `.env`에 `DATABASE_URL=mysql+pymysql://사용자:비밀번호@localhost:3306/elder_accident_newsroom?charset=utf8mb4`를 넣는다.
3. MySQL Workbench에서 `File → Open SQL Script...`로 `db/schema.sql`을 연 뒤 번개 아이콘(전체 실행)을 누른다. 스크립트가 전용 DB `elder_accident_newsroom`을 생성·선택하고 5개 테이블을 생성한다. 계정에 CREATE DATABASE 및 테이블 생성 권한이 필요하다. 기존 `rentwatch_seoul` DB는 변경하지 않는다.\n   완료 후 아래 SQL로 테이블 5개가 보이는지 확인한다.\n\n   ```sql\n   USE elder_accident_newsroom;\n   SHOW TABLES;\n   ```
4. Streamlit S02에서 후보를 선택한 뒤 **DB 저장** 버튼을 누르면 선택한 후보의 분석 스냅샷·참조 출처·취재 질문이 하나의 트랜잭션으로 저장된다.

DB를 설정하지 않아도 검색·추천 기능은 계속 작동한다. 단, 추천 내용은 Streamlit 세션이 끝나면 사라진다. DB가 미설정되었거나 접속 오류가 나면 **저장 성공이라고 표시하지 않는다.**

### 원문 대조
현재 RSS는 제목·발행처·발행일·URL만 제공한다. S02에서 기자가 원문 링크를 직접 열어 발췌 문구를 대조하고 입력할 수 있다. 빈 발췌는 `METADATA_ONLY`, 대조 완료로 제출한 발췌는 `VERIFIED`로 저장한다. 이는 **입력한 발췌문을 사람이 확인했다는 표시**이며 원문 전체, 기사 주장, 인과관계가 검증되었다는 의미가 아니다.

동일 RSS 링크는 `content_hash`로 중복 등록을 피한다. 구글 뉴스 RSS 링크와 발행사 직접 URL은 다른 주소일 수 있다. 검색 대상 전체를 무조건 보관하지 않으며 선택 기사거리와 연결된 출처만 저장한다.

## 실제 저장 확인

S02에서 하나의 후보를 선택해 `선택 기사거리 DB 저장`을 누른 후, `DB에 저장된 기사거리 보기`에서 같은 ID가 조회되는지 확인한다. Workbench에서도 아래 SQL로 확인 가능하다.

```sql
USE elder_accident_newsroom;
SELECT id, title, readiness, created_at FROM story_ideas ORDER BY id DESC LIMIT 5;
```

**주의:** `DATABASE_URL`의 사용자명·암호는 이 저장소 전용 `.env`에만 넣는다. 비밀번호에 `@`, `#`, `/`, `:` 등의 문자가 포함되면 URL 인코딩이 필요하다. MySQL 서버의 연결정보는 기존 RentWatch 프로젝트에서 사용하는 호스트·포트를 참고할 수 있지만 **RentWatch의 데이터베이스명으로 저장하지 않는다.**
