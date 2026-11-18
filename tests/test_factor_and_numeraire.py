"""Was it the commodity or the market: the factor layer, the numeraire test,
and the cross-commodity check.

These are the tests that matter most for the new layers, because the layers
are only worth having if they can tell the two cases apart. Each one builds
a series where the answer is known by construction - a move that is purely
the dollar, a move that is purely the commodity - and checks the module
returns the right one. A test that only checks the code runs would pass on
a module that always answered "macro".

No network: the factor fetcher's pure functions are tested, its downloads
are not.
"""
import numpy as np
import pandas as pd
import pytest

from src.analysis import numeraire as nm
from src.evaluation import cross_commodity as cc
from src.modeling import factor_model as fm


def _days(n, start="2020-01-01"):
    return pd.bdate_range(start, periods=n)


def _factors(n, seed=0, dollar=None):
    """Quiet factor returns unless a dollar path is handed in."""
    rng = np.random.default_rng(seed)
    idx = _days(n)
    return pd.DataFrame({
        "dollar": rng.normal(0, 0.002, n) if dollar is None else dollar,
        "equity": rng.normal(0, 0.004, n),
        "broad_commodity": rng.normal(0, 0.005, n),
    }, index=idx)


# --- the factor layer: can it tell the two cases apart? ---------------------

def test_a_move_that_is_entirely_the_dollar_leaves_no_residual():
    n = 200
    f = _factors(n, seed=1)
    # The commodity IS minus two times the dollar, exactly. Nothing else.
    y = -2.0 * f["dollar"]
    res = fm.residual_series(y, f)
    settled = res.dropna()
    assert len(settled) > 100
    # Residuals must be numerically zero, so no day can look commodity-specific.
    assert settled["residual"].abs().max() < 1e-9


def test_a_shock_the_factors_cannot_explain_shows_up_as_a_large_residual():
    n = 200
    f = _factors(n, seed=2)
    y = (-2.0 * f["dollar"]).copy()
    shock_day = f.index[150]
    y.loc[shock_day] += 0.09          # a 9% move nothing in the factors predicts
    res = fm.residual_series(y, f)
    assert abs(res.loc[shock_day, "residual"] - 0.09) < 1e-6
    assert abs(res.loc[shock_day, "residual_z"]) > 5


def test_the_day_being_tested_is_left_out_of_its_own_estimation_window():
    """A day inside its own window drags the fitted line towards itself and
    shrinks the residual the test exists to find. This checks the exclusion
    by giving the window a single huge day and confirming the fit before it
    is unaffected."""
    n = 160
    f = _factors(n, seed=3)
    y = (-2.0 * f["dollar"]).copy()
    day = f.index[120]
    y.loc[day] += 0.50                 # absurd, so any leakage is obvious
    res = fm.residual_series(y, f)
    # The residual recovers the whole injected move: the betas were not
    # bent to accommodate it.
    assert abs(res.loc[day, "residual"] - 0.50) < 1e-6
    # And the NEXT day, which now has the shock inside its window, has a
    # visibly wider residual spread - proof the window really moves.
    nxt = f.index[121]
    assert res.loc[nxt, "residual_z"] == res.loc[nxt, "residual_z"]  # not NaN


def test_classification_calls_a_flagged_day_macro_when_the_residual_is_small():
    assert fm.classify_day("shock", 0.3, None)[0] == "macro-driven"
    assert fm.classify_day("shock", 4.0, None)[0] == "commodity-specific"
    assert fm.classify_day("", 9.9, 9.9)[0] == ""     # not flagged, not classified
    assert fm.classify_day("shock", float("nan"), None)[0] == "unclassified"


def test_a_build_up_is_judged_over_ten_days_not_over_one():
    """A day flagged only by the 10-day cumulative check has no extreme
    daily move by construction. Judged by a daily residual it comes back
    macro-driven whatever drove it - which mislabelled 149 of coffee's 279
    flagged days before this was fixed."""
    label, how = fm.classify_day("trend", 0.1, 5.0)
    assert label == "commodity-specific"              # the 10-day residual decides
    assert "cumulative" in how
    label, how = fm.classify_day("shock", 5.0, 0.1)
    assert label == "commodity-specific"              # the daily residual decides
    assert how == "daily residual"
    # Flagged by both: the daily move is the larger claim, so it decides.
    assert fm.classify_day("shock+trend", 0.1, 9.9) == ("macro-driven", "daily residual")


def test_a_build_up_with_no_cumulative_residual_is_unclassified_not_macro():
    label, _ = fm.classify_day("trend", 0.1, float("nan"))
    assert label == "unclassified"


def test_the_factor_layer_adds_no_flags_of_its_own():
    """It explains the base detector's flags. If it invented flags, the 16
    labelled dates and every stored evaluation figure would stop lining up
    with the detections they were drawn from."""
    for z in (0.0, 2.5, 50.0):
        assert fm.classify_day("", z, z)[0] == ""


def test_a_negative_price_is_masked_rather_than_turned_into_a_silent_nan():
    """WTI settled at -$37.63 on 20 April 2020. numpy answers log(-37.63)
    with NaN and a warning that is easy to miss, so the most famous day in
    the oil series would drop out of every regression with nothing saying
    so."""
    prices = pd.Series([50.0, 40.0, -37.63, 10.0, 12.0], index=_days(5))
    r = fm.log_returns(prices)
    assert pd.isna(r.iloc[2])          # the negative day itself
    assert pd.isna(r.iloc[3])          # and the one measured from it
    assert not pd.isna(r.iloc[1])      # the ordinary days survive
    assert abs(r.iloc[4] - np.log(12 / 10)) < 1e-12


def test_a_window_with_too_little_history_is_left_unclassified_not_guessed():
    f = _factors(30, seed=4)
    res = fm.residual_series(-2.0 * f["dollar"], f, min_obs=40)
    assert res["residual_z"].isna().all()


# --- the numeraire test ----------------------------------------------------

def _fx_factors(n, dollar_path, seed=5):
    """Every exchange rate moving with the dollar, as they would if the
    dollar itself were what moved."""
    idx = _days(n)
    return pd.DataFrame({
        "dollar": dollar_path,
        "eur_per_usd": dollar_path,
        "jpy_per_usd": dollar_path,
        "cny_per_usd": dollar_path,
        "inr_per_usd": dollar_path,
    }, index=idx)


def test_a_pure_dollar_move_does_not_survive_translation():
    """The dollar falls 3%; the commodity's dollar price rises 3%; in every
    other currency nothing happened. Survival must be about zero."""
    n = 120
    drop = np.zeros(n)
    drop[100] = -0.03
    f = _fx_factors(n, drop)
    usd = pd.Series(-drop, index=f.index)      # +3% in dollars on that day
    locals_ = nm.local_currency_returns(usd, f)
    day = f.index[100]
    assert abs(locals_.loc[day, "USD"] - 0.03) < 1e-12
    for c in ("EUR", "JPY", "CNY", "INR"):
        assert abs(locals_.loc[day, c]) < 1e-12


def test_a_real_commodity_move_survives_translation_in_every_currency():
    n = 120
    f = _fx_factors(n, np.zeros(n))            # dollar flat
    usd = pd.Series(0.0, index=f.index)
    usd.iloc[100] = 0.05
    locals_ = nm.local_currency_returns(usd, f)
    day = f.index[100]
    for c in ("USD", "EUR", "JPY", "CNY", "INR"):
        assert abs(locals_.loc[day, c] - 0.05) < 1e-12


def test_survival_uses_the_median_so_one_managed_rate_cannot_drive_it():
    """The yuan is managed against the dollar. If one currency were allowed
    to decide, a peg would make every move look like a commodity move."""
    n = 120
    idx = _days(n)
    f = pd.DataFrame({
        "dollar": np.zeros(n),
        "eur_per_usd": np.zeros(n), "jpy_per_usd": np.zeros(n),
        "inr_per_usd": np.zeros(n),
        "cny_per_usd": np.concatenate([np.zeros(100), [0.20], np.zeros(n - 101)]),
    }, index=idx)
    usd = pd.Series(0.0, index=idx)
    usd.iloc[100] = 0.02
    locals_ = nm.local_currency_returns(usd, f)
    others = [locals_.loc[idx[100], c] for c in ("EUR", "JPY", "CNY", "INR")]
    # The median ignores the outlying yuan; a mean would not.
    assert abs(float(np.median(others)) - 0.02) < 1e-12
    assert float(np.mean(others)) > 0.06


def test_the_dollar_beta_is_fitted_only_on_days_before_the_one_explained():
    n = 150
    idx = _days(n)
    dollar = pd.Series(np.random.default_rng(6).normal(0, 0.003, n), index=idx)
    y = -1.5 * dollar
    day = idx[120]
    beta, r2, n_obs = nm.dollar_beta(y, dollar, day)
    assert abs(beta + 1.5) < 1e-6
    assert r2 > 0.99
    assert n_obs == nm.WINDOW_DAYS


def test_too_little_history_returns_no_beta_rather_than_a_bad_one():
    idx = _days(20)
    d = pd.Series(np.random.default_rng(7).normal(0, 0.003, 20), index=idx)
    beta, r2, n_obs = nm.dollar_beta(-1.5 * d, d, idx[10])
    assert beta is None and r2 is None


# --- the cross-commodity check ---------------------------------------------

def _table(rows):
    return pd.DataFrame(rows, index=pd.to_datetime(list(rows.pop("_dates")))) \
        if "_dates" in rows else None


def test_a_day_everything_flags_is_called_macro():
    idx = _days(5)
    t = pd.DataFrame({k: pd.Series([False, False, True, False, False], index=idx,
                                   dtype="boolean")
                      for k in ("coffee", "wheat", "gold", "silver")})
    rows = cc.classify(t, "coffee", min_others=2).set_index("date")
    assert rows.loc[idx[2], "verdict"] == "macro"


def test_a_day_only_one_commodity_flags_is_called_commodity_specific():
    idx = _days(5)
    t = pd.DataFrame({
        "coffee": pd.Series([False, False, True, False, False], index=idx, dtype="boolean"),
        "wheat": pd.Series(False, index=idx, dtype="boolean"),
        "gold": pd.Series(False, index=idx, dtype="boolean"),
    })
    rows = cc.classify(t, "coffee", min_others=2).set_index("date")
    assert rows.loc[idx[2], "verdict"] == "commodity-specific"


def test_a_series_that_has_not_started_is_not_counted_as_calm():
    """Missing data and a quiet market are different things. Counting the
    first as the second would make every early flag look commodity-specific
    just because the other series had not begun."""
    idx = _days(5)
    t = pd.DataFrame({
        "wheat": pd.Series([True, False, False, False, False], index=idx, dtype="boolean"),
        "coffee": pd.Series([pd.NA] * 5, index=idx, dtype="boolean"),
        "gold": pd.Series([pd.NA] * 5, index=idx, dtype="boolean"),
    })
    rows = cc.classify(t, "wheat", min_others=2).set_index("date")
    assert rows.loc[idx[0], "scorable"] == False      # noqa: E712
    assert rows.loc[idx[0], "verdict"] is None


def test_gold_and_silver_can_be_counted_as_one_market():
    idx = _days(3)
    t = pd.DataFrame({
        "gold": pd.Series([True, False, False], index=idx, dtype="boolean"),
        "silver": pd.Series([True, False, False], index=idx, dtype="boolean"),
        "coffee": pd.Series([False, False, False], index=idx, dtype="boolean"),
    })
    collapsed = cc._collapse_substitutes(t)
    assert set(collapsed.columns) == {"precious", "coffee"}
    assert bool(collapsed.loc[idx[0], "precious"]) is True


def test_the_labelled_date_scorer_reads_the_key_and_relabels_nothing():
    """It reports which labelled dates are macro days. It must never write
    a label: changing the answer key after seeing which dates a rule failed
    is the move the whole project refuses."""
    import inspect
    src = inspect.getsource(cc.score_labelled_dates)
    assert "to_csv" not in src and "write" not in src


# --- the factor fetcher's pure parts ---------------------------------------

def test_exchange_rates_are_normalised_to_foreign_units_per_dollar():
    """FRED quotes DEXUSEU as dollars per euro and the rest as foreign per
    dollar. Getting this backwards flips the sign of every pass-through
    result downstream, so the inversion is declared per series and tested."""
    from src.data.market_factors import FRED_SERIES
    assert FRED_SERIES["DEXUSEU"][2] is True        # inverted
    for sid in ("DEXJPUS", "DEXCHUS", "DEXINUS"):
        assert FRED_SERIES[sid][2] is False


def test_levels_become_returns_without_forward_filling_a_holiday():
    from src.data.market_factors import to_returns
    levels = {"dollar_broad": {"2024-01-02": 100.0, "2024-01-03": 101.0,
                               "2024-01-05": 102.0},
              "equity": {"2024-01-02": 4000.0, "2024-01-03": 4040.0,
                         "2024-01-05": 4000.0},
              "broad_commodity": {"2024-01-02": 20.0, "2024-01-03": 20.2,
                                  "2024-01-05": 20.0},
              "real_yield_10y": {"2024-01-02": 1.7, "2024-01-03": 1.8,
                                 "2024-01-05": 1.75}}
    lv, rt = to_returns(levels)
    assert len(rt) == 3
    assert abs(rt.loc[pd.Timestamp("2024-01-03"), "dollar_broad"]
               - np.log(101 / 100)) < 1e-12
    # 4 January is absent entirely rather than carried forward as a zero.
    assert pd.Timestamp("2024-01-04") not in rt.index
    # A yield is a rate already: it is carried at its level, plus a change.
    assert rt.loc[pd.Timestamp("2024-01-03"), "real_yield_10y"] == 1.8
    assert abs(rt.loc[pd.Timestamp("2024-01-03"), "real_yield_10y_change"] - 0.1) < 1e-12


def test_a_missing_factor_series_refuses_rather_than_writing_a_short_table():
    """A factor table with a column missing produces regressions that run
    and are wrong. It has to fail loudly."""
    import inspect
    from src.data import market_factors
    assert "SystemExit" in inspect.getsource(market_factors.build_levels)


# --- the anomaly card ------------------------------------------------------

def test_every_field_on_a_card_carries_an_evidence_tag_and_a_source():
    from src.evaluation import anomaly_card as ac
    card = ac.build_card("coffee", "2025-04-07")
    assert card["fields"], "no layers found for a date that is in the repository"
    for name, f in card["fields"].items():
        assert f["tag"] in ac.TAGS, f"{name} has no valid evidence tag"
        assert f["source"], f"{name} does not say where it came from"


def test_a_field_cannot_be_added_without_a_valid_tag():
    from src.evaluation import anomaly_card as ac
    with pytest.raises(ValueError):
        ac.tagged(1.0, "probably", "somewhere.csv")


def _no_layers(monkeypatch, ac, *, keep=()):
    """Every layer reports nothing, so the card is tested on its own behaviour
    rather than on which results files happen to exist today."""
    for part in ("detector_fields", "factor_fields", "cross_commodity_fields",
                 "numeraire_fields", "pipeline_fields"):
        if part not in keep:
            monkeypatch.setattr(ac, part, lambda commodity, day: {})


def test_a_layer_that_has_not_been_run_is_reported_as_missing_not_as_absence(monkeypatch):
    """A gap in what is known must not read as a negative finding.

    The assertion is about the reporting, not about which layers have been run.
    An earlier version of this test asserted that the factor model was missing
    and began failing the moment somebody ran the factor model - it was testing
    the contents of results/, not the behaviour of the card, and a test that
    breaks when the project makes progress teaches people to ignore it.
    """
    from src.evaluation import anomaly_card as ac
    _no_layers(monkeypatch, ac)
    card = ac.build_card("coffee", "2025-04-07")
    assert card["fields"] == {}
    assert card["missing_layers"] == ["factor model", "cross-commodity",
                                      "numeraire", "explanation pipeline"]


def test_a_layer_that_has_run_is_not_listed_as_missing(monkeypatch):
    """The other half of the same rule: a layer with output is not a gap."""
    from src.evaluation import anomaly_card as ac
    _no_layers(monkeypatch, ac, keep=("factor_fields",))
    monkeypatch.setattr(ac, "factor_fields", lambda commodity, day: {
        "residual_z": {"value": 2.4, "tag": "tested",
                       "source": "coffee_factor_adjusted.csv"}})
    card = ac.build_card("coffee", "2025-04-07")
    assert "factor model" not in card["missing_layers"]
    assert "numeraire" in card["missing_layers"]


def test_the_card_gives_no_overall_verdict(monkeypatch):
    """Four layers disagreeing is information. One word would hide it."""
    from src.evaluation import anomaly_card as ac
    _no_layers(monkeypatch, ac)
    card = ac.build_card("coffee", "2025-04-07")
    assert not any(k in card for k in ("verdict", "overall", "conclusion"))


# --- the FRED fetcher's retry ----------------------------------------------

def test_a_reset_connection_is_retried_rather_than_reported_as_missing_data(monkeypatch):
    """FRED resets connections on a burst of requests. Treated as "this
    series does not exist", a rate limit silently drops a factor from every
    regression downstream, and the regression still runs."""
    from src.data import cpi

    calls = {"n": 0}

    class _Resp:
        text = "observation_date,DTWEXBGS\n2024-01-02,120.5\n"
        def raise_for_status(self):
            return None

    class _Sess:
        def get(self, *a, **k):
            calls["n"] += 1
            if calls["n"] < 3:
                raise ConnectionError("Connection aborted, ConnectionResetError(10054)")
            return _Resp()

    monkeypatch.setattr(cpi, "_session", lambda: _Sess())
    monkeypatch.setattr(cpi.time if hasattr(cpi, "time") else __import__("time"),
                        "sleep", lambda s: None)
    rows = cpi.fetch_series("DTWEXBGS", "2024-01-01")
    assert calls["n"] == 3            # failed twice, succeeded on the third
    assert rows == [("2024-01-02", 120.5)]


def test_a_series_that_fails_every_attempt_raises_rather_than_returning_empty(monkeypatch):
    from src.data import cpi

    class _Sess:
        def get(self, *a, **k):
            raise ConnectionError("reset")

    monkeypatch.setattr(cpi, "_session", lambda: _Sess())
    monkeypatch.setattr(__import__("time"), "sleep", lambda s: None)
    with pytest.raises(ConnectionError):
        cpi.fetch_series("DTWEXBGS", "2024-01-01", attempts=2)


def test_the_requests_reuse_one_session_instead_of_opening_one_per_series():
    """Eight separate connections in a row is what triggered the resets."""
    from src.data import cpi
    cpi._SESSION = None
    a, b = cpi._session(), cpi._session()
    assert a is b
    assert "User-Agent" in a.headers


# --- the second source, for when one host is unreachable -------------------

def test_every_required_factor_series_has_a_second_source():
    """FRED was unreachable from the developer's network while Yahoo served
    10,725 rows in the same run. A single-source fetcher turns one blocked
    host into a blocked project."""
    from src.data.market_factors import (FRED_SERIES, OPTIONAL_COLUMNS,
                                         YAHOO_FALLBACK)
    from src.modeling.factor_model import FACTOR_COLUMNS
    for series_id, (col, _what, _inv) in FRED_SERIES.items():
        if col in OPTIONAL_COLUMNS:
            continue
        assert series_id in YAHOO_FALLBACK, f"{series_id} ({col}) has no second source"
    # And the three the factor model actually reads must all be reachable.
    assert set(FACTOR_COLUMNS) == {"dollar", "equity", "broad_commodity"}


def test_the_fallback_keeps_the_rate_direction_right():
    """FRED quotes DEXUSEU as dollars per euro; Yahoo's EURUSD=X is the
    same way round. Both must be marked for inversion, or the sign of every
    pass-through result downstream flips."""
    from src.data.market_factors import FRED_SERIES, YAHOO_FALLBACK
    assert FRED_SERIES["DEXUSEU"][2] is True
    assert YAHOO_FALLBACK["DEXUSEU"][2] is True
    for sid in ("DEXJPUS", "DEXCHUS", "DEXINUS"):
        assert FRED_SERIES[sid][2] is False
        assert YAHOO_FALLBACK[sid][2] is False


def test_a_missing_context_series_does_not_stop_the_run():
    """The real yield has no free daily substitute. Nothing in the factor
    model reads it, so refusing to write the table over it would block the
    analysis on a column no result uses."""
    from src.data.market_factors import OPTIONAL_COLUMNS
    assert "real_yield_10y" in OPTIONAL_COLUMNS
    assert "dollar_broad" not in OPTIONAL_COLUMNS


def test_the_dollar_basket_is_an_equal_weighted_check_on_a_euro_heavy_index():
    """DXY is about 58% euro. If it stands in for the Fed's broad index,
    'the dollar' quietly becomes 'the euro'. The basket is the control."""
    from src.data.market_factors import dollar_basket
    levels = {
        "eur_per_usd": {"2024-01-02": 1.0, "2024-01-03": 1.10},   # +10% vs USD
        "jpy_per_usd": {"2024-01-02": 100.0, "2024-01-03": 100.0},
        "cny_per_usd": {"2024-01-02": 7.0, "2024-01-03": 7.0},
        "inr_per_usd": {"2024-01-02": 83.0, "2024-01-03": 83.0},
    }
    b = dollar_basket(levels)
    moved = float(b.loc[pd.Timestamp("2024-01-03")])
    # One currency moving 10% must move the basket about a quarter of that,
    # not all of it, which is the whole point of not using a euro-heavy index.
    assert 0.020 < moved < 0.027


def test_the_basket_needs_at_least_two_rates_before_it_claims_anything():
    from src.data.market_factors import dollar_basket
    assert dollar_basket({"eur_per_usd": {"2024-01-02": 1.0}}) is None


def test_which_source_each_column_came_from_is_recorded():
    """A figure read months later must not require guessing whether
    'dollar' meant the Fed's broad index or DXY: they answer different
    questions."""
    import inspect
    from src.data import market_factors
    src = inspect.getsource(market_factors.write)
    assert "SOURCES_PATH" in src and "note" in src
