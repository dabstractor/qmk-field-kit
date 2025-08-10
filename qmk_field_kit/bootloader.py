#!/usr/bin/env python3

import time
import platform
import subprocess
from typing import Optional, List
from pathlib import Path
from .hid_comm import HIDCommunicator, HID_AVAILABLE


class BootloaderManager:
    """Handles bootloader entry for different MCU families."""
    
    def __init__(self):
        self.system = platform.system()
    
    def enter_bootloader(self, mcu_family: str, transport_protocol: str = 'serial') -> bool:
        """
        Enter bootloader mode for the specified MCU family.
        
        Args:
            mcu_family: MCU family (rp2040, avr, arm)
            transport_protocol: Communication protocol (serial, i2c, etc.)
        
        Returns:
            True if bootloader entry was successful or attempted
        """
        if mcu_family == 'rp2040':
            return self._enter_rp2040_bootloader(transport_protocol)
        elif mcu_family == 'avr':
            return self._enter_avr_bootloader()
        elif mcu_family == 'arm':
            return self._enter_arm_bootloader()
        else:
            print(f"Warning: Unknown MCU family '{mcu_family}', skipping bootloader entry")
            return True
    
    def _enter_rp2040_bootloader(self, transport_protocol: str = 'serial') -> bool:
        """Enter bootloader mode for RP2040 via HID commands."""
        
        # Try HID communication first
        if HID_AVAILABLE:
            print("Attempting HID bootloader entry...")
            if self._try_hid_bootloader_entry():
                return self._wait_for_bootloader_device()
            
            # HID failed, show manual instructions
            print("HID bootloader entry not available")
            print("Please manually enter bootloader mode:")
            print("  1. Hold the BOOT button on the keyboard")
            print("  2. Press and release the RESET button") 
            print("  3. Release the BOOT button")
            return self._wait_for_bootloader_device()
        else:
            # HID library not available, show manual instructions
            print("HID library not available")
            print("Please manually enter bootloader mode:")
            print("  1. Hold the BOOT button on the keyboard")
            print("  2. Press and release the RESET button") 
            print("  3. Release the BOOT button")
            return self._wait_for_bootloader_device()
    
    def _try_hid_bootloader_entry(self) -> bool:
        """Try to trigger bootloader via HID communication."""
        try:
            comm = HIDCommunicator()
            
            if comm.connect():
                success = comm.trigger_bootloader()
                comm.disconnect()
                return success
            else:
                print("Could not connect to keyboard via HID")
                return False
                
        except Exception as e:
            print(f"HID bootloader entry failed: {e}")
            return False
    
    def _enter_avr_bootloader(self) -> bool:
        """Enter bootloader mode for AVR MCUs."""
        print("AVR bootloader entry not implemented yet")
        print("Please manually enter bootloader mode")
        return True
    
    def _enter_arm_bootloader(self) -> bool:
        """Enter bootloader mode for ARM MCUs."""
        print("ARM bootloader entry not implemented yet") 
        print("Please manually enter bootloader mode")
        return True
    
    
    def _wait_for_bootloader_device(self, timeout: int = 30) -> bool:
        """Wait for bootloader device to appear."""
        print(f"Waiting for bootloader device to appear (timeout: {timeout}s)...")
        
        if self.system == "Darwin":  # macOS
            return self._wait_for_macos_bootloader_device(timeout)
        elif self.system == "Linux":
            return self._wait_for_linux_bootloader_device(timeout)
        else:
            print(f"Bootloader detection not implemented for {self.system}")
            print("Please verify bootloader device is ready and press Enter to continue...")
            input()
            return True
    
    def _wait_for_macos_bootloader_device(self, timeout: int) -> bool:
        """Wait for RPI-RP2 drive to appear on macOS."""
        drive_path = Path("/Volumes/RPI-RP2")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if drive_path.exists():
                print(f"RPI-RP2 drive detected at {drive_path}!")
                return True
            print(".", end="", flush=True)
            time.sleep(0.5)
        
        print(f"\nTimeout waiting for RPI-RP2 drive after {timeout}s")
        return False
    
    def _wait_for_linux_bootloader_device(self, timeout: int) -> bool:
        """Wait for bootloader device on Linux."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Check for RP2040 in bootloader mode
            try:
                result = subprocess.run(['lsusb'], capture_output=True, text=True)
                if 'Raspberry Pi' in result.stdout and 'RP2 Boot' in result.stdout:
                    print("RP2040 bootloader device detected!")
                    return True
            except subprocess.CalledProcessError:
                pass
            
            print(".", end="", flush=True)
            time.sleep(0.5)
        
        print(f"\nTimeout waiting for bootloader device after {timeout}s")
        return False
    
    def wait_for_device_ready(self, mcu_family: str) -> bool:
        """Wait for the device to be ready for flashing."""
        if mcu_family == 'rp2040':
            return self._wait_for_bootloader_device()
        else:
            # For other MCUs, assume they're ready
            return True


def enter_bootloader(mcu_family: str, transport_protocol: str = 'serial') -> bool:
    """Convenience function to enter bootloader mode."""
    manager = BootloaderManager()
    return manager.enter_bootloader(mcu_family, transport_protocol)


if __name__ == "__main__":
    # Test bootloader entry for RP2040
    success = enter_bootloader('rp2040', 'serial')
    print(f"Bootloader entry {'successful' if success else 'failed'}")