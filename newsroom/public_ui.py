"""S05 reader page: published articles and their stored evidence."""
from __future__ import annotations

import streamlit as st

from newsroom.persistence import engine_from_env
from newsroom.publication import approved_article, approved_articles


def render() -> None:
    st.title("승인 기사")
    st.caption("고령 보행자 사고 데이터 뉴스룸 · 편집장 승인 기사만 공개")
    try:
        engine = engine_from_env()
        try:
            articles = approved_articles(engine)
        finally:
            engine.dispose()
    except Exception as exc:
        st.error(f"승인 기사 조회에 실패했습니다 ({type(exc).__name__}). 데이터베이스 연결을 확인하세요.")
        return

    if not articles:
        st.info("현재 공개된 기사가 없습니다.")
        return

    valid_ids = {row["id"] for row in articles}
    selected = st.session_state.get("s05_selected_article")
    if selected not in valid_ids:
        st.session_state.pop("s05_selected_article", None)
        selected = None

    if selected is None:
        st.subheader("최근 승인 기사")
        for row in articles:
            with st.container(border=True):
                st.caption(f'발행 {row["published_at"]:%Y-%m-%d %H:%M} · 기사 #{row["id"]}')
                st.markdown(f'**{row["title"]}**')
                if st.button("기사 읽기", key=f's05_open_{row["id"]}'):
                    st.session_state["s05_selected_article"] = int(row["id"])
                    st.rerun()
        return

    if st.button("← 승인 기사 목록", key="s05_list"):
        st.session_state.pop("s05_selected_article", None)
        st.rerun()

    try:
        engine = engine_from_env()
        try:
            article = approved_article(engine, int(selected))
        finally:
            engine.dispose()
    except Exception as exc:
        st.error(f"기사 내용을 불러오지 못했습니다 ({type(exc).__name__}).")
        return
    if article is None:
        st.warning("이 기사는 공개 상태가 아니거나 존재하지 않습니다.")
        st.session_state.pop("s05_selected_article", None)
        return

    st.title(article["title"])
    st.caption(f'발행 {article["published_at"]:%Y-%m-%d %H:%M} · 편집장 승인 완료')
    # Source text is plain content, not interpreted as HTML or untrusted Markdown.
    st.text(article["content"])

    st.divider()
    st.subheader("자료 기준과 출처")
    if not article["evidence"]:
        st.warning("연결된 근거 정보가 없습니다.")
    for index, item in enumerate(article["evidence"]):
        if item["evidence_role"] == "STATISTIC":
            st.markdown("**통계·분석 자료**")
            if item["data_as_of"]:
                st.caption(f'분석 기준일: {item["data_as_of"]:%Y-%m-%d} (공식 데이터 최종 공개일과 다를 수 있음)')
            facts = item.get("facts_json") or {}
            st.write(f'분석 범위: {facts.get("accident_year", "미상")}년 · {facts.get("region", "미상")}')
            st.caption("고령인구는 거주지, 사고는 발생지 기준. 사고다발지역은 개별 사고가 아닌 선정된 구역입니다.")
            info = item.get("source_info_json") or {}
            st.caption(f'분석 원자료: {info.get("source", "출처 정보 없음")}')
            st.markdown("[원자료 분석 저장소](https://github.com/csy04x2/elder_accident)")
        elif item["evidence_role"] == "CONTEXT":
            st.markdown(f'**참고 문서 · {item.get("source_title") or "제목 미상"}**')
            st.caption(f'{item.get("source_org") or "발행처 미상"} · 상태: {item.get("verification_status") or "미상"}')
            if item.get("source_url"):
                st.link_button("원문 링크", item["source_url"], key=f's05_src_{index}')
            if item.get("content_excerpt") and item.get("verification_status") == "VERIFIED":
                st.caption("기자가 원문과 대조한 발췌")
                st.text(item["content_excerpt"])
    st.caption("이 화면은 저장된 출처와 근거를 표시합니다. 독립적인 최신 자료 재검증을 수행하지는 않습니다.")
