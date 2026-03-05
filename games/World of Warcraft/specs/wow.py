from libs.pixel_search import pixel_search
from libs.pixel_get_color import get_color as pixel_get_color
from libs.keyboard_actions_monitored import press_and_release, press, release, record_interrupt
from libs.key_mapping import key_mapping
from libs.logger import get_logger
from libs.wow_helpers import get_coord
import time
import keyboard

logger = get_logger('wow')

# Constants
DEFAULT_COLOR = (0, 0, 0)

# General WoW rotation logic
def wow_rotation(keys_to_watch, stop_event):
    try:
        # Get interrupt coordinates from config
        interrupt_x, interrupt_y = get_coord('interrupt')
        
        # Log once at start for debugging
        first_run = True
        
        while not stop_event.is_set():  
            key_pressed = False
            
            for key in keys_to_watch:
                # Check stop event frequently
                if stop_event.is_set():
                    return
                
                if keyboard.is_pressed(key_mapping[key]):
                    key_pressed = True
                    
                    # Check for interrupt condition using abstraction layer
                    interrupt_target = pixel_get_color(interrupt_x, interrupt_y)
                    
                    if first_run:
                        logger.info(f"Checking interrupt at ({interrupt_x}, {interrupt_y}), color: {interrupt_target}")
                        first_run = False
                    
                    # Fire interrupt if we got a valid color that's not black
                    if interrupt_target is not None and interrupt_target != DEFAULT_COLOR:
                        logger.info(f"Interrupt fired! Color detected: {interrupt_target}")
                        record_interrupt("enemy")  # Record interrupt in monitor
                        press_and_release('=')

                    # Press and release the current key
                    press(key_mapping[key])
                    release(key_mapping[key])
                    time.sleep(0.2)
                    break  # Exit key loop after handling one key
            
            # If no keys were pressed, sleep a bit to avoid busy-waiting
            if not key_pressed:
                time.sleep(0.05)

    except Exception as e:
        logger.exception(f"An error occurred during WoW rotation: {e}")

# Main run function
def run(stop_event):
    keys_to_watch = ['numpad4', 'numpad5', 'numpad7']  
    logger.info("WoW spec started. Press numpad4, numpad5, or numpad7 to activate rotation.")
    wow_rotation(keys_to_watch, stop_event)
    logger.info("WoW spec stopped.")
