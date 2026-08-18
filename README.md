# Herdr Icon Agent UI

A Herdr v1 plugin that renders large, vertically-aligned monochrome icons for coding agents in the Herdr sidebar. Icons are rendered via a custom font (`Herdr Agent Icons Max`) with non-uniform glyph scaling that matches terminal cap-height — so icons sit flush with agent names, tabs, and workspace labels instead of appearing as tiny squares.

| | | | |
|---|---|---|---|
| ![](assets/svg/claude.svg) | ![](assets/svg/codex.svg) | ![](assets/svg/opencode.svg) | ![](assets/svg/omp.svg) |
| ![](assets/svg/cline.svg) | ![](assets/svg/mastracode.svg) | ![](assets/svg/kimi.svg) | ![](assets/svg/kilo.svg) |
| ![](assets/svg/maki.svg) | ![](assets/svg/pi.svg) | ![](assets/svg/hermes.svg) | ![](assets/svg/cursor.svg) |

## Supported agents

| Harness | Codepoint | Text fallback |
| --- | --- | --- |
| Claude | `U+E1A0` | `§` |
| Codex / OpenAI | `U+E1A1` | `Λ` |
| OpenCode | `U+E1A2` | `◇` |
| OMP | `U+E1A3` | `Π` |
| Cline | `U+E1A4` | `∇` |
| MastraCode | `U+E1A5` | `∑` |
| Kimi Code CLI | `U+E1A6` | `✨` |
| Kilo Code CLI | `U+E1A7` | `♟` |
| Maki | `U+E1A8` | `✳` |
| Pi (Buffy) | `U+E1A9` | `π` |
| Hermes | `U+E1AA` | `☪` |
| Cursor | `U+E1AB` | `◆` |

The plugin only writes a display token `$harness_logo` via `pane report-metadata`. It **never** changes `display_agent`, reports state labels, or touches agent lifecycle — Herdr's native colored lifecycle icon (`state_icon`) continues to work.

Herdr-recognized harnesses without a safely reusable mark are left unmarked (token is cleared) rather than guessing at a logo.

---

## 1. Requirements

- **Herdr ≥ 0.8.0** (plugin v1 API: `report-metadata`, `$...` token sidebar)
- **Python ≥ 3.11** on the machine running Herdr — `tomllib` shipped with 3.11. The manifest invokes bare `python3` with no third-party dependencies at runtime.
- **Font `Herdr Agent Icons Max`** installed on the system for the `font` variant (the default `auto` selects it when Fontconfig finds it).
- Linux: Fontconfig (`fc-match`) for automatic detection. macOS / Windows: set `variant = "font"` explicitly after installing the font.
- Ghostty (or another terminal supporting `font-codepoint-map`) to display PUA codepoints.

## 2. Install to Herdr

### From GitHub

```sh
herdr plugin install qintmb/herdr-icon-agent-ui
```

### Or link from a local directory

```sh
git clone https://github.com/qintmb/herdr-icon-agent-ui.git
herdr plugin link /path/to/herdr-icon-agent-ui
```

Verify:

```sh
herdr plugin list
herdr plugin config-dir qintmb.herdr-icon-agent-ui
```

### 2.1 Install the font (required for icon graphics)

Copy the font to the system font directory:

```sh
# macOS
mkdir -p ~/Library/Fonts
cp dist/HerdrAgentIconsMax-Regular.ttf ~/Library/Fonts/

# Linux
mkdir -p ~/.local/share/fonts
cp dist/HerdrAgentIconsMax-Regular.ttf ~/.local/share/fonts/
fc-cache -f ~/.local/share/fonts
fc-match --format '%{family}\n' 'Herdr Agent Icons Max'
```

### 2.2 Ghostty configuration

Add the following to `~/.config/ghostty/config` (or `~/Library/Application Support/com.mitchellh.ghostty/config` on macOS). Keep your existing primary `font-family`, then append the icon family as a fallback:

```ini
font-family = "JetBrains Mono"
font-family = "Herdr Agent Icons Max"
font-codepoint-map = U+E1A0-U+E1AB="Herdr Agent Icons Max"
```

> Replace `JetBrains Mono` with your actual primary family. Font changes only apply to new terminal surfaces — open a new window/tab after editing.

Verify:

```sh
ghostty +list-fonts | grep -F 'Herdr Agent Icons Max'
```

### 2.3 Herdr sidebar configuration

Add the `$harness_logo` token to the agent rows in `~/.config/herdr/config.toml`:

```toml
[ui.sidebar.agents]
rows = [
  ["state_icon", { token = "$harness_logo", bold = true }, "agent"],
  ["workspace", "tab"],
]
```

Then reload:

```sh
herdr server reload-config
herdr plugin action invoke refresh --plugin qintmb.herdr-icon-agent-ui
```

## 3. Initialize project

Reproduce the font and run local tests without Herdr:

```sh
# Create a venv with fontTools (for font build and font tests only)
python3 -m venv .venv-font
.venv-font/bin/pip install -r requirements-font.txt

# Rebuild the font deterministically
.venv-font/bin/python tools/build_font.py

# Runtime tests (no third-party dependencies)
python3 -m unittest discover -s tests -p 'test_*.py'

# Font structure and reproducibility tests
.venv-font/bin/python -m unittest tests.test_font
```

Repository structure:

```
herdr-icon-agent-ui/
├── herdr-plugin.toml        # Herdr plugin manifest
├── agent_icons.py           # Runtime plugin (token reporting)
├── assets/svg/              # SVG marks per harness
├── dist/                    # Prebuilt font
│   └── HerdrAgentIconsMax-Regular.ttf
├── font/
│   └── codepoints.toml      # Codepoint → agent mapping
├── tools/
│   ├── build_font.py        # Build font from SVG
│   └── preview.py           # Preview codepoints and fallbacks
├── tests/
│   ├── test_agent_icons.py  # Runtime tests
│   └── test_font.py         # Font structure tests
├── requirements-font.txt    # Build-time only
├── THIRD_PARTY_NOTICES.md   # Third-party mark attributions
├── CHANGELOG.md
├── LICENSE
└── README.md
```

## 4. Customization

### Icon variant

Write to the plugin config (`$(herdr plugin config-dir qintmb.herdr-icon-agent-ui)/config.toml`):

```toml
variant = "auto"   # use font when installed, otherwise text fallback (default)
# variant = "font" # force PUA glyphs (requires font installed)
# variant = "text" # force ASCII/Unicode fallback
# variant = "none" # clear the logo token entirely
```

Or via CLI:

```sh
python3 tools/preview.py --select font --config "$(herdr plugin config-dir qintmb.herdr-icon-agent-ui)/config.toml"
herdr plugin action invoke refresh --plugin qintmb.herdr-icon-agent-ui
```

### Colors per agent

Herdr sidebar supports `rows_by_agent` with fixed hex colors. Dark theme example:

```toml
[ui.sidebar.agents.rows_by_agent]
claude = [["state_icon", { token = "$harness_logo", fg = "#d97757" }, "agent"], ["workspace", "tab"]]
codex = [["state_icon", { token = "$harness_logo", fg = "#ffffff" }, "agent"], ["workspace", "tab"]]
opencode = [["state_icon", { token = "$harness_logo", fg = "#ffffff" }, "agent"], ["workspace", "tab"]]
omp = [["state_icon", { token = "$harness_logo", fg = "#f97316" }, "agent"], ["workspace", "tab"]]
pi = [["state_icon", { token = "$harness_logo", fg = "#ffffff" }, "agent"], ["workspace", "tab"]]
hermes = [["state_icon", { token = "$harness_logo", fg = "#ffffff" }, "agent"], ["workspace", "tab"]]
```

Colors are fixed hex values — Herdr 0.8.0 cannot auto-switch per-agent colors with the theme. Choose values with sufficient contrast, or omit `fg` for fully theme-safe styling.

### Glyph size and centering

Font metrics are set to match **JetBrains Mono** (UPM 1000, advance 600, ascent 1020, descent −300) with non-uniform scaling `580×1040` — icons fill cap-height of terminal text. To change, edit constants in `tools/build_font.py`:

```python
GLYPH_WIDTH = 580
GLYPH_HEIGHT = 1040
```

Rebuild the font, reinstall, and open a new terminal surface.

### Adding a new agent

1. Place an SVG at `assets/svg/<name>.svg`
2. Add a line to `font/codepoints.toml`
3. Add entries to `PUA_LOGOS` and `TEXT_LOGOS` in `agent_icons.py`
4. Rebuild the font, reinstall, refresh

## 5. Usage

The plugin runs automatically: once on Herdr startup (`[[startup]]`) and whenever an agent is detected on a pane (`pane.agent_detected`). The `$harness_logo` token is automatically attached to supported agent panes.

Manual commands:

```sh
# Reapply icons to all panes
herdr plugin action invoke refresh --plugin qintmb.herdr-icon-agent-ui

# Check attached token
herdr pane get <PANE_ID>

# Preview all codepoints and fallbacks (no ANSI)
python3 tools/preview.py
```

## 6. Update or remove

### Update

Plugin v1 has no `plugin update` — reinstall from GitHub to refresh:

```sh
herdr plugin install qintmb/herdr-icon-agent-ui --yes
```

Config and state remain in `~/.config/herdr/plugins/config/qintmb.herdr-icon-agent-ui/`.

To update the font: replace the TTF in the system font directory, then open a new terminal surface.

### Remove

```sh
herdr plugin uninstall qintmb.herdr-icon-agent-ui
```

Clean up the font (optional):

```sh
# macOS
rm ~/Library/Fonts/HerdrAgentIconsMax-Regular.ttf
# Linux
rm ~/.local/share/fonts/HerdrAgentIconsMax-Regular.ttf
fc-cache -f ~/.local/share/fonts
```

Remove the two Ghostty lines (`font-family = "Herdr Agent Icons Max"` and `font-codepoint-map`), then open a new terminal surface.

## 7. Security

- The plugin runs as the same user as Herdr and can call the full Herdr CLI — same trust model as any editor/agent extension. Only install from authors and repos you trust.
- The plugin **only** writes a display token `$harness_logo` to pane metadata. There are no network calls, no file reads outside the plugin directory, and no code execution from agents.
- The script uses stdlib Python at runtime (`tomllib` ≥ 3.11); `fontTools` is needed only to build the font, never to run the plugin.
- SVG marks are sourced from each product's official repository (see `THIRD_PARTY_NOTICES.md`). Marks belong to their respective owners; the plugin does not imply affiliation or endorsement.
- Herdr does not sandbox plugins — review the manifest (`herdr-plugin.toml`) and `agent_icons.py` before installing if in doubt.
- Install from trusted sources with `--ref` to pin a specific revision:

```sh
herdr plugin install qintmb/herdr-icon-agent-ui --ref <commit>
```

## License

MIT — see `LICENSE`. Font marks are the property of their respective owners; details in `THIRD_PARTY_NOTICES.md`.
