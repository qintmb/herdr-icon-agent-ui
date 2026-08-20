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
    def test_working_is_spinner_and_cycles(self):
        g0 = agent_state.glyph_for("working", 0)
        g1 = agent_state.glyph_for("working", 1)
        self.assertEqual(g0, agent_state.FRAMES[0])
        self.assertEqual(g1, agent_state.FRAMES[1])
        self.assertNotEqual(g0, g1)

    def test_frame_wraps(self):
        n = len(agent_state.FRAMES)
        self.assertEqual(
            agent_state.glyph_for("working", 0),
            agent_state.glyph_for("working", n),
        )

    def test_static_states_and_no_emoji_no_ansi(self):
        self.assertEqual(agent_state.glyph_for("done", 0), "✓")
        self.assertEqual(agent_state.glyph_for("blocked", 0), "■")
        self.assertEqual(agent_state.glyph_for("idle", 0), "◦")
        self.assertEqual(agent_state.glyph_for("unknown", 0), "?")
        # no emoji, no ANSI escape bytes in any glyph
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
        # tokens are unique and match the documented names
        self.assertEqual(len(set(agent_state.ALL_TOKENS)), len(agent_state.TOKENS))
        self.assertIn("state_working", agent_state.ALL_TOKENS)


if __name__ == "__main__":
    unittest.main()
