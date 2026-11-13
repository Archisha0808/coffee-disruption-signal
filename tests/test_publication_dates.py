"""The page's own publication date: read at fetch time, used to drop an
article the search listed too early, and audited on stored runs. Offline."""
import json
from unittest import mock

from src import pipeline
from src.rag import text_fetch
from scripts import audit_publication_dates as apd

PAGE = ('<html><head><meta property="article:published_time" content="2024-09-24T10:00:00Z">'
        '<meta property="article:modified_time" content="2024-09-30"></head><body>x</body></html>')


def test_page_date_is_the_first_published_date():
    assert text_fetch.page_date(PAGE) == "2024-09-24"
    today = ('<html><head><meta property="article:published_time" content="%s"></head>'
             '<body>x</body></html>' % __import__("datetime").date.today().isoformat())
    assert text_fetch.page_date(today) is None          # today is never a past article's date
    assert text_fetch.page_date("<html><body>nothing</body></html>") is None
    assert text_fetch.page_date("") is None


def test_the_own_date_is_cached_with_the_text(tmp_path):
    with mock.patch.object(text_fetch, "TEXT_CACHE_DIR", tmp_path):
        text_fetch._text_cache_put("http://a/1", "body", "2024-09-24")
        text_fetch._text_cache_put("http://a/2", "body")          # fetched before dates were kept
        assert text_fetch.cached_article_date("http://a/1") == "2024-09-24"
        assert text_fetch.cached_article_date("http://a/2") is None
        assert text_fetch.cached_article_date("http://a/never") is None


def test_an_article_whose_own_date_is_after_the_move_is_dropped():
    docs = [{"url": "http://a/late", "title": "late", "publication_date": "2024-09-22"},
            # a forum page showing a later post, but GDELT saw it on the day: kept
            {"url": "http://a/forum", "title": "forum", "publication_date": "2024-09-23",
             "seen_at": "20240923T221500Z"},
            {"url": "http://a/ok", "title": "ok", "publication_date": "2024-09-22"},
            {"url": "http://a/unknown", "title": "?", "publication_date": "2024-09-22"},
            {"url": "", "title": "no url", "publication_date": "2024-09-22"}]
    own = {"http://a/late": "2024-09-25", "http://a/ok": "2024-09-23", "http://a/forum": "2024-09-24"}
    with mock.patch.object(pipeline, "cached_article_date", side_effect=lambda u: own.get(u)):
        kept, dropped = pipeline.drop_published_after_by_own_date(docs, "2024-09-23")
    assert [d["title"] for d in kept] == ["forum", "ok", "?", "no url"]  # same day is allowed
    assert dropped == [{"url": "http://a/late", "title": "late", "publication_date": "2024-09-22",
                        "own_date": "2024-09-25", "reason": "own_date_after_anomaly"}]
    assert kept[1]["own_date"] == "2024-09-23"


def test_the_audit_sorts_documents_into_categories():
    base = {"anomaly_date": "2024-09-23", "listed_date": "2024-09-23", "url": "http://a/x"}
    assert apd.classify({**base, "own_date": "2024-09-24"}) == apd.AFTER
    assert apd.classify({**base, "own_date": "2024-09-24", "seen_at": "20240923T221500Z"}) == apd.SEEN
    assert apd.classify({**base, "own_date": "2024-09-23"}) == apd.OK
    assert apd.classify({**base, "own_date": "2024-09-10"}) == apd.OLDER
    assert apd.classify({**base, "own_date": None}) == apd.NO_DATE
    assert apd.classify({**base, "url": "https://news.google.com/rss/x", "own_date": None}) == apd.GNEWS


def test_the_audit_reads_the_deciding_documents_of_stored_runs(tmp_path):
    run = {"pipeline_version": "11", "anomaly": {"date": "2024-09-23"},
           "explanation_result": {"decision": "EXPLAINED", "blind_evidence": {
               "supporting": ["s"], "opposing": ["o"],
               "set_aside": [{"document_id": "a", "why": "x"}]}},
           "sources": [{"document_id": d, "title": d, "url": f"http://a/{d}",
                        "publication_date": "2024-09-23"} for d in ("s", "o", "a", "unused")]}
    (tmp_path / "pipeline_output_coffee_2024-09-23.json").write_text(json.dumps(run))
    (tmp_path / "pipeline_output_coffee_2018-01-01.json").write_text(
        json.dumps({**run, "pipeline_version": "9"}))
    docs = apd.deciding_documents(tmp_path)
    assert sorted((d["document_id"], d["role"]) for d in docs) == [
        ("a", "set aside"), ("o", "opposing"), ("s", "supporting")]
    report = tmp_path / "audit.md"
    for d in docs:
        d["own_date"] = "2024-09-23"
    counts = apd.write(docs, report)
    assert counts[apd.OK] == 3 and "Publication-date audit" in report.read_text()
