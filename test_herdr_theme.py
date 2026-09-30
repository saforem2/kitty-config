from __future__ import annotations

import importlib.machinery
import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("herdr-theme")


def load_module():
    loader = importlib.machinery.SourceFileLoader("herdr_theme", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    if spec is None:
        raise RuntimeError(f"cannot load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class AgentSidebarThemeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_agent_sidebar_custom_tokens_follow_active_palette(self):
        text = """before
[ui.sidebar.agents]
rows = [
  [{ token = "$cache_high", fg = "#a6e3a1" }, { token = "$cache_mid", fg = "#f9e2af" }, { token = "$cache_low", fg = "#f38ba8" }],
  [{ token = "$rsact_summary", fg = "#89b4fa", rules = [{ contains = "subagent", fg = "#f9e2af" }, { contains = "bg", fg = "#89b4fa" }, { starts_with = "loop", fg = "#cba6f7" }] }],
]

[ui.sidebar.spaces]
rows = [[{ token = "$ai_usage", fg = "#a6e3a1" }]]
"""
        palette = {
            "green": "#1e8759",
            "yellow": "#976e4a",
            "red": "#986873",
            "blue": "#327abc",
            "mauve": "#8260cc",
        }

        updated = self.module.configure_agent_sidebar_colors(text, palette)

        agent_section = updated.split("[ui.sidebar.spaces]", 1)[0]
        self.assertIn('fg = "#1e8759"', agent_section)
        self.assertIn('fg = "#976e4a"', agent_section)
        self.assertIn('fg = "#986873"', agent_section)
        self.assertIn('fg = "#327abc"', agent_section)
        self.assertIn('fg = "#8260cc"', agent_section)
        self.assertNotIn("#a6e3a1", agent_section)
        self.assertIn('fg = "#a6e3a1"', updated.split("[ui.sidebar.spaces]", 1)[1])

    def test_spaces_sidebar_custom_tokens_follow_active_palette(self):
        text = """before
[ui.sidebar.spaces]
rows = [
  ["state_icon", "workspace"],
  ["branch", "git_status"],
  [{ token = "$rsact_summary", fg = "#89b4fa", rules = [{ contains = "subagent", fg = "#f9e2af" }, { contains = "bg", fg = "#89b4fa" }, { contains = "monitor", fg = "#89b4fa" }, { starts_with = "loop", fg = "#cba6f7" }, { starts_with = "next", fg = "#cba6f7" }] }],
]
"""
        palette = {
            "subtext0": "#5f6179",
            "green": "#1e8759",
            "yellow": "#976e4a",
            "blue": "#327abc",
            "mauve": "#8260cc",
        }

        updated = self.module.configure_spaces_sidebar_colors(text, palette)

        self.assertIn('{ token = "branch", fg = "#5f6179" }', updated)
        self.assertIn('{ token = "git_status", fg = "#1e8759" }', updated)
        self.assertIn('token = "$rsact_summary", fg = "#327abc"', updated)
        self.assertIn('contains = "subagent", fg = "#976e4a"', updated)
        self.assertIn('starts_with = "loop", fg = "#8260cc"', updated)
        self.assertNotIn("#89b4fa", updated)
        self.assertEqual(
            self.module.configure_spaces_sidebar_colors(updated, palette), updated
        )

    def test_rewrite_is_idempotent_and_switches_modes(self):
        text = """[ui.sidebar.agents]
rows = [[{ token = "$cache_high", fg = "#a6e3a1" }, { token = "$cache_mid", fg = "#f9e2af" }, { token = "$cache_low", fg = "#f38ba8" }]]
"""
        light = {
            "green": "#1e8759",
            "yellow": "#976e4a",
            "red": "#986873",
            "blue": "#327abc",
            "mauve": "#8260cc",
        }
        dark = {
            "green": "#43bf58",
            "yellow": "#ffff00",
            "red": "#fa2375",
            "blue": "#00b3e3",
            "mauve": "#ff00ff",
        }

        light_text = self.module.configure_agent_sidebar_colors(text, light)
        self.assertEqual(
            self.module.configure_agent_sidebar_colors(light_text, light), light_text
        )
        dark_text = self.module.configure_agent_sidebar_colors(light_text, dark)
        self.assertIn('fg = "#43bf58"', dark_text)
        self.assertIn('fg = "#ffff00"', dark_text)
        self.assertIn('fg = "#fa2375"', dark_text)

    def test_apply_writes_sidebar_only_change_when_theme_block_is_unchanged(self):
        palettes = {mode: self.module.build_palette(mode) for mode in ("light", "dark")}
        config = (
            """[theme]
name = "terminal"
auto_switch = true
light_name = "terminal"
dark_name = "terminal"

[ui.sidebar.agents]
rows = [[{ token = "$cache_high", fg = "#a6e3a1" }]]

"""
            + self.module.render_block(palettes)
            + "\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(config)
            self.assertTrue(self.module.apply(str(path), palettes, "light", False))
            self.assertIn('fg = "#1e8759"', path.read_text())


if __name__ == "__main__":
    unittest.main()
