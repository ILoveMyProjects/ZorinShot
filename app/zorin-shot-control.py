#!/usr/bin/env python3
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
from gi.repository import Gtk, Gdk, Gio, GLib

APP_ID = 'io.local.ZorinShot.Control'
SCHEMA_ID = 'org.gnome.shell.extensions.zorin-shot'
EXT_UUID = 'zorin-shot@local'
APP_DIR = Path.home() / '.local' / 'lib' / 'zorin-shot'
EXT_DIR = Path.home() / '.local' / 'share' / 'gnome-shell' / 'extensions' / EXT_UUID
BUILD_INFO_PATH = APP_DIR / 'build-info.json'
VERSION_PATH = APP_DIR / 'VERSION'
GITHUB_API_ACCEPT = 'application/vnd.github+json'
USER_AGENT = 'Zorin-Shot-Updater'
AUTO_CHECK_INTERVAL = 6 * 60 * 60


def load_build_info():
    info = {
        'version': '0.0.0',
        'github_repo': '',
        'build_channel': 'unknown',
        'asset_pattern': 'zorin-shot-{version}.zip',
    }
    try:
        data = json.loads(BUILD_INFO_PATH.read_text(encoding='utf-8'))
        if isinstance(data, dict):
            info.update(data)
    except Exception:
        pass
    try:
        raw = VERSION_PATH.read_text(encoding='utf-8').strip()
        if raw:
            info['version'] = raw
    except Exception:
        pass
    return info


def version_tuple(value):
    value = str(value or '').strip().lstrip('vV')
    core = value.split('+', 1)[0].split('-', 1)[0]
    parts = []
    for item in core.split('.'):
        m = re.match(r'^(\d+)', item)
        parts.append(int(m.group(1)) if m else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:4])


def is_newer(candidate, current):
    return version_tuple(candidate) > version_tuple(current)


def human_size(value):
    try:
        size = float(value)
    except Exception:
        return ''
    for unit in ('B', 'KB', 'MB', 'GB'):
        if size < 1024 or unit == 'GB':
            return f'{size:.0f} {unit}' if unit == 'B' else f'{size:.1f} {unit}'
        size /= 1024
    return ''


def safe_extract(zip_path, destination):
    destination = Path(destination).resolve()
    with zipfile.ZipFile(zip_path, 'r') as archive:
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if target != destination and destination not in target.parents:
                raise RuntimeError(f'Niebezpieczna ścieżka w paczce aktualizacji: {member.filename}')
        archive.extractall(destination)


class ControlWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title='Zorin Shot')
        self.set_default_size(820, 660)
        self.set_size_request(660, 520)

        self.build_info = load_build_info()
        self.current_version = str(self.build_info.get('version') or '0.0.0')
        self.repo = str(self.build_info.get('github_repo') or '').strip()
        self.latest_release = None
        self.update_thread = None
        self.settings = self._load_settings()

        self._build_ui()
        self._load_settings_into_ui()
        self._maybe_auto_check()

    def _load_settings(self):
        schema_dir = EXT_DIR / 'schemas'
        try:
            parent = Gio.SettingsSchemaSource.get_default()
            source = Gio.SettingsSchemaSource.new_from_directory(str(schema_dir), parent, False)
            schema = source.lookup(SCHEMA_ID, False)
            if schema is None:
                raise RuntimeError(f'Nie znaleziono schematu {SCHEMA_ID}')
            return Gio.Settings.new_full(schema, None, None)
        except Exception as exc:
            self._fatal_message = f'Nie udało się otworzyć ustawień Zorin Shot: {exc}'
            return None

    def _build_ui(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_child(root)

        header = Gtk.HeaderBar()
        header.set_show_title_buttons(True)
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        title = Gtk.Label(label='Zorin Shot')
        title.add_css_class('title')
        subtitle = Gtk.Label(label=f'wersja {self.current_version}')
        subtitle.add_css_class('dim-label')
        title_box.append(title)
        title_box.append(subtitle)
        header.set_title_widget(title_box)
        root.append(header)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(140)
        self.stack.set_hexpand(True)
        self.stack.set_vexpand(True)

        switcher_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        switcher_bar.set_halign(Gtk.Align.CENTER)
        switcher_bar.set_margin_top(8)
        switcher_bar.set_margin_bottom(8)
        switcher = Gtk.StackSwitcher()
        switcher.set_stack(self.stack)
        switcher_bar.append(switcher)
        root.append(switcher_bar)
        root.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        root.append(self.stack)

        self.stack.add_titled(self._settings_page(), 'settings', 'Ustawienia')
        self.stack.add_titled(self._about_page(), 'about', 'O programie')
        self.stack.add_titled(self._updates_page(), 'updates', 'Aktualizacje')

        if getattr(self, '_fatal_message', None):
            GLib.idle_add(self._show_dialog, 'Zorin Shot', self._fatal_message)

    def _page_scroller(self):
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        content.set_margin_top(24)
        content.set_margin_bottom(28)
        content.set_margin_start(28)
        content.set_margin_end(28)
        scroll.set_child(content)
        return scroll, content

    def _section(self, title, description=None):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        heading = Gtk.Label(label=title, xalign=0)
        heading.add_css_class('heading')
        outer.append(heading)
        if description:
            desc = Gtk.Label(label=description, xalign=0, wrap=True)
            desc.add_css_class('dim-label')
            outer.append(desc)
        frame = Gtk.Frame()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        frame.set_child(box)
        outer.append(frame)
        return outer, box

    def _row(self, title, subtitle=None, widget=None):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        row.set_margin_top(10)
        row.set_margin_bottom(10)
        row.set_margin_start(14)
        row.set_margin_end(14)
        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        labels.set_hexpand(True)
        title_label = Gtk.Label(label=title, xalign=0, wrap=True)
        labels.append(title_label)
        if subtitle:
            subtitle_label = Gtk.Label(label=subtitle, xalign=0, wrap=True)
            subtitle_label.add_css_class('dim-label')
            labels.append(subtitle_label)
        row.append(labels)
        if widget is not None:
            widget.set_valign(Gtk.Align.CENTER)
            row.append(widget)
        return row

    def _append_separator(self, box):
        box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

    def _settings_page(self):
        scroll, content = self._page_scroller()

        section, box = self._section(
            'Integracja z Zorin / GNOME',
            'Oryginalny aparat GNOME pozostaje bez zmian. Zorin Shot może dodać drugi przycisk obok niego.'
        )
        content.append(section)

        self.show_button_switch = Gtk.Switch()
        self.show_button_switch.connect('notify::active', self._setting_bool_changed, 'show-action-button')
        box.append(self._row(
            'Pokaż ikonę Zorin Shot obok oryginalnego aparatu',
            'Nowa ikona robi zrzut do edytora Zorin Shot; stara nadal obsługuje systemowy screenshot i nagrywanie.',
            self.show_button_switch,
        ))
        self._append_separator(box)

        mode_model = Gtk.StringList.new([
            'Obszar — zachowaj otwarte menu',
            'Cały widoczny pulpit',
            'Aktywne okno',
        ])
        self.mode_dropdown = Gtk.DropDown(model=mode_model)
        self.mode_dropdown.set_size_request(240, -1)
        self.mode_dropdown.connect('notify::selected', self._mode_changed)
        box.append(self._row(
            'Domyślny tryb przechwytywania',
            'Tryb obszaru najpierw zamraża aktualny ekran, dzięki czemu można przechwycić otwarte Quick Settings.',
            self.mode_dropdown,
        ))
        self._append_separator(box)

        self.cursor_switch = Gtk.Switch()
        self.cursor_switch.connect('notify::active', self._setting_bool_changed, 'include-cursor')
        box.append(self._row('Dołącz kursor myszy', None, self.cursor_switch))

        keyboard_section, keyboard_box = self._section(
            'Klawisze',
            'Zorin Shot może przejąć zwykły Print Screen, pozostawiając oryginalny panel GNOME pod Super + Print Screen.'
        )
        content.append(keyboard_section)

        self.replace_print_switch = Gtk.Switch()
        self.replace_print_switch.connect('notify::active', self._setting_bool_changed, 'replace-print-screen')
        keyboard_box.append(self._row(
            'Print Screen → Zorin Shot',
            'Po włączeniu Super + Print Screen pozostaje skrótem do oryginalnego screenshotu / nagrywania GNOME.',
            self.replace_print_switch,
        ))

        update_section, update_box = self._section('Aktualizacje')
        content.append(update_section)
        self.auto_update_switch = Gtk.Switch()
        self.auto_update_switch.connect('notify::active', self._setting_bool_changed, 'auto-check-updates')
        update_box.append(self._row(
            'Automatycznie sprawdzaj aktualizacje',
            'Przy otwieraniu Zorin Shot sprawdzenie jest wykonywane najwyżej raz na 6 godzin.',
            self.auto_update_switch,
        ))

        return scroll

    def _about_page(self):
        scroll, content = self._page_scroller()

        hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        hero.set_halign(Gtk.Align.CENTER)
        hero.set_margin_top(8)
        image = Gtk.Image.new_from_icon_name('zorin-shot')
        image.set_pixel_size(96)
        hero.append(image)
        name = Gtk.Label(label='Zorin Shot')
        name.add_css_class('title-1')
        hero.append(name)
        ver = Gtk.Label(label=f'Wersja {self.current_version}')
        ver.add_css_class('dim-label')
        hero.append(ver)
        summary = Gtk.Label(
            label='Natywne narzędzie do zrzutów ekranu dla Zorin OS 18 / GNOME 46 z własnym edytorem adnotacji.',
            wrap=True,
            justify=Gtk.Justification.CENTER,
        )
        summary.set_max_width_chars(70)
        hero.append(summary)
        content.append(hero)

        about_section, about_box = self._section('O aplikacji')
        content.append(about_section)
        about_box.append(self._row(
            'Przechwytywanie',
            'Osobny przycisk w Quick Settings, tryb obszaru zachowujący otwarte menu, pełny pulpit i aktywne okno.'
        ))
        self._append_separator(about_box)
        about_box.append(self._row(
            'Edytor',
            'Pióro, marker, strzałki, figury, tekst, cenzura, kadrowanie, undo/redo, zoom, kopiowanie i zapis PNG.'
        ))
        self._append_separator(about_box)
        about_box.append(self._row('Platforma', 'Zorin OS 18 / GNOME Shell 46'))

        repo_section, repo_box = self._section('Projekt')
        content.append(repo_section)
        repo_text = self.repo if self.repo else 'Repozytorium zostanie wpisane automatycznie podczas budowania paczki w GitHub Actions.'
        self.repo_button = Gtk.Button(label='Otwórz repozytorium GitHub')
        self.repo_button.set_sensitive(bool(self.repo))
        self.repo_button.connect('clicked', self._open_repo)
        repo_box.append(self._row('Repozytorium', repo_text, self.repo_button))

        return scroll

    def _updates_page(self):
        scroll, content = self._page_scroller()

        version_section, version_box = self._section('Wersje')
        content.append(version_section)
        self.current_version_label = Gtk.Label(label=self.current_version)
        self.current_version_label.set_selectable(True)
        version_box.append(self._row('Zainstalowana wersja', None, self.current_version_label))
        self._append_separator(version_box)
        self.latest_version_label = Gtk.Label(label='Jeszcze nie sprawdzono')
        self.latest_version_label.set_selectable(True)
        version_box.append(self._row('Najnowsza wersja na GitHubie', None, self.latest_version_label))

        action_section, action_box = self._section('Aktualizacja')
        content.append(action_section)
        action_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        action_row.set_margin_top(12)
        action_row.set_margin_bottom(12)
        action_row.set_margin_start(14)
        action_row.set_margin_end(14)
        self.check_button = Gtk.Button(label='Sprawdź aktualizacje')
        self.check_button.connect('clicked', lambda *_: self.check_updates(manual=True))
        action_row.append(self.check_button)
        self.update_button = Gtk.Button(label='Pobierz i zainstaluj aktualizację')
        self.update_button.add_css_class('suggested-action')
        self.update_button.set_sensitive(False)
        self.update_button.connect('clicked', self._install_latest)
        action_row.append(self.update_button)
        self.release_button = Gtk.Button(label='Otwórz wydanie na GitHubie')
        self.release_button.set_sensitive(False)
        self.release_button.connect('clicked', self._open_release)
        action_row.append(self.release_button)
        action_box.append(action_row)

        self.progress = Gtk.ProgressBar()
        self.progress.set_show_text(True)
        self.progress.set_text('Gotowe')
        self.progress.set_margin_start(14)
        self.progress.set_margin_end(14)
        self.progress.set_margin_bottom(12)
        action_box.append(self.progress)

        self.update_status = Gtk.Label(label='Kliknij „Sprawdź aktualizacje”, aby pobrać informacje z GitHub Releases.', xalign=0, wrap=True)
        self.update_status.set_margin_start(14)
        self.update_status.set_margin_end(14)
        self.update_status.set_margin_bottom(12)
        action_box.append(self.update_status)

        changelog_section, changelog_box = self._section('Changelog najnowszej wersji')
        content.append(changelog_section)
        self.changelog = Gtk.TextView()
        self.changelog.set_editable(False)
        self.changelog.set_cursor_visible(False)
        self.changelog.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.changelog.set_left_margin(10)
        self.changelog.set_right_margin(10)
        self.changelog.set_top_margin(10)
        self.changelog.set_bottom_margin(10)
        self.changelog.set_size_request(-1, 230)
        self.changelog.get_buffer().set_text('Changelog pojawi się tutaj po sprawdzeniu aktualizacji.')
        changelog_scroll = Gtk.ScrolledWindow()
        changelog_scroll.set_min_content_height(230)
        changelog_scroll.set_child(self.changelog)
        changelog_box.append(changelog_scroll)

        if not self.repo:
            self.check_button.set_sensitive(False)
            self.update_status.set_text(
                'Ta lokalna paczka nie jest jeszcze powiązana z repozytorium. '
                'Po zbudowaniu projektu przez GitHub Actions repozytorium zostanie wpisane automatycznie i aktualizator zacznie działać.'
            )

        return scroll

    def _load_settings_into_ui(self):
        if self.settings is None:
            for widget in (
                self.show_button_switch,
                self.mode_dropdown,
                self.cursor_switch,
                self.replace_print_switch,
                self.auto_update_switch,
            ):
                widget.set_sensitive(False)
            return

        self._loading_settings = True
        try:
            self.show_button_switch.set_active(self.settings.get_boolean('show-action-button'))
            self.cursor_switch.set_active(self.settings.get_boolean('include-cursor'))
            self.replace_print_switch.set_active(self.settings.get_boolean('replace-print-screen'))
            self.auto_update_switch.set_active(self.settings.get_boolean('auto-check-updates'))
            modes = ['region', 'full', 'window']
            mode = self.settings.get_string('capture-mode')
            self.mode_dropdown.set_selected(modes.index(mode) if mode in modes else 0)
        finally:
            self._loading_settings = False

    def _setting_bool_changed(self, switch, _pspec, key):
        if getattr(self, '_loading_settings', False) or self.settings is None:
            return
        try:
            self.settings.set_boolean(key, switch.get_active())
        except Exception as exc:
            self._show_dialog('Błąd ustawień', str(exc))

    def _mode_changed(self, dropdown, _pspec):
        if getattr(self, '_loading_settings', False) or self.settings is None:
            return
        modes = ['region', 'full', 'window']
        index = dropdown.get_selected()
        if 0 <= index < len(modes):
            try:
                self.settings.set_string('capture-mode', modes[index])
            except Exception as exc:
                self._show_dialog('Błąd ustawień', str(exc))

    def _open_uri(self, uri):
        try:
            Gio.AppInfo.launch_default_for_uri(uri, None)
        except Exception as exc:
            self._show_dialog('Nie udało się otworzyć linku', str(exc))

    def _open_repo(self, *_args):
        if self.repo:
            self._open_uri(f'https://github.com/{self.repo}')

    def _open_release(self, *_args):
        if self.latest_release and self.latest_release.get('html_url'):
            self._open_uri(self.latest_release['html_url'])

    def _maybe_auto_check(self):
        if not self.repo or self.settings is None:
            return
        try:
            if not self.settings.get_boolean('auto-check-updates'):
                return
            last = self.settings.get_int64('last-update-check')
            if int(time.time()) - last < AUTO_CHECK_INTERVAL:
                return
        except Exception:
            return
        GLib.timeout_add(1200, self._auto_check_timeout)

    def _auto_check_timeout(self):
        self.check_updates(manual=False)
        return GLib.SOURCE_REMOVE

    def check_updates(self, manual=True):
        if not self.repo or self.update_thread and self.update_thread.is_alive():
            return
        self.check_button.set_sensitive(False)
        self.update_button.set_sensitive(False)
        self.progress.set_fraction(0.0)
        self.progress.pulse()
        self.progress.set_text('Sprawdzanie…')
        self.update_status.set_text('Łączenie z GitHub Releases…')
        self.update_thread = threading.Thread(target=self._check_worker, args=(manual,), daemon=True)
        self.update_thread.start()

    def _request_json(self, url):
        request = urllib.request.Request(url, headers={
            'Accept': GITHUB_API_ACCEPT,
            'User-Agent': USER_AGENT,
        })
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode('utf-8'))

    def _check_worker(self, manual):
        try:
            url = f'https://api.github.com/repos/{self.repo}/releases/latest'
            release = self._request_json(url)
            if not isinstance(release, dict) or not release.get('tag_name'):
                raise RuntimeError('GitHub nie zwrócił prawidłowej informacji o najnowszym wydaniu.')
            GLib.idle_add(self._check_success, release)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                message = 'Repozytorium nie ma jeszcze opublikowanego GitHub Release.'
            elif exc.code == 403:
                message = 'GitHub odmówił zapytania (limit API lub brak dostępu). Spróbuj ponownie później.'
            else:
                message = f'GitHub zwrócił błąd HTTP {exc.code}.'
            GLib.idle_add(self._check_failed, message, manual)
        except Exception as exc:
            GLib.idle_add(self._check_failed, f'Nie udało się sprawdzić aktualizacji: {exc}', manual)

    def _check_success(self, release):
        self.latest_release = release
        tag = str(release.get('tag_name') or '').strip()
        latest = tag.lstrip('vV') or tag
        body = str(release.get('body') or '').strip() or 'Brak opisu zmian dla tego wydania.'
        self.latest_version_label.set_text(latest)
        self.changelog.get_buffer().set_text(body)
        self.release_button.set_sensitive(bool(release.get('html_url')))
        self.check_button.set_sensitive(True)
        self.progress.set_fraction(1.0)
        self.progress.set_text('Sprawdzono')

        if self.settings is not None:
            try:
                self.settings.set_int64('last-update-check', int(time.time()))
            except Exception:
                pass

        if is_newer(latest, self.current_version):
            asset = self._find_release_asset(release, latest)
            if asset:
                self.update_button.set_sensitive(True)
                size = human_size(asset.get('size'))
                suffix = f' ({size})' if size else ''
                self.update_status.set_text(f'Dostępna jest nowa wersja {latest}{suffix}. Możesz zainstalować ją bez terminala.')
            else:
                self.update_status.set_text(
                    f'Wersja {latest} jest nowsza, ale Release nie zawiera oczekiwanej paczki zorin-shot-{latest}.zip.'
                )
        else:
            self.update_button.set_sensitive(False)
            self.update_status.set_text(f'Masz aktualną wersję Zorin Shot ({self.current_version}).')
        return GLib.SOURCE_REMOVE

    def _check_failed(self, message, manual):
        self.check_button.set_sensitive(bool(self.repo))
        self.progress.set_fraction(0.0)
        self.progress.set_text('Błąd')
        self.update_status.set_text(message)
        if manual:
            self._show_dialog('Aktualizacje Zorin Shot', message)
        return GLib.SOURCE_REMOVE

    def _find_release_asset(self, release, latest):
        expected = f'zorin-shot-{latest}.zip'
        assets = release.get('assets') or []
        for asset in assets:
            if asset.get('name') == expected:
                return asset
        candidates = [
            asset for asset in assets
            if str(asset.get('name') or '').startswith('zorin-shot-') and str(asset.get('name') or '').endswith('.zip')
        ]
        return candidates[0] if len(candidates) == 1 else None

    def _install_latest(self, *_args):
        if not self.latest_release or self.update_thread and self.update_thread.is_alive():
            return
        latest = str(self.latest_release.get('tag_name') or '').lstrip('vV')
        asset = self._find_release_asset(self.latest_release, latest)
        if not asset:
            self._show_dialog('Aktualizacja', 'Nie znaleziono paczki aktualizacji w GitHub Release.')
            return

        self.check_button.set_sensitive(False)
        self.update_button.set_sensitive(False)
        self.progress.set_fraction(0.0)
        self.progress.set_text('Pobieranie…')
        self.update_status.set_text(f'Pobieranie Zorin Shot {latest}…')
        self.update_thread = threading.Thread(target=self._update_worker, args=(self.latest_release, asset, latest), daemon=True)
        self.update_thread.start()

    def _download(self, url, destination, progress=False):
        request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(request, timeout=45) as response, open(destination, 'wb') as out:
            total = int(response.headers.get('Content-Length') or 0)
            done = 0
            while True:
                chunk = response.read(1024 * 256)
                if not chunk:
                    break
                out.write(chunk)
                done += len(chunk)
                if progress and total > 0:
                    GLib.idle_add(self._set_download_progress, done / total)

    def _set_download_progress(self, fraction):
        self.progress.set_fraction(max(0.0, min(1.0, fraction)))
        self.progress.set_text(f'Pobieranie… {int(fraction * 100)}%')
        return GLib.SOURCE_REMOVE

    def _expected_sha256(self, release, asset, temp_dir):
        digest = str(asset.get('digest') or '')
        if digest.lower().startswith('sha256:') and len(digest.split(':', 1)[1]) == 64:
            return digest.split(':', 1)[1].lower()

        sums_asset = next((a for a in (release.get('assets') or []) if a.get('name') == 'SHA256SUMS'), None)
        if not sums_asset or not sums_asset.get('browser_download_url'):
            return None
        sums_path = Path(temp_dir) / 'SHA256SUMS'
        self._download(sums_asset['browser_download_url'], sums_path, progress=False)
        target_name = str(asset.get('name') or '')
        for line in sums_path.read_text(encoding='utf-8', errors='replace').splitlines():
            parts = line.strip().split()
            if len(parts) >= 2 and parts[1].lstrip('*') == target_name and re.fullmatch(r'[0-9a-fA-F]{64}', parts[0]):
                return parts[0].lower()
        return None

    def _update_worker(self, release, asset, latest):
        temp_dir = tempfile.mkdtemp(prefix='zorin-shot-update-')
        try:
            zip_path = Path(temp_dir) / str(asset.get('name') or 'zorin-shot-update.zip')
            self._download(asset['browser_download_url'], zip_path, progress=True)
            GLib.idle_add(self._set_stage, 'Weryfikacja SHA-256…', 1.0)

            expected = self._expected_sha256(release, asset, temp_dir)
            if not expected:
                raise RuntimeError('Release nie zawiera sumy SHA-256. Dla bezpieczeństwa aktualizacja nie zostanie uruchomiona.')
            actual = hashlib.sha256(zip_path.read_bytes()).hexdigest().lower()
            if actual != expected:
                raise RuntimeError('Suma SHA-256 pobranej paczki jest nieprawidłowa. Aktualizacja została przerwana.')

            extract_dir = Path(temp_dir) / 'extracted'
            extract_dir.mkdir(parents=True, exist_ok=True)
            GLib.idle_add(self._set_stage, 'Rozpakowywanie…', 1.0)
            safe_extract(zip_path, extract_dir)
            installers = list(extract_dir.rglob('install.sh'))
            installers = [p for p in installers if (p.parent / 'app').is_dir() and (p.parent / 'extension').is_dir()]
            if len(installers) != 1:
                raise RuntimeError('Paczka aktualizacji nie ma prawidłowej struktury instalatora.')

            installer = installers[0]
            GLib.idle_add(self._set_stage, 'Instalowanie…', 1.0)
            env = os.environ.copy()
            env['ZORIN_SHOT_UPDATE'] = '1'
            result = subprocess.run(
                ['bash', str(installer), '--update', '--no-popup'],
                cwd=str(installer.parent),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                tail = '\n'.join(result.stdout.splitlines()[-20:])
                raise RuntimeError(f'Instalator zakończył się kodem {result.returncode}.\n\n{tail}')
            GLib.idle_add(self._update_success, latest)
        except Exception as exc:
            GLib.idle_add(self._update_failed, str(exc))
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _set_stage(self, text, fraction):
        self.progress.set_fraction(fraction)
        self.progress.set_text(text)
        self.update_status.set_text(text)
        return GLib.SOURCE_REMOVE

    def _update_success(self, latest):
        self.current_version = latest
        self.current_version_label.set_text(latest)
        self.update_button.set_sensitive(False)
        self.check_button.set_sensitive(True)
        self.progress.set_fraction(1.0)
        self.progress.set_text('Zainstalowano')
        self.update_status.set_text(
            f'Zorin Shot {latest} został zainstalowany. Wyloguj się i zaloguj ponownie, aby GNOME Shell załadował nową wersję rozszerzenia.'
        )
        self._show_dialog(
            'Aktualizacja zakończona',
            f'Zorin Shot {latest} został zainstalowany.\n\nWyloguj się i zaloguj ponownie, aby nowa wersja rozszerzenia GNOME została załadowana.'
        )
        return GLib.SOURCE_REMOVE

    def _update_failed(self, message):
        self.check_button.set_sensitive(bool(self.repo))
        self.update_button.set_sensitive(bool(self.latest_release))
        self.progress.set_fraction(0.0)
        self.progress.set_text('Błąd aktualizacji')
        self.update_status.set_text(message)
        self._show_dialog('Aktualizacja nie powiodła się', message)
        return GLib.SOURCE_REMOVE

    def _show_dialog(self, title, message):
        dialog = Gtk.Dialog(transient_for=self, modal=True, title=title)
        dialog.add_button('OK', Gtk.ResponseType.OK)
        label = Gtk.Label(label=message, wrap=True, xalign=0)
        label.set_max_width_chars(75)
        label.set_margin_top(18)
        label.set_margin_bottom(18)
        label.set_margin_start(18)
        label.set_margin_end(18)
        dialog.get_content_area().append(label)
        dialog.connect('response', lambda d, _r: d.destroy())
        dialog.present()
        return GLib.SOURCE_REMOVE


class ZorinShotControlApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        win = self.props.active_window
        if win is None:
            win = ControlWindow(self)
        win.present()


def main():
    app = ZorinShotControlApp()
    return app.run(sys.argv)


if __name__ == '__main__':
    raise SystemExit(main())
