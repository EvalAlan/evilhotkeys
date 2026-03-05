"""
Configuration module for EvilHotKeys performance tuning
DEPRECATED: Use libs.config_manager.ConfigManager instead

This module is kept for backward compatibility but delegates to config_manager.
"""
from libs.logger import get_logger
from libs.config_manager import get_config_manager

logger = get_logger('config')

# Get config manager instance
_config = get_config_manager()

# Legacy compatibility - expose as module-level variables
SCREENSHOT_CACHE_DURATION = _config.get('performance.screenshot_cache_duration', 0.5)
DEBUG_TIMING = _config.get('performance.debug_timing', False)

PERFORMANCE_PROFILES = {
    'fast': {
        'screenshot_cache_duration': 1.0,
        'debug_timing': False
    },
    'balanced': {
        'screenshot_cache_duration': 0.5,
        'debug_timing': False
    },
    'responsive': {
        'screenshot_cache_duration': 0.1,
        'debug_timing': False
    },
    'debug': {
        'screenshot_cache_duration': 0.5,
        'debug_timing': True
    }
}

def get_config():
    """Get current configuration (deprecated - use config_manager)"""
    return {
        'screenshot_cache_duration': _config.get('performance.screenshot_cache_duration', 0.5),
        'debug_timing': _config.get('performance.debug_timing', False)
    }

def set_config(cache_duration=None, debug_timing=None):
    """Set configuration values (deprecated - use config_manager)"""
    if cache_duration is not None:
        _config.set('performance.screenshot_cache_duration', cache_duration)
    
    if debug_timing is not None:
        _config.set('performance.debug_timing', debug_timing)

def apply_performance_profile(profile_name):
    """Apply a performance profile"""
    return _config.apply_performance_profile(profile_name)

def print_performance_tips():
    """Print performance optimization tips"""
    logger.info("\n=== Performance Optimization Tips ===")
    logger.info("")
    logger.info("For GNOME Wayland users:")
    logger.info("1. Use 'fast' profile for best performance (1 second cache)")
    logger.info("2. Use 'responsive' profile for real-time applications (100ms cache)")
    logger.info("3. Use 'debug' profile to see timing information")
    logger.info("4. Batch pixel reads when possible")
    logger.info("5. Consider using XWayland applications for better performance")
    logger.info("")
    logger.info("For X11 users:")
    logger.info("1. Performance should be optimal by default")
    logger.info("2. No additional optimization needed")
    logger.info("")
    logger.info("To change performance profile:")
    logger.info("  from libs.config import apply_performance_profile")
    logger.info("  apply_performance_profile('fast')  # or 'balanced', 'responsive', 'debug'") 