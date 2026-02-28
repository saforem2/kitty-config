from datetime import datetime, timezone

from kitty.fast_data_types import Screen
from kitty.rgb import Color
from kitty.tab_bar import (
    DrawData,
    ExtraData,
    Formatter,
    TabBarData,
    as_rgb,
    draw_attributed_string,
    draw_title,
)
from kitty.utils import color_as_int

ICON = "  "
RIGHT_MARGIN = 1

icon_fg = as_rgb(color_as_int(Color(255, 250, 205)))
icon_bg = as_rgb(color_as_int(Color(47, 61, 68)))
clock_color = as_rgb(0x7FBBB3)
utc_color = as_rgb(color_as_int(Color(113, 115, 116)))


def _draw_icon(screen: Screen) -> int:
    fg, bg = screen.cursor.fg, screen.cursor.bg
    screen.cursor.fg = icon_fg
    screen.cursor.bg = icon_bg
    screen.draw(ICON)
    screen.cursor.fg, screen.cursor.bg = fg, bg
    return screen.cursor.x


def _draw_left_status(
    draw_data: DrawData,
    screen: Screen,
    tab: TabBarData,
    before: int,
    max_title_length: int,
    index: int,
    is_last: bool,
    extra_data: ExtraData,
) -> int:
    if draw_data.leading_spaces:
        screen.draw(" " * draw_data.leading_spaces)

    draw_title(draw_data, screen, tab, index)
    trailing_spaces = min(max_title_length - 1, draw_data.trailing_spaces)
    max_title_length -= trailing_spaces
    extra = screen.cursor.x - before - max_title_length
    if extra > 0:
        screen.cursor.x -= extra + 1
        screen.draw("…")
    if trailing_spaces:
        screen.draw(" " * trailing_spaces)
    end = screen.cursor.x
    screen.cursor.bold = screen.cursor.italic = False
    screen.cursor.fg = 0
    if not is_last:
        screen.cursor.bg = as_rgb(color_as_int(draw_data.inactive_bg))
        screen.draw(draw_data.sep)
    screen.cursor.bg = 0
    return end


def _draw_right_status(screen: Screen) -> int:
    draw_attributed_string(Formatter.reset, screen)

    now_utc = datetime.now(timezone.utc)
    clock_text = now_utc.astimezone().strftime("%H:%M")
    utc_text = now_utc.strftime(" (UTC %H:%M)")

    total_len = len(clock_text) + len(utc_text) + RIGHT_MARGIN

    draw_spaces = screen.columns - screen.cursor.x - total_len
    if draw_spaces > 0:
        screen.draw(" " * draw_spaces)

    screen.cursor.fg = clock_color
    screen.draw(clock_text)
    screen.cursor.fg = utc_color
    screen.draw(utc_text)
    screen.cursor.bg = 0

    return screen.cursor.x


def draw_tab(
    draw_data: DrawData,
    screen: Screen,
    tab: TabBarData,
    before: int,
    max_title_length: int,
    index: int,
    is_last: bool,
    extra_data: ExtraData,
) -> int:

    if index == 0:
        _draw_icon(screen)

    end = _draw_left_status(
        draw_data,
        screen,
        tab,
        before,
        max_title_length,
        index,
        is_last,
        extra_data,
    )

    if is_last:
        _draw_right_status(screen)

    return end
