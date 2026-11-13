"""Daily RSS update must preserve last successful data on failure."""
import json
from pathlib import Path

from newsroom.daily_update import run_once, local_data_status


def fake_result(link):
    return {"sources": [{"source_url": link, "id": "S1", "title": "A",
                          "published_at": "2026-11-13T01:00:00+00:00",
                          "verification_status": "METADATA_ONLY"}],
            "errors": [], "retrieved_at": "2026-11-13T09:00:00+09:00"}


def test_success_and_deduped_followup(tmp_path):
    path = tmp_path / "status.json"
    first = run_once(path, search=lambda *a: fake_result("https://example.org/a"))
    assert first["news"]["status"] == "SUCCESS"
    assert first["news"]["new_count"] == 0
    second = run_once(path, search=lambda *a: fake_result("https://example.org/a"))
    assert second["news"]["new_count"] == 0
    third = run_once(path, search=lambda *a: fake_result("https://example.org/b"))
    assert third["news"]["new_count"] == 1


def test_search_failure_preserves_previous(tmp_path):
    path = tmp_path / "status.json"
    run_once(path, search=lambda *a: fake_result("https://example.org/a"))
    failed = run_once(path, search=lambda *a: {"sources": [], "errors": ["네트워크 오류"]})
    assert failed["news"]["status"] == "FAILED"
    assert failed["news"]["sources"][0]["source_url"] == "https://example.org/a"


def test_local_source_fingerprint_changes_only_on_content(tmp_path):
    folder = tmp_path / "processed"
    folder.mkdir()
    base = local_data_status(folder, {})
    assert base["status"] == "MISSING"
