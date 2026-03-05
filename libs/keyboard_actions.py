import keyboard
import time
from libs.logger import get_logger

logger = get_logger('keyboard_actions')

# Define a function to press and release a key with an optional delay
def press_and_release(key, delay=0.02):
    keyboard.press_and_release(key)
    if delay > 0:
        time.sleep(delay)

# Define a function to hold down a key while a hotkey is pressed
def hold_key_while_pressed(hotkey, keys_to_press, delay=0.02):
    while keyboard.is_pressed(hotkey):
        for key in keys_to_press:
            press_and_release(key, delay)
        time.sleep(0.05)  # Add a small delay to reduce CPU usage

# Define a function to press a key
def press(key):
    try:
        keyboard.press(key)
    except ValueError as e:
        logger.error(f"Key '{key}' is not recognized: {e}")
    except Exception as e:
        logger.error(f"Error pressing key '{key}': {e}")

# Define a function to release a key
def release(key):
    try:
        keyboard.release(key)
    except ValueError as e:
        logger.error(f"Key '{key}' is not recognized: {e}")
    except Exception as e:
        logger.error(f"Error releasing key '{key}': {e}")

# Define a function to mash a button multiple times to ensure it registers
def button_mash(key, presses=3, delay=0.05, stop_check=None):
    """Mash a button multiple times to ensure it registers
    
    Args:
        key: The key to press
        presses: Number of times to press the key (default: 3)
        delay: Delay between presses (default: 0.05)
        stop_check: Optional function that returns True if we should stop
    
    Returns:
        True if completed all presses, False if stopped early
    """
    for _ in range(presses):
        if stop_check and stop_check():
            return False
        press(key)
        release(key)
        time.sleep(delay)
    return True
