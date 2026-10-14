# Quickstart

Five minutes from nothing to a finished run.

## 1. Create an API key

Sign in at [thinkerwave.ai/app](https://thinkerwave.ai/app), open **Settings → API keys**, and create a key.
The full key (it starts with `tw_live_`) is shown once. Copy it somewhere safe; if you lose it, revoke it and make a new one.
Never paste a key into an issue, a chat or a commit.

## 2. Install

```bash
pip install thinkerwave
export THINKERWAVE_API_KEY=tw_live_…
```

Python 3.10 or newer. Check that the key works and see your limits:

```bash
tw me
```

## 3. Run from the terminal

```bash
tw run "Should we raise prices 15%, 8%, or hold? 1,200 customers at \$85/month, 3.1% monthly churn." \
  --given "last 8% increase spiked churn to 4.6% for three months" --rounds 6 --watch
```

`--watch` follows the run live, one line per step, then prints the answer and the evidence behind it.
Without `--watch` the command prints the run id and returns; pick it up later:

```bash
tw watch wr_…      # follow it live
tw answer wr_…     # the best answer so far
tw files wr_…      # charts and tables it produced
tw get wr_… chart.png -o chart.png
```

## 4. Run from Python

```python
from thinkerwave import Client

tw = Client()  # reads THINKERWAVE_API_KEY

run = tw.runs.create(
    "Should we raise prices 15%, 8%, or hold? 1,200 customers at $85/month, 3.1% monthly churn.",
    given=["last 8% increase spiked churn to 4.6% for three months"],
    max_rounds=6,
)

for event in tw.runs.events(run.id):
    print(event)

answer = tw.runs.answer(run.id)
print(answer.answer, answer.confidence)
for finding in answer.findings:
    print(f"[{finding.evidence}] {finding.text}")
```

## What to give it

- **problem**: what you want decided or worked out, in plain words (20 to 12,000 characters).
- **given**: facts you are sure of. They are kept exactly as written. Put your real figures here.
- **standards**: what a good answer must do ("compare at least three options").
- **pitfalls**: mistakes to avoid ("don't assume churn is constant").

## Reading the result

A run works in rounds and keeps the best answer. Read the answer, then read the findings: each claim is tagged
**verified**, **assumption** or **guess**. A high score is not proof. See [evidence](evidence.md).

## Next

- [API reference](api.md)
- [Events](events.md)
- [Command line](cli.md)
- [Claude Code and Cursor](mcp.md)
- [Limits](limits.md) and [errors](errors.md)
