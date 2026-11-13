"""S02 추천은 확인 가능한 계산과 외부 검색 메타데이터를 구분한다."""
import pandas as pd
import pytest

from newsroom.recommendation import fact_sheet, validate_hint_url, recommend


def test_fact_sheet_keeps_polygon_counts_separate():
    panel = pd.DataFrame([{
        "사고연도": 2025, "자치구명": "동대문구",
        "고령보행자_사고건수": 132, "고령인구": 72767,
        "고령보행자_사망자수": 4,
    }])
    links = pd.DataFrame([
        {"사고연도": 2025, "자치구명": "동대문구", "다발지역FID": 1, "경계중첩": 0},
        {"사고연도": 2025, "자치구명": "동대문구", "다발지역FID": 2, "경계중첩": 1},
    ])
    result = fact_sheet(panel, links, 2025, "동대문구")
    assert result["accidents"] == 132
    assert result["hotspot_polygons"] == 2
    assert result["nonoverlap_with_available_zone_boundaries"] == 1
    assert result["calculation_status"] == "CHECKED"


def test_no_search_results_no_recommendation():
    with pytest.raises(ValueError, match="검색 결과"):
        recommend({"calculation_status": "CHECKED"}, {"sources": []}, "", "", "")


def test_url_is_unverified_hint():
    assert validate_hint_url("https://example.com/a") == "https://example.com/a"
    with pytest.raises(ValueError):
        validate_hint_url("file:///etc/passwd")
