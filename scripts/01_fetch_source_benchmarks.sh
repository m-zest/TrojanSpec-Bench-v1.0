#!/usr/bin/env bash
# Fetch the public verification benchmarks TrojanSpec-Bench draws source
# problems from. Each clone is best-effort; a failed/unknown URL is logged
# and skipped so the script never aborts the whole fetch.
set -uo pipefail

cd "$(dirname "$0")/.."
mkdir -p data/raw
cd data/raw

clone() {
  local url="$1" dir="$2"
  if [ -d "$dir/.git" ]; then
    echo ">> updating $dir"
    (cd "$dir" && git pull --ff-only) || echo "!! could not update $dir"
  else
    echo ">> cloning $dir"
    git clone --depth 1 "$url" "$dir" || echo "!! could not clone $url (skipped)"
  fi
}

clone https://github.com/Beneficial-AI-Foundation/fvapps.git                 fvapps
clone https://github.com/sun-wendy/DafnyBench.git                            dafnybench
clone https://github.com/Wenhan-Xu/DafnyComp.git                             dafnycomp
clone https://github.com/Beneficial-AI-Foundation/vericoding-benchmark.git   vericoding
clone https://github.com/sunblaze-ucb/verina.git                             verina
clone https://github.com/cryspen/libcrux.git                                 libcrux

echo
echo "Source benchmarks present in data/raw/:"
ls -1
