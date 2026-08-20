"""Self-check for agent_state glyph mapping, frame cycling, and line compose.

Run: python3 -m unittest tests.test_agent_state
"""
import importlib.util
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "agent_state", Path(__file__).resolve().parent.parent / "agent_state.py"
)
agent_state = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(agent_state)


class GlyphMapping(unittest.TestCase):
    def test_working_is_spinner_and_cycles(self):
        self.assertEqual(agent_state.glyph_for("working", 0), agent_state.FRAMES[0])
        self.assertEqual(agent_state.glyph_for("working", 1), agent_state.FRAMES[1])
        self.assertNotEqual(
            agent_state.glyph_for("working", 0), agent_state.glyph_for("working", 1)
        )

    def test_frame_wraps(self):
        n = len(agent_state.FRAMES)
        self.assertEqual(
            agent_state.glyph_for("working", 0), agent_state.glyph_for("working", n)
        )

    def test_static_states_and_no_emoji_no_ansi(self):
        self.assertEqual(agent_state.glyph_for("done", 0), "✓")
        self.assertEqual(agent_state.glyph_for("blocked", 0), "⬤")
        self.assertEqual(agent_state.glyph_for("idle", 0), "⬤")
        self.assertEqual(agent_state.glyph_for("unknown", 0), "⬤")
        for status in ("working", "done", "blocked", "idle", "unknown"):
            g = agent_state.glyph_for(status, 0)
            self.assertNotIn("\033", g, f"ANSI in {status}")
            for ch in g:
                self.assertLess(ord(ch), 0x1F000, f"emoji in {status}: {ch!r}")

    def test_unmapped_status_clears(self):
        self.assertIsNone(agent_state.glyph_for("nonsense", 0))

    def test_one_token_per_state(self):
        self.assertEqual(
            set(agent_state.TOKENS),
            {"working", "done", "blocked", "idle", "unknown"},
        )
        self.assertEqual(len(set(agent_state.ALL_TOKENS)), len(agent_state.TOKENS))
        self.assertIn("state_working", agent_state.ALL_TOKENS)


class ComposeLine(unittest.TestCase):
    def test_line_has_no_separator_dot(self):
        line = agent_state.compose_line("claude", "§", "working", 0)
        self.assertNotIn("·", line)
        # order: glyph, logo, name — single spaces
        self.assertEqual(line, f"{agent_state.FRAMES[0]} § claude")

    def test_line_without_logo(self):
        self.assertEqual(
            agent_state.compose_line("pi", "", "idle", 0), "⬤ pi"
        )

    def test_line_without_name(self):
        self.assertEqual(agent_state.compose_line("", "§", "done", 0), "✓ §")

    def test_unmapped_status_is_none(self):
        self.assertIsNone(agent_state.compose_line("x", "§", "nonsense", 0))


if __name__ == "__main__":
    unittest.main()
