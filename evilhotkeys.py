#!/usr/bin/env python3
"""Unified launcher for EvilHotKeys."""

from __future__ import annotations

import argparse
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _run(script_name: str) -> None:
    script_path = ROOT / script_name
    runpy.run_path(str(script_path), run_name="__main__")


def main() -> int:
    parser = argparse.ArgumentParser(description="EvilHotKeys launcher")
    parser.add_argument(
        "--mode",
        choices=["console", "gui", "enhanced"],
        default="enhanced",
        help="Which UI mode to run (default: enhanced)",
    )
    args = parser.parse_args()

    if args.mode == "console":
        _run("main.py")
    elif args.mode == "gui":
        _run("main-gui.py")
    else:
        _run("main-gui-enhanced.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
