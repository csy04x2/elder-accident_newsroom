"""S01 데이터 집계 및 경계 판정의 최소 회귀 검사."""
import pandas as pd
from fastapi.testclient import TestClient

from api.main import app
from newsroom.data import metric_summary, spatial_summary
from newsroom.paths import ROOT_DIR, processed_data_dir


def test_health():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_default_data_dir(monkeypatch):
    monkeypatch.delenv("DATA_DIR", raising=False)
    result = processed_data_dir()
    assert result in {ROOT_DIR.parent / "elder_accident" / "data" / "processed", ROOT_DIR / "data" / "processed"}


def test_metric_denominator_and_missing_year():
    current = pd.DataFrame([{"고령보행자_사고건수": 10, "고령보행자_사망자수": 2, "고령인구": 10000, "전체보행자_사망자수": 5}])
    result = metric_summary(current, current.iloc[0:0])
    assert result["rate_display"] == "10.00건"
    assert result["death_share_display"] == "40.0%"
    assert result["accidents_delta"] is None


def test_spatial_counts_not_accident_counts():
    links = pd.DataFrame([
        {"사고연도": 2025, "자치구명": "A", "다발지역FID": 1, "경계중첩": 1, "사고건수": 20},
        {"사고연도": 2025, "자치구명": "A", "다발지역FID": 2, "경계중첩": 0, "사고건수": 30},
        {"사고연도": 2025, "자치구명": "B", "다발지역FID": 3, "경계중첩": None, "사고건수": 40},
    ])
    assert spatial_summary(links, 2025, "서울 전체") == {"total": 3, "overlap": 1, "outside": 1, "unknown": 1}
