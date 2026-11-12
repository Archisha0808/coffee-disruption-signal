# Pipeline Evaluation Report

**98** stored pipeline runs. Rates are shown with 95% Wilson intervals; at this sample size the intervals are wide and the point estimates should not be quoted without them.

> **Mixed pipeline versions**: {'11': 94, '1': 4}. Runs from different versions were retrieved, gated or prompted differently and are not directly comparable. Re-run the older dates before quoting a combined figure.

Models that answered: openai/gpt-oss-120b (46), qwen/qwen3.8-27b (27), not recorded (25).

More than one model answered, and they are not interchangeable. The model's own decision (before the direction guard), by model: openai/gpt-oss-120b explained 43.5% (20/46; 95% CI 30.2-57.8%); qwen/qwen3.8-27b explained 33.3% (9/27; 95% CI 18.6-52.2%). The models did not see the same dates, so this is not a like-for-like comparison, but a pooled rate over a mixed set partly measures which model happened to answer. Set EXPLAINER_PROVIDERS to one provider for a run that is meant to be compared with another.

5 stored run(s) are on dates whose flagged move was not a real market move of that size - the price series switched futures contract that day (data/labeling/contract_switch_dates.csv) - and are left out of everything below: 2018-05-21, 2020-03-19, 2021-03-22, 2023-03-22, 2023-09-20.

2 run(s) are on dates the current detections file does not flag as anomalies (2026-08-28, 2026-09-11). They were run on request and are included, but they are not detected events.

In 74.5% (73/98; 95% CI 65.0-82.1%) of runs at least one news-API query failed after retries (in 23, none was answered). Those runs searched with fewer queries than intended: 49.3% (36/73; 95% CI 38.2-60.5%) of them ended in a refusal, against 44.0% (11/25; 95% CI 26.7-62.9%) of the rest. A refusal on such a run may reflect the API rather than the news; `python -m scripts.run_eval_set --run --retry-incomplete` re-asks only the failed queries.

## 1. Outcomes

Every run falls in exactly one tier.

| Outcome tier | Runs |
|---|---|
| REFUSED_WEAK_EVIDENCE | 40 |
| EXPLAINED_TENTATIVE | 21 |
| RETRIEVAL_FAILED | 20 |
| EXPLAINED_STRONG | 9 |
| REFUSED_CONFLICTING | 7 |
| SYSTEM_ERROR | 1 |
| **Total** | **98** |

2 run(s) were saved before the outcome tier existed and are classified here from their stored signals.

- Explained: 30.6% (30/98; 95% CI 22.4-40.3%)
- Refused: 48.0% (47/98; 95% CI 38.3-57.7%)
- Faults (model or retrieval unavailable): 21.4% (21/98; 95% CI 14.5-30.5%)
- Explained, faults excluded: 39.0% (30/77; 95% CI 28.8-50.1%)

An explanation rate is not a quality measure on its own: a system that explained every date would score 100% here. Section 2 is the one that checks decisions against ground truth.

## 2. Decision accuracy on the labelled set

16 dates carry a label (EXPLAIN: a documented cause exists; REFUSE: no clean cause, the system should decline). Graded: 16. Ended in a fault: 0. No run yet: 0.

**Explaining every date would score 100.0% (16/16; 95% CI 80.6-100.0%) here.** The "correct decision" row below is worth something only where it beats that.

**No graded date in this answer key is one where refusing is right.** So this section measures one thing only: how often the system fails to explain a move that has a documented cause. Whether it refuses when it should is not measured here at all; that is what the invented-move test is for (results/robustness_report.md).

| | As run | Model alone | Guard: more against than with | Guard: a tie also withholds |
|---|---|---|---|---|
| Correct decision | 62.5% (10/16; 95% CI 38.6-81.5%) | 62.5% (10/16; 95% CI 38.6-81.5%) | 62.5% (10/16; 95% CI 38.6-81.5%) | 62.5% (10/16; 95% CI 38.6-81.5%) |
| Explained when it should | 62.5% (10/16; 95% CI 38.6-81.5%) | 62.5% (10/16; 95% CI 38.6-81.5%) | 62.5% (10/16; 95% CI 38.6-81.5%) | 62.5% (10/16; 95% CI 38.6-81.5%) |
| Refused when it should | n/a (0 cases) | n/a (0 cases) | n/a (0 cases) | n/a (0 cases) |

73 of these runs were decided by the blind-evidence rule, which has no direction guard: for them all four columns show the decision as run. The guard columns only differ for runs made by the earlier path.

"As run" is the decision each stored run ended with, under whatever version produced it. The other three columns are computed from the same stored runs: the model's own answer, and that answer after each guard rule, so they are comparable across versions. The pipeline uses the "more against than with" rule.

Decisions that disagree with the label:

| Date | Label | System | Evidence direction (with / against) | Model |
|---|---|---|---|---|
| 2023-01-31 | EXPLAIN | REFUSED | 0 / 0 | qwen/qwen3.8-27b |
| 2024-04-30 | EXPLAIN | REFUSED | 0 / 0 | openai/gpt-oss-120b |
| 2024-09-23 | EXPLAIN | REFUSED | 0 / 0 | openai/gpt-oss-120b |
| 2024-12-02 | EXPLAIN | REFUSED | 0 / 1 | openai/gpt-oss-120b |
| 2025-04-07 | EXPLAIN | REFUSED | 0 / 0 | openai/gpt-oss-120b |
| 2025-08-15 | EXPLAIN | REFUSED | 0 / 0 | openai/gpt-oss-120b |

The guard and both of its rules were chosen after looking at runs on these labelled dates, so the guard columns are in-sample and are not evidence the guard generalises - that needs inputs it was not designed on (see results/robustness_report.md).

Caveats: each label rests on one round of research that nobody has checked independently, and rows whose notes start with CHECK are borderline; the labels were made after the system had been run on these dates, from market reports and without sight of its answers; a correct EXPLAIN decision means the system chose to explain, not that its text names the documented cause.

## 3. Citations

- Citations checked: 51 across 30 explained run(s) (0 explained run(s) have no citation report).
- Cited document was in the evidence shown to the model: 100.0% (51/51; 95% CI 93.0-100.0%)
- Claim-to-document similarity: minimum 0.777, median 0.843; flagged weak: 0.
- Cited document not among the closest to its claim: 11.4% (5/44; 95% CI 5.0-24.0%)

What this establishes: the model did not invent source ids. What it does not: that each cited document supports the claim attached to it. The similarity score cannot fail in practice (any two coffee-market texts score 0.75-0.95 with this embedding model, against a 0.60 threshold), so a 0% weak-support rate carries no information.

No human citation audit has been recorded yet. Run `python -m scripts.audit_citations --export`, label the sheet, then `--score` to add a measured support rate here.

## 4. Evidence

- Relevance gate passed: 74.5% (73/98; 95% CI 65.0-82.1%)
- Documents retrieved per run: 296.8 on average; runs with none: 20
- Accepted documents, over the 74 run(s) that saved their sources: 7924, of which 7896 are distinct stories. Copies of another accepted document: 0.4% (28/7924; 95% CI 0.2-0.5%)
- Accepted documents dated after the anomaly date: 0.0% (0/7924; 95% CI 0.0-0.0%)
- Per explained run: 13.7 accepted documents, 123.0 distinct stories, 79.7 domains (over 29 explained run(s) that saved their sources)
- Explained from a single distinct story: 0.0% (0/29; 95% CI 0.0-11.7%)

Domain counts overstate independence when the same wire story appears on several sites; distinct stories is the better measure of how many sources an explanation rests on.

## 5. Evidence direction (heuristic)

Of 30 explained runs, 30 have a direction tally. Accepted evidence leaned the same way as the move in 93.3% (28/30; 95% CI 78.7-98.2%).

Explained despite evidence leaning against the move: 2021-07-19 (2 with / 2 against), 2022-04-13 (1 with / 1 against).

This measures the retrieved documents with a word list (src/rag/direction.py). It is not a check that the explanation is correct.

### Runs decided by the blind-evidence rule

73 run(s). The model read the recent documents without being told the move: it returned a reading for 98.5% (790/802; 95% CI 97.4-99.1%) of the documents it was shown, and of the reasons it reported, the quote was found in the document for 97.0% (256/264; 95% CI 94.1-98.5%). A reason whose quote is not found is discarded before the rule runs.

| Move | Runs | Explained |
|---|---|---|
| down | 34 | 29.4% (10/34; 95% CI 16.8-46.2%) |
| up | 39 | 48.7% (19/39; 95% CI 33.9-63.8%) |

Direction test on every explained date: had prices moved the opposite way, the same readings would still have produced an explanation for 0.0% (0/29; 95% CI 0.0-11.7%). That can only happen when the deciding evidence is split evenly, and such explanations are marked tentative. Under the earlier design, where the model was told the move, this was the test it failed.

Where the refused dates stopped:

| Stopped at | Refused dates |
|---|---|
| Nothing recent was found | 0.0% (0/44; 95% CI 0.0-8.0%) |
| Recent articles found, none relevant enough to read | 0.0% (0/44; 95% CI 0.0-8.0%) |
| Recent articles read, none gave a reason with a quote | 52.3% (23/44; 95% CI 37.9-66.2%) |
| A reason was found, for the opposite move | 47.7% (21/44; 95% CI 33.8-62.1%) |

The first two rows are search and filtering: no change to the reading or the rule can explain a date for which nothing recent and relevant was retrieved.

Dates labelled as explainable that were refused:

| Date | Stopped at | Retrieved | Of those recent | Relevant enough to read |
|---|---|---|---|---|
| 2023-01-31 | A reason was found, for the opposite move | 584 | 396 | 142 |
| 2024-04-30 | A reason was found, for the opposite move | 630 | 432 | 171 |
| 2024-09-23 | A reason was found, for the opposite move | 500 | 333 | 168 |
| 2024-12-02 | A reason was found, for the opposite move | 578 | 429 | 270 |
| 2025-04-07 | A reason was found, for the opposite move | 644 | 434 | 211 |
| 2025-08-15 | A reason was found, for the opposite move | 660 | 334 | 163 |

The same stored readings under other settings of the rule (no model is called again). The first row is the pipeline's setting. If the rows differ a lot, the setting is doing the work and the result should not be trusted; "pooled" counts every recent reading equally, the shape of rule that made the earlier guard refuse most down days.

| Rule | Recent means | Explained, all runs | Explained when it should | Refused when it should |
|---|---|---|---|---|
| freshest | same day or up to 2 trading days before | 39.7% (29/73; 95% CI 29.3-51.2%) | 62.5% (10/16; 95% CI 38.6-81.5%) | n/a (0 cases) |
| freshest | same day or up to 1 trading day before | 39.7% (29/73; 95% CI 29.3-51.2%) | 62.5% (10/16; 95% CI 38.6-81.5%) | n/a (0 cases) |
| freshest | same day or up to 3 trading days before | 39.7% (29/73; 95% CI 29.3-51.2%) | 62.5% (10/16; 95% CI 38.6-81.5%) | n/a (0 cases) |
| pooled | same day or up to 2 trading days before | 42.5% (31/73; 95% CI 31.8-53.9%) | 62.5% (10/16; 95% CI 38.6-81.5%) | n/a (0 cases) |

Other versions of what counts as evidence, scored the same way from the same readings. A version is only worth adopting if it raises the last column without lowering the one before it. With this few labelled dates a difference of one date is not evidence.

| What counts as evidence | Explained, all runs | Explained when it should | Refused when it should |
|---|---|---|---|
| As the pipeline runs | 39.7% (29/73; 95% CI 29.3-51.2%) | 62.5% (10/16; 95% CI 38.6-81.5%) | n/a (0 cases) |
| Only documents that cleared the relevance filter itself | 21.9% (16/73; 95% CI 14.0-32.7%) | 43.8% (7/16; 95% CI 23.1-66.8%) | n/a (0 cases) |
| Ignore reports of a move under a quarter the size of the actual one | 39.7% (29/73; 95% CI 29.3-51.2%) | 62.5% (10/16; 95% CI 38.6-81.5%) | n/a (0 cases) |
| Both of the last two | 39.7% (29/73; 95% CI 29.3-51.2%) | 62.5% (10/16; 95% CI 38.6-81.5%) | n/a (0 cases) |
| Only articles that report a price move, not background events (added after seeing these dates) | 39.7% (29/73; 95% CI 29.3-51.2%) | 62.5% (10/16; 95% CI 38.6-81.5%) | n/a (0 cases) |
| Counting reports of older and forecast moves too (the rule before version 9) | 46.6% (34/73; 95% CI 35.6-57.9%) | 68.8% (11/16; 95% CI 44.4-85.8%) | n/a (0 cases) |
| Without the size check (a report need not describe a move this large) | 56.2% (41/73; 95% CI 44.8-67.0%) | 87.5% (14/16; 95% CI 64.0-96.5%) | n/a (0 cases) |
| Counting trading reasons too ("technical adjustments") | 46.6% (34/73; 95% CI 35.6-57.9%) | 75.0% (12/16; 95% CI 50.5-89.8%) | n/a (0 cases) |
| Counting reports about another market too (robusta, local prices) | 42.5% (31/73; 95% CI 31.8-53.9%) | 68.8% (11/16; 95% CI 44.4-85.8%) | n/a (0 cases) |
| Without all three (the rule before version 11) | 67.1% (49/73; 95% CI 55.7-76.8%) | 100.0% (16/16; 95% CI 80.6-100.0%) | n/a (0 cases) |

Recent documents read although they scored just under the relevance filter's bar: 664, of which 66 gave a reason with a quote that was found. The "only documents that cleared the filter" row above is the result without them.

Which search found the documents. "Read candidates" are documents relevant enough to be read; "gave a reason" are those whose reading counted as evidence; the last two columns are documents an explanation rests on and the number of dates they decided. A document found by two searches is credited to the one that returned it first.

| Search | Read candidates | Gave a reason | In an explanation | Dates |
|---|---|---|---|---|
| combined search, recent days | 3256 | 53 | 19 | 17 |
| combined search, day of the move | 1533 | 23 | 14 | 11 |
| combined search, full window | 1674 | 26 | 10 | 9 |
| news feed | 1362 | 10 | 1 | 1 |

Across every run, the direction guard withholds 0.0% (0/1; 95% CI 0.0-79.3%) of the explanations the model wrote. By direction of the move:

| Move | Runs | Model explained | Guard withholds | Explained after the guard |
|---|---|---|---|---|
| down | 1 | 0 | n/a (0 cases) | 0.0% (0/1; 95% CI 0.0-79.3%) |
| up | 3 | 1 | 0.0% (0/1; 95% CI 0.0-79.3%) | 33.3% (1/3; 95% CI 6.1-79.2%) |

If the guard withholds far more on one direction than the other, it is not only catching unsupported explanations: it is also reporting which way the retrieved news leans. The GDELT queries are about supply shocks (frost, drought, tariffs, shipping), which are stories about prices rising, so on a day prices fell the tally starts against the move. A should-refuse label set made only of days in the direction the guard already refuses cannot show that the guard works.

## 6. By year

| Year | Explained | Refused | Fault |
|---|---|---|---|
| 2018 | 3 | 6 | 0 |
| 2019 | 3 | 9 | 0 |
| 2020 | 3 | 8 | 0 |
| 2021 | 8 | 4 | 0 |
| 2022 | 5 | 6 | 0 |
| 2023 | 3 | 2 | 4 |
| 2024 | 1 | 3 | 8 |
| 2025 | 2 | 2 | 6 |
| 2026 | 2 | 7 | 3 |

Dates the answering model could have seen in training are a weaker test of retrieval than dates after its knowledge cutoff. That split needs the cutoff of each model used and is reported by src/evaluation/robustness.py.
