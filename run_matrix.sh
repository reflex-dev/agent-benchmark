#!/usr/bin/env bash
# Run the benchmark matrix.
#
# Per-run lifecycle:
#   1. Kill any leftover Reflex processes.
#   2. Start `reflex run` from scratch so the in-memory datastore reloads
#      from seed.json (the app holds state in a global dict; a full restart
#      is the only way to guarantee a clean slate).
#   3. Wait until the API answers.
#   4. Run the agent.
#   5. Kill Reflex.
#
# Matrix:
#   - API      × Sonnet
#   - API      × Haiku
#   - Browser  × Sonnet (vision)
#   - Browser  × Haiku  (vision)      — expected pydantic failure, kept as data
#   - Browser  × Haiku  (no-vision)
#
# Requires: ANTHROPIC_API_KEY in env, .venv populated in both subdirs.

set -u

ROOT="$(cd "$(dirname "$0")" && pwd)"
RESULTS="$ROOT/results"
REFLEX_DIR="$ROOT/reflex-admin"
BU_DIR="$ROOT/browser-use-agent"
LOG_DIR="$ROOT/results/_logs"
mkdir -p "$RESULTS" "$LOG_DIR"

: "${ANTHROPIC_API_KEY:?set ANTHROPIC_API_KEY before running}"

stop_reflex() {
  # Kill anything holding 3001/8001, then anything named reflex or the bun/node frontend.
  local pids
  pids=$(lsof -ti :3001 -ti :8001 2>/dev/null | sort -u)
  if [ -n "$pids" ]; then
    kill $pids 2>/dev/null || true
    sleep 1
    kill -9 $pids 2>/dev/null || true
  fi
  pkill -f "reflex run"      2>/dev/null || true
  pkill -f "reflex_admin"    2>/dev/null || true
  sleep 1
}

start_reflex() {
  local tag="$1"
  (
    cd "$REFLEX_DIR"
    # shellcheck disable=SC1091
    source .venv/bin/activate
    nohup reflex run --env dev > "$LOG_DIR/reflex_${tag}.log" 2>&1 &
    echo $! > "$LOG_DIR/reflex_${tag}.pid"
  )
  # The plugin-generated endpoints are POST-only; probe the always-on
  # /_reflex/retrieve_state endpoint to confirm the backend is serving.
  local probe_token
  probe_token=$(python3 -c 'import uuid; print(uuid.uuid4())')
  local i=0
  while (( i < 120 )); do
    if curl -sSf -X POST "http://localhost:8001/_reflex/retrieve_state" \
        -H "Authorization: Bearer $probe_token" >/dev/null 2>&1 \
      && curl -sSf "http://localhost:3001/" >/dev/null 2>&1; then
      echo "Reflex ready (tag=$tag) after ${i}s"
      return 0
    fi
    sleep 3
    i=$(( i + 3 ))
  done
  echo "ERROR: Reflex did not come up for tag=$tag" >&2
  tail -40 "$LOG_DIR/reflex_${tag}.log" >&2
  return 1
}

verify_clean_state() {
  # Fail-loud: if order 98 isn't "ordered" or the 4 reviews aren't "pending",
  # the datastore was not reset.
  python3 - <<'PY' || return 1
import json, uuid, urllib.request

STATE = "reflex_admin___state____state"
TOKEN = str(uuid.uuid4())
SUFFIX = "_rx_state_"

def post(handler, args=None):
    req = urllib.request.Request(
        f"http://localhost:8001/_reflex/event/{STATE}/{handler}",
        data=json.dumps(args or {}).encode(),
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    body = urllib.request.urlopen(req).read().decode()
    merged = {}
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        delta = json.loads(line)
        for path, sd in delta.items():
            if isinstance(sd, dict):
                merged.setdefault(path, {}).update(sd)
    return merged

def read(merged, var):
    key = var + SUFFIX
    for sd in merged.values():
        if key in sd:
            return sd[key]
    return None

m = post("load_order", {"order_id": 98})
order = read(m, "selected_order") or {}
assert order.get("status") == "ordered", f"order 98 not clean: {order.get('status')}"
for rid in (0, 49, 292, 293):
    m = post("select_review", {"review_id": rid})
    rev = read(m, "selected_review") or {}
    assert rev.get("status") == "pending", f"review {rid} not clean: {rev.get('status')}"
print("state clean")
PY
}

run_api_agent() {
  local model="$1" slug="$2"
  (
    cd "$REFLEX_DIR"
    # shellcheck disable=SC1091
    source .venv/bin/activate
    python run_api_agent.py --model "$model" --out "$RESULTS/api_${slug}.json"
  ) 2>&1 | tee "$LOG_DIR/api_${slug}.log"
}

run_browser_agent() {
  local model="$1" slug="$2" vision_flag="$3"
  (
    cd "$BU_DIR"
    # shellcheck disable=SC1091
    [ -d .venv ] && source .venv/bin/activate
    python run_browser_agent.py --model "$model" "$vision_flag" \
      --out "$RESULTS/browser_${slug}.json"
  ) 2>&1 | tee "$LOG_DIR/browser_${slug}.log"
}

one_run() {
  local kind="$1" model="$2" slug="$3" vision_flag="${4:-}"
  local tag="${kind}_${slug}"

  echo
  echo "==========================================================="
  echo "Run: $tag (model=$model vision=${vision_flag:-n/a})"
  echo "==========================================================="

  stop_reflex
  start_reflex "$tag" || { echo "skipping $tag (reflex failed to start)"; return; }
  verify_clean_state || { echo "skipping $tag (dirty state)"; stop_reflex; return; }

  case "$kind" in
    api)     run_api_agent "$model" "$slug" ;;
    browser) run_browser_agent "$model" "$slug" "$vision_flag" ;;
  esac

  stop_reflex
}

one_run api     "claude-sonnet-4-20250514"     sonnet
one_run api     "claude-haiku-4-5-20251001"    haiku
one_run browser "claude-sonnet-4-20250514"     sonnet           --vision
one_run browser "claude-haiku-4-5-20251001"    haiku_vision     --vision
one_run browser "claude-haiku-4-5-20251001"    haiku_no_vision  --no-vision

echo
echo "All runs attempted. Results:"
ls -la "$RESULTS/"
