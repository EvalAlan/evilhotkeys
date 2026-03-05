import os
import subprocess

def is_wayland():
    """Check if we're running under Wayland"""
    return os.environ.get('WAYLAND_DISPLAY') is not None

def is_gnome():
    """Check if we're running under GNOME"""
    desktop = os.environ.get('XDG_CURRENT_DESKTOP', '').lower()
    return 'gnome' in desktop

def is_gnome_wayland():
    """Check if we're running under GNOME on Wayland"""
    return is_wayland() and is_gnome()

def check_gnome_screenshot_support():
    """Check if GNOME screenshot D-Bus interface is available"""
    try:
        result = subprocess.run([
            'dbus-send', '--session', '--print-reply',
            '--dest=org.gnome.Shell',
            '/org/gnome/Shell',
            'org.freedesktop.DBus.Introspectable.Introspect'
        ], capture_output=True, text=True, timeout=5)
        
        return 'org.gnome.Shell.Screenshot' in result.stdout
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        return False

def get_environment_info():
    """Get information about the current environment"""
    return {
        'is_wayland': is_wayland(),
        'is_gnome': is_gnome(),
        'is_gnome_wayland': is_gnome_wayland(),
        'gnome_screenshot_support': check_gnome_screenshot_support() if is_gnome_wayland() else False,
        'wayland_display': os.environ.get('WAYLAND_DISPLAY'),
        'desktop': os.environ.get('XDG_CURRENT_DESKTOP'),
        'session_type': os.environ.get('XDG_SESSION_TYPE')
    } 