# Limits

Limits keep runs fair for everyone. Read your live values at any time:

```bash
tw me
# you@example.com · trial · 1/5 runs today · up to 10 rounds
```

or `GET /me`, which returns `runs_today`, `runs_per_day`, `concurrent_runs` and `max_rounds`. The numbers below are
typical; your account's numbers are the ones `tw me` shows.

| Limit | Value |
|---|---|
| Runs per day | `runs_per_day` from `GET /me` (typically 5). |
| Runs at the same time | `concurrent_runs` from `GET /me` (typically 1). A new run waits in line, or is refused with `run_limit`. |
| Rounds per run | At most `max_rounds` from `GET /me` (typically 10). Asking for more is capped, not rejected. |
| Requests | 60 per minute per API key. Over that you get `429 rate_limited` with a `Retry-After` header. |
| Event streams | 3 open at once per key. |
| API keys | Up to 5 active keys per account. |

Runs started from the API and from thinkerwave.ai/app share the same daily and concurrent limits. Using both does not
double them.

A run also stops on its own when it reaches the target, when further rounds stop improving the answer, at the round limit,
or when a usage limit is reached. `stop_reason` on the run says which.

## Input sizes

| Field | Limit |
|---|---|
| `problem` | 20 to 12,000 characters |
| `given` | 20 items, 300 characters each |
| `standards` | 15 items, 300 characters each |
| `pitfalls` | 10 items, 300 characters each |

## Free runs

Free runs are included with every account. When they are used up, new runs are refused with `credit_exhausted`;
runs already started finish.
