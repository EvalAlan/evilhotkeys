from PIL import ImageGrab
import numpy as np
from libs.environment import is_gnome_wayland, check_gnome_screenshot_support
from libs.logger import get_logger

logger = get_logger('pixel_search')

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

def pixel_search(color, x1, y1, x2, y2):
    """Search for a pixel of a specific color in a region of the screen.
    
    Uses vectorized numpy operations for significantly better performance
    compared to nested loops.
    
    Args:
        color: Target color as (R, G, B) tuple
        x1, y1: Top-left corner of search region
        x2, y2: Bottom-right corner of search region
    
    Returns:
        Tuple of (x, y) coordinates if found, None otherwise
    """
    try:
        image = None
        
        # Use Wayland/GNOME backend if available
        if _get_wayland_support():
            gnome_manager = _get_gnome_manager()
            if gnome_manager:
                image = gnome_manager.get_region_screenshot(x1, y1, x2, y2)
        
        # Fall back to X11 backend if no image yet
        if image is None:
            image = ImageGrab.grab(bbox=(x1, y1, x2, y2))
        
        if image is None:
            return None
        
        # Convert the image to a numpy array for faster processing
        image_np = np.array(image)
        
        # Vectorized search: create boolean mask where all RGB channels match
        # This is MUCH faster than nested loops
        matches = np.all(image_np == color, axis=-1)
        
        # Find coordinates of matches
        coords = np.argwhere(matches)
        
        if len(coords) > 0:
            # Return the first match (top-left most)
            y, x = coords[0]
            return (x1 + int(x), y1 + int(y))
        
        # If no matching pixel is found, return None
        return None
    except Exception as e:
        logger.error(f"Error during pixel search: {e}")
        return None
