from PIL import ImageGrab
from libs.environment import is_gnome_wayland, check_gnome_screenshot_support
from libs.logger import get_logger

logger = get_logger('pixel_get_color')

# Wayland/GNOME support
_gnome_manager = None
_wayland_supported = None

def _get_wayland_support():
    """Check if Wayland support is available"""
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

def get_color(x, y, img=None):
    """Get the color of a pixel at the specified coordinates
    
    Args:
        x: X coordinate
        y: Y coordinate  
        img: Optional image to use (for X11 only)
    
    Returns:
        Tuple of (R, G, B) values or None if error
    """
    try:
        # Use Wayland/GNOME backend if available
        if _get_wayland_support():
            gnome_manager = _get_gnome_manager()
            if gnome_manager:
                return gnome_manager.get_pixel_color(x, y)
        
        # Fall back to X11 backend
        if img is None:
            img = ImageGrab.grab()
        return img.getpixel((x, y))
    except Exception as e:
        logger.error(f"Error getting pixel color at ({x}, {y}): {e}")
        return None

def get_multiple_pixel_colors(coordinates):
    """Get colors of multiple pixels efficiently
    
    Args:
        coordinates: List of (x, y) tuples
    
    Returns:
        List of (R, G, B) tuples
    """
    # Use Wayland/GNOME backend if available
    if _get_wayland_support():
        gnome_manager = _get_gnome_manager()
        if gnome_manager:
            # Use optimized method for multiple pixels
            return gnome_manager.get_multiple_pixel_colors(coordinates)
    
    # Fall back to X11 backend
    colors = []
    try:
        img = ImageGrab.grab()
        for (x, y) in coordinates:
            color = get_color(x, y, img)
            if color is not None:
                colors.append(color)
    except Exception as e:
        logger.error(f"Error getting multiple pixel colors: {e}")
    
    return colors
