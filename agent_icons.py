#!/usr/bin/env python3
"""Apply display-only icons to Herdr agent names.

Supports: claude, codex, opencode, omp, cline, mastracode, kimi, kilo,
maki, pi, hermes, cursor, copilot, deepseek, gemini, gpt, qwen.

Icon variant system:
- font: Private Use Area codepoints (requires Herdr Agent Icons Max font)
- text: compact ASCII/Unicode fallbacks (works with any terminal font)
- auto: font when Fontconfig finds the face, text fallback otherwise
- none: clears the logo token
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

FONT_FAMILY = "Herdr Agent Icons Max"
TOKEN_NAME = "harness_logo"

PUA_LOGOS: dict[str, str] = {
    "claude": "\ue1a0",
    "codex": "\ue1a1",
    "opencode": "\ue1a2",
    "omp": "\ue1a3",
    "cline": "\ue1a4",
    "mastracode": "\ue1a5",
    "kimi": "\ue1a6",
    "kilo": "\ue1a7",
    "maki": "\ue1a8",
    "pi": "\ue1a9",
    "hermes": "\ue1aa",
    "cursor": "\ue1ab",
    "copilot": "\ue1ac",
    "deepseek": "\ue1ad",
    "gemini": "\ue1ae",
    "gpt": "\ue1af",
    "qwen": "\ue1b0",
}

TEXT_LOGOS: dict[str, str] = {
    "claude": "\u00a7",
    "codex": "\u039b",
    "opencode": "\u25c7",
    "omp": "\u03a0",
    "cline": "\u2207",
    "mastracode": "\u2211",
    "kimi": "\u2728",
    "kilo": "\u265f",
    "maki": "\u2733",
    "pi": "\u03c0",
    "hermes": "\u262a",
    "cursor": "\u25c6",
    "copilot": "\u2299",
    "deepseek": "\u224b",
    "gemini": "\u2726",
    "gpt": "\u273a",
    "qwen": "\u03d8",
}

VARIANTS = ("auto", "font", "text", "none")


def run_herdr(herdr: str, *args: str) -> dict[str, Any]:
    try:
        result = subprocess.run(
            [herdr, *args], check=False, capture_output=True, text=True
        )
    except OSError as error:
        raise RuntimeError(f"could not run {herdr!r}: {error}") from error
    if result.returncode != 0:
        msg = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(msg or f"herdr exit {result.returncode}")
    if not result.stdout.strip():
        return {}
    return json.loads(result.stdout)


def font_available() -> bool:
    fc_match = shutil.which("fc-match")
    if fc_match is None:
        return False
    result = subprocess.run(
        [fc_match, "--format", "%{family}\n", FONT_FAMILY],
        check=False,
        capture_output=True,
        text=True,
    )
    families = {
        name.strip()
        for line in result.stdout.splitlines()
        for name in line.split(",")
    }
    return result.returncode == 0 and FONT_FAMILY in families


def configured_variant(explicit: str | None = None) -> str:
    if explicit is not None:
        return explicit
    config_dir = os.environ.get("HERDR_PLUGIN_CONFIG_DIR")
    if not config_dir:
        return "auto"
    config_path = Path(config_dir) / "config.toml"
    if not config_path.is_file():
        return "auto"
    with config_path.open("rb") as f:
        return tomllib.load(f).get("variant", "auto")


def logo_for(agent: str, variant: str) -> str | None:
    if agent not in PUA_LOGOS or variant == "none":
        return None
    if variant == "auto":
        variant = "font" if font_available() else "text"
    return PUA_LOGOS[agent] if variant == "font" else TEXT_LOGOS[agent]


def report_logo(
    herdr: str, source: str, pane_id: str, agent: str | None, variant: str
) -> None:
    logo = logo_for(agent, variant) if agent else None
    args_ = [
        "pane",
        "report-metadata",
        pane_id,
        "--source",
        source,
    ]
    if logo is None:
        args_.extend(["--clear-token", TOKEN_NAME])
    else:
        args_.extend(["--token", f"{TOKEN_NAME}={logo}"])
    run_herdr(herdr, *args_)


def event_value(value: Any, key: str) -> str | None:
    if isinstance(value, dict):
        candidate = value.get(key)
        if isinstance(candidate, str):
            return candidate
        for child in value.values():
            found = event_value(child, key)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = event_value(child, key)
            if found is not None:
                return found
    return None


def event_pane(raw_event: str) -> str | None:
    try:
        event = json.loads(raw_event)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"invalid HERDR_PLUGIN_EVENT_JSON: {error}") from error
    return event_value(event, "pane_id")


def current_target(herdr: str, pane_id: str) -> tuple[str, str | None]:
    response = run_herdr(herdr, "pane", "get", pane_id)
    pane = response.get("result", {}).get("pane", {})
    return pane_id, pane.get("agent")


def startup_targets(herdr: str) -> list[tuple[str, str | None]]:
    response = run_herdr(herdr, "pane", "list")
    panes = response.get("result", {}).get("panes", [])
    return [
        (p["pane_id"], p.get("agent"))
        for p in panes
        if isinstance(p, dict)
        and isinstance(p.get("pane_id"), str)
        and (p.get("agent") is None or isinstance(p.get("agent"), str))
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pane")
    parser.add_argument("--agent")
    parser.add_argument("--source")
    parser.add_argument("--variant", choices=VARIANTS)
    args = parser.parse_args()

    herdr = os.environ.get("HERDR_BIN_PATH", "herdr")
    plugin_id = os.environ.get("HERDR_PLUGIN_ID", "qintmb.herdr-icon-agent-ui")
    source = args.source or f"plugin:{plugin_id}"
    variant = configured_variant(args.variant)

    if bool(args.pane) != bool(args.agent):
        parser.error("--pane and --agent must be supplied together")

    try:
        if args.pane and args.agent:
            targets = [(args.pane, args.agent)]
        elif os.environ.get("HERDR_PLUGIN_EVENT_JSON"):
            pane_id = event_pane(os.environ["HERDR_PLUGIN_EVENT_JSON"])
            targets = [] if pane_id is None else [current_target(herdr, pane_id)]
        else:
            targets = startup_targets(herdr)
    except (RuntimeError, json.JSONDecodeError) as error:
        print(error, file=sys.stderr)
        return 1

    failures = []
    for pane_id, agent in targets:
        try:
            report_logo(herdr, source, pane_id, agent, variant)
        except (RuntimeError, json.JSONDecodeError) as error:
            failures.append(f"{pane_id}: {error}")

    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())