"""
The anomaly detector across every configured commodity, in one report.

Runs the unchanged detector (src/modeling/anomaly_detector.py) on each
commodity's price file and reports, side by side:

1. Threshold sensitivity. How many days are flagged at z >= 2.0 (the setting
   every labelled date was drawn at), 2.5 and 3.0, and how many of the cited
   known events still get at least one flag at each. Reported next to the
   tail-heaviness of each commodity's daily returns (excess kurtosis, and the
   share of days beyond 3 standard deviations against 0.27% for a normal
   distribution), because a fixed 2-sigma cut means a different thing in a
   heavy-tailed market. This is reported as sensitivity; the setting is not
   changed, because the labelled dates were drawn at 2.0.
2. Clean quarters. Calendar quarters with full rolling history and zero flags
   at 2.0 - the candidates for a commodity's control period. Cocoa's and
   sugar's control periods in src/config/commodities.py are placeholders
   until one is picked from this list.
3. Shared shocks. Days on which two or more commodities had a daily shock
   flag at once, and the correlation of daily returns between commodities.
   A day on which coffee, sugar and cocoa all jump is more likely a macro or
   currency move (the Brazilian real, the dollar, a fund liquidation) than a
   crop story, and is worth knowing before an explanation is attempted.

Offline: reads data/raw/*_prices.csv only. Commodities without a price file
are listed with the command that fetches one.

Usage:
    python -m scripts.multi_commodity_report
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.config.commodities import COMMODITIES, load_contract_switches
from src.modeling.anomaly_detector import compute_anomalies, validate_against_all_events

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "results"
THRESHOLDS = (2.0, 2.5, 3.0)
NORMAL_BEYOND_3 = 0.27   # % of days beyond 3 sigma under a normal distribution
MAX_CLEAN_QUARTERS_LISTED = 8


def load_prices(key: str):
    path = REPO_ROOT / "data" / "raw" / COMMODITIES[key].price_file
    if not path.exists():
        return None
    df = pd.read_csv(path).dropna(subset=["price"])
    return df[df["price"] > 0]            # WTI settled below zero on 2020-04-20


def sensitivity(key: str, prices: pd.DataFrame) -> dict:
    cfg = COMMODITIES[key]
    switches = load_contract_switches(key)
    runs = {}
    for z in THRESHOLDS:
        result = compute_anomalies(prices, z_threshold=z, reported_returns=switches)
        valid = result["rolling_std"].notna()
        checks = validate_against_all_events(result, cfg.known_events, cfg.control_period)
        events = [c for c in checks if c["type"] == "event"]
        control = next(c for c in checks if c["type"] != "event")
        runs[z] = {
            "flagged": int(result.loc[valid, "anomaly_flag"].sum()),
            "shock_days": int(result.loc[valid, "daily_anomaly_flag"].sum()),
            "days": int(valid.sum()),
            "events_detected": sum(1 for e in events if e["detected"]),
            "events_total": len(events),
            "events_missed": [e["label"] for e in events if not e["detected"]],
            "control_flags": control["flagged_count"],
            "control_days": control["trading_days"],
            "_frame": result,
        }
    base = runs[2.0]["_frame"]
    returns = pd.Series(prices.sort_values("date")["price"].to_numpy()).pct_change().dropna()
    z = base["z_score"].dropna()
    return {
        "runs": runs,
        "excess_kurtosis": round(float(returns.kurt()), 2),
        "pct_days_beyond_3sd": round(100 * float((z.abs() > 3).mean()), 2),
        "start": str(base["date"].iloc[0]), "end": str(base["date"].iloc[-1]),
        "contract_switch_list": bool(switches),
    }


def clean_quarters(frame: pd.DataFrame) -> list:
    df = frame[frame["rolling_std"].notna() & frame["cumulative_rolling_std"].notna()].copy()
    df["quarter"] = pd.PeriodIndex(pd.to_datetime(df["date"]), freq="Q")
    out = []
    for q, g in df.groupby("quarter"):
        if len(g) >= 55 and not g["anomaly_flag"].any():   # a full quarter is ~62 sessions
            out.append({"quarter": str(q), "start": q.start_time.strftime("%Y-%m-%d"),
                        "end": q.end_time.strftime("%Y-%m-%d"), "trading_days": len(g)})
    return out


def shared_shocks(frames: dict) -> dict:
    """frames: {key: detector output at 2.0}."""
    flags = pd.DataFrame({k: f.set_index("date")["daily_anomaly_flag"] for k, f in frames.items()})
    z = pd.DataFrame({k: f.set_index("date")["z_score"] for k, f in frames.items()})
    prices = pd.DataFrame({k: f.set_index("date")["price"] for k, f in frames.items()})
    common = flags.dropna()                      # days every commodity traded
    count = common.astype(bool).sum(axis=1)
    multi = count[count >= 2].index
    days = []
    for d in multi:
        hit = [k for k in common.columns if bool(common.at[d, k])]
        days.append({"date": d, "commodities": hit,
                     "z": {k: round(float(z.at[d, k]), 2) for k in hit}})
    pairs = {}
    keys = list(common.columns)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            both = int((common[a].astype(bool) & common[b].astype(bool)).sum())
            either = int((common[a].astype(bool) | common[b].astype(bool)).sum())
            pairs[f"{a}+{b}"] = {"both": both, "either": either}
    returns = prices.loc[common.index].pct_change()
    corr = returns.corr().round(2)
    return {"days_compared": int(len(common)), "multi_days": days, "pairs": pairs,
            "return_correlation": {a: corr[a].to_dict() for a in corr.columns}}


def write(results: dict, missing: list, shared, md_path: Path, json_path: Path) -> None:
    names = {k: COMMODITIES[k].display_name for k in COMMODITIES}
    L = ["# Detector across commodities", "",
         "Produced by `python -m scripts.multi_commodity_report` (offline, reads the price files). "
         "The detector is unchanged: 75-day window, 10-day cumulative check. All labelled dates "
         "were drawn at z >= 2.0, so 2.5 and 3.0 are reported as sensitivity, not adopted.", ""]
    if missing:
        L += ["**No price file yet:** " + ", ".join(
            f"{names[k]} (`python -m src.modeling.fetch_price_data --commodity {k}`)" for k in missing),
              ""]
    L += ["## 1. Threshold sensitivity", "",
          "| Commodity | History | Excess kurtosis | Days beyond 3 sd (normal: 0.27%) "
          + "".join(f"| Flagged at {z} " for z in THRESHOLDS)
          + "".join(f"| Events at {z} " for z in THRESHOLDS) + "|",
          "|---|---|---|---" + "|---" * (2 * len(THRESHOLDS)) + "|"]
    for k, r in results.items():
        runs = r["runs"]
        L.append(f"| {names[k]} | {r['start']} to {r['end']} | {r['excess_kurtosis']} "
                 f"| {r['pct_days_beyond_3sd']}% "
                 + "".join(f"| {runs[z]['flagged']} ({100 * runs[z]['flagged'] / runs[z]['days']:.1f}%) "
                           for z in THRESHOLDS)
                 + "".join(f"| {runs[z]['events_detected']}/{runs[z]['events_total']} "
                           for z in THRESHOLDS) + "|")
    missed = [(names[k], z, r["runs"][z]["events_missed"]) for k, r in results.items()
              for z in THRESHOLDS if r["runs"][z]["events_missed"]]
    L += ["", "Events missed: " + ("; ".join(f"{n} at {z}: {', '.join(m)}" for n, z, m in missed)
                                   if missed else "none at any threshold."),
          "", "An event counts as detected if any day in its window is flagged. With 2 to 5 "
          "events per commodity this is a smoke test, not a recall estimate.", ""]
    no_switch = [names[k] for k, r in results.items() if not r["contract_switch_list"]]
    if no_switch:
        L += [f"No contract-switch list yet for: {', '.join(no_switch)}. Their counts include "
              "any roll-day jumps in the continuous front-month series.", ""]

    L += ["## 2. Clean quarters (control-period candidates, z >= 2.0)", ""]
    for k, r in results.items():
        cq = r["clean_quarters"]
        cfg = COMMODITIES[k]
        current = f"{cfg.control_period[0]} to {cfg.control_period[1]}"
        listed = ", ".join(f"{q['quarter']} ({q['trading_days']} days)"
                           for q in cq[-MAX_CLEAN_QUARTERS_LISTED:]) or "none"
        L.append(f"- **{names[k]}**: {len(cq)} clean quarters. Most recent: {listed}. "
                 f"Configured control period: {current} "
                 f"({r['runs'][2.0]['control_flags']}/{r['runs'][2.0]['control_days']} days flagged).")
    L.append("")

    if shared:
        L += ["## 3. Shared shocks", "",
              f"{shared['days_compared']} days on which every commodity above traded. Days with a "
              f"daily shock flag in two or more at once: {len(shared['multi_days'])}.", ""]
        three = [d for d in shared["multi_days"] if len(d["commodities"]) >= 3]
        if three:
            L += ["Days with three or more:", "", "| Date | Commodities (z) |", "|---|---|"]
            L += [f"| {d['date']} | " + ", ".join(f"{names[c]} ({d['z'][c]:+.1f})"
                                                   for c in d["commodities"]) + " |" for d in three]
            L.append("")
        L += ["| Pair | Shock days in both | In either | Share |", "|---|---|---|---|"]
        for pair, v in shared["pairs"].items():
            a, b = pair.split("+")
            share = f"{100 * v['both'] / v['either']:.1f}%" if v["either"] else "-"
            L.append(f"| {names[a]} + {names[b]} | {v['both']} | {v['either']} | {share} |")
        keys = list(shared["return_correlation"])
        L += ["", "Correlation of daily returns:", "",
              "| | " + " | ".join(names[k] for k in keys) + " |",
              "|---" * (len(keys) + 1) + "|"]
        for a in keys:
            L.append(f"| {names[a]} | " + " | ".join(
                f"{shared['return_correlation'][a][b]:.2f}" for b in keys) + " |")
        L.append("")
    md_path.write_text("\n".join(L), encoding="utf-8")
    clean = {k: {**{kk: vv for kk, vv in r.items() if kk != "runs"},
                 "runs": {str(z): {kk: vv for kk, vv in run.items() if kk != "_frame"}
                          for z, run in r["runs"].items()}} for k, r in results.items()}
    json_path.write_text(json.dumps({"commodities": clean, "missing": missing,
                                     "shared_shocks": shared}, indent=2, default=str),
                         encoding="utf-8")
    print(f"Saved {md_path} and {json_path.name}")


def main():
    results, missing, frames = {}, [], {}
    for key in COMMODITIES:
        prices = load_prices(key)
        if prices is None:
            missing.append(key)
            continue
        r = sensitivity(key, prices)
        r["clean_quarters"] = clean_quarters(r["runs"][2.0]["_frame"])
        frames[key] = r["runs"][2.0]["_frame"]
        results[key] = r
        runs = r["runs"]
        print(f"[{COMMODITIES[key].display_name}] flagged "
              + ", ".join(f"{runs[z]['flagged']} at {z}" for z in THRESHOLDS)
              + f"; events {runs[2.0]['events_detected']}/{runs[2.0]['events_total']} at 2.0; "
              f"{len(r['clean_quarters'])} clean quarters")
    for key in missing:
        print(f"[{COMMODITIES[key].display_name}] no price file - run: "
              f"python -m src.modeling.fetch_price_data --commodity {key}")
    shared = shared_shocks(frames) if len(frames) >= 2 else None
    write(results, missing, shared, RESULTS_DIR / "multi_commodity_report.md",
          RESULTS_DIR / "multi_commodity_report.json")


if __name__ == "__main__":
    main()
