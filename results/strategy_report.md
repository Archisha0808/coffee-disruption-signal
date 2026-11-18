# What the measurements support doing

Produced by `python -m src.analysis.strategy`. Every statement below carries the figure it rests on. Where a measurement does not support a statement, that is said rather than filled in.

**This is not advice, and nothing here is a forecast.** Short-horizon price direction was tested and is at chance (`forecast_evaluation.md`: 50.2% against a 50.7% baseline), so no recommendation of the form "prices will fall, wait" appears here. What appears is what followed comparable days in the past, which a person can weigh against their own cost of waiting.

## 1. Timing a purchase into a shock

Trading days until half the move is given back, median and quartiles. The control is days the detector did NOT flag whose move was at least as large as the smallest flagged shock: if those behaved the same, this statistic would be about the series rather than about the flag.

| Commodity | Flagged shocks | Half given back in | Never, in 120 days | Unflagged, same size | Half given back in | Never |
|---|---|---|---|---|---|---|
| Coffee (Arabica) | 130 | 4 (2-14) d | 9% | 404 | 3 (1-10) d | 9% |
| Crude Oil (WTI) | 204 | 5 (2-15) d | 13% | 905 | 3 (1-10) d | 9% |
| Wheat (Chicago SRW) | 249 | 5 (2-19) d | 8% | 1325 | 3 (1-10) d | 7% |
| Gold (COMEX) | 227 | 7 (2-18) d | 14% | 576 | 3 (1-8) d | 12% |
| Silver (COMEX) | 260 | 7 (2-18) d | 13% | 674 | 3 (1-10) d | 10% |

**What this supports.** A buyer who must transact into a flagged shock has a measured distribution for waiting, not a prediction: on most commodities half the move is typically given back within a working week or two. **What it does not support:** waiting as a general policy. Around one shock in ten never gives half back inside 120 trading days, and which one is not knowable in advance - that is the same direction question the project measured and failed.

The control column is the interesting one. Flagged shocks take longer to half-retrace than unflagged moves of the same size, so the flag is selecting days that behave differently; but the share that never retrace is close in both columns, so the flag says something about speed, not about permanence.

## 2. Which risk is actually being carried

A buyer hedging a commodity-specific disruption and a buyer carrying dollar risk have different problems, and a commodity instrument only addresses the first. The split is read from `factor_adjusted_report.md`.

| Commodity | Days assessed | Macro-driven | Share | Median window R² |
|---|---|---|---|---|
| Coffee (Arabica) | 225 | 55 | 24.4% | 0.07 |
| Crude Oil (WTI) | 330 | 226 | 68.5% | 0.76 |
| Wheat (Chicago SRW) | 394 | 112 | 28.4% | 0.12 |
| Gold (COMEX) | 397 | 167 | 42.1% | 0.30 |
| Silver (COMEX) | 429 | 140 | 32.6% | 0.29 |

**Two cautions carried over from that report, not restated as results.** Crude oil's share is inflated because the broad-complex factor is heavily weighted to energy, so crude is partly regressed on itself. And where the window R² is low the residual is most of the move whatever happened, so "commodity-specific" comes close to restating that the day was flagged.

**What this supports.** Choosing what to hedge: a commodity whose flagged days are largely the complex repricing is not well addressed by a commodity-specific contract. **What it does not establish:** that the dollar caused those moves. A confound moving with the dollar looks identical.

## 3. How much of a commodity move reaches a price people pay

25 commodity-and-index pairs were fixed in code before any result was seen and all are reported. Verdicts use the Holm-corrected p-value at 5%, which is strict with this many pairs.

| Consumer price index | Commodity | After a 10% rise | p (Holm) | Months |
|---|---|---|---|---|
| United States: gasoline | crude oil (WTI) | +5.98% | <0.001 | 308 |
| United States: energy | crude oil (WTI) | +3.89% | <0.001 | 306 |
| United States: coffee | coffee (arabica) | +2.27% | <0.001 | 282 |
| United States: food | food commodities (IMF index) | +1.31% | <0.001 | 306 |
| United States: all items | food commodities (IMF index) | +1.09% | <0.001 | 306 |
| United States: all items | all commodities (IMF index) | +0.77% | <0.001 | 306 |
| United States: food | wheat | +0.49% | 0.003 | 306 |
| United States: all items | crude oil (WTI) | +0.46% | <0.001 | 306 |
| United States: all items | wheat | +0.43% | 0.009 | 306 |

**9 of 25 pairs show pass-through. 16 show nothing that can be told from chance**, including every pair tested against India's index. A null is a result: for those commodities and those indices the monthly record shows nothing chance alone would not.

**What this supports.** Budgeting: a procurement plan can carry a stated elasticity for the pairs above, with its interval. **What it does not support:** using a commodity price to estimate next month's inflation. After correction, **0 of 25 pairs** improve a figure made before publication - several show large improvements with an uncorrected p under 0.05 and are still not counted.

## What nothing here supports

- **A direction call.** Tested on three methods and a null result each time (`forecast_evaluation.md`, `backtest_outlook_report.md`).
- **A causal claim from the inflation regressions.** They measure how two series moved together, over months, with a stated lag structure.
- **A claim that a macro-driven day was caused by the dollar.**
- **Anything about a commodity with no run behind it.** A blank in these tables is a gap in what has been measured, not a negative finding.

Not financial advice.