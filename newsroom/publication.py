"""S05 approved-only public article queries.

Always enforce publication eligibility in SQL, for both listing and direct detail reads.
"""
from __future__ import annotations

import json
from sqlalchemy import text
from sqlalchemy.engine import Engine


PUBLIC_FILTER = """a.status = '승인'
    AND a.validation_passed = TRUE
    AND a.published_at IS NOT NULL
    AND a.validated_hash IS NOT NULL"""


def approved_articles(engine: Engine, limit: int = 50) -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(text(f"""
            SELECT a.id, a.title, a.published_at, a.reviewed_by
            FROM articles a
            WHERE {PUBLIC_FILTER}
            ORDER BY a.published_at DESC, a.id DESC
            LIMIT :limit
        """), {"limit": max(1, min(int(limit), 100))}).mappings().all()
    return [dict(row) for row in rows]


def approved_article(engine: Engine, article_id: int) -> dict | None:
    """Non-approved IDs are indistinguishable from absent articles to this reader."""
    with engine.connect() as conn:
        row = conn.execute(text(f"""
            SELECT a.id, a.title, a.content, a.published_at, a.reviewed_by
            FROM articles a
            WHERE a.id = :id AND {PUBLIC_FILTER}
        """), {"id": article_id}).mappings().first()
        if row is None:
            return None
        article = dict(row)
        evidence = conn.execute(text("""
            SELECT e.evidence_role, e.location_label, e.explanation,
                   s.id AS analysis_id, s.data_as_of, s.source_info_json, s.facts_json,
                   d.id AS source_id, d.title AS source_title,
                   d.source_org, d.source_url, d.published_at AS source_published_at,
                   d.content_excerpt, d.verification_status
            FROM article_evidence e
            LEFT JOIN analysis_snapshots s ON e.analysis_id = s.id
            LEFT JOIN source_documents d ON e.source_document_id = d.id
            WHERE e.article_id = :id
            ORDER BY e.id
        """), {"id": article_id}).mappings().all()
    sources = []
    for row in evidence:
        item = dict(row)
        for key in ("source_info_json", "facts_json"):
            if isinstance(item.get(key), str):
                item[key] = json.loads(item[key])
        sources.append(item)
    article["evidence"] = sources
    return article
