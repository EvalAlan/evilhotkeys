"""
Helper utilities for World of Warcraft specs
Handles coordinate loading from config with fallbacks
"""
from libs.config_manager import get_config_manager
from libs.logger import get_logger

logger = get_logger('wow_helpers')
config = get_config_manager()


# Fallback coordinates for different resolutions if not in config
FALLBACK_COORDS = {
    '1920x1080': {
        'interrupt': (2460, 1015),
        'health_75': (2554, 1000),
        'health_50': (2483, 1000),
        'health_35': (2506, 1000),
        'health_25': (2533, 1000),
        'focus_health': (2345, 915),
        'health_below_50': (2375, 995),
        'pally_interrupt': (2505, 945),
        'pally_health_3': (2505, 975),
        'pally_health_4': (2530, 975),
        'pally_health_5': (2550, 975),
        'pally_health_6': (2575, 975),
        'druid_interrupt': (2345, 875),
        'druid_finish': (2378, 878),
    },
    '5760x1080': {
        'interrupt': (2460, 1015),
        'health_75': (2554, 1000),
        'health_50': (2483, 1000),
        'health_35': (2506, 1000),
        'health_25': (2533, 1000),
        'focus_health': (2345, 915),
        'health_below_50': (2375, 995),
        'pally_interrupt': (2505, 945),
        'pally_health_3': (2505, 975),
        'pally_health_4': (2530, 975),
        'pally_health_5': (2550, 975),
        'pally_health_6': (2575, 975),
        'druid_interrupt': (2345, 875),
        'druid_finish': (2378, 878),
    }
}


def get_coord(coord_name, default=None):
    """Get a coordinate from config or fallback.
    
    Args:
        coord_name: Name of coordinate (e.g., 'interrupt', 'health_50')
        default: Default coordinate if not found (x, y) tuple
    
    Returns:
        Tuple of (x, y) coordinates
    """
    # Try to get from config first
    coords = config.get_pixel_coords('World of Warcraft', coord_name)
    if coords:
        logger.debug(f"Using config coordinate for {coord_name}: {coords}")
        return coords
    
    # Try fallback based on resolution
    resolution = config.get('display.resolution', '1920x1080')
    if resolution in FALLBACK_COORDS and coord_name in FALLBACK_COORDS[resolution]:
        coords = FALLBACK_COORDS[resolution][coord_name]
        logger.debug(f"Using fallback coordinate for {coord_name}: {coords}")
        return coords
    
    # Use provided default
    if default:
        logger.warning(f"Using default coordinate for {coord_name}: {default}")
        return default
    
    # Last resort - return a safe coordinate
    logger.error(f"No coordinate found for {coord_name}, using (0, 0)")
    return (0, 0)


def get_coords(*coord_names):
    """Get multiple coordinates at once.
    
    Args:
        *coord_names: Variable number of coordinate names
    
    Returns:
        List of (x, y) tuples in the same order as requested
    
    Example:
        interrupt, health50, health35 = get_coords('interrupt', 'health_50', 'health_35')
    """
    return [get_coord(name) for name in coord_names]


def log_coords_once(coords_dict):
    """Log coordinates once at startup for debugging.
    
    Args:
        coords_dict: Dictionary of {name: (x, y)} coordinates
    """
    logger.info("Loaded coordinates:")
    for name, (x, y) in coords_dict.items():
        logger.info(f"  {name:20} = ({x:4}, {y:4})")

