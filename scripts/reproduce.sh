#!/usr/bin/env bash
# Reproduce the full TrojanSpec-Bench pipeline on a fresh server from a clone.
#
#   git clone https://github.com/m-zest/TrojanSpec-Bench-v1.0.git
#   cd TrojanSpec-Bench-v1.0
#   git checkout claude/professional-search-interface-MCp22
#   bash scripts/reproduce.sh            # does everything below, step by step
#
# Steps are idempotent and each prints a banner. Read STATUS.md first.
set -uo pipefail
cd "$(dirname "$0")/.."
ROOT=$(pwd)
say(){ echo; echo "######## $* ########"; }

say "1. Python venv + package"
python3 -m venv venv
./venv/bin/pip -q install --upgrade pip wheel
./venv/bin/pip -q install -e ".[dev,review]"
./venv/bin/python -m pytest tests/ -q || { echo "tests failed"; exit 1; }

say "2. .env (Fireworks optional; local Ollama is the default backend)"
[ -f .env ] || cp .env.example .env
echo "Edit .env if using Fireworks (FIREWORKS_API_KEY). Local Ollama needs no key."

say "3. Local Ollama backend (primary)"
command -v ollama >/dev/null || curl -fsSL https://ollama.com/install.sh | sh
(pgrep -f 'ollama serve' >/dev/null) || (nohup ollama serve >/tmp/ollama.log 2>&1 & sleep 5)
ollama pull qwen2.5:32b
ollama pull qwen2.5-coder:32b
ollama pull deepseek-coder-v2:16b

say "4. Verifiers (Dafny + Lean + Z3; Verus optional/often fails to build)"
bash scripts/install_verifiers.sh || echo "WARN some verifiers missing (see STATUS.md)"
export PATH="$PATH:$HOME/.dotnet/tools:$HOME/.elan/bin"

say "5. Lean + Mathlib template (one-time, ~20-40 min: clone+cache+build)"
TPL="$HOME/lean-project-template"
if [ ! -f "$TPL/.mathlib_ready" ]; then
  ( cd "$HOME" && rm -rf lean-project-template && lake new lean-project-template math ) \
   && ( cd "$TPL" && lake exe cache get ) \
   && ( cd "$TPL" && lake build ) && touch "$TPL/.mathlib_ready"
fi
export TROJANSPEC_LEAN_TEMPLATE="$TPL"

say "6. Restore the preserved v1 dataset (negative-result / HF release)"
[ -f data/v1_backup_*.tar.gz ] && tar -xzf data/v1_backup_*.tar.gz 2>/dev/null || true

say "7. Run the pipeline (sanity-gated). See scripts/run_phaseA3.sh"
echo "   bash scripts/run_phaseA3.sh   # sanity>=40% -> regen 1500+300 -> Phase7 -> report"
echo "   tail -f /tmp/phaseA3.log"
echo
echo "Manual equivalents:"
echo "   ./venv/bin/python scripts/02_generate_triples.py --sanity --out-dir data/triples_sanity --concurrency 4"
echo "   ./venv/bin/python scripts/04_validate_witnesses.py --data-dir data/triples_sanity --report-json data/sanity_report.json"
echo "   ./venv/bin/python scripts/05_specguard.py <triple.json> --no-monitor"
say "DONE - read STATUS.md for current numbers and the open issue"
