"""Browser-use agent runner.

Targets the Reflex-ported Posters Galore UI on http://localhost:3001 (not the
react-admin demo on 8000) so the comparison is one app, two interfaces.

Wraps ChatAnthropic to accumulate per-call input/output tokens — browser-use
does not surface usage in AgentHistoryList, so we intercept at the LLM layer.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from dataclasses import dataclass, field

from dotenv import load_dotenv

from browser_use import Agent
from browser_use.llm import ChatAnthropic
from browser_use.llm.views import ChatInvokeCompletion

load_dotenv()


TASK = """
Go to http://localhost:3001.
If there is a login screen, log in with username "demo" and password "demo".

Then complete these steps:

1. Click "Customers" in the left sidebar menu.
2. In the search box, type "Smith" and wait for results.
3. Look at the results. Find the customer with the most orders (look at the "Orders" column). It should be Gary Smith with 8 orders. Click on Gary Smith.
4. Note Gary Smith's customer ID from the URL or page.
5. Click "Orders" in the left sidebar menu.
6. You should see tabs at the top: "Ordered", "Delivered", "Cancelled". Make sure the "Ordered" tab is selected.
7. Search for "Gary Smith" in the orders search box to filter to his orders.
8. Find the most recent order (latest date) for Gary Smith that has status "ordered". Note the order reference.
9. Click "Reviews" in the left sidebar menu.
10. Use the status filter dropdown at the top and select "pending" to show only pending reviews.
11. Scroll through ALL pending reviews and find every review by Gary Smith. There should be about 4 pending reviews by Gary Smith. For each one, click the "View" button on the row to open the detail panel on the right, then click the "Accept" button. After accepting, the review will disappear from the pending list. Repeat for every Gary Smith pending review until there are no more.
12. After accepting ALL of Gary Smith's pending reviews, click "Orders" in the left sidebar.
13. Search for "Gary Smith" again to find his orders. Click on the order with reference matching the one from step 8.
14. On the order detail page, click the Status dropdown, select "delivered", then click the "Save" button.

When done, report:
- Customer name
- Order reference you changed to delivered
- Exact number of reviews you accepted (should be about 4)
"""


@dataclass
class UsageTotals:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    per_call: list[dict] = field(default_factory=list)


@dataclass
class TokenCountingChatAnthropic(ChatAnthropic):
    """ChatAnthropic that accumulates per-call token usage.

    Attaches a `UsageTotals` instance at `self._usage_totals`. Mirrors the
    spirit of a LangChain callback, but hooks into browser-use's own LLM
    interface since browser-use doesn't use LangChain handlers directly.
    """

    def __post_init__(self):
        self._usage_totals = UsageTotals()

    def _totals(self) -> UsageTotals:
        t = getattr(self, "_usage_totals", None)
        if t is None:
            t = UsageTotals()
            self._usage_totals = t
        return t

    async def ainvoke(self, messages, output_format=None, **kwargs):  # type: ignore[override]
        result: ChatInvokeCompletion = await super().ainvoke(messages, output_format, **kwargs)
        u = result.usage
        totals = self._totals()
        totals.calls += 1
        if u is not None:
            # prompt_tokens in browser-use = input + cache_read (see _get_usage).
            # We record raw Anthropic numbers for a faithful benchmark.
            raw_input = (u.prompt_tokens or 0) - (u.prompt_cached_tokens or 0)
            totals.input_tokens += max(raw_input, 0)
            totals.output_tokens += u.completion_tokens or 0
            totals.cache_read_tokens += u.prompt_cached_tokens or 0
            totals.cache_creation_tokens += u.prompt_cache_creation_tokens or 0
            totals.per_call.append(
                {
                    "input": max(raw_input, 0),
                    "output": u.completion_tokens or 0,
                    "cache_read": u.prompt_cached_tokens or 0,
                    "cache_creation": u.prompt_cache_creation_tokens or 0,
                }
            )
        return result


async def run_trial(model: str, out_path: str, use_vision: bool):
    llm = TokenCountingChatAnthropic(
        model=model,
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    )

    agent = Agent(task=TASK, llm=llm, use_vision=use_vision)

    start = time.time()
    error = None
    final = None
    try:
        result = await agent.run()
        final = result.final_result()
    except Exception as exc:  # noqa: BLE001 — log any failure as a data point
        error = f"{type(exc).__name__}: {exc}"
    elapsed = time.time() - start

    totals = llm._totals()
    metrics = {
        "model": model,
        "use_vision": use_vision,
        "elapsed_seconds": round(elapsed, 2),
        "llm_calls": totals.calls,
        "input_tokens": totals.input_tokens,
        "output_tokens": totals.output_tokens,
        "cache_read_tokens": totals.cache_read_tokens,
        "cache_creation_tokens": totals.cache_creation_tokens,
        "total_tokens": totals.input_tokens + totals.output_tokens,
        "per_call": totals.per_call,
        "error": error,
        "final_result": final,
    }

    with open(out_path, "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"Done in {elapsed:.1f}s")
    print(
        f"LLM calls: {totals.calls} | input {totals.input_tokens} | "
        f"output {totals.output_tokens} | cache_read {totals.cache_read_tokens}"
    )
    if error:
        print(f"ERROR: {error}")
    else:
        print(final)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--model",
        default="claude-sonnet-4-20250514",
        help="Anthropic model id (e.g. claude-sonnet-4-20250514, claude-haiku-4-5-20251001)",
    )
    ap.add_argument(
        "--out",
        default=None,
        help="Output JSON path (default: browser_use_<model-slug>.json)",
    )
    ap.add_argument(
        "--vision",
        dest="vision",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Toggle vision mode. --no-vision runs in text-only DOM mode.",
    )
    args = ap.parse_args()
    suffix = "" if args.vision else "_no_vision"
    out = args.out or f"browser_use_{args.model.replace('/', '-')}{suffix}.json"
    asyncio.run(run_trial(args.model, out, args.vision))


if __name__ == "__main__":
    main()
