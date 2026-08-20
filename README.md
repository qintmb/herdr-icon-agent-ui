<div align="center">

# Herdr Icon Agent UI

A Herdr v1 plugin for the sidebar: large, vertically-aligned monochrome **harness logos** (custom font, scaled to cap-height and aspect-correct) plus an **animated lifecycle-state line** — orange braille spinner while working, held green `✓` on done, red/dim LED `⬤` for blocked/idle — rendered dot-free so the state glyph, logo, and agent name sit flush together.

<video src="https://github.com/qintmb/herdr-icon-agent-ui/releases/download/v1.3.0/preview.mp4" autoplay loop muted playsinline width="360"></video>

</div>

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
| GitHub Copilot | `U+E1AC` | `⊙` |
| DeepSeek | `U+E1AD` | `≋` |
| Gemini | `U+E1AE` | `✦` |
| GPT / OpenAI | `U+E1AF` | `✺` |
| Qwen | `U+E1B0` | `Ϙ` |

The plugin writes display tokens via `pane report-metadata`:

- `$harness_logo` — the harness mark (static, per detected agent), for layouts that want the logo as its own cell.
- `$state_working` / `$state_done` / `$state_blocked` / `$state_idle` / `$state_unknown` — **animated lifecycle-state line**. Exactly one is set per pane (the rest cleared) and holds the whole dot-free line `⟨glyph⟩ ⟨logo⟩ ⟨name⟩`: braille spinner while `working`, `✓` on `done`, LED `⬤` on `blocked`/`idle`/`unknown`. Colour comes from each cell's `fg` in the sidebar row.

It **never** changes `display_agent`, reports state labels, or touches agent lifecycle — Herdr's own detection drives everything; the plugin only mirrors the reported status into a styled line. Herdr's native `state_icon` still works and can be kept alongside.

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
font-codepoint-map = U+E1A0-U+E1B0="Herdr Agent Icons Max"
```

> Replace `JetBrains Mono` with your actual primary family. Font changes only apply to new terminal surfaces — open a new window/tab after editing.

Verify:

```sh
ghostty +list-fonts | grep -F 'Herdr Agent Icons Max'
```

### 2.3 Herdr sidebar configuration

Add the tokens to the agent rows in `~/.config/herdr/config.toml`. To avoid Herdr's `·` cell separator, `agent_state.py` packs the whole line — **state glyph + harness logo + agent name** — into a single token, one per state (only one set at a time, the rest cleared). Each carries its own `fg`, so the line is coloured by status:

```toml
[ui.sidebar.agents.rows_by_agent]
claude   = [["workspace"], [{ token = "$state_working", fg = "#d97757" }, { token = "$state_done", fg = "#a6da95" }, { token = "$state_blocked", fg = "#ed8796" }, { token = "$state_idle", fg = "#6e738d" }, { token = "$state_unknown", fg = "#6e738d" }], ["terminal_title_stripped"]]
# codex / opencode / omp / pi / hermes: identical (state colour is per-status, not per-agent)
```

The line reads e.g. `⣷ § claude` (spinner) or `✓ § claude` (done) with **no separator dots**. Because the logo lives inside the coloured line, brand colours are traded for one status colour per line — this is the only dot-free layout Herdr allows. Want the brand-coloured logo back? Add a separate `{ token = "$harness_logo", fg = "#d97757" }` cell (accepting the `·` before it).

> **Glyph coverage.** Working frames use braille (`U+2800–U+28FF`); `✓`/`⬤` are common Unicode; `$harness_logo` (PUA `U+E1A0–U+E1B0`) needs the icon font from §2.1. The line embeds the logo glyph, so keep the font installed.

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

### Lifecycle state glyphs

`agent_state.py` mirrors each pane's reported `agent_status` into a per-state token that holds the whole dot-free line (`⟨glyph⟩ ⟨logo⟩ ⟨name⟩`) — exactly one is set, the others cleared. Colour lives in each cell's `fg`:

| State | Glyph | Token | Suggested `fg` |
| --- | --- | --- | --- |
| working | braille spinner (8 frames, animated) | `$state_working` | orange `#d97757` |
| done | `✓` | `$state_done` | green `#a6da95` |
| blocked | `⬤` (LED) | `$state_blocked` | red `#ed8796` |
| idle | `⬤` (LED) | `$state_idle` | dim `#6e738d` |
| unknown | `⬤` (LED) | `$state_unknown` | dim `#6e738d` |

The `⬤` LED marks and `✓` follow [lfsmoura/led-agent-status](https://github.com/lfsmoura/led-agent-status)'s colour scheme (working spinner, red-blink-style blocked, green done, dim idle) — here as sidebar glyphs instead of a BLE strip.

**"done" hold.** Herdr collapses `done` into `idle` almost immediately, so a finished turn would flash green then vanish. The animator watches for a `working → idle/done` transition and holds the green `✓` for `DONE_HOLD_SECONDS` (default 6 s) before letting the line fall back to idle.

Herdr never animates a static token, so a short-lived background **animator** rewrites the working frame every 150 ms. It is spawned on demand (startup, `pane.agent_detected`, `pane.agent_status_changed`, or the `state-start` action), is the only writer of these tokens, and **self-exits ~1.8 s after nothing needs animating** — so it costs nothing on an idle machine. Stop it manually with the `state-stop` action or:

```sh
python3 agent_state.py --stop
```

Tune frames/timing via constants at the top of `agent_state.py` (`FRAMES`, `STATIC_GLYPH`, `POLL_SECONDS`, `IDLE_GRACE_TICKS`, `DONE_HOLD_SECONDS`); colours are set in the sidebar row `fg`.

### Glyph size and centering

Font metrics are set to match **JetBrains Mono** (UPM 1000, advance 600, ascent 1020, descent −300). Each mark is scaled **uniformly** to fit a `560×760` cell — whichever axis hits its limit first stops the scale, so the source aspect ratio is preserved and wide marks (mastracode, claude) are not flattened. Glyphs are centred on `CENTER_Y = 365`, the midpoint of JetBrains Mono cap height. To change, edit constants in `tools/build_font.py`:

```python
MAX_WIDTH = 560
MAX_HEIGHT = 760
CENTER_Y = 365
```

`tools/build_font.py` asserts after every build that each glyph matches its SVG aspect ratio (±0.02) and fits the cell.

Rebuild the font, reinstall, and open a new terminal surface.

### Adding a new agent

1. Place an SVG at `assets/svg/<name>.svg`
2. Run `python3 tools/normalize_svg.py` to strip `<title>`, fills, and wrappers — `build_font.py` only accepts `<svg>` and `<path>`
3. Add a line to `font/codepoints.toml`
4. Add entries to `PUA_LOGOS` and `TEXT_LOGOS` in `agent_icons.py`
5. Rebuild the font, reinstall, refresh

## 5. Usage

The plugin runs automatically: once on Herdr startup (`[[startup]]`) and whenever an agent is detected on a pane (`pane.agent_detected`). The `$harness_logo` token is attached to supported agent panes; `agent_state.py` spawns the animator so `$agent_state` tracks lifecycle status live (also refreshed on `pane.agent_status_changed`).

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
