#!/usr/bin/env python3
"""Runtime tests for the agent icon plugin (stdlib only)."""
import unittest
from unittest.mock import patch

from agent_icons import (
    PUA_LOGOS,
    TEXT_LOGOS,
    event_pane,
    logo_for,
    startup_targets,
)


class TestLogoFor(unittest.TestCase):
    def test_supported_agent_returns_glyph(self):
        self.assertEqual(logo_for("claude", "font"), PUA_LOGOS["claude"])
        self.assertEqual(logo_for("pi", "font"), PUA_LOGOS["pi"])
        self.assertEqual(logo_for("hermes", "font"), PUA_LOGOS["hermes"])

    def test_text_variant_returns_fallback(self):
        self.assertEqual(logo_for("claude", "text"), TEXT_LOGOS["claude"])
        self.assertEqual(logo_for("pi", "text"), TEXT_LOGOS["pi"])

    def test_unsupported_agent_returns_none(self):
        self.assertIsNone(logo_for("unknown-agent", "font"))

    def test_none_variant_clears(self):
        self.assertIsNone(logo_for("claude", "none"))

    def test_auto_uses_font_when_available(self):
        with patch("agent_icons.font_available", return_value=True):
            self.assertEqual(logo_for("claude", "auto"), PUA_LOGOS["claude"])

    def test_auto_falls_back_to_text(self):
        with patch("agent_icons.font_available", return_value=False):
            self.assertEqual(logo_for("claude", "auto"), TEXT_LOGOS["claude"])

    def test_all_codepoints_in_pua_range(self):
        for agent, glyph in PUA_LOGOS.items():
            self.assertIn(agent, TEXT_LOGOS, f"{agent} missing text fallback")
            self.assertGreaterEqual(ord(glyph), 0xE000)
            self.assertLessEqual(ord(glyph), 0xF8FF)


class TestEventPane(unittest.TestCase):
    def test_extracts_pane_id_nested(self):
        raw = '{"pane": {"pane_id": "wF:p1"}, "type": "pane_created"}'
        self.assertEqual(event_pane(raw), "wF:p1")

    def test_missing_pane_id_returns_none(self):
        self.assertIsNone(event_pane('{"type": "unknown"}'))


class TestStartupTargets(unittest.TestCase):
    def test_missing_agent_key_handled(self):
        response = {
            "result": {
                "panes": [
                    {"pane_id": "wF:p1", "agent": "claude"},
                    {"pane_id": "wF:p2"},  # no agent key
                ]
            }
        }
        with patch("agent_icons.run_herdr", return_value=response):
            targets = startup_targets("herdr")
        self.assertEqual(targets, [("wF:p1", "claude"), ("wF:p2", None)])


if __name__ == "__main__":
    unittest.main()
