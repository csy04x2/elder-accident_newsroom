"""S02 persistence: no external DB required for deterministic preflight."""
import pytest

from newsroom.persistence import checked_facts, as_naive_datetime, source_key


def test_checked_snapshot():
    row = dict(calculation_status="CHECKED", accidents=10, elderly_residents=10000,
               accidents_per_10000_residents=10.0, hotspot_polygons=3,
               overlap_with_available_zone_boundaries=1,
               nonoverlap_with_available_zone_boundaries=1, unclassified_hotspot_polygons=1)
    assert checked_facts(row)
    row["accidents_per_10000_residents"] = 11.0
    assert not checked_facts(row)


def test_stable_source_hash():
    source = {"source_url": "https://example.com/item"}
    assert source_key(source) == source_key(source)


def test_datetime_utc_conversion():
    assert as_naive_datetime("2026-11-13T14:00:00+09:00").hour == 5
