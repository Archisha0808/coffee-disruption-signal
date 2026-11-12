"""The reading audit: export a blind sheet, score it, and re-decide the
labelled dates with a person's readings. Offline, on the stored runs."""
import csv
import json

import pytest

from scripts import audit_readings as ar

RUNS = ar.labelled_runs()


def _paths(tmp_path):
    return tmp_path / "sheet.csv", tmp_path / "key.json", tmp_path / "report.md"


def _read(sheet):
    with open(sheet, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write(sheet, rows):
    with open(sheet, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ar.SHEET_COLUMNS)
        w.writeheader()
        w.writerows(rows)


def _fill_as_model(row, model):
    """Answer every field exactly as the model did."""
    row.update({
        "human_price_move": model["price_move"], "human_when": model["when"],
        "human_move_pct": "" if model["move_pct"] is None else str(model["move_pct"]),
        "human_move_size": model["move_size"],
        "human_this_market": "yes" if model["this_market"] else "no",
        "human_reason": "yes" if model["cause"] else "no",
        "human_cause_type": model["cause_type"] or "", "human_pressure": model["pressure"]})


@pytest.mark.skipif(len(RUNS) < 16, reason="needs the stored version 11 runs")
def test_the_sheet_is_blind_and_puts_the_refused_dates_first(tmp_path):
    sheet, key, _ = _paths(tmp_path)
    ar.export(n=50, sheet=sheet, key=key, runs=RUNS, shown_dir=tmp_path)
    rows = _read(sheet)
    assert len(rows) == 50
    header = set(rows[0])
    assert not {"direction", "price_move", "move_size", "tier"} & header   # nothing of the model's
    tiers = [v["tier"] for v in json.loads(key.read_text())["rows"].values()]
    refused_pool = sum(1 for d, label, run in RUNS
                       if label == "EXPLAIN" and run["explanation_result"]["decision"] != "EXPLAINED"
                       for r in run["explanation_result"]["blind_evidence"]["readings"]
                       if r.get("read") and ar.decisive(r))
    assert tiers.count("refused_date") == min(refused_pool, 40)
    assert tiers.count("model_saw_nothing") == 10


@pytest.mark.skipif(len(RUNS) < 16, reason="needs the stored version 11 runs")
def test_re_export_keeps_answers(tmp_path):
    sheet, key, _ = _paths(tmp_path)
    ar.export(n=20, sheet=sheet, key=key, runs=RUNS, shown_dir=tmp_path)
    rows = _read(sheet)
    rows[3]["human_notes"] = "checked"
    _write(sheet, rows)
    ar.export(n=20, sheet=sheet, key=key, runs=RUNS, shown_dir=tmp_path)
    assert any(r["human_notes"] == "checked" for r in _read(sheet))


@pytest.mark.skipif(len(RUNS) < 16, reason="needs the stored version 11 runs")
def test_a_person_who_reads_like_the_model_changes_nothing(tmp_path):
    sheet, key, report = _paths(tmp_path)
    ar.export(n=50, sheet=sheet, key=key, runs=RUNS, shown_dir=tmp_path)
    answers = json.loads(key.read_text())["rows"]
    rows = _read(sheet)
    for row in rows:
        _fill_as_model(row, answers[row["audit_id"]]["model"])
    _write(sheet, rows)
    result = ar.score(sheet=sheet, key=key, report=report, runs=RUNS)
    assert all(v["pct"] == 100.0 for v in result["agreement"].values())
    assert result["redecided"] and all(d["model_readings"] == d["person_readings"]
                                       for d in result["redecided"])
    assert report.exists()


def test_a_size_read_as_large_turns_a_set_aside_report_into_support():
    """2024-09-23: the one same-day report rising 'with violent weather swings'
    was read as size unstated and set aside. Read as large, it explains."""
    runs = [r for r in RUNS if r[0] == "2024-09-23"]
    if not runs:
        pytest.skip("needs the stored 2024-09-23 run")
    date, _, run = runs[0]
    blind = run["explanation_result"]["blind_evidence"]
    reading = next(r for r in blind["readings"] if r["document_id"] == "4cee8671b3e63a36")
    row = {"human_price_move": "up", "human_when": "same_day", "human_move_pct": "",
           "human_move_size": "large", "human_this_market": "yes", "human_reason": "yes",
           "human_cause_type": "event", "human_pressure": "up"}
    swapped = [ar.human_reading(r, row) if r is reading else r for r in blind["readings"]]
    actual = ar.be.flagged_day_move(run["anomaly"])
    variants = tuple(blind["variants"])
    assert ar.be.decide(blind["readings"], "up", variants=variants, actual_pct=actual)["decision"] == "REFUSE"
    assert ar.be.decide(swapped, "up", variants=variants, actual_pct=actual)["decision"] == "EXPLAIN"


def test_a_person_can_withdraw_a_reason_but_not_add_one():
    model = {"document_id": "x", "trading_days_before": 0, "price_move": "up", "pressure": "up",
             "direction": "up", "kind": "report", "when": "same_day", "move_pct": 6.0,
             "move_size": "large", "this_market": True, "cause": "frost", "cause_type": "event",
             "quote": "frost", "quote_found": True}
    withdrawn = ar.human_reading(model, {"human_price_move": "up", "human_reason": "no"})
    assert withdrawn["cause"] is None and not withdrawn["quote_found"]
    silent = {**model, "cause": None, "quote": None, "quote_found": False}
    added = ar.human_reading(silent, {"human_price_move": "up", "human_reason": "yes"})
    assert not added["quote_found"]                          # no verified quote, still unusable
    flat = ar.human_reading(model, {"human_price_move": "none", "human_pressure": "none"})
    assert flat["direction"] is None and flat["move_size"] == "unstated"
