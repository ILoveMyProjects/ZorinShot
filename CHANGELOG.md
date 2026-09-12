# Changelog

All notable Zorin Shot changes are documented here. The section matching a release tag is automatically used as the GitHub Release description and is displayed in the application's **Updates** tab.

## [0.3.10] - 2026-09-12

### Added
- The update manifest now includes the full Markdown changelog in `changelog_markdown` while keeping the compact changelog list for backward compatibility.
- The Updates tab renders release notes as formatted text with headings, bullets, bold text and inline code instead of showing raw Markdown syntax.

### Changed
- `README.md`, `TESTING.md`, and the repository changelog are maintained in English. The application UI itself remains localized independently and still follows the detected/selected English or Polish language.
- The changelog panel in the Updates tab now expands vertically with the window instead of leaving unused space below it.
- GitHub Actions now uses Node.js 24-compatible action majors (`actions/checkout@v7` and `actions/upload-artifact@v7`).

### Fixed
- Removed the GitHub Actions Node.js 20 deprecation warning caused by older `checkout` and `upload-artifact` action majors.

## [0.3.9] - 2026-09-12

### Added
- GitHub Actions generates a stable `update.json` with the version, direct package URL, SHA-256, GNOME 46 compatibility and changelog data.
- A `vX.Y.Z` tag creates or updates the GitHub Release, publishes the ZIP and `SHA256SUMS`, and then writes `update.json` to the default branch.
- Added `package.sh` to build the same release package locally as GitHub Actions.
- Added `update.json.example` documenting the update-manifest format.

### Changed
- The updater checks stable `update.json` first, following the same model as ZorinTinyResourceMonitor.
- GitHub Releases API remains an automatic fallback when the manifest is temporarily unavailable.
- Release packages embed the repository, default branch and manifest URL in `build-info.json`.

### Security
- The updater requires a valid SHA-256 from the manifest or `SHA256SUMS` before launching the installer.
- The manifest is validated for UUID, version, HTTPS URL and GNOME Shell 46 compatibility.

## [0.3.8] - 2026-09-12

### Fixed
- Removed the incorrect coupling between the right sidebar position and the vertically centered screenshot. **Tools / Tool options / Elements / Image details** are anchored at the top of the sidebar from the first frame, regardless of screenshot size or zoom.
- Fixed delayed sidebar appearance when opening the editor.
- A small centered screenshot no longer moves Tools toward the center of the window; zooming no longer changes the sidebar's vertical position.

## [0.3.7] - 2026-09-12

### Fixed
- Removed the artificial 18 px top gap from the right panel.
- Unified the entire right-column background, including its scroll viewport and the space underneath section headings.
- Section headings use a transparent background and inherit the same sidebar color.

## [0.3.6] - 2026-09-12

### Changed
- The close-confirmation dialog now centers its icon, question, description, **Do not ask again** checkbox and three action buttons.
- Close actions are clearly separated into **Cancel**, **Copy and close**, and **Close**.

### Fixed
- Restored vertical and horizontal image centering in the workspace.

## [0.3.5] - 2026-09-12

### Fixed
- Fixed **Fit** so it re-reads the actual viewport size after window resize or maximization.

### Added
- **Ctrl + mouse wheel** zoom over the image.

### Changed
- **Tools**, **Tool options**, **Elements**, and **Image details** headings are outside their bordered content cards.
- Removed the darker strip directly behind section headings.
- Tool Options uses only the natural height required by the active tool.

## [0.3.4] - 2026-09-12

### Fixed
- First-install / welcome messages now use the detected system language: English desktop gets English messages and Polish desktop gets Polish messages.
- Removed white lines connecting consecutive **Number** markers by isolating Cairo paths between annotations.
- **Dark / Light / System** theme selection now applies to the editor as well as the settings window and updates live.
- Added consistent spacing around Tools, Tool Options, Elements and Image details.

### Changed
- **Pen** is the first tool and the default active tool when the editor opens.
- The dark theme uses a darker Zorin-like sidebar and workspace treatment.

## [0.3.3] - 2026-09-12

### Changed
- Tools now contains compact icon-only buttons with tooltips.
- Added a consistent symbolic icon set for Zorin Shot tools.
- Reordered the top toolbar into edit/history → zoom → copy/save groups.
- Tool Options is dynamic and occupies only the height required by the current tool.
- Elements grows with content up to a limit and then becomes scrollable.

### Added
- Added a Settings button to the editor title bar that opens the same Zorin Shot control center as the application-menu entry.
- Crop preview now shows a visible dashed border and dims the area that will be discarded.

### Fixed
- Disabled drawing drag for **Number** so it cannot create an accidental line between markers.
- Stabilized right-column layout when tool options change.

## [0.3.2] - 2026-09-12

### Added
- Added **System / Dark / Light** application theme selection.
- Improved the editor sidebar and tool presentation.

### Changed
- Improved tool-button layout and reduced unnecessary Tool Options whitespace.
- The settings window also respects the selected application theme.

### Fixed
- Fixed an issue where the Number tool could create an unwanted connecting line.
- Improved right-panel stability.

## [0.3.1] - 2026-09-12

### Changed
- The top editor toolbar uses icons for undo, redo, delete, zoom out, zoom in, fit, copy and save.
- The right column contains only Tools, Tool Options, Elements and Image details.
- Elements has its own scroll area so additional annotations do not enlarge the application window or move the image workspace.
- Closing the editor shows **Cancel**, **Copy and close**, **Close**, and a **Do not ask again** checkbox.

### Fixed
- Fixed layout shifts caused by changes in the right panel.
- Fixed the right panel disappearing while switching tools.
- Improved active-annotation selection in the Elements list.

## [0.3.0] - 2026-09-12

### Added
- Rebuilt the editor around a large image workspace with a right-side options panel.
- Added **Line**, **Move**, and sequential **Number** tools.
- Added an Elements list with selection, deletion and ordering controls.
- Added Image details with file name, image dimensions, zoom and annotation count.
- Added per-tool controls for thickness, color, opacity, fill, text background, number radius and redaction pixel size.

### Changed
- The image automatically fits the current window while manual zoom remains available.
- Highlighter uses translucent ink so the image remains visible below it.
- Redaction uses square pixelation blocks.
- Text and numbered markers support configurable backgrounds/fills and opacity.

## [0.2.1] - 2026-09-12

### Fixed
- Improved GNOME 46 Quick Settings button discovery and reinsertion when Zorin Taskbar rebuilds the menu.
- Removed the user-facing “Quick Settings action bar not found” notification and switched to silent retries.
- GNOME's native screenshot UI now starts in **Area** mode.
- Zorin Shot does not close Quick Settings before GNOME freezes the stage, so open shell menus can remain visible in the captured scene.
- Fixed the duplicate title bar by using `Gtk.Window.set_titlebar()` correctly.
- Installed application-ID icon aliases so GTK4/GNOME associates windows with the Zorin Shot icon.
- Removed the obsolete `zorin-shot-settings.desktop` entry.
- Initial language is detected from `LANGUAGE`, `LC_*`, and `LANG`.
- Bound the updater to `ILoveMyProjects/ZorinShot`.
- GitHub Actions builds from both `master` and `main`.

## [0.2.0] - 2026-09-12

### Fixed
- Added the Zorin Shot action directly after the original GNOME screenshot button in the GNOME Shell 46 system action row.
- Default capture now opens GNOME's native area/window/screen chooser instead of opening a full-desktop image first.
- The native chooser result is sent automatically to the Zorin Shot editor.
- Redaction is fully opaque.
- Matched application IDs and `.desktop` filenames for correct GNOME window/icon association.
- Installer now deploys both regular and symbolic Zorin Shot icons and refreshes the icon cache.

### Added
- Added **Polish / English** language selection.
- Added translations for the control center, editor and extension messages.
- Added migration from the older capture mode to GNOME's native chooser.

## [0.1.0] - 2026-09-12

### Added
- Added a separate Zorin Shot button next to GNOME's original screenshot button.
- Added capture of the current shell state before opening the editor.
- Added area, full desktop and active-window modes.
- Added a built-in annotation editor with pen, highlighter, arrow, shapes, text, redaction, crop, undo/redo, zoom, clipboard copy and PNG save.
- Added optional `Print Screen` takeover while keeping the original GNOME panel on `Super + Print Screen`.
- Added the Zorin Shot control center with **Settings**, **About**, and **Updates** tabs.
- Added GitHub Release update checks, changelog display and terminal-free update installation.
- Added SHA-256 verification for downloaded update packages.
- Added GitHub Actions release-package generation and publishing for `vX.Y.Z` tags.
