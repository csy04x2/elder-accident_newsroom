"""Streamlit 뉴스룸 화면의 최소 진입점. 실제 분석과 기사 기능은 미구현."""
import streamlit as st

st.set_page_config(page_title="노인보행자 교통사고 데이터 뉴스룸", page_icon="🚶", layout="wide")

PAGES = {
    "뉴스룸 홈 / 분석": "S01",
    "AI 기사거리 추천": "S02",
    "기사 작성·편집": "S03",
    "검수·편집장 승인": "S04",
    "승인 기사": "S05",
}

with st.sidebar:
    st.title("데이터 뉴스룸")
    page = st.radio("화면", list(PAGES), label_visibility="collapsed")

st.title(page)
st.info(f"{PAGES[page]} 화면 뼈대입니다. 데이터와 기능은 아직 연결되지 않았습니다.")
st.caption("실제 통계 기준일·수집 시각은 데이터 연동 후 별도로 표시합니다.")
