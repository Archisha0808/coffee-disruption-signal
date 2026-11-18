# Explain or Refuse on Other Commodities

The same pipeline that is measured on coffee, run on crude oil, wheat, gold and silver. Produced by `python -m scripts.run_commodity_eval`. Rates carry 95% Wilson intervals; the samples are small and the intervals say so.

**These commodities have no answer key.** What is measured instead:

- *Explained a documented move*: the days the detector flags as a one-day shock inside each commodity's cited historical events, from 2017 on (the news search reaches no further back). A documented event is weaker than a checked label, and an explanation counted here has not been checked against the cited cause.
- *Explained an invented move*: quiet days given the size and direction of a real shock. Refusing is the only right answer, so every explanation is false. This needs no labels and is the one figure here that is comparable with coffee's.

Always explaining would score 100% on the first column and 100% on the second; always refusing would score 0% on both. A system is doing something only if the first figure is well above the second.

| Commodity | Explained a documented move | Explained an invented move (right answer: none) |
|---|---|---|
| Crude Oil (WTI) | 100.0% (4/4; 95% CI 51.0-100.0%); 2 more not decided (2 of them a fault, so the rate is over 4 date(s), not 6) | 16.7% (2/12; 95% CI 4.7-44.8%) |

## Crude Oil (WTI)

Not run, because the news search does not reach back that far: 2014 OPEC no-cut decision.

| Date | Event it belongs to | Move | Outcome | What was said, or why not |
|---|---|---|---|---|
| 2020-03-06 | 2020 Saudi-Russia price war | -10.1% | explained | -10.1% day-over-day move (z-score -5.06), on top of -22.7% over the last 10 trading days on 2020-03-06. Reasons given by 4 reports from that day: - "Crude Oil Prices : Crude oil prices plunge over 5 % on Opec reports , coronavirus" (economictimes.indiatimes.com, 2020-03-06). Reported move: down 5%. Reason: Opec reports , coronavirus. Quote: "Brent and WTI crude futures tumbled by nearly $3 a barrel, or more than 5%,  |
| 2020-03-09 | 2020 Saudi-Russia price war | -24.6% | explained | -24.6% day-over-day move (z-score -10.83), on top of -39.5% over the last 10 trading days on 2020-03-09. Reasons given by 5 reports from that day: - "Brent oil prices drop to $ 31 . 74" (news.am, 2020-03-09). Reported move: down 42.6%. Reason: falling demand due to coronavirus. Quote: "falling demand due to coronavirus" (source: 4ee1e219f3a837fd) - "Цена нефти Brent упала до $31 , 74" (armenpress.am, 2020-03-09). Rep |
| 2020-04-20 | 2020 negative WTI price | - | fault | The size and direction of this move cannot be computed: the price was not positive at one end of the day. |
| 2020-04-21 | 2020 negative WTI price | - | fault | The size and direction of this move cannot be computed: the price was not positive at one end of the day. |
| 2022-03-01 | 2022 Russia invades Ukraine | +8.0% | explained | +8.0% day-over-day move (z-score 3.03) on 2022-03-01. Reasons given by 7 reports from that day: - "Oil price rises above $105 a barrel ahead of OPEC+ meeting" (thecable.ng, 2022-03-01). Reported move: up 7%. Reason: OPEC and its allies adopted a production cut system to prop up prices and prevent an oversupply in the global oil market. Quote: "OPEC and its allies adopted a production cut system to prop up prices and  |
| 2022-03-09 | 2022 Russia invades Ukraine | -12.1% | explained | -12.1% day-over-day move (z-score -4.34) on 2022-03-09. Reasons given by 2 reports from that day: - "Oil Prices Tumbles 15 % As Ukraine President Signals Openness to Talks" (markets.businessinsider.com, 2022-03-09). Reported move: down 15%. Reason: Ukraine President signals openness to talks. Quote: "Oil Prices Tumbles 15 % As Ukraine President Signals Openness to Talks" (source: 0a88da377840da56) - "Oil Falters on O |

Invented-move test (pipeline version 11, seed 7): explained 16.7% (2/12; 95% CI 4.7-44.8%).

- False explanation on 2019-11-14: +2.0% day-over-day move (z-score 2.35) on 2019-11-14. Reasons given by 4 reports from that day: - "Oil up 1 % on U . S . crude stocks fall , OPEC comments on U . S . shale growth" (lfpress.com, 2019-11-14). Reported move: up 1%. Reason: U.S. crude stocks fall. Quote: "Oil up 1 % on U . S . crude stocks fall , OPEC comments on U . S . shale growth" (source: 8afff5b56e9e3dc6) - "UPDATE 4 - Oil up 1 
- False explanation on 2024-12-02: +5.1% day-over-day move (z-score 2.46) on 2024-12-02. Reasons given by 2 reports from that day: - "Oil prices rise on China demand optimism ; markets eye OPEC meeting" (invezz.com, 2024-12-02). Reported move: up, size not stated. Reason: robust manufacturing in China and rising geopolitical tensions. Quote: "Oil prices rose sharply on robust manufacturing in China and rising geopolitical tensions.

## Limits

- No answer key for these commodities. The documented dates were chosen by a rule (largest shock days inside cited events), not checked one by one, and nobody has read whether each explanation names the cited cause.
- The headline word lists that choose which articles are read were built and tuned on coffee. For the other commodities they were written once and not tuned (src/rag/market_report.py), so their reading is likely to be worse chosen.
- The decision rule and its settings were designed on coffee dates. Every figure here is therefore out of sample for the rule, which is what makes it worth having, and also why it may be lower than coffee's.
- A handful of dates per commodity. One date changes a rate by ten points or more.
