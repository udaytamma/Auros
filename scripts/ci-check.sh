#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT=8008
LOG_FILE="/tmp/auros-ci.log"

cd "$ROOT_DIR"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

source .venv/bin/activate

export DISABLE_SCHEDULER=true

pip install -r requirements.txt -r requirements-dev.txt
pytest tests

pushd ui >/dev/null
export VITE_API_BASE_URL="http://127.0.0.1:${PORT}"
if [[ -n "${API_KEY:-}" ]]; then
  export VITE_API_KEY="${API_KEY}"
fi
npm install
npm run build
popd >/dev/null

uvicorn api.main:app --host 127.0.0.1 --port "$PORT" >"$LOG_FILE" 2>&1 &
PID=$!

cleanup() {
  kill "$PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT

python - <<'PY'
import socket, time, sys
host = "127.0.0.1"
port = 8008
deadline = time.time() + 20
while time.time() < deadline:
    try:
        with socket.create_connection((host, port), timeout=1):
            sys.exit(0)
    except OSError:
        time.sleep(0.5)
print("Server did not start in time", file=sys.stderr)
sys.exit(1)
PY

if [[ -n "${API_KEY:-}" ]]; then
  curl -fsS -H "X-API-Key: ${API_KEY}" "http://127.0.0.1:${PORT}/api" >/dev/null
  curl -fsS -H "X-API-Key: ${API_KEY}" "http://127.0.0.1:${PORT}/health" >/dev/null
else
  curl -fsS "http://127.0.0.1:${PORT}/api" >/dev/null
  curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null
fi
curl -fsS "http://127.0.0.1:${PORT}/" >/dev/null

echo "CI checks passed"
