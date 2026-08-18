#!/usr/bin/env python3
"""Build the Herdr agent icon font from local SVG marks.

Glyph metrics match JetBrains Mono (UPM 1000, advance 600, ascent 1020,
descent -300) so icons align with terminal text in the Herdr sidebar.
A non-uniform scale (580 wide x 1040 tall) makes icons roughly cap
height even when the source mark is squarer or wider than tall.
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

# Non-uniform scale: width fit, height stretch to match cap height.
GLYPH_WIDTH = 580
GLYPH_HEIGHT = 1040


def svg_glyph(path: Path):
    root = ElementTree.parse(path).getroot()
    ns = {"svg": "http://www.w3.org/2000/svg"}
    # Strip container elements that wrap paths.
    for tag in ("title", "desc", "metadata", "defs", "g"):
        for element in root.findall(f"svg:{tag}", ns):
            root.remove(element)
    # Remove any remaining non-path children.
    for element in list(root):
        tag = element.tag.rsplit("}", 1)[-1]
        if tag not in {"svg", "path"}:
            root.remove(element)
    svg_path = SVGPath(str(path))
    bounds_pen = BoundsPen(None)
    svg_path.draw(bounds_pen)
    if bounds_pen.bounds is None:
        raise ValueError(f"{path}: no outlines")
    x_min, y_min, x_max, y_max = bounds_pen.bounds
    dx = x_max - x_min
    dy = y_max - y_min
    scale_x = GLYPH_WIDTH / dx
    scale_y = GLYPH_HEIGHT / dy
    x_offset = (ADVANCE - dx * scale_x) / 2 - x_min * scale_x
    # Vertical center on JetBrains Mono midpoint (ascent 1020 / descent -300).
    y_offset = 360 + dy * scale_y / 2 + y_min * scale_y
    glyph_pen = TTGlyphPen(None)
    quadratic_pen = Cu2QuPen(glyph_pen, max_err=1.0, reverse_direction=True)
    transform_pen = TransformPen(
        quadratic_pen, (scale_x, 0, 0, -scale_y, x_offset, y_offset)
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "dist" / "HerdrAgentIconsMax-Regular.ttf",
    )
    args = parser.parse_args()
    build(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
