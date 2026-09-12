# Zorin Shot

Zorin Shot is a screenshot tool for **Zorin OS 18 / GNOME Shell 46**. It consists of a GNOME Shell extension, a GTK4 annotation editor, and a settings/update application.

## Features

- Keeps the original GNOME screenshot button unchanged.
- Adds a second **Zorin Shot** button next to the original screenshot button in Quick Settings.
- Uses GNOME's native screenshot chooser for area, window, or screen capture.
- Can assign `Print Screen` to Zorin Shot while keeping `Super + Print Screen` for the original GNOME screenshot / screen-recording panel.
- Includes optional direct full-desktop and active-window capture modes.
- Built-in editor with pen, translucent highlighter, line, arrow, rectangle, ellipse, text, numbered markers, pixelated redaction, crop, move, undo/redo, zoom, clipboard copy, and PNG save.
- Light, dark, and system themes.
- Polish and English application UI. On first installation the language is detected from the desktop locale; it can be changed later in Zorin Shot Settings.
- Built-in update checker and installer with SHA-256 validation.

## Installation

### Quick install

Install the latest published release with one command:

```bash
curl -fsSL https://raw.githubusercontent.com/ILoveMyProjects/ZorinShot/master/install-latest.sh | bash
```

The installer automatically:

- reads the current stable `update.json`;
- downloads the latest Zorin Shot release ZIP;
- verifies its SHA-256 checksum;
- extracts the package safely;
- runs the normal Zorin Shot installer.

After installation, log out and sign back in so GNOME Shell can load the extension. A fresh installation enables the extension for the next login and opens the Zorin Shot settings application once after signing back in. No additional `gnome-extensions enable` or `gnome-extensions prefs` command is required.

### Manual installation

Manual download is only a fallback. Download `zorin-shot-X.Y.Z.zip` from GitHub Releases, extract it, and run `install.sh`.

## Screenshot workflow

The default `native` capture mode opens `Main.screenshotUI` from GNOME Shell 46 and starts in area-selection mode. Zorin Shot does not close Quick Settings before GNOME freezes the current stage, which allows open shell menus to remain visible in the captured scene. After GNOME emits `screenshot-taken`, the resulting PNG is opened directly in the Zorin Shot editor.

## Application language

Repository documentation is maintained in English. The application itself supports:

- English
- Polish

On first installation, Zorin Shot detects the system locale. The language can later be changed in **Zorin Shot → Settings → Language**. The editor and settings window use the selected application language.

## Updates

Release builds contain repository and update-manifest information in `app/build-info.json`.

The updater first downloads the stable manifest:

`https://raw.githubusercontent.com/ILoveMyProjects/ZorinShot/master/update.json`

The manifest contains:

- version number;
- supported GNOME Shell versions;
- direct GitHub Release asset URL;
- SHA-256 checksum;
- GitHub Release URL;
- release changelog.

If the manifest cannot be read, the application automatically falls back to the GitHub Releases API.

When a newer version is available, **Zorin Shot → Updates → Download and install update** downloads the ZIP, verifies SHA-256, extracts it safely, and runs `install.sh --update --no-popup`. User preferences are preserved.

## GitHub Actions release pipeline

The workflow is stored in `.github/workflows/build-release.yml`.

A regular push to `master` or `main` validates and builds the project. A version tag such as `v0.3.11` additionally:

1. verifies that the tag matches `VERSION`;
2. builds `zorin-shot-X.Y.Z.zip`;
3. generates `SHA256SUMS`;
4. generates `RELEASE_NOTES.md`;
5. generates `update.json`;
6. creates or updates the GitHub Release;
7. uploads the ZIP and checksum to the Release;
8. writes the stable `update.json` back to the repository's default branch.

The workflow uses current Node.js 24-compatible GitHub Actions majors to avoid the Node.js 20 deprecation warning on GitHub-hosted runners.

The repository needs **Actions → Workflow permissions → Read and write permissions** so `GITHUB_TOKEN` can update `update.json` on the default branch.

## Releasing a new version

1. Update `VERSION`.
2. Add a matching section to `CHANGELOG.md`.
3. Push the changes to `master`.
4. Create and push the matching tag, for example:

```bash
git tag v0.3.11
git push origin v0.3.11
```

GitHub Actions handles the remaining release steps.

## Local release build

Run:

```bash
./package.sh
```

This uses the same release builder as GitHub Actions and creates the ZIP, checksum, release notes, and update manifest in `dist/`.

## Project structure

- `extension/zorin-shot@local/` — GNOME Shell 46 extension.
- `app/zorin-shot-editor.py` — annotation editor.
- `app/zorin-shot-control.py` — Settings / About / Updates application.
- `app/i18n.py` — English and Polish UI strings.
- `install-online.sh` — one-command online installer that downloads and verifies the latest release.
- `install.sh` — installer and update installer.
- `uninstall.sh` — uninstaller.
- `tools/build_release.py` — release ZIP, SHA-256 and update-manifest builder.
- `package.sh` — local release build helper.
- `update.json.example` — update-manifest example.
- `.github/workflows/build-release.yml` — CI and release workflow.
- `VERSION` — application version.
- `CHANGELOG.md` — release changelog and GitHub Release notes source.

## Runtime dependencies

The installer checks for Python 3, PyGObject, Cairo and GTK4. On Zorin OS 18 the required packages can be installed with:

```bash
sudo apt install python3-gi python3-cairo gir1.2-gtk-4.0
```

## Uninstallation

Run `uninstall.sh` from an extracted project or release package.
