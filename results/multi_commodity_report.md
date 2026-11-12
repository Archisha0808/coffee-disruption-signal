# Detector across commodities

Produced by `python -m scripts.multi_commodity_report` (offline, reads the price files). The detector is unchanged: 75-day window, 10-day cumulative check. All labelled dates were drawn at z >= 2.0, so 2.5 and 3.0 are reported as sensitivity, not adopted.

## 1. Threshold sensitivity

| Commodity | History | Excess kurtosis | Days beyond 3 sd (normal: 0.27%) | Flagged at 2.0 | Flagged at 2.5 | Flagged at 3.0 | Events at 2.0 | Events at 2.5 | Events at 3.0 |
|---|---|---|---|---|---|---|---|---|---|
| Coffee (Arabica) | 2018-01-02 to 2026-10-23 | 1.77 | 1.21% | 279 (13.0%) | 133 (6.2%) | 56 (2.6%) | 4/4 | 3/4 | 3/4 |
| Crude Oil (WTI) | 2013-01-02 to 2026-09-11 | 38.4 | 1.72% | 425 (12.6%) | 199 (5.9%) | 101 (3.0%) | 5/5 | 4/5 | 4/5 |
| Wheat (Chicago SRW) | 2009-01-02 to 2026-09-11 | 4.71 | 1.12% | 519 (11.9%) | 228 (5.2%) | 95 (2.2%) | 4/4 | 4/4 | 4/4 |
| Cocoa (ICE New York) | 2015-01-02 to 2026-11-12 | 7.61 | 1.38% | 361 (12.4%) | 157 (5.4%) | 65 (2.2%) | 2/2 | 2/2 | 1/2 |
| Sugar (Raw, No. 11) | 2015-01-02 to 2026-11-12 | 1.94 | 1.03% | 377 (13.0%) | 172 (5.9%) | 76 (2.6%) | 1/2 | 1/2 | 1/2 |

Events missed: Coffee (Arabica) at 2.5: 2024 Brazil drought+Typhoon Yagi; Coffee (Arabica) at 3.0: 2024 Brazil drought+Typhoon Yagi; Crude Oil (WTI) at 2.5: 2024 Red Sea shipping attacks; Crude Oil (WTI) at 3.0: 2024 Red Sea shipping attacks; Cocoa (ICE New York) at 3.0: 2024 December record high; Sugar (Raw, No. 11) at 2.0: 2023 India export curbs, 12-year high; Sugar (Raw, No. 11) at 2.5: 2023 India export curbs, 12-year high; Sugar (Raw, No. 11) at 3.0: 2023 India export curbs, 12-year high

An event counts as detected if any day in its window is flagged. With 2 to 5 events per commodity this is a smoke test, not a recall estimate.

No contract-switch list yet for: Crude Oil (WTI), Wheat (Chicago SRW), Cocoa (ICE New York), Sugar (Raw, No. 11). Their counts include any roll-day jumps in the continuous front-month series.

## 2. Clean quarters (control-period candidates, z >= 2.0)

- **Coffee (Arabica)**: 2 clean quarters. Most recent: 2019Q1 (61 days), 2020Q2 (63 days). Configured control period: 2019-01-01 to 2019-03-31 (0/61 days flagged).
- **Crude Oil (WTI)**: 2 clean quarters. Most recent: 2023Q3 (63 days), 2025Q3 (65 days). Configured control period: 2023-07-01 to 2023-09-30 (0/63 days flagged).
- **Wheat (Chicago SRW)**: 1 clean quarters. Most recent: 2022Q2 (62 days). Configured control period: 2022-04-01 to 2022-06-30 (0/62 days flagged).
- **Cocoa (ICE New York)**: 0 clean quarters. Most recent: none. Configured control period: 2019-01-01 to 2019-03-31 (1/61 days flagged).
- **Sugar (Raw, No. 11)**: 1 clean quarters. Most recent: 2025Q2 (62 days). Configured control period: 2025-04-01 to 2025-06-30 (0/62 days flagged).

## 3. Shared shocks

2185 days on which every commodity above traded. Days with a daily shock flag in two or more at once: 81.

Days with three or more:

| Date | Commodities (z) |
|---|---|
| 2020-03-16 | Crude Oil (WTI) (-2.3), Wheat (Chicago SRW) (-2.6), Cocoa (ICE New York) (-2.1), Sugar (Raw, No. 11) (-3.1) |
| 2021-07-19 | Coffee (Arabica) (-2.1), Crude Oil (WTI) (-4.5), Cocoa (ICE New York) (-2.3), Sugar (Raw, No. 11) (-2.1) |
| 2021-11-26 | Crude Oil (WTI) (-7.6), Cocoa (ICE New York) (-3.1), Sugar (Raw, No. 11) (-2.1) |
| 2021-11-30 | Crude Oil (WTI) (-2.3), Wheat (Chicago SRW) (-2.8), Sugar (Raw, No. 11) (-2.1) |
| 2024-04-22 | Coffee (Arabica) (-2.2), Wheat (Chicago SRW) (+2.2), Cocoa (ICE New York) (-2.2) |
| 2025-04-04 | Coffee (Arabica) (-2.5), Crude Oil (WTI) (-4.4), Cocoa (ICE New York) (-2.0) |
| 2026-03-02 | Crude Oil (WTI) (+3.2), Wheat (Chicago SRW) (-2.3), Sugar (Raw, No. 11) (-2.0) |
| 2026-03-06 | Crude Oil (WTI) (+5.3), Wheat (Chicago SRW) (+3.5), Sugar (Raw, No. 11) (+2.0) |

| Pair | Shock days in both | In either | Share |
|---|---|---|---|
| Coffee (Arabica) + Crude Oil (WTI) | 8 | 266 | 3.0% |
| Coffee (Arabica) + Wheat (Chicago SRW) | 7 | 254 | 2.8% |
| Coffee (Arabica) + Cocoa (ICE New York) | 12 | 237 | 5.1% |
| Coffee (Arabica) + Sugar (Raw, No. 11) | 8 | 249 | 3.2% |
| Crude Oil (WTI) + Wheat (Chicago SRW) | 13 | 262 | 5.0% |
| Crude Oil (WTI) + Cocoa (ICE New York) | 12 | 251 | 4.8% |
| Crude Oil (WTI) + Sugar (Raw, No. 11) | 13 | 258 | 5.0% |
| Wheat (Chicago SRW) + Cocoa (ICE New York) | 10 | 240 | 4.2% |
| Wheat (Chicago SRW) + Sugar (Raw, No. 11) | 12 | 246 | 4.9% |
| Cocoa (ICE New York) + Sugar (Raw, No. 11) | 8 | 238 | 3.4% |

Correlation of daily returns:

| | Coffee (Arabica) | Crude Oil (WTI) | Wheat (Chicago SRW) | Cocoa (ICE New York) | Sugar (Raw, No. 11) |
|---|---|---|---|---|---|
| Coffee (Arabica) | 1.00 | 0.09 | 0.08 | 0.14 | 0.17 |
| Crude Oil (WTI) | 0.09 | 1.00 | 0.13 | 0.04 | 0.23 |
| Wheat (Chicago SRW) | 0.08 | 0.13 | 1.00 | 0.01 | 0.14 |
| Cocoa (ICE New York) | 0.14 | 0.04 | 0.01 | 1.00 | 0.08 |
| Sugar (Raw, No. 11) | 0.17 | 0.23 | 0.14 | 0.08 | 1.00 |
