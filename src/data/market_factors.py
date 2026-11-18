"""
The shared drivers: the dollar, the market, the complex, and four exchange
rates.

Two modules need these and neither can work without them:

  src/modeling/factor_model.py  removes the part of a commodity's move that
                                the dollar, equities and the broad complex
                                explain, so a flagged day can be called
                                commodity-specific or macro-driven.
  src/analysis/numeraire.py     prices a commodity in euro, yen, yuan and
                                rupees as well as dollars, to separate "the
                                commodity moved" from "the measuring stick
                                moved".

Sources, all keyless. The daily series come from FRED's public CSV
endpoint, the same one src/data/cpi.py uses:

    DTWEXBGS   broad trade-weighted US dollar index (the Fed's own)
    DFII10     10-year US real yield (TIPS)
    T10YIE     10-year breakeven inflation
    DGS10      10-year nominal Treasury yield
    DEXUSEU    US dollars per euro
    DEXJPUS    yen per US dollar
    DEXCHUS    yuan per US dollar
    DEXINUS    rupees per US dollar

Two series FRED does not carry daily and far enough back come from Yahoo
Finance through yfinance, which the project already uses for futures:

    ^GSPC      S&P 500, the risk-appetite factor
    DBC        Invesco DB Commodity Index Fund, the broad-complex factor

Why the broad dollar index and not DXY. DXY is roughly 58% euro by weight,
so a move in it is substantially a move in one currency pair; using it
would make "the dollar" mean "the euro" in every result. DTWEXBGS is
trade-weighted across the currencies the US actually trades with, which is
what the numeraire argument needs. Both are recorded if available so the
choice can be checked, but the factor model uses the broad index.

Why DBC rather than a spot index. It is an investable fund, so it exists at
daily frequency over the whole period; a spot index like the S&P GSCI is
not freely available at that frequency without a key. DBC holds energy
heavily, which means that for crude oil the "broad complex" factor is
partly the commodity itself - the factor model's report prints the window
R-squared so that overlap is visible rather than hidden, and crude's
residual should be read with it in mind.

Exchange rate direction. FRED quotes these inconsistently: DEXUSEU is
dollars per euro, the other three are foreign units per dollar. This module
normalises every one to FOREIGN UNITS PER US DOLLAR, so multiplying a
dollar price by the rate always gives the local price. The conversion is
done once, here, rather than in each caller, because getting it backwards
inverts the sign of every pass-through result downstream.

Usage:
    python -m src.data.market_factors
    python -m src.data.market_factors --start 2005-01-01
"""

import argparse
import csv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_PATH = REPO_ROOT / "data" / "raw" / "market_factors.csv"
LEVELS_PATH = REPO_ROOT / "data" / "raw" / "market_factor_levels.csv"
SOURCES_PATH = REPO_ROOT / "data" / "raw" / "market_factor_sources.csv"

DEFAULT_START = "2005-01-01"

# series id -> (column name, what it is, invert?)
# invert=True means FRED quotes it as US dollars per foreign unit and it has
# to be flipped to reach foreign units per US dollar.
FRED_SERIES = {
    "DTWEXBGS": ("dollar_broad", "Broad trade-weighted US dollar index", False),
    "DFII10": ("real_yield_10y", "10-year US real yield (TIPS), percent", False),
    "T10YIE": ("breakeven_10y", "10-year breakeven inflation, percent", False),
    "DGS10": ("nominal_yield_10y", "10-year Treasury yield, percent", False),
    "DEXUSEU": ("eur_per_usd", "Euro per US dollar (FRED quotes USD per EUR)", True),
    "DEXJPUS": ("jpy_per_usd", "Yen per US dollar", False),
    "DEXCHUS": ("cny_per_usd", "Yuan per US dollar", False),
    "DEXINUS": ("inr_per_usd", "Rupee per US dollar", False),
}

YAHOO_SERIES = {
    "^GSPC": ("equity", "S&P 500 close"),
    "DBC": ("broad_commodity", "Invesco DB Commodity Index Fund close"),
}

# A second source for every FRED series that has one. FRED was unreachable
# from the developer's network on 11 November 2026 - 32 attempts across 8
# series, every one a reset connection or a read timeout, while Yahoo served
# 10,725 rows in the same run. That is a block on one host, not a rate
# limit, and no amount of backoff fixes it.
#
# The substitutions are NOT equivalent and the difference is recorded in
# data/raw/market_factor_sources.csv and printed on every run:
#
#   DTWEXBGS -> DX-Y.NYB   The Fed's broad index is trade-weighted across
#                          the currencies the US actually trades with. DXY
#                          is a fixed 1973 basket about 58% euro, so "the
#                          dollar" becomes substantially "the euro". For
#                          the numeraire argument that matters: a move
#                          driven by the euro alone would read as a dollar
#                          move. `dollar_basket` below is the mitigation.
#   DEX* -> *=X            Spot rates rather than the Fed's noon fixings.
#                          Different snapshot time, same currency pair;
#                          close enough for daily returns and not for a
#                          level comparison.
#   DFII10, T10YIE, DGS10  No free daily equivalent. ^TNX is the nominal
#                          10-year yield and is taken where available; the
#                          real yield has no Yahoo substitute, so it is
#                          simply absent when FRED is unreachable. Nothing
#                          in the factor model uses it - it is context for
#                          gold - so its absence does not block a run.
YAHOO_FALLBACK = {
    "DTWEXBGS": ("DX-Y.NYB", "US dollar index (DXY) - a different basket, see note", False),
    "DEXUSEU": ("EURUSD=X", "US dollars per euro (spot)", True),
    "DEXJPUS": ("JPY=X", "Yen per US dollar (spot)", False),
    "DEXCHUS": ("CNY=X", "Yuan per US dollar (spot)", False),
    "DEXINUS": ("INR=X", "Rupee per US dollar (spot)", False),
    "DGS10": ("^TNX", "10-year Treasury yield (index points = percent)", False),
}

# Series the run can finish without. The factor model uses only the three
# in FACTOR_COLUMNS; these are context, and refusing to write the table
# because a context series is missing would block the whole analysis over
# a column nothing reads.
OPTIONAL_COLUMNS = ("real_yield_10y", "breakeven_10y", "nominal_yield_10y")

# Columns the factor model needs as RETURNS. Everything else is carried at
# its level, because a yield is already a rate and differencing it twice is
# meaningless.
RETURN_COLUMNS = ("dollar_broad", "equity", "broad_commodity",
                  "eur_per_usd", "jpy_per_usd", "cny_per_usd", "inr_per_usd")
LEVEL_COLUMNS = ("real_yield_10y", "breakeven_10y", "nominal_yield_10y")


def fetch_fred(series_id: str, start: str) -> list:
    """Reuses cpi.py's fetcher so there is one FRED code path, not two -
    including its session, its retries and its backoff, which exist because
    FRED resets connections on a burst of rapid sequential requests."""
    from src.data.cpi import fetch_series
    return fetch_series(series_id, start, verbose=True)


def fetch_yahoo(ticker: str, start: str) -> list:
    import yfinance as yf
    df = yf.download(ticker, start=start, progress=False, auto_adjust=True)
    if df is None or df.empty:
        raise RuntimeError(f"yfinance returned no data for {ticker}")
    close = df["Close"]
    if hasattr(close, "columns"):          # MultiIndex for a single ticker
        close = close.iloc[:, 0]
    return [(d.date().isoformat(), float(v)) for d, v in close.items() if v == v]


def build_levels(start: str = DEFAULT_START, verbose: bool = True):
    """{column: {date: level}} with every exchange rate already normalised
    to foreign units per US dollar, plus a record of which source each
    column actually came from.

    FRED first, Yahoo second. A column that came from the fallback is not
    the same series as the one named in the docstring above, so the
    substitution is recorded and printed rather than being silently
    equivalent."""
    import time
    from src.data.cpi import FRED_PAUSE_SECONDS

    out, sources, failed, substituted = {}, {}, [], []

    for i, (series_id, (col, what, invert)) in enumerate(FRED_SERIES.items()):
        if i:
            time.sleep(FRED_PAUSE_SECONDS)   # a run of requests, not a burst
        rows, used, note = None, None, ""
        try:
            rows = fetch_fred(series_id, start)
            used = f"FRED:{series_id}"
        except Exception as exc:  # noqa: BLE001 - try the second source next
            first_error = f"{type(exc).__name__}"
            fb = YAHOO_FALLBACK.get(series_id)
            if fb is None:
                failed.append((series_id, col, first_error))
                if verbose:
                    print(f"  {series_id:<10} FAILED ({first_error}); no second source")
                continue
            ticker, fb_what, fb_invert = fb
            try:
                rows, invert = fetch_yahoo(ticker, start), fb_invert
                used, note = f"Yahoo:{ticker}", fb_what
                substituted.append((series_id, ticker, col))
                if verbose:
                    print(f"  {series_id:<10} FRED unreachable ({first_error}) "
                          f"-> {ticker}")
            except Exception as exc2:  # noqa: BLE001
                failed.append((series_id, col, f"{first_error} / {type(exc2).__name__}"))
                if verbose:
                    print(f"  {series_id:<10} FAILED on both sources "
                          f"({first_error}, {type(exc2).__name__})")
                continue

        values = {d: (1.0 / v if invert and v else v) for d, v in rows if v}
        out[col] = values
        sources[col] = {"used": used, "note": note}
        if verbose:
            span = f"{rows[0][0]} to {rows[-1][0]}" if rows else "no rows"
            print(f"  {col:<18} {len(values):>5} rows  {span}  {used}")

    for ticker, (col, what) in YAHOO_SERIES.items():
        try:
            rows = fetch_yahoo(ticker, start)
        except Exception as exc:  # noqa: BLE001
            failed.append((ticker, col, type(exc).__name__))
            if verbose:
                print(f"  {ticker:<10} FAILED: {type(exc).__name__}: {str(exc)[:80]}")
            continue
        out[col] = dict(rows)
        sources[col] = {"used": f"Yahoo:{ticker}", "note": ""}
        if verbose:
            span = f"{rows[0][0]} to {rows[-1][0]}" if rows else "no rows"
            print(f"  {col:<18} {len(rows):>5} rows  {span}  Yahoo:{ticker}")

    # Only a column the factor model or the numeraire test actually reads
    # can stop the run. A missing context series is reported and skipped.
    blocking = [(sid, col, err) for sid, col, err in failed
                if col not in OPTIONAL_COLUMNS]
    if blocking:
        names = ", ".join(f"{sid} ({col})" for sid, col, _ in blocking)
        raise SystemExit(
            f"\n{len(blocking)} required series could not be downloaded from either "
            f"source: {names}. The existing {OUTPUT_PATH.name} was left alone: a table "
            "with a factor missing gives regressions that run and are wrong.")
    skipped = [col for _sid, col, _e in failed if col in OPTIONAL_COLUMNS]
    if skipped and verbose:
        print(f"\n  Context series unavailable and skipped: {', '.join(sorted(set(skipped)))}. "
              "Nothing in the factor model reads them.")
    return out, sources, substituted


def dollar_basket(levels: dict):
    """A second dollar measure built from the exchange rates themselves.

    DXY is about 58% euro by weight, so when it stands in for the Fed's
    broad index "the dollar" quietly becomes "the euro", and a move driven
    by one currency reads as a move in the numeraire. This is the check on
    that: an equal-weighted average of the log changes in the four rates
    already fetched, each quoted as foreign units per dollar, so it rises
    when the dollar rises.

    Equal weights are a deliberate choice, not an estimate of trade shares.
    They are stated rather than fitted, and the point is only that a result
    which holds under both measures does not depend on the euro."""
    import numpy as np
    import pandas as pd

    rates = [c for c in ("eur_per_usd", "jpy_per_usd", "cny_per_usd", "inr_per_usd")
             if c in levels]
    if len(rates) < 2:
        return None
    frame = {}
    for c in rates:
        s = pd.Series(levels[c])
        s.index = pd.to_datetime(s.index)
        frame[c] = np.log(s.astype(float).sort_index()).diff()
    return pd.DataFrame(frame).mean(axis=1, skipna=True)


def to_returns(levels: dict):
    """Daily log returns for the price-like columns, levels for the rates.

    Returns are taken over consecutive OBSERVED days, not calendar days, and
    nothing is forward-filled: holidays differ between the exchanges and the
    FRED series, and filling a gap invents a zero-return day that the
    regression would treat as real."""
    import numpy as np
    import pandas as pd

    frame = {}
    for col, values in levels.items():
        s = pd.Series(values)
        s.index = pd.to_datetime(s.index)
        frame[col] = s.sort_index()
    df = pd.DataFrame(frame).sort_index()

    out = pd.DataFrame(index=df.index)
    for col in RETURN_COLUMNS:
        if col in df.columns:
            out[col] = np.log(df[col].astype(float)).diff()
    for col in LEVEL_COLUMNS:
        if col in df.columns:
            out[col] = df[col].astype(float)
            out[col + "_change"] = df[col].astype(float).diff()

    # The factor model's three columns, under the names it expects.
    if "dollar_broad" in out.columns:
        out["dollar"] = out["dollar_broad"]
    basket = dollar_basket(levels)
    if basket is not None:
        out["dollar_basket"] = basket.reindex(out.index)
    return df, out


def write(levels: dict, sources: dict = None, path: Path = OUTPUT_PATH,
          levels_path: Path = LEVELS_PATH) -> int:
    lv, rt = to_returns(levels)
    path.parent.mkdir(parents=True, exist_ok=True)
    rt.index.name = "date"
    rt.to_csv(path)
    lv.index.name = "date"
    lv.to_csv(levels_path)
    if sources:
        # Which source each column actually came from. A result read months
        # later must not have to guess whether "dollar" meant the Fed's
        # broad index or DXY, because the two answer different questions.
        with open(SOURCES_PATH, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["column", "source", "note"])
            for col, s in sorted(sources.items()):
                w.writerow([col, s["used"], s["note"]])
    return len(rt)


def main():
    p = argparse.ArgumentParser(description="Download the shared market drivers")
    p.add_argument("--start", default=DEFAULT_START)
    args = p.parse_args()
    levels, sources, substituted = build_levels(args.start)
    n = write(levels, sources)
    print(f"\nSaved {OUTPUT_PATH}  ({n} rows, daily returns)")
    print(f"Saved {LEVELS_PATH}  (the underlying levels, for checking)")
    print(f"Saved {SOURCES_PATH}  (which source each column came from)")
    print("\nExchange rates are normalised to FOREIGN UNITS PER US DOLLAR: multiply a "
          "dollar price by the rate to get the local price.")
    if substituted:
        print("\nSecond source used for: "
              + ", ".join(f"{sid} -> {tk}" for sid, tk, _c in substituted))
        if any(sid == "DTWEXBGS" for sid, _t, _c in substituted):
            print("  The dollar column is DXY, a fixed basket about 58% euro, not the "
                  "Fed's trade-weighted index.\n"
                  "  `dollar_basket` is in the table beside it: an equal-weighted "
                  "average of the four exchange rates.\n"
                  "  Run the factor model both ways. A result that holds under both "
                  "does not depend on the euro.")


if __name__ == "__main__":
    main()
