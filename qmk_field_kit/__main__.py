#!/usr/bin/env python3

"""
Entry point for running qmk_field_kit as a module.

Usage:
    python -m qmk_field_kit [args]
"""

from .cli import run_as_module

if __name__ == "__main__":
    run_as_module()