#!/usr/bin/env python3

"""
Minimal test of side lock functionality 
"""

import sys
import subprocess
from qmk_field_kit.hid_comm import HIDCommunicator
from qmk_field_kit.features import get_features

def test_side_lock():
    print("=== SIDE LOCK TEST ===")
    
    if len(sys.argv) < 2:
        print("Usage: test_sidelock.py <left|right>")
        return 1
        
    requested_side = sys.argv[1]
    print(f"Requested side: {requested_side}")
    
    # Check if side lock is enabled
    features = get_features()
    if not features.get('side_lock_enabled', False):
        print("❌ Side lock is not enabled")
        return 1
    
    print("✓ Side lock is enabled")
    
    # Query current side
    comm = HIDCommunicator()
    if not comm.connect():
        print("❌ Cannot connect to keyboard")
        return 1
        
    side_info = comm.get_side_info()
    comm.disconnect()
    
    if not side_info:
        print("❌ No side information available")
        return 1
        
    current_side = side_info.get('SIDE')
    print(f"✓ Current keyboard side: {current_side}")
    
    # Check for mismatch
    if requested_side != current_side:
        print(f"❌ SIDE LOCK VIOLATION!")
        print(f"   You requested '{requested_side}' but keyboard is configured as '{current_side}'")
        print(f"   Use --force to override: ./flash.sh {requested_side} --force")
        return 1
    
    print(f"✓ Side match OK - can proceed with {requested_side} flash")
    return 0

if __name__ == "__main__":
    sys.exit(test_side_lock())