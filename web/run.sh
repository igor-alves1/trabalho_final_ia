#!/usr/bin/env bash
# Sobe backend (porta 8000) + frontend Vite (porta 5173).
# Uso: bash web/run.sh
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

CONDA_ENV="${CONDA_ENV:-venv}"

echo "==> Iniciando backend (conda env: $CONDA_ENV) na porta 8000..."
conda run --no-capture-output -n "$CONDA_ENV" python web/backend/server.py &
BACKEND_PID=$!
trap "echo; echo 'Encerrando...'; kill $BACKEND_PID 2>/dev/null" EXIT

sleep 3

echo "==> Iniciando frontend (Vite) na porta 5173..."
cd web/frontend
if [ ! -d node_modules ]; then
  echo "    Instalando dependências do npm (primeira vez)..."
  npm install
fi
npm run dev
