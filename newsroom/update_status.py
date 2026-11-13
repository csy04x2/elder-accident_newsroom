"""Read-only status view of scheduled refresh; does not initiate network calls."""
import json

from newsroom.daily_update import STATE_PATH


def read_daily_status():
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def search_from_daily(status):
    """Compatible with S02 search_sources() for no-custom-keyword 90-day search."""
    if not status or status.get("news", {}).get("status") != "SUCCESS":
        return None
    news = status["news"]
    sources = news.get("sources", [])
    if not sources:
        return None
    return {
        "sources": sources,
        "errors": [],
        "retrieved_at": news["last_success_at"],
        "search_complete": True,
        "searched_categories": ["정책", "보도자료", "언론"],
        "days": 90,
    }
