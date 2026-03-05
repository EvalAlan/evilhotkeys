from libs.pixel_search import pixel_search
from libs.keyboard_actions import press_and_release, press, release
from libs.key_mapping import key_mapping
import time
import keyboard

def fishing_rotation(stop_event):
    press(key_mapping['numpad1'])
    release(key_mapping['numpad1'])
    while not stop_event.is_set():
        
        if keyboard.is_pressed(key_mapping['numpad2']):
            press_and_release('j')  # Equip fishing
            time.sleep(2.5)
            if stop_event.is_set(): break  
            press(key_mapping['numpad1'])  # Begin fishing
            release(key_mapping['numpad1'])  

        if keyboard.is_pressed(key_mapping['numpad1']):
            catch_color = pixel_search((233, 54, 101), 1855, 840, 1965, 950)  # Searching for the catch color
            if catch_color:
                press(key_mapping['numpad1'])
                release(key_mapping['numpad1'])
                time.sleep(0.5)
                if stop_event.is_set(): break 

                while not stop_event.is_set():  
                    green_color = pixel_search((113, 241, 156), 1665, 1590, 2174, 1624)  # Searching for the green block
                    if not green_color:
                        orange_color = pixel_search((12, 47, 84), 1665, 1590, 2174, 1624)  # Searching for the orange block
                        if orange_color:
                            green_x, green_y = green_color
                            orange_x, orange_y = orange_color
                            if green_x < orange_x - 5:
                                press_and_release('d')  # Press "d" to move the orange block to the left
                            elif green_x > orange_x + 5:
                                press_and_release('a')  # Press "a" to move the orange block to the right
                    else:
                        press_and_release('a up')
                        press_and_release('d up')
                        time.sleep(4)
                        break  # This break exits the while loop, so it's okay to keep

def run(stop_event):
    while not stop_event.is_set():
        fishing_rotation(stop_event)  
        time.sleep(0.1)  
