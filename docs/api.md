# API reference

Base URL: `https://api.thinkerwave.ai/api/v1`

Every request carries your API key as a bearer token. Bodies and responses are JSON unless stated.
Rounds are numbered from 1 in every field. The machine-readable description is [`spec/openapi.yaml`](../spec/openapi.yaml).

```bash
export THINKERWAVE_API_KEY=tw_live_…
```

Errors have one shape everywhere; see [errors](errors.md).

## Start a run: `POST /runs`

```bash
curl -X POST https://api.thinkerwave.ai/api/v1/runs \
  -H "Authorization: Bearer $THINKERWAVE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "problem": "Should we raise prices 15%, 8%, or hold? 1,200 customers at $85/month, 3.1% monthly churn.",
    "given": ["last 8% increase spiked churn to 4.6% for three months"],
    "standards": ["compare at least three options"],
    "pitfalls": ["do not assume churn is constant"],
    "max_rounds": 6
  }'
```

| Field | Type | Notes |
|---|---|---|
| `problem` | string | Required. 20 to 12,000 characters. |
| `given` | string[] | Optional. Up to 20 items of up to 300 characters. Facts kept exactly as written. |
| `standards` | string[] | Optional. Up to 15 items of up to 300 characters. What a good answer must do. |
| `pitfalls` | string[] | Optional. Up to 10 items of up to 300 characters. Mistakes to avoid. |
| `max_rounds` | integer | Optional. At least 1. Capped at your plan's limit (`tw me`). |

Response `201`:

```json
{ "id": "wr_…", "status": "queued", "queue_position": 3 }
```

`status` is `queued` or `running`; `queue_position` is null unless queued. The request returns at once; the run takes
minutes. Do not blindly retry this request after a network failure, or you may start a second run: list your runs first.

## List runs: `GET /runs`

```bash
curl -H "Authorization: Bearer $THINKERWAVE_API_KEY" "https://api.thinkerwave.ai/api/v1/runs?limit=20"
```

`limit` is 1 to 100 (default 20). Newest first. Each item:

```json
{ "id": "wr_…", "status": "completed", "problem_preview": "Should we raise prices…",
  "best_score": 6.0, "rounds_done": 4, "created_at": "2026-10-14T10:00:00", "elapsed_seconds": 412.5 }
```

## One run: `GET /runs/{id}`

```bash
curl -H "Authorization: Bearer $THINKERWAVE_API_KEY" https://api.thinkerwave.ai/api/v1/runs/wr_…
```

```json
{ "id": "wr_…", "status": "running", "problem": "your problem text", "round": 4, "max_rounds": 6,
  "best_score": 6.0, "started_at": "2026-10-14T10:00:05", "completed_at": null,
  "elapsed_seconds": 412.5, "stop_reason": null, "error": null }
```

`status` is one of `queued`, `running`, `completed`, `stopped`, `failed`.
`stop_reason` is null while the run is going, then one of:

| `stop_reason` | Meaning |
|---|---|
| `target_reached` | The answer is as good as the run aims for. |
| `plateau` | Further rounds stopped improving it. |
| `max_rounds` | The round limit was reached. |
| `limit_reached` | A usage limit was reached. |
| `stopped` | You stopped it. |
| `failed` | Something went wrong; `error` says what, in a sentence. |

## Stop a run: `POST /runs/{id}/stop`

```bash
curl -X POST -H "Authorization: Bearer $THINKERWAVE_API_KEY" https://api.thinkerwave.ai/api/v1/runs/wr_…/stop
```

Returns `{"ok": true}`. Safe to call more than once. The best answer so far stays available.

## The answer: `GET /runs/{id}/answer`

```bash
curl -H "Authorization: Bearer $THINKERWAVE_API_KEY" https://api.thinkerwave.ai/api/v1/runs/wr_…/answer
```

```json
{ "round": 3, "score": 6.0, "final": false,
  "answer": "Take the 8% increase now.",
  "confidence": "medium",
  "findings": [
    { "text": "At 3.1% churn, +15% adds revenue", "evidence": "verified", "flagged": false },
    { "text": "Churn reacts 1.5x to price", "evidence": "assumption", "flagged": false }
  ],
  "text": "The round's written conclusion." }
```

This is the best answer so far, or the final one once `final` is true. `confidence` is `high`, `medium`, `low` or `unknown`.
Each finding's `evidence` is `verified`, `assumption`, `guess`, or null when untagged; `flagged` marks a finding that is
disputed or needs a second look. Read [evidence](evidence.md) before trusting a score.
Returns `404 not_found` until a round has produced an answer. Schema: [`spec/answer.schema.json`](../spec/answer.schema.json).

## Rounds: `GET /runs/{id}/rounds`

```bash
curl -H "Authorization: Bearer $THINKERWAVE_API_KEY" https://api.thinkerwave.ai/api/v1/runs/wr_…/rounds
```

One item per finished round, oldest first:

```json
{ "round": 2, "score": 5.2, "change": "refined",
  "answer": { "answer": "…", "confidence": "low", "findings": [], "text": "…" },
  "tools": { "python": 2, "web_search": 1, "pages_read": 0 } }
```

`change` says how the agent changed after the round: `refined`, `changed_approach`, `rethought`, or null.
`answer` is null if the round produced none. `tools` counts calculations run, web searches made and pages read.

## Files: `GET /runs/{id}/files`

```bash
curl -H "Authorization: Bearer $THINKERWAVE_API_KEY" https://api.thinkerwave.ai/api/v1/runs/wr_…/files
```

```json
[ { "path": "chart.png", "size": 48213, "type": "image/png", "kind": "image" } ]
```

`kind` is `image`, `table`, `text` or `other`. Only files the run produced are listed.

## Download a file: `GET /runs/{id}/files/{path}`

```bash
curl -H "Authorization: Bearer $THINKERWAVE_API_KEY" -o chart.png \
  https://api.thinkerwave.ai/api/v1/runs/wr_…/files/chart.png
```

`path` is the path from the listing and may contain slashes. Images, tables and text are served with their own type;
anything else is sent as a download (`application/octet-stream`).

## Your account: `GET /me`

```bash
curl -H "Authorization: Bearer $THINKERWAVE_API_KEY" https://api.thinkerwave.ai/api/v1/me
```

```json
{ "email": "you@example.com", "plan": "trial", "runs_today": 1, "runs_per_day": 5,
  "concurrent_runs": 1, "max_rounds": 10 }
```

## Follow a run live: `GET /runs/{id}/events`

Server-Sent Events. See [events](events.md).

```bash
curl -N -H "Authorization: Bearer $THINKERWAVE_API_KEY" https://api.thinkerwave.ai/api/v1/runs/wr_…/events
```
