# MySQL DB

[루트 README의 DB 설계](../README.md#4-db-설계)를 기준으로 합니다.

예정된 테이블은 `analysis_snapshots`, `source_documents`, `story_ideas`, `articles`, `article_evidence` 총 5개입니다.

이번 커밋에는 SQL 스키마, 마이그레이션, DB 연결·생성 로직을 넣지 않습니다. 다음 구현 단계에서 설계된 FK·CHECK 및 승인 차단 조건을 적용합니다.
