# Changelog

All notable changes to this project will be documented in this file.

## [1.2.0] - 2026-08-20

### Added
- `agent_state.py` — animated lifecycle-state glyph via the `$agent_state` token: orange braille spinner while `working`, green `✓` on `done`, red `■` on `blocked`, dim `◦`/`?` for `idle`/`unknown`. Coloured with inline ANSI, no emoji.
- Background animator (150 ms frame cadence) spawned on demand and self-terminating ~1.8 s after no agent is working, so it costs nothing on an idle machine. Single-writer PID lock; `state-stop` action / `--stop` to halt.
- Manifest: `pane.agent_status_changed` event, extra `[[startup]]`/`[[events]]` pass, and `state-start`/`state-stop` actions.
- `tests/test_agent_state.py` — glyph mapping, frame cycling, no-emoji assertions.
- README: recommended `rows_by_agent` layout with `$agent_state` + `$harness_logo`, and a lifecycle-state reference table.

## [1.1.0] - 2026-08-18

### Added
- 5 new agent icons: `copilot` (`U+E1AC`), `deepseek` (`U+E1AD`), `gemini` (`U+E1AE`), `gpt` (`U+E1AF`), `qwen` (`U+E1B0`) — 17 glyphs total. Marks from [lobehub/lobe-icons](https://github.com/lobehub/lobe-icons) (MIT).
- `tools/normalize_svg.py` — strips `<title>`, `<desc>`, fills, and wrapper elements from a downloaded mark.
- `build_font.py` now rejects SVGs containing anything other than `<svg>`/`<path>` instead of silently dropping outlines, and self-checks every built glyph against its source aspect ratio.
- `tests/test_font.py`: `test_aspect_ratio_matches_source_svg`.

### Fixed
- Glyphs no longer distorted: replaced the non-uniform `580×1040` stretch with a uniform scale into a `560×760` cell, so each mark keeps its source aspect ratio. Wide marks (`mastracode`, `claude`) were flattened before.
- Vertical centring moved to `CENTER_Y = 365` (midpoint of JetBrains Mono cap height 730) so icons sit on the same optical line as adjacent text.

### Changed
- All source SVGs re-normalized to bare `<svg viewBox>` + `<path d>`. `claude.svg` replaced with the full Anthropic starburst (the previous file was a 24×15 crop that read as a flat bar).
- Ghostty `font-codepoint-map` range widened to `U+E1A0-U+E1B0`.

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