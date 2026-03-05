from libs.pixel_get_color import get_color as pixel_get_color
from libs.keyboard_actions import press_and_release
from libs.key_mapping import key_mapping
from PIL import ImageGrab
import time
import keyboard

# Constants
DEFAULT_COLOR = (0, 0, 0)

# Helper function for pixel actions
def handle_pixel_action(condition_color, key):
    if condition_color != DEFAULT_COLOR:
        press_and_release(key)

# Disc rotation logic for numpad4
def wow4_rotation(stop_event):
    try:
        while not stop_event.is_set() and keyboard.is_pressed(key_mapping['numpad4']):
            # Grab the entire screen region once
            screen_image = ImageGrab.grab()

            # Extract relevant pixel colors from the cached screen image
            focus_health = screen_image.getpixel((2345, 915))
            health_below_50 = screen_image.getpixel((2375, 995))

            # Handle actions based on pixel colors
            handle_pixel_action(focus_health, '=')
            handle_pixel_action(health_below_50, '-')

            # Default key press
            press_and_release(key_mapping['numpad4'])
            time.sleep(0.2)  

    except Exception as e:
        print(f"An error occurred during wow4 rotation: {e}")

# Disc rotation logic for numpad7
def wow7_rotation(stop_event):
    try:
        while not stop_event.is_set() and keyboard.is_pressed(key_mapping['numpad7']):
            # Grab the entire screen region once
            screen_image = ImageGrab.grab()

            # Extract relevant pixel colors from the cached screen image
            focus_health = screen_image.getpixel((2345, 915))
            health_below_50 = screen_image.getpixel((2375, 995))

            # Handle actions based on pixel colors
            handle_pixel_action(focus_health, '=')
            handle_pixel_action(health_below_50, '-')

            # Default key press
            press_and_release(key_mapping['numpad7'])
            time.sleep(0.2)  

    except Exception as e:
        print(f"An error occurred during wow7 rotation: {e}")

# Main run function
def run(stop_event):
    while not stop_event.is_set():
        if keyboard.is_pressed(key_mapping['numpad4']):
            wow4_rotation(stop_event)
        elif keyboard.is_pressed(key_mapping['numpad7']):
            wow7_rotation(stop_event)
        time.sleep(0.1)  # Sleep to avoid busy-waiting
