"""Self-check for agent_state glyph mapping and frame cycling.

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
    def test_working_is_orange_spinner_and_cycles(self):
        g0 = agent_state.glyph_for("working", 0)
        g1 = agent_state.glyph_for("working", 1)
        self.assertIn(agent_state.FRAMES[0], g0)
        self.assertIn(agent_state.FRAMES[1], g1)
        self.assertNotEqual(g0, g1)
        self.assertIn("38;2;217;119;87", g0)  # orange
        self.assertTrue(g0.endswith("\033[0m"))

    def test_frame_wraps(self):
        n = len(agent_state.FRAMES)
        self.assertEqual(
            agent_state.glyph_for("working", 0),
            agent_state.glyph_for("working", n),
        )

    def test_done_blocked_idle_unknown_static_no_emoji(self):
        done = agent_state.glyph_for("done", 0)
        blocked = agent_state.glyph_for("blocked", 0)
        self.assertIn("✓", done)
        self.assertIn("166;218;149", done)      # green
        self.assertIn("■", blocked)
        self.assertIn("237;135;150", blocked)    # red
        self.assertIsNotNone(agent_state.glyph_for("idle", 0))
        self.assertIsNotNone(agent_state.glyph_for("unknown", 0))
        # no emoji codepoints in any static glyph
        for status in ("done", "blocked", "idle", "unknown"):
            for ch in agent_state.glyph_for(status, 0):
                self.assertLess(ord(ch), 0x1F000, f"emoji in {status}: {ch!r}")

    def test_unmapped_status_clears(self):
        self.assertIsNone(agent_state.glyph_for("nonsense", 0))


if __name__ == "__main__":
    unittest.main()
