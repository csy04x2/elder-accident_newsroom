"""S03 saved story idea to draft editor. Desktop Streamlit UI."""
from __future__ import annotations

import streamlit as st

from newsroom.article_draft import (
    draft_for_idea, generate_draft, load_draft, load_idea_context, save_draft,
)
from newsroom.persistence import engine_from_env, recent_saved_ideas


def render():
    st.title("기사 작성·편집")
    st.caption("S03 · DB에 저장된 기사거리에서 시작 · 작성된 기사는 검토대기 상태이며 공개되지 않습니다.")
    try:
        engine = engine_from_env()
        try:
            ideas = recent_saved_ideas(engine, 50)
        finally:
            engine.dispose()
    except Exception as exc:
        st.error(f"DB 기사거리 목록을 가져오지 못했습니다: {type(exc).__name__}. DATABASE_URL을 확인하세요.")
        return
    if not ideas:
        st.info("DB에 저장된 기사거리가 없습니다. S02에서 먼저 선택·저장해 주세요.")
        return
    ids = [int(item["id"]) for item in ideas]
    default_id = st.session_state.pop("s03_requested_idea", None)
    if default_id in ids:
        st.session_state["s03_idea_id"] = default_id
    current = st.session_state.get("s03_idea_id")
    if current not in ids:
        current = ids[0]
        st.session_state["s03_idea_id"] = current
    labels = {int(item["id"]): f'#{item["id"]} · {item["title"]}' for item in ideas}
    idea_id = st.selectbox("저장된 기사거리 선택", ids, format_func=lambda n: labels[n], key="s03_idea_id")
    try:
        engine = engine_from_env()
        try:
            context = load_idea_context(engine, idea_id)
            existing = draft_for_idea(engine, idea_id)
        finally:
            engine.dispose()
    except Exception as exc:
        st.error(f"기사거리 근거를 불러오지 못했습니다: {type(exc).__name__} · {exc}")
        return

    st.subheader("취재 방향과 근거")
    st.write(context["angle"])
    st.caption(f'취재 가능 상태: {context["readiness"]} · 분석 스냅샷 #{context["analysis_id"]} · PASSED')
    with st.expander("검증된 Fact Sheet", expanded=True):
        st.json(context["facts_json"])
        st.caption("PASSED는 저장된 수치의 기본 산식 확인이며 기사 사실 검수가 아닙니다.")
    with st.expander("검색 문서와 확인 상태"):
        if not context["sources"]:
            st.info("연결된 검색 문서가 없습니다. 통계 근거만으로 제한적 초안을 작성할 수 있습니다.")
        for ref in context["sources"]:
            st.markdown(f'**#{ref["id"]} · {ref["title"]}**')
            st.caption(f'{ref["source_org"]} · {ref["verification_status"]}')
            st.link_button("검색 링크 열기", ref["source_url"], key=f's03_source_{ref["id"]}')
            if ref["verification_status"] == "VERIFIED" and ref["content_excerpt"]:
                st.write(ref["content_excerpt"])
            else:
                st.caption("본문 미확인: AI 기사 작성의 사실 근거에서 제외")
    with st.expander("추가 취재가 필요한 사항"):
        for item in context["reporting_gaps_json"].get("gaps", []):
            st.markdown("- " + str(item))

    st.divider()
    if existing:
        st.info(f'이 기사거리에는 기사 초안 #{existing["id"]}이 저장돼 있습니다. 마지막 저장: {existing["updated_at"]}')
    else:
        st.caption("저장된 초안이 없습니다.")
    # A newly loaded idea or article resets editor widgets to that persisted content.
    fingerprint = (idea_id, existing["id"] if existing else None,
                   existing["updated_at"] if existing else None)
    if st.session_state.get("s03_loaded") != fingerprint:
        st.session_state["s03_loaded"] = fingerprint
        st.session_state["s03_title"] = existing["title"] if existing else ""
        st.session_state["s03_body"] = existing["content"] if existing else ""
    if st.button("AI 기사 초안 생성", disabled=bool(existing), type="primary",
                 help="기존 저장 초안은 덮어쓰지 않습니다. 수정은 아래 편집기를 사용하세요."):
        try:
            with st.spinner("검증된 통계와 원문 대조 발췌를 바탕으로 초안 생성 중"):
                draft = generate_draft(context)
            st.session_state["s03_title"] = draft.title
            st.session_state["s03_body"] = draft.content
            st.success("AI 초안을 생성했습니다. 아래 내용을 검토하고 저장해 주세요.")
        except Exception as exc:
            st.error(f"초안 생성 실패: {type(exc).__name__} · {exc if isinstance(exc, (RuntimeError, ValueError)) else 'AI 응답·연결을 확인하세요.'}")
    st.text_input("기사 제목", key="s03_title", max_chars=500)
    st.text_area("기사 본문", key="s03_body", height=420)
    st.warning("현재 기사는 검토대기 초안입니다. 자동 사실 검수·편집장 승인 기능(S04)은 아직 연결되지 않았습니다.")
    if st.button("초안 저장 / 수정 저장", key="s03_save"):
        try:
            engine = engine_from_env()
            try:
                article_id = save_draft(engine, context, st.session_state["s03_title"],
                                        st.session_state["s03_body"], existing)
                saved = load_draft(engine, article_id)
            finally:
                engine.dispose()
            st.session_state["s03_loaded"] = (idea_id, saved["id"], saved["updated_at"])
            st.success(f'기사 #{saved["id"]} DB 저장 성공 · 상태: {saved["status"]} · 자동 검수: 미실시')
        except Exception as exc:
            st.error(f"초안 저장 실패: {type(exc).__name__} · {exc}")
    if existing:
        if st.button("DB에서 저장된 초안 다시 불러오기"):
            st.session_state.pop("s03_loaded", None)
            st.rerun()
