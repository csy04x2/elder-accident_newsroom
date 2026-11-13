"""Approved-only SQL scope: list and direct article detail."""
from sqlalchemy import create_engine, text

from newsroom.publication import approved_article, approved_articles


def memory_db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as c:
        c.execute(text("""CREATE TABLE articles (
            id INTEGER PRIMARY KEY, title TEXT, content TEXT, status TEXT,
            validation_passed BOOLEAN, published_at DATETIME, validated_hash TEXT, reviewed_by TEXT)"""))
        c.execute(text("""CREATE TABLE article_evidence(
            id INTEGER PRIMARY KEY, article_id INTEGER, evidence_role TEXT,
            location_label TEXT, explanation TEXT, analysis_id INTEGER, source_document_id INTEGER)"""))
        c.execute(text("""CREATE TABLE analysis_snapshots (
            id INTEGER PRIMARY KEY, data_as_of DATE, source_info_json TEXT, facts_json TEXT)"""))
        c.execute(text("""CREATE TABLE source_documents (
            id INTEGER PRIMARY KEY, title TEXT, source_org TEXT,
            source_url TEXT, published_at DATETIME,
            content_excerpt TEXT, verification_status TEXT)"""))
        for id, status, passed, publish, digest in [
            (1, "승인", True, "2026-11-13 06:00:00", "abc"),
            (2, "검토대기", True, None, "def"),
            (3, "보류", True, None, "ghi"),
            (4, "승인", False, "2026-11-13 06:00:00", "xyz"),
            (5, "승인", True, None, "xyz"),
        ]:
            c.execute(text("""INSERT INTO articles VALUES
                (:id,:title,'내용',:status,:passed,:publish,:digest,'편집장')"""),
                {"id": id, "title": f"기사 {id}", "status": status,
                 "passed": passed, "publish": publish, "digest": digest})
        c.execute(text("""INSERT INTO analysis_snapshots
            VALUES (1, '2025-12-31', '{"source":"TAAS"}',
                    '{"accident_year":2025,"region":"서울 전체"}')"""))
        c.execute(text("""INSERT INTO article_evidence
            VALUES (1,1,'STATISTIC','2025년','분석 통계',1,NULL)"""))
    return engine


def test_list_exposes_only_approved():
    e = memory_db()
    assert [row["id"] for row in approved_articles(e)] == [1]
    e.dispose()


def test_direct_read_cannot_bypass_approval():
    e = memory_db()
    assert approved_article(e, 1)["title"] == "기사 1"
    assert approved_article(e, 1)["evidence"][0]["facts_json"]["accident_year"] == 2025
    for id in (2, 3, 4, 5, 99):
        assert approved_article(e, id) is None
    e.dispose()
