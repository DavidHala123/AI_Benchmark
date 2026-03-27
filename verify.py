"""Environment verification script for the palletization project."""

from __future__ import annotations

import importlib
import sys


MIN_PYTHON = (3, 10)
REQUIRED_MODULES = ["PyQt5", "src.palletizer.app", "src.palletizer.solver"]


def main() -> int:
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version}")

    if sys.version_info < MIN_PYTHON:
        print(f"ERROR: Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} or newer is required.")
        return 1

    for module_name in REQUIRED_MODULES:
        try:
            importlib.import_module(module_name)
            print(f"OK: import {module_name}")
        except Exception as exc:
            print(f"ERROR: import {module_name} failed: {exc}")
            return 1

    print("Environment verification completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
