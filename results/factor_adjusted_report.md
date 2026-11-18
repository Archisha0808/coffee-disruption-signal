# Factor-Adjusted Anomalies: which flagged days are about the commodity

Each flagged day's return is compared with what the dollar, equities and a broad commodity index would predict, using betas fitted on the 75 trading days **before** that day. What is left over is the residual; a day whose residual is extreme is about this commodity, and a day whose raw move is extreme while its residual is not was the complex repricing.

**Each day is assessed over the horizon it was flagged on.** The base detector flags on a daily shock or on a 10-day build-up, and most flagged days are the second kind. A build-up has no extreme daily move by construction, so judging it by a daily residual returns "macro-driven" whatever drove it. Those days are tested against 10-day cumulative factor returns instead; a day flagged by both is judged on the daily move.

This sits beside the base detector and does not change it. Every evaluation figure in `results/` was drawn at the base detector's raw threshold, so changing which days are flagged would invalidate the answer key.

| Commodity | Flagged | Assessed | Commodity-specific | Macro-driven | Macro share | Macro share, shock days only | Median window R² |
|---|---|---|---|---|---|---|---|
| coffee | 279 | 225 | 170 | 55 | 24.4% | 15.3% | 0.06 |
| crude_oil | 420 | 330 | 104 | 226 | 68.5% | 62.8% | 0.75 |
| wheat | 519 | 394 | 282 | 112 | 28.4% | 19.8% | 0.12 |
| gold | 491 | 397 | 230 | 167 | 42.1% | 31.9% | 0.29 |
| silver | 515 | 429 | 289 | 140 | 32.6% | 22.3% | 0.27 |

Unclassified days are left out of the shares: a day with too little history for its window, a contract-switch day, or a day whose price was not positive (WTI settled at -$37.63 on 20 April 2020, where a log return does not exist).

### Two readings that are not comparable with the others

**Crude oil's window R² is high because the factor contains the commodity.** The broad-complex factor is DBC, which is heavily weighted to energy, so crude is being regressed partly on itself. Its macro share is inflated by an unknown amount and should not be set beside the others. A spot index with no energy weight, or dropping the broad factor for crude alone, would fix it; neither has been done.

**A low window R² makes the split uninformative.** Where the three factors account for little of a commodity's day-to-day variation, the residual is most of the move whatever happened, and "commodity-specific" is close to restating that the day was flagged at all.

## What a macro verdict does and does not mean

- **Tested.** The residual and its z-score are the output of a stated model on a stated window, fitted without the day being tested.
- **Not established.** That the dollar *caused* the move. A confound moving with the dollar would look identical. The honest reading is narrower: nothing in this day's move needs a commodity-specific story.
- **The cumulative z-scores are optimistic.** Consecutive 10-day windows overlap by nine days, so those residuals are autocorrelated and the spread they are measured against is too narrow. Read them as a ranking, not as a probability. The detector's own cumulative check has the same property.
- The residual is never attributed. Whatever the three factors do not explain is reported as unexplained, not assigned to a preferred cause.