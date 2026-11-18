"""
Fetch the news the invented-move test is waiting for, and nothing else.

Why this exists. The invented-move test takes quiet trading days, tells the
pipeline a real shock's size and direction, and counts how often it explains
one anyway - refusing is the only right answer, so every explanation is a
false one. It is the one figure on a commodity with no answer key that is
comparable with coffee's.

A quiet day is only tested once EVERY news request for its window has an
answer in the cache. GDELT answers roughly one request in five, and the test's
own fetching pass asks each missing request a fixed number of times (twelve)
before giving up. With about three requests a day that leaves a quarter of the
days short, and a day left short is dropped silently - which is how the test
ends up scoring nothing at all while reporting that it ran.

This script does only the fetching, with as many rounds as you ask for, and
prints what is still missing after each pass. Every answer is written to the
same cache the test reads, so stopping this and running it again continues
where it left off; nothing else on disk is touched, no model is called and no
pipeline output changes. When it reports that every day is complete, run the
test itself with --no-fill.

Usage:
    py -m scripts.fill_placebo_news --commodity crude_oil --rounds 40
    py -m scripts.fill_placebo_news --commodity crude_oil --dry-run

Then:
    py -m src.evaluation.robustness --commodity crude_oil \
        --experiments placebo --n-placebo 12 --seed 7 --providers groq --no-fill
"""

import argparse
import sys


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[1].strip())
    p.add_argument("--commodity", default="crude_oil")
    p.add_argument("--n-placebo", type=int, default=12,
                   help="How many quiet days (must match the test's --n-placebo)")
    p.add_argument("--seed", type=int, default=7,
                   help="Must match the test's --seed, or these are different days")
    p.add_argument("--rounds", type=int, default=40,
                   help="How many times to ask for each missing request (default 40)")
    p.add_argument("--dry-run", action="store_true",
                   help="Report what is missing and fetch nothing")
    args = p.parse_args()

    from src.config.commodities import COMMODITIES
    if args.commodity not in COMMODITIES:
        print(f"unknown --commodity {args.commodity!r}; choose from {', '.join(COMMODITIES)}")
        return 2

    from src.evaluation import robustness as rb
    from scripts.run_eval_set import fill_cache, uncached_requests

    rb.use_commodity(args.commodity)
    days = rb.select_placebo_dates(rb.load_detections(), args.n_placebo, args.seed)
    if not days:
        print(f"No quiet day could be chosen for {args.commodity}. Run the detector first:"
              f"\n    py -m src.modeling.anomaly_detector --commodity {args.commodity}")
        return 1

    def missing():
        return {d: len(uncached_requests(d, args.commodity)) for d in days}

    def show(m):
        done = [d for d, n in m.items() if not n]
        print(f"  {len(done)} of {len(days)} day(s) complete; "
              f"{sum(m.values())} request(s) still missing")
        for d, n in sorted(m.items()):
            print(f"    {d}  {'complete' if not n else f'{n} request(s) missing'}")

    print(f"=== Invented-move news for {args.commodity}: "
          f"{len(days)} quiet day(s), seed {args.seed}")
    before = missing()
    show(before)
    if not sum(before.values()):
        print("\nEvery day is complete. Now run the test itself:\n"
              f"    py -m src.evaluation.robustness --commodity {args.commodity} "
              f"--experiments placebo --n-placebo {args.n_placebo} --seed {args.seed} "
              f"--providers groq --no-fill")
        return 0
    if args.dry_run:
        print("\n--dry-run: nothing was fetched.")
        return 0

    print(f"\nAsking for each missing request up to {args.rounds} time(s). GDELT answers "
          f"about one in five,\nso this is slow; every answer is cached as it arrives, so "
          f"this can be stopped and run again.\n")
    fill_cache([d for d, n in before.items() if n], args.commodity, rounds=args.rounds)

    print("\n=== After fetching")
    after = missing()
    show(after)
    if sum(after.values()):
        print(f"\nStill short. Run this again - the {sum(before.values()) - sum(after.values())} "
              f"answer(s) gathered just now are kept, so the next pass starts from here.")
        return 1
    print("\nEvery day is complete. Now run the test itself:\n"
          f"    py -m src.evaluation.robustness --commodity {args.commodity} "
          f"--experiments placebo --n-placebo {args.n_placebo} --seed {args.seed} "
          f"--providers groq --no-fill")
    return 0


if __name__ == "__main__":
    sys.exit(main())
