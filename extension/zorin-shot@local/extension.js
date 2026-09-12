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
const SCREENSHOT_ONLY_MODE = 2; // GNOME Shell 46: UIMode.SCREENSHOT_ONLY
const EDITOR = GLib.build_filenamev([
    GLib.get_home_dir(), '.local', 'lib', 'zorin-shot', 'zorin-shot-editor.py',
]);

const TEXT = {
    pl: {
        action: 'Zorin Shot — zrzut z adnotacjami',
        editorMissing: 'Brak edytora Zorin Shot. Uruchom ponownie instalator.',
        editorLaunchFailed: 'Zrzut został wykonany, ale nie udało się uruchomić edytora.',
        nativeOpenFailed: 'Nie udało się otworzyć systemowego selektora zrzutu ekranu.',
        fullFailed: 'Nie udało się zrobić zrzutu całego pulpitu.',
        windowFailed: 'Nie udało się przechwycić aktywnego okna.',
        keyFailed: 'Nie udało się przejąć klawisza Print Screen.',
    },
    en: {
        action: 'Zorin Shot — annotated screenshot',
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
        this._quickSettingsMenuSignal = 0;

        this._watchQuickSettingsMenu();
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
        this._unwatchQuickSettingsMenu();
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
        const value = this._settings?.get_string('language') ?? 'en';
        return value === 'pl' ? 'pl' : 'en';
    }

    _t(key) {
        return TEXT[this._language()][key] ?? TEXT.en[key] ?? key;
    }

    _watchQuickSettingsMenu() {
        const menu = Main.panel.statusArea.quickSettings?.menu;
        if (!menu || this._quickSettingsMenuSignal)
            return;
        this._quickSettingsMenuSignal = menu.connect('open-state-changed', (_menu, isOpen) => {
            if (!isOpen || !this._settings?.get_boolean('show-action-button'))
                return;
            // Zorin Taskbar can rebuild/move the system menu. Validate our parent
            // every time the menu opens and reinsert the button if necessary.
            if (this._button && !this._button.get_parent?.())
                this._button = null;
            if (!this._button)
                this._tryAddButton();
        });
    }

    _unwatchQuickSettingsMenu() {
        const menu = Main.panel.statusArea.quickSettings?.menu;
        if (menu && this._quickSettingsMenuSignal) {
            try { menu.disconnect(this._quickSettingsMenuSignal); } catch (_) {}
        }
        this._quickSettingsMenuSignal = 0;
    }

    _syncButton() {
        if (this._settings.get_boolean('show-action-button'))
            this._scheduleButtonAdd();
        else {
            this._cancelButtonRetry();
            this._removeButton();
        }
    }

    _iconName(actor) {
        if (!actor)
            return '';
        for (const value of [actor.iconName, actor.icon_name]) {
            if (value)
                return String(value);
        }
        try {
            const value = actor.get_property?.('icon-name');
            if (value)
                return String(value);
        } catch (_) {}
        try {
            const child = actor.get_child?.();
            if (child && child !== actor)
                return this._iconName(child);
        } catch (_) {}
        return '';
    }

    _isScreenshotButton(actor) {
        const icon = this._iconName(actor);
        return icon === 'screenshooter-symbolic' ||
            icon.includes('screenshot') || icon.includes('screenshooter');
    }

    _containsScreenshotButton(actor) {
        if (!actor)
            return false;
        if (this._isScreenshotButton(actor))
            return true;
        let children = [];
        try { children = actor.get_children?.() ?? []; } catch (_) {}
        return children.some(child => this._containsScreenshotButton(child));
    }

    _systemActionBox() {
        const quickSettings = Main.panel.statusArea.quickSettings;
        if (!quickSettings)
            return null;

        // 1. Stock GNOME 46 SystemStatus.Indicator keeps SystemItem in both
        // _systemItem and quickSettingsItems. The array is the more robust path
        // for distro patches that rename the private field.
        const indicator = quickSettings._system ?? null;
        const candidates = [];
        if (indicator?._systemItem)
            candidates.push(indicator._systemItem);
        try {
            for (const item of indicator?.quickSettingsItems ?? [])
                candidates.push(item);
        } catch (_) {}

        // 2. Fallback: find the system item directly in QuickSettingsMenu grid.
        try {
            for (const item of quickSettings.menu?._grid?.get_children?.() ?? [])
                candidates.push(item);
        } catch (_) {}

        const seen = new Set();
        for (const item of candidates) {
            if (!item || seen.has(item))
                continue;
            seen.add(item);

            let isSystemItem = false;
            try {
                isSystemItem = item.has_style_class_name?.('quick-settings-system-item') ?? false;
            } catch (_) {}
            if (!isSystemItem)
                isSystemItem = this._containsScreenshotButton(item);
            if (!isSystemItem)
                continue;

            const box = item.child ?? item.get_child?.() ?? null;
            if (box?.get_children)
                return box;
        }

        return null;
    }

    _scheduleButtonAdd() {
        if (this._button?.get_parent?.())
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
            // Do not show a user-facing error. Zorin Taskbar can construct the
            // row later; _watchQuickSettingsMenu() will retry whenever it opens.
            if (this._buttonRetryCount >= 80) {
                console.warn(`${UUID}: Quick Settings system action row not ready; will retry on menu open`);
                this._buttonRetryId = 0;
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
        if (this._button?.get_parent?.())
            return true;
        this._button = null;

        const box = this._systemActionBox();
        if (!box)
            return false;

        const button = new QuickSettings.QuickSettingsItem({
            style_class: 'icon-button',
            can_focus: true,
            icon_name: 'zorin-shot-symbolic',
            accessible_name: this._t('action'),
        });
        button.connect('clicked', () => this._capture(true));

        const children = box.get_children();
        let stockIndex = children.findIndex(child => this._isScreenshotButton(child));
        // Stock GNOME 46 SystemItem order is: power, spacer, screenshot,
        // settings, spacer, lock, shutdown. If a Zorin patch obscures the icon
        // property but keeps that row, index 2 is still the screenshot action.
        if (stockIndex < 0 && children.length >= 5)
            stockIndex = 2;
        if (stockIndex < 0) {
            button.destroy();
            return false;
        }

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

    _capture(_fromQuickSettings) {
        let mode = this._settings.get_string('capture-mode');
        if (mode === 'region')
            mode = 'native';

        if (mode === 'full')
            this._captureFull();
        else if (mode === 'window')
            this._captureWindow();
        else
            this._captureWithNativeUI();
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

    _captureWithNativeUI() {
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

        try {
            // GNOME 46 remembers the last screenshot type. Zorin Shot must open
            // on Area Selection, so explicitly select it every time.
            if (ui._selectionButton)
                ui._selectionButton.checked = true;
            if (ui._showPointerButton)
                ui._showPointerButton.checked = this._settings.get_boolean('include-cursor');

            // IMPORTANT: do not close Quick Settings here. ScreenshotUI.open()
            // first snapshots the current stage and only afterwards emits
            // system-modal-opened, which closes popup menus. This preserves the
            // open Zorin/GNOME menu in the frozen screenshot while still giving
            // the user the native area/window/screen chooser.
            ui.open(SCREENSHOT_ONLY_MODE).catch(error => {
                this._disconnectScreenshotSignals();
                this._fail(this._t('nativeOpenFailed'), error);
            });
        } catch (error) {
            this._disconnectScreenshotSignals();
            this._fail(this._t('nativeOpenFailed'), error);
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

    async _captureFull() {
        let file;
        let stream;
        try {
            [file, stream] = this._newOutput();
            const shot = new Shell.Screenshot();
            const cursor = this._settings.get_boolean('include-cursor');
            await shot.screenshot(cursor, stream);
            stream.close(null);
            Main.panel.closeQuickSettings();
            this._launchEditor(file.get_path());
        } catch (error) {
            try { stream?.close(null); } catch (_) {}
            this._fail(this._t('fullFailed'), error);
        }
    }

    async _captureWindow() {
        let file;
        let stream;
        try {
            [file, stream] = this._newOutput();
            const shot = new Shell.Screenshot();
            const cursor = this._settings.get_boolean('include-cursor');
            await shot.screenshot_window(true, cursor, stream);
            stream.close(null);
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
