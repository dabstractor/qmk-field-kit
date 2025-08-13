# QMK Field Kit

A modular Python replacement for QMK's `flash.sh` script that automatically detects keyboard features, handles bootloader entry, and manages split keyboard flashing with advanced features like side lock protection.

## Features

- **Automatic Feature Detection**: Parses `keyboard.json` and `rules.mk` to detect split keyboards, bootloaders, and MCU types
- **Auto Bootloader**: Automatically triggers bootloader mode after compilation for seamless flashing
- **Side Lock Protection**: Prevents accidentally flashing the wrong side of a split keyboard
- **Cross-Platform Support**: Works on Linux (including Arch), macOS, and Windows (via WSL)
- **Split Keyboard Aware**: Automatically handles left/right side selection and appropriate flash commands
- **Modular Architecture**: Easy to extend for new MCUs and bootloader types

## Installation

### 1. Add as Git Submodule

Navigate to your QMK firmware root directory and add QMK Field Kit as a submodule in your keyboard directory:

```bash
# Adjust the keyboard path to point to your keyboard
git submodule add https://github.com/dabstractor/qmk-field-kit keyboards/[YOUR/KEYBOARD]/qmk-field-kit
```

### 2. Install Dependencies

QMK Field Kit uses only Python 3.8+ standard library except for HID communication:

```bash
# Install dependencies for HID bootloader communication
pip install -r requirements.txt
```


### Enable Features in rules.mk

Add the following to your keyboard's `rules.mk` file to enable QMK Field Kit features:

```makefile
# QMK Field Kit Features
AUTO_BOOTLOADER_ENABLE = yes    # Enable automatic bootloader triggering
SIDE_LOCK_ENABLE = yes          # Enable side lock protection (split keyboards only)
```

### Include Field Kit in Your Keymap

Add the following to your keymap's `keymap.c`:

```c
#include QMK_KEYBOARD_H
#include "../qmk-field-kit/field_kit.h"

// ... your keymap code ...

// Add this to handle HID communication
void raw_hid_receive(uint8_t *data, uint8_t length) {
    field_kit_process_message(data, length);
}
```


### 3. (Optional) Create Wrapper Script

For convenience, add this `flash` script at the root of your QMK repository:

```bash
#!/bin/bash

# QMK Field Kit Flash Wrapper
# Python-based replacement for the original flash.sh

# Extract keyboard and keymap from QMK config
KEYBOARD=$(qmk config user.keyboard | cut -d'=' -f2)
KEYMAP=$(qmk config user.keymap | cut -d'=' -f2)

# Validate that we got the config values
if [ -z "$KEYBOARD" ] || [ -z "$KEYMAP" ]; then
    echo "Error: Could not extract keyboard or keymap from QMK config"
    echo "Please ensure QMK is properly configured with 'qmk config user.keyboard=<keyboard>' and 'qmk config user.keymap=<keymap>'"
    exit 1
fi

# Navigate to the QMK Field Kit directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIELD_KIT_DIR="$SCRIPT_DIR/keyboards/$KEYBOARD/qmk-field-kit"

# Check if QMK Field Kit exists
if [ ! -d "$FIELD_KIT_DIR" ]; then
    echo "Error: QMK Field Kit not found at $FIELD_KIT_DIR"
    echo "Please ensure the qmk-field-kit directory exists and contains the Python modules."
    exit 1
fi

# Change to field kit directory
cd "$FIELD_KIT_DIR"

# Run the Python module with all arguments passed through
python3 -m qmk_field_kit "$@"
```

And make it executable:
```bash
chmod +x flash
```

## Usage

### Basic Flashing

```bash
# First run
./flash left --force   # Sets initial left side state
./flash right --force  # Sets initial right side state

# Subsequent runs (side auto-detected)
./flash

# Flash specific side (no need to ever run these, but they are here)
./flash left   # Will fail if attempting to flash right side
./flash right  # Will fail if attempting to flash left side
```

### Information and Diagnostics

```bash
# Show keyboard information and enabled features
./flash --info

# Validate environment and dependencies
./flash --validate

# Test HID communication with keyboard
./flash --hid-test

# Enter bootloader mode only (no flashing)
./flash --bootloader
```

### Advanced Usage

```bash
# Flash specific keyboard (override QMK config)
./flash left --keyboard handwired/dactyl_manuform/5x7

# Verbose output for debugging
./flash right --verbose
```

## Features

### Auto Bootloader (`AUTO_BOOTLOADER_ENABLE = yes`)

When enabled, QMK Field Kit:
1. Compiles your firmware first
2. Automatically triggers bootloader mode via HID commands
3. Flashes the compiled firmware
4. No manual bootloader entry required!

**Benefits:**
- Seamless one-command flashing
- No need to press BOOT+RESET buttons
- Works with RP2040 keyboards (others coming soon)

### Side Lock (`SIDE_LOCK_ENABLE = yes`)

Prevents accidentally flashing the wrong side of a split keyboard by:
1. Querying the keyboard via HID to determine current side configuration
2. Blocking cross-side flashing attempts
3. Providing clear error messages and override options

### Supported MCUs

- **RP2040**: HID bootloader entry, UF2 flashing
- **AVR**: Standard bootloaders (DFU, Caterina, etc.) - *coming soon*
- **ARM**: STM32 and similar ARM-based MCUs - *coming soon*

### Platform Support

- **Linux**: Full support including Arch Linux optimizations
- **macOS**: Uses `picotool` for RP2040, standard QMK flash for others
- **Windows/WSL**: Generic QMK flash commands

## Examples

### Complete Setup Example

For a `handwired/dactyl_manuform/5x7_1` keyboard:

1. **Add submodule:**
```bash
git submodule add https://github.com/dabstractor/qmk-field-kit keyboards/[path/to/your/keyboard]/qmk-field-kit
```

2. **Update `keyboards/handwired/dactyl_manuform/5x7_1/rules.mk`:**
```makefile
AUTO_BOOTLOADER_ENABLE = yes
SIDE_LOCK_ENABLE = yes
```

3. **Update your `keymap.c`:**
```c
#include "./qmk-field-kit/field_kit.h"

void raw_hid_receive(uint8_t *data, uint8_t length) {
    field_kit_process_message(data, length);
}
```

4. **Create root `flash` script** (use the script from the Installation section)

5. **Set up QMK config (if not already done):**
```bash
qmk config user.keyboard=handwired/dactyl_manuform/5x7
qmk config user.keymap=default  # or your keymap name
```

6. **Flash your keyboard:**
```bash
./flash left   # First time setup - flash left side
./flash right  # First time setup - flash right side
./flash        # After setup - auto-detects side
```

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
1. Use `./flash --bootloader` to test bootloader entry only
2. Check serial port permissions
3. Manually enter bootloader mode (BOOT + RESET)
4. Use `./flash --verbose` for detailed output

### Side Lock Issues

If side lock isn't working:
1. Ensure you don't have `RAW_HID_ENABLE = no` in `rules.mk`
2. Verify `field_kit_process_message()` is in `raw_hid_receive()`
3. Test with `./flash --hid-test`
4. Use `./flash --force` to bypass for initial setup

## Development

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

### Extending Support

See the existing modules for examples of adding:
- New MCU families (`bootloader.py`)
- New platform support (`flash.py`)
- Additional features (`features.py`)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

[License information here]

## Changelog

### v1.0.0
- Initial release
- RP2040 support with HID bootloader entry
- Side lock protection for split keyboards
- Auto bootloader feature
- Cross-platform support (Linux, macOS, Windows/WSL)
