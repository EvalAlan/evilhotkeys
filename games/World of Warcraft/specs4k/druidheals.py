from libs.pixel_get_color import get_color as pixel_get_color
from libs.keyboard_actions import press_and_release, press
from libs.key_mapping import key_mapping
from PIL import ImageGrab
import time
import keyboard

# Constants
DEFAULT_COLOR = (0, 0, 0)

# Druid Heals Rotation Logic
def druidheals_rotation(stop_event):
    try:
        while not stop_event.is_set():
            # NumPad4 behavior
            if keyboard.is_pressed(key_mapping['numpad4']):
                # Grab the entire screen region once
                screen_image = ImageGrab.grab()
                
                # Extract pixel color for interrupt check
                interrupt_target = screen_image.getpixel((4690, 1760))
                if interrupt_target != DEFAULT_COLOR:
                    press_and_release('=')

                # Default key press
                press_and_release(key_mapping['numpad4'])
                time.sleep(0.25)  # Sleep 250ms as per AHK script

            # NumPad5 behavior with a continuous loop while held
            if keyboard.is_pressed(key_mapping['numpad5']):
                while keyboard.is_pressed(key_mapping['numpad5']) and not stop_event.is_set():
                    # Grab the entire screen region once
                    screen_image = ImageGrab.grab()
                    
                    # Check for interrupt
                    interrupt_target = screen_image.getpixel((4690, 1760))
                    if interrupt_target != DEFAULT_COLOR:
                        press_and_release('=')

                    # Combo bust
                    finish_color = screen_image.getpixel((2378, 878))
                    if finish_color != DEFAULT_COLOR:
                        press_and_release('0')

                    # Sending a modified input equivalent to Control + NumPad4
                    press('ctrl')
                    press_and_release(key_mapping['numpad4'])
                    keyboard.release('ctrl')

                    time.sleep(0.25)  # Sleep 250ms as per AHK script

    except Exception as e:
        print(f"An error occurred during druid heals rotation: {e}")

# Main run function
def run(stop_event):
    while not stop_event.is_set():
        druidheals_rotation(stop_event)
        time.sleep(0.1)  # Sleep to avoid busy-waiting
