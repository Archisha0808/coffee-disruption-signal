"""
Publication-date audit: did any document dated after the move decide a run?

The pipeline drops everything published after the anomaly date, but "published"
means the date the search listed: GDELT's crawl time, or the pubDate Google
News puts in its feed. An article dated 3 September by itself has appeared as
current news, so a listed date can be wrong. If it is earlier than the real
date, an article written after the move could become evidence for it.

This script checks every document that took part in a decision in the stored
runs (supporting, opposing or set aside by the rule) against the date its own
page states, read with htmldate (first-published date, not last-modified):

    python -m scripts.audit_publication_dates               # fetches each page (network)
    python -m scripts.audit_publication_dates --offline     # dates recorded at fetch time only

Writes results/publication_date_audit.md. Categories:

    after the move    the page's own date is after the anomaly date and nothing
                      shows it existed by then: a leak
    seen in time      the page shows a later date, but GDELT saw it on or
                      before the anomaly date, so it existed then (a forum
                      page showing its last post, or local time)
    older than listed the page's own date is more than 3 days before its listed
                      date: an old article counted as recent
    consistent        within that range
    no date on page   the page states none, or would not load
    Google News       a news.google.com link is a redirect page with no
                      article to read; listed for a person to check by title

Since version 11 the pipeline also drops a fetched document whose own date is
after the anomaly date (src/pipeline.py, drop_published_after_by_own_date), so
this audit is about runs stored before that guard, and about Google News links,
which the guard cannot see.
"""

import argparse
import glob
import json
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "results"
REPORT = RESULTS_DIR / "publication_date_audit.md"
OLDER_THAN_LISTED_DAYS = 3

AFTER, SEEN, OLDER, OK, NO_DATE, GNEWS = ("after the move", "seen in time", "older than listed",
                                          "consistent", "no date on page", "Google News")


def deciding_documents(results_dir: Path = RESULTS_DIR, version: str = "11") -> list:
    """One record per (run, document) the rule counted or set aside."""
    out = []
    for path in sorted(glob.glob(str(results_dir / "pipeline_output_*.json"))):
        run = json.loads(Path(path).read_text(encoding="utf-8"))
        if version and str(run.get("pipeline_version")) != version:
            continue
        blind = (run.get("explanation_result") or {}).get("blind_evidence") or {}
        role = {**{i: "opposing" for i in blind.get("opposing") or []},
                **{x.get("document_id"): "set aside" for x in blind.get("set_aside") or []},
                **{i: "supporting" for i in blind.get("supporting") or []}}
        for source in run.get("sources") or []:
            if source.get("document_id") in role:
                out.append({"anomaly_date": (run.get("anomaly") or {}).get("date"),
                            "decision": (run.get("explanation_result") or {}).get("decision"),
                            "role": role[source["document_id"]],
                            "document_id": source["document_id"],
                            "title": source.get("title", ""), "url": source.get("url", ""),
                            "listed_date": source.get("publication_date", ""),
                            "own_date": source.get("own_date"),
                            "seen_at": source.get("seen_at"),
                            "found_by": source.get("found_by")})
    return out


def classify(doc: dict) -> str:
    if "news.google.com" in (doc.get("url") or ""):
        return GNEWS
    own = doc.get("own_date")
    if not own:
        return NO_DATE
    if own > doc["anomaly_date"]:
        from src.pipeline import seen_by_anomaly_date
        return SEEN if seen_by_anomaly_date(doc, doc["anomaly_date"]) else AFTER
    listed = doc.get("listed_date") or ""
    try:
        if listed and date.fromisoformat(own) < date.fromisoformat(listed) - timedelta(
                days=OLDER_THAN_LISTED_DAYS):
            return OLDER
    except ValueError:
        pass
    return OK


def fill_own_dates(docs: list, offline: bool) -> None:
    from src.rag.text_fetch import cached_article_date
    if offline:
        for d in docs:
            d["own_date"] = d.get("own_date") or cached_article_date(d["url"])
        return
    import requests
    from src.rag.text_fetch import HEADERS, page_date
    seen = {}
    for i, d in enumerate(docs, 1):
        url = d["url"]
        if d.get("own_date") or "news.google.com" in url:
            continue
        if url not in seen:
            try:
                resp = requests.get(url, headers=HEADERS, timeout=(6, 20))
                seen[url] = page_date(resp.text, url) if resp.ok else None
            except requests.RequestException:
                seen[url] = None
            print(f"  [{i}/{len(docs)}] {seen[url] or 'no date':<10}  {url[:80]}")
        d["own_date"] = seen[url]


def write(docs: list, report: Path) -> dict:
    for d in docs:
        d["category"] = classify(d)
    counts = {c: sum(1 for d in docs if d["category"] == c)
              for c in (AFTER, SEEN, OLDER, OK, NO_DATE, GNEWS)}
    explained = [d for d in docs if d["decision"] == "EXPLAINED" and d["role"] == "supporting"]
    L = ["# Publication-date audit", "",
         f"{len(docs)} documents took part in a decision in the stored version 11 runs "
         f"({len(explained)} of them supporting an explanation). Each was checked against the "
         "first-published date its own page states. Produced by "
         "`python -m scripts.audit_publication_dates`.", "",
         "| Category | Documents | Supporting an explanation |", "|---|---|---|"]
    for c, n in counts.items():
        L.append(f"| {c} | {n} | {sum(1 for d in explained if d['category'] == c)} |")
    L += ["", "A leak is a document in the first row. \"Seen in time\" pages show a later date "
              "than the move, but GDELT found them on or before the day of the move, so they "
              "existed then. A page dated the day this audit ran counts as having no date. "
              f"\"Older than listed\" means the page "
              f"gives a date more than {OLDER_THAN_LISTED_DAYS} days before the date the search "
              "gave it, so an old article was treated as recent.", ""]
    for c in (AFTER, SEEN, OLDER, GNEWS, NO_DATE):
        rows = [d for d in docs if d["category"] == c]
        if not rows:
            continue
        L += [f"## {c}", "", "| Anomaly date | Run | Role | Listed | Seen by GDELT | Own date | Title |",
              "|---|---|---|---|---|---|---|"]
        L += [f"| {d['anomaly_date']} | {d['decision']} | {d['role']} | {d['listed_date']} "
              f"| {d.get('seen_at') or ''} | {d.get('own_date') or ''} | {d['title'][:80]} |"
              for d in rows]
        L.append("")
    report.write_text("\n".join(L), encoding="utf-8")
    print(f"Saved {report}")
    for c, n in counts.items():
        print(f"  {c:<18} {n}")
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--offline", action="store_true",
                        help="Use only dates recorded when the text was fetched; no network")
    args = parser.parse_args()
    docs = deciding_documents()
    fill_own_dates(docs, args.offline)
    write(docs, REPORT)


if __name__ == "__main__":
    main()
