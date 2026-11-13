"""S02: 사고 분석 + 검색 메타데이터로 취재 후보 만들기.

제목만 검색된 외부 자료는 검증된 내용으로 간주하지 않는다.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlparse

import feedparser
import pandas as pd
import requests
from openai import OpenAI

from newsroom.data import spatial_summary

KST = timezone(timedelta(hours=9))
NEWS_RSS = "https://news.google.com/rss/search"
CATEGORIES = {
    "정책": 'site:seoul.go.kr OR site:korea.kr 노인보호구역 보행안전',
    "보도자료": 'site:seoul.go.kr OR site:koroad.or.kr 고령 보행자 교통사고',
    "언론": '고령 보행자 노인보호구역 사고 서울',
}
LIMITATIONS = (
    "사고는 발생지 기준, 인구는 거주지 기준이다. 사고율은 실제 보행량을 보정하지 않는다.",
    "사고다발지역은 개별 사고 전체가 아닌 선정된 공간 폴리곤이다.",
    "보호구역 API 경계에 공식 지정 시설 일부가 누락될 수 있다.",
    "선정연도와 실제 사고 발생연도는 다를 수 있고 정책 효과·원인을 단정할 수 없다.",
)


def fact_sheet(panel: pd.DataFrame, links: pd.DataFrame, year: int, district: str) -> dict:
    rows = panel[panel["사고연도"] == year]
    if district != "서울 전체":
        rows = rows[rows["자치구명"] == district]
    def summed(col: str):
        if col not in rows:
            return None
        n = pd.to_numeric(rows[col], errors="coerce").sum(min_count=1)
        return None if pd.isna(n) else int(n)
    accidents, population, deaths = (summed(x) for x in (
        "고령보행자_사고건수", "고령인구", "고령보행자_사망자수"))
    spatial = spatial_summary(links, year, district)
    return {
        "region": district, "accident_year": year,
        "accidents": accidents, "elderly_residents": population,
        "elderly_pedestrian_deaths": deaths,
        "accidents_per_10000_residents": (
            round(accidents / population * 10000, 2)
            if accidents is not None and population and population > 0 else None),
        "hotspot_polygons": spatial["total"],
        "overlap_with_available_zone_boundaries": spatial["overlap"],
        "nonoverlap_with_available_zone_boundaries": spatial["outside"],
        "unclassified_hotspot_polygons": spatial["unknown"],
        "source": "elder_accident/data/processed CSV, TAAS·서울 열린데이터광장·보호구역 API 가공",
        "limitations": LIMITATIONS,
        "calculation_status": "CHECKED" if accidents is not None and population and population > 0
        and spatial["total"] == spatial["overlap"] + spatial["outside"] + spatial["unknown"]
        else "INCOMPLETE",
    }


def validate_hint_url(value: str) -> str:
    """기자 URL은 출처가 아니라 미검증 단서. 임의 주소로 서버 요청하지 않는다."""
    value = value.strip()
    if not value:
        return ""
    parsed = urlparse(value)
    if parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("http(s)로 시작하는 공개 웹 URL을 입력해 주세요.")
    if len(value) > 2000:
        raise ValueError("URL은 2,000자 이내로 입력해 주세요.")
    return value


def search_sources(days: int, categories: list[str], keyword: str = "") -> dict:
    """Google News RSS 검색 결과만 수집; 본문 확인/원문 검증은 하지 않는다."""
    if days not in (30, 90, 365):
        raise ValueError("검색 기간은 30/90/365일 중 하나여야 합니다.")
    if not set(categories).issubset(CATEGORIES):
        raise ValueError("지원하지 않는 출처 유형입니다.")
    keyword = re.sub(r"[^\w가-힣\s-]", " ", keyword)[:80].strip()
    retrieved_at = datetime.now(KST).isoformat(timespec="seconds")
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    items, errors, seen = [], [], set()
    for category in categories:
        query = CATEGORIES[category]
        if keyword:
            query += " " + keyword
        try:
            response = requests.get(
                NEWS_RSS,
                params={"q": query, "hl": "ko", "gl": "KR", "ceid": "KR:ko"},
                timeout=12, headers={"User-Agent": "elder-accident-newsroom/0.1"},
            )
            response.raise_for_status()
            parsed = feedparser.parse(response.content)
            if parsed.bozo and not parsed.entries:
                raise ValueError("RSS 형식을 읽을 수 없습니다.")
            for entry in parsed.entries[:25]:
                link = str(entry.get("link", "")).strip()
                if not link.startswith("https://") or link in seen:
                    continue
                published = entry.get("published_parsed")
                pub_iso = None
                if published:
                    from calendar import timegm
                    pub_dt = datetime.fromtimestamp(timegm(published), timezone.utc)
                    if pub_dt < cutoff:
                        continue
                    pub_iso = pub_dt.isoformat()
                else:
                    continue  # 발행일 미확인 결과는 검색 기간 준수 여부를 알 수 없음
                seen.add(link)
                source = entry.get("source", {})
                items.append({
                    "id": f"S{len(items)+1}", "title": str(entry.get("title", ""))[:500],
                    "source_org": str(source.get("title", ""))[:200] or "발행처 미확인",
                    "source_type": category, "source_url": link,
                    "published_at": pub_iso, "retrieved_at": retrieved_at,
                    "verification_status": "METADATA_ONLY",
                })
        except (requests.RequestException, ValueError) as exc:
            errors.append(f"{category} 검색 실패: {type(exc).__name__}")
    items.sort(key=lambda s: s["published_at"], reverse=True)
    items = items[:30]
    for i, item in enumerate(items, 1):
        item["id"] = f"S{i}"
    return {"sources": items, "errors": errors, "retrieved_at": retrieved_at,
            "search_complete": not errors, "searched_categories": categories, "days": days}


def recommend(facts: dict, search: dict, keyword: str, url: str, memo: str) -> list[dict]:
    """LLM은 취재 방향만 제안한다. 검색 메타데이터를 검증된 원문으로 승격하지 않는다."""
    if facts["calculation_status"] != "CHECKED":
        raise ValueError("기초 분석 수치를 확인할 수 없어 추천을 생성하지 않습니다.")
    if not search["sources"]:
        raise ValueError("검색 결과를 확보하지 못했습니다. 관련 보도가 없다는 의미는 아닙니다.")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(".env의 OPENAI_API_KEY가 필요합니다. 검색 결과만 먼저 검토할 수 있습니다.")
    source_ids = {item["id"] for item in search["sources"]}
    instructions = """당신은 한국 데이터 저널리즘 취재기획 보조자다.
입력된 CSV 사실표와 검색 결과 '제목/발행처/발행일'만 활용해 기사거리 0~3개를 반환하라.
검색 결과 본문은 읽지 않았으므로 제목에 나타난 쟁점 이상의 정책 사실을 주장하지 마라.
검색에 걸리지 않은 기사가 없다고 단정하지 마라. 입력 URL과 메모는 검증되지 않은 단서다.
원인, 사고 예방 효과, 정책 실패를 단정하지 마라. 각 후보는 차별성, 추가 확인 항목을 명시.
후보가 빈약하면 0건을 허용한다. 모든 후보는 NEEDS_REPORTING으로 표기한다.
JSON object만 응답: {"ideas":[{"title":"가제","angle":"취재 방향",
"news_value":"뉴스 가치·기존 보도와 비교할 점","evidence":"검증된 CSV 수치와 한계",
"reporting_gaps":["추가 확인 1"],"source_ids":["S1"],"readiness":"NEEDS_REPORTING"}]}.
source_ids는 입력에 실제 존재하는 ID만 쓰고, 관계가 불확실하면 빈 배열.
숫자를 새로 만들지 말고, AI가 직접 검색하거나 원문을 읽었다고 주장하지 마라."""
    payload = {
        "fact_sheet": facts,
        "search_status": {"retrieved_at": search["retrieved_at"],
                          "errors": search["errors"], "days": search["days"]},
        "source_metadata_only": search["sources"],
        "reporter_unverified_hints": {"keyword": keyword[:80], "url": url, "memo": memo[:3000]},
    }
    client = OpenAI(api_key=api_key, timeout=35, max_retries=0)
    result = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        messages=[{"role": "system", "content": instructions},
                  {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    raw = json.loads(result.choices[0].message.content or "{}")
    output = []
    for item in raw.get("ideas", [])[:3]:
        if not isinstance(item, dict) or not item.get("title") or not item.get("angle"):
            continue
        ids = item.get("source_ids", [])
        if not isinstance(ids, list):
            ids = []
        gaps = item.get("reporting_gaps", [])
        if not isinstance(gaps, list):
            gaps = []
        output.append({
            "title": str(item["title"])[:500], "angle": str(item["angle"])[:1500],
            "news_value": str(item.get("news_value", ""))[:1500],
            "evidence": str(item.get("evidence", ""))[:1500],
            "reporting_gaps": [str(g)[:500] for g in gaps[:6]],
            "source_ids": [s for s in ids if isinstance(s, str) and s in source_ids],
            "readiness": "NEEDS_REPORTING",
        })
    return output
