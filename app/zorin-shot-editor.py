#!/usr/bin/env python3
import argparse
import copy
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


def read_language():
    try:
        source = Gio.SettingsSchemaSource.new_from_directory(
            str(EXT_SCHEMA_DIR), Gio.SettingsSchemaSource.get_default(), False)
        schema = source.lookup(SCHEMA_ID, False)
        if schema is None:
            return 'pl'
        settings = Gio.Settings.new_full(schema, None, None)
        return 'en' if settings.get_string('language') == 'en' else 'pl'
    except Exception:
        return 'pl'


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def norm_rect(x1, y1, x2, y2):
    left = min(x1, x2)
    top = min(y1, y2)
    right = max(x1, x2)
    bottom = max(y1, y2)
    return left, top, right - left, bottom - top


class EditorWindow(Gtk.ApplicationWindow):
    TOOLS = [
        ('crop', 'tool_crop'),
        ('pen', 'tool_pen'),
        ('highlighter', 'tool_highlighter'),
        ('arrow', 'tool_arrow'),
        ('rect', 'tool_rect'),
        ('ellipse', 'tool_ellipse'),
        ('text', 'tool_text'),
        ('redact', 'tool_redact'),
    ]

    def __init__(self, app, image_path, select_region=False):
        super().__init__(application=app, title='Zorin Shot')
        self.lang = read_language()
        self.set_default_size(1200, 800)
        self.maximize()

        self.image_path = Path(image_path)
        try:
            self.base = cairo.ImageSurface.create_from_png(str(self.image_path))
        except Exception as exc:
            raise RuntimeError(self._t('png_open_failed', error=exc)) from exc

        self.img_w = self.base.get_width()
        self.img_h = self.base.get_height()
        self.zoom = self._initial_zoom()
        self.tool = 'crop' if select_region else 'pen'
        self.color = (1.0, 0.15, 0.15, 1.0)
        self.stroke_width = 5.0
        self.annotations = []
        self.undo_stack = []
        self.redo_stack = []
        self.drag_start = None
        self.drag_current = None
        self.current_points = None
        self._save_dialog = None

        self._build_ui(select_region)
        self._update_canvas_size()

    def _t(self, key, **kwargs):
        return tr(self.lang, key, **kwargs)

    def _initial_zoom(self):
        try:
            display = Gdk.Display.get_default()
            monitors = display.get_monitors()
            monitor = monitors.get_item(0) if monitors.get_n_items() else None
            if monitor:
                g = monitor.get_geometry()
                return clamp(min((g.width * 0.88) / self.img_w,
                                 (g.height * 0.72) / self.img_h), 0.12, 1.0)
        except Exception:
            pass
        return min(1.0, 1600.0 / max(1, self.img_w))

    def _build_ui(self, select_region):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_child(root)

        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        toolbar.set_margin_top(8)
        toolbar.set_margin_bottom(8)
        toolbar.set_margin_start(8)
        toolbar.set_margin_end(8)
        root.append(toolbar)

        first = None
        self.tool_buttons = {}
        for key, label_key in self.TOOLS:
            b = Gtk.ToggleButton(label=self._t(label_key))
            if first is None:
                first = b
            else:
                b.set_group(first)
            b.connect('toggled', self._on_tool_toggled, key)
            self.tool_buttons[key] = b
            toolbar.append(b)
        self.tool_buttons[self.tool].set_active(True)

        toolbar.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

        self.color_button = Gtk.ColorButton()
        rgba = Gdk.RGBA()
        rgba.red, rgba.green, rgba.blue, rgba.alpha = self.color
        self.color_button.set_rgba(rgba)
        self.color_button.set_tooltip_text(self._t('tooltip_color'))
        self.color_button.connect('color-set', self._color_changed)
        toolbar.append(self.color_button)

        self.width_spin = Gtk.SpinButton.new_with_range(1, 40, 1)
        self.width_spin.set_value(self.stroke_width)
        self.width_spin.set_tooltip_text(self._t('tooltip_width'))
        self.width_spin.connect('value-changed', lambda w: setattr(self, 'stroke_width', w.get_value()))
        toolbar.append(self.width_spin)

        toolbar.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

        undo = Gtk.Button(label=self._t('undo'))
        undo.connect('clicked', lambda *_: self._undo())
        toolbar.append(undo)
        redo = Gtk.Button(label=self._t('redo'))
        redo.connect('clicked', lambda *_: self._redo())
        toolbar.append(redo)

        zoom_out = Gtk.Button(label='−')
        zoom_out.set_tooltip_text(self._t('zoom_out'))
        zoom_out.connect('clicked', lambda *_: self._set_zoom(self.zoom / 1.2))
        toolbar.append(zoom_out)
        zoom_in = Gtk.Button(label='+')
        zoom_in.set_tooltip_text(self._t('zoom_in'))
        zoom_in.connect('clicked', lambda *_: self._set_zoom(self.zoom * 1.2))
        toolbar.append(zoom_in)
        fit = Gtk.Button(label=self._t('fit'))
        fit.connect('clicked', lambda *_: self._fit())
        toolbar.append(fit)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        toolbar.append(spacer)

        copy_btn = Gtk.Button(label=self._t('copy'))
        copy_btn.add_css_class('suggested-action')
        copy_btn.connect('clicked', lambda *_: self._copy_to_clipboard())
        toolbar.append(copy_btn)
        save_btn = Gtk.Button(label=self._t('save_as'))
        save_btn.connect('clicked', lambda *_: self._save_as())
        toolbar.append(save_btn)

        self.status = Gtk.Label(xalign=0)
        self.status.set_margin_start(10)
        self.status.set_margin_end(10)
        self.status.set_margin_bottom(6)
        root.append(self.status)

        scroll = Gtk.ScrolledWindow()
        scroll.set_hexpand(True)
        scroll.set_vexpand(True)
        root.append(scroll)

        self.canvas = Gtk.DrawingArea()
        self.canvas.set_content_width(max(1, int(self.img_w * self.zoom)))
        self.canvas.set_content_height(max(1, int(self.img_h * self.zoom)))
        self.canvas.set_draw_func(self._draw, None)
        scroll.set_child(self.canvas)

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

        keys = Gtk.EventControllerKey()
        keys.connect('key-pressed', self._key_pressed)
        self.add_controller(keys)

        if select_region:
            self.status.set_text(self._t('region_hint'))
        else:
            self._set_status_for_tool()

    def _set_status_for_tool(self):
        messages = {
            'crop': 'status_crop',
            'pen': 'status_pen',
            'highlighter': 'status_highlighter',
            'arrow': 'status_arrow',
            'rect': 'status_rect',
            'ellipse': 'status_ellipse',
            'text': 'status_text',
            'redact': 'status_redact',
        }
        key = messages.get(self.tool)
        self.status.set_text(self._t(key) if key else '')

    def _on_tool_toggled(self, button, tool):
        if button.get_active():
            self.tool = tool
            self.drag_start = None
            self.drag_current = None
            self.current_points = None
            self._set_status_for_tool()
            self.canvas.queue_draw()

    def _color_changed(self, button):
        rgba = button.get_rgba()
        self.color = (rgba.red, rgba.green, rgba.blue, rgba.alpha)

    def _set_zoom(self, value):
        self.zoom = clamp(value, 0.08, 4.0)
        self._update_canvas_size()
        self.canvas.queue_draw()

    def _fit(self):
        self.zoom = self._initial_zoom()
        self._update_canvas_size()
        self.canvas.queue_draw()

    def _update_canvas_size(self):
        if hasattr(self, 'canvas'):
            self.canvas.set_content_width(max(1, int(self.img_w * self.zoom)))
            self.canvas.set_content_height(max(1, int(self.img_h * self.zoom)))

    def _to_image(self, x, y):
        return clamp(x / self.zoom, 0, self.img_w), clamp(y / self.zoom, 0, self.img_h)

    def _drag_begin(self, _gesture, x, y):
        if self.tool == 'text':
            return
        p = self._to_image(x, y)
        self.drag_start = p
        self.drag_current = p
        if self.tool in ('pen', 'highlighter'):
            self.current_points = [p]
        self.canvas.queue_draw()

    def _drag_update(self, _gesture, dx, dy):
        if self.drag_start is None or self.tool == 'text':
            return
        sx, sy = self.drag_start
        # GestureDrag offsets are in widget coordinates; convert the delta.
        self.drag_current = (
            clamp(sx + dx / self.zoom, 0, self.img_w),
            clamp(sy + dy / self.zoom, 0, self.img_h),
        )
        if self.tool in ('pen', 'highlighter'):
            if not self.current_points:
                self.current_points = [self.drag_start]
            self.current_points.append(self.drag_current)
        self.canvas.queue_draw()

    def _drag_end(self, _gesture, dx, dy):
        if self.drag_start is None or self.tool == 'text':
            return
        self._drag_update(_gesture, dx, dy)
        start, end = self.drag_start, self.drag_current

        if self.tool == 'crop':
            x, y, w, h = norm_rect(start[0], start[1], end[0], end[1])
            if w >= 4 and h >= 4:
                self._apply_crop(int(round(x)), int(round(y)), int(round(w)), int(round(h)))
                self.tool_buttons['pen'].set_active(True)
        elif self.tool in ('pen', 'highlighter'):
            pts = list(self.current_points or [])
            if len(pts) >= 2:
                self._add_annotation({
                    'kind': self.tool,
                    'points': pts,
                    'color': self.color,
                    'width': self.stroke_width,
                })
        else:
            x, y, w, h = norm_rect(start[0], start[1], end[0], end[1])
            if w >= 2 or h >= 2:
                ann = {
                    'kind': self.tool,
                    'start': start,
                    'end': end,
                    'color': self.color,
                    'width': self.stroke_width,
                }
                self._add_annotation(ann)

        self.drag_start = None
        self.drag_current = None
        self.current_points = None
        self.canvas.queue_draw()

    def _click_pressed(self, _gesture, _n_press, x, y):
        if self.tool != 'text':
            return
        ix, iy = self._to_image(x, y)
        self._ask_text(ix, iy)

    def _ask_text(self, x, y):
        dialog = Gtk.Dialog(transient_for=self, modal=True, title=self._t('add_text'))
        dialog.add_button(self._t('cancel'), Gtk.ResponseType.CANCEL)
        dialog.add_button(self._t('add'), Gtk.ResponseType.OK)
        box = dialog.get_content_area()
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        entry = Gtk.Entry()
        entry.set_placeholder_text(self._t('text_placeholder'))
        entry.set_activates_default(True)
        box.append(entry)
        dialog.set_default_response(Gtk.ResponseType.OK)

        def response(dlg, response_id):
            if response_id == Gtk.ResponseType.OK and entry.get_text():
                self._add_annotation({
                    'kind': 'text',
                    'x': x,
                    'y': y,
                    'text': entry.get_text(),
                    'color': self.color,
                    'size': max(14.0, self.stroke_width * 5.0),
                })
            dlg.destroy()
            self.canvas.queue_draw()

        dialog.connect('response', response)
        dialog.present()
        entry.grab_focus()

    def _add_annotation(self, ann):
        self.annotations.append(ann)
        self.undo_stack.append({'type': 'annotation', 'annotation': ann})
        self.redo_stack.clear()
        self.canvas.queue_draw()

    def _copy_surface(self, surface):
        out = cairo.ImageSurface(cairo.FORMAT_ARGB32, surface.get_width(), surface.get_height())
        cr = cairo.Context(out)
        cr.set_source_surface(surface, 0, 0)
        cr.paint()
        return out

    def _apply_crop(self, x, y, w, h):
        x = int(clamp(x, 0, max(0, self.img_w - 1)))
        y = int(clamp(y, 0, max(0, self.img_h - 1)))
        w = int(clamp(w, 1, self.img_w - x))
        h = int(clamp(h, 1, self.img_h - y))

        before_surface = self.base
        before_annotations = copy.deepcopy(self.annotations)

        cropped = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr = cairo.Context(cropped)
        cr.set_source_surface(self.base, -x, -y)
        cr.paint()

        shifted = []
        for ann in self.annotations:
            a = copy.deepcopy(ann)
            self._shift_annotation(a, -x, -y)
            shifted.append(a)

        self.base = cropped
        self.annotations = shifted
        self.img_w, self.img_h = w, h
        after_surface = self.base
        after_annotations = copy.deepcopy(self.annotations)
        self.undo_stack.append({
            'type': 'crop',
            'before_surface': before_surface,
            'before_annotations': before_annotations,
            'before_size': (before_surface.get_width(), before_surface.get_height()),
            'after_surface': after_surface,
            'after_annotations': after_annotations,
            'after_size': (w, h),
        })
        self.redo_stack.clear()
        self._fit()
        self.status.set_text(self._t('selected_area', w=w, h=h))

    def _shift_annotation(self, ann, dx, dy):
        kind = ann.get('kind')
        if kind in ('pen', 'highlighter'):
            ann['points'] = [(x + dx, y + dy) for x, y in ann['points']]
        elif kind in ('arrow', 'rect', 'ellipse', 'redact'):
            ann['start'] = (ann['start'][0] + dx, ann['start'][1] + dy)
            ann['end'] = (ann['end'][0] + dx, ann['end'][1] + dy)
        elif kind == 'text':
            ann['x'] += dx
            ann['y'] += dy

    def _undo(self):
        if not self.undo_stack:
            return
        action = self.undo_stack.pop()
        if action['type'] == 'annotation':
            if self.annotations:
                self.annotations.pop()
        elif action['type'] == 'crop':
            self.base = action['before_surface']
            self.annotations = copy.deepcopy(action['before_annotations'])
            self.img_w, self.img_h = action['before_size']
            self._fit()
        self.redo_stack.append(action)
        self.canvas.queue_draw()

    def _redo(self):
        if not self.redo_stack:
            return
        action = self.redo_stack.pop()
        if action['type'] == 'annotation':
            self.annotations.append(action['annotation'])
        elif action['type'] == 'crop':
            self.base = action['after_surface']
            self.annotations = copy.deepcopy(action['after_annotations'])
            self.img_w, self.img_h = action['after_size']
            self._fit()
        self.undo_stack.append(action)
        self.canvas.queue_draw()

    def _draw(self, _area, cr, _width, _height, _data):
        cr.save()
        cr.scale(self.zoom, self.zoom)
        cr.set_source_surface(self.base, 0, 0)
        cr.paint()
        for ann in self.annotations:
            self._draw_annotation(cr, ann)
        self._draw_preview(cr)
        cr.restore()

    def _set_source(self, cr, color, alpha_mult=1.0):
        r, g, b, a = color
        cr.set_source_rgba(r, g, b, a * alpha_mult)

    def _draw_annotation(self, cr, ann):
        kind = ann['kind']
        cr.save()
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)

        if kind in ('pen', 'highlighter'):
            pts = ann['points']
            if len(pts) > 1:
                mult = 4.0 if kind == 'highlighter' else 1.0
                alpha = 0.32 if kind == 'highlighter' else 1.0
                self._set_source(cr, ann['color'], alpha)
                cr.set_line_width(ann['width'] * mult)
                cr.move_to(*pts[0])
                for p in pts[1:]:
                    cr.line_to(*p)
                cr.stroke()
        elif kind == 'arrow':
            self._draw_arrow(cr, ann['start'], ann['end'], ann['color'], ann['width'])
        elif kind in ('rect', 'ellipse', 'redact'):
            x, y, w, h = norm_rect(*ann['start'], *ann['end'])
            if kind == 'redact':
                cr.set_source_rgba(0.0, 0.0, 0.0, 1.0)
                cr.rectangle(x, y, w, h)
                cr.fill()
            elif kind == 'rect':
                self._set_source(cr, ann['color'])
                cr.set_line_width(ann['width'])
                cr.rectangle(x, y, w, h)
                cr.stroke()
            else:
                if w > 0 and h > 0:
                    self._set_source(cr, ann['color'])
                    cr.save()
                    cr.translate(x + w / 2.0, y + h / 2.0)
                    cr.scale(w / 2.0, h / 2.0)
                    # Cairo scales the stroke too, so compensate approximately.
                    cr.set_line_width(ann['width'] / max(1.0, min(w, h) / 2.0))
                    cr.arc(0, 0, 1, 0, 2 * math.pi)
                    cr.stroke()
                    cr.restore()
        elif kind == 'text':
            self._set_source(cr, ann['color'])
            cr.select_font_face('Sans', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(ann['size'])
            cr.move_to(ann['x'], ann['y'])
            cr.show_text(ann['text'])

        cr.restore()

    def _draw_arrow(self, cr, start, end, color, width):
        x1, y1 = start
        x2, y2 = end
        self._set_source(cr, color)
        cr.set_line_width(width)
        cr.move_to(x1, y1)
        cr.line_to(x2, y2)
        cr.stroke()

        angle = math.atan2(y2 - y1, x2 - x1)
        head = max(10.0, width * 3.2)
        spread = math.radians(28)
        p1 = (x2 - head * math.cos(angle - spread), y2 - head * math.sin(angle - spread))
        p2 = (x2 - head * math.cos(angle + spread), y2 - head * math.sin(angle + spread))
        cr.move_to(x2, y2)
        cr.line_to(*p1)
        cr.move_to(x2, y2)
        cr.line_to(*p2)
        cr.stroke()

    def _draw_preview(self, cr):
        if self.drag_start is None or self.drag_current is None:
            return
        if self.tool in ('pen', 'highlighter') and self.current_points:
            self._draw_annotation(cr, {
                'kind': self.tool,
                'points': self.current_points,
                'color': self.color,
                'width': self.stroke_width,
            })
            return

        if self.tool == 'crop':
            x, y, w, h = norm_rect(*self.drag_start, *self.drag_current)
            cr.save()
            cr.set_source_rgba(0, 0, 0, 0.45)
            cr.rectangle(0, 0, self.img_w, y)
            cr.rectangle(0, y + h, self.img_w, self.img_h - (y + h))
            cr.rectangle(0, y, x, h)
            cr.rectangle(x + w, y, self.img_w - (x + w), h)
            cr.fill()
            cr.set_source_rgba(1, 1, 1, 0.95)
            cr.set_line_width(max(1.0, 2.0 / self.zoom))
            cr.rectangle(x, y, w, h)
            cr.stroke()
            cr.restore()
            return

        if self.tool in ('arrow', 'rect', 'ellipse', 'redact'):
            self._draw_annotation(cr, {
                'kind': self.tool,
                'start': self.drag_start,
                'end': self.drag_current,
                'color': self.color,
                'width': self.stroke_width,
            })

    def _render_flattened(self):
        out = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.img_w, self.img_h)
        cr = cairo.Context(out)
        cr.set_source_surface(self.base, 0, 0)
        cr.paint()
        for ann in self.annotations:
            self._draw_annotation(cr, ann)
        out.flush()
        return out

    def _copy_to_clipboard(self):
        fd, path = tempfile.mkstemp(prefix='zorin-shot-copy-', suffix='.png')
        os.close(fd)
        try:
            self._render_flattened().write_to_png(path)
            texture = Gdk.Texture.new_from_filename(path)
            png_bytes = texture.save_to_png_bytes()
            content = Gdk.ContentProvider.new_for_bytes('image/png', png_bytes)
            clipboard = Gdk.Display.get_default().get_clipboard()
            clipboard.set_content(content)
            self.status.set_text(self._t('copied'))
            # Keep the file briefly: some clipboard backends may consume lazily.
            GLib.timeout_add_seconds(30, self._delete_temp, path)
        except Exception as exc:
            try:
                os.unlink(path)
            except OSError:
                pass
            self._error(self._t('copy_failed', error=exc))

    def _delete_temp(self, path):
        try:
            os.unlink(path)
        except OSError:
            pass
        return GLib.SOURCE_REMOVE

    def _default_save_name(self):
        stamp = GLib.DateTime.new_now_local().format('%Y-%m-%d_%H-%M-%S')
        return f'ZorinShot_{stamp}.png'

    def _save_as(self):
        dialog = Gtk.FileChooserNative.new(
            self._t('save_screenshot'), self, Gtk.FileChooserAction.SAVE,
            self._t('save'), self._t('cancel_mnemonic'))
        dialog.set_current_name(self._default_save_name())
        pictures = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_PICTURES)
        if pictures:
            try:
                dialog.set_current_folder(Gio.File.new_for_path(pictures))
            except Exception:
                pass
        dialog.connect('response', self._save_response)
        self._save_dialog = dialog
        dialog.show()

    def _save_response(self, dialog, response):
        try:
            if response == Gtk.ResponseType.ACCEPT:
                file = dialog.get_file()
                path = file.get_path() if file else None
                if path:
                    if not path.lower().endswith('.png'):
                        path += '.png'
                    self._render_flattened().write_to_png(path)
                    self.status.set_text(self._t('saved', path=path))
        except Exception as exc:
            self._error(self._t('save_failed', error=exc))
        finally:
            dialog.destroy()
            self._save_dialog = None

    def _error(self, message):
        self.status.set_text(message)
        dialog = Gtk.Dialog(transient_for=self, modal=True, title=self._t('editor_error'))
        dialog.add_button(self._t('ok'), Gtk.ResponseType.OK)
        label = Gtk.Label(label=message, wrap=True)
        label.set_margin_top(16)
        label.set_margin_bottom(16)
        label.set_margin_start(16)
        label.set_margin_end(16)
        dialog.get_content_area().append(label)
        dialog.connect('response', lambda d, _r: d.destroy())
        dialog.present()

    def _key_pressed(self, _controller, keyval, _keycode, state):
        ctrl = bool(state & Gdk.ModifierType.CONTROL_MASK)
        shift = bool(state & Gdk.ModifierType.SHIFT_MASK)
        if ctrl and keyval in (Gdk.KEY_z, Gdk.KEY_Z):
            if shift:
                self._redo()
            else:
                self._undo()
            return True
        if ctrl and keyval in (Gdk.KEY_y, Gdk.KEY_Y):
            self._redo()
            return True
        if ctrl and keyval in (Gdk.KEY_c, Gdk.KEY_C):
            self._copy_to_clipboard()
            return True
        if ctrl and keyval in (Gdk.KEY_s, Gdk.KEY_S):
            self._save_as()
            return True
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
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
