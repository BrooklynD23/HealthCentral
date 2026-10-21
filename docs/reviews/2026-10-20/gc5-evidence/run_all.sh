#!/usr/bin/env bash
# Hold all three pyslot locks, then run every G-C5 Task 7 measurement. Usage: run_all.sh <worktree-root>
# The NLI model must already be fetched: cd src/backend && python scripts/download_models.py nli
set -u
R="$(cd "${1:?worktree root}" && pwd)"; E="$R/docs/reviews/2026-10-20/gc5-evidence"; V=~/venvs/asclexis-311/bin/python
D=models/nli/nli-deberta-v3-xsmall
cd "$R/src/backend"
run() { echo; echo "\$ $*"; "$@" 2>&1 | grep -v -i -E "warn|^ +(from|print)|Batches:|Loading weights"; }
echo "\$ ls -la $D; du -sb $D; du -ab $D"; ls -la "$D"; du -sb "$D"; du -ab "$D"
echo "\$ sha256sum $D/model.safetensors"; sha256sum "$D/model.safetensors"
echo "\$ grep sha256 ../../config/model_manifest.json | grep 4e4fc"; grep sha256 ../../config/model_manifest.json | grep 4e4fc
echo "\$ grep license $D/README.md"; grep -n license "$D/README.md"
for m in load latency contradiction gate block; do run "$V" "$E/measure.py" "$m"; done
run "$V" "$E/routes_probe.py"
echo; echo "\$ git status --short (repo root)"; git -C "$R" status --short
