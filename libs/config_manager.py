"""
Configuration management for EvilHotKeys
Supports YAML-based configuration files
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from libs.logger import get_logger

logger = get_logger('config_manager')

# Default configuration
DEFAULT_CONFIG = {
    'performance': {
        'profile': 'balanced',  # fast, balanced, responsive, debug
        'screenshot_cache_duration': 0.5,
        'debug_timing': False
    },
    'logging': {
        'level': 'INFO',  # DEBUG, INFO, WARNING, ERROR
        'log_to_file': False,
        'log_file_path': 'evilhotkeys.log'
    },
    'keybinds': {
        'pause': 'end',
        'stop': 'esc'
    },
    'display': {
        'resolution': '5760x1080',  # Default multi-monitor setup
        'use_auto_detect': True
    }
}

# Performance profiles
PERFORMANCE_PROFILES = {
    'fast': {
        'screenshot_cache_duration': 1.0,  # 1 second - best performance
        'debug_timing': False
    },
    'balanced': {
        'screenshot_cache_duration': 0.5,  # 500ms - default
        'debug_timing': False
    },
    'responsive': {
        'screenshot_cache_duration': 0.1,  # 100ms - most responsive
        'debug_timing': False
    },
    'debug': {
        'screenshot_cache_duration': 0.5,  # 500ms
        'debug_timing': True
    }
}


class ConfigManager:
    """Manages application configuration"""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize configuration manager.
        
        Args:
            config_path: Path to config file (default: ./config.yaml)
        """
        if config_path is None:
            config_path = Path('config.yaml')
        
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = DEFAULT_CONFIG.copy()
        self.load()
    
    def load(self) -> bool:
        """Load configuration from file.
        
        Returns:
            True if config loaded successfully, False otherwise
        """
        if not self.config_path.exists():
            logger.info(f"Config file not found: {self.config_path}")
            logger.info("Using default configuration")
            return False
        
        try:
            with open(self.config_path, 'r') as f:
                user_config = yaml.safe_load(f)
            
            if user_config:
                # Deep merge user config with defaults
                self._merge_config(self.config, user_config)
                logger.info(f"Loaded configuration from {self.config_path}")
                return True
            else:
                logger.warning(f"Config file is empty: {self.config_path}")
                return False
                
        except yaml.YAMLError as e:
            logger.error(f"Error parsing config file: {e}")
            return False
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
            return False
    
    def save(self) -> bool:
        """Save current configuration to file.
        
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
            logger.info(f"Saved configuration to {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving config file: {e}")
            return False
    
    def create_default_config(self) -> bool:
        """Create a default config file.
        
        Returns:
            True if created successfully, False otherwise
        """
        if self.config_path.exists():
            logger.warning(f"Config file already exists: {self.config_path}")
            return False
        
        self.config = DEFAULT_CONFIG.copy()
        return self.save()
    
    def _merge_config(self, base: Dict, updates: Dict):
        """Deep merge updates into base config."""
        for key, value in updates.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """Get a configuration value by dot-separated path.
        
        Args:
            key_path: Dot-separated path (e.g., 'performance.profile')
            default: Default value if key not found
        
        Returns:
            Configuration value or default
        
        Example:
            >>> config.get('performance.profile')
            'balanced'
        """
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, key_path: str, value: Any):
        """Set a configuration value by dot-separated path.
        
        Args:
            key_path: Dot-separated path (e.g., 'performance.profile')
            value: Value to set
        
        Example:
            >>> config.set('performance.profile', 'fast')
        """
        keys = key_path.split('.')
        target = self.config
        
        # Navigate to the parent dict
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        
        # Set the final value
        target[keys[-1]] = value
    
    def apply_performance_profile(self, profile_name: str) -> bool:
        """Apply a performance profile.
        
        Args:
            profile_name: Name of profile (fast, balanced, responsive, debug)
        
        Returns:
            True if profile applied successfully, False otherwise
        """
        if profile_name not in PERFORMANCE_PROFILES:
            logger.error(f"Unknown performance profile: {profile_name}")
            logger.info(f"Available profiles: {list(PERFORMANCE_PROFILES.keys())}")
            return False
        
        profile = PERFORMANCE_PROFILES[profile_name]
        
        # Update config
        self.set('performance.profile', profile_name)
        self.set('performance.screenshot_cache_duration', profile['screenshot_cache_duration'])
        self.set('performance.debug_timing', profile['debug_timing'])
        
        # Apply to GNOME screenshot manager if available
        try:
            from libs.gnome_screenshot import get_gnome_screenshot_manager
            from libs.environment import is_gnome_wayland
            
            if is_gnome_wayland():
                manager = get_gnome_screenshot_manager()
                if manager:
                    manager.set_cache_duration(profile['screenshot_cache_duration'])
                    manager.enable_debug_timing(profile['debug_timing'])
                    logger.info(f"Applied {profile_name} profile to GNOME screenshot manager")
        except Exception as e:
            logger.warning(f"Could not apply profile to GNOME screenshot manager: {e}")
        
        logger.info(f"Applied {profile_name} performance profile")
        return True
    
    def get_game_config(self, game_name: str) -> Dict[str, Any]:
        """Get game-specific configuration.
        
        Args:
            game_name: Name of the game
        
        Returns:
            Game configuration dict or empty dict if not found
        """
        games = self.get('games', {})
        return games.get(game_name, {})
    
    def get_pixel_coords(self, game_name: str, coord_name: str, resolution: Optional[str] = None) -> Optional[tuple]:
        """Get pixel coordinates for a game.
        
        Args:
            game_name: Name of the game
            coord_name: Name of the coordinate (e.g., 'interrupt', 'health_50')
            resolution: Screen resolution (uses config default if not specified)
        
        Returns:
            Tuple of (x, y) coordinates or None if not found
        """
        game_config = self.get_game_config(game_name)
        
        if not game_config:
            return None
        
        if resolution is None:
            resolution = self.get('display.resolution', '5760x1080')
        
        coords = game_config.get('coordinates', {}).get(resolution, {})
        coord_data = coords.get(coord_name)
        
        if coord_data and isinstance(coord_data, (list, tuple)) and len(coord_data) == 2:
            return tuple(coord_data)
        
        return None


# Global config instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def reload_config():
    """Reload configuration from file."""
    global _config_manager
    if _config_manager:
        _config_manager.load()

