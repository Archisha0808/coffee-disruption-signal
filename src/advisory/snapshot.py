"""
Saved briefing and outlook for the public dashboard.

The public dashboard runs with READ_ONLY=1: it calls no model and no news
API, so a visitor cannot spend the project's quota. The daily briefing and
the price outlook both need a model, so on the public site they used to show
only the price data, under the heading "Market data available but LLM
synthesis unavailable" - which reads as a fault to anyone visiting.

This module lets the briefing and the outlook be generated on a machine that
has the keys, saved under results/, committed, and shown on the public site
with the date they were made:

    python -m src.advisory.snapshot          # generate both live, then save them

A snapshot is saved only when the model actually wrote it. If the model or
the news API fails, nothing is written and the previous snapshot stays, so a
bad run cannot replace a good one with a data-only fallback.

Article text is stripped before saving: only title, url, outlet and date of
each document are kept, enough for the dashboard's source links. Other
publishers' text is never committed (see data/text_cache/ in .gitignore).
"""

import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = REPO_ROOT / "results"
KINDS = ("daily_briefing", "price_outlook")
_DOC_KEYS = ("document_id", "title", "url", "source", "domain", "publication_date", "_source")


def path_for(kind: str, commodity: str = "coffee", results_dir: Path = RESULTS_DIR) -> Path:
    if kind not in KINDS:
        raise ValueError(f"unknown snapshot kind {kind!r}; expected one of {KINDS}")
    return results_dir / f"{kind}_{commodity}.json"


def written_by_model(kind: str, data: dict) -> bool:
    """Did a model write this, as opposed to the data-only fallback?"""
    if not isinstance(data, dict) or data.get("error"):
        return False
    if kind == "daily_briefing":
        return bool(data.get("model_generated"))
    return "n_upward" in data          # only the outlook's model path sets the counts


def _strip(data: dict) -> dict:
    out = dict(data)
    out["accepted_documents"] = [{k: d.get(k) for k in _DOC_KEYS if d.get(k) is not None}
                                 for d in data.get("accepted_documents") or []]
    return out


def save(kind: str, data: dict, commodity: str = "coffee",
         results_dir: Path = RESULTS_DIR, now: datetime = None) -> Path:
    """Write a model-written result; refuse a fallback."""
    if not written_by_model(kind, data):
        raise ValueError(f"{kind} was not written by a model "
                         f"({data.get('error') or 'data-only fallback'}); not saved")
    now = now or datetime.now(timezone.utc)
    path = path_for(kind, commodity, results_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"saved_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "commodity": commodity,
               "kind": kind, "data": _strip(data)}
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return path


def load(kind: str, commodity: str = "coffee", results_dir: Path = RESULTS_DIR):
    """(data, saved_at) of the saved snapshot, or (None, None)."""
    path = path_for(kind, commodity, results_dir)
    if not path.exists():
        return None, None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload["data"], payload.get("saved_at")
    except (ValueError, KeyError, OSError):
        return None, None


def saved_on(saved_at: str) -> str:
    """'2026-11-18T09:12:00Z' -> '18 Nov 2026'."""
    try:
        return datetime.strptime(saved_at[:10], "%Y-%m-%d").strftime("%d %b %Y").lstrip("0")
    except (TypeError, ValueError):
        return "an earlier date"


def main():
    from src.advisory.daily_briefing import generate_daily_briefing
    from src.advisory.outlook_rag import generate_outlook
    ok = True
    for kind, make in (("daily_briefing", lambda: generate_daily_briefing(allow_live=True)),
                       ("price_outlook", lambda: generate_outlook(allow_live=True))):
        print(f"Generating {kind.replace('_', ' ')} (calls the news API and the model)...")
        try:
            path = save(kind, make())
            print(f"  saved {path.relative_to(REPO_ROOT)}")
        except ValueError as exc:
            ok = False
            print(f"  NOT saved: {exc}. The previous snapshot, if any, is unchanged.")
    if ok:
        print("\nCommit and push to update the public dashboard:\n"
              "  git add results/daily_briefing_coffee.json results/price_outlook_coffee.json\n"
              "  git commit -m \"Update the saved briefing and outlook\"\n"
              "  git push")


if __name__ == "__main__":
    main()
