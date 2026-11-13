"""Run the existing RSS search daily and detect local source-data changes.

No article generation, no rewriting processed CSV, no DB mutation.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from newsroom.data import FILES
from newsroom.paths import ROOT_DIR, processed_data_dir
from newsroom.recommendation import CATEGORIES, search_sources

KST = timezone(timedelta(hours=9))
STATE_PATH = ROOT_DIR / "data" / "updates" / "daily_status.json"


def _read_previous(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _signature(path: Path) -> dict | None:
    if not path.is_file():
        return None
    stat = path.stat()
    # Hash avoids marking an unchanged source as fresh after file copy/touch.
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"sha256": digest.hexdigest(), "bytes": stat.st_size}


def local_data_status(folder: Path, previous: dict) -> dict:
    files = {name: _signature(folder / name) for name in FILES.values()}
    missing = [name for name, value in files.items() if value is None]
    old = previous.get("files", {})
    changes = [name for name, value in files.items()
               if value is not None and old.get(name, {}).get("sha256") not in
               (None, value["sha256"])]
    return {
        "directory": str(folder),
        "files": files,
        "missing": missing,
        "changed": changes,
        "latest_accident_year": _max_year(folder / FILES["panel"]),
        "status": "MISSING" if missing else ("CHANGED" if changes else "UNCHANGED"),
        "note": "로컬 CSV 상태만 확인. 공식 원천 자료 신규 공개 여부는 자동 조회하지 않음.",
    }


def _max_year(path: Path) -> int | None:
    if not path.is_file():
        return None
    import pandas as pd
    years = pd.read_csv(path, encoding="utf-8-sig", usecols=["사고연도"])["사고연도"]
    years = pd.to_numeric(years, errors="coerce").dropna()
    return int(years.max()) if not years.empty else None


def run_once(path: Path = STATE_PATH, search=None, now=None) -> dict:
    """Keep last successful news set on partial/network failures."""
    previous = _read_previous(path)
    now = now or datetime.now(KST)
    local = local_data_status(processed_data_dir(), previous.get("data", {}))
    search = search or search_sources
    try:
        found = search(90, list(CATEGORIES), "")
        errors = list(found.get("errors", []))
        if not found.get("sources") and not errors:
            errors.append("검색 결과가 0건: 이전 성공 자료 유지")
        if errors:
            previous_news = previous.get("news", {})
            news = {
                "status": "PARTIAL" if found.get("sources") else "FAILED",
                "errors": errors,
                "last_success_at": previous_news.get("last_success_at"),
                "sources": previous_news.get("sources", []),
                "new_count": 0,
                "note": "검색 일부/전체 실패: 마지막 완전 성공 검색 자료를 유지함",
            }
        else:
            old_urls = {item["source_url"] for item in previous.get("news", {}).get("sources", [])}
            sources = found["sources"]
            news = {
                "status": "SUCCESS",
                "errors": [],
                "last_success_at": found["retrieved_at"],
                "sources": sources,
                "new_count": sum(item["source_url"] not in old_urls for item in sources)
                if previous.get("news", {}).get("last_success_at") else 0,
                "note": "새 항목 수는 지난번 성공 검색 결과와 비교한 값. RSS 제목 정보만 확인.",
            }
    except Exception as exc:
        news = {
            "status": "FAILED",
            "errors": [f"검색 실행 오류: {type(exc).__name__}"],
            "last_success_at": previous.get("news", {}).get("last_success_at"),
            "sources": previous.get("news", {}).get("sources", []),
            "new_count": 0,
            "note": "검색 실패: 이전 성공 자료 유지",
        }
    output = {"last_checked_at": now.isoformat(timespec="seconds"),
              "data": local, "news": news}
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)
    return output


def main():
    result = run_once()
    print(f'확인: {result["last_checked_at"]}')
    print(f'정책·보도: {result["news"]["status"]}, 새 항목 {result["news"]["new_count"]}건')
    print(f'분석 CSV: {result["data"]["status"]}, 최신 사고연도 {result["data"]["latest_accident_year"]}')
    if result["news"]["errors"]:
        print("검색 오류: " + " / ".join(result["news"]["errors"]))


if __name__ == "__main__":
    main()
