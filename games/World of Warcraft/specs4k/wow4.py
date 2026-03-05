from libs.pixel_get_color import get_color as pixel_get_color
from libs.keyboard_actions import press_and_release
from libs.key_mapping import key_mapping
from PIL import ImageGrab
import time
import keyboard

# Constants
DEFAULT_COLOR = (0, 0, 0)

# WoW4 Rotation Logic
def wow4_rotation(stop_event):
    try:
        while not stop_event.is_set() and keyboard.is_pressed(key_mapping['numpad4']):
            # Grab the entire screen region once
            screen_image = ImageGrab.grab()

            # Extract pixel color for interrupt check
            interrupt_target = screen_image.getpixel((4690, 1760))
            if interrupt_target != DEFAULT_COLOR:  # Interrupt target
                press_and_release('=')

            # Default key press
            press_and_release(key_mapping['numpad4'])
            time.sleep(0.2)  # Increased sleep to reduce CPU usage

    except Exception as e:
        print(f"An error occurred during wow4 rotation: {e}")

# Main run function
def run(stop_event):
    while not stop_event.is_set():
        if keyboard.is_pressed(key_mapping['numpad4']):
            wow4_rotation(stop_event)
        time.sleep(0.1)  # Sleep to avoid busy-waiting
