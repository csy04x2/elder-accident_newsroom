"""S01 서울 고령 보행자 데이터 뉴스룸: 기존 elder_accident 가공 자료를 읽는 화면."""
from __future__ import annotations

import json
from html import escape

import folium
import pandas as pd
import plotly.express as px
import streamlit as st
from shapely import wkt
from shapely.geometry import mapping
from streamlit_folium import st_folium

from newsroom.data import dataset_state, load_data, metric_summary, spatial_summary

st.set_page_config(page_title="서울 고령 보행자 데이터 뉴스룸", page_icon="🚶", layout="wide")
st.markdown(
    """<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;500;600;700&display=swap');
    html, body, [class*="css"], .stApp {font-family:'IBM Plex Sans KR','Malgun Gothic',sans-serif;}
    .block-container {max-width:1220px;padding-top:2.5rem;}
    [data-testid="stSidebar"] {background:#142238;}
    [data-testid="stSidebar"] * {color:#edf2fb;}
    .eyebrow {font-size:13px;letter-spacing:.09em;color:#64748b;font-weight:700;}
    .intro {color:#475467;font-size:15px;line-height:1.7;}
    .section-marker {padding-top:16px;color:#a34a19;font-size:13px;font-weight:700;letter-spacing:.08em;}
    .small-note {font-size:12px;color:#64748b;line-height:1.65;}
    </style>""", unsafe_allow_html=True
)

SECTIONS = [
    ("protect", "왜 보호가 필요한가?"),
    ("where", "어디가 위험한가?"),
    ("spatial", "어디를 우선 검토해야 하는가?"),
    ("policy", "무엇을 개선해야 하는가?"),
]
with st.sidebar:
    st.title("서울 보행안전")
    st.caption("ELDER ACCIDENT NEWSROOM")
    st.markdown("**뉴스룸 홈 · 심층 분석**")
    st.markdown("### 분석 목차")
    for anchor, name in SECTIONS:
        st.markdown(f'<a href="#{anchor}" target="_self">{escape(name)}</a>', unsafe_allow_html=True)
    st.divider()
    if st.button("AI 기사거리 추천", use_container_width=True):
        st.session_state["placeholder_page"] = "AI 기사거리 추천"
    st.caption("S02–S05는 다음 구현 단계에서 연결됩니다.")

if st.session_state.get("placeholder_page"):
    st.info(f'{st.session_state["placeholder_page"]} 기능은 아직 구현되지 않았습니다.')
    if st.button("뉴스룸 홈으로 돌아가기"):
        st.session_state.pop("placeholder_page", None)
        st.rerun()
    st.stop()

state = dataset_state()
if state["missing"]:
    st.title("서울 고령 보행자 데이터 뉴스룸")
    st.error("기존 분석 자료를 찾을 수 없습니다. 통계를 임의로 표시하지 않습니다.")
    st.code("DATA_DIR=../elder_accident/data/processed", language="ini")
    st.write("누락 파일: " + ", ".join(state["missing"]))
    st.caption(f'현재 검색 경로: {state["directory"]}')
    st.stop()

data = load_data(state["directory"], state["versions"])
panel = data["panel"]
links = data["links"]
hotspots = data["hotspots"]
zones = data["zones"]

years = sorted(panel["사고연도"].dropna().astype(int).unique().tolist())
districts = sorted(panel["자치구명"].dropna().astype(str).unique().tolist())
with st.sidebar:
    year = st.selectbox("사고 연도", years, index=len(years) - 1)
    district = st.selectbox("지역", ["서울 전체"] + districts)
    st.caption("통계는 실시간 사고 집계가 아닙니다.")

current = panel[panel["사고연도"] == year]
previous = panel[panel["사고연도"] == year - 1]
if district != "서울 전체":
    current = current[current["자치구명"] == district]
    previous = previous[previous["자치구명"] == district]
summary = metric_summary(current, previous)
place = "서울" if district == "서울 전체" else district

st.markdown('<div class="eyebrow">SEOUL · ELDERLY PEDESTRIAN SAFETY</div>', unsafe_allow_html=True)
st.title("노인보행자 교통사고 데이터 뉴스룸")
st.markdown(f'<p class="intro">{escape(place)}의 공식 사고 통계와 기존 공간 분석으로 보행 안전의 사각지대를 살펴봅니다. 아래 분석은 정책 효과를 판정하는 것이 아니라 추가 취재가 필요한 지점을 찾는 자료입니다.</p>', unsafe_allow_html=True)
st.caption(f"사고 통계 기준: {year}년 · 데이터 출처: 한국도로교통공단 TAAS, 서울 열린데이터광장 등 · 서비스의 마지막 원격 수집 시각: 미연동")
st.caption("기존 CSV 파일을 로컬에서 읽는 상태입니다. 앱을 열거나 새로고침한 시각은 공식 자료의 갱신 시각이 아닙니다.")

k1, k2, k3, k4 = st.columns(4)
k1.metric("고령 보행자 사고", summary["accidents_display"], summary["accidents_delta"])
k2.metric("고령 보행 사망자", summary["deaths_display"], summary["deaths_delta"])
k3.metric("고령인구 1만 명당 사고", summary["rate_display"], help="지역 발생 사고건수 ÷ 해당 지역 65세 이상 거주인구 × 10,000. 실제 보행량을 보정한 위험률은 아닙니다.")
k4.metric("전체 보행 사망자 중 고령층", summary["death_share_display"], help="고령 보행 사망자 ÷ 전체 보행 사망자. 사고당 치명률과 다릅니다.")
st.caption("증감은 전년 대비이며, 전년 자료가 없으면 표시하지 않습니다. 각 수치는 선택 지역에서 발생한 사고 기준입니다.")
st.divider()

def section(anchor: str, idx: int, name: str, caption: str) -> None:
    st.markdown(f'<div id="{anchor}" class="section-marker">{idx:02d} / ANALYSIS</div>', unsafe_allow_html=True)
    st.header(name)
    st.caption(caption)

def present(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    view = df[[c for c in columns if c in df.columns]].copy()
    return view

section("protect", 1, "왜 보호가 필요한가?", "고령인구 변화와 보행 사고·사망 피해를 함께 살펴봅니다.")
scope_panel = panel if district == "서울 전체" else panel[panel["자치구명"] == district]
trend = scope_panel.groupby("사고연도", as_index=False)[["고령인구", "고령보행자_사고건수"]].sum(min_count=1)
c1, c2 = st.columns(2)
with c1:
    fig = px.line(trend, x="사고연도", y="고령인구", markers=True, labels={"사고연도": "연도", "고령인구": "65세 이상 거주인구 (명)"})
    fig.update_traces(line_color="#1d4ed8")
    fig.update_xaxes(dtick=1)
    st.plotly_chart(fig, use_container_width=True)
with c2:
    fig = px.bar(trend, x="사고연도", y="고령보행자_사고건수", labels={"사고연도": "연도", "고령보행자_사고건수": "고령 보행자 사고 (건)"})
    fig.update_traces(marker_color="#c2410c")
    fig.update_xaxes(dtick=1, type="category")
    st.plotly_chart(fig, use_container_width=True)
st.info("거주인구는 해당 지역을 실제로 걸은 사람의 수가 아닙니다. 사고 발생 지역과 인구의 거주지가 다를 수 있습니다.")

section("where", 2, "어디가 위험한가?", f"{year}년 서울 25개 자치구의 고령인구 대비 사고 건수를 비교합니다.")
ranking = panel[panel["사고연도"] == year].copy()
ranking["고령보행자_사고건수"] = pd.to_numeric(ranking["고령보행자_사고건수"], errors="coerce")
ranking["고령인구"] = pd.to_numeric(ranking["고령인구"], errors="coerce")
ranking["사고율"] = ranking["고령보행자_사고건수"] / ranking["고령인구"].where(ranking["고령인구"] > 0) * 10000
ranking = ranking.sort_values("사고율", ascending=False, na_position="last")
chart = px.bar(ranking.dropna(subset=["사고율"]), x="사고율", y="자치구명", orientation="h",
               labels={"사고율": "65세 이상 거주인구 1만 명당 사고 (건)", "자치구명": ""},
               color_discrete_sequence=["#c2410c"])
chart.update_layout(height=700, yaxis={"categoryorder": "total ascending"}, showlegend=False)
st.plotly_chart(chart, use_container_width=True)
with st.expander("서울 자치구별 원자료 지표"):
    st.dataframe(present(ranking, ["자치구명", "고령인구", "고령보행자_사고건수", "고령보행자_사망자수", "사고율"]), hide_index=True, use_container_width=True)
st.caption("서울 전체 사고율은 자치구 사고율의 단순 평균이 아니라 전체 사고건수 ÷ 전체 고령인구로 계산합니다.")

section("spatial", 3, "어디를 우선 검토해야 하는가?", "공식 선정 사고다발지역 폴리곤과 확보된 노인보호구역 API 경계를 비교합니다.")
spatial = spatial_summary(links, year, district)
a, b, c = st.columns(3)
a.metric("비교 가능한 사고다발지역", spatial["total"])
b.metric("보호구역 경계와 겹침", spatial["overlap"])
c.metric("보호구역 경계와 비중첩", spatial["outside"])
if spatial["unknown"]:
    st.warning(f'중첩 여부를 알 수 없는 기록 {spatial["unknown"]}곳은 겹침·비중첩 통계에서 제외했습니다.')
st.warning("위 수치는 사고다발지역의 폴리곤 개수이지 개별 교통사고의 위치·발생 비율이 아닙니다. 확보된 API 경계에는 공식 지정 명단의 일부 시설이 빠져 있어, 비중첩을 정책 실패나 사고 예방 효과 부재로 단정할 수 없습니다.")
filtered_h = hotspots[(hotspots["사고연도"] == year)]
filtered_z = zones if district == "서울 전체" else zones[zones["자치구명"] == district]
if district != "서울 전체":
    filtered_h = filtered_h[filtered_h["자치구명"] == district]
if not filtered_h.empty and {"경도", "위도"}.issubset(filtered_h.columns):
    centers = filtered_h[["위도", "경도"]].apply(pd.to_numeric, errors="coerce").dropna()
    loc = centers.mean().tolist() if len(centers) else [37.5665, 126.978]
    m = folium.Map(location=loc, zoom_start=11 if district == "서울 전체" else 13, tiles="OpenStreetMap")
    for _, record in filtered_z.iterrows():
        boundary = record.get("경계WKT")
        if pd.isna(boundary):
            continue
        try:
            shape = mapping(wkt.loads(boundary))
            folium.GeoJson(shape, style_function=lambda _: {"color": "#1d4ed8", "weight": 2, "fillOpacity": .2},
                           tooltip=f'노인보호구역: {escape(str(record.get("API시설명", "이름 없음")))}').add_to(m)
        except (ValueError, TypeError):
            continue
    for _, record in filtered_h.iterrows():
        longitude = pd.to_numeric(record.get("경도"), errors="coerce")
        latitude = pd.to_numeric(record.get("위도"), errors="coerce")
        if pd.isna(longitude) or pd.isna(latitude):
            continue
        folium.CircleMarker([latitude, longitude], radius=5, weight=1, color="#c2410c",
                            fill=True, fill_opacity=.85,
                            tooltip=str(record.get("지점명", "사고다발지역"))).add_to(m)
    st_folium(m, width=None, height=490, returned_objects=[])
    st.caption("주황 점은 사고다발지역의 대표 좌표입니다. 실제 중첩 판정은 점이 아니라 폴리곤 경계를 기준으로 계산한 기존 CSV 결과를 사용합니다.")
else:
    st.info("선택 범위에서 표시 가능한 사고다발지역 좌표가 없습니다.")
with st.expander("사고다발지역의 보호구역 거리 자료"):
    filtered_links = links[links["사고연도"] == year]
    if district != "서울 전체":
        filtered_links = filtered_links[filtered_links["자치구명"] == district]
    st.dataframe(present(filtered_links, ["자치구명", "지점명", "최단거리_m", "경계중첩", "최근접_API시설명"]), hide_index=True, use_container_width=True)

section("policy", 4, "무엇을 개선해야 하는가?", "기존 분석에서 확인된 사실과 아직 확인하지 못한 행정 판단을 구분합니다.")
st.markdown("""
**확인된 분석:** 공식 사고다발지역의 상당수는 확보된 보호구역 API 경계와 겹치지 않습니다.
이 위치 차이는 안전시설 개선의 우선순위를 취재할 단서가 됩니다.

**추가 확인이 필요한 사항:** 실제 보호구역 지정 고시일과 경계, 행정기관의 사고자료 활용 여부,
개별 개선공사 범위, 동일 공간·비교 가능한 기간의 지정 전후 사고 변화입니다.
""")
st.info("보호구역 경계가 없는 시설이 있고 사고다발지역 선정 기준도 연도별로 다릅니다. 지도에 보이는 현재 경계를 과거 지정 당시 경계로 간주하지 않습니다.")
st.markdown("원자료·분석 방법·한계: [elder_accident 연구 저장소](https://github.com/csy04x2/elder_accident)")
st.divider()
st.caption("이 화면은 기존 가공자료를 읽는 S01 첫 구현입니다. 새 공식 통계 자동 수집, 정책·뉴스 검색, AI 기사거리 추천과 기사 승인·공개는 아직 연결하지 않았습니다.")
