#!/usr/bin/env python3

import sys
import argparse
from typing import Optional

from .features import get_features, FeatureDetector
from .flash import FlashManager
from .bootloader import BootloaderManager
from .hid_comm import HIDCommunicator, HID_AVAILABLE


def main():
    """Main CLI entry point for QMK Field Kit."""
    import sys
    print(f"DEBUG: CLI main() called with sys.argv: {sys.argv}")
    print("DEBUG: About to create argument parser")
    parser = argparse.ArgumentParser(
        description="QMK Field Kit - Advanced flashing utility for QMK keyboards",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s left               # Flash left side  
  %(prog)s right              # Flash right side
  %(prog)s --info             # Show keyboard information
  %(prog)s --bootloader       # Enter bootloader mode only
  %(prog)s --validate         # Validate flash environment
        """
    )
    
    parser.add_argument(
        'side',
        nargs='?',
        choices=['left', 'right'],
        help='Which side of split keyboard to flash'
    )
    
    parser.add_argument(
        '--keyboard', '-k',
        help='Keyboard to flash (overrides qmk config user.keyboard)'
    )
    
    parser.add_argument(
        '--info', '-i',
        action='store_true',
        help='Show keyboard information and detected features'
    )
    
    parser.add_argument(
        '--bootloader', '-b',
        action='store_true', 
        help='Enter bootloader mode only (do not flash)'
    )
    
    parser.add_argument(
        '--validate', '-v',
        action='store_true',
        help='Validate flash environment and exit'
    )
    
    parser.add_argument(
        '--hid-test',
        action='store_true',
        help='Test HID communication with keyboard'
    )
    
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Force flash to specified side (bypasses side lock checks)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # Determine if side was explicitly provided
    explicit_side = args.side is not None
    
    try:
        if args.info:
            return show_info(args.keyboard, args.verbose)
        elif args.bootloader:
            return enter_bootloader_only(args.keyboard)
        elif args.validate:
            return validate_environment()
        elif args.hid_test:
            return test_hid_communication()
        else:
            # If no side specified, check if we can use side lock
            if args.side is None:
                try:
                    features = get_features(args.keyboard)
                    if not features.get('side_lock_enabled', False):
                        parser.print_help()
                        print("\nError: No side specified. Use 'left' or 'right' argument.")
                        return 1
                    # Side lock is enabled, let it determine the side
                    args.side = 'auto'  # Special value for auto-detection
                except Exception as e:
                    parser.print_help()
                    print(f"\nError: Cannot determine side lock status: {e}")
                    return 1
            
            return flash_keyboard_main(args.side, args.keyboard, args.verbose, explicit_side, args.force)
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def show_info(keyboard: Optional[str] = None, verbose: bool = False) -> int:
    """Show keyboard information and detected features."""
    try:
        features = get_features(keyboard)
    except Exception as e:
        print(f"Error detecting features: {e}")
        return 1
    
    print(f"Keyboard: {features['keyboard']}")
    print(f"Path: {features['keyboard_path']}")
    print(f"Bootloader: {features['bootloader']}")
    print(f"MCU Family: {features['mcu_family'] or 'Unknown'}")
    print(f"Split Keyboard: {'Yes' if features['split_enabled'] else 'No'}")
    
    if features['split_enabled']:
        print(f"Transport: {features.get('transport_protocol', 'Unknown')}")
    
    print(f"Auto Bootloader: {'Yes' if features.get('auto_bootloader', False) else 'No'}")
    print(f"Side Lock: {'Yes' if features.get('side_lock_enabled', False) else 'No'}")
    
    if verbose:
        print("\nAll detected features:")
        import pprint
        pprint.pprint(features, indent=2)
    
    return 0


def enter_bootloader_only(keyboard: Optional[str] = None) -> int:
    """Enter bootloader mode without flashing."""
    try:
        features = get_features(keyboard)
    except Exception as e:
        print(f"Error detecting features: {e}")
        return 1
    
    if not features['mcu_family']:
        print("Warning: Unknown MCU family, cannot auto-enter bootloader")
        print("Please manually enter bootloader mode")
        return 0
    
    print(f"Entering bootloader mode for {features['mcu_family']}...")
    
    manager = BootloaderManager()
    success = manager.enter_bootloader(
        features['mcu_family'],
        features.get('transport_protocol', 'serial')
    )
    
    if success:
        print("Bootloader mode entered successfully")
        return 0
    else:
        print("Failed to enter bootloader mode")
        return 1


def validate_environment() -> int:
    """Validate that the flash environment is ready."""
    print("Validating flash environment...")
    
    manager = FlashManager()
    if manager.validate_flash_environment():
        print("✓ Environment is ready for flashing")
        return 0
    else:
        print("✗ Environment validation failed")
        return 1


def flash_keyboard_main(side: str, keyboard: Optional[str] = None, verbose: bool = False, explicit_side: bool = False, force: bool = False) -> int:
    """Main keyboard flashing function."""
    manager = FlashManager()
    
    # Validate environment first
    if not manager.validate_flash_environment():
        return 1
    
    # Perform the flash
    success = manager.flash_keyboard(side, keyboard, explicit_side, force)
    
    return 0 if success else 1


def test_hid_communication() -> int:
    """Test HID communication with the keyboard."""
    print("QMK Field Kit HID Communication Test")
    print("=====================================")
    
    if not HID_AVAILABLE:
        print("❌ HID library not available")
        print("   Install with: pip install hidapi")
        return 1
    
    print("✓ HID library available")
    
    # Test connection
    comm = HIDCommunicator()
    
    print("Searching for keyboard...")
    device_info = comm.find_device()
    
    if not device_info:
        print("❌ Keyboard not found (VID: 0xFEED, PID: 0x0000)")
        print("   Make sure keyboard is connected and firmware supports raw HID")
        return 1
    
    print(f"✓ Found keyboard: {device_info.get('product_string', 'Unknown')}")
    
    # Test communication
    if not comm.connect():
        print("❌ Failed to connect to keyboard")
        return 1
    
    print("✓ Connected to keyboard")
    
    # Test ping
    print("Testing basic communication...")
    if comm.ping():
        print("✓ Communication test passed")
    else:
        print("❌ Communication test failed")
        comm.disconnect()
        return 1
    
    # Get firmware info
    print("\nFirmware Information:")
    fw_info = comm.get_firmware_info()
    if fw_info:
        for key, value in fw_info.items():
            print(f"  {key}: {value}")
    else:
        print("  No firmware info available")
    
    # Get side info
    print("\nSide Information:")
    side_info = comm.get_side_info()
    if side_info:
        for key, value in side_info.items():
            print(f"  {key}: {value}")
    else:
        print("  No side info available")
    
    comm.disconnect()
    print("\n✓ HID communication test completed successfully!")
    return 0


def run_as_module():
    """Entry point when run as python -m qmk_field_kit."""
    sys.exit(main())


if __name__ == "__main__":
    sys.exit(main())