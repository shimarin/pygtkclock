#!/usr/bin/env python3
"""GTK4 アナログ時計 - dotnetclock の見た目を再現"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gtk, Gdk, GLib, Gio, Gst
import cairo
import math
import os
import sys
from datetime import datetime

Gst.init(None)

RESIZE_HANDLE_SIZE = 22
CHIME_QUIET_START = 22  # 夜10時以降は無音
CHIME_QUIET_END   = 5   # 朝5時まで無音


CHIME_INTERVAL_MS = 2000  # 打鐘間隔 (ms)

# 時報音声は XDG データディレクトリ配下の pygtkclock/chime.<ext> を自動検出する。
# 例: ~/.local/share/pygtkclock/chime.ogg, /usr/share/pygtkclock/chime.ogg
CHIME_SUBDIR = 'pygtkclock'
CHIME_BASENAME = 'chime'
# GStreamer playbin が（プラグイン次第で）再生しうる形式を優先順で。
CHIME_EXTS = (
    'ogg', 'oga', 'opus', 'flac', 'wav',
    'mp3', 'm4a', 'aac', 'aiff', 'aif', 'wma',
)


def find_chime_file():
    """時報音声ファイルを探して最初に見つかったパスを返す。無ければ None。"""
    search_dirs = []
    # XDG: ユーザーデータ -> システムデータの順
    search_dirs.append(os.path.join(GLib.get_user_data_dir(), CHIME_SUBDIR))
    for d in GLib.get_system_data_dirs():
        search_dirs.append(os.path.join(d, CHIME_SUBDIR))
    # 開発ツリー: clock.py と同じ場所（zipapp 実行時は存在しないだけ）
    here = os.path.dirname(os.path.abspath(__file__))
    search_dirs.append(here)

    for d in search_dirs:
        for ext in CHIME_EXTS:
            p = os.path.join(d, f'{CHIME_BASENAME}.{ext}')
            if os.path.isfile(p):
                return p
    return None


class ChimePlayer:
    """指定ファイルを count 回、2秒間隔で再生する。前の音の終了を待たずに次を鳴らす。"""

    def __init__(self, sound_file: str):
        self._uri = f'file://{os.path.abspath(sound_file)}'
        self._remaining = 0

    def chime(self, count: int):
        if self._remaining > 0:
            return  # 前の時報がまだ進行中
        self._remaining = count
        self._fire()

    def _fire(self):
        if self._remaining <= 0:
            return GLib.SOURCE_REMOVE
        self._remaining -= 1
        self._play_once()
        if self._remaining > 0:
            GLib.timeout_add(CHIME_INTERVAL_MS, self._fire)
        return GLib.SOURCE_REMOVE

    def _play_once(self):
        player = Gst.ElementFactory.make('playbin', None)
        player.set_property('uri', self._uri)
        bus = player.get_bus()
        bus.add_signal_watch()
        bus.connect('message::eos',   lambda b, m: player.set_state(Gst.State.NULL))
        bus.connect('message::error', lambda b, m: (
            print(f'ChimePlayer error: {m.parse_error()[0]}', file=sys.stderr),
            player.set_state(Gst.State.NULL)
        ))
        player.set_state(Gst.State.PLAYING)


def _pt(cx, cy, r, angle_rad):
    return cx + r * math.cos(angle_rad), cy + r * math.sin(angle_rad)


def _draw_face(cr, cx, cy, radius):
    cr.set_source_rgba(20/255, 20/255, 20/255, 180/255)
    cr.arc(cx, cy, radius, 0, 2 * math.pi)
    cr.fill()

    cr.set_line_width(3.0)
    cr.set_source_rgba(220/255, 220/255, 220/255, 220/255)
    cr.arc(cx, cy, radius, 0, 2 * math.pi)
    cr.stroke()

    for i in range(60):
        a = (i * 6 - 90) * math.pi / 180
        is_hour = (i % 5 == 0)
        outer = radius * 0.92
        inner = radius * 0.78 if is_hour else radius * 0.88
        if is_hour:
            cr.set_line_width(3.0)
            cr.set_source_rgba(230/255, 230/255, 230/255, 230/255)
        else:
            cr.set_line_width(1.2)
            cr.set_source_rgba(140/255, 140/255, 140/255, 160/255)
        cr.move_to(*_pt(cx, cy, outer, a))
        cr.line_to(*_pt(cx, cy, inner, a))
        cr.stroke()

    cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    cr.set_font_size(radius * 0.10)
    cr.set_source_rgba(220/255, 220/255, 220/255, 220/255)
    for h in range(1, 13):
        a = (h * 30 - 90) * math.pi / 180
        x, y = _pt(cx, cy, radius * 0.65, a)
        text = str(h)
        e = cr.text_extents(text)
        cr.move_to(x - e.x_bearing - e.width / 2,
                   y - e.y_bearing - e.height / 2)
        cr.show_text(text)


def _draw_date(cr, cx, cy, radius, now):
    dow = now.weekday()  # 0=月, 6=日
    char = ['月', '火', '水', '木', '金', '土', '日'][dow]
    if dow == 5:
        dow_rgba = (110/255, 160/255, 1.0, 220/255)
    elif dow == 6:
        dow_rgba = (1.0, 90/255, 90/255, 220/255)
    else:
        dow_rgba = (210/255, 210/255, 210/255, 210/255)

    date_str = f"{now.month}月{now.day}日"
    dow_str  = f"({char})"

    cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    cr.set_font_size(radius * 0.13)
    de = cr.text_extents(date_str)
    we = cr.text_extents(dow_str)
    total_w = de.x_advance + we.x_advance
    x = cx - total_w / 2
    y = cy - radius * 0.33 - de.y_bearing - de.height / 2

    cr.set_source_rgba(210/255, 210/255, 210/255, 210/255)
    cr.move_to(x, y)
    cr.show_text(date_str)
    cr.set_source_rgba(*dow_rgba)
    cr.move_to(x + de.x_advance, y)
    cr.show_text(dow_str)


def _draw_hand(cr, cx, cy, angle, length, width, rgba):
    perp = angle + math.pi / 2
    hw = width / 2
    tip_x  = cx + length     * math.cos(angle)
    tip_y  = cy + length     * math.sin(angle)
    tail_x = cx - width*1.5  * math.cos(angle)
    tail_y = cy - width*1.5  * math.sin(angle)
    pts = [
        (cx     + hw * math.cos(perp), cy     + hw * math.sin(perp)),
        (cx     - hw * math.cos(perp), cy     - hw * math.sin(perp)),
        (tail_x - hw * math.cos(perp), tail_y - hw * math.sin(perp)),
        (tip_x, tip_y),
        (tail_x + hw * math.cos(perp), tail_y + hw * math.sin(perp)),
    ]
    cr.set_source_rgba(*rgba)
    cr.move_to(*pts[0])
    for p in pts[1:]:
        cr.line_to(*p)
    cr.close_path()
    cr.fill()


def _draw_clock(cr, width, height):
    cr.set_operator(cairo.OPERATOR_CLEAR)
    cr.paint()
    cr.set_operator(cairo.OPERATOR_OVER)
    cr.set_antialias(cairo.ANTIALIAS_BEST)

    sz = min(width, height)
    cx, cy = width / 2, height / 2
    radius = sz / 2 - 10
    now = datetime.now()

    _draw_face(cr, cx, cy, radius)
    _draw_date(cr, cx, cy, radius, now)

    # 時針
    a = ((now.hour % 12) * 30 + now.minute * 0.5 + now.second / 120 - 90) * math.pi / 180
    _draw_hand(cr, cx, cy, a, radius * 0.50, radius * 0.045,
               (220/255, 220/255, 220/255, 230/255))

    # 分針
    a = (now.minute * 6 + now.second * 0.1 - 90) * math.pi / 180
    _draw_hand(cr, cx, cy, a, radius * 0.72, radius * 0.030,
               (200/255, 200/255, 200/255, 220/255))

    # 秒針 (テール付き赤線)
    ms = now.microsecond / 1e6
    a = (now.second * 6 + ms * 6 - 90) * math.pi / 180
    cr.set_source_rgba(220/255, 60/255, 60/255, 230/255)
    cr.set_line_width(radius * 0.018)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.move_to(*_pt(cx, cy, -radius * 0.20, a))
    cr.line_to(*_pt(cx, cy,  radius * 0.82, a))
    cr.stroke()
    cr.arc(cx, cy, radius * 0.04, 0, 2 * math.pi)
    cr.fill()

    # 中心ドット (グレー、秒針の上に重ねる)
    cr.set_source_rgba(160/255, 160/255, 160/255, 200/255)
    cr.arc(cx, cy, radius * 0.03, 0, 2 * math.pi)
    cr.fill()

    # リサイズグリップ (右下3本斜め線)
    cr.set_line_width(1.5)
    cr.set_source_rgba(200/255, 200/255, 200/255, 140/255)
    for i in range(3):
        off = 5 + i * 5
        cr.move_to(width - 5, height - off)
        cr.line_to(width - off, height - 5)
        cr.stroke()


class ClockWindow(Gtk.ApplicationWindow):
    def __init__(self, app, chime_player=None):
        super().__init__(application=app)
        self.set_title("Analog Clock")
        self.set_default_size(400, 400)
        self.set_decorated(False)

        self._chime_player = chime_player
        self._last_chime_hour = -1
        self._resizing = False
        self._resize_start_size = 400
        self._resize_start_local = (0.0, 0.0)

        # ウィンドウ背景を透明に
        css = Gtk.CssProvider()
        css.load_from_string(
            "window, window.background, .background { background: transparent; }"
        )
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        drawing = Gtk.DrawingArea()
        drawing.set_draw_func(lambda area, cr, w, h: _draw_clock(cr, w, h))
        self.set_child(drawing)

        # カーソル変更用モーションコントローラ
        motion = Gtk.EventControllerMotion()
        motion.connect('motion', self._on_motion)
        drawing.add_controller(motion)

        # 左ドラッグ: 移動 or リサイズ
        drag = Gtk.GestureDrag()
        drag.set_button(1)
        drag.connect('drag-begin',  self._drag_begin)
        drag.connect('drag-update', self._drag_update)
        drag.connect('drag-end',    self._drag_end)
        drawing.add_controller(drag)

        # 右クリックメニュー
        close_action = Gio.SimpleAction.new('close-window', None)
        close_action.connect('activate', lambda *_: self.close())
        self.add_action(close_action)

        rclick = Gtk.GestureClick()
        rclick.set_button(3)
        rclick.connect('pressed', self._right_click)
        drawing.add_controller(rclick)

        GLib.timeout_add(50, self._tick)

    def _tick(self):
        self.get_child().queue_draw()
        if self._chime_player:
            self._check_chime()
        return GLib.SOURCE_CONTINUE

    def _check_chime(self):
        now = datetime.now()
        if now.minute != 0 or now.second != 0:
            return
        hour = now.hour
        if hour == self._last_chime_hour:
            return  # この時を既に鳴らした
        self._last_chime_hour = hour
        if CHIME_QUIET_START <= hour or hour <= CHIME_QUIET_END:
            return  # 夜10時〜朝5時は無音
        count = hour % 12 or 12
        self._chime_player.chime(count)

    def _is_resize_area(self, x, y):
        return (x >= self.get_width()  - RESIZE_HANDLE_SIZE and
                y >= self.get_height() - RESIZE_HANDLE_SIZE)

    def _on_motion(self, ctrl, x, y):
        name = 'se-resize' if self._is_resize_area(x, y) else 'default'
        self.set_cursor_from_name(name)

    def _drag_begin(self, gesture, x, y):
        if self._is_resize_area(x, y):
            self._resizing = True
            self._resize_start_size = self.get_width()
            self._resize_start_local = (x, y)
            gesture.set_state(Gtk.EventSequenceState.CLAIMED)
        else:
            seq   = gesture.get_last_updated_sequence()
            event = gesture.get_last_event(seq)
            surface = self.get_surface()
            device  = self.get_display().get_default_seat().get_pointer()
            try:
                surface.begin_move(device, 1, x, y, event.get_time())
            except Exception:
                pass
            gesture.set_state(Gtk.EventSequenceState.DENIED)

    def _drag_update(self, gesture, dx, dy):
        if self._resizing:
            new_size = max(150, self._resize_start_size + int(max(dx, dy)))
            self.set_size_request(new_size, new_size)

    def _drag_end(self, gesture, dx, dy):
        if self._resizing:
            new_size = max(150, self._resize_start_size + int(max(dx, dy)))
            self.set_default_size(new_size, new_size)
            self.set_size_request(-1, -1)
        self._resizing = False

    def _right_click(self, gesture, n_press, x, y):
        menu = Gio.Menu()
        menu.append('閉じる', 'win.close-window')
        popover = Gtk.PopoverMenu.new_from_model(menu)
        popover.set_parent(self.get_child())
        rect = Gdk.Rectangle()
        rect.x, rect.y = int(x), int(y)
        rect.width = rect.height = 1
        popover.set_pointing_to(rect)
        popover.popup()


class ClockApp(Gtk.Application):
    def __init__(self, chime_player=None):
        super().__init__(application_id='com.walbrix.analogclock')
        self._chime_player = chime_player
        self.connect('activate', self._on_activate)

    def _on_activate(self, app):
        ClockWindow(app, chime_player=self._chime_player).present()


if __name__ == '__main__':
    # 時報音声は XDG データディレクトリの pygtkclock/chime.<ext> を自動検出する。
    # 見つからなければ無音で動作する。
    chime = None
    chime_path = find_chime_file()
    if chime_path:
        print(f'時報音声: {chime_path}', file=sys.stderr)
        chime = ChimePlayer(chime_path)

    ClockApp(chime_player=chime).run(sys.argv)
