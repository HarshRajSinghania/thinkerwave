# Evidence

ThinkerWave does not just hand you an answer. It hands you the answer, how confident it is, and a list of
**findings**, each tagged with the kind of evidence behind it. Read the findings; they are the point.

## The tags

| Tag | What it means for you |
|---|---|
| **verified** | Checked: the number came out of a calculation the run actually did, or the claim came from a source it actually read. You can ask for the file or the source and re-check it. |
| **assumption** | Taken as given or reasoned from what it knows. It may well be right, but nothing confirmed it. Check it against what you know. |
| **guess** | A hunch with no support. Treat it as a lead to look into, not a fact. |
| *(untagged)* | The finding carries no evidence tag. Treat it like an assumption until you know better. |

## Flagged findings

A finding with `flagged: true` is disputed or needs a second look: the run itself found a reason to doubt it. Look at
these first.

## Confidence

`confidence` is `high`, `medium`, `low` or `unknown`. It is the agent's own statement of how sure it is, and it should
fall when the findings are mostly assumptions and guesses.

## A high score is not proof

Every round gets a score from 0 to 10, and the run keeps the round that scored best. The score is a useful signal that a
later round improved on an earlier one, but it is a judgement, not a measurement. A high score does not mean the answer is
correct, and a mid score does not mean it is wrong. Read the findings: how many are verified, how many rest on assumptions, and
whether the assumptions are ones you accept.

## Getting better evidence

- Put the figures you are sure of in `given`; they are kept exactly as written and used in the calculations.
- Use `standards` to demand what matters ("show the calculation behind every revenue figure").
- Use `pitfalls` to rule out mistakes you have seen before.
- If an answer is wrong, open an issue with the run id; that is the most useful report we can get.
