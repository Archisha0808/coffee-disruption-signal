"""The five-commodity scope: configuration, commodity-aware headline scoring,
the inflation comparison and the cross-commodity detector report. All offline,
on stand-in data."""
from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from src.analysis import inflation
from src.config.commodities import COMMODITIES
from src.rag import blind_evidence
from src.rag import market_report as mr
from scripts import multi_commodity_report as mcr


# --- configuration ---------------------------------------------------------

def test_all_five_commodities_are_configured():
    assert set(COMMODITIES) == {"coffee", "crude_oil", "wheat", "cocoa", "sugar"}


@pytest.mark.parametrize("key", list(COMMODITIES))
def test_history_starts_well_before_every_window(key):
    """A window with no rolling history reports a meaningless MISS or 'clean'
    (see the note on history_start_date): 75 trading days is ~4 months."""
    cfg = COMMODITIES[key]
    start = datetime.strptime(cfg.history_start_date, "%Y-%m-%d")
    windows = [e[1] for e in cfg.known_events] + [cfg.control_period[0]]
    for w in windows:
        assert (datetime.strptime(w, "%Y-%m-%d") - start).days > 120, (key, w)


@pytest.mark.parametrize("key", list(COMMODITIES))
def test_every_commodity_has_its_news_queries(key):
    from src.rag.news_aggregator import INDUSTRY_FEEDS, NEWS_QUERIES
    from src.rag.news_rss import RSS_QUERIES
    cfg = COMMODITIES[key]
    assert cfg.gdelt_queries and cfg.semantic_reference_query
    assert key in RSS_QUERIES and key in NEWS_QUERIES and key in INDUSTRY_FEEDS
    assert key in mr.COMMODITY_NAMES


def test_the_reading_is_told_which_market_is_watched():
    watched, others = blind_evidence.market_names("sugar")
    assert "No. 11" in watched and "London" in others
    watched, _ = blind_evidence.market_names("crude oil")      # as the pipeline passes it
    assert watched == "crude oil futures"                      # no wording configured: generic


# --- headline scoring per commodity ----------------------------------------

def test_coffee_is_still_the_default_and_unchanged():
    title = "SOFTS - Coffee prices jump nearly 7 % in New York after stocks drawn"
    assert mr.market_report_score({"title": title}) == mr.market_report_score({"title": title}, "coffee")
    assert mr.commodity_key("anything unknown") == "coffee"


def test_a_commodity_is_scored_on_its_own_name():
    sugar = {"title": "Raw sugar hits 12-year high on India export curbs"}
    assert mr.market_report_score(sugar) < mr.REPORT_SCORE                  # read as coffee: not a report
    assert mr.market_report_score(sugar, "sugar") >= mr.REPORT_SCORE
    oil = {"title": "Crude oil settles up 4% as OPEC+ cuts output"}
    assert mr.market_report_score(oil, "crude oil") == mr.market_report_score(oil) + 1
    cocoa = {"title": "Cacau despenca em Nova York com chuvas na Costa do Marfim"}
    assert mr.market_report_score(cocoa, "cocoa") >= mr.REPORT_SCORE


def test_a_round_up_is_cut_to_the_passage_about_the_commodity_asked_for():
    text = ("Arabica coffee futures rose on Tuesday as dry weather in Brazil persisted. "
            + "Dealers said the coffee market was watching rain forecasts closely. " * 10
            + "New York cocoa fell 6% to $8,900 a tonne. Dealers said rain in Ivory Coast "
              "eased supply worries. "
            + "London sugar was little changed. " * 5)
    focused = mr.focus_text(text, commodity="cocoa")
    assert "rain in Ivory Coast" in focused[:mr.OPENING_CHARS]
    for piece in focused.split(mr.SEPARATOR):
        assert piece in text                      # still verbatim, so quotes still check
    cocoa_only = "Cocoa rose. " * 100            # names only itself: never rearranged
    assert mr.focus_text(cocoa_only, commodity="cocoa") == cocoa_only


# --- inflation -------------------------------------------------------------

def _cpi(months=36, monthly=0.004, missing=None):
    idx = pd.period_range("2020-01", periods=months, freq="M")
    df = pd.DataFrame({"month": idx, "cpi": 100 * (1 + monthly) ** np.arange(months),
                       "interpolated": False})
    if missing:
        df.loc[df["month"] == pd.Period(missing, "M"), "cpi"] = np.nan
        df["interpolated"] = df["cpi"].isna()
        df["cpi"] = df["cpi"].interpolate()
    return df


def _prices(days=700, drift=0.0, seed=1):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2020-01-02", periods=days)
    price = 100 * np.exp(np.cumsum(drift + rng.normal(0, 0.015, days)))
    return pd.DataFrame({"date": dates.strftime("%Y-%m-%d"), "price": price})


def test_load_cpi_fills_a_missing_month(tmp_path):
    path = tmp_path / "cpi.csv"
    pd.DataFrame({"month": ["2025-08", "2025-09", "2025-11"], "cpi": [320.0, 321.0, 323.0]}).to_csv(path, index=False)
    cpi = inflation.load_cpi(path)
    row = cpi[cpi["month"] == pd.Period("2025-10", "M")].iloc[0]
    assert row["interpolated"] and row["cpi"] == pytest.approx(322.0)


def test_deflating_has_no_step_at_month_starts():
    cpi = _cpi(monthly=0.01)                      # 1% a month: a step would be obvious
    flat = pd.DataFrame({"date": pd.bdate_range("2020-02-03", "2021-06-30").strftime("%Y-%m-%d")})
    flat["price"] = 100.0
    real = inflation.deflate(flat, cpi)
    daily = real["real_price"].pct_change().abs().dropna()
    assert daily.max() < 0.0035                   # ~1%/month spread over the days, never 1% at once
    assert real["real_price"].iloc[0] > real["real_price"].iloc[-1]   # older dollars are worth more


def test_whole_period_separates_inflation_from_the_real_move():
    cpi = _cpi(months=36, monthly=0.004)
    prices = pd.DataFrame({"date": ["2020-01-15", "2022-12-15"], "price": [100.0, 100.0]})
    w = inflation.whole_period(inflation.deflate(prices, cpi))
    assert w["nominal_change_pct"] == 0.0
    assert w["cpi_change_pct"] > 14 and w["real_change_pct"] < -12


def test_by_year_compares_against_december_cpi():
    cpi = _cpi(months=36, monthly=0.004)
    dates = pd.bdate_range("2020-01-02", "2022-12-30")
    prices = pd.DataFrame({"date": dates.strftime("%Y-%m-%d"),
                           "price": np.linspace(100, 160, len(dates))})
    rows = inflation.by_year(inflation.deflate(prices, cpi), cpi)
    assert [r["year"] for r in rows] == [2021, 2022]
    for r in rows:
        assert r["cpi_pct"] == pytest.approx(100 * (1.004 ** 12 - 1), abs=0.1)
        assert r["beat_inflation"] and r["real_pct"] < r["nominal_pct"]


def test_the_detector_barely_notices_inflation():
    cpi = _cpi(months=36, monthly=0.004)
    df = inflation.deflate(_prices(), cpi)
    d = inflation.detector_with_and_without_inflation(df)
    assert d["days"] > 500
    assert d["days_that_differ"] <= 0.01 * d["days"]
    if d["days_that_differ"]:
        assert d["max_distance_from_threshold"] < 0.2


# --- cross-commodity report ------------------------------------------------

def test_clean_quarters_need_full_history_and_no_flags():
    from src.modeling.anomaly_detector import compute_anomalies
    frame = compute_anomalies(_prices(days=600, seed=3))
    quarters = mcr.clean_quarters(frame)
    flagged = pd.PeriodIndex(pd.to_datetime(frame.loc[frame["anomaly_flag"], "date"]), freq="Q")
    for q in quarters:
        assert pd.Period(q["quarter"], "Q") not in set(flagged)
        assert q["trading_days"] >= 55
    assert all(q["quarter"] > "2020Q1" for q in quarters)   # the first quarter has no history yet


def test_shared_shocks_finds_a_day_two_markets_jumped_together():
    from src.modeling.anomaly_detector import compute_anomalies
    a, b = _prices(seed=4), _prices(seed=5)
    for df in (a, b):
        df.loc[400:, "price"] *= 1.12             # the same 12% jump on the same day
    frames = {"coffee": compute_anomalies(a), "sugar": compute_anomalies(b)}
    shared = mcr.shared_shocks(frames)
    assert any(d["date"] == a.at[400, "date"] for d in shared["multi_days"])
    assert shared["pairs"]["coffee+sugar"]["both"] >= 1
