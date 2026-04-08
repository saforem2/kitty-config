from os import getlogin, uname
import re
import subprocess
from datetime import datetime
from kitty.boss import get_boss
from kitty.fast_data_types import Screen, get_options
from kitty.utils import color_as_int
from kitty.tab_bar import (
    DrawData,
    ExtraData,
    Formatter,
    TabBarData,
    as_rgb,
    draw_attributed_string,
    draw_title,
)
"""
ABOUT

Custom Kitty tab bar with three sections:
  - Left status
  - Tab Bar (with overflow indicators)
  - Right status

Left status:
  - Kitty emoji (😺)
  - Powerline separator

Tab Bar:
  - Individual tabs with:
    - Tab number
    - Title (rewritten to icons: 🏠 for home, 🗑️ for /tmp, ⚡ for ssh)
    - Window count (⊞ N) if multiple windows
    - Powerline separators
  - Overflow handling:
    - » (right) indicator when tabs are hidden after visible range
    - Smart overflow: active tab always visible, other tabs hidden when space runs out
  - Dynamic width calculation: adjusts tab width based on terminal size and tab count

Right status (fixed position):
  - Git branch ( branchname, if in git repository, with clock on same background)
  - Clock (🕐 HH:MM)
  - User (👨 username)
  - Host (🖥️ hostname)
  - Proper emoji width handling with wcwidth
"""
opts = get_options()

# Use background color as tab_background color if none is set by the theme
if opts.tab_bar_background is None:
    opts.tab_bar_background = opts.background
    # don't trust themes
    # opts.tab_bar_background = Color(0, 0, 0)
    # opts.tab_bar_background = Color(237, 28, 36) # red
    # opts.tab_bar_background = Color(229, 192, 123) # yellowish


config = {"tab_width": 25, "rewrite_title": True}
colors = {
    "fg": as_rgb(color_as_int(opts.inactive_tab_foreground)),
    "bg": as_rgb(color_as_int(opts.inactive_tab_background)),
    "active_fg": as_rgb(color_as_int(opts.active_tab_foreground)),
    "active_bg": as_rgb(color_as_int(opts.active_tab_background)),
    "bar_bg": as_rgb(color_as_int(opts.tab_bar_background)),
    "accent": as_rgb(color_as_int(opts.selection_background)),
    "background": as_rgb(color_as_int(opts.background)),
}
symbols = {"separator_right": "", "separator_left": "", "truncation": "»", "overflow_left": "«", "overflow_right": "»"}
icons = {
    "kitty": "😺",
    "window": " ⊞",  # alt: 🪟
    "tab": "📑",
    "host": "🖥️",
    "user": "👨",
    "home": "🏠",
    "root": "🌳",
    "trash": "🗑️",
    "ssh": "⚡",
    "git": "",
    "clock": "🕐",
}

_overflow_state = {
    "total_tabs": 0,
    "active_tab": 1,
    "visible_start": 1,
    "visible_end": 0,
    "right_width": 0,
    "tab_area_start": 0,
    "tab_area_end": 0,
    "overflow_triggered": False,
    "tab_width": 0,
    "num_tabs": 1
}


def _draw_window_count(screen: Screen, num_window_groups: int) -> bool:
    if num_window_groups > 1:
        screen.draw(icons["window"] + str(num_window_groups))
    return True


def _get_git_branch() -> str:
    tab_manager = get_boss().active_tab_manager
    if not tab_manager or not tab_manager.active_window:
        return ""

    cwd = tab_manager.active_window.cwd_of_child
    if not cwd:
        return ""

    try:
        result = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=0.1
        )
        if result.returncode == 0:
            branch = result.stdout.strip()
            return f" {branch}" if branch else ""
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return ""


def _draw_git_branch(screen: Screen) -> int:
    branch = _get_git_branch()
    if branch:
        screen.cursor.fg = colors["fg"]
        screen.cursor.bg = colors["bg"]
        screen.draw(icons["git"] + branch)
    return screen.cursor.x


def _draw_left(screen: Screen) -> int:
    screen.cursor.bg = colors["bg"]
    screen.draw(icons["kitty"])
    screen.cursor.x = len(icons["kitty"]) + 1

    screen.cursor.fg = colors["bg"]
    screen.cursor.bg = colors["bar_bg"]
    screen.draw(symbols["separator_right"] + " ")

    return screen.cursor.x


def _calculate_tab_width(screen: Screen, num_tabs: int) -> int:
    left_width = 25
    right_width = 38
    available_width = screen.columns - left_width - right_width

    if num_tabs > 0:
        dynamic_width = available_width // num_tabs
        min_width = 15
        max_width = config["tab_width"]
        return max(min_width, min(max_width, dynamic_width))

    return config["tab_width"]


def _rewrite_title(title: str) -> str:
    new_title = ""
    if "~" in title:
        new_title = icons["home"]
    elif "/tmp" in title:
        new_title = icons["trash"]
    elif title.startswith("ssh") or "@" in title:
        # Handle both "ssh hostname" and "user@hostname" formats
        pattern = re.compile(r"^ssh (\w+)")
        match = re.search(pattern, title)
        if match:
            new_title = icons["ssh"] + " " + match.group(1)
        else:
            # Extract hostname from "user@hostname" format
            at_pattern = re.compile(r"@([\w\.-]+)")
            at_match = re.search(at_pattern, title)
            if at_match:
                new_title = icons["ssh"] + " " + at_match.group(1)
            else:
                return title
    else:
        return title

    return new_title


def _get_tab_metadata():
    try:
        tab_manager = get_boss().active_tab_manager
        if tab_manager:
            num_tabs = len(tab_manager.tabs)
            for i, t in enumerate(tab_manager.tabs, 1):
                if t.id == tab_manager.active_tab.id:
                    return num_tabs, i
        return 1, 1
    except:
        return 1, 1


def _draw_tabbar(
    draw_data: DrawData,
    screen: Screen,
    tab: TabBarData,
    index: int,
    extra_data: ExtraData,
) -> int:
    if tab.is_active:
        tab_fg = colors["active_fg"]
        tab_bg = colors["active_bg"]
    else:
        tab_fg = colors["fg"]
        tab_bg = colors["bg"]
    bar_bg = colors["bar_bg"]

    screen.cursor.fg, screen.cursor.bg = tab_bg, bar_bg
    screen.draw(symbols["separator_left"])

    screen.cursor.fg, screen.cursor.bg = tab_fg, tab_bg
    screen.draw(f"{index} ")

    dynamic_width = _overflow_state["tab_width"]
    if dynamic_width and len(tab.title) > dynamic_width:
        title_length = dynamic_width - 2
        tab = tab._replace(title=f"{tab.title:^{dynamic_width}.{title_length}}")

    if config["rewrite_title"]:
        new_title = _rewrite_title(tab.title)
        tab = tab._replace(title=new_title)

    draw_title(draw_data, screen, tab, index)
    _draw_window_count(screen, tab.num_window_groups)

    screen.cursor.fg, screen.cursor.bg = tab_bg, bar_bg
    screen.draw(symbols["separator_right"])
    screen.draw(opts.tab_separator)

    return screen.cursor.x


def _draw_overflow_left(screen: Screen) -> int:
    screen.cursor.fg = colors["fg"]
    screen.cursor.bg = colors["bar_bg"]
    screen.draw(" " + symbols["overflow_left"])
    return screen.cursor.x


def _draw_overflow_right(screen: Screen) -> int:
    screen.cursor.fg = colors["fg"]
    screen.cursor.bg = colors["bar_bg"]
    screen.draw(symbols["overflow_right"] + " ")
    return screen.cursor.x


def _should_skip_tab(index: int, screen_x: int, tab_area_end: int, total_tabs: int, active_tab: int) -> bool:
    overflow_indicator_width = 3
    space_needed = overflow_indicator_width if index < total_tabs else 0
    estimated_tab_width = 12
    would_overflow = (screen_x + estimated_tab_width + space_needed) > tab_area_end

    if would_overflow:
        return index != active_tab

    return False


def _get_right_status_data():
    branch = _get_git_branch()
    time_str = icons["clock"] + datetime.now().strftime("%H:%M")
    user = icons["user"] + getlogin()
    host = icons["host"] + uname()[1]
    return branch, time_str, user, host


def _calculate_right_width() -> int:
    import wcwidth

    branch, time_str, user, host = _get_right_status_data()

    cells = [symbols["separator_left"]]
    if branch:
        cells.extend([
            icons["git"] + branch,
            " " + time_str
        ])
    else:
        cells.append(time_str)

    cells.extend([symbols["separator_left"], user, symbols["separator_left"], host])

    width = 1
    for cell in cells:
        width += wcwidth.wcswidth(str(cell))

    return width + 1


def _draw_right(screen: Screen, is_last: bool, right_width: int = None) -> int:
    if not is_last:
        return screen.cursor.x
    draw_attributed_string(Formatter.reset, screen)

    branch, time_str, user, host = _get_right_status_data()

    cells = [
        (colors["bg"], colors["bar_bg"], symbols["separator_left"]),
    ]
    if branch:
        cells.extend([
            (colors["fg"], colors["bg"], icons["git"] + branch),
            (colors["fg"], colors["bg"], " " + time_str),
        ])
    else:
        cells.append((colors["fg"], colors["bg"], time_str))

    cells.extend([
        (colors["bg"], colors["bg"], symbols["separator_left"]),
        (colors["fg"], colors["bg"], user),
        (colors["bg"], colors["bg"], symbols["separator_left"]),
        (colors["fg"], colors["bg"], host)
    ])

    if right_width is None:
        right_width = _calculate_right_width()

    target_x = screen.columns - right_width

    if screen.cursor.x < target_x:
        screen.cursor.bg = colors["bar_bg"]
        screen.draw(" " * (target_x - screen.cursor.x))

    for fg, bg, content in cells:
        screen.cursor.fg = fg
        screen.cursor.bg = bg
        screen.draw(content)

    remaining = screen.columns - screen.cursor.x
    if remaining > 0:
        screen.cursor.bg = colors["bg"]
        screen.draw(" " * remaining)

    return screen.cursor.x


def _initialize_state(screen: Screen):
    _draw_left(screen)
    _overflow_state["tab_area_start"] = screen.cursor.x
    _overflow_state["current_width"] = 0
    _overflow_state["overflow_triggered"] = False
    _overflow_state["visible_end"] = 0
    _overflow_state["visible_start"] = 1
    _overflow_state["right_width"] = _calculate_right_width()
    _overflow_state["tab_area_end"] = screen.columns - _overflow_state["right_width"]

    num_tabs, active_tab = _get_tab_metadata()
    _overflow_state["num_tabs"] = num_tabs
    _overflow_state["total_tabs"] = num_tabs
    _overflow_state["active_tab"] = active_tab
    _overflow_state["tab_width"] = _calculate_tab_width(screen, num_tabs)


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
    global _overflow_state

    if index == 1:
        _initialize_state(screen)

    if index < _overflow_state["visible_start"]:
        if is_last:
            _draw_right(screen, is_last, _overflow_state["right_width"])
        return screen.cursor.x

    if index == _overflow_state["visible_start"] and _overflow_state["visible_start"] > 1:
        _draw_overflow_left(screen)

    skip = _should_skip_tab(
        index,
        screen.cursor.x,
        _overflow_state["tab_area_end"],
        _overflow_state["total_tabs"],
        _overflow_state["active_tab"]
    )

    if skip:
        if not _overflow_state["overflow_triggered"]:
            _overflow_state["overflow_triggered"] = True
            _overflow_state["visible_end"] = index - 1
            _draw_overflow_right(screen)

        if is_last:
            _draw_right(screen, is_last, _overflow_state["right_width"])
        return screen.cursor.x

    if _overflow_state["visible_end"] < index:
        _overflow_state["visible_end"] = index

    pos_before = screen.cursor.x
    _draw_tabbar(draw_data, screen, tab, index, extra_data)
    pos_after = screen.cursor.x
    _overflow_state["current_width"] += (pos_after - pos_before)

    if is_last:
        if _overflow_state["visible_end"] < _overflow_state["total_tabs"] and not _overflow_state["overflow_triggered"]:
            _draw_overflow_right(screen)

        _draw_right(screen, is_last, _overflow_state["right_width"])

    return screen.cursor.x

