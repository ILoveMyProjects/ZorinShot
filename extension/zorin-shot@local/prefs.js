import Adw from 'gi://Adw';
import Gio from 'gi://Gio';
import Gtk from 'gi://Gtk';

import {ExtensionPreferences} from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';

const TEXT = {
    pl: {
        page: 'Zorin Shot',
        integration: 'Integracja z Zorin / GNOME',
        integrationDesc: 'Oryginalny aparat GNOME pozostaje bez zmian. Zorin Shot dodaje drugi przycisk bezpośrednio obok niego.',
        show: 'Pokaż nową ikonę obok oryginalnego aparatu',
        showSub: 'Nowa ikona otwiera natywny selektor GNOME i przekazuje wykonany zrzut do edytora Zorin Shot.',
        mode: 'Domyślny sposób przechwytywania',
        modeSub: 'Zalecany jest selektor GNOME: obszar, okno lub ekran.',
        modeNative: 'Selektor GNOME — obszar / okno / ekran',
        modeFull: 'Cały pulpit bez pytania',
        modeWindow: 'Aktywne okno bez pytania',
        cursor: 'Dołącz kursor myszy',
        keys: 'Klawisze',
        keysDesc: 'Po przejęciu Print Screen oryginalny panel GNOME pozostaje pod Super + Print Screen.',
        replace: 'Print Screen → Zorin Shot',
        replaceSub: 'Super + Print Screen → oryginalny screenshot / nagrywanie GNOME.',
        language: 'Język / Language',
        languageSub: 'Język interfejsu Zorin Shot i edytora.',
        editor: 'Wbudowany edytor',
        editorDesc: 'Edytor jest częścią Zorin Shot — Gradia nie jest wymagana.',
        tools: 'Narzędzia',
        toolsSub: 'Pióro, marker, strzałka, prostokąt, elipsa, tekst, pełna nieprzezroczysta cenzura, kadrowanie, undo/redo, kopiowanie i zapis PNG.',
    },
    en: {
        page: 'Zorin Shot',
        integration: 'Zorin / GNOME integration',
        integrationDesc: 'The original GNOME screenshot button remains unchanged. Zorin Shot adds a second button directly next to it.',
        show: 'Show the new icon next to the original screenshot button',
        showSub: 'The new icon opens GNOME’s native chooser and sends the captured image to the Zorin Shot editor.',
        mode: 'Default capture behavior',
        modeSub: 'GNOME chooser is recommended: area, window, or screen.',
        modeNative: 'GNOME chooser — area / window / screen',
        modeFull: 'Entire desktop immediately',
        modeWindow: 'Active window immediately',
        cursor: 'Include mouse pointer',
        keys: 'Keyboard shortcuts',
        keysDesc: 'When Print Screen is taken over, the original GNOME panel stays on Super + Print Screen.',
        replace: 'Print Screen → Zorin Shot',
        replaceSub: 'Super + Print Screen → original GNOME screenshot / screen recording.',
        language: 'Language / Język',
        languageSub: 'Language used by the Zorin Shot application and editor.',
        editor: 'Built-in editor',
        editorDesc: 'The editor is part of Zorin Shot — Gradia is not required.',
        tools: 'Tools',
        toolsSub: 'Pen, highlighter, arrow, rectangle, ellipse, text, fully opaque redaction, crop, undo/redo, copy and PNG save.',
    },
};

export default class ZorinShotPreferences extends ExtensionPreferences {
    fillPreferencesWindow(window) {
        const settings = this.getSettings();
        window._zorinShotSettings = settings;
        const lang = settings.get_string('language') === 'en' ? 'en' : 'pl';
        const t = TEXT[lang];

        const page = new Adw.PreferencesPage({
            title: t.page,
            icon_name: 'zorin-shot-symbolic',
        });
        window.add(page);

        const integration = new Adw.PreferencesGroup({
            title: t.integration,
            description: t.integrationDesc,
        });
        page.add(integration);

        const showButton = new Adw.SwitchRow({title: t.show, subtitle: t.showSub});
        integration.add(showButton);
        settings.bind('show-action-button', showButton, 'active', Gio.SettingsBindFlags.DEFAULT);

        const modeRow = new Adw.ComboRow({title: t.mode, subtitle: t.modeSub});
        modeRow.model = Gtk.StringList.new([t.modeNative, t.modeFull, t.modeWindow]);
        integration.add(modeRow);
        const modes = ['native', 'full', 'window'];
        let currentMode = settings.get_string('capture-mode');
        if (currentMode === 'region') {
            currentMode = 'native';
            settings.set_string('capture-mode', currentMode);
        }
        modeRow.selected = Math.max(0, modes.indexOf(currentMode));
        modeRow.connect('notify::selected', row => {
            if (row.selected < modes.length)
                settings.set_string('capture-mode', modes[row.selected]);
        });

        const cursor = new Adw.SwitchRow({title: t.cursor});
        integration.add(cursor);
        settings.bind('include-cursor', cursor, 'active', Gio.SettingsBindFlags.DEFAULT);

        const keyboard = new Adw.PreferencesGroup({title: t.keys, description: t.keysDesc});
        page.add(keyboard);
        const replacePrint = new Adw.SwitchRow({title: t.replace, subtitle: t.replaceSub});
        keyboard.add(replacePrint);
        settings.bind('replace-print-screen', replacePrint, 'active', Gio.SettingsBindFlags.DEFAULT);

        const language = new Adw.PreferencesGroup({title: t.language, description: t.languageSub});
        page.add(language);
        const languageRow = new Adw.ComboRow({title: t.language});
        languageRow.model = Gtk.StringList.new(['Polski', 'English']);
        languageRow.selected = lang === 'en' ? 1 : 0;
        language.add(languageRow);
        languageRow.connect('notify::selected', row => {
            settings.set_string('language', row.selected === 1 ? 'en' : 'pl');
        });

        const editor = new Adw.PreferencesGroup({title: t.editor, description: t.editorDesc});
        page.add(editor);
        editor.add(new Adw.ActionRow({title: t.tools, subtitle: t.toolsSub}));
    }
}
