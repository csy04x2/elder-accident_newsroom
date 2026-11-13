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
from newsroom.recommendation import fact_sheet, recommend, search_sources, validate_hint_url
from newsroom.persistence import engine_from_env, recent_saved_ideas, save_idea
from newsroom.article_ui import render as render_article_editor
from newsroom.review_ui import render as render_review
from newsroom.public_ui import render as render_public_articles

st.set_page_config(page_title="서울 고령 보행자 데이터 뉴스룸", page_icon="🚶", layout="wide")
st.markdown(
    """<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;500;600;700&display=swap');
    html, body, [class*="css"], .stApp {font-family:'IBM Plex Sans KR','Malgun Gothic',sans-serif;}
    .block-container {max-width:1220px;padding-top:2.5rem;}
    [data-testid="stSidebar"] {background:#142238;}
    [data-testid="stSidebar"] * {color:#edf2fb;}
    /* Sidebar buttons have a light background; override the sidebar's white text. */
    [data-testid="stSidebar"] button,
    [data-testid="stSidebar"] button * {color:#142238 !important;}
    .eyebrow {font-size:13px;letter-spacing:.09em;color:#64748b;font-weight:700;}
    .intro {color:#475467;font-size:15px;line-height:1.7;}
    .section-marker {padding-top:16px;color:#a34a19;font-size:13px;font-weight:700;letter-spacing:.08em;}
    .small-note {font-size:12px;color:#64748b;line-height:1.65;}
    [data-testid="stSidebar"] a[href^="#"] {display:block;padding:9px 12px;border-radius:7px;text-decoration:none;transition:background .15s ease;}
    [data-testid="stSidebar"] a[href^="#"].active-analysis {background:#eaf1ff;color:#17375e!important;font-weight:700;}
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
    if st.button("기사 작성·편집", use_container_width=True):
        st.session_state["placeholder_page"] = "기사 작성·편집"
    if st.button("자동 검수·편집장 승인", use_container_width=True):
        st.session_state["placeholder_page"] = "자동 검수·편집장 승인"
    if st.button("승인 기사", use_container_width=True):
        st.session_state["placeholder_page"] = "승인 기사"

if st.session_state.get("placeholder_page") == "승인 기사":
    if st.button("← 뉴스룸 홈으로 돌아가기", key="s05_back"):
        st.session_state.pop("placeholder_page", None)
        st.rerun()
    render_public_articles()
    st.stop()

if st.session_state.get("placeholder_page") == "자동 검수·편집장 승인":
    if st.button("← 뉴스룸 홈으로 돌아가기", key="s04_back"):
        st.session_state.pop("placeholder_page", None)
        st.rerun()
    render_review()
    st.stop()

if st.session_state.get("placeholder_page") == "기사 작성·편집":
    if st.button("← 뉴스룸 홈으로 돌아가기", key="s03_back"):
        st.session_state.pop("placeholder_page", None)
        st.rerun()
    render_article_editor()
    st.stop()

# 화면 전환 상태는 S01에서 선택한 연도·자치구를 유지한다.
if st.session_state.get("placeholder_page") == "AI 기사거리 추천":
    st.title("AI 기사거리 추천")
    st.caption("S02 · 기존 분석 결과 + 최근 정책·보도 검색 · 데스크톱 기준")
    if st.button("← 뉴스룸 홈으로 돌아가기"):
        st.session_state.pop("placeholder_page", None)
        st.rerun()

    state = dataset_state()
    if state["missing"]:
        st.error("기초 분석 CSV가 없습니다: " + ", ".join(state["missing"]))
        st.stop()
    dataset = load_data(state["directory"], state["versions"])
    panel, links = dataset["panel"], dataset["links"]
    years = sorted(panel["사고연도"].dropna().astype(int).unique())
    districts = sorted(panel["자치구명"].dropna().unique())
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        year = st.selectbox("분석 사고연도", years, index=years.index(st.session_state.get("s01_year")) if st.session_state.get("s01_year") in years else len(years)-1, key="s02_year")
    with col2:
        district = st.selectbox("분석 지역", ["서울 전체"] + districts, index=(["서울 전체"] + districts).index(st.session_state.get("s01_district")) if st.session_state.get("s01_district") in (["서울 전체"] + districts) else 0, key="s02_district")
    with col3:
        days = st.selectbox("최근 검색 기간", [30, 90, 365], index=1, format_func=lambda n: f"최근 {n}일")
    facts = fact_sheet(panel, links, year, district)
    st.subheader("분석 근거")
    x1, x2, x3 = st.columns(3)
    x1.metric("고령 보행자 사고", str(facts["accidents"]) if facts["accidents"] is not None else "자료 없음")
    x2.metric("고령인구 1만 명당 사고", str(facts["accidents_per_10000_residents"]) if facts["accidents_per_10000_residents"] is not None else "자료 없음")
    x3.metric("보호구역 경계와 비중첩된 사고다발지역", f'{facts["nonoverlap_with_available_zone_boundaries"]}/{facts["hotspot_polygons"]}곳')
    st.caption(f'분석 자료 기준: {year}년 · 산식 확인: {facts["calculation_status"]} · 개별 사고의 보호구역 밖 발생 비율이 아닙니다.')
    st.divider()
    st.subheader("최근 정책·보도 검색")
    categories = st.multiselect("검색 범주", ["정책", "보도자료", "언론"], default=["정책", "보도자료", "언론"])
    keyword = st.text_input("추가 검색 키워드 (선택)", max_chars=80, placeholder="예: 청량리 노인보호구역")
    with st.expander("기자가 추가한 취재 단서 (선택)"):
        url_input = st.text_input("참고할 원문 URL (미검증 단서)", max_chars=2000)
        memo = st.text_area("취재 메모·자료 내용 (검증되지 않은 입력)", height=120, max_chars=3000)
    signature = (year, district, days, tuple(categories), keyword.strip())
    if st.session_state.get("s02_signature") != signature:
        st.session_state["s02_signature"] = signature
        st.session_state.pop("s02_search", None)
        st.session_state.pop("s02_ideas", None)
        st.session_state.pop("s02_selected_idea", None)
        st.session_state.pop("s02_selected_index", None)
    left, right = st.columns([1, 1])
    with left:
        search_clicked = st.button("최신 자료 다시 검색", use_container_width=True, disabled=not categories)
    with right:
        generate_clicked = st.button("AI 기사거리 추천 생성", type="primary", use_container_width=True)
    if search_clicked:
        with st.spinner("정책·보도 검색 중"):
            st.session_state["s02_search"] = search_sources(days, categories, keyword)
            st.session_state.pop("s02_ideas", None)
            st.session_state.pop("s02_selected_idea", None)
            st.session_state.pop("s02_selected_index", None)
    search = st.session_state.get("s02_search")
    if generate_clicked:
        try:
            validated_url = validate_hint_url(url_input)
            if not search:
                if not categories:
                    raise ValueError("검색 범주를 하나 이상 선택하세요.")
                with st.spinner("정책·보도 검색 중"):
                    search = search_sources(days, categories, keyword)
                    st.session_state["s02_search"] = search
            with st.spinner("근거 범위 내 기사거리 구성 중"):
                st.session_state["s02_ideas"] = recommend(facts, search, keyword, validated_url, memo)
                st.session_state.pop("s02_selected_idea", None)
                st.session_state.pop("s02_selected_index", None)
        except (ValueError, RuntimeError) as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"추천 생성 실패: {type(exc).__name__}")
            # 로컬 개발 중에는 실제 실패 위치를 확인한다. 배포 환경에는 상세 예외를 노출하지 않는다.
            import os
            if os.getenv("APP_ENV", "development") == "development":
                st.exception(exc)
            else:
                st.caption("서버 로그에서 실패 원인을 확인하세요.")
    search = st.session_state.get("s02_search")
    if search:
        st.caption(f'검색 확인 시각: {search["retrieved_at"]} · 최근 {search["days"]}일 · 검색 항목 {len(search["sources"])}건')
        if search["errors"]:
            st.warning(" / ".join(search["errors"]) + " · 검색 실패는 관련 기사 부재가 아닙니다.")
        st.info("검색 결과는 제목·발행처·발행일 메타데이터입니다. 기사 원문 내용은 검증하지 않았습니다. 검색 누락 가능성이 있습니다.")
        with st.expander("검색된 자료 목록", expanded=True):
            for item in search["sources"]:
                st.markdown(f'**{item["id"]} · {item["title"]}** · {item["source_org"]} · {item["source_type"]}')
                st.caption(f'{item["published_at"][:10]} · METADATA_ONLY')
                st.link_button("검색 결과 열기", item["source_url"], key=f'src_{item["id"]}')
    else:
        st.caption("이 세션에서 아직 최신 검색을 실행하지 않았습니다. 검색·추천 버튼을 누르면 실행됩니다.")
    st.divider()
    st.subheader("추천 기사거리")
    ideas = st.session_state.get("s02_ideas")
    if ideas is None:
        st.info("검색 결과를 검토한 뒤 'AI 기사거리 추천 생성'을 눌러주세요. 추천은 아직 준비되지 않았습니다.")
    elif not ideas:
        st.info("현재 조건에서 추천할 후보가 없습니다. 검색 범위나 취재 단서를 조정해 다시 시도할 수 있습니다.")
    else:
        refs = {s["id"]: s for s in search["sources"]}
        for idx, idea in enumerate(ideas, 1):
            with st.container(border=True):
                st.caption(f'후보 {idx} · {idea["readiness"]} · 추가 취재 필요')
                st.subheader(idea["title"])
                st.markdown("**취재 방향**")
                st.write(idea["angle"])
                st.markdown("**뉴스 가치 및 기존 보도와 비교할 점**")
                st.write(idea["news_value"])
                st.markdown("**분석 근거**")
                st.write(idea["evidence"])
                st.markdown("**추가 취재·확인 항목**")
                for gap in idea["reporting_gaps"]:
                    st.markdown("- " + gap)
                st.markdown("**연관 검색 결과 (본문 미확인)**")
                for sid in idea["source_ids"]:
                    src = refs.get(sid)
                    if src:
                        st.markdown(f'[{sid} · {src["title"]}]({src["source_url"]})')
                if st.button("취재 후보로 선택", key=f"idea_{idx}"):
                    st.session_state["s02_selected_idea"] = idea
                    st.session_state["s02_selected_index"] = idx - 1
                    st.success("선택한 후보를 이 세션에 보관했습니다. 아래에서 원문 대조 후 저장할 수 있습니다.")
        if st.session_state.get("s02_selected_index") is not None:
            selected_idx = st.session_state["s02_selected_index"]
            if selected_idx < len(ideas):
                selected = ideas[selected_idx]
                st.divider()
                st.subheader("선택한 기사거리 저장")
                st.write(selected["title"])
                st.caption("검색 목록은 RSS 제목 정보만 확인됐습니다. 링크의 실제 원문을 직접 열어 동일 문구를 확인한 경우에만 대조 발췌문을 입력하세요.")
                excerpts = {}
                for sid in selected["source_ids"]:
                    src = refs.get(sid)
                    if not src:
                        continue
                    with st.expander(f'원문 대조 · {sid} · {src["title"]}'):
                        st.link_button("원문 링크 열어 확인", src["source_url"], key=f'check_url_{sid}')
                        checked = st.checkbox("발행사 또는 공식 기관 원문에서 아래 발췌문을 직접 대조했습니다", key=f"verified_{sid}")
                        snippet = st.text_area("원문에 실제로 있는 문구 (최대 4,000자)", key=f"excerpt_{sid}", max_chars=4000)
                        if checked and snippet.strip():
                            excerpts[sid] = snippet.strip()
                        elif checked and not snippet.strip():
                            st.warning("대조 확인을 표시했다면 실제 원문 발췌문을 입력해야 합니다.")
                        elif snippet.strip():
                            st.info("대조 확인을 체크하지 않아 이 자료는 METADATA_ONLY로 저장됩니다.")
                if st.button("선택 기사거리 DB 저장", type="primary", key="s02_save"):
                    try:
                        engine = engine_from_env()
                        try:
                            new_id = save_idea(engine, facts, selected, search["sources"], excerpts)
                        finally:
                            engine.dispose()
                        st.success(f"DB 저장 완료 · 기사거리 ID #{new_id} · S03 기능은 아직 구현되지 않았습니다.")
                        st.session_state["s02_last_saved_id"] = new_id
                        st.session_state["s03_requested_idea"] = new_id
                    except Exception as exc:
                        st.error(f"DB 저장 실패 ({type(exc).__name__}). MySQL 연결·db/schema.sql 적용 여부를 확인하세요. 저장 성공으로 처리하지 않았습니다.")
    if st.button("DB에 저장된 기사거리 보기", key="s02_list_saved"):
        try:
            engine = engine_from_env()
            try:
                st.session_state["s02_saved_rows"] = recent_saved_ideas(engine)
            finally:
                engine.dispose()
        except Exception as exc:
            st.error(f"저장 목록 조회 실패 ({type(exc).__name__}). DB 접속 설정을 확인하세요.")
    for row in st.session_state.get("s02_saved_rows", []):
        st.caption(f'#{row["id"]} · {row["readiness"]} · {row["created_at"]}')
        st.markdown(f'**{row["title"]}** · {row["angle"][:200]}')
        if st.button("이 기사거리로 작성", key=f's02_to_s03_{row["id"]}'):
            st.session_state["s03_requested_idea"] = int(row["id"])
            st.session_state["placeholder_page"] = "기사 작성·편집"
            st.rerun()
    st.caption("수동 원문 대조는 발췌 확인 기록일 뿐 기사 전체 검증이 아닙니다. READY 판정 및 S03 기사 작성은 아직 미구현입니다.")
    st.stop()

if st.session_state.get("placeholder_page"):
    st.info("이 화면은 아직 구현되지 않았습니다.")
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
st.markdown('<div class="eyebrow">SEOUL · ELDERLY PEDESTRIAN SAFETY</div>', unsafe_allow_html=True)
st.title("노인보행자 교통사고 데이터 뉴스룸")
st.markdown("**분석 조건**")
filter_year, filter_district, _ = st.columns([1, 2, 2])
with filter_year:
    year = st.selectbox("사고 연도", years, index=len(years) - 1, key="s01_year")
with filter_district:
    district = st.selectbox("지역", ["서울 전체"] + districts, key="s01_district")
st.caption("통계는 실시간 사고 집계가 아닙니다.")

current = panel[panel["사고연도"] == year]
previous = panel[panel["사고연도"] == year - 1]
if district != "서울 전체":
    current = current[current["자치구명"] == district]
    previous = previous[previous["자치구명"] == district]
summary = metric_summary(current, previous)
place = "서울" if district == "서울 전체" else district

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

# 분석 섹션을 모두 렌더링한 다음 실제 스크롤 위치에 맞춰 사이드바 링크를 강조합니다.
# st.html의 JS는 Streamlit 본문과 같은 document에서 실행됩니다 (>=1.52).
st.html("""
<script>
(() => {
  // Streamlit 재실행 시 이전 이벤트 리스너를 정리합니다.
  if (window.__elderNewsroomScrollSpyCleanup) {
    window.__elderNewsroomScrollSpyCleanup();
  }
  const ids = ["protect", "where", "spatial", "policy"];
  const markers = ids.map(id => document.getElementById(id));
  const links = ids.map(id =>
    document.querySelector('[data-testid="stSidebar"] a[href="#' + id + '"]')
  );
  if (markers.some(el => !el) || links.some(el => !el)) return;

  function refresh() {
    // 화면 상단에서 180px 아래까지 진입한 마지막 분석 섹션을 활성화.
    // Streamlit의 실제 스크롤 컨테이너 종류와 무관하게 좌표로 판정.
    let active = 0;
    markers.forEach((element, index) => {
      if (element.getBoundingClientRect().top <= 180) active = index;
    });
    // 짧은 마지막 섹션도 맨 아래까지 내려가면 선택되도록 처리.
    const scroller = document.querySelector('[data-testid="stMain"]') ||
                     document.scrollingElement;
    if (scroller && scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight < 16) {
      active = ids.length - 1;
    }
    links.forEach((link, index) => {
      link.classList.toggle("active-analysis", index === active);
      if (index === active) link.setAttribute("aria-current", "location");
      else link.removeAttribute("aria-current");
    });
  }

  // capture를 써서 본문 내부 스크롤에도 반응하고 스크롤 시 앱을 재실행하지 않습니다.
  let frame = 0;
  const update = () => {
    if (!frame) frame = requestAnimationFrame(() => {
      frame = 0;
      refresh();
    });
  };
  document.addEventListener("scroll", update, true);
  window.addEventListener("resize", update);
  refresh();
  window.__elderNewsroomScrollSpyCleanup = () => {
    document.removeEventListener("scroll", update, true);
    window.removeEventListener("resize", update);
    if (frame) cancelAnimationFrame(frame);
  };
})();
</script>
""", unsafe_allow_javascript=True)
