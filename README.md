# Browser agent vs API agent benchmark

Two ways to solve the same admin task, measured head-to-head:

- **Browser-use agent** — an LLM driving a real browser through the UI.
- **Structured-API agent** — an LLM calling typed HTTP tools that back the same app.

Both target a Reflex port of the react-admin "Posters Galore" demo, so the comparison is **one app, two interfaces** — not two different apps.

## The task

"A customer named Smith has complained about a recent order. Find the Smith with the most orders, accept all their pending reviews, and mark their most-recent ordered order as delivered."

Validated against `expected_outcome.json`:

| | |
| --- | --- |
| Customer | Gary Smith (ID 421) |
| Order to mark delivered | #98 (ref `5WUJSYV5`) |
| Reviews to accept | IDs 0, 49, 292, 293 |

Data is pinned in `seed.json` (900 customers, 600 orders, 324 reviews).

## Results

n=1 per configuration; see [Limitations and caveats](#limitations-and-caveats) for important context. Results in `results/`.

| Run | Model | Vision | Time | Reasoning units | Input tokens | Output tokens | Cache read | Outcome |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| API agent | Sonnet 4 | n/a | 17.07 s | 8 tool calls (~14 HTTP requests) | 12,119 | 931 | n/a | ✅ correct |
| API agent | Haiku 4.5 | n/a | 8.38 s | 8 tool calls (~14 HTTP requests) | 9,853 | 858 | n/a | ✅ correct |
| Browser agent | Sonnet 4 | yes | 601.64 s | 34 LLM cycles | 299,494 | 23,793 | 332,032 | ✅ correct |
| Browser agent | Haiku 4.5 | yes | 87.75 s | 1 LLM cycle | 2,390 | 614 | 0 | ❌ no final result |
| Browser agent | Haiku 4.5 | no | 92.96 s | 3 LLM cycles | 66 | 2,290 | 30,732 | ❌ no final result |

**Reasoning units are not directly comparable across rows.** An API tool call is one Anthropic request — but each tool maps to 1–3 HTTP requests against the Reflex backend (see `run_api_agent.py`). A browser-agent "LLM cycle" is one screenshot/DOM-reason-act loop in browser-use. For dollar-cost comparison, look at input/output tokens.

## Repo layout

```
benchmark/
├── seed.json                    pinned dataset (shared)
├── expected_outcome.json        task success criteria
├── reflex-admin/                Reflex port of Posters Galore
│   ├── reflex_admin/
│   │   ├── reflex_admin.py      app + page routes
│   │   ├── state.py             Reflex state — UI handlers (also serve as API endpoints via the plugin)
│   │   ├── pages/               customers, orders, reviews
│   │   └── data.py              in-memory datastore over seed.json
│   ├── run_api_agent.py         API agent runner (tool-use)
│   ├── rxconfig.py              rxe.Config + EventHandlerAPIPlugin
│   └── requirements.txt
├── browser-use-agent/
│   ├── run_browser_agent.py     browser-use runner w/ token counting
│   ├── pyproject.toml
│   └── .env.example             copy to .env, set ANTHROPIC_API_KEY
└── results/                     benchmark output JSONs
```

### How the API is generated

`rxe.EventHandlerAPIPlugin` (configured in `rxconfig.py`) auto-generates an HTTP endpoint for every event handler on the State — `set_customers_query`, `load_order`, `accept_review`, etc. There is no API-specific code in `reflex_admin/state.py`: the same handlers that drive the UI also serve the API. This is the point of the benchmark — measuring an agent against Reflex's "free" API surface, not a hand-shaped REST layer.

Responses stream as NDJSON state deltas, including recomputed dependent computed vars (`customer_rows`, `order_rows`, `selected_order`, etc.). The agent's REST-shaped tool surface (`list_customers`, `update_order`, etc.) is mapped in `run_api_agent.py` to handler sequences — e.g. `update_order` is `load_order` → `set_order_status_draft` → `save_order_status`, mirroring the order detail page's UI flow.

The plugin is part of `reflex-enterprise` and requires `rxe.App()` / `rxe.Config()`.

## Running

### 1. Prereqs

- Python 3.12
- Node.js + `bun` (`npm install -g bun`) — Reflex needs `bun` for its dev server
- `ANTHROPIC_API_KEY` in `browser-use-agent/.env` (copy from `.env.example`)

### 2. Start the Reflex app

```bash
cd reflex-admin
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
reflex login             # one-time, for reflex-enterprise
reflex init              # only first time
reflex run               # frontend :3001, backend :8001
```

This serves:
- UI → `http://localhost:3001` (for the browser-use agent)
- API → `http://localhost:8001/_reflex/event/...` (for the API agent)
- OpenAPI spec → `http://localhost:8001/_reflex/events/openapi.yaml`

### 3. Run an agent

**API agent:**

```bash
cd reflex-admin
source .venv/bin/activate
export ANTHROPIC_API_KEY=...
python run_api_agent.py --model claude-sonnet-4-20250514 --out ../results/api_sonnet.json
python run_api_agent.py --model claude-haiku-4-5-20251001 --out ../results/api_haiku.json
```

**Browser-use agent:**

```bash
cd browser-use-agent
uv sync          # or: pip install -r requirements.txt
uv run python run_browser_agent.py --model claude-sonnet-4-20250514  --vision    --out ../results/browser_sonnet.json
uv run python run_browser_agent.py --model claude-haiku-4-5-20251001 --vision    --out ../results/browser_haiku_vision.json
uv run python run_browser_agent.py --model claude-haiku-4-5-20251001 --no-vision --out ../results/browser_haiku_no_vision.json
```

Both Haiku browser runs in `results/` failed to produce a final answer (`final_result: null`) without raising an exception (`error: null`) — browser-use's agent loop exited cleanly after 1 cycle (vision) or 3 cycles (no-vision) without completing the task. The runner catches and records exceptions in the `error` field, but in these runs there was no exception to catch. Re-running may produce different outcomes; current results are kept as-is rather than retried-until-success.

### 4. Full matrix convenience script

```bash
./run_matrix.sh    # starts Reflex fresh per-run (seed reload), writes to ./results/
```

The script **restarts Reflex before every run** — the in-memory datastore mutates during a run (reviews accepted, orders updated), so without a restart the next agent sees dirty state. It also verifies clean state before each run (order 98 `ordered`, reviews 0/49/292/293 `pending`) and aborts that run if dirty.

## What gets measured

Per run, the result JSON contains:

- `model`
- `elapsed_seconds` — wall time
- `input_tokens`, `output_tokens`, `total_tokens`
- `cache_read_tokens`, `cache_creation_tokens` (browser-use)
- `tool_calls` (API) or `llm_calls` (browser-use)
- `final_answer` / `final_result`
- `error` (browser-use only — records failures)

`total_tokens` is **`input_tokens + output_tokens` only** — it does **not** include `cache_read_tokens`. The browser-use Sonnet run, for example, reports `total_tokens: 323,287` while having `cache_read_tokens: 332,032`; the model actually processed ~631 k tokens of input including cached prefixes. For raw cost-of-prompt comparisons, sum `input_tokens + cache_read_tokens` instead.

The browser-use script counts tokens by subclassing `ChatAnthropic.ainvoke` and accumulating `ChatInvokeCompletion.usage` per call; browser-use's own `AgentHistoryList` does not surface usage.

## Limitations and caveats

Read these before drawing conclusions from the numbers.

- **n=1 per configuration.** Each row in the results table is a single trial. LLMs are non-deterministic; latency in particular has wide run-to-run spread. Median + range across multiple trials is the right way to compare; this repo doesn't have that yet.
- **The API agent's tool surface is hand-written.** `EventHandlerAPIPlugin` auto-generates the HTTP endpoints with no work on the app side — that part is genuinely zero-overhead. But `run_api_agent.py` defines a REST-shaped tool surface (`list_customers`, `update_order`, ...) and maps each tool to a sequence of raw-handler POSTs (e.g. `update_order` → `load_order` + `set_order_status_draft` + `save_order_status`). That mapping is human-authored. It could plausibly be auto-generated from the plugin's OpenAPI spec, or skipped entirely by exposing the raw handlers to the agent — neither variant is implemented here.
- **Tool calls and LLM cycles are different units.** The API agent's `tool_calls: 8` is 8 Anthropic requests; on the wire, those expand to ~14 HTTP requests against Reflex (the multi-step handler sequences above). The browser agent's `llm_calls: 34` is 34 screenshot-reason-act loops in browser-use. Don't compare these counts directly. Token totals are the more honest cost metric.
- **Single task.** "Find Smith with the most orders, accept their pending reviews, mark their latest ordered order as delivered" is one workflow on one app. Conclusions about agent strategies in general should not lean on this dataset.
- **Cache reads are not in `total_tokens`.** See "What gets measured" for the formula. Side-by-side comparison of `total_tokens` understates browser-agent input volume substantially.
- **Two of five runs failed.** Both Haiku browser variants returned `final_result: null` with no exception. Counting them as data points (not errors) is a deliberate choice — the runs completed without crashing — but neither row should be read as "Haiku can't do this task," only as "Haiku didn't do this task in this single attempt."

## Notes

- Reflex defaults (frontend :3000, backend :8000) are overridden to `:3001/:8001` so the upstream react-admin demo (if you set it up) can run on `:8000` side-by-side.
- `ANTHROPIC_API_KEY` with a 10 k input-tokens/min limit will make browser-use runs slow due to retries — expected.
- The Reflex app's in-memory data is not persisted between restarts; re-run after reloading `seed.json` to reset.

## Reproducing the react-admin baseline (optional)

The Reflex app in this repo is a port of [marmelab/react-admin](https://github.com/marmelab/react-admin)'s "Posters Galore" demo (`examples/demo`). The benchmark itself does not need react-admin — it targets the Reflex port at `:3001`/`:8001`. To stand the original demo up against the same pinned dataset, see [`react-admin-setup/README.md`](react-admin-setup/README.md): clone upstream, drop in `seed.json`, apply `data-generator.patch`, run `make run-demo`.
