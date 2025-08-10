"""
QMK Field Kit - Advanced flashing utility for QMK keyboards

A modular Python replacement for QMK's flash.sh script that automatically
detects keyboard features, handles bootloader entry, and manages split
keyboard flashing.

Modules:
- features: Parse keyboard.json and rules.mk to detect enabled features
- bootloader: Handle MCU-specific bootloader entry methods
- flash: Manage side selection and firmware flashing logic
- cli: Command-line interface and main entry point
"""

__version__ = "1.0.0"
__author__ = "QMK Field Kit"

from .features import get_features, FeatureDetector
from .bootloader import enter_bootloader, BootloaderManager
from .flash import flash_keyboard, FlashManager
from .cli import main

__all__ = [
    'get_features',
    'FeatureDetector', 
    'enter_bootloader',
    'BootloaderManager',
    'flash_keyboard',
    'FlashManager',
    'main'
]