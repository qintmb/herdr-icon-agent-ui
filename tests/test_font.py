#!/usr/bin/env python3
"""Font structure and reproducibility tests (needs fontTools)."""
import unittest
from pathlib import Path

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
FONT = ROOT / "dist" / "HerdrAgentIconsMax-Regular.ttf"


class TestFontStructure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font = TTFont(FONT)

    def test_metrics_match_jetbrains_mono(self):
        hhea = self.font["hhea"]
        os2 = self.font["OS/2"]
        self.assertEqual(hhea.ascent, 1020)
        self.assertEqual(hhea.descent, -300)
        self.assertEqual(os2.usWinAscent, 1020)
        self.assertEqual(os2.usWinDescent, 300)

    def test_advance_width_fixed(self):
        hmtx = self.font["hmtx"]
        for name in self.font.getGlyphOrder():
            if name != ".notdef":
                self.assertEqual(hmtx[name][0], 600)

    def test_glyph_bounds_fill_cell(self):
        from fontTools.pens.boundsPen import BoundsPen

        glyf = self.font["glyf"]
        for name in self.font.getGlyphOrder():
            if name == ".notdef":
                continue
            pen = BoundsPen(glyf)
            glyf[name].draw(pen, glyf)
            bounds = pen.bounds
            self.assertIsNotNone(bounds, f"{name} has no outline")
            width = bounds[2] - bounds[0]
            height = bounds[3] - bounds[1]
            self.assertGreater(height, 800, f"{name} too short: {height}")
            self.assertGreater(width, 400, f"{name} too narrow: {width}")


if __name__ == "__main__":
    unittest.main()
