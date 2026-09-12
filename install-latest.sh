#!/usr/bin/env bash
set -euo pipefail

REPO="ILoveMyProjects/ZorinShot"
BRANCH="master"
MANIFEST_URL="https://raw.githubusercontent.com/${REPO}/${BRANCH}/update.json"
TMP_DIR="$(mktemp -d -t zorin-shot-install-XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

printf '\nZorin Shot — online installer\n\n'

if ! command -v python3 >/dev/null 2>&1; then
  printf 'Error: Python 3 is required.\n' >&2
  exit 2
fi

ROOT_FILE="$TMP_DIR/root-path.txt"

python3 - "$MANIFEST_URL" "$TMP_DIR" "$ROOT_FILE" <<'PY'
import hashlib
import json
import os
import pathlib
import sys
import urllib.request
import zipfile

manifest_url, tmp_dir, root_file = sys.argv[1:]
tmp = pathlib.Path(tmp_dir)
headers = {'User-Agent': 'Zorin-Shot-Online-Installer'}

print('Fetching update manifest...')
with urllib.request.urlopen(urllib.request.Request(manifest_url, headers=headers), timeout=30) as response:
    manifest = json.loads(response.read().decode('utf-8'))

version = str(manifest.get('version_name') or '').strip()
download_url = str(manifest.get('download_url') or '').strip()
expected_sha = str(manifest.get('sha256') or '').strip().lower()

if not version or not download_url or len(expected_sha) != 64:
    raise SystemExit('The update manifest is incomplete or invalid.')

zip_path = tmp / f'zorin-shot-{version}.zip'
print(f'Downloading Zorin Shot {version}...')
with urllib.request.urlopen(urllib.request.Request(download_url, headers=headers), timeout=120) as response, zip_path.open('wb') as out:
    while True:
        chunk = response.read(1024 * 1024)
        if not chunk:
            break
        out.write(chunk)

actual_sha = hashlib.sha256(zip_path.read_bytes()).hexdigest().lower()
if actual_sha != expected_sha:
    raise SystemExit(
        'SHA-256 verification failed.\n'
        f'Expected: {expected_sha}\n'
        f'Actual:   {actual_sha}'
    )
print('SHA-256 verified.')

extract_dir = tmp / 'extracted'
extract_dir.mkdir()
with zipfile.ZipFile(zip_path, 'r') as archive:
    for member in archive.infolist():
        target = (extract_dir / member.filename).resolve()
        if target != extract_dir.resolve() and extract_dir.resolve() not in target.parents:
            raise SystemExit(f'Unsafe path in archive: {member.filename}')
    archive.extractall(extract_dir)

installers = list(extract_dir.glob('*/install.sh'))
if len(installers) != 1:
    raise SystemExit('Could not locate install.sh in the release package.')

installer = installers[0]
os.chmod(installer, installer.stat().st_mode | 0o111)
pathlib.Path(root_file).write_text(str(installer.parent), encoding='utf-8')
print(f'Release package ready: {installer.parent.name}')
PY

PACKAGE_ROOT="$(cat "$ROOT_FILE")"

printf '\nStarting Zorin Shot installer...\n\n'
exec bash "$PACKAGE_ROOT/install.sh"
