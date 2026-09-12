#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPO = 'ILoveMyProjects/ZorinShot'
RUNTIME_ITEMS = [
    'app',
    'extension',
    'icons',
    'install.sh',
    'uninstall.sh',
    'README.md',
    'VERSION',
    'CHANGELOG.md',
]


def run(cmd, cwd=None):
    print('+', ' '.join(map(str, cmd)))
    subprocess.run(cmd, cwd=cwd or ROOT, check=True)


def read_version():
    return (ROOT / 'VERSION').read_text(encoding='utf-8').strip()


def detect_repo():
    env_repo = os.environ.get('GITHUB_REPOSITORY', '').strip()
    if env_repo:
        return env_repo
    try:
        url = subprocess.check_output(
            ['git', 'remote', 'get-url', 'origin'], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return ''
    patterns = [
        r'github\.com[:/](?P<repo>[^/]+/[^/]+?)(?:\.git)?$',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group('repo').removesuffix('.git')
    return ''


def changelog_for(version):
    text = (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8')
    start = re.search(rf'^## \[{re.escape(version)}\].*$', text, re.MULTILINE)
    if not start:
        return f'# Zorin Shot {version}\n\nBrak sekcji dla tej wersji w CHANGELOG.md.\n'
    after = text[start.start():]
    next_heading = re.search(r'^## \[', after[start.end() - start.start():], re.MULTILINE)
    if next_heading:
        end = start.end() + next_heading.start()
        return text[start.start():end].strip() + '\n'
    return after.strip() + '\n'


def validate_project(project_root):
    py_files = list((project_root / 'app').glob('*.py'))
    for path in py_files:
        run([sys.executable, '-m', 'py_compile', str(path)], cwd=project_root)

    node = shutil.which('node')
    if node:
        for path in (project_root / 'extension').rglob('*.js'):
            run([node, '--check', str(path)], cwd=project_root)
    else:
        print('warning: node not found; JS syntax validation skipped')

    bash = shutil.which('bash')
    if bash:
        for path in [project_root / 'install.sh', project_root / 'uninstall.sh',
                     project_root / 'app' / 'zorin-shot-first-login.sh']:
            run([bash, '-n', str(path)], cwd=project_root)

    desktop_validate = shutil.which('desktop-file-validate')
    if desktop_validate:
        for path in (project_root / 'app').glob('*.desktop'):
            run([desktop_validate, str(path)], cwd=project_root)
    else:
        print('warning: desktop-file-validate not found; desktop entry validation skipped')

    schema_dir = project_root / 'extension' / 'zorin-shot@local' / 'schemas'
    compiler = shutil.which('glib-compile-schemas')
    if compiler:
        run([compiler, '--strict', str(schema_dir)], cwd=project_root)
    else:
        import xml.etree.ElementTree as ET
        for path in schema_dir.glob('*.xml'):
            ET.parse(path)
        print('warning: glib-compile-schemas not found; XML parsed, full GSettings validation skipped')

    for path in project_root.rglob('*.json'):
        json.loads(path.read_text(encoding='utf-8'))


def create_zip(source_dir, zip_path, top_name):
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(source_dir.rglob('*')):
            if path.is_dir() or '__pycache__' in path.parts or path.name.endswith('.pyc'):
                continue
            rel = path.relative_to(source_dir)
            arcname = Path(top_name) / rel
            info = zipfile.ZipInfo.from_file(path, str(arcname))
            # Preserve executable bit for scripts when unpacked with common ZIP tools.
            if os.access(path, os.X_OK):
                info.external_attr = (0o100755 << 16)
            with path.open('rb') as handle:
                archive.writestr(info, handle.read(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def main():
    parser = argparse.ArgumentParser(description='Build a GitHub-ready Zorin Shot release package')
    parser.add_argument('--version', default=read_version())
    parser.add_argument('--repo', default=detect_repo() or DEFAULT_REPO, help='GitHub owner/repository; auto-detected in GitHub Actions')
    parser.add_argument('--out', default=str(ROOT / 'dist'))
    args = parser.parse_args()

    version = args.version.strip().lstrip('vV')
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?', version):
        raise SystemExit(f'Invalid semantic version: {version}')
    if read_version() != version:
        raise SystemExit(f'VERSION contains {read_version()}, but build requested {version}')
    if not args.repo or '/' not in args.repo:
        raise SystemExit('GitHub repository is required, e.g. OWNER/zorin-shot. In GitHub Actions it is detected automatically.')

    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob('zorin-shot-*.zip'):
        old.unlink()

    with tempfile.TemporaryDirectory(prefix='zorin-shot-build-') as tmp:
        stage = Path(tmp) / 'runtime'
        stage.mkdir()
        for item in RUNTIME_ITEMS:
            src = ROOT / item
            dst = stage / item
            if src.is_dir():
                shutil.copytree(src, dst, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            else:
                shutil.copy2(src, dst)

        build_info = {
            'version': version,
            'github_repo': args.repo,
            'build_channel': 'github-release',
            'asset_pattern': 'zorin-shot-{version}.zip',
        }
        (stage / 'app' / 'build-info.json').write_text(
            json.dumps(build_info, indent=2, ensure_ascii=False) + '\n', encoding='utf-8'
        )
        (stage / 'VERSION').write_text(version + '\n', encoding='utf-8')

        metadata_path = stage / 'extension' / 'zorin-shot@local' / 'metadata.json'
        metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
        metadata['version-name'] = version
        metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

        validate_project(stage)

        asset_name = f'zorin-shot-{version}.zip'
        zip_path = out_dir / asset_name
        create_zip(stage, zip_path, f'zorin-shot-{version}')

    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    (out_dir / 'SHA256SUMS').write_text(f'{digest}  {zip_path.name}\n', encoding='utf-8')
    (out_dir / 'RELEASE_NOTES.md').write_text(changelog_for(version), encoding='utf-8')

    print(f'Built: {zip_path}')
    print(f'SHA256: {digest}')
    print(f'GitHub repo embedded in updater: {args.repo}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
