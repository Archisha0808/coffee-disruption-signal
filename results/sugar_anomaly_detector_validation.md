# Sugar (Raw, No. 11) — Anomaly Detector Validation

Rolling window: 75 days. Z-score threshold: 2.0 (chosen before this validation, not tuned against it). Two independent checks, either one can flag a day: a daily shock check (day-over-day return z-score) and a 10-trading-day cumulative-return check (catches slower, multi-day build-ups a single-day check can miss - see anomaly_detector.py's module docstring for why this was added).

**Result: 1/2 known real events had at least one day flagged. Control period false positives: 0.**

## Events

- **2020 COVID and oil-price collapse** (2020-03-06 to 2020-03-31) — DETECTED, 10/18 days flagged (type: shock+trend, shock+trend, trend, trend, shock+trend, trend, shock+trend, trend, trend, trend). Source: Oil's collapse made Brazilian mills switch cane from ethanol to sugar; raw sugar fell from a one-year peak on 20 Feb to near 10 c/lb by 31 Mar 2020, a 12-year low (Argus, 'Brazil cane harvest kicks off with whimper', 1 Apr 2020; S&P Global Platts, 16 Mar 2020)
- **2023 India export curbs, 12-year high** (2023-10-16 to 2023-11-10) — MISSED, 0/20 days flagged (type: -). Source: India extended its sugar export curbs indefinitely on 18 Oct 2023 after a weak monsoon; raw sugar hit a 12-year high near 28 c/lb, again on 7 Nov 2023 (Nikkei via datamarnews.com, 31 Oct 2023; Barchart, Nov 2023)

## Control period

- **Control period (2025-04-01 to 2025-06-30): Verified quiet in real data - 0/62 days flagged; the only fully clean quarter for sugar (scripts/multi_commodity_report.py).** — 0/62 days flagged (clean).

This control period is a candidate verified by this run's own numbers above, not assumed correct in advance - see src/config/commodities.py's note on this commodity's control_period for whether it was pre-verified or is still a first-pass candidate.