from libs.pixel_get_color import get_color as pixel_get_color
from libs.keyboard_actions import press_and_release
from libs.key_mapping import key_mapping
from PIL import ImageGrab
import time
import keyboard

DEFAULT_COLOR = (0, 0, 0)

def handle_pixel_action(condition_color, key):
    if condition_color != DEFAULT_COLOR:
        press_and_release(key)

def tank_rotation(stop_event):
    try:
        while not stop_event.is_set():
            if keyboard.is_pressed(key_mapping['numpad4']):
                screen_image = ImageGrab.grab()

                interrupt = screen_image.getpixel((4690, 1760))
                healerhealth = screen_image.getpixel((2345, 920))
                health50 = screen_image.getpixel((4750, 1995))
                health35 = screen_image.getpixel((4815, 1995))
                health25 = screen_image.getpixel((4880, 1995))
                health75 = screen_image.getpixel((4695, 1995))

                handle_pixel_action(interrupt, '=')
                handle_pixel_action(healerhealth, '5')
                handle_pixel_action(health50, '4')
                handle_pixel_action(health35, '5')
                handle_pixel_action(health25, '3')
                handle_pixel_action(health75, '0')

                press_and_release(key_mapping['numpad4'])
                time.sleep(0.2)
            else:
                time.sleep(0.1)
    except Exception as e:
        print(f"An error occurred during tank rotation: {e}")

def run(stop_event):
    tank_rotation(stop_event)
