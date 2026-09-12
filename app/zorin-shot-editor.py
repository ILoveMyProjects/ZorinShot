#!/usr/bin/env python3
import argparse
import copy
import json
import math
import os
import sys
import tempfile
from pathlib import Path

try:
    import gi
    gi.require_version('Gtk', '4.0')
    gi.require_version('Gdk', '4.0')
    from gi.repository import Gtk, Gdk, Gio, GLib
    import cairo
    from i18n import tr
except Exception as exc:
    sys.stderr.write(
        'Zorin Shot: missing GTK/PyGObject dependencies.\n'
        'Install: sudo apt install python3-gi python3-cairo gir1.2-gtk-4.0\n'
        f'Detail: {exc}\n'
    )
    raise SystemExit(2)

APP_ID = 'io.local.ZorinShot.Editor'
SCHEMA_ID = 'org.gnome.shell.extensions.zorin-shot'
EXT_SCHEMA_DIR = Path.home() / '.local/share/gnome-shell/extensions/zorin-shot@local/schemas'
EDITOR_STATE_PATH = Path.home() / '.config' / 'zorin-shot' / 'editor-state.json'
APP_DIR = Path.home() / '.local' / 'lib' / 'zorin-shot'


def detect_system_language():
    values = [
        os.environ.get('LANGUAGE', ''),
        os.environ.get('LC_ALL', ''),
        os.environ.get('LC_MESSAGES', ''),
        os.environ.get('LANG', ''),
    ]
    for value in values:
        for part in str(value).split(':'):
            code = part.strip().lower().replace('-', '_')
            if code.startswith('pl'):
                return 'pl'
            if code.startswith('en'):
                return 'en'
    return 'en'


def _load_app_settings():
    try:
        source = Gio.SettingsSchemaSource.new_from_directory(
            str(EXT_SCHEMA_DIR), Gio.SettingsSchemaSource.get_default(), False)
        schema = source.lookup(SCHEMA_ID, False)
        if schema is None:
            return None
        return Gio.Settings.new_full(schema, None, None)
    except Exception:
        return None


def read_language():
    fallback = detect_system_language()
    settings = _load_app_settings()
    if settings is None:
        return fallback
    try:
        value = settings.get_string('language')
        return value if value in ('pl', 'en') else fallback
    except Exception:
        return fallback


def read_theme():
    settings = _load_app_settings()
    if settings is None:
        return 'system'
    try:
        value = settings.get_string('app-theme')
        return value if value in ('system', 'dark', 'light') else 'system'
    except Exception:
        return 'system'


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def norm_rect(x1, y1, x2, y2):
    left = min(x1, x2)
    top = min(y1, y2)
    right = max(x1, x2)
    bottom = max(y1, y2)
    return left, top, right - left, bottom - top


def rgba_tuple(rgba):
    return (rgba.red, rgba.green, rgba.blue, rgba.alpha)


def to_rgba(color):
    rgba = Gdk.RGBA()
    rgba.red, rgba.green, rgba.blue, rgba.alpha = color
    return rgba


def load_editor_state():
    try:
        return json.loads(EDITOR_STATE_PATH.read_text(encoding='utf-8'))
    except Exception:
        return {'confirm_close': True}


def save_editor_state(state):
    try:
        EDITOR_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        EDITOR_STATE_PATH.write_text(json.dumps(state, indent=2), encoding='utf-8')
    except Exception:
        pass


class EditorWindow(Gtk.ApplicationWindow):
    TOOL_ORDER = ['pen', 'highlighter', 'line', 'arrow', 'rect', 'ellipse', 'text', 'number', 'redact', 'crop', 'move']

    def __init__(self, app, image_path, select_region=False):
        super().__init__(application=app, title='Zorin Shot')
        self.set_property('icon-name', APP_ID)
        self.app_settings = _load_app_settings()
        self.lang = read_language()
        self.theme = read_theme()
        self.editor_state = load_editor_state()
        self.set_default_size(1460, 920)
        self.maximize()

        self.image_path = Path(image_path)
        try:
            self.base = cairo.ImageSurface.create_from_png(str(self.image_path))
        except Exception as exc:
            raise RuntimeError(self._t('png_open_failed', error=exc)) from exc

        self.img_w = self.base.get_width()
        self.img_h = self.base.get_height()
        self.zoom = 1.0
        self.auto_fit = True
        self.fit_margin = 36
        self.tool = 'crop' if select_region else 'pen'
        self.annotations = []
        self.undo_stack = []
        self.redo_stack = []
        self.selected_index = None
        self.drag_mode = None
        self.drag_start = None
        self.drag_current = None
        self.current_points = None
        self.preview_annotation = None
        self.move_snapshot = None
        self.viewport_w = 1100
        self.viewport_h = 760
        self.offset_x = 0
        self.offset_y = 0
        self._save_dialog = None
        self._closing_programmatically = False
        self._suspend_list_selection = False
        self.render_surface = None

        self.config = {
            'pen': {'color': (0.12, 0.18, 0.25, 1.0), 'width': 4.0, 'opacity': 1.0},
            'highlighter': {'color': (1.0, 0.92, 0.15, 1.0), 'width': 18.0, 'opacity': 0.35},
            'line': {'color': (0.12, 0.18, 0.25, 1.0), 'width': 5.0, 'opacity': 1.0},
            'arrow': {'color': (0.95, 0.25, 0.25, 1.0), 'width': 5.0, 'opacity': 1.0},
            'rect': {
                'stroke_color': (0.12, 0.18, 0.25, 1.0), 'width': 5.0,
                'fill_enabled': False, 'fill_color': (0.20, 0.56, 0.98, 1.0), 'fill_opacity': 0.22,
            },
            'ellipse': {
                'stroke_color': (0.12, 0.18, 0.25, 1.0), 'width': 5.0,
                'fill_enabled': False, 'fill_color': (0.20, 0.56, 0.98, 1.0), 'fill_opacity': 0.22,
            },
            'text': {
                'color': (0.10, 0.10, 0.10, 1.0), 'size': 28.0,
                'bg_enabled': False, 'bg_color': (1.0, 1.0, 1.0, 1.0), 'bg_opacity': 0.84,
                'padding': 8.0,
            },
            'number': {
                'text_color': (1.0, 1.0, 1.0, 1.0), 'size': 22.0,
                'fill_color': (0.22, 0.56, 0.98, 1.0), 'fill_opacity': 1.0,
                'radius': 20.0, 'border_color': (1.0, 1.0, 1.0, 1.0), 'border_width': 2.0,
            },
            'redact': {'block_size': 16.0},
        }
        self.next_number = 1

        self._apply_theme()
        if self.app_settings is not None:
            try:
                self.app_settings.connect('changed::app-theme', self._theme_setting_changed)
            except Exception:
                pass
        self.connect('close-request', self._on_close_request)
        self._build_ui(select_region)
        self._fit_to_view(allow_enlarge=True)

    def _t(self, key, **kwargs):
        return tr(self.lang, key, **kwargs)

    def _L(self, pl, en):
        return pl if self.lang == 'pl' else en

    def _apply_theme(self):
        if self.theme == 'system':
            dark = False
            try:
                dark = Gio.Settings.new('org.gnome.desktop.interface').get_string('color-scheme') == 'prefer-dark'
            except Exception:
                pass
        else:
            dark = self.theme == 'dark'
        gtk_settings = Gtk.Settings.get_default()
        if gtk_settings is not None:
            gtk_settings.set_property('gtk-application-prefer-dark-theme', dark)
        display = Gdk.Display.get_default()
        if getattr(self, '_theme_provider', None) is not None and display is not None:
            try:
                Gtk.StyleContext.remove_provider_for_display(display, self._theme_provider)
            except Exception:
                pass
        provider = Gtk.CssProvider()
        bg_sidebar = '#202226' if dark else '#f4f5f7'
        bg_card = '#292c31' if dark else '#ffffff'
        fg_dim = '#b7bec8' if dark else '#5f6368'
        border = '#3b3f46' if dark else '#d8dce2'
        self.canvas_bg = (0.065, 0.072, 0.085) if dark else (0.94, 0.95, 0.97)
        self.canvas_shadow_alpha = 0.36 if dark else 0.08
        css = f'''
        .sidebar-shell, .sidebar-shell > viewport, .sidebar {{ background-color: {bg_sidebar}; }}
        .section-card {{ background: {bg_card}; border: 1px solid {border}; border-radius: 12px; padding: 0; }}
        .section-title {{ background-color: transparent; padding: 0 6px 5px 6px; font-weight: 700; }}
        .section-body {{ padding: 10px; }}
        .card {{ background: {bg_card}; border: 1px solid {border}; border-radius: 12px; }}
        .tool-button {{ padding: 3px; min-width: 36px; min-height: 36px; border-radius: 8px; }}
        .toolbar-button {{ padding: 3px; min-width: 34px; min-height: 34px; }}
        .dim-tint {{ color: {fg_dim}; }}
        .topbar {{ padding: 2px; }}
        '''
        provider.load_from_data(css.encode('utf-8'))
        if display is not None:
            Gtk.StyleContext.add_provider_for_display(display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self._theme_provider = provider

    def _theme_setting_changed(self, settings, _key):
        try:
            value = settings.get_string('app-theme')
            self.theme = value if value in ('system', 'dark', 'light') else 'system'
        except Exception:
            self.theme = 'system'
        self._apply_theme()
        if hasattr(self, 'canvas'):
            self.canvas.queue_draw()

    def _display_name(self, tool):
        names = {
            'move': self._L('Przesuń', 'Move'),
            'crop': self._L('Kadruj', 'Crop'),
            'pen': self._L('Pióro', 'Pen'),
            'highlighter': self._L('Marker', 'Highlighter'),
            'line': self._L('Linia', 'Line'),
            'arrow': self._L('Strzałka', 'Arrow'),
            'rect': self._L('Prostokąt', 'Rectangle'),
            'ellipse': self._L('Owal', 'Oval'),
            'text': self._L('Tekst', 'Text'),
            'number': self._L('Numer', 'Number'),
            'redact': self._L('Cenzura', 'Redact'),
        }
        return names.get(tool, tool)

    def _tool_hint(self, tool):
        hints = {
            'move': self._L('Kliknij element i przeciągnij, aby go przesunąć.', 'Click an element and drag it to move it.'),
            'crop': self._L('Przeciągnij prostokąt, aby wykadrować obraz.', 'Drag a rectangle to crop the image.'),
            'pen': self._L('Rysuj swobodnie.', 'Draw freely.'),
            'highlighter': self._L('Zaznaczaj półprzezroczystym kolorem.', 'Highlight with a translucent color.'),
            'line': self._L('Przeciągnij od początku do końca linii.', 'Drag from start to end of the line.'),
            'arrow': self._L('Przeciągnij od początku do końca strzałki.', 'Drag from start to end of the arrow.'),
            'rect': self._L('Przeciągnij, aby narysować prostokąt.', 'Drag to draw a rectangle.'),
            'ellipse': self._L('Przeciągnij, aby narysować owal.', 'Drag to draw an oval.'),
            'text': self._L('Kliknij miejsce i wpisz tekst.', 'Click a location and enter text.'),
            'number': self._L('Klikaj kolejne miejsca, aby wstawiać numery 1, 2, 3…', 'Click locations to place numbered circles 1, 2, 3…'),
            'redact': self._L('Przeciągnij obszar, aby go ocenzurować pikselami.', 'Drag an area to pixelate it.'),
        }
        return hints.get(tool, '')

    def _make_icon_button(self, icon_name, tooltip, callback):
        btn = Gtk.Button()
        btn.add_css_class('toolbar-button')
        image = Gtk.Image.new_from_icon_name(icon_name)
        image.set_pixel_size(18)
        btn.set_child(image)
        btn.set_tooltip_text(tooltip)
        btn.connect('clicked', callback)
        return btn

    def _toolbar_separator(self):
        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        sep.set_margin_start(4)
        sep.set_margin_end(4)
        sep.set_margin_top(5)
        sep.set_margin_bottom(5)
        return sep

    def _open_settings(self, *_args):
        candidates = [APP_DIR / 'zorin-shot-control.py', Path(__file__).with_name('zorin-shot-control.py')]
        for path in candidates:
            if path.is_file():
                try:
                    Gio.Subprocess.new([sys.executable, str(path)], Gio.SubprocessFlags.NONE)
                    return
                except Exception as exc:
                    self._error(self._L(f'Nie udało się otworzyć ustawień: {exc}', f'Could not open settings: {exc}'))
                    return
        self._error(self._L('Nie znaleziono centrum ustawień Zorin Shot.', 'Zorin Shot settings center was not found.'))

    def _build_ui(self, select_region):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_child(root)

        header = Gtk.HeaderBar()
        header.set_show_title_buttons(True)
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        title = Gtk.Label(label='Zorin Shot')
        title.add_css_class('title')
        subtitle = Gtk.Label(label=self._L('Edytor adnotacji', 'Annotation editor'))
        subtitle.add_css_class('dim-label')
        title_box.append(title)
        title_box.append(subtitle)
        header.set_title_widget(title_box)
        settings_btn = Gtk.Button()
        settings_img = Gtk.Image.new_from_icon_name('preferences-system-symbolic')
        settings_img.set_pixel_size(18)
        settings_btn.set_child(settings_img)
        settings_btn.set_tooltip_text(self._L('Ustawienia Zorin Shot', 'Zorin Shot settings'))
        settings_btn.connect('clicked', self._open_settings)
        header.pack_end(settings_btn)
        self.set_titlebar(header)

        topbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        topbar.add_css_class('topbar')
        topbar.set_margin_start(10)
        topbar.set_margin_end(10)
        topbar.set_margin_top(6)
        topbar.set_margin_bottom(6)
        root.append(topbar)

        # History / editing
        topbar.append(self._make_icon_button('edit-undo-symbolic', self._t('undo'), self._undo))
        topbar.append(self._make_icon_button('edit-redo-symbolic', self._t('redo'), self._redo))
        delete_btn = self._make_icon_button('user-trash-symbolic', self._L('Usuń zaznaczone', 'Delete selected'), lambda *_: self._delete_selected())
        delete_btn.add_css_class('destructive-action')
        topbar.append(delete_btn)
        topbar.append(self._toolbar_separator())

        # View / zoom
        topbar.append(self._make_icon_button('zoom-out-symbolic', self._t('zoom_out'), lambda *_: self._manual_zoom(1 / 1.15)))
        topbar.append(self._make_icon_button('zoom-fit-best-symbolic', self._t('fit'), lambda *_: self._fit_to_view(allow_enlarge=True)))
        topbar.append(self._make_icon_button('zoom-in-symbolic', self._t('zoom_in'), lambda *_: self._manual_zoom(1.15)))

        self.zoom_label = Gtk.Label(label='100%')
        self.zoom_label.add_css_class('dim-label')
        self.zoom_label.set_margin_start(6)
        self.zoom_label.set_margin_end(4)
        topbar.append(self.zoom_label)
        topbar.append(self._toolbar_separator())

        # Output
        topbar.append(self._make_icon_button('edit-copy-symbolic', self._t('copy'), lambda *_: self._copy_to_clipboard()))
        topbar.append(self._make_icon_button('document-save-symbolic', self._t('save_as'), lambda *_: self._save_as()))

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        topbar.append(spacer)

        self.hint_label = Gtk.Label(label=self._tool_hint(self.tool), xalign=1)
        self.hint_label.add_css_class('dim-label')
        topbar.append(self.hint_label)

        main = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        main.set_hexpand(True)
        main.set_vexpand(True)
        root.append(main)

        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        left.set_hexpand(True)
        left.set_vexpand(True)
        main.append(left)

        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_hexpand(True)
        self.scroll.set_vexpand(True)
        self.scroll.connect('notify::width', self._viewport_changed)
        self.scroll.connect('notify::height', self._viewport_changed)
        left.append(self.scroll)

        self.canvas = Gtk.DrawingArea()
        self.canvas.set_hexpand(True)
        self.canvas.set_vexpand(True)
        self.canvas.set_draw_func(self._draw, None)
        self.scroll.set_child(self.canvas)

        self.status = Gtk.Label(xalign=0, wrap=True)
        self.status.set_margin_start(12)
        self.status.set_margin_end(12)
        self.status.set_margin_top(6)
        self.status.set_margin_bottom(8)
        self.status.set_text(self._t('region_hint') if select_region else self._tool_hint(self.tool))
        left.append(self.status)

        sidebar_scroll = Gtk.ScrolledWindow()
        sidebar_scroll.add_css_class('sidebar-shell')
        sidebar_scroll.set_size_request(350, -1)
        sidebar_scroll.set_min_content_width(350)
        sidebar_scroll.set_hexpand(False)
        sidebar_scroll.set_vexpand(True)
        main.append(sidebar_scroll)

        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        right.add_css_class('sidebar')
        # Sidebar is anchored to the top of its own viewport. Do not tie its
        # position to the vertically centered image; otherwise small screenshots
        # push the entire Tools panel down and make it appear late/centered.
        right.set_margin_top(0)
        right.set_margin_bottom(10)
        right.set_margin_start(10)
        right.set_margin_end(12)
        sidebar_scroll.set_child(right)

        # Tools: title is outside the card; only the controls are framed.
        tools_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        tools_section.append(self._section_title(self._L('Narzędzia', 'Tools')))
        tools_frame = Gtk.Frame()
        tools_frame.add_css_class('section-card')
        tool_body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        tool_body.add_css_class('section-body')
        tools_frame.set_child(tool_body)
        tools_section.append(tools_frame)
        right.append(tools_section)

        tool_box = Gtk.FlowBox()
        tool_box.set_min_children_per_line(6)
        tool_box.set_max_children_per_line(6)
        tool_box.set_selection_mode(Gtk.SelectionMode.NONE)
        tool_box.set_valign(Gtk.Align.START)
        tool_box.set_row_spacing(6)
        tool_box.set_column_spacing(6)
        tool_body.append(tool_box)

        self.tool_buttons = {}
        group_leader = None
        tool_icons = {
            'move': 'zorin-shot-tool-move-symbolic',
            'crop': 'zorin-shot-tool-crop-symbolic',
            'pen': 'zorin-shot-tool-pen-symbolic',
            'highlighter': 'zorin-shot-tool-highlighter-symbolic',
            'line': 'zorin-shot-tool-line-symbolic',
            'arrow': 'zorin-shot-tool-arrow-symbolic',
            'rect': 'zorin-shot-tool-rect-symbolic',
            'ellipse': 'zorin-shot-tool-ellipse-symbolic',
            'text': 'zorin-shot-tool-text-symbolic',
            'number': 'zorin-shot-tool-number-symbolic',
            'redact': 'zorin-shot-tool-redact-symbolic',
        }
        for key in self.TOOL_ORDER:
            btn = Gtk.ToggleButton()
            btn.add_css_class('tool-button')
            btn.set_size_request(38, 38)
            image = Gtk.Image.new_from_icon_name(tool_icons[key])
            image.set_pixel_size(20)
            btn.set_child(image)
            btn.set_tooltip_text(self._display_name(key))
            if group_leader is None:
                group_leader = btn
            else:
                btn.set_group(group_leader)
            btn.connect('toggled', self._on_tool_toggled, key)
            self.tool_buttons[key] = btn
            tool_box.insert(btn, -1)
        self.tool_buttons[self.tool].set_active(True)

        # Dynamic tool options: title outside the card; card height follows active content.
        options_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        options_section.append(self._section_title(self._L('Opcje narzędzia', 'Tool options')))
        options_frame = Gtk.Frame()
        options_frame.add_css_class('section-card')
        options_wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        options_wrap.add_css_class('section-body')
        self.options_stack = Gtk.Stack()
        self.options_stack.set_transition_type(Gtk.StackTransitionType.NONE)
        self.options_stack.set_hhomogeneous(False)
        self.options_stack.set_vhomogeneous(False)
        self.options_stack.set_vexpand(False)
        self.options_stack.set_valign(Gtk.Align.START)
        options_wrap.set_vexpand(False)
        options_frame.set_vexpand(False)
        self._build_option_pages()
        options_wrap.append(self.options_stack)
        options_frame.set_child(options_wrap)
        options_section.append(options_frame)
        right.append(options_section)

        # Elements: title outside; list grows naturally and then scrolls.
        elements_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        elements_section.append(self._section_title(self._L('Elementy', 'Elements')))
        elements_frame = Gtk.Frame()
        elements_frame.add_css_class('section-card')
        elements_holder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        elements_holder.add_css_class('section-body')
        elements_frame.set_child(elements_holder)
        elements_section.append(elements_frame)
        right.append(elements_section)

        elements_scroll = Gtk.ScrolledWindow()
        elements_scroll.set_min_content_height(56)
        elements_scroll.set_max_content_height(240)
        elements_scroll.set_propagate_natural_height(True)
        elements_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        elements_holder.append(elements_scroll)

        self.elements_list = Gtk.ListBox()
        self.elements_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.elements_list.connect('row-selected', self._row_selected)
        elements_scroll.set_child(self.elements_list)

        row_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        elements_holder.append(row_actions)
        row_actions.append(self._make_icon_button('go-up-symbolic', self._L('Przesuń wyżej', 'Move up'), lambda *_: self._reorder_selected(-1)))
        row_actions.append(self._make_icon_button('go-down-symbolic', self._L('Przesuń niżej', 'Move down'), lambda *_: self._reorder_selected(1)))
        row_actions.append(self._make_icon_button('user-trash-symbolic', self._L('Usuń zaznaczone', 'Delete selected'), lambda *_: self._delete_selected()))

        # Image details: title outside the card.
        image_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        image_section.append(self._section_title(self._L('Szczegóły obrazu', 'Image details')))
        image_frame = Gtk.Frame()
        image_frame.add_css_class('section-card')
        image_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        image_box.add_css_class('section-body')
        image_frame.set_child(image_box)
        image_section.append(image_frame)
        right.append(image_section)
        self.details_label = Gtk.Label(xalign=0, wrap=True)
        image_box.append(self.details_label)

        drag = Gtk.GestureDrag()
        drag.set_button(1)
        drag.connect('drag-begin', self._drag_begin)
        drag.connect('drag-update', self._drag_update)
        drag.connect('drag-end', self._drag_end)
        self.canvas.add_controller(drag)

        click = Gtk.GestureClick()
        click.set_button(1)
        click.connect('pressed', self._click_pressed)
        self.canvas.add_controller(click)

        # Ctrl + mouse wheel zooms the image instead of scrolling the viewport.
        zoom_scroll = Gtk.EventControllerScroll.new(Gtk.EventControllerScrollFlags.VERTICAL)
        zoom_scroll.connect('scroll', self._on_zoom_scroll)
        self.canvas.add_controller(zoom_scroll)

        keys = Gtk.EventControllerKey()
        keys.connect('key-pressed', self._key_pressed)
        self.add_controller(keys)

        self._update_details()
        self._refresh_elements_list()
        self._sync_option_pages()

    def _section_title(self, text):
        label = Gtk.Label(label=text, xalign=0)
        label.add_css_class('heading')
        label.add_css_class('section-title')
        label.set_margin_start(2)
        label.set_margin_end(2)
        label.set_margin_top(0)
        label.set_margin_bottom(4)
        return label

    def _build_option_pages(self):
        move_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        move_page.append(Gtk.Label(label=self._tool_hint('move'), xalign=0, wrap=True))
        self.options_stack.add_named(move_page, 'move')

        crop_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        crop_page.append(Gtk.Label(label=self._tool_hint('crop'), xalign=0, wrap=True))
        self.options_stack.add_named(crop_page, 'crop')

        self.options_stack.add_named(self._penlike_page('pen'), 'pen')
        self.options_stack.add_named(self._penlike_page('highlighter', alpha=True), 'highlighter')
        self.options_stack.add_named(self._line_page('line'), 'line')
        self.options_stack.add_named(self._line_page('arrow'), 'arrow')
        self.options_stack.add_named(self._shape_page('rect'), 'rect')
        self.options_stack.add_named(self._shape_page('ellipse'), 'ellipse')
        self.options_stack.add_named(self._text_page(), 'text')
        self.options_stack.add_named(self._number_page(), 'number')
        self.options_stack.add_named(self._redact_page(), 'redact')

    def _penlike_page(self, key, alpha=False):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self._add_color_row(box, self._L('Kolor', 'Color'), key, 'color')
        self._add_scale_row(box, self._L('Rozmiar', 'Size'), key, 'width', 1, 80, 1)
        if alpha:
            self._add_scale_row(box, self._L('Przezroczystość', 'Opacity'), key, 'opacity', 0.05, 1.0, 0.01)
        return box

    def _line_page(self, key):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self._add_color_row(box, self._L('Kolor', 'Color'), key, 'color')
        self._add_scale_row(box, self._L('Grubość', 'Thickness'), key, 'width', 1, 50, 1)
        self._add_scale_row(box, self._L('Przezroczystość', 'Opacity'), key, 'opacity', 0.05, 1.0, 0.01)
        return box

    def _shape_page(self, key):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self._add_color_row(box, self._L('Kolor obramowania', 'Outline color'), key, 'stroke_color')
        self._add_scale_row(box, self._L('Grubość obramowania', 'Outline width'), key, 'width', 1, 40, 1)
        self._add_switch_row(box, self._L('Wypełnienie', 'Fill'), key, 'fill_enabled')
        self._add_color_row(box, self._L('Kolor wypełnienia', 'Fill color'), key, 'fill_color')
        self._add_scale_row(box, self._L('Przezroczystość wypełnienia', 'Fill opacity'), key, 'fill_opacity', 0.0, 1.0, 0.01)
        return box

    def _text_page(self):
        key = 'text'
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self._add_color_row(box, self._L('Kolor tekstu', 'Text color'), key, 'color')
        self._add_scale_row(box, self._L('Rozmiar tekstu', 'Text size'), key, 'size', 10, 96, 1)
        self._add_switch_row(box, self._L('Tło tekstu', 'Text background'), key, 'bg_enabled')
        self._add_color_row(box, self._L('Kolor tła', 'Background color'), key, 'bg_color')
        self._add_scale_row(box, self._L('Przezroczystość tła', 'Background opacity'), key, 'bg_opacity', 0.0, 1.0, 0.01)
        self._add_scale_row(box, self._L('Odstęp', 'Padding'), key, 'padding', 0, 32, 1)
        return box

    def _number_page(self):
        key = 'number'
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self._add_color_row(box, self._L('Kolor cyfry', 'Number color'), key, 'text_color')
        self._add_scale_row(box, self._L('Rozmiar cyfry', 'Number size'), key, 'size', 10, 72, 1)
        self._add_color_row(box, self._L('Kolor koła', 'Circle fill color'), key, 'fill_color')
        self._add_scale_row(box, self._L('Przezroczystość koła', 'Circle opacity'), key, 'fill_opacity', 0.0, 1.0, 0.01)
        self._add_scale_row(box, self._L('Promień koła', 'Circle radius'), key, 'radius', 8, 80, 1)
        self._add_color_row(box, self._L('Kolor obramowania', 'Border color'), key, 'border_color')
        self._add_scale_row(box, self._L('Grubość obramowania', 'Border width'), key, 'border_width', 0, 12, 1)
        return box

    def _redact_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self._add_scale_row(box, self._L('Rozmiar pikseli', 'Pixel size'), 'redact', 'block_size', 4, 50, 1)
        info = Gtk.Label(label=self._L('Cenzura pikseluje obszar w kwadraty.', 'Redaction pixelates the area into square blocks.'), xalign=0, wrap=True)
        info.add_css_class('dim-label')
        box.append(info)
        return box

    def _add_scale_row(self, parent, title, section, key, lo, hi, step):
        row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        label = Gtk.Label(label=title, xalign=0)
        value_label = Gtk.Label(xalign=1)
        value_label.add_css_class('dim-label')
        value_label.set_hexpand(True)
        header.append(label)
        header.append(value_label)
        row.append(header)
        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, lo, hi, step)
        scale.set_draw_value(False)
        scale.set_value(self.config[section][key])
        def changed(s):
            self.config[section][key] = s.get_value()
            decimals = 2 if step < 1 else 0
            value_label.set_text(f'{s.get_value():.{decimals}f}')
            self.canvas.queue_draw()
        changed(scale)
        scale.connect('value-changed', changed)
        row.append(scale)
        parent.append(row)

    def _add_switch_row(self, parent, title, section, key):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        label = Gtk.Label(label=title, xalign=0)
        label.set_hexpand(True)
        row.append(label)
        switch = Gtk.Switch(active=bool(self.config[section][key]))
        def changed(sw, _pspec):
            self.config[section][key] = sw.get_active()
            self.canvas.queue_draw()
        switch.connect('notify::active', changed)
        row.append(switch)
        parent.append(row)

    def _add_color_row(self, parent, title, section, key):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        label = Gtk.Label(label=title, xalign=0)
        label.set_hexpand(True)
        row.append(label)
        btn = Gtk.ColorButton()
        btn.set_use_alpha(True)
        btn.set_rgba(to_rgba(self.config[section][key]))
        def changed(button):
            self.config[section][key] = rgba_tuple(button.get_rgba())
            self.canvas.queue_draw()
        btn.connect('color-set', changed)
        row.append(btn)
        parent.append(row)

    def _sync_option_pages(self):
        self.options_stack.set_visible_child_name(self.tool)
        hint = self._tool_hint(self.tool)
        self.hint_label.set_text(hint)
        self.status.set_text(hint)

    def _on_tool_toggled(self, button, tool):
        if not button.get_active():
            return
        self.tool = tool
        self.preview_annotation = None
        self.drag_mode = None
        self.current_points = None
        self.drag_start = None
        self.drag_current = None
        self._sync_option_pages()
        self.canvas.queue_draw()

    def _viewport_changed(self, *_args):
        width = self.scroll.get_width()
        height = self.scroll.get_height()
        if width > 1:
            self.viewport_w = width
        if height > 1:
            self.viewport_h = height
        if self.auto_fit:
            self._fit_to_view(allow_enlarge=True)
        else:
            self.canvas.queue_draw()

    def _fit_to_view(self, *_args, allow_enlarge=True):
        # Re-read the actual viewport every time Fit is clicked; cached values
        # can be stale after resizing/maximizing a GTK window.
        if hasattr(self, 'scroll'):
            width = self.scroll.get_width()
            height = self.scroll.get_height()
            if width > 1:
                self.viewport_w = width
            if height > 1:
                self.viewport_h = height
        self.auto_fit = True
        usable_w = max(100, self.viewport_w - self.fit_margin)
        usable_h = max(100, self.viewport_h - self.fit_margin)
        fit = min(usable_w / max(1, self.img_w), usable_h / max(1, self.img_h))
        if not allow_enlarge:
            fit = min(fit, 1.0)
        self.zoom = clamp(fit, 0.05, 8.0)
        self._update_canvas_metrics()
        self.canvas.queue_draw()

    def _manual_zoom(self, factor):
        self.auto_fit = False
        self.zoom = clamp(self.zoom * factor, 0.05, 8.0)
        self._update_canvas_metrics()
        self.canvas.queue_draw()

    def _on_zoom_scroll(self, controller, _dx, dy):
        state = controller.get_current_event_state()
        if not (state & Gdk.ModifierType.CONTROL_MASK):
            return False
        if dy < 0:
            self._manual_zoom(1.12)
        elif dy > 0:
            self._manual_zoom(1 / 1.12)
        return True

    def _update_canvas_metrics(self):
        target_w = max(self.viewport_w, int(self.img_w * self.zoom) + self.fit_margin)
        target_h = max(self.viewport_h, int(self.img_h * self.zoom) + self.fit_margin)
        self.canvas.set_content_width(target_w)
        self.canvas.set_content_height(target_h)
        self.zoom_label.set_text(f'{int(round(self.zoom * 100))}%')
        self._update_details()

    def _image_to_widget(self, x, y):
        return self.offset_x + x * self.zoom, self.offset_y + y * self.zoom

    def _widget_to_image(self, x, y):
        ix = (x - self.offset_x) / self.zoom
        iy = (y - self.offset_y) / self.zoom
        return clamp(ix, 0, self.img_w), clamp(iy, 0, self.img_h)

    def _draw(self, _area, cr, width, height, _data):
        self._update_canvas_metrics()
        display_w = self.img_w * self.zoom
        display_h = self.img_h * self.zoom
        self.offset_x = max(18, (width - display_w) / 2.0)
        self.offset_y = max(18, (height - display_h) / 2.0)

        cr.set_source_rgb(*self.canvas_bg)
        cr.paint()

        cr.set_source_rgba(0, 0, 0, self.canvas_shadow_alpha)
        cr.rectangle(self.offset_x + 6, self.offset_y + 6, display_w + 6, display_h + 6)
        cr.fill()
        cr.set_source_rgb(1, 1, 1)
        cr.rectangle(self.offset_x, self.offset_y, display_w, display_h)
        cr.fill()

        surface = self._flattened_surface(include_preview=False)
        self.render_surface = surface
        cr.save()
        cr.translate(self.offset_x, self.offset_y)
        cr.scale(self.zoom, self.zoom)
        cr.set_source_surface(surface, 0, 0)
        cr.paint()
        if self.tool == 'crop' and self.drag_mode == 'draw' and self.drag_start is not None and self.drag_current is not None:
            self._draw_crop_preview(cr)
        if self.preview_annotation is not None:
            if self.preview_annotation['kind'] == 'redact':
                temp = self._copy_surface(surface)
                self._apply_pixelate(temp, self.preview_annotation)
                cr.set_source_surface(temp, 0, 0)
                cr.paint()
            else:
                self._draw_annotation(cr, self.preview_annotation)
        if self.selected_index is not None and 0 <= self.selected_index < len(self.annotations):
            self._draw_selection(cr, self.annotations[self.selected_index])
        cr.restore()

    def _draw_crop_preview(self, cr):
        x, y, w, h = norm_rect(*self.drag_start, *self.drag_current)
        if w < 1 or h < 1:
            return
        cr.save()
        # Dim only the part that will be removed.
        cr.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
        cr.rectangle(0, 0, self.img_w, self.img_h)
        cr.rectangle(x, y, w, h)
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.34)
        cr.fill()
        # Clear dashed crop boundary, independent of zoom.
        line = max(1.0, 2.0 / max(self.zoom, 0.05))
        cr.set_line_width(line)
        dash = max(2.0, 7.0 / max(self.zoom, 0.05))
        gap = max(2.0, 5.0 / max(self.zoom, 0.05))
        cr.set_dash([dash, gap], 0)
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.98)
        cr.rectangle(x, y, w, h)
        cr.stroke()
        cr.set_dash([], 0)
        cr.restore()

    def _draw_selection(self, cr, ann):
        x, y, w, h = self._annotation_bounds(ann)
        cr.save()
        cr.set_source_rgba(0.16, 0.48, 0.95, 0.95)
        cr.set_line_width(max(1.3, 2.0 / max(0.1, self.zoom)))
        cr.rectangle(x - 4 / self.zoom, y - 4 / self.zoom, w + 8 / self.zoom, h + 8 / self.zoom)
        cr.stroke()
        cr.restore()

    def _set_source(self, cr, color, opacity_override=None):
        r, g, b, a = color
        cr.set_source_rgba(r, g, b, a if opacity_override is None else opacity_override)

    def _flattened_surface(self, include_preview=False):
        out = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.img_w, self.img_h)
        cr = cairo.Context(out)
        cr.set_source_surface(self.base, 0, 0)
        cr.paint()
        for ann in self.annotations:
            if ann['kind'] == 'redact':
                self._apply_pixelate(out, ann)
            else:
                self._draw_annotation(cr, ann)
        if include_preview and self.preview_annotation is not None:
            if self.preview_annotation['kind'] == 'redact':
                self._apply_pixelate(out, self.preview_annotation)
            else:
                self._draw_annotation(cr, self.preview_annotation)
        out.flush()
        return out

    def _draw_annotation(self, cr, ann):
        kind = ann['kind']
        cr.new_path()
        cr.save()
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        if kind in ('pen', 'highlighter'):
            pts = ann['points']
            if len(pts) > 1:
                self._set_source(cr, ann['color'], ann.get('opacity', ann['color'][3]))
                cr.set_line_width(ann['width'])
                cr.move_to(*pts[0])
                for p in pts[1:]:
                    cr.line_to(*p)
                cr.stroke()
        elif kind == 'line':
            self._set_source(cr, ann['color'], ann['opacity'])
            cr.set_line_width(ann['width'])
            cr.move_to(*ann['start'])
            cr.line_to(*ann['end'])
            cr.stroke()
        elif kind == 'arrow':
            self._draw_arrow(cr, ann['start'], ann['end'], ann['color'], ann['width'], ann['opacity'])
        elif kind in ('rect', 'ellipse'):
            x, y, w, h = norm_rect(*ann['start'], *ann['end'])
            if ann.get('fill_enabled'):
                if kind == 'rect':
                    cr.rectangle(x, y, w, h)
                    self._set_source(cr, ann['fill_color'], ann['fill_opacity'])
                    cr.fill_preserve()
                else:
                    cr.save()
                    cr.translate(x + w / 2.0, y + h / 2.0)
                    cr.scale(max(1e-6, w / 2.0), max(1e-6, h / 2.0))
                    cr.arc(0, 0, 1, 0, 2 * math.pi)
                    cr.restore()
                    self._set_source(cr, ann['fill_color'], ann['fill_opacity'])
                    cr.fill_preserve()
            self._set_source(cr, ann['stroke_color'])
            if kind == 'rect':
                cr.set_line_width(ann['width'])
                cr.rectangle(x, y, w, h)
                cr.stroke()
            else:
                cr.save()
                cr.translate(x + w / 2.0, y + h / 2.0)
                cr.scale(max(1e-6, w / 2.0), max(1e-6, h / 2.0))
                cr.set_line_width(ann['width'] / max(1.0, min(w, h) / 2.0))
                cr.arc(0, 0, 1, 0, 2 * math.pi)
                cr.stroke()
                cr.restore()
        elif kind == 'text':
            self._draw_text_annotation(cr, ann)
        elif kind == 'number':
            self._draw_number_annotation(cr, ann)
        cr.restore()
        cr.new_path()

    def _draw_text_annotation(self, cr, ann):
        size = ann['size']
        cr.select_font_face('Sans', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(size)
        ext = cr.text_extents(ann['text'])
        padding = ann.get('padding', 8.0)
        x = ann['x']
        y = ann['y']
        if ann.get('bg_enabled'):
            rect_x = x + ext.x_bearing - padding
            rect_y = y + ext.y_bearing - padding
            rect_w = ext.width + 2 * padding
            rect_h = ext.height + 2 * padding
            self._rounded_rect(cr, rect_x, rect_y, rect_w, rect_h, 8)
            self._set_source(cr, ann['bg_color'], ann['bg_opacity'])
            cr.fill()
        self._set_source(cr, ann['color'])
        cr.move_to(x, y)
        cr.show_text(ann['text'])

    def _draw_number_annotation(self, cr, ann):
        x = ann['x']; y = ann['y']; radius = ann['radius']
        cr.new_path()
        self._set_source(cr, ann['fill_color'], ann['fill_opacity'])
        cr.arc(x, y, radius, 0, 2 * math.pi)
        cr.fill_preserve()
        self._set_source(cr, ann['border_color'])
        cr.set_line_width(ann['border_width'])
        cr.stroke()
        cr.select_font_face('Sans', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(ann['size'])
        text = str(ann['number'])
        ext = cr.text_extents(text)
        self._set_source(cr, ann['text_color'])
        cr.move_to(x - (ext.width / 2 + ext.x_bearing), y - (ext.height / 2 + ext.y_bearing))
        cr.show_text(text)
        cr.new_path()

    def _rounded_rect(self, cr, x, y, w, h, r):
        r = min(r, w / 2, h / 2)
        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
        cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()

    def _draw_arrow(self, cr, start, end, color, width, opacity=1.0):
        x1, y1 = start; x2, y2 = end
        self._set_source(cr, color, opacity)
        cr.set_line_width(width)
        cr.move_to(x1, y1)
        cr.line_to(x2, y2)
        cr.stroke()
        angle = math.atan2(y2 - y1, x2 - x1)
        head = max(12.0, width * 3.5)
        spread = math.radians(28)
        p1 = (x2 - head * math.cos(angle - spread), y2 - head * math.sin(angle - spread))
        p2 = (x2 - head * math.cos(angle + spread), y2 - head * math.sin(angle + spread))
        cr.move_to(x2, y2); cr.line_to(*p1); cr.move_to(x2, y2); cr.line_to(*p2); cr.stroke()

    def _apply_pixelate(self, surface, ann):
        x, y, w, h = norm_rect(*ann['start'], *ann['end'])
        x = int(clamp(round(x), 0, self.img_w)); y = int(clamp(round(y), 0, self.img_h))
        w = int(clamp(round(w), 0, self.img_w - x)); h = int(clamp(round(h), 0, self.img_h - y))
        if w <= 0 or h <= 0:
            return
        block = int(max(2, ann.get('block_size', 12)))
        data = surface.get_data(); stride = surface.get_stride(); mv = memoryview(data)
        for by in range(y, y + h, block):
            bh = min(block, y + h - by)
            for bx in range(x, x + w, block):
                bw = min(block, x + w - bx)
                total_b = total_g = total_r = total_a = count = 0
                for yy in range(by, by + bh):
                    row = yy * stride
                    for xx in range(bx, bx + bw):
                        idx = row + xx * 4
                        total_b += mv[idx + 0]; total_g += mv[idx + 1]; total_r += mv[idx + 2]; total_a += mv[idx + 3]; count += 1
                if count == 0:
                    continue
                avg_b = int(total_b / count); avg_g = int(total_g / count); avg_r = int(total_r / count); avg_a = int(total_a / count)
                for yy in range(by, by + bh):
                    row = yy * stride
                    for xx in range(bx, bx + bw):
                        idx = row + xx * 4
                        mv[idx + 0] = avg_b; mv[idx + 1] = avg_g; mv[idx + 2] = avg_r; mv[idx + 3] = avg_a
        surface.mark_dirty()

    def _drag_begin(self, _gesture, x, y):
        ix, iy = self._widget_to_image(x, y)
        self.drag_start = (ix, iy)
        self.drag_current = (ix, iy)
        self.preview_annotation = None
        self.move_snapshot = None
        self.current_points = None
        if self.tool in ('text', 'number'):
            self.drag_mode = None
            self.drag_start = None
            self.drag_current = None
            self.preview_annotation = None
            self.current_points = None
            return

        if self.tool == 'move':
            idx = self._find_annotation(ix, iy)
            self.selected_index = idx
            if idx is not None:
                self.drag_mode = 'move-existing'
                self.move_snapshot = copy.deepcopy(self.annotations[idx])
            else:
                self.drag_mode = None
            self._refresh_elements_list()
            self.canvas.queue_draw()
            return
        self.drag_mode = 'draw'
        if self.tool in ('pen', 'highlighter'):
            self.current_points = [self.drag_start]

    def _drag_update(self, _gesture, dx, dy):
        if self.tool in ('text', 'number'):
            self.preview_annotation = None
            return
        if self.drag_start is None or self.drag_mode is None:
            return
        start_x, start_y = self.drag_start
        ix = clamp(start_x + dx / self.zoom, 0, self.img_w)
        iy = clamp(start_y + dy / self.zoom, 0, self.img_h)
        self.drag_current = (ix, iy)
        if self.drag_mode == 'move-existing' and self.selected_index is not None and self.move_snapshot is not None:
            delta_x = ix - self.drag_start[0]; delta_y = iy - self.drag_start[1]
            moved = copy.deepcopy(self.move_snapshot)
            self._shift_annotation(moved, delta_x, delta_y)
            self.annotations[self.selected_index] = moved
            self.canvas.queue_draw(); return
        if self.tool in ('pen', 'highlighter'):
            self.current_points.append(self.drag_current)
            cfg = self.config[self.tool]
            self.preview_annotation = {
                'kind': self.tool, 'points': list(self.current_points),
                'color': cfg['color'], 'width': cfg['width'], 'opacity': cfg.get('opacity', 1.0),
            }
        else:
            self.preview_annotation = self._build_shape_annotation(self.tool, self.drag_start, self.drag_current)
        self.canvas.queue_draw()

    def _drag_end(self, _gesture, dx, dy):
        if self.tool in ('text', 'number'):
            self.drag_start = None
            self.drag_current = None
            self.preview_annotation = None
            self.drag_mode = None
            return
        if self.drag_start is None or self.drag_mode is None:
            return
        self._drag_update(_gesture, dx, dy)
        if self.drag_mode == 'move-existing' and self.selected_index is not None and self.move_snapshot is not None:
            self.undo_stack.append({'type': 'move', 'index': self.selected_index, 'before': self.move_snapshot, 'after': copy.deepcopy(self.annotations[self.selected_index])})
            self.redo_stack.clear()
        elif self.tool == 'crop':
            x, y, w, h = norm_rect(*self.drag_start, *self.drag_current)
            if w >= 4 and h >= 4:
                self._apply_crop(int(round(x)), int(round(y)), int(round(w)), int(round(h)))
                self.tool_buttons['move'].set_active(True)
        elif self.tool in ('pen', 'highlighter'):
            if self.preview_annotation and len(self.preview_annotation['points']) > 1:
                self._add_annotation(self.preview_annotation)
        elif self.preview_annotation is not None:
            x, y, w, h = norm_rect(*self.preview_annotation.get('start', self.drag_start), *self.preview_annotation.get('end', self.drag_current))
            if w >= 2 or h >= 2:
                self._add_annotation(self.preview_annotation)
        self.drag_mode = None; self.drag_start = None; self.drag_current = None
        self.current_points = None; self.preview_annotation = None; self.move_snapshot = None
        self.canvas.queue_draw()

    def _click_pressed(self, _gesture, _n_press, x, y):
        ix, iy = self._widget_to_image(x, y)
        if self.tool == 'text':
            self._ask_text(ix, iy)
        elif self.tool == 'number':
            self.drag_start = None
            self.drag_current = None
            self.drag_mode = None
            self.preview_annotation = None
            self.current_points = None
            self._add_number(ix, iy)
        elif self.tool == 'move':
            self.selected_index = self._find_annotation(ix, iy)
            self._refresh_elements_list(); self.canvas.queue_draw()

    def _build_shape_annotation(self, tool, start, end):
        if tool == 'line':
            cfg = self.config['line']
            return {'kind': 'line', 'start': start, 'end': end, 'color': cfg['color'], 'width': cfg['width'], 'opacity': cfg['opacity']}
        if tool == 'arrow':
            cfg = self.config['arrow']
            return {'kind': 'arrow', 'start': start, 'end': end, 'color': cfg['color'], 'width': cfg['width'], 'opacity': cfg['opacity']}
        if tool in ('rect', 'ellipse'):
            cfg = self.config[tool]
            return {
                'kind': tool, 'start': start, 'end': end,
                'stroke_color': cfg['stroke_color'], 'width': cfg['width'],
                'fill_enabled': cfg['fill_enabled'], 'fill_color': cfg['fill_color'], 'fill_opacity': cfg['fill_opacity'],
            }
        if tool == 'redact':
            return {'kind': 'redact', 'start': start, 'end': end, 'block_size': self.config['redact']['block_size']}
        return None

    def _ask_text(self, x, y):
        dialog = Gtk.Dialog(transient_for=self, modal=True, title=self._L('Dodaj tekst', 'Add text'))
        dialog.add_button(self._t('cancel'), Gtk.ResponseType.CANCEL)
        dialog.add_button(self._t('add'), Gtk.ResponseType.OK)
        box = dialog.get_content_area()
        box.set_margin_top(12); box.set_margin_bottom(12); box.set_margin_start(12); box.set_margin_end(12)
        entry = Gtk.Entry(); entry.set_placeholder_text(self._t('text_placeholder')); entry.set_activates_default(True)
        box.append(entry); dialog.set_default_response(Gtk.ResponseType.OK)
        def response(dlg, response_id):
            if response_id == Gtk.ResponseType.OK and entry.get_text():
                cfg = self.config['text']
                self._add_annotation({
                    'kind': 'text', 'x': x, 'y': y, 'text': entry.get_text(),
                    'color': cfg['color'], 'size': cfg['size'], 'bg_enabled': cfg['bg_enabled'],
                    'bg_color': cfg['bg_color'], 'bg_opacity': cfg['bg_opacity'], 'padding': cfg['padding'],
                })
            dlg.destroy(); self.canvas.queue_draw()
        dialog.connect('response', response); dialog.present(); entry.grab_focus()

    def _add_number(self, x, y):
        cfg = self.config['number']
        num = self.next_number; self.next_number += 1
        self._add_annotation({
            'kind': 'number', 'x': x, 'y': y, 'number': num,
            'text_color': cfg['text_color'], 'size': cfg['size'],
            'fill_color': cfg['fill_color'], 'fill_opacity': cfg['fill_opacity'],
            'radius': cfg['radius'], 'border_color': cfg['border_color'], 'border_width': cfg['border_width'],
        })

    def _add_annotation(self, ann):
        self.annotations.append(copy.deepcopy(ann))
        self.selected_index = len(self.annotations) - 1
        self.undo_stack.append({'type': 'add', 'annotation': copy.deepcopy(ann), 'index': self.selected_index})
        self.redo_stack.clear(); self._refresh_elements_list(); self._update_details(); self.canvas.queue_draw()

    def _delete_selected(self):
        if self.selected_index is None or not (0 <= self.selected_index < len(self.annotations)):
            return
        idx = self.selected_index; ann = self.annotations.pop(idx)
        self.undo_stack.append({'type': 'delete', 'annotation': copy.deepcopy(ann), 'index': idx}); self.redo_stack.clear()
        self.selected_index = min(idx, len(self.annotations) - 1) if self.annotations else None
        self._renumber_numbers(); self._refresh_elements_list(); self._update_details(); self.canvas.queue_draw()

    def _reorder_selected(self, delta):
        if self.selected_index is None:
            return
        idx = self.selected_index; new_idx = idx + delta
        if not (0 <= new_idx < len(self.annotations)):
            return
        self.annotations[idx], self.annotations[new_idx] = self.annotations[new_idx], self.annotations[idx]
        self.selected_index = new_idx
        self.undo_stack.append({'type': 'reorder', 'before': idx, 'after': new_idx}); self.redo_stack.clear()
        self._refresh_elements_list(); self.canvas.queue_draw()

    def _renumber_numbers(self):
        current = 1
        for ann in self.annotations:
            if ann['kind'] == 'number':
                ann['number'] = current; current += 1
        self.next_number = current

    def _refresh_elements_list(self):
        self._suspend_list_selection = True
        child = self.elements_list.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling(); self.elements_list.remove(child); child = next_child
        for index, ann in enumerate(self.annotations):
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            box.set_margin_top(6); box.set_margin_bottom(6); box.set_margin_start(8); box.set_margin_end(8)
            label = Gtk.Label(label=f'{index + 1}. {self._element_label(ann)}', xalign=0)
            label.set_hexpand(True); box.append(label); row.set_child(box); self.elements_list.append(row)
            if index == self.selected_index:
                self.elements_list.select_row(row)
        self._suspend_list_selection = False

    def _element_label(self, ann):
        if ann['kind'] == 'text':
            text = ann['text']; short = text[:18] + ('…' if len(text) > 18 else '')
            return self._display_name('text') + f' — "{short}"'
        if ann['kind'] == 'number':
            return self._display_name('number') + f' {ann["number"]}'
        return self._display_name(ann['kind'])

    def _row_selected(self, _listbox, row):
        if self._suspend_list_selection:
            return
        self.selected_index = row.get_index() if row is not None else None
        self.canvas.queue_draw()

    def _update_details(self):
        self.details_label.set_text(
            self._L('Plik', 'File') + f': {self.image_path.name}\n' +
            self._L('Rozmiar obrazu', 'Image size') + f': {self.img_w} × {self.img_h} px\n' +
            self._L('Powiększenie', 'Zoom') + f': {int(round(self.zoom * 100))}%\n' +
            self._L('Adnotacje', 'Annotations') + f': {len(self.annotations)}'
        )

    def _annotation_bounds(self, ann):
        kind = ann['kind']
        if kind in ('pen', 'highlighter'):
            xs = [p[0] for p in ann['points']]; ys = [p[1] for p in ann['points']]
            pad = ann['width'] / 2 + 4
            return min(xs) - pad, min(ys) - pad, (max(xs) - min(xs)) + 2 * pad, (max(ys) - min(ys)) + 2 * pad
        if kind in ('line', 'arrow', 'rect', 'ellipse', 'redact'):
            x, y, w, h = norm_rect(*ann['start'], *ann['end'])
            pad = ann.get('width', ann.get('block_size', 8)) / 2 + 6
            return x - pad, y - pad, w + 2 * pad, h + 2 * pad
        if kind == 'text':
            size = ann['size']; width = max(12, len(ann['text']) * size * 0.62); height = size * 1.5
            return ann['x'] - 6, ann['y'] - height, width + 12, height + 12
        if kind == 'number':
            r = ann['radius'] + 4; return ann['x'] - r, ann['y'] - r, 2 * r, 2 * r
        return 0, 0, 0, 0

    def _find_annotation(self, x, y):
        for idx in range(len(self.annotations) - 1, -1, -1):
            bx, by, bw, bh = self._annotation_bounds(self.annotations[idx])
            if bx <= x <= bx + bw and by <= y <= by + bh:
                return idx
        return None

    def _shift_annotation(self, ann, dx, dy):
        kind = ann['kind']
        if kind in ('pen', 'highlighter'):
            ann['points'] = [(x + dx, y + dy) for x, y in ann['points']]
        elif kind in ('line', 'arrow', 'rect', 'ellipse', 'redact'):
            ann['start'] = (ann['start'][0] + dx, ann['start'][1] + dy); ann['end'] = (ann['end'][0] + dx, ann['end'][1] + dy)
        elif kind in ('text', 'number'):
            ann['x'] += dx; ann['y'] += dy

    def _copy_surface(self, surface):
        out = cairo.ImageSurface(cairo.FORMAT_ARGB32, surface.get_width(), surface.get_height())
        cr = cairo.Context(out); cr.set_source_surface(surface, 0, 0); cr.paint(); return out

    def _apply_crop(self, x, y, w, h):
        x = int(clamp(x, 0, max(0, self.img_w - 1))); y = int(clamp(y, 0, max(0, self.img_h - 1)))
        w = int(clamp(w, 1, self.img_w - x)); h = int(clamp(h, 1, self.img_h - y))
        before_surface = self.base; before_annotations = copy.deepcopy(self.annotations)
        cropped = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr = cairo.Context(cropped); cr.set_source_surface(self.base, -x, -y); cr.paint()
        shifted = []
        for ann in self.annotations:
            a = copy.deepcopy(ann); self._shift_annotation(a, -x, -y); shifted.append(a)
        self.base = cropped; self.annotations = shifted; self.img_w, self.img_h = w, h
        self.undo_stack.append({'type': 'crop', 'before_surface': before_surface, 'before_annotations': before_annotations, 'before_size': (before_surface.get_width(), before_surface.get_height()), 'after_surface': self.base, 'after_annotations': copy.deepcopy(self.annotations), 'after_size': (w, h)})
        self.redo_stack.clear(); self.selected_index = None; self._renumber_numbers(); self._refresh_elements_list(); self._fit_to_view(allow_enlarge=True)
        self.status.set_text(self._t('selected_area', w=w, h=h))

    def _render_flattened(self):
        return self._flattened_surface(include_preview=False)

    def _copy_to_clipboard(self):
        fd, path = tempfile.mkstemp(prefix='zorin-shot-copy-', suffix='.png'); os.close(fd)
        try:
            self._render_flattened().write_to_png(path)
            texture = Gdk.Texture.new_from_filename(path)
            png_bytes = texture.save_to_png_bytes()
            content = Gdk.ContentProvider.new_for_bytes('image/png', png_bytes)
            clipboard = Gdk.Display.get_default().get_clipboard(); clipboard.set_content(content)
            self.status.set_text(self._t('copied')); GLib.timeout_add_seconds(30, self._delete_temp, path)
        except Exception as exc:
            try: os.unlink(path)
            except OSError: pass
            self._error(self._t('copy_failed', error=exc))

    def _delete_temp(self, path):
        try: os.unlink(path)
        except OSError: pass
        return GLib.SOURCE_REMOVE

    def _default_save_name(self):
        stamp = GLib.DateTime.new_now_local().format('%Y-%m-%d_%H-%M-%S'); return f'ZorinShot_{stamp}.png'

    def _save_as(self):
        dialog = Gtk.FileChooserNative.new(self._t('save_screenshot'), self, Gtk.FileChooserAction.SAVE, self._t('save'), self._t('cancel_mnemonic'))
        dialog.set_current_name(self._default_save_name())
        pictures = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_PICTURES)
        if pictures:
            try: dialog.set_current_folder(Gio.File.new_for_path(pictures))
            except Exception: pass
        dialog.connect('response', self._save_response); self._save_dialog = dialog; dialog.show()

    def _save_response(self, dialog, response):
        try:
            if response == Gtk.ResponseType.ACCEPT:
                file = dialog.get_file(); path = file.get_path() if file else None
                if path:
                    if not path.lower().endswith('.png'): path += '.png'
                    self._render_flattened().write_to_png(path); self.status.set_text(self._t('saved', path=path))
        except Exception as exc:
            self._error(self._t('save_failed', error=exc))
        finally:
            dialog.destroy(); self._save_dialog = None

    def _error(self, message):
        self.status.set_text(message)
        dialog = Gtk.Dialog(transient_for=self, modal=True, title=self._t('editor_error'))
        dialog.add_button(self._t('ok'), Gtk.ResponseType.OK)
        label = Gtk.Label(label=message, wrap=True)
        label.set_margin_top(16); label.set_margin_bottom(16); label.set_margin_start(16); label.set_margin_end(16)
        dialog.get_content_area().append(label); dialog.connect('response', lambda d, _r: d.destroy()); dialog.present()

    def _undo(self, *_args):
        if not self.undo_stack: return
        action = self.undo_stack.pop()
        if action['type'] == 'add':
            if 0 <= action['index'] < len(self.annotations): self.annotations.pop(action['index'])
        elif action['type'] == 'delete':
            self.annotations.insert(action['index'], action['annotation'])
        elif action['type'] == 'move':
            self.annotations[action['index']] = copy.deepcopy(action['before'])
        elif action['type'] == 'reorder':
            before, after = action['before'], action['after']; self.annotations[before], self.annotations[after] = self.annotations[after], self.annotations[before]; self.selected_index = before
        elif action['type'] == 'crop':
            self.base = action['before_surface']; self.annotations = copy.deepcopy(action['before_annotations']); self.img_w, self.img_h = action['before_size']; self._fit_to_view(allow_enlarge=True)
        self.redo_stack.append(action); self._renumber_numbers(); self._refresh_elements_list(); self._update_details(); self.canvas.queue_draw()

    def _redo(self, *_args):
        if not self.redo_stack: return
        action = self.redo_stack.pop()
        if action['type'] == 'add':
            self.annotations.insert(action['index'], copy.deepcopy(action['annotation'])); self.selected_index = action['index']
        elif action['type'] == 'delete':
            if 0 <= action['index'] < len(self.annotations): self.annotations.pop(action['index'])
        elif action['type'] == 'move':
            self.annotations[action['index']] = copy.deepcopy(action['after'])
        elif action['type'] == 'reorder':
            before, after = action['before'], action['after']; self.annotations[before], self.annotations[after] = self.annotations[after], self.annotations[before]; self.selected_index = after
        elif action['type'] == 'crop':
            self.base = action['after_surface']; self.annotations = copy.deepcopy(action['after_annotations']); self.img_w, self.img_h = action['after_size']; self._fit_to_view(allow_enlarge=True)
        self.undo_stack.append(action); self._renumber_numbers(); self._refresh_elements_list(); self._update_details(); self.canvas.queue_draw()

    def _confirm_close_enabled(self):
        return bool(self.editor_state.get('confirm_close', True))

    def _on_close_request(self, *_args):
        if self._closing_programmatically:
            return False
        if not self._confirm_close_enabled():
            return False

        dialog = Gtk.Dialog(transient_for=self, modal=True)
        dialog.set_title(self._L('Zamknąć Zorin Shot?', 'Close Zorin Shot?'))
        dialog.set_default_size(520, -1)
        dialog.set_resizable(False)

        content = dialog.get_content_area()
        content.set_spacing(14)
        content.set_margin_top(24)
        content.set_margin_bottom(22)
        content.set_margin_start(28)
        content.set_margin_end(28)

        icon = Gtk.Image.new_from_icon_name('dialog-question-symbolic')
        icon.set_pixel_size(42)
        icon.set_halign(Gtk.Align.CENTER)
        content.append(icon)

        question = Gtk.Label(
            label=self._L('Co chcesz zrobić przed zamknięciem?', 'What would you like to do before closing?'),
            wrap=True,
            justify=Gtk.Justification.CENTER,
        )
        question.set_halign(Gtk.Align.CENTER)
        question.add_css_class('title-3')
        content.append(question)

        description = Gtk.Label(
            label=self._L(
                'Możesz skopiować gotowy obraz do schowka albo zamknąć edytor bez kopiowania.',
                'You can copy the finished image to the clipboard or close the editor without copying.'
            ),
            wrap=True,
            justify=Gtk.Justification.CENTER,
        )
        description.set_halign(Gtk.Align.CENTER)
        description.set_max_width_chars(54)
        description.add_css_class('dim-label')
        content.append(description)

        checkbox = Gtk.CheckButton(label=self._L('Nie pytaj ponownie', 'Do not ask again'))
        checkbox.set_halign(Gtk.Align.CENTER)
        checkbox.set_margin_top(4)
        checkbox.set_margin_bottom(4)
        content.append(checkbox)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        buttons.set_halign(Gtk.Align.CENTER)
        buttons.set_homogeneous(True)
        buttons.set_margin_top(4)
        content.append(buttons)

        cancel_btn = Gtk.Button(label=self._L('Anuluj', 'Cancel'))
        copy_btn = Gtk.Button(label=self._L('Kopiuj i zamknij', 'Copy and close'))
        close_btn = Gtk.Button(label=self._L('Zamknij', 'Close'))
        copy_btn.add_css_class('suggested-action')
        close_btn.add_css_class('destructive-action')
        for btn in (cancel_btn, copy_btn, close_btn):
            btn.set_size_request(138, 38)
            buttons.append(btn)

        def remember_choice():
            if checkbox.get_active():
                self.editor_state['confirm_close'] = False
                save_editor_state(self.editor_state)

        def cancel_clicked(_button):
            remember_choice()
            dialog.destroy()

        def copy_clicked(_button):
            remember_choice()
            self._copy_to_clipboard()
            self._closing_programmatically = True
            dialog.destroy()
            self.close()

        def close_clicked(_button):
            remember_choice()
            self._closing_programmatically = True
            dialog.destroy()
            self.close()

        cancel_btn.connect('clicked', cancel_clicked)
        copy_btn.connect('clicked', copy_clicked)
        close_btn.connect('clicked', close_clicked)
        dialog.present()
        return True

    def _key_pressed(self, _controller, keyval, _keycode, state):
        ctrl = bool(state & Gdk.ModifierType.CONTROL_MASK)
        shift = bool(state & Gdk.ModifierType.SHIFT_MASK)
        if ctrl and keyval in (Gdk.KEY_z, Gdk.KEY_Z):
            self._redo() if shift else self._undo(); return True
        if ctrl and keyval in (Gdk.KEY_y, Gdk.KEY_Y):
            self._redo(); return True
        if ctrl and keyval in (Gdk.KEY_c, Gdk.KEY_C):
            self._copy_to_clipboard(); return True
        if ctrl and keyval in (Gdk.KEY_s, Gdk.KEY_S):
            self._save_as(); return True
        if keyval == Gdk.KEY_Delete:
            self._delete_selected(); return True
        if keyval == Gdk.KEY_Escape:
            self.close(); return True
        return False


class ZorinShotApp(Gtk.Application):
    def __init__(self, image_path, select_region=False):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.NON_UNIQUE)
        self.image_path = image_path
        self.select_region = select_region

    def do_activate(self):
        try:
            win = EditorWindow(self, self.image_path, self.select_region)
            win.present()
        except Exception as exc:
            sys.stderr.write(f'Zorin Shot editor error: {exc}\n')
            self.quit()


def main():
    parser = argparse.ArgumentParser(description='Zorin Shot annotation editor')
    parser.add_argument('--image', required=True, help='PNG file captured by the GNOME Shell extension')
    parser.add_argument('--select-region', action='store_true', help='Start in crop/region selection mode')
    args = parser.parse_args()
    if not os.path.isfile(args.image):
        parser.error(f'Image does not exist: {args.image}')
    app = ZorinShotApp(args.image, args.select_region)
    return app.run(sys.argv[:1])


if __name__ == '__main__':
    raise SystemExit(main())
