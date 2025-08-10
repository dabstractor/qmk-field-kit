#!/usr/bin/env python3

import json
import re
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional


class FeatureDetector:
    """Parses QMK configuration to detect enabled features."""

    def __init__(self):
        self.qmk_root = self._find_qmk_root()

    def _find_qmk_root(self) -> Path:
        """Find QMK firmware root directory."""
        current = Path.cwd()
        while current.parent != current:
            if (current / "quantum").is_dir() and (current / "keyboards").is_dir():
                return current
            current = current.parent
        return Path.cwd()

    def get_current_keyboard(self) -> str:
        """Get currently selected keyboard from qmk config."""
        try:
            result = subprocess.run(['qmk', 'config', 'user.keyboard'],
                                  capture_output=True, text=True, check=True)
            return result.stdout.strip().split('=')[1]
        except (subprocess.CalledProcessError, IndexError):
            raise RuntimeError("Could not determine current keyboard from qmk config")

    def get_keyboard_path(self, keyboard: Optional[str] = None) -> Path:
        """Get path to keyboard directory."""
        if keyboard is None:
            keyboard = self.get_current_keyboard()
        return self.qmk_root / "keyboards" / keyboard

    def parse_keyboard_json(self, keyboard_path: Path) -> Dict[str, Any]:
        """Parse keyboard.json file."""
        keyboard_json = keyboard_path / "keyboard.json"
        if not keyboard_json.exists():
            return {}

        with open(keyboard_json, 'r') as f:
            return json.load(f)

    def parse_rules_mk(self, keyboard_path: Path) -> Dict[str, str]:
        """Parse rules.mk file for KEY=VALUE pairs."""
        rules_mk = keyboard_path / "rules.mk"
        features = {}

        if not rules_mk.exists():
            return features

        with open(rules_mk, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                # Handle include statements
                if line.startswith('include '):
                    include_path = line.split(' ', 1)[1]
                    include_full_path = keyboard_path / include_path
                    if include_full_path.exists():
                        included_features = self.parse_rules_mk(include_full_path.parent)
                        features.update(included_features)
                    continue

                # Parse KEY = VALUE pairs
                if '=' in line:
                    key, value = line.split('=', 1)
                    features[key.strip()] = value.strip()

        return features

    def detect_features(self, keyboard: Optional[str] = None) -> Dict[str, Any]:
        """Detect all features for the specified keyboard."""
        keyboard_path = self.get_keyboard_path(keyboard)

        # Parse both keyboard.json and rules.mk
        json_config = self.parse_keyboard_json(keyboard_path)
        rules_config = self.parse_rules_mk(keyboard_path)

        # Combine and normalize features
        features = {
            'keyboard': keyboard or self.get_current_keyboard(),
            'keyboard_path': str(keyboard_path),
            'bootloader': json_config.get('bootloader', 'unknown'),
            'split_enabled': json_config.get('split', {}).get('enabled', False),
            'features': json_config.get('features', {}),
            'rules_mk': rules_config,
            'transport_protocol': None,
            'mcu_family': None,
            'auto_bootloader': rules_config.get('AUTO_BOOTLOADER_ENABLE', 'no').lower() == 'yes',
            'side_lock_enabled': rules_config.get('SIDE_LOCK_ENABLE', 'no').lower() == 'yes'
        }

        # Detect transport protocol for split keyboards
        if features['split_enabled']:
            split_config = json_config.get('split', {})
            transport = split_config.get('transport', {})
            features['transport_protocol'] = transport.get('protocol', 'serial')

        # Detect MCU family from bootloader
        bootloader = features['bootloader']
        if bootloader in ['rp2040']:
            features['mcu_family'] = 'rp2040'
        elif bootloader in ['atmel-dfu', 'caterina', 'halfkay']:
            features['mcu_family'] = 'avr'
        elif bootloader in ['stm32-dfu', 'stm32duino']:
            features['mcu_family'] = 'arm'

        return features


def get_features(keyboard: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function to get features for a keyboard."""
    detector = FeatureDetector()
    return detector.detect_features(keyboard)


if __name__ == "__main__":
    features = get_features()
    import pprint
    pprint.pprint(features)
