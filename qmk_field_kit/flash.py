#!/usr/bin/env python3

import subprocess
import platform
import shutil
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

from .features import get_features
from .bootloader import BootloaderManager
from .hid_comm import HIDCommunicator


class FlashManager:
    """Manages firmware flashing for QMK keyboards."""
    
    def __init__(self):
        self.system = platform.system()
        self.bootloader_manager = BootloaderManager()
    
    def flash_keyboard(self, side: str = "right", keyboard: Optional[str] = None, explicit_side: bool = False, force: bool = False) -> bool:
        """
        Flash the keyboard with automatic side detection and bootloader entry.
        
        Args:
            side: Which side to flash ("left" or "right")
            keyboard: Keyboard to flash (defaults to current qmk config)
            explicit_side: True if side was explicitly provided by user (initial flash)
            force: True to bypass side lock checks and force flash to specified side
        
        Returns:
            True if flash was successful
        """
        print(f"DEBUG: FlashManager.flash_keyboard called with side='{side}', explicit_side={explicit_side}, force={force}")
        if side not in ["left", "right", "auto"]:
            print(f"Error: Invalid side '{side}'. Must be 'left' or 'right'.")
            return False
        
        # Get keyboard features
        try:
            features = get_features(keyboard)
        except Exception as e:
            print(f"Error detecting keyboard features: {e}")
            return False
        
        # Handle side_lock logic
        if features.get('side_lock_enabled', False):
            print(f"DEBUG: Side lock enabled, requested='{side}', force={force}")
            final_side = self._handle_side_lock(side, explicit_side, features, force)
            if final_side is None:
                return False
            print(f"DEBUG: Side lock resolved '{side}' -> '{final_side}'")
            side = final_side
        
        print(f"\nFlashing the *{side}* side of {features['keyboard']}")
        self._print_side_indicator(side)
        
        # Determine flash strategy based on features and platform
        flash_command, post_command = self._build_flash_commands(features, side)
        
        if not flash_command:
            print("Error: Could not determine flash command")
            return False
        
        # Determine if this is a compile-only command (when auto_bootloader is enabled)
        is_compile_only = features.get('auto_bootloader', False)
        
                # Clean previous build artifacts to ensure fresh compilation
        print("Cleaning QMK build artifacts...")
        subprocess.run(['qmk', 'clean'], check=True)
        print("✓ QMK build artifacts cleaned.")

        # Execute flash command (compile, or compile+flash)
        print(f"\nRunning: {flash_command}")
        try:
            result = subprocess.run(flash_command, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Flash command failed with exit code {e.returncode}")
            return False
        
        if is_compile_only:
            print("✓ Compilation successful")
            
            # Enter bootloader mode after successful compilation
            if features['mcu_family']:
                print(f"Triggering bootloader mode for {features['mcu_family']}...")
                self.bootloader_manager.enter_bootloader(
                    features['mcu_family'], 
                    features.get('transport_protocol', 'serial')
                )
            
            # Execute post-bootloader command (actual flashing)
            if post_command:
                print(f"Running flash command: {post_command}")
                try:
                    subprocess.run(post_command, shell=True, check=True)
                except subprocess.CalledProcessError as e:
                    print(f"Flash command failed: {e}")
                    return False
        else:
            print("✓ Flash completed successfully")
            
            # Execute post-command if needed (cleanup, etc.)
            if post_command:
                print(f"Running post-command: {post_command}")
                try:
                    subprocess.run(post_command, shell=True, check=True)
                except subprocess.CalledProcessError as e:
                    print(f"Post-command failed: {e}")
                    # Don't return False here as the main flash might have succeeded
        
        print(f"\n✓ Flash completed for {side} side")
        return True
    
    def _handle_side_lock(self, requested_side: str, explicit_side: bool, features: Dict[str, Any], force: bool = False) -> Optional[str]:
        """
        Handle side_lock logic for determining which side to flash.
        
        Args:
            requested_side: The side requested by user
            explicit_side: True if this is an initial flash with explicit side
            features: Keyboard features dictionary
            force: True to bypass side lock checks and force flash
            
        Returns:
            Side to flash ("left" or "right") or None to abort
        """
        print("Side lock is enabled - querying keyboard for current side...")
        
        # If force flag is used, bypass all checks and use requested side
        if force:
            print(f"⚠️  Force flag detected - bypassing side lock checks!")
            print(f"   Forcing flash to '{requested_side}' side regardless of current configuration")
            return requested_side
        
        # If this is an explicit initial flash with force flag, use the requested side
        # Otherwise, we need to check the current side first
        
        # Query the keyboard for its current side via HID
        comm = HIDCommunicator()
        
        if not comm.connect():
            print("❌ Cannot connect to keyboard via HID")
            print("   Side lock requires HID connection to query keyboard side")
            print("   Either:")
            print("   - Flash with explicit side for initial setup: ./flash.sh left")
            print("   - Disable side lock: remove SIDE_LOCK_ENABLE from rules.mk")
            return None
        
        try:
            side_info = comm.get_side_info()
            comm.disconnect()
            
            if not side_info:
                print("❌ No side information available from keyboard")
                print("   This may be an unflashed keyboard or firmware without side support")
                print("   Use explicit side for initial flash: ./flash.sh left")
                return None
            
            current_side = side_info.get('SIDE')
            if not current_side:
                print("❌ Keyboard did not report its side")
                print("   Use explicit side for initial flash: ./flash.sh left")
                return None
            
            if current_side not in ['left', 'right']:
                print(f"❌ Keyboard reported invalid side: {current_side}")
                return None
            
            print(f"✓ Keyboard reports side: {current_side}")
            
            # If user requested a different side than what's configured, ERROR
            # (but not when auto-detecting)
            if requested_side != current_side and requested_side != 'auto':
                print(f"❌ SIDE LOCK: You requested '{requested_side}' but keyboard is configured as '{current_side}'")
                print(f"   To flash the {requested_side} side, use --force flag:")
                print(f"   ./flash.sh {requested_side} --force")
                print(f"   Or to flash the configured side:")
                print(f"   ./flash.sh {current_side}")
                return None
            
            return current_side
            
        except Exception as e:
            comm.disconnect()
            print(f"❌ Error querying keyboard side: {e}")
            return None
    
    def _print_side_indicator(self, side: str):
        """Print visual indicator of which side is being flashed."""
        print()
        if side == "left":
            print("<----------------------- The one over here")
        elif side == "right":
            print("The one over there ---------------------->")
        print()
    
    def _find_qmk_root(self) -> Optional[Path]:
        """
        Find QMK firmware root by traversing up the directory tree until we find util/uf2conv.py.
        
        Returns:
            Path to QMK firmware root or None if not found
        """
        current_path = Path.cwd().resolve()
        
        # Traverse up the directory tree
        while current_path != current_path.parent:
            uf2conv_path = current_path / "util" / "uf2conv.py"
            if uf2conv_path.exists():
                return current_path
            current_path = current_path.parent
        
        return None

    def _build_flash_commands(self, features: Dict[str, Any], side: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Build flash and post-flash commands based on features and platform.
        
        Returns:
            Tuple of (flash_command, post_command)
        """
        print(f"DEBUG: _build_flash_commands called with side='{side}'")
        if not features['split_enabled']:
            # Single keyboard
            if features.get('auto_bootloader', False):
                return "qmk compile", None
            else:
                return "qmk flash", None
        
        # Split keyboard logic
        bootloader = features['bootloader']
        auto_bootloader = features.get('auto_bootloader', False)
        
        if auto_bootloader:
            # Use compile-first approach with auto bootloader triggering
            side_flag = f"-DMASTER_{side.upper()} -DINIT_EE_HANDS_{side.upper()}"
            # Pass EXTRAFLAGS through to qmk compile - ensure they're used in compilation
            compile_cmd = f'EXTRAFLAGS="{side_flag}" qmk compile'
            
            if bootloader == 'rp2040':
                # Get the compiled firmware file
                keyboard_name = features['keyboard'].replace('/', '_')
                keymap = self._get_current_keymap()
                filename = f"{keyboard_name}_{keymap}.uf2"
                
                # Find QMK firmware root dynamically
                qmk_root = self._find_qmk_root()
                if not qmk_root:
                    print("Error: Could not find QMK firmware root (util/uf2conv.py)")
                    return None, None
                
                # Use QMK's built-in uf2conv.py tool with --wait --deploy for automatic reboot
                post_cmd = f"cd {qmk_root} && ./util/uf2conv.py --wait --deploy {filename}"
            else:
                # For other bootloaders, use appropriate flash command after bootloader trigger
                post_cmd = f"qmk flash -bl {bootloader}-split-{side}"
            
            return compile_cmd, post_cmd
        else:
            # Use traditional qmk flash approach
            if bootloader == 'rp2040':
                return f"qmk flash -bl uf2-split-{side}", None
            else:
                return f"qmk flash -bl {bootloader}-split-{side}", None
    
    def _get_current_keymap(self) -> str:
        """Get current keymap from qmk config."""
        try:
            result = subprocess.run(['qmk', 'config', 'user.keymap'], 
                                  capture_output=True, text=True, check=True)
            return result.stdout.strip().split('=')[1]
        except (subprocess.CalledProcessError, IndexError):
            return "default"
    
    def validate_flash_environment(self) -> bool:
        """Validate that the environment is ready for flashing."""
        # Check if qmk command is available
        if not shutil.which('qmk'):
            print("Error: qmk command not found. Please install QMK CLI.")
            return False
        
        # Check if current keyboard is set
        try:
            result = subprocess.run(['qmk', 'config', 'user.keyboard'], 
                                  capture_output=True, text=True, check=True)
            if not result.stdout.strip().split('=')[1]:
                print("Error: No keyboard selected. Use 'qmk config user.keyboard=...'")
                return False
        except subprocess.CalledProcessError:
            print("Error: Could not get keyboard configuration")
            return False
        
        # Platform-specific checks
        if self.system == "Darwin":
            # Check for picotool on macOS
            features = get_features()
            if features.get('bootloader') == 'rp2040' and not shutil.which('picotool'):
                print("Warning: picotool not found. Install with 'brew install picotool'")
        
        return True


def flash_keyboard(side: str = "right", keyboard: Optional[str] = None, explicit_side: bool = False, force: bool = False) -> bool:
    """Convenience function to flash keyboard."""
    manager = FlashManager()
    
    if not manager.validate_flash_environment():
        return False
    
    return manager.flash_keyboard(side, keyboard, explicit_side, force)


if __name__ == "__main__":
    import sys
    
    side = "right"
    if len(sys.argv) > 1:
        side = sys.argv[1]
    
    success = flash_keyboard(side)
    sys.exit(0 if success else 1)