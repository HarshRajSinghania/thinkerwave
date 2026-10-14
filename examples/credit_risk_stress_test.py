"""Stress-test a loan portfolio against a downturn and see which findings are verified.

Run it:  THINKERWAVE_API_KEY=tw_live_… python examples/credit_risk_stress_test.py
Needs:   pip install thinkerwave
"""

from thinkerwave import Client, RoundFinished, RunError, RunFinished

PROBLEM = (
    "Stress-test a mid-sized consumer and small-business loan portfolio against a recession in which "
    "unemployment rises 4 points and house prices fall 15% over 18 months. Estimate expected losses, "
    "which segments break first, and whether current capital covers the loss."
)
GIVEN = [
    "Portfolio: 40,000 loans, 1.8 billion outstanding",
    "Segments: 55% unsecured consumer, 30% mortgage, 15% small business",
    "Current 12-month default rate: 2.4% overall",
    "Tier 1 capital is 9.5% of risk-weighted assets",
    "Loss given default on unsecured loans has been about 70%",
]
STANDARDS = [
    "Break losses down by segment",
    "Show the calculation behind every loss figure",
    "State the capital shortfall or surplus explicitly",
]
PITFALLS = [
    "Do not assume defaults rise at the same rate in every segment",
    "Do not treat a single historical recession as the only possible path",
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
