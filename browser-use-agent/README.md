# browser-use-agent

Runs a browser-use agent against the Reflex port of Posters Galore (`http://localhost:3001` — see `../reflex-admin`).

## Setup

```bash
uv sync
# or: python -m venv .venv && source .venv/bin/activate && pip install -e .
```

Copy `.env.example` to `.env` and set `ANTHROPIC_API_KEY`.

## Run

```bash
uv run python run_browser_agent.py --model claude-sonnet-4-20250514  --vision    --out ../results/browser_sonnet.json
uv run python run_browser_agent.py --model claude-haiku-4-5-20251001 --vision    --out ../results/browser_haiku_vision.json
uv run python run_browser_agent.py --model claude-haiku-4-5-20251001 --no-vision --out ../results/browser_haiku_no_vision.json
```

The `--vision`/`--no-vision` flag picks between browser-use's screenshot+DOM prompt and its DOM-only prompt. File names match the matrix script's outputs.

## Token counting

`TokenCountingChatAnthropic` subclasses `browser_use.llm.ChatAnthropic.ainvoke` and accumulates per-call usage from `ChatInvokeCompletion.usage`. browser-use's own `AgentHistoryList` does not surface usage, so intercepting at the LLM layer is the only reliable path. The result JSON includes `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_creation_tokens`, and a `per_call` breakdown.
