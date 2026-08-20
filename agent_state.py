#!/usr/bin/env python3
"""Animated lifecycle-state line for Herdr agent panes.

Herdr joins adjacent sidebar cells with a `·` separator and renders token
values as plain text (ANSI is shown literally). To get a dot-free line and
colour, we pack the *whole line* — ``<state-glyph> <logo> <name>`` — into a
single token, and expose one token per state so exactly one is ever lit (the
rest cleared). The row gives each state token its own ``fg`` (see README), so
the line is coloured by status. LED marks follow lfsmoura/led-agent-status:

    working  → braille spinner (animated)  → $state_working  (orange)
    done     → ✓                           → $state_done     (green)
    blocked  → ⬤ (LED)                     → $state_blocked  (red)
    idle     → ⬤ (LED)                     → $state_idle     (dim)
    unknown  → ⬤ (LED)                     → $state_unknown  (dim)

Herdr never cycles a static token, so a short-lived background animator
(``--animate``) rewrites the working frame on a timer, holds a green ✓ for a
few seconds after a turn finishes (Herdr collapses done→idle instantly), and
self-exits once nothing needs animating so it costs nothing on an idle machine.
Any event/startup invocation just (re)spawns it on demand.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# One token per state — coloured individually in the sidebar row.
TOKENS = {
    "working": "state_working",
    "done": "state_done",
    "blocked": "state_blocked",
    "idle": "state_idle",
    "unknown": "state_unknown",
}
ALL_TOKENS = tuple(TOKENS.values())

FRAMES = ("⣷", "⣯", "⣟", "⡿", "⢿", "⣻", "⣽", "⣾")
# LED-style marks (à la lfsmoura/led-agent-status, but as sidebar glyphs):
# U+2B24 BLACK LARGE CIRCLE fills the line height so the LED reads at text
# size; colour per state comes from the row fg. done = check.
STATIC_GLYPH = {"done": "✓", "blocked": "⬤", "idle": "⬤", "unknown": "⬤"}
POLL_SECONDS = 0.15
IDLE_GRACE_TICKS = 12       # ~1.8s of nothing to show, then the animator exits
DONE_HOLD_SECONDS = 6.0     # hold green ✓ after work finishes before falling to idle



def _herdr() -> str:
    return os.environ.get("HERDR_BIN_PATH", "herdr")


def _tmp_dir() -> Path:
    base = os.environ.get("HERDR_PLUGIN_STATE_DIR") or os.environ.get("TMPDIR", "/tmp")
    d = Path(base) / "herdr-agent-state"
    d.mkdir(parents=True, exist_ok=True)
    try:
        d.chmod(0o700)
    except OSError:
        pass
    return d


def _lock_file() -> Path:
    return _tmp_dir() / "animator.pid"


def run_herdr(*args: str) -> dict[str, Any]:
    proc = subprocess.run([_herdr(), *args], capture_output=True, text=True)
    if proc.returncode != 0 or not proc.stdout.strip():
        return {}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {}


def working_agents() -> list[dict[str, str]]:
    """[{pane, status, name}, ...] for every live agent."""
    data = run_herdr("agent", "list")
    out = []
    for a in data.get("result", {}).get("agents", []):
        pane = a.get("pane_id")
        status = a.get("agent_status")
        name = a.get("agent")
        if isinstance(pane, str) and isinstance(status, str):
            out.append({"pane": pane, "status": status, "name": name or ""})
    return out


def glyph_for(status: str, frame: int) -> str | None:
    """Plain glyph for a status (no ANSI). None if the status is unmapped."""
    if status == "working":
        return FRAMES[frame % len(FRAMES)]
    return STATIC_GLYPH.get(status)


def _variant() -> str:
    """font | text — whether $harness_logo should use the PUA glyph."""
    try:
        from agent_icons import configured_variant, font_available

        v = configured_variant()
        if v == "auto":
            return "font" if font_available() else "text"
        return v if v in ("font", "text") else "text"
    except Exception:
        return "text"


def _logo(name: str, variant: str) -> str:
    try:
        from agent_icons import logo_for

        return logo_for(name, variant) or ""
    except Exception:
        return ""


def compose_line(name: str, logo: str, status: str, frame: int) -> str | None:
    """One combined cell: `<state-glyph> <logo> <name>` — no separators.

    Herdr joins adjacent row cells with `·`; putting the whole line in a
    single token is the only way to render it dot-free. The cost is one colour
    per line (set by the row `fg`), so brand-coloured logos are traded for a
    clean, status-coloured line.
    """
    glyph = glyph_for(status, frame)
    if glyph is None:
        return None
    parts = [glyph]
    if logo:
        parts.append(logo)
    if name:
        parts.append(name)
    return " ".join(parts)


def write_state(source: str, pane: str, line: str | None, status: str) -> None:
    """Set the one matching per-status line token, clear the rest."""
    active = TOKENS.get(status)
    args = ["pane", "report-metadata", pane, "--source", source]
    for name in ALL_TOKENS:
        if name == active and line is not None:
            args += ["--token", f"{name}={line}"]
        else:
            args += ["--clear-token", name]
    run_herdr(*args)


def clear_state(source: str, pane: str) -> None:
    args = ["pane", "report-metadata", pane, "--source", source]
    for name in ALL_TOKENS:
        args += ["--clear-token", name]
    run_herdr(*args)


def _already_running() -> bool:
    lock = _lock_file()
    if lock.is_file():
        try:
            pid = int(lock.read_text().strip())
            os.kill(pid, 0)  # raises if dead
            return True
        except (ValueError, ProcessLookupError, PermissionError):
            pass
    return False


def spawn_animator() -> None:
    """(Re)start the background animator unless one is already live."""
    if _already_running():
        return
    subprocess.Popen(
        [sys.executable, os.path.abspath(__file__), "--animate"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def animate(source: str) -> int:
    """Sole token writer. Renders every agent's state; self-exits when idle."""
    lock = _lock_file()
    lock.write_text(str(os.getpid()))
    stop = _tmp_dir() / "animator.stop"
    stop.unlink(missing_ok=True)

    def _bye(*_: Any) -> None:
        lock.unlink(missing_ok=True)
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, _bye)

    frame = 0
    idle_ticks = 0
    variant = _variant()
    last: dict[str, str] = {}
    prev_status: dict[str, str] = {}   # pane -> last real status seen
    done_until: dict[str, float] = {}  # pane -> monotonic deadline to hold "done"
    try:
        while True:
            now = time.monotonic()
            agents = working_agents()
            live = {a["pane"] for a in agents}
            active = False  # working, or holding a done badge → keep animating
            for a in agents:
                pane, status, name = a["pane"], a["status"], a["name"]
                # working → idle/done means a turn just finished: synthesize a
                # held "done" badge, because Herdr collapses done into idle fast.
                if prev_status.get(pane) == "working" and status in ("idle", "done"):
                    done_until[pane] = now + DONE_HOLD_SECONDS
                prev_status[pane] = status

                if status == "working":
                    done_until.pop(pane, None)
                    display = "working"
                elif now < done_until.get(pane, 0.0):
                    display = "done"
                else:
                    done_until.pop(pane, None)
                    display = status

                line = compose_line(name, _logo(name, variant), display, frame)
                key = f"{display}:{line}"
                if last.get(pane) != key:
                    write_state(source, pane, line, display)
                    last[pane] = key
                if display == "working" or pane in done_until:
                    active = True
            # clear panes whose agent vanished
            for pane in [p for p in last if p not in live]:
                clear_state(source, pane)
                for d in (last, prev_status, done_until):
                    d.pop(pane, None)

            idle_ticks = 0 if active else idle_ticks + 1
            if idle_ticks >= IDLE_GRACE_TICKS or stop.is_file():
                break
            frame += 1
            time.sleep(POLL_SECONDS)
    finally:
        lock.unlink(missing_ok=True)
        stop.unlink(missing_ok=True)
    return 0


def stop_animator() -> None:
    lock = _lock_file()
    (_tmp_dir() / "animator.stop").touch()
    if lock.is_file():
        try:
            os.kill(int(lock.read_text().strip()), signal.SIGTERM)
        except (ValueError, ProcessLookupError, PermissionError):
            lock.unlink(missing_ok=True)


def main() -> int:
    source = os.environ.get(
        "HERDR_PLUGIN_ID", "qintmb.herdr-icon-agent-ui"
    )
    source = f"plugin:{source}:state"
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "--animate":
        return animate(source)
    if arg == "--stop":
        stop_animator()
        return 0
    # default (startup / pane.agent_detected / pane.agent_status_changed /
    # refresh action): just ensure the animator is running.
    spawn_animator()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
