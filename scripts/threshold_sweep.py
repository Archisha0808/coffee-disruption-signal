"""
Why is the z-score threshold 2.0? What every other choice would have caught.

The detector flags a day when |z| >= T on the daily check OR |cumulative z| >= T
on the 10-day check (src/modeling/anomaly_detector.py). Both z-scores are stored
per day in each commodity's detections file and neither depends on T, so every
threshold can be re-scored from the files already in results/ - nothing is
refetched and no price series is recomputed. The figures at T = 2.0 therefore
reconcile with results/detector_evaluation.md by construction.

What is reported per commodity and per threshold:

  flagged / rate       days flagged, and their share of scorable days
  daily only           share flagged by the single-day check alone
  detected             cited events with at least one flag in their window
  chance               how many events a detector with NO SKILL would be
                       expected to catch. Empirical, not binomial: every
                       window of the event's length is slid across the series
                       and the share holding a flag is taken, which accounts
                       for flags clustering. Recall read without this column
                       looks far better than it is.
  control FP           flags inside the commodity's verified quiet period
  density / lift       share of event-window days flagged, and that over the
                       base flag rate. Lift rises monotonically with T because
                       a stricter detector flags fewer days everywhere, so it
                       measures concentration, not usefulness - at T = 4.0
                       wheat's lift is 22x and it catches one event of four.

Two things this cannot measure. Whether the hundreds of flagged days outside
any event window deserve flagging: nobody has labelled them, which is why the
evaluation uses event density and control periods rather than a precision
figure over the whole series. And it inherits the event list, which the team
compiled - a benchmark with a known bias, since an event is easier to recall
when the price moved a lot. The --top-moves check uses a benchmark nobody
curated instead: each series' largest actual one-day moves.

Usage:
    python -m scripts.threshold_sweep
    python -m scripts.threshold_sweep --save          # writes results/threshold_sweep.{md,csv}
    python -m scripts.threshold_sweep --commodity coffee
    python -m scripts.threshold_sweep --thresholds 1.5,2.0,2.5
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.config.commodities import COMMODITIES, get_commodity   # noqa: E402

RESULTS_DIR = REPO_ROOT / "results"
REPORT_MD = RESULTS_DIR / "threshold_sweep.md"
REPORT_CSV = RESULTS_DIR / "threshold_sweep.csv"

DEFAULT_THRESHOLDS = (1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 3.5, 4.0)
PRODUCTION_THRESHOLD = 2.0
TOP_MOVES = 20


def load_detections(key: str) -> pd.DataFrame:
    path = RESULTS_DIR / get_commodity(key).anomalies_file
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run: python -m src.modeling.anomaly_detector "
            f"--commodity {key}")
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


def switch_mask(df: pd.DataFrame) -> pd.Series:
    """A contract-switch day shows a move no contract made, so it is excluded
    at every threshold, as the production detector excludes it."""
    if "contract_switch" not in df.columns:
        return pd.Series(False, index=df.index)
    return df["contract_switch"].fillna(False).astype(bool)


def flags_at(df: pd.DataFrame, threshold: float):
    """(flagged, daily_only) at this threshold. A day with no rolling window
    cannot be flagged, so the first 75 trading days are never counted."""
    daily = (df["z_score"].abs() >= threshold).fillna(False) & df["rolling_std"].notna()
    cum = ((df["cumulative_z_score"].abs() >= threshold).fillna(False)
           & df["cumulative_rolling_std"].notna())
    keep = ~switch_mask(df)
    return (daily | cum) & keep, daily & keep


def in_window(df: pd.DataFrame, start: str, end: str) -> pd.Series:
    return (df["date"] >= start) & (df["date"] <= end)


def chance_of_a_flag(flagged: pd.Series, length: int) -> float:
    """Share of all windows of this length holding at least one flag."""
    if length <= 0 or length > len(flagged):
        return float("nan")
    rolled = flagged.rolling(length).sum().dropna()
    return float((rolled >= 1).mean()) if len(rolled) else float("nan")


def sweep_one(key: str, thresholds=DEFAULT_THRESHOLDS) -> pd.DataFrame:
    cfg = get_commodity(key)
    df = load_detections(key)
    control_start, control_end = cfg.control_period[0], cfg.control_period[1]
    rows = []
    for t in thresholds:
        flagged, daily = flags_at(df, t)
        scorable = int(df["rolling_std"].notna().sum())
        event_days = pd.Series(False, index=df.index)
        detected = 0
        chance = 0.0
        for event in cfg.known_events:
            label, start, end = event[0], event[1], event[2]
            mask = in_window(df, start, end)
            length = int(mask.sum())
            if length == 0:
                continue                      # window outside this series' history
            event_days |= mask
            if flagged[mask].any():
                detected += 1
            chance += chance_of_a_flag(flagged, length)
        n_event_days = int(event_days.sum())
        n_event_flagged = int(flagged[event_days].sum())
        rate = int(flagged.sum()) / scorable if scorable else float("nan")
        density = n_event_flagged / n_event_days if n_event_days else float("nan")
        rows.append({
            "commodity": key,
            "threshold": t,
            "flagged": int(flagged.sum()),
            "scorable_days": scorable,
            "flag_rate": rate,
            "daily_only_rate": int(daily.sum()) / scorable if scorable else float("nan"),
            "events": sum(1 for e in cfg.known_events
                          if int(in_window(df, e[1], e[2]).sum()) > 0),
            "detected": detected,
            "chance_expectation": chance,
            "control_false_positives": int(flagged[in_window(df, control_start, control_end)].sum()),
            "event_window_days": n_event_days,
            "event_window_flagged": n_event_flagged,
            "density": density,
            "lift": density / rate if rate else float("nan"),
        })
    return pd.DataFrame(rows)


def per_event(key: str, thresholds=DEFAULT_THRESHOLDS) -> pd.DataFrame:
    """The highest tested threshold at which each cited event is still caught,
    and the peak |z| inside its window. The fragile events are the long
    gradual ones; every event with peak |z| above 4 is a sharp session."""
    cfg = get_commodity(key)
    df = load_detections(key)
    sets = {t: flags_at(df, t)[0] for t in thresholds}
    rows = []
    for event in cfg.known_events:
        label, start, end = event[0], event[1], event[2]
        mask = in_window(df, start, end)
        length = int(mask.sum())
        if length == 0:
            continue
        survives = [t for t in thresholds if sets[t][mask].any()]
        peak = max(float(df.loc[mask, "z_score"].abs().max() or 0),
                   float(df.loc[mask, "cumulative_z_score"].abs().max() or 0))
        rows.append({"commodity": key, "event": label, "start": start, "end": end,
                     "window_days": length,
                     "max_threshold_detected": max(survives) if survives else None,
                     "peak_abs_z": peak})
    return pd.DataFrame(rows)


def top_moves(key: str, thresholds=DEFAULT_THRESHOLDS, n: int = TOP_MOVES) -> dict:
    """Of the n largest actual one-day moves, how many are flagged.

    A benchmark nobody curated. Days where a percentage change is undefined
    (a price at or below zero at either end - WTI settled at -$37.63 on 20
    April 2020) are left out, as are contract-switch days.
    """
    df = load_detections(key)
    df["pct_move"] = df["price"].pct_change() * 100
    usable = (~switch_mask(df) & df["pct_move"].notna()
              & (df["price"] > 0) & (df["price"].shift() > 0))
    cand = df[usable]
    if cand.empty:
        return {}
    top = cand.reindex(cand["pct_move"].abs().sort_values(ascending=False).index).head(n)
    out = {"commodity": key, "n": len(top),
           "smallest_pct": float(top["pct_move"].abs().min()),
           "largest_pct": float(top["pct_move"].abs().max())}
    for t in thresholds:
        flagged, _ = flags_at(df, t)
        out[f"flagged_at_{t}"] = int(flagged.reindex(top.index).fillna(False).sum())
    return out


def report(sweeps: dict, events: dict, moves: list, thresholds) -> str:
    L = ["# Threshold Sensitivity: what every other z-score would have caught", ""]
    L.append("Produced by `python -m scripts.threshold_sweep`. Re-scored from the stored "
             "detections, so the rows at the production threshold reconcile with "
             "`detector_evaluation.md` by construction. See this script's docstring for "
             "what each column means and what it cannot measure.")
    L.append("")
    L.append(f"Production threshold: **{PRODUCTION_THRESHOLD}**, fixed before any "
             f"validation and unchanged since.")
    L.append("")

    total_events = sum(int(s[s.threshold == thresholds[0]].iloc[0].events) for s in sweeps.values())
    L.append("## Across every cited event")
    L.append("")
    L.append("| Threshold | Events detected | Recall | Control false positives |")
    L.append("|---|---|---|---|")
    for t in thresholds:
        det = sum(int(s[s.threshold == t].iloc[0].detected) for s in sweeps.values())
        fp = sum(int(s[s.threshold == t].iloc[0].control_false_positives) for s in sweeps.values())
        mark = "**" if t == PRODUCTION_THRESHOLD else ""
        L.append(f"| {mark}{t:g}{mark} | {det}/{total_events} | "
                 f"{100 * det / total_events:.0f}% | {fp} |")
    L.append("")
    L.append("Recall cannot choose between the loosest thresholds: it is flat where the "
             "detectors differ most. The control periods can, and they were chosen "
             "independently of the threshold.")
    L.append("")

    for key, s in sweeps.items():
        cfg = get_commodity(key)
        first = s.iloc[0]
        L.append(f"## {cfg.display_name} (`{key}`)")
        L.append("")
        L.append(f"{int(first.events)} cited event(s) inside this series' history, "
                 f"{int(first.scorable_days)} scorable days, control period "
                 f"{cfg.control_period[0]} to {cfg.control_period[1]}.")
        L.append("")
        L.append("| T | Flagged | Rate | Daily only | Detected | Chance | Control FP | "
                 "Density | Lift |")
        L.append("|---|---|---|---|---|---|---|---|---|")
        for _, r in s.iterrows():
            mark = "**" if r.threshold == PRODUCTION_THRESHOLD else ""
            L.append(f"| {mark}{r.threshold:g}{mark} | {int(r.flagged)} | "
                     f"{100 * r.flag_rate:.1f}% | {100 * r.daily_only_rate:.1f}% | "
                     f"{int(r.detected)}/{int(r.events)} | {r.chance_expectation:.1f} | "
                     f"{int(r.control_false_positives)} | {100 * r.density:.1f}% | "
                     f"{r.lift:.1f}x |")
        L.append("")
        ev = events[key]
        if not ev.empty:
            L.append("| Event | Window | Survives to | Peak \\|z\\| |")
            L.append("|---|---|---|---|")
            for _, r in ev.iterrows():
                mt = "never" if r.max_threshold_detected is None else f"{r.max_threshold_detected:g}"
                L.append(f"| {r.event} | {int(r.window_days)}d | {mt} | {r.peak_abs_z:.2f} |")
            L.append("")

    L.append("## The largest actual moves")
    L.append("")
    L.append(f"Of each series' {TOP_MOVES} largest one-day moves - a benchmark nobody "
             f"curated - how many the detector flags.")
    L.append("")
    header = "| Commodity | Smallest | Largest | " + " | ".join(f"T={t:g}" for t in thresholds) + " |"
    L.append(header)
    L.append("|---" * (3 + len(thresholds)) + "|")
    for m in moves:
        if not m:
            continue
        cells = " | ".join(f"{m[f'flagged_at_{t}']}/{m['n']}" for t in thresholds)
        L.append(f"| {get_commodity(m['commodity']).display_name} | "
                 f"{m['smallest_pct']:.1f}% | {m['largest_pct']:.1f}% | {cells} |")
    L.append("")
    L.append("A rolling z-score asks whether a move is unusual *for this market right "
             "now*, not whether it is large. During a sustained crisis those questions "
             "come apart: a 12% day in a window whose typical day moves 10% has a small "
             "z-score however the threshold is set, which is why lowering the threshold "
             "recovers none of crude oil's missed moves. That is the adaptive design "
             "working as intended, and its cost. A fixed-size second channel, reported "
             "beside the z-score rather than merged into it, would close the gap; it "
             "would have to sit beside the detector, as the factor model and the "
             "cross-commodity check do, because every evaluation figure in `results/` "
             "was drawn at the current rule.")
    return "\n".join(L)


def main():
    p = argparse.ArgumentParser(description="Threshold sensitivity for the anomaly detector")
    p.add_argument("--commodity", default=None, help="one commodity (default: all with a detections file)")
    p.add_argument("--thresholds", default=None,
                   help=f"comma-separated (default {','.join(f'{t:g}' for t in DEFAULT_THRESHOLDS)})")
    p.add_argument("--save", action="store_true", help="write results/threshold_sweep.{md,csv}")
    args = p.parse_args()

    thresholds = (tuple(float(x) for x in args.thresholds.split(","))
                  if args.thresholds else DEFAULT_THRESHOLDS)
    if args.commodity and args.commodity not in COMMODITIES:
        p.error(f"unknown --commodity {args.commodity!r}; choose from {', '.join(COMMODITIES)}")
    keys = [args.commodity] if args.commodity else [
        k for k in COMMODITIES if (RESULTS_DIR / get_commodity(k).anomalies_file).exists()]
    if not keys:
        p.error("no detections file found in results/. Run the detector first.")

    sweeps, events, moves = {}, {}, []
    for key in keys:
        sweeps[key] = sweep_one(key, thresholds)
        events[key] = per_event(key, thresholds)
        moves.append(top_moves(key, thresholds))

    text = report(sweeps, events, moves, thresholds)
    print(text)
    if args.save:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        REPORT_MD.write_text(text, encoding="utf-8")
        pd.concat(sweeps.values(), ignore_index=True).to_csv(REPORT_CSV, index=False)
        print(f"\nSaved {REPORT_MD} and {REPORT_CSV}")


if __name__ == "__main__":
    main()
