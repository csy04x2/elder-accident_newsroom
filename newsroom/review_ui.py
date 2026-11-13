"""S04 editor checks & decision screen."""
import os
import streamlit as st
from newsroom.persistence import engine_from_env
from newsroom.review import context,list_articles,validate,decide,CHECKS

def render():
    st.title("자동 검수·편집장 승인")
    st.caption("S04 · 검수 PASS와 사람 승인 모두 통과해야만 공개")
    try:
        engine=engine_from_env()
        try:rows=list_articles(engine)
        finally:engine.dispose()
    except Exception as exc:
        st.error(f"기사 목록 DB 오류: {type(exc).__name__}");return
    if not rows:st.info("S03에서 기사 초안을 먼저 저장하세요.");return
    ids={int(r["id"]):r for r in rows}
    id=st.selectbox("검수할 기사",list(ids),format_func=lambda k:f'#{k} · {ids[k]["title"]} · {ids[k]["status"]}')
    engine=engine_from_env()
    try:
        with engine.connect() as conn:a=context(conn,id)
    finally:engine.dispose()
    l,r=st.columns([3,2])
    with l:
        st.subheader(a["title"]);st.caption(f'상태: {a["status"]}')
        st.text(a["content"])
    with r:
        st.subheader("근거")
        for e in a["evidence"]:
            st.caption(f'{e["evidence_role"]} · 분석 #{e["analysis_id"] or "-"} · 자료 #{e["source_document_id"] or "-"}')
            p=e["payload"]
            if not p:st.error("근거 누락")
            elif e["evidence_role"]=="STATISTIC":st.json(p["facts_json"])
            else:
                st.write(p["title"],p["verification_status"])
                st.write(p["content_excerpt"])
                st.link_button("링크 열기",p["source_url"])
    if a["status"]=="검토대기" and st.button("자동 사실 검수 실행",type="primary"):
        try:
            engine=engine_from_env()
            try:result=validate(engine,id)
            finally:engine.dispose()
            st.success("검수 PASS" if result["passed"] else "검수 FAIL")
            st.rerun()
        except Exception as exc:
            st.error(f"자동 검수 실패: {type(exc).__name__} · {exc}")
    report=a["validation_result"]
    if report:
        st.subheader("자동 검수 결과")
        st.write("PASS" if report["passed"] else "FAIL")
        for issue in report.get("issues",[]):
            st.warning(f'{issue.get("category","ISSUE")} · {issue.get("excerpt","")} · {issue.get("reason","")}')
    st.divider()
    st.subheader("편집장 검토")
    if a["status"]!="검토대기":st.info("이미 승인·보류된 기사입니다.");return
    if not os.getenv("EDITOR_PASSWORD_HASH"):
        st.warning("EDITOR_PASSWORD_HASH 미설정: 승인·보류 불가. README 설정 참조")
    checks=[st.checkbox(c,key=f"review_{id}_{i}") for i,c in enumerate(CHECKS)]
    reviewer=st.text_input("편집장 이름",max_chars=100)
    password=st.text_input("편집장 비밀번호",type="password")
    note=st.text_area("검토 메모/보류 사유",max_chars=3000)
    c1,c2=st.columns(2)
    action=None
    if c1.button("최종 승인",disabled=not a["validation_passed"] or not all(checks)):action=True
    if c2.button("보류"):action=False
    if action is not None:
        try:
            engine=engine_from_env()
            try:status=decide(engine,id,reviewer,password,checks,action,note)
            finally:engine.dispose()
            st.success(f'기사 #{id}: {status}')
            st.rerun()
        except Exception as exc:st.error(f"상태 변경 실패: {type(exc).__name__} · {exc}")
