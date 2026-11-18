# Threshold Sensitivity: what every other z-score would have caught

Produced by `python -m scripts.threshold_sweep`. Re-scored from the stored detections, so the rows at the production threshold reconcile with `detector_evaluation.md` by construction. See this script's docstring for what each column means and what it cannot measure.

Production threshold: **2.0**, fixed before any validation and unchanged since.

## Across every cited event

| Threshold | Events detected | Recall | Control false positives |
|---|---|---|---|
| 1.5 | 25/25 | 100% | 26 |
| 1.75 | 25/25 | 100% | 12 |
| **2** | 25/25 | 100% | 0 |
| 2.25 | 24/25 | 96% | 0 |
| 2.5 | 23/25 | 92% | 0 |
| 2.75 | 23/25 | 92% | 0 |
| 3 | 23/25 | 92% | 0 |
| 3.5 | 21/25 | 84% | 0 |
| 4 | 18/25 | 72% | 0 |

Recall cannot choose between the loosest thresholds: it is flat where the detectors differ most. The control periods can, and they were chosen independently of the threshold.

## Coffee (Arabica) (`coffee`)

4 cited event(s) inside this series' history, 2128 scorable days, control period 2019-01-01 to 2019-03-31.

| T | Flagged | Rate | Daily only | Detected | Chance | Control FP | Density | Lift |
|---|---|---|---|---|---|---|---|---|
| 1.5 | 586 | 27.5% | 13.8% | 4/4 | 3.7 | 2 | 37.4% | 1.4x |
| 1.75 | 395 | 18.6% | 9.2% | 4/4 | 3.4 | 1 | 26.7% | 1.4x |
| **2** | 279 | 13.1% | 6.1% | 4/4 | 3.0 | 0 | 21.4% | 1.6x |
| 2.25 | 189 | 8.9% | 3.9% | 4/4 | 2.7 | 0 | 18.3% | 2.1x |
| 2.5 | 133 | 6.2% | 2.5% | 3/4 | 2.2 | 0 | 14.5% | 2.3x |
| 2.75 | 85 | 4.0% | 1.6% | 3/4 | 1.6 | 0 | 13.7% | 3.4x |
| 3 | 56 | 2.6% | 1.2% | 3/4 | 1.4 | 0 | 11.5% | 4.4x |
| 3.5 | 21 | 1.0% | 0.5% | 3/4 | 0.7 | 0 | 4.6% | 4.6x |
| 4 | 14 | 0.7% | 0.4% | 2/4 | 0.6 | 0 | 2.3% | 3.5x |

| Event | Window | Survives to | Peak \|z\| |
|---|---|---|---|
| 2021 Brazil drought+frost | 53d | 4 | 4.81 |
| 2024 Brazil drought+Typhoon Yagi | 43d | 2.25 | 2.26 |
| 2025 sharp spike+reversal | 25d | 3.5 | 3.50 |
| 2026 frost concerns (16%+ single-day surge) | 10d | 4 | 6.81 |

## Crude Oil (WTI) (`crude_oil`)

5 cited event(s) inside this series' history, 3368 scorable days, control period 2023-07-01 to 2023-09-30.

| T | Flagged | Rate | Daily only | Detected | Chance | Control FP | Density | Lift |
|---|---|---|---|---|---|---|---|---|
| 1.5 | 958 | 28.4% | 13.8% | 5/5 | 3.9 | 10 | 42.5% | 1.5x |
| 1.75 | 642 | 19.1% | 9.2% | 5/5 | 3.2 | 4 | 31.5% | 1.7x |
| **2** | 420 | 12.5% | 6.1% | 5/5 | 2.5 | 0 | 28.8% | 2.3x |
| 2.25 | 286 | 8.5% | 4.3% | 4/5 | 1.9 | 0 | 24.7% | 2.9x |
| 2.5 | 198 | 5.9% | 3.1% | 4/5 | 1.6 | 0 | 23.3% | 4.0x |
| 2.75 | 131 | 3.9% | 2.1% | 4/5 | 1.2 | 0 | 17.8% | 4.6x |
| 3 | 99 | 2.9% | 1.7% | 4/5 | 0.9 | 0 | 16.4% | 5.6x |
| 3.5 | 51 | 1.5% | 1.0% | 4/5 | 0.6 | 0 | 8.2% | 5.4x |
| 4 | 33 | 1.0% | 0.7% | 4/5 | 0.4 | 0 | 6.8% | 7.0x |

| Event | Window | Survives to | Peak \|z\| |
|---|---|---|---|
| 2014 OPEC no-cut decision | 9d | 4 | 6.62 |
| 2020 Saudi-Russia price war | 6d | 4 | 10.83 |
| 2020 negative WTI price | 6d | 4 | 43.21 |
| 2022 Russia invades Ukraine | 11d | 4 | 4.34 |
| 2024 Red Sea shipping attacks | 41d | 2 | 2.15 |

## Wheat (Chicago SRW) (`wheat`)

4 cited event(s) inside this series' history, 4373 scorable days, control period 2022-04-01 to 2022-06-30.

| T | Flagged | Rate | Daily only | Detected | Chance | Control FP | Density | Lift |
|---|---|---|---|---|---|---|---|---|
| 1.5 | 1184 | 27.1% | 12.8% | 4/4 | 3.3 | 1 | 55.9% | 2.1x |
| 1.75 | 804 | 18.4% | 8.6% | 4/4 | 2.9 | 0 | 44.1% | 2.4x |
| **2** | 519 | 11.9% | 5.7% | 4/4 | 2.4 | 0 | 39.7% | 3.3x |
| 2.25 | 354 | 8.1% | 4.0% | 4/4 | 1.9 | 0 | 35.3% | 4.4x |
| 2.5 | 228 | 5.2% | 2.6% | 4/4 | 1.5 | 0 | 29.4% | 5.6x |
| 2.75 | 144 | 3.3% | 1.7% | 4/4 | 1.1 | 0 | 26.5% | 8.0x |
| 3 | 95 | 2.2% | 1.1% | 4/4 | 0.8 | 0 | 20.6% | 9.5x |
| 3.5 | 43 | 1.0% | 0.5% | 2/4 | 0.4 | 0 | 13.2% | 13.5x |
| 4 | 20 | 0.5% | 0.3% | 1/4 | 0.2 | 0 | 10.3% | 22.5x |

| Event | Window | Survives to | Peak \|z\| |
|---|---|---|---|
| 2010 Russia export ban | 10d | 3 | 3.44 |
| 2012 US drought | 37d | 3 | 3.26 |
| 2022 Russia invades Ukraine | 11d | 4 | 8.66 |
| 2023 Black Sea grain deal collapse | 10d | 3.5 | 3.61 |

## Gold (COMEX) (`gold`)

6 cited event(s) inside this series' history, 3659 scorable days, control period 2026-04-01 to 2026-06-30.

| T | Flagged | Rate | Daily only | Detected | Chance | Control FP | Density | Lift |
|---|---|---|---|---|---|---|---|---|
| 1.5 | 987 | 27.0% | 13.1% | 6/6 | 3.8 | 6 | 60.5% | 2.2x |
| 1.75 | 686 | 18.7% | 8.6% | 6/6 | 3.0 | 2 | 60.5% | 3.2x |
| **2** | 491 | 13.4% | 6.2% | 6/6 | 2.3 | 0 | 57.9% | 4.3x |
| 2.25 | 336 | 9.2% | 4.6% | 6/6 | 1.8 | 0 | 55.3% | 6.0x |
| 2.5 | 227 | 6.2% | 3.1% | 6/6 | 1.3 | 0 | 55.3% | 8.9x |
| 2.75 | 147 | 4.0% | 2.1% | 6/6 | 0.9 | 0 | 52.6% | 13.1x |
| 3 | 96 | 2.6% | 1.5% | 6/6 | 0.6 | 0 | 44.7% | 17.1x |
| 3.5 | 41 | 1.1% | 0.7% | 6/6 | 0.3 | 0 | 39.5% | 35.2x |
| 4 | 27 | 0.7% | 0.5% | 6/6 | 0.2 | 0 | 34.2% | 46.4x |

| Event | Window | Survives to | Peak \|z\| |
|---|---|---|---|
| 2013 April gold crash | 4d | 4 | 10.27 |
| 2016 Brexit referendum | 4d | 4 | 4.73 |
| 2020 pandemic dash for cash | 15d | 4 | 4.63 |
| 2020 August reversal from the record | 5d | 4 | 4.72 |
| 2025 October reversal from the record | 4d | 4 | 5.36 |
| 2026 January metals crash | 6d | 4 | 6.82 |

## Silver (COMEX) (`silver`)

6 cited event(s) inside this series' history, 4162 scorable days, control period 2026-04-01 to 2026-06-30.

| T | Flagged | Rate | Daily only | Detected | Chance | Control FP | Density | Lift |
|---|---|---|---|---|---|---|---|---|
| 1.5 | 1127 | 27.1% | 12.9% | 6/6 | 4.0 | 7 | 87.5% | 3.2x |
| 1.75 | 776 | 18.6% | 9.0% | 6/6 | 3.1 | 5 | 77.5% | 4.2x |
| **2** | 515 | 12.4% | 6.2% | 6/6 | 2.4 | 0 | 75.0% | 6.1x |
| 2.25 | 362 | 8.7% | 4.9% | 6/6 | 1.9 | 0 | 67.5% | 7.8x |
| 2.5 | 249 | 6.0% | 3.5% | 6/6 | 1.4 | 0 | 60.0% | 10.0x |
| 2.75 | 165 | 4.0% | 2.6% | 6/6 | 1.0 | 0 | 60.0% | 15.1x |
| 3 | 111 | 2.7% | 1.9% | 6/6 | 0.7 | 0 | 57.5% | 21.6x |
| 3.5 | 55 | 1.3% | 1.0% | 6/6 | 0.4 | 0 | 47.5% | 35.9x |
| 4 | 30 | 0.7% | 0.6% | 5/6 | 0.2 | 0 | 25.0% | 34.7x |

| Event | Window | Survives to | Peak \|z\| |
|---|---|---|---|
| 2011 May margin-hike collapse | 5d | 4 | 4.21 |
| 2011 September plunge | 3d | 4 | 6.15 |
| 2013 April metals crash | 4d | 4 | 7.74 |
| 2020 pandemic dash for cash | 15d | 4 | 5.94 |
| 2021 retail silver squeeze | 5d | 3.5 | 3.93 |
| 2026 January metals crash | 8d | 4 | 7.55 |

## The largest actual moves

Of each series' 20 largest one-day moves - a benchmark nobody curated - how many the detector flags.

| Commodity | Smallest | Largest | T=1.5 | T=1.75 | T=2 | T=2.25 | T=2.5 | T=2.75 | T=3 | T=3.5 | T=4 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Coffee (Arabica) | 6.7% | 15.3% | 20/20 | 20/20 | 20/20 | 20/20 | 19/20 | 19/20 | 18/20 | 8/20 | 7/20 |
| Crude Oil (WTI) | 11.4% | 37.7% | 15/20 | 15/20 | 15/20 | 15/20 | 14/20 | 14/20 | 12/20 | 12/20 | 11/20 |
| Wheat (Chicago SRW) | 7.6% | 21.8% | 19/20 | 19/20 | 19/20 | 19/20 | 19/20 | 18/20 | 16/20 | 8/20 | 7/20 |
| Gold (COMEX) | 4.3% | 10.8% | 19/20 | 19/20 | 19/20 | 19/20 | 18/20 | 18/20 | 15/20 | 13/20 | 12/20 |
| Silver (COMEX) | 8.6% | 31.3% | 20/20 | 19/20 | 19/20 | 19/20 | 19/20 | 18/20 | 17/20 | 13/20 | 8/20 |

A rolling z-score asks whether a move is unusual *for this market right now*, not whether it is large. During a sustained crisis those questions come apart: a 12% day in a window whose typical day moves 10% has a small z-score however the threshold is set, which is why lowering the threshold recovers none of crude oil's missed moves. That is the adaptive design working as intended, and its cost. A fixed-size second channel, reported beside the z-score rather than merged into it, would close the gap; it would have to sit beside the detector, as the factor model and the cross-commodity check do, because every evaluation figure in `results/` was drawn at the current rule.