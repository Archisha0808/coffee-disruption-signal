"""
Was the move about this commodity, or about the dollar and the market?

The base detector (src/modeling/anomaly_detector.py) flags a day when one
price moved unusually against its own recent volatility. It never looks at
anything else, so it cannot distinguish a supply disruption from a day the
dollar fell and every dollar-priced asset repriced. The explanation
pipeline then goes looking for a coffee story, because a coffee story is
what it was asked for, and the evidence rule has no way to notice that the
question was wrong.

This module adds the layer that notices. For each day it removes the part
of the return that the shared drivers explain, and flags what is left:

    return = a + b1 * dollar + b2 * equity + b3 * broad commodity + residual

The betas are estimated on a trailing window that EXCLUDES the day being
tested, so the day cannot pull the line towards itself and hide its own
residual. The residual is then z-scored against the same window's residual
spread, which is the direct analogue of what the base detector does to the
raw return.

Every flagged day gets one of three labels:

    commodity-specific   the residual is extreme
    macro-driven         the raw move is extreme, the residual is not
    both                 the raw move is extreme and so is what is left

This runs ALONGSIDE the base detector and never replaces it. That is not a
style preference: the 16 labelled dates, the 279 coffee anomalies and every
evaluation figure in results/ were drawn at the base detector's raw 2-sigma
threshold. Swapping the detector would change which dates exist and quietly
invalidate the answer key, so `anomaly_flag` keeps its meaning and the new
columns sit beside it.

Why these three factors. The dollar, because commodities are quoted in it
and a move in the numeraire moves every price without anything happening to
any commodity. Equities, because risk appetite moves commodity and share
prices together. A broad commodity index, because it absorbs what is common
to the complex (freight, energy costs, the commodity cycle) and leaves
behind what is particular to this market. Together they are the shared
drivers; they are not a complete model of a commodity price, and the
unexplained residual is always reported rather than attributed.

What this does NOT establish: that a macro-driven day was CAUSED by the
dollar. A high R-squared says the move is consistent with the shared
drivers; a confound that moves with the dollar would look the same. The
honest reading of a macro verdict is "nothing here needs a commodity story",
which is a reason to refuse, not a cause.

Usage:
    python -m src.modeling.factor_model --commodity coffee
    python -m src.modeling.factor_model --all
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.config.commodities import COMMODITIES

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = REPO_ROOT / "results"
RAW_DIR = REPO_ROOT / "data" / "raw"
FACTORS_PATH = RAW_DIR / "market_factors.csv"

# Matches the base detector, so the two layers are comparable and neither
# was tuned against the other.
WINDOW_DAYS = 75
Z_THRESHOLD = 2.0

# The factor columns expected in data/raw/market_factors.csv. Written by
# src/data/market_factors.py; see that module for each series and source.
FACTOR_COLUMNS = ("dollar", "equity", "broad_commodity")

# Below this many usable rows in the trailing window the betas are noise and
# the day is left unclassified rather than guessed at.
MIN_WINDOW_OBS = 40

# Matches the base detector's second check. A day flagged only by that check
# has no extreme daily move to explain, so the daily residual says nothing
# about it and it has to be assessed over the same horizon it was flagged on.
CUMULATIVE_WINDOW_DAYS = 10


def load_factors(path: Path = FACTORS_PATH) -> pd.DataFrame:
    """Daily log returns of each shared driver, dates indexed."""
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run: python -m src.data.market_factors")
    df = pd.read_csv(path, parse_dates=["date"]).set_index("date").sort_index()
    missing = [c for c in FACTOR_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{path} is missing factor column(s): {missing}")
    return df[list(FACTOR_COLUMNS)]


def log_returns(prices: pd.Series) -> pd.Series:
    """Daily log returns, with non-positive prices removed rather than
    turned into silent NaN.

    WTI settled at -$37.63 on 20 April 2020. A log return is undefined on a
    negative price, and numpy answers with NaN and a warning that is easy to
    miss - so the most famous day in the oil series would quietly drop out of
    every regression with nothing in the output saying so. Masking it makes
    the gap explicit: that day and the one after have no defined return, and
    both come back unclassified."""
    p = prices.astype(float)
    bad = p <= 0
    if bad.any():
        p = p.mask(bad)
    return np.log(p).diff()


def _ols(X: np.ndarray, y: np.ndarray):
    """Least squares with an intercept. numpy only - the same dependency
    avoidance the rest of the project uses (no scipy, no scikit-learn)."""
    A = np.column_stack([np.ones(len(X)), X])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    fitted = A @ beta
    return beta, y - fitted


def residual_series(commodity_returns: pd.Series, factors: pd.DataFrame,
                    window: int = WINDOW_DAYS,
                    min_obs: int = MIN_WINDOW_OBS) -> pd.DataFrame:
    """Per day: the factor-explained part, the residual, and the residual's
    z-score against the same trailing window.

    The window ends the day BEFORE the day being tested. A day included in
    its own estimation window pulls the fitted line towards itself, which
    shrinks exactly the residual the test is looking for - on a large single
    day with a 75-day window that bias is easily enough to hide a real
    outlier."""
    joined = pd.concat([commodity_returns.rename("y"), factors], axis=1,
                       sort=True).dropna()
    out = []
    ys, Xs, idx = joined["y"].to_numpy(), joined[list(FACTOR_COLUMNS)].to_numpy(), joined.index

    for i in range(len(joined)):
        lo = max(0, i - window)
        Xw, yw = Xs[lo:i], ys[lo:i]
        if len(yw) < min_obs:
            out.append((idx[i], np.nan, np.nan, np.nan, np.nan))
            continue
        beta, resid_w = _ols(Xw, yw)
        predicted = float(beta[0] + Xs[i] @ beta[1:])
        residual = float(ys[i] - predicted)
        sd = float(np.std(resid_w, ddof=1))
        z = residual / sd if sd > 0 else np.nan
        # Share of the window's variance the factors account for: context for
        # how much weight the residual deserves on this commodity.
        var_y = float(np.var(yw, ddof=1))
        r2 = 1.0 - (float(np.var(resid_w, ddof=1)) / var_y) if var_y > 0 else np.nan
        out.append((idx[i], predicted, residual, z, r2))

    return pd.DataFrame(out, columns=["date", "factor_explained", "residual",
                                      "residual_z", "window_r2"]).set_index("date")


def cumulative_residual_series(commodity_returns: pd.Series, factors: pd.DataFrame,
                               window: int = WINDOW_DAYS,
                               cum_days: int = CUMULATIVE_WINDOW_DAYS,
                               min_obs: int = MIN_WINDOW_OBS) -> pd.DataFrame:
    """The same test over the horizon the cumulative check flags on.

    A day flagged only by the detector's 10-day check has, by construction,
    no extreme daily move: it was flagged for a build-up. Judging it by a
    daily residual asks the wrong question and answers it confidently - the
    daily residual is small because the daily move was small, so the day
    comes back "macro-driven" whatever drove it. On coffee that mislabelled
    149 of 279 flagged days.

    So the commodity's 10-day cumulative return is regressed on the factors'
    10-day cumulative returns, betas fitted on the trailing window ending
    before the day tested, exactly as the daily version does.

    One caveat that does not apply to the daily test: consecutive 10-day
    windows overlap by nine days, so these residuals are autocorrelated and
    the spread they are z-scored against is too narrow. The z-scores here
    are therefore optimistic - they overstate how unusual a day is - and are
    read as a ranking rather than as a probability. The same overlap is
    present in the detector's own cumulative check, so the two are at least
    consistent with each other."""
    y = commodity_returns.rolling(cum_days).sum()
    X = factors.rolling(cum_days).sum()
    joined = pd.concat([y.rename("y"), X], axis=1, sort=True).dropna()
    ys, Xs, idx = joined["y"].to_numpy(), joined[list(FACTOR_COLUMNS)].to_numpy(), joined.index

    out = []
    for i in range(len(joined)):
        lo = max(0, i - window)
        Xw, yw = Xs[lo:i], ys[lo:i]
        if len(yw) < min_obs:
            out.append((idx[i], np.nan, np.nan))
            continue
        beta, resid_w = _ols(Xw, yw)
        residual = float(ys[i] - (beta[0] + Xs[i] @ beta[1:]))
        sd = float(np.std(resid_w, ddof=1))
        out.append((idx[i], residual, residual / sd if sd > 0 else np.nan))
    return pd.DataFrame(out, columns=["date", "cum_residual",
                                      "cum_residual_z"]).set_index("date")


def classify_day(anomaly_type, residual_z, cum_residual_z,
                 threshold: float = Z_THRESHOLD):
    """The label, and which test produced it.

    A flagged day is assessed over the horizon it was flagged on: a daily
    shock by the daily residual, a build-up by the 10-day cumulative one. A
    day flagged by both is judged on the daily move, which is the larger
    claim. Days the base detector did not flag are not classified at all -
    this layer explains the detector's flags, it never adds any.

    Only two outcomes are possible for a flagged day, because a flagged day
    already has an extreme raw move: either what is left after the factors
    is also extreme, or it is not."""
    kind = (anomaly_type or "").strip()
    if not kind:
        return "", ""
    if "shock" in kind:
        z, how = residual_z, "daily residual"
    elif "trend" in kind:
        z, how = cum_residual_z, f"{CUMULATIVE_WINDOW_DAYS}-day cumulative residual"
    else:
        return "unclassified", ""
    if z is None or pd.isna(z):
        return "unclassified", how
    return ("commodity-specific" if abs(z) >= threshold else "macro-driven"), how


def analyse(commodity_key: str, factors: pd.DataFrame = None,
            window: int = WINDOW_DAYS, threshold: float = Z_THRESHOLD) -> pd.DataFrame:
    """Join the stored detections to the factor residuals and classify."""
    cfg = COMMODITIES[commodity_key]
    det_path = RESULTS_DIR / cfg.anomalies_file
    if not det_path.exists():
        raise FileNotFoundError(
            f"{det_path} not found. Run: python -m src.modeling.anomaly_detector "
            f"--commodity {commodity_key}")
    det = pd.read_csv(det_path, parse_dates=["date"]).set_index("date").sort_index()
    factors = load_factors() if factors is None else factors

    rets = log_returns(det["price"])
    df = det.join(residual_series(rets, factors, window=window), how="left")
    df = df.join(cumulative_residual_series(rets, factors, window=window), how="left")

    # A contract-switch day shows a move no contract made, so its residual is
    # an artefact of the series, not of the market.
    switch = (df["contract_switch"].fillna(False).astype(bool)
              if "contract_switch" in df.columns else pd.Series(False, index=df.index))
    df.loc[switch, ["residual", "residual_z", "factor_explained",
                    "cum_residual", "cum_residual_z"]] = np.nan

    labels, hows = [], []
    for flag, kind, z, cz, sw in zip(df["anomaly_flag"].fillna(False), df.get("anomaly_type"),
                                     df["residual_z"], df["cum_residual_z"], switch):
        if not bool(flag) or bool(sw):
            labels.append("")
            hows.append("")
            continue
        label, how = classify_day(kind, z, cz, threshold)
        labels.append(label)
        hows.append(how)
    df["factor_class"] = labels
    df["assessed_by"] = hows
    return df


def summarise(df: pd.DataFrame, commodity_key: str) -> dict:
    flagged = df[df["factor_class"] != ""]
    counts = flagged["factor_class"].value_counts().to_dict()
    assessed = flagged[flagged["factor_class"] != "unclassified"]
    n = len(assessed)
    by_test = flagged["assessed_by"].value_counts().to_dict()
    return {
        "commodity": commodity_key,
        "flagged_days": len(flagged),
        "assessed": n,
        "classes": {k: int(v) for k, v in counts.items()},
        "by_test": {k: int(v) for k, v in by_test.items() if k},
        "macro_share": ((assessed["factor_class"] == "macro-driven").mean()
                        if n else None),
        "macro_share_shock_days": (
            lambda s: float((s["factor_class"] == "macro-driven").mean()) if len(s) else None
        )(assessed[assessed["assessed_by"] == "daily residual"]),
        "median_window_r2": (float(flagged["window_r2"].median())
                             if len(flagged) and flagged["window_r2"].notna().any() else None),
        "first_date": str(flagged.index.min().date()) if len(flagged) else None,
        "last_date": str(flagged.index.max().date()) if len(flagged) else None,
    }


def report(summaries: list) -> str:
    L = ["# Factor-Adjusted Anomalies: which flagged days are about the commodity", ""]
    L.append("Each flagged day's return is compared with what the dollar, equities and a "
             "broad commodity index would predict, using betas fitted on the 75 trading "
             "days **before** that day. What is left over is the residual; a day whose "
             "residual is extreme is about this commodity, and a day whose raw move is "
             "extreme while its residual is not was the complex repricing.")
    L.append("")
    L.append("**Each day is assessed over the horizon it was flagged on.** The base "
             "detector flags on a daily shock or on a 10-day build-up, and most flagged "
             "days are the second kind. A build-up has no extreme daily move by "
             "construction, so judging it by a daily residual returns \"macro-driven\" "
             "whatever drove it. Those days are tested against 10-day cumulative factor "
             "returns instead; a day flagged by both is judged on the daily move.")
    L.append("")
    L.append("This sits beside the base detector and does not change it. Every evaluation "
             "figure in `results/` was drawn at the base detector's raw threshold, so "
             "changing which days are flagged would invalidate the answer key.")
    L.append("")
    L.append("| Commodity | Flagged | Assessed | Commodity-specific | Macro-driven | "
             "Macro share | Macro share, shock days only | Median window R² |")
    L.append("|---|---|---|---|---|---|---|---|")
    for s in summaries:
        c = s["classes"]
        share = "-" if s["macro_share"] is None else f"{100 * s['macro_share']:.1f}%"
        shock = ("-" if s["macro_share_shock_days"] is None
                 else f"{100 * s['macro_share_shock_days']:.1f}%")
        r2 = "-" if s["median_window_r2"] is None else f"{s['median_window_r2']:.2f}"
        L.append(f"| {s['commodity']} | {s['flagged_days']} | {s['assessed']} | "
                 f"{c.get('commodity-specific', 0)} | {c.get('macro-driven', 0)} | "
                 f"{share} | {shock} | {r2} |")
    L.append("")
    L.append("Unclassified days are left out of the shares: a day with too little history "
             "for its window, a contract-switch day, or a day whose price was not positive "
             "(WTI settled at -$37.63 on 20 April 2020, where a log return does not exist).")
    L.append("")
    L.append("### Two readings that are not comparable with the others")
    L.append("")
    L.append("**Crude oil's window R² is high because the factor contains the commodity.** "
             "The broad-complex factor is DBC, which is heavily weighted to energy, so "
             "crude is being regressed partly on itself. Its macro share is inflated by "
             "an unknown amount and should not be set beside the others. A spot index "
             "with no energy weight, or dropping the broad factor for crude alone, would "
             "fix it; neither has been done.")
    L.append("")
    L.append("**A low window R² makes the split uninformative.** Where the three factors "
             "account for little of a commodity's day-to-day variation, the residual is "
             "most of the move whatever happened, and \"commodity-specific\" is close to "
             "restating that the day was flagged at all.")
    L.append("")
    L.append("## What a macro verdict does and does not mean")
    L.append("")
    L.append("- **Tested.** The residual and its z-score are the output of a stated model "
             "on a stated window, fitted without the day being tested.")
    L.append("- **Not established.** That the dollar *caused* the move. A confound moving "
             "with the dollar would look identical. The honest reading is narrower: "
             "nothing in this day's move needs a commodity-specific story.")
    L.append("- **The cumulative z-scores are optimistic.** Consecutive 10-day windows "
             "overlap by nine days, so those residuals are autocorrelated and the spread "
             "they are measured against is too narrow. Read them as a ranking, not as a "
             "probability. The detector's own cumulative check has the same property.")
    L.append("- The residual is never attributed. Whatever the three factors do not "
             "explain is reported as unexplained, not assigned to a preferred cause.")
    return "\n".join(L)


def run(commodities=None, verbose: bool = True) -> dict:
    factors = load_factors()
    keys = commodities or [k for k in COMMODITIES
                           if (RESULTS_DIR / COMMODITIES[k].anomalies_file).exists()]
    summaries, out = [], {}
    for key in keys:
        df = analyse(key, factors=factors)
        path = RESULTS_DIR / f"{key}_factor_adjusted.csv"
        cols = [c for c in ("price", "z_score", "anomaly_flag", "anomaly_type",
                            "factor_explained", "residual", "residual_z",
                            "cum_residual", "cum_residual_z", "window_r2",
                            "factor_class", "assessed_by") if c in df.columns]
        df[cols].to_csv(path)
        s = summarise(df, key)
        summaries.append(s)
        out[key] = s
        if verbose:
            print(f"  {key}: {s['flagged_days']} flagged -> {s['classes']}  (saved {path.name})")

    text = report(summaries)
    (RESULTS_DIR / "factor_adjusted_report.md").write_text(text, encoding="utf-8")
    with open(RESULTS_DIR / "factor_adjusted.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    if verbose:
        print("\n" + text)
    return out


def main():
    p = argparse.ArgumentParser(description="Factor-adjusted anomaly classification")
    p.add_argument("--commodity", default=None)
    p.add_argument("--all", action="store_true")
    args = p.parse_args()
    run(commodities=None if (args.all or not args.commodity) else [args.commodity])


if __name__ == "__main__":
    main()
