#!/usr/bin/env bash
# Phase 14 prerequisites: install everything MutDafny (Amaral et al.,
# arXiv:2511.15403, ICSE 2026) needs, into $HOME/tools/mutdafny.
#
# Idempotent: re-running skips steps that already succeeded.
# Tested on Ubuntu 22.04. Requires sudo for apt + dpkg.
#
# After this script: bash scripts/run_phase14.sh
set -uo pipefail

MUTDAFNY_TOOL=https://github.com/MutDafny/mutdafny.git
MUTDAFNY_PARENT_COMMIT=9766186  # the commit our results were measured against
Z3_URL=https://github.com/dafny-lang/solver-builds/releases/download/snapshot-2023-08-02/z3-4.12.1-x64-ubuntu-20.04-bin.zip
TOOLS=$HOME/tools

say(){ echo; echo "######## $* ########"; }

# ---------------------------------------------------------------- 1. .NET
say "1. Microsoft .NET SDKs (6.0 + 8.0)"
if ! command -v dotnet >/dev/null 2>&1 || ! dotnet --list-sdks 2>/dev/null | grep -q '8\.'; then
  wget -q https://packages.microsoft.com/config/ubuntu/22.04/packages-microsoft-prod.deb \
       -O /tmp/packages-microsoft-prod.deb
  sudo dpkg -i /tmp/packages-microsoft-prod.deb
  sudo apt-get update -y
  sudo apt-get install -y dotnet-sdk-6.0 dotnet-sdk-8.0
  # Fix Ubuntu/MS mixed-install: symlink host + shared into /usr/share/dotnet
  sudo ln -sfn /usr/lib/dotnet/host   /usr/share/dotnet/host
  sudo ln -sfn /usr/lib/dotnet/shared /usr/share/dotnet/shared
  sudo ln -sfn /usr/share/dotnet/dotnet /usr/local/bin/dotnet
fi
dotnet --list-sdks

# ---------------------------------------------------------------- 2. Java
say "2. OpenJDK 21 (Java <=22, per MutDafny README)"
if ! command -v java >/dev/null 2>&1; then
  sudo apt-get install -y openjdk-21-jdk-headless
fi
java -version

# ---------------------------------------------------------------- 3. MutDafny
say "3. Clone + build MutDafny + bundled Dafny fork"
mkdir -p "$TOOLS"
if [ ! -d "$TOOLS/mutdafny" ]; then
  git clone "$MUTDAFNY_TOOL" "$TOOLS/mutdafny"
fi
cd "$TOOLS/mutdafny"
# pin the parent-repo commit our experiment was measured against
git fetch origin
git checkout "$MUTDAFNY_PARENT_COMMIT" 2>/dev/null || true
git submodule update --init --recursive
( cd dafny && make exe )
cd "$TOOLS/mutdafny/mutdafny" && dotnet build
cd "$TOOLS/mutdafny"

# ---------------------------------------------------------------- 4. Z3
say "4. Z3 4.12.1 (specific snapshot MutDafny pins)"
cd "$TOOLS/mutdafny/dafny/Binaries"
if [ ! -x z3 ] || ! ./z3 --version 2>/dev/null | grep -q '4.12.1'; then
  wget -q "$Z3_URL"
  unzip -o z3-4.12.1-x64-ubuntu-20.04-bin.zip
  # the zip contains a single ELF binary named "z3-4.12.1"
  rm -f z3
  mv z3-4.12.1 z3
  chmod 755 z3
fi
./z3 --version
cd - >/dev/null

# ---------------------------------------------------------------- 5. Smoke
say "5. Smoke verify on a tiny Dafny program"
cat > /tmp/_mutdafny_smoke.dfy <<'EOF'
method Inc(n: int) returns (r: int) ensures r == n + 1 { r := n + 1; }
EOF
dotnet "$TOOLS/mutdafny/dafny/Binaries/Dafny.dll" verify /tmp/_mutdafny_smoke.dfy \
  --solver-path "$TOOLS/mutdafny/dafny/Binaries/z3" --allow-warnings \
  | tail -3

say "DONE. MutDafny stack ready at $TOOLS/mutdafny."
echo "  Dafny (Amaral fork): $(dotnet $TOOLS/mutdafny/dafny/Binaries/Dafny.dll --version 2>&1 | head -1)"
echo "  Z3                  : $($TOOLS/mutdafny/dafny/Binaries/z3 --version)"
echo
echo "Next: bash scripts/run_phase14.sh"
