#!/usr/bin/env bash
# Run a single matrix slot (kind, model, slug, [vision_flag]).
# Useful for re-running one cell after a bug fix without redoing the whole matrix.
#
# Usage:
#   ./run_single.sh api     claude-sonnet-4-20250514  sonnet
#   ./run_single.sh api     claude-haiku-4-5-20251001 haiku
#   ./run_single.sh browser claude-sonnet-4-20250514  sonnet          --vision
#   ./run_single.sh browser claude-haiku-4-5-20251001 haiku_vision    --vision
#   ./run_single.sh browser claude-haiku-4-5-20251001 haiku_no_vision --no-vision

set -u

if [ "$#" -lt 3 ]; then
  echo "usage: $0 <api|browser> <model> <slug> [--vision|--no-vision]" >&2
  exit 2
fi

ROOT="$(cd "$(dirname "$0")" && pwd)"
RESULTS="$ROOT/results"
LOG_DIR="$ROOT/results/_logs"
REFLEX_DIR="$ROOT/reflex-admin"
BU_DIR="$ROOT/browser-use-agent"
mkdir -p "$RESULTS" "$LOG_DIR"

: "${ANTHROPIC_API_KEY:?set ANTHROPIC_API_KEY before running}"

KIND="$1"; MODEL="$2"; SLUG="$3"; VFLAG="${4:-}"
TAG="${KIND}_${SLUG}"

stop_reflex() {
  local pids
  pids=$(lsof -ti :3001 -ti :8001 2>/dev/null | sort -u)
  [ -n "$pids" ] && { kill $pids 2>/dev/null || true; sleep 1; kill -9 $pids 2>/dev/null || true; }
  pkill -f "reflex run" 2>/dev/null || true
  pkill -f "reflex_admin" 2>/dev/null || true
  sleep 1
}

start_reflex() {
  (
    cd "$REFLEX_DIR"
    # shellcheck disable=SC1091
    source .venv/bin/activate
    nohup reflex run --env dev > "$LOG_DIR/reflex_${TAG}.log" 2>&1 &
    echo $! > "$LOG_DIR/reflex_${TAG}.pid"
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
      echo "Reflex ready (tag=$TAG) after ${i}s"
      return 0
    fi
    sleep 3
    i=$(( i + 3 ))
  done
  echo "ERROR: Reflex did not come up for tag=$TAG" >&2
  tail -40 "$LOG_DIR/reflex_${TAG}.log" >&2
  return 1
}

verify_clean_state() {
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
assert (read(m, "selected_order") or {}).get("status") == "ordered", "order 98 not clean"
for rid in (0, 49, 292, 293):
    m = post("select_review", {"review_id": rid})
    assert (read(m, "selected_review") or {}).get("status") == "pending", f"review {rid} not clean"
print("state clean")
PY
}

echo
echo "==========================================================="
echo "Run: $TAG (model=$MODEL vision=${VFLAG:-n/a})"
echo "==========================================================="

stop_reflex
start_reflex || exit 1
verify_clean_state || { echo "dirty state; aborting"; stop_reflex; exit 1; }

if [ "$KIND" = "api" ]; then
  (
    cd "$REFLEX_DIR"
    # shellcheck disable=SC1091
    source .venv/bin/activate
    python run_api_agent.py --model "$MODEL" --out "$RESULTS/api_${SLUG}.json"
  ) 2>&1 | tee "$LOG_DIR/api_${SLUG}.log"
else
  (
    cd "$BU_DIR"
    # shellcheck disable=SC1091
    [ -d .venv ] && source .venv/bin/activate
    python run_browser_agent.py --model "$MODEL" "$VFLAG" --out "$RESULTS/browser_${SLUG}.json"
  ) 2>&1 | tee "$LOG_DIR/browser_${SLUG}.log"
fi

stop_reflex

echo "Done: $TAG"
