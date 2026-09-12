import Adw from 'gi://Adw';
import Gio from 'gi://Gio';
import Gtk from 'gi://Gtk';

import {ExtensionPreferences} from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';

export default class ZorinShotPreferences extends ExtensionPreferences {
    fillPreferencesWindow(window) {
        const settings = this.getSettings();
        window._zorinShotSettings = settings;

        const page = new Adw.PreferencesPage({
            title: 'Zorin Shot',
            icon_name: 'camera-photo-symbolic',
        });
        window.add(page);

        const integration = new Adw.PreferencesGroup({
            title: 'Integracja z Zorin / GNOME',
            description: 'Oryginalny przycisk aparatu pozostaje bez zmian. Zorin Shot dodaje drugi przycisk tuż obok niego.',
        });
        page.add(integration);

        const showButton = new Adw.SwitchRow({
            title: 'Pokaż nową ikonę obok oryginalnego aparatu',
            subtitle: 'Nowa ikona uruchamia Zorin Shot. Stara nadal otwiera systemowy screenshot i nagrywanie ekranu.',
        });
        integration.add(showButton);
        settings.bind('show-action-button', showButton, 'active', Gio.SettingsBindFlags.DEFAULT);

        const modeRow = new Adw.ComboRow({
            title: 'Domyślny tryb nowego przycisku',
            subtitle: '„Obszar” najpierw zamraża cały widoczny pulpit — razem z otwartymi menu — a potem pozwala zaznaczyć fragment.',
        });
        const modeModel = Gtk.StringList.new([
            'Obszar — zachowaj otwarte menu',
            'Cały widoczny pulpit',
            'Aktywne okno',
        ]);
        modeRow.model = modeModel;
        integration.add(modeRow);

        const modes = ['region', 'full', 'window'];
        const current = modes.indexOf(settings.get_string('capture-mode'));
        modeRow.selected = current >= 0 ? current : 0;
        modeRow.connect('notify::selected', row => {
            const index = row.selected;
            if (index >= 0 && index < modes.length)
                settings.set_string('capture-mode', modes[index]);
        });
        const modeSignal = settings.connect('changed::capture-mode', () => {
            const index = modes.indexOf(settings.get_string('capture-mode'));
            if (index >= 0 && modeRow.selected !== index)
                modeRow.selected = index;
        });
        window.connect('close-request', () => {
            try { settings.disconnect(modeSignal); } catch (_) {}
            return false;
        });

        const cursor = new Adw.SwitchRow({
            title: 'Dołącz kursor myszy',
        });
        integration.add(cursor);
        settings.bind('include-cursor', cursor, 'active', Gio.SettingsBindFlags.DEFAULT);

        const keyboard = new Adw.PreferencesGroup({
            title: 'Klawisze',
            description: 'Po przejęciu Print Screen oryginalny panel GNOME pozostaje pod Super+Print Screen.',
        });
        page.add(keyboard);

        const replacePrint = new Adw.SwitchRow({
            title: 'Print Screen → Zorin Shot',
            subtitle: 'Super+Print Screen → oryginalny screenshot / nagrywanie GNOME.',
        });
        keyboard.add(replacePrint);
        settings.bind('replace-print-screen', replacePrint, 'active', Gio.SettingsBindFlags.DEFAULT);

        const editor = new Adw.PreferencesGroup({
            title: 'Wbudowany edytor',
            description: 'Edytor jest częścią Zorin Shot — Gradia nie jest wymagana.',
        });
        page.add(editor);

        const features = new Adw.ActionRow({
            title: 'Narzędzia',
            subtitle: 'Pióro, zakreślacz, strzałka, prostokąt, elipsa, tekst, cenzura, kadrowanie, cofanie/ponawianie, kopiowanie i zapis PNG.',
        });
        editor.add(features);
    }
}
