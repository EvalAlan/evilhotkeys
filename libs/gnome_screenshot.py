import dbus
import tempfile
import os
import time
from PIL import Image
import io
from libs.logger import get_logger

logger = get_logger('gnome_screenshot')

class GnomeScreenshotManager:
    """Manager for GNOME Wayland screenshot functionality"""
    
    def __init__(self):
        self.bus = None
        self.screenshot_interface = None
        self.permission_granted = False
        self.session_screenshot = None  # Cache for screenshot
        self.session_timestamp = 0
        self.cache_duration = 0.5  # Increased from 0.1 to 0.5 seconds
        self.debug_timing = False  # Set to True to enable timing output
        self._initialize_dbus()
    
    def _initialize_dbus(self):
        """Initialize D-Bus connection"""
        try:
            self.bus = dbus.SessionBus()
            self.screenshot_interface = self.bus.get_object(
                'org.gnome.Shell', '/org/gnome/Shell'
            ).get_dbus_method('Screenshot', 'org.gnome.Shell.Screenshot')
            return True
        except Exception as e:
            logger.error(f"Failed to initialize D-Bus connection: {e}")
            return False
    
    def request_permission(self):
        """Request screenshot permission from user"""
        logger.info("EvilHotKeys needs permission to take screenshots.")
        logger.info("A permission dialog will appear. Please grant permission to continue.")
        logger.info("This permission will be remembered for this session.")
        
        try:
            # Try to take a screenshot to trigger permission dialog
            success = self._take_screenshot_internal()
            if success:
                self.permission_granted = True
                logger.info("Screenshot permission granted!")
                return True
            else:
                logger.warning("Screenshot permission denied or failed.")
                return False
        except Exception as e:
            logger.error(f"Error requesting permission: {e}")
            return False
    
    def _take_screenshot_internal(self):
        """Internal method to take screenshot using D-Bus"""
        if not self.screenshot_interface:
            return False
        
        start_time = time.time()
        
        try:
            # Create a temporary file for the screenshot
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            # Take screenshot
            dbus_start = time.time()
            result = self.screenshot_interface(
                False,  # include_cursor
                False,  # flash
                tmp_path
            )
            dbus_time = time.time() - dbus_start
            
            if result:
                # Load the image and delete the temporary file
                load_start = time.time()
                try:
                    image = Image.open(tmp_path)
                    # Convert to RGB if needed
                    if image.mode != 'RGB':
                        image = image.convert('RGB')
                    
                    # Cache the screenshot
                    self.session_screenshot = image
                    self.session_timestamp = time.time()
                    
                    load_time = time.time() - load_start
                    total_time = time.time() - start_time
                    
                    if self.debug_timing:
                        logger.debug(f"Screenshot timing - D-Bus: {dbus_time:.3f}s, Load: {load_time:.3f}s, Total: {total_time:.3f}s")
                    
                    return True
                finally:
                    # Clean up temporary file
                    try:
                        os.unlink(tmp_path)
                    except:
                        pass
            
            return False
            
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return False
    
    def get_screenshot(self, force_new=False):
        """Get a screenshot, using cache if available"""
        if not self.permission_granted:
            if not self.request_permission():
                return None
        
        # Use cached screenshot if it's recent and not forcing new
        current_time = time.time()
        cache_age = current_time - self.session_timestamp
        
        if (not force_new and 
            self.session_screenshot and 
            cache_age < self.cache_duration):
            if self.debug_timing:
                logger.debug(f"Using cached screenshot (age: {cache_age:.3f}s)")
            return self.session_screenshot
        
        if self.debug_timing:
            logger.debug(f"Taking new screenshot (cache age: {cache_age:.3f}s)")
        
        # Take new screenshot
        if self._take_screenshot_internal():
            return self.session_screenshot
        
        return None
    
    def get_pixel_color(self, x, y):
        """Get color of pixel at coordinates"""
        screenshot = self.get_screenshot()
        if screenshot:
            try:
                return screenshot.getpixel((x, y))
            except Exception as e:
                logger.error(f"Error getting pixel color at ({x}, {y}): {e}")
        return None
    
    def get_multiple_pixel_colors(self, coordinates):
        """Get colors of multiple pixels efficiently using one screenshot"""
        screenshot = self.get_screenshot()
        if not screenshot:
            return [None] * len(coordinates)
        
        colors = []
        for (x, y) in coordinates:
            try:
                color = screenshot.getpixel((x, y))
                colors.append(color)
            except Exception as e:
                logger.error(f"Error getting pixel color at ({x}, {y}): {e}")
                colors.append(None)
        
        return colors
    
    def get_region_screenshot(self, x1, y1, x2, y2):
        """Get screenshot of a specific region"""
        screenshot = self.get_screenshot()
        if screenshot:
            try:
                return screenshot.crop((x1, y1, x2, y2))
            except Exception as e:
                logger.error(f"Error cropping region ({x1}, {y1}, {x2}, {y2}): {e}")
        return None
    
    def set_cache_duration(self, seconds):
        """Set the cache duration in seconds"""
        self.cache_duration = seconds
    
    def enable_debug_timing(self, enable=True):
        """Enable or disable debug timing output"""
        self.debug_timing = enable

# Global instance
_gnome_screenshot_manager = None

def get_gnome_screenshot_manager():
    """Get the global GNOME screenshot manager instance"""
    global _gnome_screenshot_manager
    if _gnome_screenshot_manager is None:
        _gnome_screenshot_manager = GnomeScreenshotManager()
    return _gnome_screenshot_manager 