"""The invented-move test must choose days whose news can be fetched.

A quiet day is only tested once EVERY one of its news requests has been
answered. The news search holds nothing before NEWS_SEARCH_STARTS, so a day
chosen before it waits forever, is dropped, and takes its slot with it. Three
runs of crude oil reported "12 quiet day(s) still waiting for news" and scored
nothing for exactly this reason: four of its twelve days were 2013-2016.

Coffee's prices begin in 2018, so coffee never met the floor and its measured
false-explanation rate is unaffected by the fix. That is asserted here too,
because if the fix HAD moved coffee's days it would have invalidated the one
figure the project reports against its answer key.
"""
import pandas as pd
import pytest

from src.config.commodities import COMMODITIES
from src.evaluation import robustness as rb
from src.evaluation.robustness import NEWS_SEARCH_STARTS


def _quiet_frame(start: str, days: int) -> pd.DataFrame:
    """Calm prices: nothing flagged, so every day is a candidate and the
    choice is decided by the window alone."""
    idx = pd.bdate_range(start, periods=days)
    return pd.DataFrame({
        "date": [d.strftime("%Y-%m-%d") for d in idx],
        "price": 100.0,
        "z_score": 0.1,
        "cumulative_z_score": 0.1,
        "anomaly_flag": False,
        "anomaly_type": None,
    })


def test_no_quiet_day_is_chosen_from_before_the_news_search_begins():
    df = _quiet_frame("2010-01-04", 4200)
    chosen = rb.select_placebo_dates(df, 12, seed=7)
    assert chosen, "a calm series should yield candidates"
    assert len(chosen) == 12
    assert min(chosen) >= NEWS_SEARCH_STARTS, (
        f"chose {min(chosen)}, before the news search starts: that day can never "
        f"have its news fetched, so it is dropped and its slot is wasted")


def test_a_series_entirely_before_the_news_search_yields_nothing_rather_than_dates():
    """Better an empty list, which reads as 'not run', than twelve dates that
    will each wait forever while the report says the test ran."""
    df = _quiet_frame("2010-01-04", 1200)        # ends in 2014
    assert rb.select_placebo_dates(df, 12, seed=7) == []


def test_the_floor_matches_the_one_the_documented_dates_use():
    """Two copies of this date would let the two halves of the evaluation
    disagree about which years are reachable. They are separate constants in
    this tree; the merged tree has one shared definition instead."""
    from scripts import run_commodity_eval as rce
    assert rce.NEWS_SEARCH_STARTS == NEWS_SEARCH_STARTS


@pytest.mark.parametrize("key", sorted(COMMODITIES))
def test_every_commodity_can_actually_complete_the_invented_move_test(key):
    """The one figure comparable with coffee's. If any chosen day is outside
    the fetchable window, that commodity's column can never be filled in."""
    rb.use_commodity(key)
    try:
        df = rb.load_detections()
    except FileNotFoundError:
        pytest.skip(f"no detections file for {key}; run the detector first")
    chosen = rb.select_placebo_dates(df, 12, seed=7)
    if not chosen:
        pytest.skip(f"{key} has no quiet day inside the news window")
    assert min(chosen) >= NEWS_SEARCH_STARTS


def test_coffees_days_are_the_ones_its_published_rate_was_measured_on():
    """Coffee's detections start in 2018, so the floor cannot bind. Were this
    to fail, the reported 2-of-12 invented-move rate would be describing a
    different set of days than the code now picks."""
    rb.use_commodity("coffee")
    try:
        df = rb.load_detections()
    except FileNotFoundError:
        pytest.skip("no coffee detections file")
    assert df["date"].min() >= NEWS_SEARCH_STARTS
    chosen = rb.select_placebo_dates(df, 12, seed=7)
    assert len(chosen) == 12
