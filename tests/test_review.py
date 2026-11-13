import copy
from newsroom.review import digest, grounding, numeric, editor_password_valid

def sample():
    return {"title":"서울 사고","content":"고령 보행자 사고 999건","idea_analysis_id":1,
     "evidence":[{"evidence_role":"STATISTIC","analysis_id":1,"source_document_id":None,
     "payload":{"verification_status":"PASSED","facts_json":{
       "calculation_status":"CHECKED","accidents":132,"elderly_residents":72767,
       "accidents_per_10000_residents":18.14,"hotspot_polygons":2,
       "overlap_with_available_zone_boundaries":1,
       "nonoverlap_with_available_zone_boundaries":1,
       "unclassified_hotspot_polygons":0}}}]}

def test_wrong_number():
    assert numeric(sample())[0]["category"]=="NUMBER"

def test_hash_changes():
    a=sample();before=digest(a);a["content"]="수정"
    assert digest(a)!=before

def test_no_password(monkeypatch):
    monkeypatch.delenv("EDITOR_PASSWORD_HASH",raising=False)
    assert not editor_password_valid("guess")


def test_validation_prompt_does_not_reject_historical_year_or_descriptive_rate():
    from newsroom.review import PROMPT
    assert "today_kst" in PROMPT
    assert "거주지 고령인구" in PROMPT
    assert "미래 데이터" in PROMPT
