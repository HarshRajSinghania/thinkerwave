"""Decide between a price rise and holding prices, using the figures you are sure of.

Run it:  THINKERWAVE_API_KEY=tw_live_… python examples/pricing_and_churn.py
Needs:   pip install thinkerwave
"""

from thinkerwave import Client, RoundFinished, RunError, RunFinished

PROBLEM = (
    "Should we raise prices 15%, 8%, or hold? We want the choice that maximises revenue "
    "over the next 12 months without damaging the customer base."
)
GIVEN = [
    "1,200 customers",
    "$85/month",
    "3.1% monthly logo churn",
    "Last 8% increase spiked churn to 4.6% for three months",
]
STANDARDS = [
    "Show the break-even churn rate for +15% vs hold",
]
PITFALLS = [
    "Do not assume churn is constant after a price change",
    "Do not ignore that the last increase raised churn only for a while",
]


def main() -> None:
    with Client() as tw:  # reads THINKERWAVE_API_KEY
        run = tw.runs.create(PROBLEM, given=GIVEN, standards=STANDARDS, pitfalls=PITFALLS, max_rounds=6)
        print(f"Started {run.id}")

        for event in tw.runs.events(run.id):
            if isinstance(event, RoundFinished):
                score = "n/a" if event.score is None else f"{event.score:.1f}"
                print(f"Round {event.round} · {score}")
            elif isinstance(event, RunFinished):
                print(f"Run {event.status}.")
            elif isinstance(event, RunError):
                raise SystemExit(event.message)

        answer = tw.runs.answer(run.id)
        print(f"\n{answer.answer}\n")
        print(f"Confidence: {answer.confidence} (round {answer.round})")
        for finding in answer.findings:
            flag = " [flagged]" if finding.flagged else ""
            print(f"  [{finding.evidence or 'untagged'}]{flag} {finding.text}")

        for file in tw.runs.files(run.id):
            if file.kind == "image":
                path = tw.runs.download(run.id, file.path, to="out")
                print(f"Saved {path}")


if __name__ == "__main__":
    main()
