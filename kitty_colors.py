"""Shared color math for the kitty theme mirrors (herdr-theme, leaf-theme).

The kitty themes in themes/theme-{light,dark}.conf are authored in OKLCH, but
every downstream consumer wants hex -- so conversion lives here, along with the
WCAG contrast helpers the mirrors use to keep derived colors legible.

The central idea: do NOT lift greys and muted text straight out of kitty's ANSI
palette. ANSI 'bright black' measures ~1.2:1 against a near-black background,
which is invisible. Derive them instead by blending background toward
foreground until a target contrast ratio is hit -- see at_contrast().
"""

import math
import os
import re
import sys

# The kitty-config checkout; themes/ lives beside this file. realpath, not
# abspath: these scripts are also symlinked into ~/.config/kitty, and abspath
# would resolve to that directory, where themes/ does not exist.
KITTY_DIR = os.path.dirname(os.path.realpath(__file__))

OKLCH_RE = re.compile(r"oklch\(\s*([0-9.]+)(%?)\s+([0-9.]+)\s+([0-9.]+)\s*\)")


def oklch_to_hex(L, C, H):
    """OKLCH -> sRGB hex. Values outside sRGB gamut are clipped per channel."""
    h = math.radians(H)
    a, b = C * math.cos(h), C * math.sin(h)
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bl = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s

    def enc(u):
        u = 12.92 * u if u <= 0.0031308 else 1.055 * (max(u, 0) ** (1 / 2.4)) - 0.055
        return max(0, min(255, round(u * 255)))

    return "#{:02x}{:02x}{:02x}".format(enc(r), enc(g), enc(bl))


def hex_to_oklch(h):
    """sRGB hex -> (L, C, H). The exact inverse of oklch_to_hex().

    Lets a hand-picked hex tint take the same OKLCH-relative path as a colour
    authored in the theme -- i.e. CSS's `oklch(from <c> ...)`, where you keep a
    colour's hue and chroma and move only its lightness. Blending in sRGB
    instead drags the hue through grey; see deepen()'s docstring.
    """
    c = h.lstrip("#")
    rgb = [int(c[i:i + 2], 16) / 255 for i in (0, 2, 4)]

    def dec(u):
        return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4

    r, g, b = (dec(u) for u in rgb)
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = (u ** (1 / 3) if u >= 0 else -((-u) ** (1 / 3))
                  for u in (l, m, s))
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    A = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    B = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    C = math.hypot(A, B)
    H = math.degrees(math.atan2(B, A)) % 360
    return L, C, H


def _lum(h):
    h = h.lstrip("#")
    ch = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    ch = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in ch]
    return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]


def contrast(a, b):
    l1, l2 = sorted((_lum(a), _lum(b)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def mix(a, b, t):
    a, b = a.lstrip("#"), b.lstrip("#")
    return "#" + "".join(
        f"{round(int(a[i:i+2], 16) * (1 - t) + int(b[i:i+2], 16) * t):02x}"
        for i in (0, 2, 4)
    )


def at_contrast(bg, fg, target):
    """Blend bg toward fg until it hits `target` contrast against bg.

    Deriving the greys this way (rather than borrowing kitty's ANSI color8/
    color0) is what keeps them legible: ANSI 'bright black' is near-invisible
    on a near-black panel -- measured 1.16:1, well under the 4.5:1 needed for
    body text.
    """
    lo, hi = 0.0, 1.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if contrast(mix(bg, fg, mid), bg) < target:
            lo = mid
        else:
            hi = mid
    return mix(bg, fg, hi)


def legible(color, bg, fg, target=4.5):
    """Nudge a hue toward the foreground until it clears `target` contrast.

    Bright ANSI colors are low-contrast on a white panel -- the light theme's
    yellow measures 2.18:1 -- so any of them used as text needs deepening. Hue
    is preserved; colors already at target pass through unchanged, which makes
    this close to a no-op on the dark theme.
    """
    if contrast(color, bg) >= target:
        return color
    for i in range(1, 41):
        candidate = mix(color, fg, i / 40)
        if contrast(candidate, bg) >= target:
            return candidate
    return fg


def deepen(color, raw, bg, fg, target):
    """Push `color` to `target` contrast, preserving chroma where possible.

    `raw` is the color as authored in the kitty conf; when it is an oklch()
    string we walk L while holding C and H, because a plain mix() toward `fg`
    drags the hue and washes the chroma out -- on the light theme it took the
    accent pink from 72% to 46% saturation, visibly muddy. Falls back to
    blending when `raw` is not OKLCH.
    """
    if contrast(color, bg) >= target:
        return color

    m = OKLCH_RE.match((raw or "").strip())
    if m:
        L0 = float(m.group(1)) / (100 if m.group(2) else 1)
        C0, H0 = float(m.group(3)), float(m.group(4))
        # Direction is set by the PANEL, not by the color: to gain contrast you
        # move away from the background. Keying this off the color's own L0
        # silently walked the wrong way for any bright hue on a dark panel --
        # the dark theme's red (#fc1a70, L0=0.64) hit the loop bound and was
        # returned unchanged at 4.48:1 against a 6.0 target.
        darker = _lum(bg) > 0.5   # light panel -> go down; dark panel -> go up
        for step in range(1, 61):
            L = L0 + (-step if darker else step) * 0.01
            if not 0.0 <= L <= 1.0:
                break
            cand = oklch_to_hex(L, C0, H0)
            if contrast(cand, bg) >= target:
                return cand
        return color

    for i in range(1, 61):
        cand = mix(color, fg, i / 60)
        if contrast(cand, bg) >= target:
            return cand
    return color


def parse_color(v):
    v = v.strip()
    if re.fullmatch(r"#[0-9a-fA-F]{6}", v):
        return v.lower()
    m = OKLCH_RE.match(v)
    if not m:
        return None
    L = float(m.group(1))
    if m.group(2):  # percentage form
        L /= 100
    return oklch_to_hex(L, float(m.group(3)), float(m.group(4)))


def load_kitty_theme(mode, who="kitty-colors"):
    """Parse themes/theme-{mode}.conf into {key: hex}.

    Every parsed key also gets a "__raw__<key>" entry holding the value as
    authored: the OKLCH form carries chroma/hue that is awkward to recover from
    the hex round-trip, and deepen() needs it.
    """
    path = os.path.join(KITTY_DIR, "themes", f"theme-{mode}.conf")
    if not os.path.exists(path):
        sys.exit(f"{who}: missing kitty theme: {path}")
    colors = {}
    for line in open(path, encoding="utf-8"):
        line = line.split("#!")[0]
        m = re.match(r"^\s*([a-z_0-9]+)\s+(.+?)\s*$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2)
        # skip comment lines, but keep bare hex values
        if val.lstrip().startswith("#") and not re.fullmatch(r"#[0-9a-fA-F]{6}", val.strip()):
            continue
        hexval = parse_color(val)
        if hexval:
            colors[key] = hexval
            colors["__raw__" + key] = val.strip()
    return colors
