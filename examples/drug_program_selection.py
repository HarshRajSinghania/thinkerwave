"""Choose which drug programs to fund when the budget covers only some of them.

Run it:  THINKERWAVE_API_KEY=tw_live_… python examples/drug_program_selection.py
Needs:   pip install thinkerwave
"""

from thinkerwave import Client, RoundFinished, RunError, RunFinished

PROBLEM = (
    "We can fund two of four preclinical programs this year. Recommend which two and say how sure you "
    "are. Programs: an oral kinase inhibitor for lung cancer, an antibody for psoriasis, a gene therapy "
    "for a rare eye disease, and a small molecule for type 2 diabetes."
)
GIVEN = [
    "Budget covers two programs",
    "The kinase inhibitor has shown tumour shrinkage in mice but no safety data yet",
    "The gene therapy targets a population of roughly 5,000 patients in our markets",
    "The diabetes market is crowded with approved competitors",
]
STANDARDS = [
    "Rate each program on probability of success, market size and time to first revenue",
    "Mark clearly which numbers are published figures and which are estimates",
    "Name the single fact that would most change the recommendation",
]
PITFALLS = [
    "Do not treat mouse results as evidence of human efficacy",
    "Do not rank by market size alone",
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
