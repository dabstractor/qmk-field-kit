# QMK Field Kit

A modular Python replacement for QMK's `flash.sh` script that automatically detects keyboard features, handles bootloader entry, and manages split keyboard flashing.

## Features

- **Automatic Feature Detection**: Parses `keyboard.json` and `rules.mk` to detect split keyboards, bootloaders, and MCU types
- **Smart Bootloader Entry**: Automatically enters bootloader mode via serial commands (RP2040) with fallback to manual mode
- **Cross-Platform Support**: Works on Linux (including Arch), macOS, and Windows (via WSL)
- **Split Keyboard Aware**: Automatically handles left/right side selection and appropriate flash commands
- **Modular Architecture**: Easy to extend for new MCUs and bootloader types

## Installation

The package is self-contained and uses only Python 3.8+ standard library (except for `pyserial` for bootloader communication).

```bash
# Install pyserial if not already installed
pip install pyserial
```

## Usage

### Basic Flashing

```bash
# Flash right side (default)
python -m qmk_field_kit

# Flash left side  
python -m qmk_field_kit left

# Flash specific keyboard
python -m qmk_field_kit right --keyboard handwired/dactyl_manuform/5x7_1
```

### Information and Diagnostics

```bash
# Show keyboard information
python -m qmk_field_kit --info

# Validate environment
python -m qmk_field_kit --validate

# Enter bootloader mode only
python -m qmk_field_kit --bootloader
```

### Direct Module Usage

```bash
# Run the main CLI module directly
python qmk_field_kit/cli.py left

# Or make it executable and run directly
chmod +x qmk_field_kit/cli.py
./qmk_field_kit/cli.py left
```

## Architecture

### Core Modules

- **`features.py`**: Parses `keyboard.json` and `rules.mk` to detect enabled features
- **`bootloader.py`**: Handles MCU-specific bootloader entry (RP2040, AVR, ARM)  
- **`flash.py`**: Manages side selection and platform-specific flash commands
- **`cli.py`**: Command-line interface and main entry point

### Supported MCUs

- **RP2040**: Serial bootloader entry, UF2 flashing
- **AVR**: Standard bootloaders (DFU, Caterina, etc.)
- **ARM**: STM32 and similar ARM-based MCUs

### Platform Support

- **Linux**: Full support including Arch Linux optimizations
- **macOS**: Uses `picotool` for RP2040, standard QMK flash for others
- **Windows/WSL**: Generic QMK flash commands

## Integration

### Replacing flash.sh

To replace the existing `flash.sh` with this Python implementation:

```bash
# Backup original
cp flash.sh flash.sh.backup

# Create new wrapper (done automatically by installation)
cat > flash.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/keyboards/handwired/dactyl_manuform/5x7_1/qmk-field-kit"
python -m qmk_field_kit "$@"
EOF

chmod +x flash.sh
```

### Module Import

```python
from qmk_field_kit import get_features, flash_keyboard, enter_bootloader

# Get keyboard features
features = get_features()
print(f"Split keyboard: {features['split_enabled']}")

# Flash keyboard
success = flash_keyboard('left')

# Enter bootloader only
enter_bootloader('rp2040', 'serial')
```

## Configuration

The tool reads configuration from:

1. **QMK Config**: `qmk config user.keyboard` and `qmk config user.keymap`
2. **Keyboard JSON**: `keyboards/{keyboard}/keyboard.json`
3. **Rules MK**: `keyboards/{keyboard}/rules.mk` and included files

No separate configuration file is needed - `keyboard.json` and `rules.mk` are the single source of truth.

## Troubleshooting

### Serial Permission Issues (Linux)

```bash
# Add user to dialout group
sudo usermod -a -G dialout $USER
# Log out and back in
```

### macOS picotool Missing

```bash
brew install picotool
```

### Bootloader Detection Issues

If automatic bootloader entry fails:
1. Use `--bootloader` flag to test bootloader entry only
2. Check serial port permissions
3. Manually enter bootloader mode (BOOT + RESET)
4. Use `--verbose` flag for detailed output

## Extending

### Adding New MCU Support

Add new MCU family to `bootloader.py`:

```python
def _enter_new_mcu_bootloader(self):
    # Implementation for new MCU
    pass
```

### Adding New Platform Support

Extend platform detection in `flash.py`:

```python
def _build_new_platform_commands(self, features, side):
    # Platform-specific command building
    pass
```