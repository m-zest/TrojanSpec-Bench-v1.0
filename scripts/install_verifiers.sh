#!/usr/bin/env bash
# Install Dafny 4.x, Lean 4 (+ Mathlib cache), Verus, and system Z3 on Linux.
# Idempotent: re-running skips already-installed components.
set -euo pipefail

echo "== System Z3 =="
if ! command -v z3 >/dev/null 2>&1; then
  sudo apt-get update -y && sudo apt-get install -y z3
fi
z3 --version || true

echo "== Dafny (via .NET SDK 8) =="
if ! command -v dafny >/dev/null 2>&1; then
  if ! command -v dotnet >/dev/null 2>&1; then
    wget -q https://packages.microsoft.com/config/ubuntu/22.04/packages-microsoft-prod.deb \
      -O /tmp/packages-microsoft-prod.deb
    sudo dpkg -i /tmp/packages-microsoft-prod.deb
    sudo apt-get update -y && sudo apt-get install -y dotnet-sdk-8.0
  fi
  dotnet tool install -g dafny
  export PATH="$PATH:$HOME/.dotnet/tools"
fi
dafny --version || true

echo "== Lean 4 + Mathlib =="
if ! command -v lean >/dev/null 2>&1; then
  curl -sSf https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh \
    | sh -s -- -y
  # shellcheck disable=SC1090
  source "$HOME/.elan/env"
  elan default leanprover/lean4:stable
fi
lean --version || true

echo "== Verus =="
if [ ! -d "$HOME/verus" ]; then
  git clone --depth 1 https://github.com/verus-lang/verus.git "$HOME/verus"
  ( cd "$HOME/verus" && ./tools/get-z3.sh && . tools/activate && \
    cd source && cargo build --release )
fi

echo
echo "All verifiers attempted. Add to PATH:"
echo '  export PATH="$PATH:$HOME/.dotnet/tools:$HOME/verus/source/target-verus/release"'
