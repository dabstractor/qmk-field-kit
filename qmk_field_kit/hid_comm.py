#!/usr/bin/env python3

import time
import platform
from typing import Optional, List, Dict, Any

# Try to import hid library, fall back gracefully if not available
try:
    import hid
    HID_AVAILABLE = True
except ImportError:
    HID_AVAILABLE = False
    print("Warning: hidapi library not available. Install with: pip install -r requirements.txt")


class HIDCommunicator:
    """Handles HID communication with the QMK Field Kit firmware."""
    
    # Field Kit protocol identifiers
    FIELD_KIT_ID1 = 0x82
    FIELD_KIT_ID2 = 0x9E
    ETX_TERMINATOR = 0x03
    
    # Response codes
    RESPONSE_OK = 0x01
    RESPONSE_ERROR = 0x00
    RESPONSE_BOOTLOADER_TRIGGERED = 0x02
    RESPONSE_INFO = 0x03
    
    def __init__(self):
        self.device = None
        self.system = platform.system()
    
    def find_device(self) -> Optional[Dict[str, Any]]:
        """Find the keyboard's QMK Raw HID interface.

        VID/PID-agnostic: enumerate every HID device and select the one carrying
        the QMK Raw HID signature (usage page 0xFF60, usage 0x61). This finds
        the keyboard regardless of its USB VID/PID — so it survives a VID/PID
        change and finds either half of the split even if they're on different
        firmware (e.g. one still on the legacy 0xFEED:0x0000).
        """
        if not HID_AVAILABLE:
            return None
        for device_info in hid.enumerate(0x0, 0x0):
            if (device_info.get('usage_page') == 0xFF60
                    and device_info.get('usage') == 0x61):
                return device_info
        return None
    
    def connect(self) -> bool:
        """Connect to the keyboard HID device."""
        if not HID_AVAILABLE:
            print("HID library not available")
            return False
        
        device_info = self.find_device()
        if not device_info:
            print("Keyboard not found (no QMK Raw HID interface on usage page 0xFF60)")
            return False
        
        try:
            self.device = hid.Device(path=device_info['path'])
            
            # Get device info
            manufacturer = self.device.manufacturer
            product = self.device.product
            
            print(f"Connected to {manufacturer} {product}")
            return True
            
        except Exception as e:
            print(f"Failed to connect to keyboard: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the device."""
        if self.device:
            try:
                self.device.__exit__(None, None, None)
            except:
                pass
            self.device = None
    
    def send_command(self, command: str, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """Send a command and wait for response."""
        if not self.device:
            if not self.connect():
                return None
        
        try:
            # Prepare message: [ID1, ID2, command, ETX]
            message = command.encode('utf-8') + bytes([self.ETX_TERMINATOR])
            packet = bytes([self.FIELD_KIT_ID1, self.FIELD_KIT_ID2]) + message
            
            # Pad packet to match HID report size (typically 32 or 64 bytes)
            report_size = 32  # Common size for raw HID reports
            if len(packet) < report_size:
                packet += b'\x00' * (report_size - len(packet))
            elif len(packet) > report_size:
                packet = packet[:report_size]
            
            # Send the packet (convert to bytes if needed)
            if isinstance(packet, list):
                packet = bytes(packet)
            self.device.write(packet)
            
            # Wait for response
            start_time = time.time()
            while time.time() - start_time < timeout:
                response = self.device.read(report_size, timeout=100)
                
                if response and len(response) > 0:
                    # Parse response
                    status = response[0]
                    message_bytes = bytes(response[1:]).rstrip(b'\x00')
                    message = message_bytes.decode('utf-8', errors='ignore')
                    
                    return {
                        'status': status,
                        'message': message,
                        'success': status in [self.RESPONSE_OK, self.RESPONSE_BOOTLOADER_TRIGGERED, self.RESPONSE_INFO]
                    }
            
            return {'status': self.RESPONSE_ERROR, 'message': 'Timeout', 'success': False}
            
        except Exception as e:
            # Special handling for bootloader command - disconnection is expected success
            if command == "BOOTLOADER":
                error_msg = str(e).lower()
                if any(word in error_msg for word in ['success', 'disconnect', 'device', 'hid']):
                    return {'status': self.RESPONSE_BOOTLOADER_TRIGGERED, 'message': 'Device entering bootloader', 'success': True}
            
            print(f"Communication error: {e}")
            return {'status': self.RESPONSE_ERROR, 'message': str(e), 'success': False}
    
    def trigger_bootloader(self) -> bool:
        """Trigger bootloader mode."""
        print("Sending bootloader command via HID...")
        
        response = self.send_command("BOOTLOADER")
        
        if response and response['success']:
            print("✓ HID bootloader command sent successfully")
            return True
        else:
            print(f"Bootloader command failed: {response['message'] if response else 'No response'}")
            return False
    
    def get_firmware_info(self) -> Optional[Dict[str, str]]:
        """Get firmware information."""
        response = self.send_command("FIRMWARE_INFO")
        
        if response and response['success']:
            # Parse key=value pairs separated by |
            info = {}
            parts = response['message'].split('|')
            for part in parts:
                if '=' in part:
                    key, value = part.split('=', 1)
                    info[key] = value
            return info
        
        return None
    
    def get_side_info(self) -> Optional[Dict[str, str]]:
        """Get keyboard side information."""
        response = self.send_command("SIDE_INFO")
        
        if response and response['success']:
            # Parse key=value pairs separated by |
            info = {}
            parts = response['message'].split('|')
            for part in parts:
                if '=' in part:
                    key, value = part.split('=', 1)
                    info[key] = value
            return info
        
        return None
    
    def ping(self) -> bool:
        """Test communication with the device."""
        response = self.send_command("STATUS")
        return response and response['success']


def test_hid_communication():
    """Test HID communication with the keyboard."""
    comm = HIDCommunicator()
    
    if comm.connect():
        print("Testing HID communication...")
        
        # Test ping
        if comm.ping():
            print("✓ Communication test passed")
        else:
            print("✗ Communication test failed")
        
        # Get firmware info
        fw_info = comm.get_firmware_info()
        if fw_info:
            print("Firmware info:", fw_info)
        
        # Get side info  
        side_info = comm.get_side_info()
        if side_info:
            print("Side info:", side_info)
        
        comm.disconnect()
    else:
        print("Failed to connect to keyboard")


if __name__ == "__main__":
    test_hid_communication()