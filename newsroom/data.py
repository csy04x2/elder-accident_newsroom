"""기존 elder_accident의 가공 CSV 읽기 및 뉴스룸 브리핑 계산."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from newsroom.paths import processed_data_dir

FILES = {
    "panel": "01_자치구연도_패널.csv",
    "hotspots": "03_다발지역_서울.csv",
    "zones": "05_보호구역_경계.csv",
    "links": "06_다발지역_보호구역_연결.csv",
}


def dataset_state() -> dict:
    folder = processed_data_dir()
    missing = [filename for filename in FILES.values() if not (folder / filename).is_file()]
    versions = tuple((folder / filename).stat().st_mtime_ns for filename in FILES.values() if (folder / filename).is_file())
    return {"directory": folder, "missing": missing, "versions": versions}


def load_data(folder: Path, versions: tuple[int, ...]) -> dict[str, pd.DataFrame]:
    """수집하지 않고 CSV만 읽는다. versions는 추후 캐시 키 확장용."""
    del versions
    result = {}
    for key, filename in FILES.items():
        frame = pd.read_csv(folder / filename, encoding="utf-8-sig")
        for col in ("사고연도", "경계중첩"):
            if col in frame:
                frame[col] = pd.to_numeric(frame[col], errors="coerce")
        result[key] = frame
    return result


def _sum(frame: pd.DataFrame, name: str) -> float:
    if name not in frame:
        return float("nan")
    return pd.to_numeric(frame[name], errors="coerce").sum(min_count=1)


def _format(value: float, suffix: str, decimals: int = 0) -> str:
    return "자료 없음" if pd.isna(value) else f"{value:,.{decimals}f}{suffix}"


def _delta(now: float, before: float) -> str | None:
    if pd.isna(now) or pd.isna(before):
        return None
    return f"{now - before:+,.0f}건"


def metric_summary(current: pd.DataFrame, previous: pd.DataFrame) -> dict[str, str | None]:
    accidents = _sum(current, "고령보행자_사고건수")
    deaths = _sum(current, "고령보행자_사망자수")
    population = _sum(current, "고령인구")
    all_deaths = _sum(current, "전체보행자_사망자수")
    rate = accidents / population * 10000 if pd.notna(population) and population > 0 else float("nan")
    death_share = deaths / all_deaths * 100 if pd.notna(all_deaths) and all_deaths > 0 else float("nan")
    previous_accidents = _sum(previous, "고령보행자_사고건수")
    previous_deaths = _sum(previous, "고령보행자_사망자수")
    return {
        "accidents_display": _format(accidents, "건"),
        "accidents_delta": _delta(accidents, previous_accidents),
        "deaths_display": _format(deaths, "명"),
        "deaths_delta": None if pd.isna(deaths) or pd.isna(previous_deaths) else f"{deaths - previous_deaths:+,.0f}명",
        "rate_display": _format(rate, "건", 2),
        "death_share_display": _format(death_share, "%", 1),
    }


def spatial_summary(links: pd.DataFrame, year: int, district: str) -> dict[str, int]:
    rows = links[links["사고연도"] == year].drop_duplicates("다발지역FID")
    if district != "서울 전체":
        rows = rows[rows["자치구명"] == district]
    known = pd.to_numeric(rows["경계중첩"], errors="coerce")
    return {
        "total": len(rows),
        "overlap": int((known == 1).sum()),
        "outside": int((known == 0).sum()),
        "unknown": int(known.isna().sum()),
    }
