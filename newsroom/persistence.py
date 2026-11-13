"""S02 selected idea persistence: write one fact snapshot, chosen sources, one idea atomically.

Schema is created separately; no implicit DB mutation at app startup.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import date, datetime, timezone

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

TYPE_MAP = {"정책": "POLICY", "보도자료": "PRESS", "언론": "NEWS"}
KST_OFFSET = "+09:00"


def engine_from_env() -> Engine:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url or "user:password@" in url:
        raise RuntimeError("DATABASE_URL을 실제 MySQL 접속 정보로 설정하세요.")
    if not url.startswith("mysql+pymysql://"):
        raise RuntimeError("README에 정의된 MySQL(PYMySQL) 접속 문자열이 필요합니다.")
    return create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 5})


def as_naive_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo:
        result = result.astimezone(timezone.utc).replace(tzinfo=None)
    return result


def source_key(source: dict) -> str:
    """Same URL may occur in different searches; avoid duplicating a source in DB."""
    return hashlib.sha256(source["source_url"].encode("utf-8")).hexdigest()


def checked_facts(facts: dict) -> bool:
    """Only internally consistent calculated figures qualify as a checked snapshot."""
    if facts.get("calculation_status") != "CHECKED":
        return False
    a, p, rate = (facts.get(k) for k in ("accidents", "elderly_residents", "accidents_per_10000_residents"))
    count_keys = ["hotspot_polygons", "overlap_with_available_zone_boundaries",
                  "nonoverlap_with_available_zone_boundaries", "unclassified_hotspot_polygons"]
    if a is None or not isinstance(p, int) or p <= 0 or rate is None:
        return False
    if abs(a / p * 10000 - rate) > 0.011:
        return False
    if any(not isinstance(facts.get(k), int) for k in count_keys):
        return False
    return facts["hotspot_polygons"] == sum(facts[k] for k in count_keys[1:])


def save_idea(engine: Engine, facts: dict, idea: dict, sources: list[dict],
              verified_excerpts: dict[str, str]) -> int:
    """Never promote RSS headline to verified content. Atomic commit or rollback."""
    if not checked_facts(facts):
        raise ValueError("계산값이 확인되지 않은 Fact Sheet는 저장할 수 없습니다.")
    if idea.get("readiness") != "NEEDS_REPORTING":
        raise ValueError("원문·추가 취재 검증 전에는 NEEDS_REPORTING만 저장할 수 있습니다.")
    by_id = {s["id"]: s for s in sources}
    selected = [by_id[sid] for sid in idea.get("source_ids", []) if sid in by_id]
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with engine.begin() as conn:
        analysis_id = conn.execute(text("""
            INSERT INTO analysis_snapshots
              (analysis_type, filters_json, facts_json, source_info_json, verification_status, data_as_of, created_at)
            VALUES
              (:analysis_type, :filters, :facts, :source, 'PASSED', :data_as_of, :created_at)
        """), {
            "analysis_type": "elderly_pedestrian_safety",
            "filters": json.dumps({"region": facts["region"], "year": facts["accident_year"]}, ensure_ascii=False),
            "facts": json.dumps(facts, ensure_ascii=False),
            "source": json.dumps({"source": facts["source"], "limitations": facts["limitations"]}, ensure_ascii=False),
            "data_as_of": date(int(facts["accident_year"]), 12, 31),
            "created_at": now,
        }).lastrowid
        document_ids = []
        for source in selected:
            if not source.get("source_url"):
                continue
            snippet = verified_excerpts.get(source["id"], "").strip()[:4000]
            # Human has compared exact excerpt with original; selection is an assertion of review, not AI fact-check.
            status = "VERIFIED" if snippet else "METADATA_ONLY"
            content_hash = source_key(source)
            conn.execute(text("""
                INSERT INTO source_documents
                  (title, source_org, source_type, source_url, published_at, retrieved_at,
                   content_excerpt, content_hash, verification_status)
                VALUES (:title, :org, :type, :url, :published, :retrieved, :excerpt, :hash, :status)
                ON DUPLICATE KEY UPDATE
                  retrieved_at = VALUES(retrieved_at),
                  content_excerpt = CASE WHEN VALUES(verification_status) = 'VERIFIED'
                                    THEN VALUES(content_excerpt) ELSE content_excerpt END,
                  verification_status = CASE WHEN VALUES(verification_status) = 'VERIFIED'
                                    THEN 'VERIFIED' ELSE verification_status END
            """), {
                "title": source["title"][:500], "org": source["source_org"][:200],
                "type": TYPE_MAP.get(source.get("source_type"), "NEWS"),
                "url": source["source_url"], "published": as_naive_datetime(source.get("published_at")),
                "retrieved": as_naive_datetime(source.get("retrieved_at")) or now,
                "excerpt": snippet or None, "hash": content_hash, "status": status,
            })
            found = conn.execute(text(
                "SELECT id FROM source_documents WHERE content_hash=:h"
            ), {"h": content_hash}).scalar_one()
            document_ids.append(int(found))
        result = conn.execute(text("""
            INSERT INTO story_ideas (analysis_id, title, angle, news_value,
                                     source_ids_json, reporting_gaps_json, readiness, created_at)
            VALUES (:analysis_id, :title, :angle, :news_value,
                    :source_ids, :gaps, 'NEEDS_REPORTING', :created_at)
        """), {
            "analysis_id": analysis_id,
            "title": idea["title"][:500],
            "angle": idea["angle"],
            "news_value": idea.get("news_value", ""),
            "source_ids": json.dumps(document_ids),
            "gaps": json.dumps({
                "gaps": idea.get("reporting_gaps", []),
                "analysis_summary": idea.get("evidence", ""),
                "source_review": "원문 대조 발췌만 VERIFIED; 원문 전체와 기사 주장의 사실성은 미검증",
            }, ensure_ascii=False),
            "created_at": now,
        })
        return int(result.lastrowid)


def recent_saved_ideas(engine: Engine, limit: int = 10) -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT si.id, si.title, si.angle, si.readiness, si.created_at,
                   a.filters_json, si.source_ids_json
            FROM story_ideas si JOIN analysis_snapshots a ON a.id = si.analysis_id
            ORDER BY si.id DESC LIMIT :limit
        """), {"limit": min(50, max(1, limit))}).mappings().all()
    result = []
    for row in rows:
        item = dict(row)
        for field in ("filters_json", "source_ids_json"):
            if isinstance(item[field], str):
                item[field] = json.loads(item[field])
        result.append(item)
    return result
