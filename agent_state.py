#!/usr/bin/env python3
"""Animated lifecycle state glyphs for Herdr agent panes.

The Herdr sidebar renders token values as plain text (ANSI escapes are shown
literally), so colour comes from per-cell ``fg`` in the sidebar row, not from
the token. We therefore expose one token *per state* and light exactly one at a
time; the others are cleared so their cells vanish. Each state token gets its
own fixed colour in ``rows_by_agent`` (see README). No emoji — braille + marks:

    working  → braille spinner (animated)  → $state_working  (colour orange)
    done     → check   ✓                   → $state_done     (colour green)
    blocked  → square  ■  (stop/block)     → $state_blocked  (colour red)
    idle     → ring    ◦                   → $state_idle     (dim)
    unknown  → question ?                  → $state_unknown  (dim)

Herdr never cycles a static token, so a short-lived background animator
(``--animate``) rewrites the working frame on a timer. It is the *sole* writer
of these tokens, and self-exits after a grace period with no working agent so
it never burns CPU on an idle machine. Any event/startup invocation just
(re)spawns it on demand.
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
STATIC_GLYPH = {"done": "✓", "blocked": "■", "idle": "◦", "unknown": "?"}
POLL_SECONDS = 0.15
IDLE_GRACE_TICKS = 12  # ~1.8s of no working agents, then the animator exits


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
    """[(pane_id, agent_status), ...] for every live agent."""
    data = run_herdr("agent", "list")
    out = []
    for a in data.get("result", {}).get("agents", []):
        pane = a.get("pane_id")
        status = a.get("agent_status")
        if isinstance(pane, str) and isinstance(status, str):
            out.append({"pane": pane, "status": status})
    return out


def glyph_for(status: str, frame: int) -> str | None:
    """Plain glyph for a status (no ANSI). None if the status is unmapped."""
    if status == "working":
        return FRAMES[frame % len(FRAMES)]
    return STATIC_GLYPH.get(status)


def write_state(source: str, pane: str, status: str, frame: int) -> None:
    """Set the one matching state token, clear the rest, in a single call."""
    active = TOKENS.get(status)
    glyph = glyph_for(status, frame)
    args = ["pane", "report-metadata", pane, "--source", source]
    for name in ALL_TOKENS:
        if name == active and glyph is not None:
            args += ["--token", f"{name}={glyph}"]
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
    last: dict[str, str] = {}
    try:
        while True:
            agents = working_agents()
            live = {a["pane"] for a in agents}
            any_working = False
            for a in agents:
                status = a["status"]
                g = glyph_for(status, frame)
                key = f"{status}:{g}"
                if last.get(a["pane"]) != key:
                    write_state(source, a["pane"], status, frame)
                    last[a["pane"]] = key
                if status == "working":
                    any_working = True
            # clear panes whose agent vanished
            for pane in [p for p in last if p not in live]:
                clear_state(source, pane)
                last.pop(pane, None)

            idle_ticks = 0 if any_working else idle_ticks + 1
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
