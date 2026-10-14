# Command line: `tw`

```bash
pip install thinkerwave
export THINKERWAVE_API_KEY=tw_live_…
```

Instead of the environment variable you can run `tw login`, which asks for the key (input is hidden) and saves it to
`~/.config/thinkerwave/config.toml` (or `$XDG_CONFIG_HOME/thinkerwave/config.toml`) with owner-only permissions.
The environment variable wins if both are set.

## Commands

| Command | What it does |
|---|---|
| `tw login` | Store an API key. |
| `tw me` | Your plan and today's usage. |
| `tw run "problem" [options]` | Start a run. |
| `tw runs` | Your recent runs. |
| `tw status ID` | One line: status, round, best score, why it stopped. |
| `tw watch ID` | Follow a run live. |
| `tw answer ID [--json]` | The best answer so far, with confidence and tagged findings. |
| `tw rounds ID` | One line per finished round. |
| `tw files ID` | Files the run produced. |
| `tw get ID PATH [-o FILE]` | Download one produced file. |
| `tw stop ID` | Stop a run. |

## `tw run`

```bash
tw run "Should we raise prices 15%, 8%, or hold? 1,200 customers at \$85/month, 3.1% monthly churn." \
  --given "last 8% increase spiked churn to 4.6% for three months" \
  --standard "compare at least three options" \
  --pitfall "do not assume churn is constant" \
  --rounds 6 --watch
```

| Option | Meaning |
|---|---|
| `--given TEXT` | A fact to keep exactly as written. Repeat for more. |
| `--standard TEXT` | What a good answer must do. Repeat for more. |
| `--pitfall TEXT` | A mistake to avoid. Repeat for more. |
| `--rounds N` | Most rounds to run (capped at your plan's limit). |
| `--watch` | Follow the run live, then print the answer. |
| `--json` | Print JSON instead of text. With `--watch`, progress goes to stderr, so stdout is only the JSON answer (`tw run … --watch --json \| jq`). |

Without `--watch`, `tw run` prints the run id and exits. Pick the run up later with `tw watch ID` or `tw answer ID`.

While watching, each line shows the round, the current step (planning, working, checking, rethinking), tools used
so far and the best score:

```
Round 2 of 6 · working · python ×2, web search ×1 · best 5.2
```

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success (for `--watch`, the run completed). |
| 1 | The run failed or was stopped, there was no answer yet, or the API could not be reached. |
| 2 | Bad usage (unknown option, missing argument). |
| 3 | The API key is missing, invalid or revoked. |
| 4 | A rate limit or run limit was hit, or your free runs are used up. |

## Files

`tw files ID` prints `path`, `kind` and size. `tw get ID chart.png` writes `chart.png` into the current directory;
use `-o` to choose another name.
