from libs.pixel_search import pixel_search
from libs.pixel_get_color import get_color as pixel_get_color
from libs.keyboard_actions import press_and_release, press, release
from libs.key_mapping import key_mapping
import time
import keyboard
from PIL import ImageGrab

# Constants
DEFAULT_COLOR = (0, 0, 0)

# General WoW rotation logic
def wow_rotation(keys_to_watch, stop_event):
    try:
        while not stop_event.is_set():  
            for key in keys_to_watch:
                if keyboard.is_pressed(key_mapping[key]):
                    # Grab the screen region once per rotation
                    screen_image = ImageGrab.grab()

                    # Check for interrupt condition
                    interrupt_target = screen_image.getpixel((4690, 1760))
                    if interrupt_target != DEFAULT_COLOR:
                        press_and_release('=')

                    # Press and release the current key
                    press(key_mapping[key])
                    release(key_mapping[key])
                    time.sleep(0.2) 

                if stop_event.is_set():  
                    break

    except Exception as e:
        print(f"An error occurred during WoW rotation: {e}")

# Main run function
def run(stop_event):
    keys_to_watch = ['numpad4', 'numpad5', 'numpad7']  
    while not stop_event.is_set():
        wow_rotation(keys_to_watch, stop_event)
        time.sleep(0.1)  # Sleep to avoid busy-waiting
