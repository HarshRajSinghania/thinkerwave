# Events

`GET /runs/{id}/events` returns a live feed of what a run is doing, as Server-Sent Events (`text/event-stream`).
It first replays what has already happened, then continues live. The stream always ends with `run.finished`, also for a
run that failed (`"status": "failed"`) or was interrupted by maintenance.

```bash
curl -N -H "Authorization: Bearer $THINKERWAVE_API_KEY" https://api.thinkerwave.ai/api/v1/runs/wr_…/events
```

```
id: 1
event: run.started
data: {"max_rounds": 6}

id: 2
event: round.started
data: {"round": 1}
```

## Event types

| `event:` | `data:` | Meaning |
|---|---|---|
| `run.started` | `{"max_rounds"}` | The run began. `max_rounds` may be null when the limit is not known. |
| `round.started` | `{"round"}` | A round began. |
| `round.step` | `{"round", "step"}` | The round moved to a new step: `plan`, `work`, `check` or `rethink`. |
| `round.tool` | `{"round", "kind", "ok"}` | The agent used a tool. `kind` is `python`, `web_search`, `page_read` or `other`; `ok` says whether it worked. Only the kind is reported, never the content. |
| `round.finished` | `{"round", "score", "change", "best_so_far"}` | A round ended. `change` is `refined`, `changed_approach`, `rethought` or null. `best_so_far` is true when this is the best round yet. |
| `run.went_back` | `{"round", "to_round"}` | Later rounds were not improving, so the run returned to the best earlier answer. |
| `run.finished` | `{"status", "stop_reason", "best_score"}` | The run is over; always the last event. See the `stop_reason` values in the [API reference](api.md). |
| `run.error` | `{"message"}` | The run hit a problem. `message` is a plain sentence. Sent when a reason is known; `run.finished` with `"status": "failed"` follows. |

The four steps in a round: **plan** (decide an approach), **work** (research and calculate), **check** (judge the result honestly),
**rethink** (decide what to change for the next round).

JSON Schema for every payload: [`spec/events.schema.json`](../spec/events.schema.json).

## Reconnecting

Every message has an `id`, except a closing `run.finished` for a run interrupted by maintenance. If the connection drops, reconnect to the same URL with the header
`Last-Event-ID: <last id you saw>` and the stream resumes after it:

```bash
curl -N -H "Authorization: Bearer $THINKERWAVE_API_KEY" -H "Last-Event-ID: 14" \
  https://api.thinkerwave.ai/api/v1/runs/wr_…/events
```

A line starting with `: keepalive` arrives about every 15 seconds. Ignore it; it keeps the connection open.

## Writing a client

- Ignore event names you do not know and fields you do not know. New ones may be added.
- A key may hold at most 3 streams open at once; a fourth gets `429 rate_limited`.
- The Python SDK does all of this for you: `tw.runs.events(run_id)` yields typed events and reconnects itself.
