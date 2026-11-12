# Cocoa (ICE New York) — Anomaly Detector Validation

Rolling window: 75 days. Z-score threshold: 2.0 (chosen before this validation, not tuned against it). Two independent checks, either one can flag a day: a daily shock check (day-over-day return z-score) and a 10-trading-day cumulative-return check (catches slower, multi-day build-ups a single-day check can miss - see anomaly_detector.py's module docstring for why this was added).

**Result: 2/2 known real events had at least one day flagged. Control period false positives: 1.**

## Events

- **2024 April record high and crash** (2024-04-15 to 2024-05-03) — DETECTED, 8/15 days flagged (type: shock, shock, shock, trend, shock+trend, shock+trend, shock+trend, trend). Source: New York futures set an all-time high on 19 Apr 2024 (ICCO Cocoa Market Report for April 2024, US$11,878/t) and then fell ~15% on 29 Apr 2024, the largest one-day drop in data back to 1960 (Bloomberg, 29 Apr 2024)
- **2024 December record high** (2024-12-09 to 2024-12-20) — DETECTED, 3/10 days flagged (type: trend, trend, trend). Source: Dry Harmattan weather in West Africa; New York futures hit a record $12,931/t on 18 Dec 2024 (Reuters, 'Cocoa and coffee futures post strong gains in 2024', Dec 2024)

## Control period

- **Control period (2019-01-01 to 2019-03-31): No fully quiet quarter exists for cocoa: every quarter from 2015 on has at least one flagged day (scripts/multi_commodity_report.py). This is one of five quarters with the fewest, 1 of 61 days, and the same quarter as coffee's control. Reported as 1 false flag, not as clean.** — 1/61 days flagged (FALSE POSITIVES FOUND).

This control period is a candidate verified by this run's own numbers above, not assumed correct in advance - see src/config/commodities.py's note on this commodity's control_period for whether it was pre-verified or is still a first-pass candidate.