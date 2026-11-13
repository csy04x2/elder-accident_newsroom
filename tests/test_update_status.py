from newsroom.update_status import search_from_daily


def test_reuses_successful_daily_news_only():
    status={"news":{"status":"SUCCESS","sources":[{"id":"S1","source_url":"https://example.org/a"}],
                    "last_success_at":"2026-11-13T09:00:00+09:00"}}
    assert search_from_daily(status)["sources"][0]["id"]=="S1"
    status["news"]["status"]="PARTIAL"
    assert search_from_daily(status) is None
