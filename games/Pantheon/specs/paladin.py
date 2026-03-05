from libs.keyboard_actions import press_and_release
from libs.key_mapping import key_mapping
import time
import keyboard
import pyautogui



def paladin_attack(stop_event):
    try:
        while not stop_event.is_set() and keyboard.is_pressed(key_mapping['numpad4']):
            keyboard.press('alt')
            press_and_release('1')
            keyboard.release('alt')
            press_and_release('2')
            keyboard.press('shift')
            press_and_release('1')
            keyboard.release('shift')           
            press_and_release('3')        

            time.sleep(0.2)

        return True
        
    except Exception as e:
        print(f"Error in paladin attack: {e}")
        return False

def run(stop_event):
    while not stop_event.is_set():      
        if keyboard.is_pressed(key_mapping['numpad4']):
            paladin_attack(stop_event)
        time.sleep(0.1)        