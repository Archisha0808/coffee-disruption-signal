"""Saved briefing and outlook for the public dashboard. Offline."""
from datetime import datetime, timezone

import pytest

from src.advisory import snapshot as snap

BRIEFING = {"headline": "Frost risk lifts arabica", "model_generated": True,
            "accepted_documents": [{"document_id": "a1", "title": "Frost", "url": "http://x/1",
                                    "text": "the article body, never saved"}]}
OUTLOOK = {"lean": "upward", "n_upward": 3, "n_downward": 1, "n_neutral": 2,
           "accepted_documents": []}


def test_a_model_written_briefing_is_saved_without_article_text(tmp_path):
    when = datetime(2026, 11, 18, 9, 0, tzinfo=timezone.utc)
    snap.save("daily_briefing", BRIEFING, results_dir=tmp_path, now=when)
    data, saved_at = snap.load("daily_briefing", results_dir=tmp_path)
    assert data["headline"] == "Frost risk lifts arabica"
    assert data["accepted_documents"] == [{"document_id": "a1", "title": "Frost", "url": "http://x/1"}]
    assert saved_at == "2026-11-18T09:00:00Z" and snap.saved_on(saved_at) == "18 Nov 2026"


def test_a_fallback_is_never_saved_over_a_good_snapshot(tmp_path):
    snap.save("price_outlook", OUTLOOK, results_dir=tmp_path)
    for bad in ({"lean": "balanced", "label": "Signals only"},
                {"lean": "balanced", "n_upward": 0, "error": "quota"}):
        with pytest.raises(ValueError):
            snap.save("price_outlook", bad, results_dir=tmp_path)
    with pytest.raises(ValueError):
        snap.save("daily_briefing", {**BRIEFING, "model_generated": False}, results_dir=tmp_path)
    assert snap.load("price_outlook", results_dir=tmp_path)[0]["n_upward"] == 3


def test_no_snapshot_and_a_broken_one_both_read_as_none(tmp_path):
    assert snap.load("daily_briefing", results_dir=tmp_path) == (None, None)
    snap.path_for("daily_briefing", results_dir=tmp_path).write_text("{not json")
    assert snap.load("daily_briefing", results_dir=tmp_path) == (None, None)
    with pytest.raises(ValueError):
        snap.path_for("weather", results_dir=tmp_path)
