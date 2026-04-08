#!/usr/bin/env python3
# Standalone script to display a formatted keyboard shortcut cheatsheet
# Reads kitty config files directly — no kitty API dependency.
# Tables are arranged side-by-side to fill available terminal width.
# Usage: map kitty_mod+m launch --type=overlay python3 ~/.config/kitty/keymap.py

import re
import glob
import os
import sys
import tty
import termios
from collections import OrderedDict

# ANSI color helpers
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
WHITE = "\033[37m"
PINK = "\033[38;5;205m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
LAVENDER = "\033[38;5;183m"
GRAY = "\033[38;5;245m"
ORANGE = "\033[38;5;209m"

CATEGORY_COLORS = [PINK, CYAN, GREEN, YELLOW, BLUE, MAGENTA, LAVENDER]

# Per-modifier colors
MOD_COLORS = {
    'kitty_mod': PINK,
    'cmd':       CYAN,
    'ctrl':      GREEN,
    'alt':       ORANGE,
    'shift':     LAVENDER,
    'super':     YELLOW,
    'opt':       CYAN,
}

# Categories and patterns (first match wins)
categories = OrderedDict((
    ('Navigation',        r'(neighboring_window|focus_visible|move_window|swap_with)'),
    ('Splits & Layout',   r'(launch.*(split|location)|resize_window|layout_action|zoom_toggle|toggle_maximized)'),
    ('Scrolling',         r'(scroll_|show_scrollback|show_last|last_cmd_output|screen_scrollback)'),
    ('Tabs',              r'(tab|goto_tab|next_tab|previous_tab|next_layout)'),
    ('Windows & OS',      r'(new_os_window|close_os_window|close_window)'),
    ('Clipboard',         r'(copy_|paste_|pass_selection)'),
    ('Hints',             r'(khints|kitten hints|open_url)'),
    ('Font & Appearance', r'(font_size|background_opacity)'),
    ('Search & Browse',   r'(search|pipe.*overlay|vim-ansi)'),
    ('Kittens & Tools',   r'(kitten |kitty_shell|kitty_scrollback|kitty_config|edit_config|unicode_input|grab\.py|keymap\.py)'),
    ('Config',            r'(load_config|debug_config)'),
    ('Misc',              r'.'),
))

# Box-drawing characters
H = "─"; V = "│"
TL = "╭"; TR = "╮"; BL = "╰"; BR = "╯"
TD = "┬"; TU = "┴"; TRight = "├"; TLeft = "┤"; X = "┼"

ANSI_RE = re.compile(r'\033\[[0-9;]*m')
COL_GAP = 3  # spaces between side-by-side tables



def visible_len(s):
    """Length of string ignoring ANSI escape codes."""
    return len(ANSI_RE.sub('', s))


def pad_to_visible(s, width):
    """Pad string with spaces so its visible width equals `width`."""
    return s + ' ' * (width - visible_len(s))


def colorize_key(key_str):
    """Colorize modifier prefixes in a key string, return (colored, plain_len)."""
    plain = key_str
    parts = key_str.split('+')
    if len(parts) <= 1:
        return f"{BOLD}{WHITE}{key_str}{RESET}", len(key_str)

    colored = ""
    for i, part in enumerate(parts):
        is_last = (i == len(parts) - 1)
        suffix = '' if is_last else '+'
        mod_color = MOD_COLORS.get(part.lower())
        if mod_color and not is_last:
            colored += f"{mod_color}{part}{DIM}{suffix}{RESET}"
        else:
            colored += f"{BOLD}{WHITE}{part}{suffix}{RESET}"

    return colored, len(plain)


def parse_bindings(config_dir):
    """Read all .conf files and extract 'map' lines."""
    bindings = []
    for path in sorted(glob.glob(os.path.join(config_dir, "*.conf"))):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("map "):
                    parts = line.split(None, 2)
                    if len(parts) >= 3:
                        key, action = parts[1], parts[2]
                        if action != "no_op":
                            bindings.append((key, action))
    return bindings


def prettify_action(s):
    """Shorten action strings for display."""
    s = s.replace('kitten ~/.config/kitty/', '⚙ ')
    s = s.replace('launch --allow-remote-control kitty +kitten ~/.config/kitty/', '⚙ ')
    s = s.replace('launch --allow-remote-control kitty +', '⚙ ')
    s = s.replace('launch --stdin-source=@screen_scrollback --stdin-add-formatting', 'scrollback →')
    s = s.replace('launch --stdin-source=@last_cmd_output --stdin-add-formatting', 'last output →')
    s = s.replace('launch --type=overlay', 'overlay:')
    s = s.replace('launch --type=window', 'window:')
    s = s.replace('launch --location=hsplit', 'hsplit:')
    s = s.replace('launch --location=vsplit', 'vsplit:')
    s = s.replace('--hints-foreground-color=#FF1A8F --hints-background-color=#FFE0FF', '')
    s = s.replace('--hints-offset=0', '')
    s = re.sub(r'  +', ' ', s)
    return s.strip()


def render_block(cat, entries, color):
    """Render a single category as a block of lines. Returns (lines, visible_width)."""
    display = [(k, prettify_action(a)) for k, a in entries]
    display.sort(key=lambda x: x[0])

    kw = max(max(len(k) for k, _ in display), 10)
    aw = max(max(len(a) for _, a in display), 16)

    table_w = kw + aw + 7

    lines = []
    lines.append(f" {BOLD}{color}▎ {cat}{RESET}")
    lines.append(f" {DIM}{TL}{H*(kw+2)}{TD}{H*(aw+2)}{TR}{RESET}")
    for i, (key, action) in enumerate(display):
        k_colored, k_plain_len = colorize_key(key)
        k_padded = k_colored + ' ' * (kw - k_plain_len)
        a = f"{GRAY}{action:<{aw}}{RESET}"
        lines.append(f" {DIM}{V}{RESET} {k_padded} {DIM}{V}{RESET} {a} {DIM}{V}{RESET}")
        if i < len(display) - 1:
            lines.append(f" {DIM}{TRight}{H*(kw+2)}{X}{H*(aw+2)}{TLeft}{RESET}")
    lines.append(f" {DIM}{BL}{H*(kw+2)}{TU}{H*(aw+2)}{BR}{RESET}")

    return lines, table_w


def merge_blocks_horizontal(block_list, term_width):
    """Arrange blocks side-by-side in rows that fit within term_width."""
    rows = []
    current_row = []
    current_width = 0

    for lines, width in block_list:
        needed = width + (COL_GAP if current_row else 0)
        if current_row and current_width + needed > term_width:
            rows.append(current_row)
            current_row = [(lines, width)]
            current_width = width
        else:
            current_row.append((lines, width))
            current_width += needed

    if current_row:
        rows.append(current_row)

    output = []
    for row in rows:
        max_height = max(len(lines) for lines, _ in row)
        padded = []
        for lines, width in row:
            extended = lines + [''] * (max_height - len(lines))
            padded.append((extended, width))

        for line_idx in range(max_height):
            combined = ""
            for col_idx, (lines, width) in enumerate(padded):
                if col_idx > 0:
                    combined += ' ' * COL_GAP
                line = lines[line_idx]
                combined += pad_to_visible(line, width + 1)
            output.append(combined.rstrip())
        output.append("")

    return output


def read_key(fd):
    """Read a keypress, handling escape sequences for arrow keys."""
    ch = os.read(fd, 1)
    if ch == b'\x1b':
        seq = os.read(fd, 2)
        if seq == b'[A':
            return 'up'
        elif seq == b'[B':
            return 'down'
        elif seq == b'[5':
            os.read(fd, 1)  # consume ~
            return 'pgup'
        elif seq == b'[6':
            os.read(fd, 1)  # consume ~
            return 'pgdn'
        return 'esc'
    return ch.decode('utf-8', errors='replace')


def render_all(bindings, term_width, query=""):
    """Categorize bindings, render blocks, return list of display lines."""
    if query:
        q = query.lower()
        bindings = [(k, a) for k, a in bindings if q in k.lower() or q in a.lower()]

    categorized = {}
    for key, action in bindings:
        for cat, pattern in categories.items():
            if re.search(pattern, action):
                categorized.setdefault(cat, []).append((key, action))
                break

    out = []
    out.append("")
    if query:
        out.append(f"  {BOLD}{PINK}  Kitty Keybindings{RESET}  {DIM}{GRAY}matching{RESET} {BOLD}{CYAN}{query}{RESET}  {DIM}{GRAY}({len(bindings)} results){RESET}")
    else:
        out.append(f"  {BOLD}{PINK}  Kitty Keybindings{RESET}")
    out.append(f"  {DIM}{GRAY}{'─' * (term_width - 4)}{RESET}")
    out.append(f"  {DIM}{GRAY}kitty_mod = alt+shift  │  j/k scroll  │  / search  │  q close{RESET}")
    out.append("")

    blocks = []
    ci = 0
    for cat in categories:
        entries = categorized.get(cat, [])
        if not entries:
            continue
        color = CATEGORY_COLORS[ci % len(CATEGORY_COLORS)]
        ci += 1
        block_lines, block_width = render_block(cat, entries, color)
        blocks.append((block_lines, block_width))

    if blocks:
        out.extend(merge_blocks_horizontal(blocks, term_width))
    else:
        out.append(f"  {DIM}{GRAY}No matches.{RESET}")
        out.append("")

    return out


def read_search_input(fd):
    """Read a character in search mode. Returns (char, special) where special is a control signal."""
    ch = os.read(fd, 1)
    if ch == b'\x1b':
        os.read(fd, 2)  # consume escape sequence
        return None, 'esc'
    if ch == b'\r' or ch == b'\n':
        return None, 'enter'
    if ch == b'\x7f' or ch == b'\x08':
        return None, 'backspace'
    if ch == b'\x03':
        return None, 'ctrl-c'
    return ch.decode('utf-8', errors='replace'), None


def pager(bindings, term_width):
    """Interactive pager with / search. Renders from bindings data."""
    fd = sys.stdin.fileno()
    old_attrs = termios.tcgetattr(fd)

    sys.stdout.write('\033[?1049h\033[?25l')
    sys.stdout.flush()

    query = ""
    lines = render_all(bindings, term_width)

    try:
        tty.setraw(fd)
        offset = 0
        term_h = os.get_terminal_size().lines
        max_offset = max(len(lines) - term_h + 1, 0)

        while True:
            sys.stdout.write('\033[2J\033[H')
            visible = lines[offset:offset + term_h]
            sys.stdout.write('\r\n'.join(visible))
            sys.stdout.flush()

            key = read_key(fd)
            if key in ('q', 'Q', '\x03'):
                break
            elif key == 'esc':
                if query:
                    query = ""
                    lines = render_all(bindings, term_width)
                    offset = 0
                    max_offset = max(len(lines) - term_h + 1, 0)
                else:
                    break
            elif key == '/':
                # Enter search mode — show cursor and prompt
                sys.stdout.write('\033[?25h')
                search_buf = query
                while True:
                    # Draw search prompt on last line
                    sys.stdout.write(f'\033[{term_h};1H\033[2K')
                    sys.stdout.write(f' {BOLD}{CYAN}/{RESET}{search_buf}\033[K')
                    sys.stdout.flush()

                    ch, special = read_search_input(fd)
                    if special == 'enter':
                        break
                    elif special in ('esc', 'ctrl-c'):
                        search_buf = query  # revert
                        break
                    elif special == 'backspace':
                        search_buf = search_buf[:-1]
                    elif ch:
                        search_buf += ch

                    # Live-filter as user types
                    preview = render_all(bindings, term_width, search_buf)
                    preview_offset = 0
                    sys.stdout.write('\033[2J\033[H')
                    visible = preview[preview_offset:preview_offset + term_h - 1]
                    sys.stdout.write('\r\n'.join(visible))
                    sys.stdout.flush()

                sys.stdout.write('\033[?25l')
                query = search_buf
                lines = render_all(bindings, term_width, query)
                offset = 0
                max_offset = max(len(lines) - term_h + 1, 0)
            elif key in ('j', 'down'):
                offset = min(offset + 1, max_offset)
            elif key in ('k', 'up'):
                offset = max(offset - 1, 0)
            elif key in ('d', 'pgdn', ' '):
                offset = min(offset + term_h // 2, max_offset)
            elif key in ('u', 'pgup'):
                offset = max(offset - term_h // 2, 0)
            elif key == 'g':
                offset = 0
            elif key == 'G':
                offset = max_offset
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_attrs)
        sys.stdout.write('\033[?25h\033[?1049l')
        sys.stdout.flush()


def main():
    config_dir = os.path.expanduser("~/.config/kitty")
    bindings = parse_bindings(config_dir)
    term_width = os.get_terminal_size().columns
    pager(bindings, term_width)


if __name__ == '__main__':
    main()
