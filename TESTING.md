# Test plan — Zorin Shot 0.3.10

After installing on Zorin OS 18 / GNOME Shell 46 and signing back in, verify the following:

1. Open Quick Settings. The original GNOME screenshot button is still present and the Zorin Shot button appears next to it.
2. Click the original button and verify that GNOME's original screenshot / screen-recording panel opens.
3. Click Zorin Shot in the default native mode and verify that GNOME's native screenshot chooser opens.
4. Capture an area and verify that only the selected screenshot opens in the Zorin Shot editor.
5. Verify pen, highlighter, line, arrow, rectangle, ellipse, text, number, pixelated redaction, crop and move tools.
6. Verify undo/redo, copy, save, Fit, toolbar zoom and Ctrl + mouse wheel zoom.
7. Verify that Number markers do not draw connecting lines.
8. Verify that the right editor sidebar remains anchored at the top and does not move when zoom changes.
9. Verify light, dark and system themes in both Settings and the editor.
10. Verify that `Print Screen` opens Zorin Shot and `Super + Print Screen` opens the original GNOME screenshot panel when takeover is enabled.
11. Open Zorin Shot from the application menu and verify the correct Zorin Shot application icon.
12. On an English desktop, verify that first-install messages and the initial application language are English. Repeat on a Polish desktop for Polish.
13. Change the application language in Settings and verify that Settings and newly opened editor windows use the selected language.
14. Open Updates, enlarge the settings window and verify that the changelog area expands to use the available vertical space rather than leaving an empty block underneath.
15. Check for updates and verify that Markdown release notes are rendered as formatted headings, bullets, bold text and inline code rather than displayed as raw Markdown syntax.
16. Verify update-manifest fallback behavior by testing both a valid `update.json` and the GitHub Releases API fallback.
17. Verify SHA-256 validation before the updater launches the installer.
