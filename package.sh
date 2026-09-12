#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
python3 tools/build_release.py \
  --repo "${GITHUB_REPOSITORY:-ILoveMyProjects/ZorinShot}" \
  --default-branch "${DEFAULT_BRANCH:-master}"
echo "Built files are in: $ROOT/dist"
