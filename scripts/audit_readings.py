"""
Reading audit: does the model read a document the way a person would?

Every decision the pipeline makes rests on the blind readings (direction of
the move, when it happened, how large it was, which market, what kind of
reason). Nobody had checked them. Version 11's rule rests most on move_size:
without the size check 14 of the 16 labelled dates would be explained instead
of 10 (results/evaluation_report.md, section 5). So this audit asks a person
to fill in the same fields for a sample of the documents the model read,
without seeing the model's answers, and then measures agreement.

Three steps
-----------
1. Export a sheet (offline):

       python -m scripts.audit_readings --export

   Writes data/labeling/reading_audit_sheet.csv. The model's answers go to a
   separate file, data/labeling/reading_audit_key.json, which the person
   filling in the sheet must not open. The sheet does not say which way
   prices moved on the date, for the same reason the model is not told.
   Re-exporting keeps answers already entered.

   The sample (default 50 rows), in this order:
     - every reading that could have decided one of the labelled dates the
       system refused (recent, with a direction and a reason),
     - readings of the same kind from the labelled dates it explained,
     - readings the model said report nothing, to see what it misses.

2. Fill in, per row, the human_* columns (leave a cell empty if unsure):

       human_price_move   up / down / mixed / none
                          Does the document say coffee FUTURES prices moved?
       human_when         same_day / previous_day / earlier / forecast / unclear
                          relative to the document's own date
       human_move_pct     the size it states, a number of percent, or empty
       human_move_size    large / small / unstated
                          large = described as a big move (surge, plunge,
                          jumps 5%), small = slight (edges up, 0.6%)
       human_this_market  yes / no   arabica futures (no = robusta, local price)
       human_reason       yes / no   does it give a reason for the move or pressure?
       human_cause_type   event / trading
                          event = weather, stocks, policy, currency...;
                          trading = "technical adjustments", fund selling with
                          no event behind it
       human_pressure     up / down / none
                          only when it reports no move: which way would the
                          events it reports push prices?

   The article text the model was shown is in the sheet when this machine has
   data/eval_cache/shown/ (it is not in the repository: other publishers'
   text). Otherwise open the URL.

3. Score:

       python -m scripts.audit_readings --score

   Writes results/reading_audit.md: agreement per field with 95% Wilson
   intervals, the move_size confusion table, every disagreement, and the
   decision each labelled date would get with the person's readings in place
   of the model's (the rule is a pure function of the readings, so no model
   is called).

   Limit of the re-decision: a person's reading can remove or re-class a
   reason the model gave, but cannot add one the model missed, because the
   rule also needs a verified quote. Reasons the model missed are counted
   separately.
"""

import argparse
import csv
import json
import random
from collections import Counter
from pathlib import Path

from src.evaluation.metrics import rate
from src.rag import blind_evidence as be

REPO_ROOT = Path(__file__).resolve().parent.parent
LABELS = REPO_ROOT / "data" / "labeling" / "labels_by_written_rule.csv"
SHEET = REPO_ROOT / "data" / "labeling" / "reading_audit_sheet.csv"
KEY = REPO_ROOT / "data" / "labeling" / "reading_audit_key.json"
SHOWN_DIR = REPO_ROOT / "data" / "eval_cache" / "shown"
REPORT = REPO_ROOT / "results" / "reading_audit.md"
RESULTS = REPO_ROOT / "results"

FIELDS = ("price_move", "when", "move_pct", "move_size", "this_market", "reason",
          "cause_type", "pressure")
HUMAN = [f"human_{f}" for f in FIELDS]
SHEET_COLUMNS = (["audit_id", "date", "document_id", "title", "url", "publication_date", "text"]
                 + HUMAN + ["human_notes"])
TEXT_CHARS = 1500           # the excerpt length the reading is usually sent


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def labelled_runs(labels_path: Path = LABELS, results_dir: Path = RESULTS) -> list:
    """(date, label, run) for every labelled EXPLAIN/REFUSE date with a stored
    blind-mode run."""
    out = []
    with open(labels_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["expected_outcome"] not in ("EXPLAIN", "REFUSE"):
                continue
            path = results_dir / f"pipeline_output_coffee_{row['date']}.json"
            if not path.exists():
                continue
            run = json.loads(path.read_text(encoding="utf-8"))
            blind = (run.get("explanation_result") or {}).get("blind_evidence")
            if blind and blind.get("readings") is not None:
                out.append((row["date"], row["expected_outcome"], run))
    return out


def shown_texts(date: str, shown_dir: Path = SHOWN_DIR) -> dict:
    path = shown_dir / f"coffee_{date}.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    return {d.get("document_id"): d.get("text") or "" for d in data.get("documents") or []}


def decisive(reading: dict) -> bool:
    """Could this reading take part in the decision: recent, with a direction
    and a reason?"""
    age = reading.get("trading_days_before")
    return bool(reading.get("direction") and reading.get("cause")
                and age is not None and 0 <= age <= be.FRESH_TRADING_DAYS)


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def choose(runs: list, n: int, seed: int, n_silent: int) -> list:
    """[(tier, date, reading, run)] in sheet order."""
    rng = random.Random(seed)
    refused, explained, silent = [], [], []
    for date, label, run in runs:
        er = run["explanation_result"]
        was_refused = er.get("decision") != "EXPLAINED"
        for r in er["blind_evidence"]["readings"]:
            if not r.get("read"):
                continue
            item = (date, r, run)
            if decisive(r):
                (refused if (label == "EXPLAIN" and was_refused) else explained).append(item)
            elif r.get("price_move") == "none" and r.get("pressure") == "none":
                silent.append(item)
    for pool in (refused, explained, silent):
        rng.shuffle(pool)
    n_silent = min(n_silent, len(silent), n)
    take_refused = refused[:n - n_silent]
    take_explained = explained[:max(0, n - n_silent - len(take_refused))]
    take_silent = silent[:n - len(take_refused) - len(take_explained)]
    chosen = ([("refused_date", *x) for x in take_refused]
              + [("explained_date", *x) for x in take_explained]
              + [("model_saw_nothing", *x) for x in take_silent])
    rng.shuffle(chosen)       # so the person cannot tell the tier from the position
    return chosen


def export(n: int = 50, seed: int = 11, n_silent: int = 10,
           sheet: Path = SHEET, key: Path = KEY, runs: list = None,
           shown_dir: Path = SHOWN_DIR) -> dict:
    runs = labelled_runs() if runs is None else runs
    kept = {}
    if sheet.exists():
        with open(sheet, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if any((row.get(h) or "").strip() for h in HUMAN + ["human_notes"]):
                    kept[(row["date"], row["document_id"])] = row
    rows, answers = [], {}
    texts = {}
    for i, (tier, date, reading, run) in enumerate(choose(runs, n, seed, n_silent), 1):
        doc_id = reading.get("document_id")
        if date not in texts:
            texts[date] = shown_texts(date, shown_dir)
        source = next((s for s in run.get("sources") or [] if s.get("document_id") == doc_id), {})
        audit_id = f"r{i:03d}"
        row = {"audit_id": audit_id, "date": date, "document_id": doc_id,
               "title": source.get("title", ""), "url": source.get("url", ""),
               "publication_date": source.get("publication_date", ""),
               "text": (texts[date].get(doc_id) or "")[:TEXT_CHARS],
               **{h: "" for h in HUMAN}, "human_notes": ""}
        previous = kept.get((date, doc_id))
        if previous:
            row.update({h: previous.get(h, "") for h in HUMAN + ["human_notes"]})
        rows.append(row)
        answers[audit_id] = {"tier": tier, "date": date, "document_id": doc_id,
                             "model": {k: reading.get(k) for k in
                                       ("price_move", "pressure", "direction", "kind", "when",
                                        "move_pct", "move_size", "this_market", "cause",
                                        "cause_type", "quote", "quote_found",
                                        "trading_days_before")}}
    sheet.parent.mkdir(parents=True, exist_ok=True)
    with open(sheet, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SHEET_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    key.write_text(json.dumps({"seed": seed, "rows": answers}, indent=2), encoding="utf-8")
    tiers = Counter(a["tier"] for a in answers.values())
    with_text = sum(1 for r in rows if r["text"])
    print(f"Wrote {len(rows)} rows to {sheet} ({dict(tiers)}); article text included for "
          f"{with_text} of them. {len(kept)} rows kept answers from an earlier sheet.")
    print(f"The model's answers are in {key.name}. The person filling in the sheet must not open it.")
    return {"rows": rows, "answers": answers}


# ---------------------------------------------------------------------------
# Score
# ---------------------------------------------------------------------------

def _norm(field: str, value):
    """A sheet cell or a model value in one comparable form; None = no answer."""
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in ("", "null", "nan"):
        return None
    if field == "move_pct":
        try:
            return abs(float(text.replace("%", "").replace(",", ".")))
        except ValueError:
            return None
    if field == "this_market":
        return {"yes": True, "true": True, "y": True, "no": False, "false": False, "n": False}.get(text)
    if field == "reason":
        return {"yes": True, "true": True, "y": True, "no": False, "false": False, "n": False}.get(text)
    return text.replace(" ", "_")


def model_value(field: str, model: dict):
    if field == "reason":
        return bool(model.get("cause"))
    if field == "cause_type":
        return model.get("cause_type") if model.get("cause") else None
    return model.get(field)


def agree(field: str, human, model) -> bool:
    if field == "move_pct":
        if human is None and model is None:
            return True
        if human is None or model is None:
            return False
        return abs(human - model) <= 0.5
    return human == model


def human_reading(model_reading: dict, row: dict) -> dict:
    """The model's reading with the person's answers in its place, re-derived
    the way normalize_reading derives direction and kind. Cause and quote stay
    the model's: the person can withdraw a reason (human_reason = no) but the
    rule cannot use a reason that has no verified quote."""
    h = {f: _norm(f, row.get(f"human_{f}")) for f in FIELDS}
    r = dict(model_reading)
    for f in ("price_move", "when", "move_size", "cause_type", "pressure"):
        if h[f] is not None:
            r[f] = h[f]
    if h["price_move"] is not None:          # the person read this far: their size stands,
        r["move_pct"] = h["move_pct"]         # including "states no percentage" (empty)
    if h["this_market"] is not None:
        r["this_market"] = h["this_market"]
    if h["reason"] is False:
        r["cause"], r["quote_found"] = None, False
    pm, pr = r.get("price_move"), r.get("pressure")
    r["direction"] = pm if pm in be.DIRECTIONS else (pr if pm == "none" and pr in be.DIRECTIONS else None)
    r["kind"] = None if r["direction"] is None else ("report" if pm in be.DIRECTIONS else "pressure")
    if pm not in be.DIRECTIONS:
        r["move_size"] = "unstated"
    return r


def score(sheet: Path = SHEET, key: Path = KEY, report: Path = REPORT, runs: list = None) -> dict:
    if not sheet.exists() or not key.exists():
        raise SystemExit("No sheet yet - run with --export first.")
    answers = json.loads(key.read_text(encoding="utf-8"))["rows"]
    with open(sheet, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f)
                if any((r.get(h) or "").strip() for h in HUMAN)]
    if not rows:
        raise SystemExit(f"No answers in {sheet.name} yet.")

    per_field, disagreements = {}, []
    size_table = Counter()
    missed_reasons = 0
    for row in rows:
        model = answers[row["audit_id"]]["model"]
        for field in FIELDS:
            h = _norm(field, row.get(f"human_{field}"))
            if h is None and field != "move_pct":
                continue
            if field == "move_pct" and (row.get("human_move_pct") or "").strip() == "" \
                    and _norm("price_move", row.get("human_price_move")) is None:
                continue                         # row not filled in this far
            m = _norm(field, model_value(field, model))
            ok = agree(field, h, m)
            k, n = per_field.get(field, (0, 0))
            per_field[field] = (k + ok, n + 1)
            if not ok:
                disagreements.append((row["audit_id"], row["date"], field, h, m, row.get("title", "")))
        hs = _norm("move_size", row.get("human_move_size"))
        if hs is not None:
            size_table[(hs, model.get("move_size"))] += 1
        if _norm("reason", row.get("human_reason")) is True and not model.get("cause"):
            missed_reasons += 1

    # Re-decide every labelled date with the person's readings swapped in.
    runs = labelled_runs() if runs is None else runs
    by_doc = {(r["date"], r["document_id"]): r for r in rows}
    redecided = []
    for date, label, run in runs:
        er = run["explanation_result"]
        blind = er["blind_evidence"]
        readings = blind["readings"]
        swapped = [human_reading(r, by_doc[(date, r.get("document_id"))])
                   if (date, r.get("document_id")) in by_doc else r for r in readings]
        n_swapped = sum(1 for r in readings if (date, r.get("document_id")) in by_doc)
        if not n_swapped:
            continue
        direction = run["anomaly"].get("direction")
        actual = be.flagged_day_move(run["anomaly"])
        variants = tuple(blind.get("variants") or ())
        before = be.decide(readings, direction, variants=variants, actual_pct=actual)["decision"]
        after = be.decide(swapped, direction, variants=variants, actual_pct=actual)["decision"]
        redecided.append({"date": date, "label": label, "readings_audited": n_swapped,
                          "model_readings": before, "person_readings": after})

    result = {"rows_scored": len(rows),
              "agreement": {f: rate(k, n) for f, (k, n) in per_field.items()},
              "move_size_table": {f"{h}|{m}": c for (h, m), c in size_table.items()},
              "reasons_the_model_missed": missed_reasons,
              "disagreements": disagreements, "redecided": redecided}
    _write(result, report)
    return result


def _fmt(r: dict) -> str:
    return f"{r['pct']}% ({r['k']}/{r['n']}; 95% CI {r['ci95'][0]}-{r['ci95'][1]}%)" if r["n"] else "n/a"


def _write(result: dict, report: Path) -> None:
    L = ["# Reading audit", "",
         f"A person filled in the reading fields for {result['rows_scored']} documents the model read on "
         "the labelled dates, without seeing the model's answers. Produced by "
         "`python -m scripts.audit_readings --score`. One person, one pass: this measures agreement "
         "with that person, not correctness.", "",
         "## Agreement by field", "", "| Field | Agreement |", "|---|---|"]
    order = ["move_size", "price_move", "when", "move_pct", "this_market", "reason", "cause_type", "pressure"]
    for f in order:
        if f in result["agreement"]:
            L.append(f"| {f}{' (the size check rests on this)' if f == 'move_size' else ''} "
                     f"| {_fmt(result['agreement'][f])} |")
    L += ["", "move_pct counts as agreeing within 0.5 percentage points, or when neither states one.", "",
          "## move_size: person (rows) against model (columns)", ""]
    sizes = ("large", "small", "unstated")
    L += ["| person \\ model | " + " | ".join(sizes) + " |", "|---" * 4 + "|"]
    for h in sizes:
        L.append(f"| {h} | " + " | ".join(str(result["move_size_table"].get(f"{h}|{m}", 0))
                                          for m in sizes) + " |")
    L += ["", f"Documents the person says give a reason where the model gave none: "
              f"{result['reasons_the_model_missed']}.", "",
          "## Decisions with the person's readings in place of the model's", "",
          "| Date | Label | Readings audited | With the model's readings | With the person's |",
          "|---|---|---|---|---|"]
    changed = 0
    for d in result["redecided"]:
        mark = " **changed**" if d["model_readings"] != d["person_readings"] else ""
        changed += bool(mark)
        L.append(f"| {d['date']} | {d['label']} | {d['readings_audited']} | {d['model_readings']} "
                 f"| {d['person_readings']}{mark} |")
    L += ["", f"{changed} of {len(result['redecided'])} dates change decision. A person's reading can "
              "withdraw or re-class a reason; it cannot add one the model missed (the rule needs a "
              "verified quote), so this undercounts dates a better reading would explain.", "",
          "## Every disagreement", "", "| Row | Date | Field | Person | Model | Title |", "|---|---|---|---|---|---|"]
    for row_id, date, field, h, m, title in result["disagreements"]:
        L.append(f"| {row_id} | {date} | {field} | {h} | {m} | {title[:70]} |")
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"Saved {report}")
    for f in order:
        if f in result["agreement"]:
            print(f"  {f:<12} {_fmt(result['agreement'][f])}")
    print(f"  {changed} of {len(result['redecided'])} labelled dates change decision with the person's readings")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--export", action="store_true", help="Write the sheet to fill in")
    group.add_argument("--score", action="store_true", help="Score a filled-in sheet")
    parser.add_argument("--n", type=int, default=50, help="Rows in the sheet (default 50)")
    parser.add_argument("--seed", type=int, default=11)
    args = parser.parse_args()
    if args.export:
        export(n=args.n, seed=args.seed)
    else:
        score()


if __name__ == "__main__":
    main()
