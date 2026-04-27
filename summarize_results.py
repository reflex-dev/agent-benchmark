"""Render the benchmark matrix from `results/*.json` as a markdown table."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def row(label: str, path: Path) -> str:
    if not path.exists():
        return f"| {label} | — | — | — | — | — | — |"
    d = json.loads(path.read_text())
    err = d.get("error")
    if err:
        return f"| {label} | ❌ | — | — | — | — | {err[:60]} |"
    elapsed = d.get("elapsed_seconds", "—")
    inp = d.get("input_tokens", "—")
    out = d.get("output_tokens", "—")
    cache = d.get("cache_read_tokens", 0) or 0
    calls = d.get("tool_calls") or d.get("llm_calls") or "—"
    return f"| {label} | ✅ | {elapsed}s | {inp} | {out} | {cache} | {calls} |"


def main() -> None:
    print("| Run | OK | Elapsed | Input tok | Output tok | Cache read | Calls |")
    print("| --- | --- | --- | --- | --- | --- | --- |")
    for label, fname in [
        ("API · Sonnet", "api_sonnet.json"),
        ("API · Haiku", "api_haiku.json"),
        ("Browser · Sonnet (vision)", "browser_sonnet.json"),
        ("Browser · Haiku (vision)", "browser_haiku_vision.json"),
        ("Browser · Haiku (no-vision)", "browser_haiku_no_vision.json"),
    ]:
        print(row(label, RESULTS / fname))


if __name__ == "__main__":
    main()
