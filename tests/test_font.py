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
            # Uniform scale: one axis hits its limit, so the mark stays big
            # without being stretched.
            self.assertGreater(max(width, height), 500, f"{name} too small")
            self.assertLessEqual(width, 568, f"{name} too wide: {width}")
            self.assertLessEqual(height, 768, f"{name} too tall: {height}")

    def test_aspect_ratio_matches_source_svg(self):
        from fontTools.pens.boundsPen import BoundsPen
        from fontTools.svgLib.path import SVGPath

        glyf = self.font["glyf"]
        for name in self.font.getGlyphOrder():
            if name == ".notdef":
                continue
            pen = BoundsPen(glyf)
            glyf[name].draw(pen, glyf)
            width = pen.bounds[2] - pen.bounds[0]
            height = pen.bounds[3] - pen.bounds[1]
            svg_pen = BoundsPen(None)
            SVGPath(str(ROOT / "assets" / "svg" / f"{name}.svg")).draw(svg_pen)
            sx0, sy0, sx1, sy1 = svg_pen.bounds
            expected = (sx1 - sx0) / (sy1 - sy0)
            self.assertAlmostEqual(
                width / height, expected, delta=0.02,
                msg=f"{name} distorted: {width / height:.3f} vs {expected:.3f}",
            )


if __name__ == "__main__":
    unittest.main()
