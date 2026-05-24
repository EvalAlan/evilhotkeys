from PIL import ImageGrab, Image
import time

from libs.environment import is_gnome_wayland, check_gnome_screenshot_support, is_wayland
from libs.logger import get_logger

logger = get_logger('pixel_get_color')

# Wayland/GNOME support
_gnome_manager = None
_wayland_supported = None

# Generic screenshot cache/backoff for all backends
_cached_screenshot = None
_cached_at = 0.0
_cache_duration = None
_consecutive_failures = 0
_next_retry_ts = 0.0
_logged_backend = None

# Optional X11 backend (faster + avoids repeated external screenshot process churn)
try:
    import mss
except Exception:
    mss = None


def _get_cache_duration():
    """Read screenshot cache duration from config manager once, fallback to default."""
    global _cache_duration
    if _cache_duration is None:
        _cache_duration = 0.5
        try:
            from libs.config_manager import get_config_manager
            cfg = get_config_manager()
            _cache_duration = float(cfg.get('performance.screenshot_cache_duration', 0.5))
        except Exception:
            pass
    return _cache_duration


def _get_wayland_support():
    """Check if GNOME Wayland screenshot D-Bus support is available"""
    global _wayland_supported
    if _wayland_supported is None:
        _wayland_supported = is_gnome_wayland() and check_gnome_screenshot_support()
    return _wayland_supported


def _get_gnome_manager():
    """Get the GNOME screenshot manager"""
    global _gnome_manager
    if _gnome_manager is None and _get_wayland_support():
        try:
            from libs.gnome_screenshot import get_gnome_screenshot_manager
            _gnome_manager = get_gnome_screenshot_manager()
        except ImportError as e:
            logger.error(f"Failed to import GNOME screenshot support: {e}")
            logger.info("Install required dependencies: dbus-python PyGObject")
    return _gnome_manager


def _log_backend_once(name):
    global _logged_backend
    if _logged_backend != name:
        _logged_backend = name
        logger.info(f"Pixel capture backend: {name}")


def _capture_x11_with_mss():
    if mss is None:
        raise RuntimeError("mss backend unavailable")
    with mss.mss() as sct:
        # Monitor 0 is the full virtual desktop
        shot = sct.grab(sct.monitors[0])
        return Image.frombytes('RGB', shot.size, shot.rgb)


def _capture_with_pillow():
    return ImageGrab.grab()


def _capture_screenshot():
    """Capture one screenshot with backend selection + fallback."""
    # GNOME Wayland optimized path first
    if _get_wayland_support():
        gnome_manager = _get_gnome_manager()
        if gnome_manager:
            _log_backend_once('gnome-wayland-dbus')
            return gnome_manager.get_screenshot(force_new=True)

    # X11: prefer mss (fast, no Qt/spectacle dependency)
    if not is_wayland() and mss is not None:
        try:
            _log_backend_once('x11-mss')
            return _capture_x11_with_mss()
        except Exception as e:
            logger.debug(f"mss capture failed, falling back to PIL.ImageGrab: {e}")

    # Generic fallback (X11 or non-GNOME Wayland)
    _log_backend_once('pillow-imagegrab')
    return _capture_with_pillow()


def _get_screenshot(force_new=False):
    """Get a screenshot with cache and failure backoff."""
    global _cached_screenshot, _cached_at, _consecutive_failures, _next_retry_ts

    now = time.time()
    cache_duration = _get_cache_duration()

    if (not force_new and _cached_screenshot is not None and (now - _cached_at) < cache_duration):
        return _cached_screenshot

    if now < _next_retry_ts:
        return None

    try:
        img = _capture_screenshot()
        _cached_screenshot = img
        _cached_at = time.time()
        _consecutive_failures = 0
        _next_retry_ts = 0.0
        return img
    except Exception as e:
        _consecutive_failures += 1
        # Exponential backoff capped at 2s
        backoff = min(0.1 * (2 ** min(_consecutive_failures, 4)), 2.0)
        _next_retry_ts = now + backoff
        logger.error(f"Screenshot capture failed (attempt {_consecutive_failures}, backoff {backoff:.2f}s): {e}")
        return None


def get_color(x, y, img=None):
    """Get the color of a pixel at the specified coordinates.

    Args:
        x: X coordinate
        y: Y coordinate
        img: Optional image to use

    Returns:
        Tuple of (R, G, B) values or None if error
    """
    try:
        if img is None:
            img = _get_screenshot()
        if img is None:
            return None
        return img.getpixel((x, y))
    except Exception as e:
        logger.error(f"Error getting pixel color at ({x}, {y}): {e}")
        return None


def get_multiple_pixel_colors(coordinates):
    """Get colors of multiple pixels efficiently using one screenshot.

    Args:
        coordinates: List of (x, y) tuples

    Returns:
        List of (R, G, B) tuples or None entries (same length as input)
    """
    img = _get_screenshot()
    if img is None:
        return [None] * len(coordinates)

    colors = []
    for (x, y) in coordinates:
        try:
            colors.append(img.getpixel((x, y)))
        except Exception as e:
            logger.error(f"Error getting pixel color at ({x}, {y}): {e}")
            colors.append(None)

    return colors
