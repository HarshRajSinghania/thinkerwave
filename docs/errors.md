# Errors

Every error has the same body, and the message is one plain sentence:

```json
{ "error": { "code": "run_limit", "message": "Run limit reached — wait for a run to finish or try tomorrow." } }
```

Branch on `code`, not on the message. In Python each code has its own exception class (`thinkerwave.RunLimitError`,
`thinkerwave.InvalidKeyError`, …), all subclasses of `ThinkerWaveError`, with `.code`, `.message` and `.status`.

| HTTP | `code` | What happened | What to do |
|---|---|---|---|
| 401 | `invalid_key` | The key is missing, malformed, unknown or revoked. | Check the `Authorization: Bearer …` header. Create a new key in Settings if it was revoked. |
| 403 | `account_disabled` | The account is disabled. | Contact support. Retrying will not help. |
| 403 | `not_invited` | ThinkerWave runs are invite-only for this account for now. | Ask for access at thinkerwave.ai. |
| 402 | `credit_exhausted` | Your free runs are used up. | Ask for more runs at thinkerwave.ai/app. Retrying will not help. |
| 404 | `not_found` | No such run, a run that is not yours, or no such file. Also returned by `/answer` before the first round finishes. | Check the id. For `/answer`, wait and try again. |
| 422 | `invalid_request` | The request failed validation; the message names the field. | Fix the field. See the limits in [limits](limits.md). |
| 429 | `rate_limited` | Too many requests, or too many open event streams. | Wait for the `Retry-After` header (seconds), then retry. |
| 429 | `run_limit` | You hit the daily or concurrent run limit. | Wait for a run to finish or try tomorrow. `Retry-After` is set when known. |
| 503 | `unavailable` | The API is not available right now. | Retry with backoff. |

## Retrying

Safe to retry: reads, `POST /runs/{id}/stop`, and `429 rate_limited` / `503` on any request.
**Not safe to retry blindly:** `POST /runs` after a network failure or a 5xx, because the run may have been accepted.
List your runs before creating another. The Python SDK follows these rules for you, and raises `UnavailableError`
(`unavailable`) when ThinkerWave cannot be reached at all.

Do not retry `invalid_key`, `account_disabled`, `not_invited`, `credit_exhausted`, `not_found` (except for `/answer`),
`invalid_request` or `run_limit` without changing something first.

## Failed runs

A run can start fine and still fail. Then `GET /runs/{id}` shows `status: "failed"` and an `error` sentence. Its event
stream carries `run.error` with a plain sentence when the reason is known, and always ends with
`run.finished` `{"status": "failed", "stop_reason": "failed", …}`. A run interrupted by maintenance also ends with
`run.finished` (`"status": "failed"`). Any answer found before the failure stays available through `/answer`.
