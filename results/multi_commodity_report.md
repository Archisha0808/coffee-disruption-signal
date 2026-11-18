# Detector across commodities

Produced by `python -m scripts.multi_commodity_report` (offline, reads the price files). The detector is unchanged: 75-day window, 10-day cumulative check. All labelled dates were drawn at z >= 2.0, so 2.5 and 3.0 are reported as sensitivity, not adopted.

## 1. Threshold sensitivity

| Commodity | History | Excess kurtosis | Days beyond 3 sd (normal: 0.27%) | Flagged at 2.0 | Flagged at 2.5 | Flagged at 3.0 | Events at 2.0 | Events at 2.5 | Events at 3.0 |
|---|---|---|---|---|---|---|---|---|---|
| Coffee (Arabica) | 2018-01-02 to 2026-11-10 | 1.77 | 1.21% | 279 (13.0%) | 133 (6.2%) | 56 (2.6%) | 4/4 | 3/4 | 3/4 |
| Crude Oil (WTI) | 2013-01-02 to 2026-09-11 | 38.4 | 1.72% | 425 (12.6%) | 199 (5.9%) | 101 (3.0%) | 5/5 | 4/5 | 4/5 |
| Wheat (Chicago SRW) | 2009-01-02 to 2026-09-11 | 4.71 | 1.12% | 519 (11.9%) | 228 (5.2%) | 95 (2.2%) | 4/4 | 4/4 | 4/4 |
| Cocoa (ICE New York) | 2015-01-02 to 2026-11-12 | 7.61 | 1.38% | 361 (12.4%) | 157 (5.4%) | 65 (2.2%) | 2/2 | 2/2 | 1/2 |
| Sugar (Raw, No. 11) | 2015-01-02 to 2026-11-12 | 1.94 | 1.03% | 377 (13.0%) | 172 (5.9%) | 76 (2.6%) | 1/2 | 1/2 | 1/2 |
| Gold (COMEX) | 2012-01-03 to 2026-11-09 | 7.27 | 1.48% | 491 (13.4%) | 227 (6.2%) | 96 (2.6%) | 6/6 | 6/6 | 6/6 |
| Silver (COMEX) | 2010-01-04 to 2026-11-09 | 15.51 | 1.92% | 515 (12.4%) | 249 (6.0%) | 111 (2.7%) | 6/6 | 6/6 | 6/6 |

Events missed: Coffee (Arabica) at 2.5: 2024 Brazil drought+Typhoon Yagi; Coffee (Arabica) at 3.0: 2024 Brazil drought+Typhoon Yagi; Crude Oil (WTI) at 2.5: 2024 Red Sea shipping attacks; Crude Oil (WTI) at 3.0: 2024 Red Sea shipping attacks; Cocoa (ICE New York) at 3.0: 2024 December record high; Sugar (Raw, No. 11) at 2.0: 2023 India export curbs, 12-year high; Sugar (Raw, No. 11) at 2.5: 2023 India export curbs, 12-year high; Sugar (Raw, No. 11) at 3.0: 2023 India export curbs, 12-year high

An event counts as detected if any day in its window is flagged. With 2 to 5 events per commodity this is a smoke test, not a recall estimate.

No contract-switch list yet for: Crude Oil (WTI), Wheat (Chicago SRW), Cocoa (ICE New York), Sugar (Raw, No. 11), Gold (COMEX), Silver (COMEX). Their counts include any roll-day jumps in the continuous front-month series.

## 2. Clean quarters (control-period candidates, z >= 2.0)

- **Coffee (Arabica)**: 2 clean quarters. Most recent: 2019Q1 (61 days), 2020Q2 (63 days). Configured control period: 2019-01-01 to 2019-03-31 (0/61 days flagged).
- **Crude Oil (WTI)**: 2 clean quarters. Most recent: 2023Q3 (63 days), 2025Q3 (65 days). Configured control period: 2023-07-01 to 2023-09-30 (0/63 days flagged).
- **Wheat (Chicago SRW)**: 1 clean quarters. Most recent: 2022Q2 (62 days). Configured control period: 2022-04-01 to 2022-06-30 (0/62 days flagged).
- **Cocoa (ICE New York)**: 0 clean quarters. Most recent: none. Configured control period: 2019-01-01 to 2019-03-31 (1/61 days flagged).
- **Sugar (Raw, No. 11)**: 1 clean quarters. Most recent: 2025Q2 (62 days). Configured control period: 2025-04-01 to 2025-06-30 (0/62 days flagged).
- **Gold (COMEX)**: 1 clean quarters. Most recent: 2026Q2 (62 days). Configured control period: 2026-04-01 to 2026-06-30 (0/62 days flagged).
- **Silver (COMEX)**: 1 clean quarters. Most recent: 2026Q2 (62 days). Configured control period: 2026-04-01 to 2026-06-30 (0/62 days flagged).

## 3. Shared shocks

2184 days on which every commodity above traded. Days with a daily shock flag in two or more at once: 186.

Days with three or more:

| Date | Commodities (z) |
|---|---|
| 2018-01-24 | Wheat (Chicago SRW) (+2.2), Gold (COMEX) (+2.4), Silver (COMEX) (+3.2) |
| 2018-10-02 | Coffee (Arabica) (+3.1), Cocoa (ICE New York) (+2.4), Gold (COMEX) (+2.4) |
| 2018-11-01 | Coffee (Arabica) (+2.2), Gold (COMEX) (+3.0), Silver (COMEX) (+3.5) |
| 2019-01-25 | Sugar (Raw, No. 11) (-2.6), Gold (COMEX) (+2.0), Silver (COMEX) (+2.5) |
| 2019-04-11 | Coffee (Arabica) (-2.5), Gold (COMEX) (-2.7), Silver (COMEX) (-2.7) |
| 2019-06-20 | Coffee (Arabica) (+2.5), Crude Oil (WTI) (+3.1), Gold (COMEX) (+5.9), Silver (COMEX) (+3.8) |
| 2019-08-07 | Sugar (Raw, No. 11) (-2.1), Gold (COMEX) (+2.9), Silver (COMEX) (+4.3) |
| 2019-09-30 | Sugar (Raw, No. 11) (+2.4), Gold (COMEX) (-2.6), Silver (COMEX) (-2.4) |
| 2020-02-24 | Crude Oil (WTI) (-2.2), Wheat (Chicago SRW) (-2.2), Gold (COMEX) (+2.4) |
| 2020-02-28 | Crude Oil (WTI) (-2.7), Gold (COMEX) (-7.5), Silver (COMEX) (-6.1) |
| 2020-03-02 | Crude Oil (WTI) (+2.6), Sugar (Raw, No. 11) (-3.5), Gold (COMEX) (+2.0) |
| 2020-03-12 | Cocoa (ICE New York) (-3.0), Sugar (Raw, No. 11) (-3.4), Gold (COMEX) (-3.5), Silver (COMEX) (-3.0) |
| 2020-03-13 | Cocoa (ICE New York) (-3.5), Gold (COMEX) (-4.6), Silver (COMEX) (-5.8) |
| 2020-03-16 | Crude Oil (WTI) (-2.3), Wheat (Chicago SRW) (-2.6), Cocoa (ICE New York) (-2.1), Sugar (Raw, No. 11) (-3.1), Silver (COMEX) (-5.9) |
| 2020-03-18 | Crude Oil (WTI) (-5.9), Gold (COMEX) (-2.6), Silver (COMEX) (-2.4) |
| 2020-03-23 | Wheat (Chicago SRW) (+3.1), Gold (COMEX) (+4.4), Silver (COMEX) (+3.0) |
| 2020-09-21 | Wheat (Chicago SRW) (-2.1), Gold (COMEX) (-2.5), Silver (COMEX) (-3.5) |
| 2020-11-09 | Crude Oil (WTI) (+3.5), Gold (COMEX) (-4.1), Silver (COMEX) (-2.3) |
| 2021-07-19 | Coffee (Arabica) (-2.1), Crude Oil (WTI) (-4.5), Cocoa (ICE New York) (-2.3), Sugar (Raw, No. 11) (-2.1) |
| 2021-11-26 | Crude Oil (WTI) (-7.6), Cocoa (ICE New York) (-3.1), Sugar (Raw, No. 11) (-2.1) |
| 2021-11-30 | Crude Oil (WTI) (-2.3), Wheat (Chicago SRW) (-2.8), Sugar (Raw, No. 11) (-2.1) |
| 2022-03-01 | Crude Oil (WTI) (+3.0), Wheat (Chicago SRW) (+3.0), Gold (COMEX) (+2.6), Silver (COMEX) (+2.9) |
| 2022-03-08 | Wheat (Chicago SRW) (-3.0), Gold (COMEX) (+2.5), Silver (COMEX) (+2.6) |
| 2022-03-09 | Crude Oil (WTI) (-4.3), Gold (COMEX) (-3.0), Silver (COMEX) (-2.4) |
| 2022-10-03 | Sugar (Raw, No. 11) (-3.8), Gold (COMEX) (+2.3), Silver (COMEX) (+4.3) |
| 2023-03-13 | Cocoa (ICE New York) (-2.0), Gold (COMEX) (+2.7), Silver (COMEX) (+3.9) |
| 2023-06-08 | Coffee (Arabica) (+2.6), Sugar (Raw, No. 11) (+2.0), Silver (COMEX) (+2.0) |
| 2023-10-13 | Coffee (Arabica) (+2.3), Crude Oil (WTI) (+3.2), Gold (COMEX) (+5.4), Silver (COMEX) (+2.8) |
| 2023-12-04 | Cocoa (ICE New York) (-2.1), Gold (COMEX) (-3.0), Silver (COMEX) (-2.5) |
| 2023-12-14 | Cocoa (ICE New York) (-2.0), Gold (COMEX) (+2.8), Silver (COMEX) (+4.1) |
| 2024-04-22 | Coffee (Arabica) (-2.2), Wheat (Chicago SRW) (+2.2), Cocoa (ICE New York) (-2.2), Gold (COMEX) (-4.0), Silver (COMEX) (-4.1) |
| 2024-04-30 | Coffee (Arabica) (-2.9), Gold (COMEX) (-3.1), Silver (COMEX) (-2.6) |
| 2025-04-04 | Coffee (Arabica) (-2.5), Crude Oil (WTI) (-4.4), Cocoa (ICE New York) (-2.0), Gold (COMEX) (-3.4), Silver (COMEX) (-4.8) |
| 2025-04-09 | Crude Oil (WTI) (+2.6), Cocoa (ICE New York) (+2.3), Gold (COMEX) (+2.9) |
| 2025-10-13 | Sugar (Raw, No. 11) (-2.2), Gold (COMEX) (+3.1), Silver (COMEX) (+4.1) |
| 2025-10-21 | Sugar (Raw, No. 11) (-2.3), Gold (COMEX) (-5.4), Silver (COMEX) (-4.0) |
| 2025-10-27 | Wheat (Chicago SRW) (+2.2), Sugar (Raw, No. 11) (-2.5), Gold (COMEX) (-2.3) |
| 2026-03-02 | Crude Oil (WTI) (+3.2), Wheat (Chicago SRW) (-2.3), Sugar (Raw, No. 11) (-2.0) |
| 2026-03-06 | Crude Oil (WTI) (+5.3), Wheat (Chicago SRW) (+3.5), Sugar (Raw, No. 11) (+2.0) |

| Pair | Shock days in both | In either | Share |
|---|---|---|---|
| Coffee (Arabica) + Crude Oil (WTI) | 8 | 266 | 3.0% |
| Coffee (Arabica) + Wheat (Chicago SRW) | 7 | 254 | 2.8% |
| Coffee (Arabica) + Cocoa (ICE New York) | 12 | 237 | 5.1% |
| Coffee (Arabica) + Sugar (Raw, No. 11) | 8 | 249 | 3.2% |
| Coffee (Arabica) + Gold (COMEX) | 14 | 263 | 5.3% |
| Coffee (Arabica) + Silver (COMEX) | 18 | 253 | 7.1% |
| Crude Oil (WTI) + Wheat (Chicago SRW) | 13 | 262 | 5.0% |
| Crude Oil (WTI) + Cocoa (ICE New York) | 12 | 251 | 4.8% |
| Crude Oil (WTI) + Sugar (Raw, No. 11) | 13 | 258 | 5.0% |
| Crude Oil (WTI) + Gold (COMEX) | 15 | 276 | 5.4% |
| Crude Oil (WTI) + Silver (COMEX) | 14 | 271 | 5.2% |
| Wheat (Chicago SRW) + Cocoa (ICE New York) | 10 | 240 | 4.2% |
| Wheat (Chicago SRW) + Sugar (Raw, No. 11) | 12 | 246 | 4.9% |
| Wheat (Chicago SRW) + Gold (COMEX) | 12 | 266 | 4.5% |
| Wheat (Chicago SRW) + Silver (COMEX) | 11 | 261 | 4.2% |
| Cocoa (ICE New York) + Sugar (Raw, No. 11) | 8 | 238 | 3.4% |
| Cocoa (ICE New York) + Gold (COMEX) | 13 | 253 | 5.1% |
| Cocoa (ICE New York) + Silver (COMEX) | 9 | 251 | 3.6% |
| Sugar (Raw, No. 11) + Gold (COMEX) | 15 | 259 | 5.8% |
| Sugar (Raw, No. 11) + Silver (COMEX) | 13 | 255 | 5.1% |
| Gold (COMEX) + Silver (COMEX) | 63 | 225 | 28.0% |

Correlation of daily returns:

| | Coffee (Arabica) | Crude Oil (WTI) | Wheat (Chicago SRW) | Cocoa (ICE New York) | Sugar (Raw, No. 11) | Gold (COMEX) | Silver (COMEX) |
|---|---|---|---|---|---|---|---|
| Coffee (Arabica) | 1.00 | 0.09 | 0.08 | 0.14 | 0.17 | 0.10 | 0.13 |
| Crude Oil (WTI) | 0.09 | 1.00 | 0.13 | 0.04 | 0.23 | 0.07 | 0.11 |
| Wheat (Chicago SRW) | 0.08 | 0.13 | 1.00 | 0.01 | 0.14 | 0.07 | 0.07 |
| Cocoa (ICE New York) | 0.14 | 0.04 | 0.01 | 1.00 | 0.08 | 0.04 | 0.06 |
| Sugar (Raw, No. 11) | 0.17 | 0.23 | 0.14 | 0.08 | 1.00 | 0.08 | 0.10 |
| Gold (COMEX) | 0.10 | 0.07 | 0.07 | 0.04 | 0.08 | 1.00 | 0.77 |
| Silver (COMEX) | 0.13 | 0.11 | 0.07 | 0.06 | 0.10 | 0.77 | 1.00 |
