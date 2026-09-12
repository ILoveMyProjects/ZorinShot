import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as QuickSettings from 'resource:///org/gnome/shell/ui/quickSettings.js';
import {PopupAnimation} from 'resource:///org/gnome/shell/ui/boxpointer.js';

const UUID = 'zorin-shot@local';
const KEYBINDING_NAME = 'capture-shortcut';
const NATIVE_SCHEMA = 'org.gnome.shell.keybindings';
const NATIVE_KEY = 'show-screenshot-ui';
const SCREENSHOT_ONLY_MODE = 2; // GNOME Shell 46 screenshot.js UIMode.SCREENSHOT_ONLY
const EDITOR = GLib.build_filenamev([
    GLib.get_home_dir(), '.local', 'lib', 'zorin-shot', 'zorin-shot-editor.py',
]);

const TEXT = {
    pl: {
        action: 'Zorin Shot — zrzut z adnotacjami',
        noQuickSettings: 'Nie znaleziono paska akcji Quick Settings w GNOME Shell 46.',
        editorMissing: 'Brak edytora Zorin Shot. Uruchom ponownie instalator.',
        editorLaunchFailed: 'Zrzut został wykonany, ale nie udało się uruchomić edytora.',
        nativeOpenFailed: 'Nie udało się otworzyć systemowego selektora zrzutu ekranu.',
        fullFailed: 'Nie udało się zrobić zrzutu całego pulpitu.',
        windowFailed: 'Nie udało się przechwycić aktywnego okna.',
        keyFailed: 'Nie udało się przejąć klawisza Print Screen.',
    },
    en: {
        action: 'Zorin Shot — annotated screenshot',
        noQuickSettings: 'Could not find the GNOME Shell 46 Quick Settings action bar.',
        editorMissing: 'The Zorin Shot editor is missing. Run the installer again.',
        editorLaunchFailed: 'The screenshot was captured, but the editor could not be started.',
        nativeOpenFailed: 'Could not open the system screenshot chooser.',
        fullFailed: 'Could not capture the full desktop.',
        windowFailed: 'Could not capture the active window.',
        keyFailed: 'Could not take over the Print Screen key.',
    },
};

export default class ZorinShotExtension extends Extension {
    enable() {
        this._settings = this.getSettings();
        this._nativeSettings = new Gio.Settings({schema_id: NATIVE_SCHEMA});
        this._button = null;
        this._buttonRetryId = 0;
        this._buttonRetryCount = 0;
        this._keybindingInstalled = false;
        this._signals = [];
        this._screenshotSignals = [];

        this._syncButton();
        this._syncKeybinding();

        this._signals.push(this._settings.connect(
            'changed::show-action-button', () => this._syncButton()));
        this._signals.push(this._settings.connect(
            'changed::replace-print-screen', () => this._syncKeybinding()));
        this._signals.push(this._settings.connect(
            'changed::language', () => this._refreshButtonLabel()));
    }

    disable() {
        this._disconnectScreenshotSignals();
        this._removeKeybinding();
        this._restoreNativeBinding();
        this._cancelButtonRetry();
        this._removeButton();

        if (this._settings) {
            for (const id of this._signals)
                this._settings.disconnect(id);
        }
        this._signals = [];
        this._nativeSettings = null;
        this._settings = null;
    }

    _language() {
        const value = this._settings?.get_string('language') ?? 'pl';
        return value === 'en' ? 'en' : 'pl';
    }

    _t(key) {
        return TEXT[this._language()][key] ?? TEXT.pl[key] ?? key;
    }

    _syncButton() {
        if (this._settings.get_boolean('show-action-button'))
            this._scheduleButtonAdd();
        else {
            this._cancelButtonRetry();
            this._removeButton();
        }
    }

    _findScreenshotButton(actor) {
        if (!actor)
            return null;

        const direct = String(actor.icon_name ?? actor.iconName ?? '');
        const nested = String(actor.get_child?.()?.icon_name ?? actor.get_child?.()?.iconName ?? '');
        if (direct === 'screenshooter-symbolic' || nested === 'screenshooter-symbolic')
            return actor;

        let children = [];
        try { children = actor.get_children?.() ?? []; } catch (_) {}
        for (const child of children) {
            const match = this._findScreenshotButton(child);
            if (match)
                return match;
        }
        return null;
    }

    _actionBox() {
        // Stock GNOME Shell 46 keeps the action row here. Zorin may carry
        // Shell patches, so fall back to locating the stock screenshot
        // button in the visible Quick Settings actor tree and use its parent.
        const quickSettings = Main.panel.statusArea.quickSettings;
        const direct = quickSettings?._system?._systemItem?.child ?? null;
        if (direct)
            return direct;

        const roots = [quickSettings?.menu?.box, quickSettings?.menu?.actor];
        for (const root of roots) {
            const screenshot = this._findScreenshotButton(root);
            const parent = screenshot?.get_parent?.();
            if (parent)
                return parent;
        }
        return null;
    }

    _scheduleButtonAdd() {
        if (this._button)
            return;
        if (this._tryAddButton())
            return;
        if (this._buttonRetryId)
            return;

        this._buttonRetryCount = 0;
        this._buttonRetryId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 250, () => {
            this._buttonRetryCount++;
            if (!this._settings?.get_boolean('show-action-button')) {
                this._buttonRetryId = 0;
                return GLib.SOURCE_REMOVE;
            }
            if (this._tryAddButton()) {
                this._buttonRetryId = 0;
                return GLib.SOURCE_REMOVE;
            }
            if (this._buttonRetryCount >= 40) {
                this._buttonRetryId = 0;
                Main.notify('Zorin Shot', this._t('noQuickSettings'));
                return GLib.SOURCE_REMOVE;
            }
            return GLib.SOURCE_CONTINUE;
        });
        GLib.Source.set_name_by_id(this._buttonRetryId, '[zorin-shot] wait for Quick Settings system row');
    }

    _cancelButtonRetry() {
        if (!this._buttonRetryId)
            return;
        GLib.source_remove(this._buttonRetryId);
        this._buttonRetryId = 0;
    }

    _tryAddButton() {
        if (this._button)
            return true;

        const box = this._actionBox();
        if (!box)
            return false;

        const button = new QuickSettings.QuickSettingsItem({
            style_class: 'icon-button',
            can_focus: true,
            icon_name: 'zorin-shot-symbolic',
            accessible_name: this._t('action'),
        });
        button.connect('clicked', () => this._capture(true));

        // Put Zorin Shot directly after GNOME's built-in ScreenshotItem.
        // In GNOME Shell 46 that item uses "screenshooter-symbolic".
        const children = box.get_children();
        let stockIndex = children.findIndex(child => {
            const direct = String(child.icon_name ?? child.iconName ?? '');
            const nestedChild = child.get_child?.();
            const nested = String(nestedChild?.icon_name ?? nestedChild?.iconName ?? '');
            return direct === 'screenshooter-symbolic' || nested === 'screenshooter-symbolic' ||
                direct.includes('screenshot') || nested.includes('screenshot') ||
                direct.includes('camera') || nested.includes('camera');
        });
        if (stockIndex < 0)
            stockIndex = 0;

        box.insert_child_at_index(button, Math.min(stockIndex + 1, children.length));
        this._button = button;
        return true;
    }

    _refreshButtonLabel() {
        if (this._button)
            this._button.accessible_name = this._t('action');
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
        let mode = this._settings.get_string('capture-mode');
        // Migration from the 0.1.x implementation where "region" meant
        // "capture the whole stage and crop later".
        if (mode === 'region')
            mode = 'native';

        if (mode === 'full')
            this._captureFull(fromQuickSettings);
        else if (mode === 'window')
            this._captureWindow(fromQuickSettings);
        else
            this._captureWithNativeUI(fromQuickSettings);
    }

    _disconnectScreenshotSignals() {
        const ui = Main.screenshotUI;
        if (ui) {
            for (const id of this._screenshotSignals) {
                try { ui.disconnect(id); } catch (_) {}
            }
        }
        this._screenshotSignals = [];
    }

    _captureWithNativeUI(fromQuickSettings) {
        this._disconnectScreenshotSignals();
        const ui = Main.screenshotUI;
        if (!ui) {
            this._fail(this._t('nativeOpenFailed'), new Error('Main.screenshotUI is unavailable'));
            return;
        }

        const takenId = ui.connect('screenshot-taken', (_sender, file) => {
            this._disconnectScreenshotSignals();
            const path = file?.get_path?.();
            if (path)
                this._launchEditor(path);
        });
        const closedId = ui.connect('closed', () => this._disconnectScreenshotSignals());
        this._screenshotSignals = [takenId, closedId];

        const openUi = () => {
            ui.open(SCREENSHOT_ONLY_MODE).catch(error => {
                this._disconnectScreenshotSignals();
                this._fail(this._t('nativeOpenFailed'), error);
            });
            return GLib.SOURCE_REMOVE;
        };

        if (fromQuickSettings) {
            // Match GNOME Shell 46's own ScreenshotItem ordering: close the
            // Quick Settings menu without animation, then open screenshot UI
            // just before redraw.
            const topMenu = Main.panel.statusArea.quickSettings.menu;
            const laters = global.compositor.get_laters();
            laters.add(Meta.LaterType.BEFORE_REDRAW, openUi);
            topMenu.close(PopupAnimation.NONE);
        } else {
            openUi();
        }
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

    async _captureFull(fromQuickSettings) {
        let file;
        let stream;
        try {
            [file, stream] = this._newOutput();
            const shot = new Shell.Screenshot();
            const cursor = this._settings.get_boolean('include-cursor');
            await shot.screenshot(cursor, stream);
            stream.close(null);
            if (fromQuickSettings)
                Main.panel.closeQuickSettings();
            this._launchEditor(file.get_path());
        } catch (error) {
            try { stream?.close(null); } catch (_) {}
            this._fail(this._t('fullFailed'), error);
        }
    }

    async _captureWindow(fromQuickSettings) {
        let file;
        let stream;
        try {
            [file, stream] = this._newOutput();
            const shot = new Shell.Screenshot();
            const cursor = this._settings.get_boolean('include-cursor');
            await shot.screenshot_window(true, cursor, stream);
            stream.close(null);
            if (fromQuickSettings)
                Main.panel.closeQuickSettings();
            this._launchEditor(file.get_path());
        } catch (error) {
            try { stream?.close(null); } catch (_) {}
            this._fail(this._t('windowFailed'), error);
        }
    }

    _launchEditor(path) {
        try {
            const editorFile = Gio.File.new_for_path(EDITOR);
            if (!editorFile.query_exists(null)) {
                Main.notify('Zorin Shot', this._t('editorMissing'));
                return;
            }
            Gio.Subprocess.new([EDITOR, '--image', path], Gio.SubprocessFlags.NONE);
        } catch (error) {
            this._fail(this._t('editorLaunchFailed'), error);
        }
    }

    _fail(message, error) {
        logError(error, `${UUID}: ${message}`);
        Main.notify('Zorin Shot', `${message} ${error?.message ?? ''}`.trim());
    }

    _pruneCache(cacheDir) {
        try {
            const dir = Gio.File.new_for_path(cacheDir);
            const enumerator = dir.enumerate_children(
                'standard::name,time::modified', Gio.FileQueryInfoFlags.NONE, null);
            const now = Math.floor(GLib.get_real_time() / 1000000);
            let info;
            while ((info = enumerator.next_file(null)) !== null) {
                const age = now - info.get_modification_date_time().to_unix();
                if (age > 2 * 24 * 60 * 60)
                    dir.get_child(info.get_name()).delete(null);
            }
            enumerator.close(null);
        } catch (_) {
            // Best effort only.
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
            this._fail(this._t('keyFailed'), error);
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
        this._nativeSettings.set_strv(
            NATIVE_KEY, this._settings.get_strv('native-fallback-shortcut'));
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
                this._nativeSettings.set_strv(
                    NATIVE_KEY, this._settings.get_strv('saved-native-shortcut'));
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
