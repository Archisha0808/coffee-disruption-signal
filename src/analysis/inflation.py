"""
Inflation comparison across the configured commodities.

Every price in this project is a US-dollar futures price, so the deflator is
the US consumer price index (CPI-U, all items, seasonally adjusted: BLS series
CUSR0000SA0, the same numbers as FRED's CPIAUCSL), kept monthly in
data/raw/us_cpi_monthly.csv.

Three questions, each answered with a number:

1. Over the whole history, how much of each commodity's price change is just
   inflation? (nominal change, CPI change, real change)
2. Year by year, did the commodity rise faster or slower than consumer prices?
3. Does inflation belong in the anomaly detector? The detector works on
   day-over-day returns against a 75-day baseline. Deflating moves a day's
   return by the CPI's daily drift, roughly a hundredth of a percent, against
   daily moves of one to three percent. This module runs the unchanged
   detector on nominal and on deflated prices and counts the days whose flag
   differs, so the answer is measured, not argued.

What this does NOT do: it does not change the detector, and it does not
deflate the prices the dashboard or the explanation pipeline use.

CPI is monthly. A daily price is deflated by the CPI interpolated linearly
between month midpoints, so the deflator has no step on the first trading day
of a month (a step of up to ~0.8% in 2022 would otherwise appear as a
one-day move that no market made). Days after the last published CPI month
use the last published value; the report says how many there are.
October 2025 was never published (US federal shutdown); it is interpolated
from September and November and the report says so.

Usage:
    python -m src.analysis.inflation                  # every commodity with a price file
    python -m src.analysis.inflation --refresh-cpi    # first re-download CPI from FRED
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.config.commodities import COMMODITIES, get_commodity, load_contract_switches
from src.modeling.anomaly_detector import compute_anomalies

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CPI_PATH = REPO_ROOT / "data" / "raw" / "us_cpi_monthly.csv"
RESULTS_DIR = REPO_ROOT / "results"
FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL"


# ---------------------------------------------------------------------------
# CPI
# ---------------------------------------------------------------------------

def refresh_cpi(path: Path = CPI_PATH) -> pd.DataFrame:
    """Download CPIAUCSL from FRED (no key needed) and save it as month,cpi."""
    raw = pd.read_csv(FRED_CSV_URL)
    date_col = raw.columns[0]
    raw = raw.rename(columns={date_col: "date", "CPIAUCSL": "cpi"})
    raw["cpi"] = pd.to_numeric(raw["cpi"], errors="coerce")   # FRED writes "." for missing
    raw = raw.dropna(subset=["cpi"])
    out = pd.DataFrame({"month": pd.to_datetime(raw["date"]).dt.strftime("%Y-%m"),
                        "cpi": raw["cpi"]})
    out = out[out["month"] >= "2008-01"]
    path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(path, index=False)
    print(f"Saved {len(out)} CPI months ({out['month'].min()} to {out['month'].max()}) to {path}")
    return out


def load_cpi(path: Path = CPI_PATH) -> pd.DataFrame:
    """Monthly CPI with every calendar month present. Returns columns
    month (Period), cpi, interpolated (True where the month was missing)."""
    if not Path(path).exists():
        raise SystemExit(f"{path} not found - run 'python -m src.analysis.inflation --refresh-cpi'.")
    df = pd.read_csv(path)
    df["month"] = pd.PeriodIndex(df["month"], freq="M")
    df = df.set_index("month").sort_index()
    full = pd.period_range(df.index.min(), df.index.max(), freq="M")
    df = df.reindex(full)
    df["interpolated"] = df["cpi"].isna()
    df["cpi"] = df["cpi"].interpolate()
    return df.rename_axis("month").reset_index()


def daily_cpi(cpi: pd.DataFrame, dates: pd.Series) -> pd.DataFrame:
    """CPI for each date, interpolated between month midpoints (15th).
    Returns columns date, cpi, beyond_cpi (True after the last published month)."""
    anchors = pd.Series(cpi["cpi"].to_numpy(),
                        index=cpi["month"].dt.to_timestamp() + pd.Timedelta(days=14))
    dates = pd.to_datetime(pd.Series(dates)).reset_index(drop=True)
    grid = anchors.index.union(pd.DatetimeIndex(dates))
    filled = anchors.reindex(grid).interpolate(method="time").ffill().bfill()
    last_month_end = cpi["month"].max().to_timestamp(how="end")
    return pd.DataFrame({"date": dates,
                         "cpi": filled.reindex(dates).to_numpy(),
                         "beyond_cpi": (dates > last_month_end).to_numpy()})


def deflate(prices: pd.DataFrame, cpi: pd.DataFrame) -> pd.DataFrame:
    """Adds real_price: the price in dollars of the last CPI month."""
    out = prices.copy()
    out["date"] = pd.to_datetime(out["date"])
    out = out.sort_values("date").reset_index(drop=True)
    d = daily_cpi(cpi, out["date"])
    base = float(cpi["cpi"].iloc[-1])
    out["cpi"] = d["cpi"].to_numpy()
    out["beyond_cpi"] = d["beyond_cpi"].to_numpy()
    out["real_price"] = out["price"] * base / out["cpi"]
    return out


# ---------------------------------------------------------------------------
# The three comparisons
# ---------------------------------------------------------------------------

def whole_period(df: pd.DataFrame) -> dict:
    """Nominal, CPI and real change from the first to the last day, and the
    dates of the nominal and the real highs."""
    first, last = df.iloc[0], df.iloc[-1]
    nominal = last["price"] / first["price"] - 1
    cpi_change = last["cpi"] / first["cpi"] - 1
    real = last["real_price"] / first["real_price"] - 1
    i_nom, i_real = df["price"].idxmax(), df["real_price"].idxmax()
    return {
        "start": first["date"].strftime("%Y-%m-%d"), "end": last["date"].strftime("%Y-%m-%d"),
        "nominal_change_pct": round(100 * nominal, 1),
        "cpi_change_pct": round(100 * cpi_change, 1),
        "real_change_pct": round(100 * real, 1),
        "nominal_high": {"date": df.at[i_nom, "date"].strftime("%Y-%m-%d"),
                         "price": round(float(df.at[i_nom, "price"]), 2)},
        "real_high": {"date": df.at[i_real, "date"].strftime("%Y-%m-%d"),
                      "price_in_latest_dollars": round(float(df.at[i_real, "real_price"]), 2)},
        "latest_vs_real_high_pct": round(100 * (last["real_price"] / df.at[i_real, "real_price"] - 1), 1),
        "days_beyond_cpi": int(df["beyond_cpi"].sum()),
    }


def by_year(df: pd.DataFrame, cpi: pd.DataFrame) -> list:
    """Per calendar year: last close vs the previous year's last close,
    December CPI vs the previous December, and the real change. Only complete
    years with a previous year in the data."""
    closes = df.groupby(df["date"].dt.year).last()
    december = cpi[cpi["month"].dt.month == 12]
    dec = pd.Series(december["cpi"].to_numpy(), index=december["month"].dt.year.to_numpy())
    last_year_in_data = int(df["date"].iloc[-1].year)
    rows = []
    for year in closes.index[1:]:
        if year == last_year_in_data and df["date"].iloc[-1].month < 12:
            continue                       # year not finished
        if year not in dec.index or (year - 1) not in dec.index:
            continue
        nominal = closes.at[year, "price"] / closes.at[year - 1, "price"] - 1
        inflation = dec[year] / dec[year - 1] - 1
        real = (1 + nominal) / (1 + inflation) - 1
        rows.append({"year": int(year), "nominal_pct": round(100 * nominal, 1),
                     "cpi_pct": round(100 * inflation, 1), "real_pct": round(100 * real, 1),
                     "beat_inflation": bool(nominal > inflation)})
    return rows


def detector_with_and_without_inflation(df: pd.DataFrame, switches: dict = None) -> dict:
    """Run the unchanged detector on nominal and on deflated prices, and count
    the days whose flag differs. Contract-switch days are treated the same way
    in both runs: the reported move, deflated, stands in for the jump."""
    switches = switches or {}
    nominal = compute_anomalies(df[["date", "price"]], reported_returns=switches)
    real_input = df[["date", "real_price"]].rename(columns={"real_price": "price"})
    # The reported move on a switch day is a nominal move; deflate it by that
    # day's CPI drift so both runs see the same market move.
    if switches:
        drift = (df.set_index(df["date"].dt.strftime("%Y-%m-%d"))["cpi"].pct_change())
        switches_real = {d: (1 + r) / (1 + float(drift.get(d, 0.0) or 0.0)) - 1
                         for d, r in switches.items()}
    else:
        switches_real = {}
    real = compute_anomalies(real_input, reported_returns=switches_real)
    a, b = nominal["anomaly_flag"].to_numpy(), real["anomaly_flag"].to_numpy()
    valid = nominal["rolling_std"].notna().to_numpy()
    differ = (a != b) & valid
    daily_drift = df["cpi"].pct_change().abs()
    strongest = nominal[["z_score", "cumulative_z_score"]].abs().max(axis=1)
    from src.modeling.anomaly_detector import Z_SCORE_THRESHOLD
    distance = (strongest[differ] - Z_SCORE_THRESHOLD).abs()
    return {
        # How far from the cut-off the differing days were: if every one sat
        # within a few hundredths of it, deflating only tipped borderline days.
        "max_distance_from_threshold": round(float(distance.max()), 3) if differ.any() else None,
        "days": int(valid.sum()),
        "flagged_nominal": int(a[valid].sum()),
        "flagged_real": int(b[valid].sum()),
        "days_that_differ": int(differ.sum()),
        "dates_that_differ": [str(d)[:10] for d in nominal.loc[differ, "date"]],
        "median_abs_daily_return_pct": round(100 * float(df["price"].pct_change().abs().median()), 3),
        "median_abs_daily_cpi_drift_pct": round(100 * float(daily_drift.median()), 4),
    }


def analyse(key: str, cpi: pd.DataFrame) -> dict:
    cfg = get_commodity(key)
    path = REPO_ROOT / "data" / "raw" / cfg.price_file
    if not path.exists():
        return {"key": key, "display_name": cfg.display_name, "missing": True,
                "fetch": f"python -m src.modeling.fetch_price_data --commodity {key}"}
    prices = pd.read_csv(path).dropna(subset=["price"])
    prices = prices[pd.to_datetime(prices["date"]) >= cpi["month"].min().to_timestamp()]
    df = deflate(prices, cpi)
    return {"key": key, "display_name": cfg.display_name, "missing": False,
            "whole_period": whole_period(df),
            "by_year": by_year(df, cpi),
            "detector": detector_with_and_without_inflation(df, load_contract_switches(key)),
            "_frame": df}


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _plot(results: list, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    have = [r for r in results if not r["missing"]]
    if not have:
        return
    fig, axes = plt.subplots(len(have), 1, figsize=(10, 2.6 * len(have)), sharex=True)
    axes = np.atleast_1d(axes)
    for ax, r in zip(axes, have):
        df = r["_frame"]
        ax.plot(df["date"], df["price"], lw=1, color="#888888", label="nominal")
        ax.plot(df["date"], df["real_price"], lw=1.2, color="#1f5fa8",
                label=f"real (dollars of {r['cpi_base']})")
        ax.set_title(r["display_name"], fontsize=10, loc="left")
        ax.grid(alpha=0.25)
    axes[0].legend(fontsize=8, loc="upper left")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=120)
    plt.close(fig)


def write_report(results: list, cpi: pd.DataFrame, md_path: Path, json_path: Path,
                 plot_path: Path) -> None:
    base = str(cpi["month"].iloc[-1])
    interpolated = [str(m) for m in cpi.loc[cpi["interpolated"], "month"]]
    for r in results:
        r["cpi_base"] = base
    lines = [
        "# Inflation comparison",
        "",
        f"Deflator: US CPI-U, all items, seasonally adjusted (BLS CUSR0000SA0 = FRED CPIAUCSL), "
        f"{cpi['month'].iloc[0]} to {base}. Real prices are in dollars of {base}."
        + (f" Months missing from the published series and interpolated: "
           f"{', '.join(interpolated)}." if interpolated else ""),
        "",
        "Produced by `python -m src.analysis.inflation`. The detector itself is unchanged; "
        "this is an analysis next to it.",
        "",
        "## 1. Whole period: how much of the move is inflation",
        "",
        "| Commodity | From | To | Nominal | CPI | Real | Nominal high | Real high | Latest vs real high |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        if r["missing"]:
            lines.append(f"| {r['display_name']} | no price file - run `{r['fetch']}` ||||||||")
            continue
        w = r["whole_period"]
        lines.append(
            f"| {r['display_name']} | {w['start']} | {w['end']} | {w['nominal_change_pct']:+.1f}% "
            f"| {w['cpi_change_pct']:+.1f}% | {w['real_change_pct']:+.1f}% "
            f"| {w['nominal_high']['date']} | {w['real_high']['date']} "
            f"| {w['latest_vs_real_high_pct']:+.1f}% |")
    beyond = {r["display_name"]: r["whole_period"]["days_beyond_cpi"]
              for r in results if not r["missing"] and r["whole_period"]["days_beyond_cpi"]}
    if beyond:
        lines += ["", "Trading days after the last published CPI month (deflated with the last "
                  "published value): " + ", ".join(f"{k} {v}" for k, v in beyond.items()) + "."]

    lines += ["", "## 2. Year by year: did the commodity beat consumer inflation?", "",
              "Year-end close vs previous year-end close, against December-to-December CPI. "
              "Real = (1 + nominal) / (1 + CPI) - 1.", ""]
    for r in results:
        if r["missing"] or not r["by_year"]:
            continue
        beat = sum(1 for y in r["by_year"] if y["beat_inflation"])
        lines += [f"### {r['display_name']} - beat inflation in {beat} of {len(r['by_year'])} years",
                  "", "| Year | Nominal | CPI | Real |", "|---|---|---|---|"]
        lines += [f"| {y['year']} | {y['nominal_pct']:+.1f}% | {y['cpi_pct']:+.1f}% | {y['real_pct']:+.1f}% |"
                  for y in r["by_year"]]
        lines.append("")

    lines += ["## 3. Does deflating change what the detector flags?", "",
              "The same detector (75-day window, z >= 2.0, 10-day cumulative check, contract-switch "
              "handling where a list exists) run on nominal and on deflated prices.", "",
              "| Commodity | Days | Flagged (nominal) | Flagged (real) | Days that differ "
              "| Median daily move | Median daily CPI drift |",
              "|---|---|---|---|---|---|---|"]
    for r in results:
        if r["missing"]:
            continue
        d = r["detector"]
        lines.append(f"| {r['display_name']} | {d['days']} | {d['flagged_nominal']} | {d['flagged_real']} "
                     f"| {d['days_that_differ']} | {d['median_abs_daily_return_pct']:.2f}% "
                     f"| {d['median_abs_daily_cpi_drift_pct']:.4f}% |")
    differ = [(r["display_name"], r["detector"]["dates_that_differ"]) for r in results
              if not r["missing"] and r["detector"]["dates_that_differ"]]
    lines += ["", "Dates that differ: " + ("; ".join(f"{n}: {', '.join(ds)}" for n, ds in differ)
                                          if differ else "none."), "",
              "Largest distance of a differing day's z-score from the 2.0 cut-off: "
              + ("; ".join(f"{r['display_name']} {r['detector']['max_distance_from_threshold']}"
                           for r in results if not r["missing"]
                           and r["detector"]["max_distance_from_threshold"] is not None) or "n/a")
              + ". Days that differ are days the detector was already on the fence about.", "",
              "Reading this table: the CPI moves prices by about a hundredth of a percent a day, "
              "against typical daily moves of one to two percent, so a daily z-score is almost "
              "blind to it. Inflation matters for statements about price LEVELS (a record high, "
              "a multi-year comparison), which is what sections 1 and 2 are for; it is not a "
              "reason to change the detector.", "",
              f"![Nominal and real prices]({plot_path.name})", ""]
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(lines), encoding="utf-8")
    serialisable = [{k: v for k, v in r.items() if k != "_frame"} for r in results]
    json_path.write_text(json.dumps({"cpi_base": base, "cpi_interpolated_months": interpolated,
                                     "commodities": serialisable}, indent=2), encoding="utf-8")
    _plot(results, plot_path)
    print(f"Saved {md_path}, {json_path.name}, {plot_path.name}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--commodity", choices=list(COMMODITIES.keys()),
                        help="One commodity (default: all of them)")
    parser.add_argument("--refresh-cpi", action="store_true",
                        help="Re-download CPIAUCSL from FRED before the analysis")
    args = parser.parse_args()
    if args.refresh_cpi:
        refresh_cpi()
    cpi = load_cpi()
    keys = [args.commodity] if args.commodity else list(COMMODITIES)
    results = [analyse(k, cpi) for k in keys]
    for r in results:
        if r["missing"]:
            print(f"[{r['display_name']}] no price file - run: {r['fetch']}")
        else:
            w, d = r["whole_period"], r["detector"]
            print(f"[{r['display_name']}] nominal {w['nominal_change_pct']:+.1f}%, "
                  f"real {w['real_change_pct']:+.1f}%; detector flags differ on "
                  f"{d['days_that_differ']} of {d['days']} days")
    write_report(results, cpi, RESULTS_DIR / "inflation_comparison.md",
                 RESULTS_DIR / "inflation_comparison.json",
                 RESULTS_DIR / "inflation_comparison.png")


if __name__ == "__main__":
    main()
