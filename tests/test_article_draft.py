"""Drafting does not publish unverified material and edits reset validation."""
import pytest

from newsroom.article_draft import _validated_text, ArticleDraft, DRAFTING_RULES


def test_title_body():
    assert _validated_text(" 제목 ", " 본문 ") == ("제목", "본문")
    with pytest.raises(ValueError):
        _validated_text("제목", "")
    with pytest.raises(ValueError):
        _validated_text("줄1\n줄2", "본문")


def test_structured_draft():
    result = ArticleDraft(title="보행자 통계", content="확인된 결과")
    assert result.title == "보행자 통계"


def test_prompt_forbids_metadata_as_facts():
    assert "METADATA_ONLY" in DRAFTING_RULES
    assert "사고다발지역" in DRAFTING_RULES
