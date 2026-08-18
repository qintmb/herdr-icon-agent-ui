#!/usr/bin/env python3
"""Normalize SVGs: strip title, non-path elements, styling attributes."""
import xml.etree.ElementTree as ET
from pathlib import Path
import sys

SVG_DIR = Path(__file__).resolve().parent.parent / "assets" / "svg"
KEEP_ATTRS = set()  # keep nothing except 'd' on path elements

for svg_file in sorted(SVG_DIR.glob("*.svg")):
    try:
        tree = ET.parse(svg_file)
    except ET.ParseError:
        print(f"SKIP {svg_file.name}: invalid XML", file=sys.stderr)
        continue
    root = tree.getroot()
    ns = {"svg": "http://www.w3.org/2000/svg"}

    # Remove title/desc/metadata elements
    for tag in ["title", "desc", "metadata"]:
        for elem in root.findall(f"svg:{tag}", ns):
            root.remove(elem)

    # For each path, strip all attrs except 'd' (and fill-rule if present)
    for path_el in root.iter():
        tag = path_el.tag.rsplit("}", 1)[-1]
        if tag == "path":
            d = path_el.get("d", "")
            fill_rule = path_el.get("fill-rule") or path_el.get("clip-rule")
            for attr in list(path_el.attrib):
                if attr not in ("d", "fill-rule", "clip-rule"):
                    del path_el.attrib[attr]
            # strip xmlns from root and width/height/style on root
        elif tag != "path" and tag != "svg":
            # remove any non-path, non-root children
            for parent in root:
                if parent is path_el:
                    try:
                        root.remove(path_el)
                    except ValueError:
                        pass

    # strip width/height/style/title from root
    for attr in ["width", "height", "style", "fill", "xmlns:xlink"]:
        if attr in root.attrib:
            del root.attrib[attr]
    # Remove title element at root level
    for child in list(root):
        child_tag = child.tag.rsplit("}", 1)[-1]
        if child_tag == "title":
            root.remove(child)

    # Rewrite clean: only path children
    # Collect path data
    paths = []
    for path_el in root.iter():
        d = path_el.get("d")
        if d and path_el.tag.rsplit("}", 1)[-1] == "path":
            paths.append(d)

    # Build new clean SVG
    new_root = ET.Element("svg", {"viewBox": root.get("viewBox", "0 0 24 24")})
    for d in paths:
        path_el = ET.SubElement(new_root, "path", d=d)

    ET.indent(new_root, space="  ")
    new_tree = ET.ElementTree(new_root)
    new_tree.write(svg_file, xml_declaration=False, encoding="unicode")
    print(f"OK {svg_file.name}")

print("done")
