# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2025-08-18

### Added
- Initial release: 12 agent icons (claude, codex, opencode, omp, cline, mastracode, kimi, kilo, maki, pi, hermes, cursor)
- Font `Herdr Agent Icons Max` with metrics matching JetBrains Mono (UPM 1000, advance 600, ascent 1020, descent -300)
- Non-uniform glyph scale (580×1040) so icons align with terminal text height
- Variant system: auto, font, text, none
- Runtime plugin `agent_icons.py` using stdlib only (Python ≥ 3.11)
- Build script `tools/build_font.py` with deterministic output
- Preview tool `tools/preview.py` for selecting variant
- Sidebar color examples in README
- Comprehensive documentation