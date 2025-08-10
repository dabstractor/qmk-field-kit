#!/usr/bin/env python3

print("=== Simple Test Script ===")
print("This should print before any QMK commands")

import sys
print("sys.argv:", sys.argv)

if len(sys.argv) > 1:
    print(f"Argument provided: {sys.argv[1]}")

print("=== Test completed ===")