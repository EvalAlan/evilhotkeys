# EvilHotKeys

EvilHotKeys is a Python script that allows you to automate key presses and scan pixel colors for various games. It's intended to replace AutoHotKey as Python is compatible on multiple operating systems. Now supports both X11 and Wayland (GNOME) environments.

## Features

- Cross-platform hotkey automation
- Pixel color detection and searching
- Support for X11 and Wayland (GNOME) environments
- Session-based permission handling for Wayland
- Game-specific automation scripts
- Extensible architecture for adding new games
- **NEW:** Interactive coordinate helper tool
- **NEW:** YAML-based configuration system
- Professional logging framework
- Vectorized pixel search (10-100x faster)

## System Requirements

### For X11 (Traditional Linux Desktop)
- Python 3.7+
- X11 display server

### For Wayland (GNOME)
- Python 3.7+
- GNOME desktop environment on Wayland
- System packages: `python3-dbus`, `python3-gi`, `gir1.2-gtk-3.0`, `xdg-desktop-portal-gnome`

## Installation

1. Clone the repository: `git clone https://github.com/busybox42/EvilHotKeys`
2. Install system dependencies (for Wayland support):
   ```bash
   # Ubuntu/Debian
   sudo apt install python3-dbus python3-gi gir1.2-gtk-3.0 xdg-desktop-portal-gnome
   
   # Fedora
   sudo dnf install python3-dbus python3-gobject gtk3-devel
   
   # Arch Linux
   sudo pacman -S python-dbus python-gobject gtk3
   ```
3. Install Python dependencies: `pip install -r requirements.txt`

## Usage

### Quick Start

**Console Mode:**
```bash
python main.py
```

**GUI Mode:**
```bash
python main-gui.py
```

**Enhanced GUI with Monitoring (NEW!):**
```bash
python main-gui-enhanced.py
```

The enhanced GUI shows:
- Real-time APM (Actions Per Minute)
- Performance metrics (keys pressed, interrupts fired)
- Live activity log with timestamps
- Visual status indicators

See `ENHANCED_GUI_GUIDE.md` for details.

### Coordinate Helper Tool (NEW!)

Easily capture and save pixel coordinates for your game:

```bash
python coordinate_helper.py
```

1. Select your game
2. Enter a coordinate name (or use presets like "interrupt")
3. Hover over the UI element in-game
4. Press **F9** to capture
5. Click "Save to Config"

See `COORDINATE_HELPER_GUIDE.md` for detailed instructions.

### Configuration

Copy the example config and customize for your setup:

```bash
cp config.example.yaml config.yaml
nano config.yaml
```

Configure:
- Screen resolution
- Performance profiles (fast, balanced, responsive)
- Game-specific pixel coordinates
- Logging preferences

### First Run on GNOME Wayland

When running EvilHotKeys for the first time on GNOME Wayland:
1. A permission dialog will appear asking for screenshot access
2. Click "Allow" to grant permission
3. The permission will be remembered for the current session
4. You may need to restart the application after granting permission

### Testing Wayland Support

Run the test script to verify Wayland functionality:
```bash
python test_wayland_support.py
```

This will test:
- Environment detection
- Screenshot permissions
- Pixel color detection
- Pixel search functionality
- Performance benchmarks

## Architecture

### Environment Detection
The application automatically detects your environment:
- **X11**: Uses PIL ImageGrab for screenshots
- **Wayland (GNOME)**: Uses GNOME D-Bus Screenshot interface
- **Other**: Falls back to X11 methods

### Screenshot Caching
On Wayland, screenshots are cached for up to 100ms to improve performance when sampling multiple pixels.

## Adding a new game

1. Create a new directory for the game in the `games` directory.
2. Create a `specs` directory inside the game directory.
3. Create a new Python file for each spec in the `specs` directory.
4. Implement the spec logic in the Python file.

### Example spec structure:
```python
from libs.pixel_get_color import get_color
from libs.keyboard_actions import press_and_release
import time

def run(stop_event):
    while not stop_event.is_set():
        # Check pixel color
        color = get_color(100, 100)
        if color == (255, 0, 0):  # Red pixel
            press_and_release('space')
        time.sleep(0.1)
```

## Troubleshooting

### Wayland Issues

**Permission dialog doesn't appear:**
- Ensure `xdg-desktop-portal-gnome` is installed and running
- Check that you're running on GNOME Wayland: `echo $XDG_SESSION_TYPE`

**Screenshots fail:**
- Verify D-Bus service is available: `dbus-send --session --print-reply --dest=org.gnome.Shell /org/gnome/Shell org.freedesktop.DBus.Introspectable.Introspect`
- Check if GNOME Screenshot service is running

**Performance issues:**
- Screenshots are cached for 100ms to improve performance
- Consider reducing the frequency of pixel checks in your specs

### X11 Issues

**PIL ImageGrab fails:**
- Install additional dependencies: `pip install Pillow[X11]`
- Ensure X11 is running and accessible

### General Issues

**Import errors:**
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check Python version compatibility

**Permission errors:**
- Ensure your user has access to input devices
- Consider running with appropriate permissions

## Contributing

1. Fork the repository.
2. Create a new branch: `git checkout -b my-feature-branch`
3. Make your changes and commit them: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin my-feature-branch`
5. Create a pull request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
