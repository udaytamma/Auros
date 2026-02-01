#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"

if command -v curl >/dev/null 2>&1; then
  if curl -fsS "${BASE_URL}/api/tags" >/dev/null; then
    echo "Ollama OK at ${BASE_URL}"
    exit 0
  fi
fi

echo "Ollama not reachable at ${BASE_URL}"
exit 1
