#!/usr/bin/env python3
"""Build the Herdr agent icon font from local SVG marks.

Glyph metrics match JetBrains Mono (UPM 1000, advance 600, ascent 1020,
descent -300) so icons align with terminal text in the Herdr sidebar.
Each mark is scaled uniformly to fit a 560x760 cell, so the source
aspect ratio is preserved -- a non-uniform stretch flattens wide marks
such as mastracode and claude.
"""
from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path
from xml.etree import ElementTree

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.svgLib.path import SVGPath

ROOT = Path(__file__).resolve().parent.parent
UPM = 1000
ADVANCE = 600
ASCENT = 1020
DESCENT = -300
FONT_TIMESTAMP = 2082844800  # 1970-01-01 in OpenType's 1904 epoch.

# Uniform-scale fit box. Aspect ratio is preserved; the smaller of the two
# ratios wins so the mark never exceeds the cell in either axis.
MAX_WIDTH = 560
MAX_HEIGHT = 760
# Vertical centre = middle of JetBrains Mono cap height (730), so icons sit
# on the same optical line as adjacent text.
CENTER_Y = 365


def svg_glyph(path: Path):
    root = ElementTree.parse(path).getroot()
    # SVGPath re-reads the file, so unsupported elements cannot be stripped
    # in-memory -- reject them instead. Run tools/normalize_svg.py to clean
    # a downloaded mark. This also catches HTML saved under an .svg name.
    for element in root.iter():
        tag = element.tag.rsplit("}", 1)[-1]
        if tag not in {"svg", "path"}:
            raise ValueError(f"{path}: unexpected element {tag!r}")
    svg_path = SVGPath(str(path))
    bounds_pen = BoundsPen(None)
    svg_path.draw(bounds_pen)
    if bounds_pen.bounds is None:
        raise ValueError(f"{path}: no outlines")
    x_min, y_min, x_max, y_max = bounds_pen.bounds
    dx = x_max - x_min
    dy = y_max - y_min
    scale = min(MAX_WIDTH / dx, MAX_HEIGHT / dy)
    x_offset = (ADVANCE - dx * scale) / 2 - x_min * scale
    y_offset = CENTER_Y + dy * scale / 2 + y_min * scale
    glyph_pen = TTGlyphPen(None)
    quadratic_pen = Cu2QuPen(glyph_pen, max_err=1.0, reverse_direction=True)
    transform_pen = TransformPen(
        quadratic_pen, (scale, 0, 0, -scale, x_offset, y_offset)
    )
    svg_path.draw(transform_pen)
    return glyph_pen.glyph()


def build(output: Path) -> None:
    with (ROOT / "font" / "codepoints.toml").open("rb") as config_file:
        config = tomllib.load(config_file)
    names = list(config["glyphs"].keys())
    codepoints = {int(value, 16): name for name, value in config["glyphs"].items()}
    if len(codepoints) != len(names):
        raise ValueError("duplicate codepoint")
    empty_pen = TTGlyphPen(None)
    glyphs: dict[str, object] = {".notdef": empty_pen.glyph()}
    for name in names:
        svg_path = ROOT / "assets" / "svg" / f"{name}.svg"
        if not svg_path.exists():
            print(f"WARN: missing {svg_path}, skipping", file=sys.stderr)
            continue
        try:
            glyphs[name] = svg_glyph(svg_path)
            print(f"OK {name}")
        except Exception as error:
            print(f"ERR {name}: {error}", file=sys.stderr)
    family = config.get("family", "Herdr Agent Icons Max")
    version = config.get("version", "1.0.0")
    builder = FontBuilder(UPM, isTTF=True)
    builder.setupGlyphOrder([".notdef", *names])
    builder.setupCharacterMap(codepoints)
    builder.setupGlyf(glyphs)
    builder.setupHorizontalMetrics({name: (ADVANCE, 0) for name in glyphs})
    builder.setupHorizontalHeader(ascent=ASCENT, descent=DESCENT, lineGap=0)
    builder.setupNameTable(
        {
            "copyright": "See THIRD_PARTY_NOTICES.md; marks belong to their respective owners.",
            "familyName": family,
            "styleName": "Regular",
            "uniqueFontIdentifier": f"qintmb.herdr-icon-agent-ui:{version}",
            "fullName": f"{family} Regular",
            "version": f"Version {version}",
            "psName": family.replace(" ", "-") + "-Regular",
            "licenseDescription": "See bundled THIRD_PARTY_NOTICES.md.",
        }
    )
    builder.setupOS2(
        sTypoAscender=ASCENT,
        sTypoDescender=DESCENT,
        sTypoLineGap=0,
        usWinAscent=ASCENT,
        usWinDescent=-DESCENT,
        sxHeight=500,
        sCapHeight=700,
        xAvgCharWidth=ADVANCE,
        achVendID="HRDR",
        fsType=0,
    )
    builder.setupPost(isFixedPitch=1)
    builder.setupMaxp()
    builder.font["head"].created = FONT_TIMESTAMP
    builder.font["head"].modified = FONT_TIMESTAMP
    output.parent.mkdir(parents=True, exist_ok=True)
    builder.save(output)
    print(f"Built: {output}")


def selfcheck(path: Path) -> None:
    """Assert every glyph keeps its SVG aspect ratio and fits the cell."""
    from fontTools.ttLib import TTFont

    font = TTFont(path)
    glyf = font["glyf"]
    checked = 0
    for name in font.getGlyphOrder():
        if name == ".notdef":
            continue
        glyph = glyf[name]
        glyph.recalcBounds(glyf)
        width = glyph.xMax - glyph.xMin
        height = glyph.yMax - glyph.yMin
        bounds_pen = BoundsPen(None)
        SVGPath(str(ROOT / "assets" / "svg" / f"{name}.svg")).draw(bounds_pen)
        sx0, sy0, sx1, sy1 = bounds_pen.bounds
        expected = (sx1 - sx0) / (sy1 - sy0)
        assert abs(width / height - expected) < 0.02, (
            f"{name}: aspect {width / height:.3f} != svg {expected:.3f}"
        )
        assert width <= MAX_WIDTH + 8 and height <= MAX_HEIGHT + 8, (
            f"{name}: {width}x{height} overflows {MAX_WIDTH}x{MAX_HEIGHT}"
        )
        checked += 1
    print(f"selfcheck OK ({checked} glyphs)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "dist" / "HerdrAgentIconsMax-Regular.ttf",
    )
    args = parser.parse_args()
    build(args.output)
    selfcheck(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
