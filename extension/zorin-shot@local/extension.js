import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as QuickSettings from 'resource:///org/gnome/shell/ui/quickSettings.js';

const UUID = 'zorin-shot@local';
const KEYBINDING_NAME = 'capture-shortcut';
const NATIVE_SCHEMA = 'org.gnome.shell.keybindings';
const NATIVE_KEY = 'show-screenshot-ui';
const EDITOR = GLib.build_filenamev([GLib.get_home_dir(), '.local', 'lib', 'zorin-shot', 'zorin-shot-editor.py']);

export default class ZorinShotExtension extends Extension {
    enable() {
        this._settings = this.getSettings();
        this._nativeSettings = new Gio.Settings({schema_id: NATIVE_SCHEMA});
        this._button = null;
        this._keybindingInstalled = false;
        this._signals = [];

        this._syncButton();
        this._syncKeybinding();

        this._signals.push(this._settings.connect('changed::show-action-button', () => this._syncButton()));
        this._signals.push(this._settings.connect('changed::replace-print-screen', () => this._syncKeybinding()));
    }

    disable() {
        this._removeKeybinding();
        this._restoreNativeBinding();
        this._removeButton();

        if (this._settings) {
            for (const id of this._signals)
                this._settings.disconnect(id);
        }
        this._signals = [];
        this._nativeSettings = null;
        this._settings = null;
    }

    _syncButton() {
        if (this._settings.get_boolean('show-action-button'))
            this._addButton();
        else
            this._removeButton();
    }

    _actionBox() {
        return Main.panel.statusArea.quickSettings?._system?._indicator?.child ?? null;
    }

    _addButton() {
        if (this._button)
            return;

        const box = this._actionBox();
        if (!box) {
            Main.notify('Zorin Shot', 'Nie znaleziono paska akcji Quick Settings w GNOME Shell 46.');
            return;
        }

        this._button = new QuickSettings.QuickSettingsItem({
            style_class: 'icon-button',
            can_focus: true,
            icon_name: 'document-edit-symbolic',
            accessible_name: 'Zorin Shot — zrzut z adnotacjami',
        });
        this._button.connect('clicked', () => this._capture(true));

        // GNOME 46 normally places the stock screenshot action first.  Try to
        // identify it by icon; if Zorin's theme hides that property, index 1
        // still places our button directly after the first action.
        const children = box.get_children();
        let stockIndex = children.findIndex(child => {
            const direct = child.icon_name ?? '';
            const nested = child.get_child?.()?.icon_name ?? '';
            return direct.includes('camera') || direct.includes('screenshot') ||
                nested.includes('camera') || nested.includes('screenshot');
        });
        if (stockIndex < 0)
            stockIndex = 0;

        box.insert_child_at_index(this._button, Math.min(stockIndex + 1, children.length));
    }

    _removeButton() {
        if (!this._button)
            return;
        try {
            const parent = this._button.get_parent();
            if (parent)
                parent.remove_child(this._button);
            this._button.destroy();
        } catch (error) {
            logError(error, `${UUID}: removing Quick Settings button`);
        }
        this._button = null;
    }

    _capture(fromQuickSettings) {
        const mode = this._settings.get_string('capture-mode');
        if (mode === 'window')
            this._captureWindow(fromQuickSettings);
        else
            this._captureVisibleStage(fromQuickSettings, mode === 'region');
    }

    _newOutput() {
        const cacheDir = GLib.build_filenamev([GLib.get_user_cache_dir(), 'zorin-shot']);
        GLib.mkdir_with_parents(cacheDir, 0o700);
        this._pruneCache(cacheDir);

        const stamp = GLib.DateTime.new_now_local().format('%Y-%m-%d_%H-%M-%S');
        const filename = `ZorinShot_${stamp}_${GLib.get_monotonic_time()}.png`;
        const path = GLib.build_filenamev([cacheDir, filename]);
        const file = Gio.File.new_for_path(path);
        const stream = file.replace(null, false, Gio.FileCreateFlags.REPLACE_DESTINATION, null);
        return [file, stream];
    }

    async _captureVisibleStage(fromQuickSettings, selectRegion) {
        let file;
        let stream;
        try {
            [file, stream] = this._newOutput();
            const shot = new Shell.Screenshot();

            // Use the same "freeze the Shell stage first" primitive as GNOME's
            // own interactive screenshot UI.  The important ordering is:
            //   1) capture stage (Quick Settings is still open),
            //   2) write the frozen texture to PNG,
            //   3) only then close Quick Settings and launch our editor.
            const [content, scale, cursorContent, cursorPoint, cursorScale] =
                await shot.screenshot_stage_to_content();
            const texture = content.get_texture();
            const includeCursor = this._settings.get_boolean('include-cursor');
            const cursorTexture = includeCursor && cursorContent
                ? cursorContent.get_texture()
                : null;
            const cursorX = cursorPoint ? Math.round(cursorPoint.x * scale) : 0;
            const cursorY = cursorPoint ? Math.round(cursorPoint.y * scale) : 0;

            await Shell.Screenshot.composite_to_stream(
                texture,
                0, 0, -1, -1,
                scale,
                cursorTexture,
                cursorX,
                cursorY,
                cursorScale ?? 1.0,
                stream
            );
            stream.close(null);

            if (fromQuickSettings)
                Main.panel.statusArea.quickSettings.menu.close();
            this._launchEditor(file.get_path(), selectRegion);
        } catch (error) {
            try { stream?.close(null); } catch (_) {}
            this._fail('Nie udało się zrobić zrzutu aktualnego stanu pulpitu.', error);
        }
    }

    _captureWindow(fromQuickSettings) {
        let file;
        let stream;
        try {
            [file, stream] = this._newOutput();
            const shot = new Shell.Screenshot();
            const cursor = this._settings.get_boolean('include-cursor');
            shot.screenshot_window(true, cursor, stream, (object, result) => {
                try {
                    object.screenshot_window_finish(result);
                    stream.close(null);
                    if (fromQuickSettings)
                        Main.panel.statusArea.quickSettings.menu.close();
                    this._launchEditor(file.get_path(), false);
                } catch (error) {
                    try { stream.close(null); } catch (_) {}
                    this._fail('Nie udało się przechwycić aktywnego okna.', error);
                }
            });
        } catch (error) {
            try { stream?.close(null); } catch (_) {}
            this._fail('Nie udało się przygotować zrzutu okna.', error);
        }
    }

    _launchEditor(path, selectRegion) {
        try {
            const editorFile = Gio.File.new_for_path(EDITOR);
            if (!editorFile.query_exists(null)) {
                Main.notify('Zorin Shot', `Brak edytora: ${EDITOR}. Uruchom ponownie install.sh.`);
                return;
            }
            const argv = [EDITOR, '--image', path];
            if (selectRegion)
                argv.push('--select-region');
            Gio.Subprocess.new(argv, Gio.SubprocessFlags.NONE);
        } catch (error) {
            this._fail('Zrzut został wykonany, ale nie udało się uruchomić edytora.', error);
        }
    }

    _fail(message, error) {
        logError(error, `${UUID}: ${message}`);
        Main.notify('Zorin Shot', `${message} ${error.message ?? ''}`);
    }

    _pruneCache(cacheDir) {
        try {
            const dir = Gio.File.new_for_path(cacheDir);
            const enumerator = dir.enumerate_children('standard::name,time::modified', Gio.FileQueryInfoFlags.NONE, null);
            const now = Math.floor(GLib.get_real_time() / 1000000);
            let info;
            while ((info = enumerator.next_file(null)) !== null) {
                const age = now - info.get_modification_date_time().to_unix();
                if (age > 2 * 24 * 60 * 60)
                    dir.get_child(info.get_name()).delete(null);
            }
            enumerator.close(null);
        } catch (_) {
            // Cache cleanup is best effort and must never block taking a shot.
        }
    }

    _syncKeybinding() {
        this._removeKeybinding();
        if (!this._settings.get_boolean('replace-print-screen')) {
            this._restoreNativeBinding();
            return;
        }

        try {
            this._moveNativeBindingToFallback();
            Main.wm.addKeybinding(
                KEYBINDING_NAME,
                this._settings,
                Meta.KeyBindingFlags.NONE,
                Shell.ActionMode.NORMAL | Shell.ActionMode.OVERVIEW | Shell.ActionMode.POPUP,
                () => this._capture(false)
            );
            this._keybindingInstalled = true;
        } catch (error) {
            this._restoreNativeBinding();
            this._fail('Nie udało się przejąć klawisza Print Screen.', error);
        }
    }

    _removeKeybinding() {
        if (!this._keybindingInstalled)
            return;
        try {
            Main.wm.removeKeybinding(KEYBINDING_NAME);
        } catch (error) {
            logError(error, `${UUID}: removing keybinding`);
        }
        this._keybindingInstalled = false;
    }

    _moveNativeBindingToFallback() {
        if (!this._settings.get_boolean('saved-native-valid')) {
            this._settings.set_strv('saved-native-shortcut', this._nativeSettings.get_strv(NATIVE_KEY));
            this._settings.set_boolean('saved-native-valid', true);
        }
        this._nativeSettings.set_strv(NATIVE_KEY, this._settings.get_strv('native-fallback-shortcut'));
    }

    _restoreNativeBinding() {
        if (!this._settings || !this._nativeSettings)
            return;
        if (!this._settings.get_boolean('saved-native-valid'))
            return;

        try {
            const fallback = this._settings.get_strv('native-fallback-shortcut');
            const current = this._nativeSettings.get_strv(NATIVE_KEY);
            if (this._sameArray(current, fallback))
                this._nativeSettings.set_strv(NATIVE_KEY, this._settings.get_strv('saved-native-shortcut'));
            this._settings.set_strv('saved-native-shortcut', []);
            this._settings.set_boolean('saved-native-valid', false);
        } catch (error) {
            logError(error, `${UUID}: restoring GNOME screenshot shortcut`);
        }
    }

    _sameArray(a, b) {
        return a.length === b.length && a.every((value, index) => value === b[index]);
    }
}
