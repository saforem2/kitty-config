# kitty-config

My [kitty](https://sw.kovidgoyal.net/kitty/) terminal emulator configuration.

All files in `~/.config/kitty/` are symlinked back to this repo.

## Structure

```
kitty.conf              # Main config — includes the files below
├── keys.conf           # Keybindings (kitty_mod = alt+shift)
├── mouse.conf          # Mouse bindings
├── os.conf             # macOS-specific settings
└── theme.conf -> themes/theme-light.conf
```

| File | Purpose |
|------|---------|
| `kitty.conf` | Main config: fonts, scrollback, tab bar, window layout, bell, includes |
| `keys.conf` | All keyboard bindings |
| `mouse.conf` | Mouse bindings and click handlers |
| `mouse-actions.conf` | Mouse action overrides |
| `os.conf` | macOS-specific settings |
| `font.conf` | Font families and size |
| `font-nerd-symbols.conf` | Nerd Font symbol map overrides |
| `window.conf` | Window padding, borders, placement |
| `diff.conf` | Diff kitten config |
| `grab.conf` | Grab kitten config |
| `open-actions.conf` | Rules for opening files by type |
| `launch-actions.conf` | Rules for launching files by type |
| `quick-access-terminal.conf` | Quake-style dropdown terminal |
| `tab_bar.py` | Custom tab bar (cwd display, catppuccin separators) |
| `zoom_toggle.py` | Toggle window zoom kitten |
| `sync-theme` | Script to sync dark/light theme with OS |
| `themes/` | Theme definitions (dark + light) |

## Kittens

| Kitten | Binding | Description |
|--------|---------|-------------|
| [`kitty_grab`](kitty_grab/) | `alt+shift+a`, `alt+shift+space` | Keyboard-driven text selection |
| [`kitty_search`](kitty_search/) | `cmd+/`, `alt+shift+s` | Search terminal scrollback |
| [`kitty_config`](kitty_config/) | `shift+cmd+,`, `alt+shift+'` | Interactive config viewer |

## Cheatsheet

The keybinding cheatsheet is a separate package: [`kitty-cheatsheet`](https://github.com/saforem2/kitty-cheatsheet)

```bash
uvx kitty-cheatsheet
```

Bound to `alt+shift+m` in `keys.conf`.

## Setup

Clone and symlink:

```bash
git clone https://github.com/saforem2/kitty-config ~/projects/saforem2/kitty-config

# Symlink everything into ~/.config/kitty/
for f in kitty.conf keys.conf mouse.conf mouse-actions.conf os.conf window.conf \
         font.conf font-nerd-symbols.conf diff.conf grab.conf \
         open-actions.conf launch-actions.conf quick-access-terminal.conf \
         tab_bar.py zoom_toggle.py keymap.py sync-theme; do
    ln -sf ~/projects/saforem2/kitty-config/$f ~/.config/kitty/$f
done

# Symlink kitten directories
for d in kitty_grab kitty_search kitty_config; do
    ln -sf ~/projects/saforem2/kitty-config/$d ~/.config/kitty/$d
done

# Symlink themes
ln -sf ~/projects/saforem2/kitty-config/themes/theme-dark.conf ~/.config/kitty/themes/theme-dark.conf
ln -sf ~/projects/saforem2/kitty-config/themes/theme-light.conf ~/.config/kitty/themes/theme-light.conf
```

Reload with `ctrl+shift+f5`.
