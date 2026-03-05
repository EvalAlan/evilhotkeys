from libs.keyboard_actions import press_and_release
from libs.key_mapping import key_mapping
import time
import keyboard
import pyautogui

def summon_attack(stop_event):
    try:
        while not stop_event.is_set() and keyboard.is_pressed(key_mapping['numpad4']):

            press_and_release('2') 

            keyboard.press('alt')
            press_and_release('1')
            keyboard.release('alt')

            keyboard.press('alt')
            press_and_release('2')
            keyboard.release('alt')

            keyboard.press('alt')
            press_and_release('3')
            keyboard.release('alt')

            keyboard.press('alt')
            press_and_release('4')
            keyboard.release('alt') 

            press_and_release('2')

            press_and_release('4')

            press_and_release('1')

            press_and_release('6')

            press_and_release('5')        

            time.sleep(0.2)

        return True
        
    except Exception as e:
        print(f"Error in summon attack: {e}")
        return False

def summon_shield(stop_event):
    try:
        while not stop_event.is_set() and keyboard.is_pressed(key_mapping['numpad2']):
            pyautogui.click()  # Left click
            keyboard.press('shift')
            press_and_release('2')
            keyboard.release('shift')

            time.sleep(0.2)
            
        return True
        
    except Exception as e:
        print(f"Error in summon shield: {e}")
        return False

def summon_healpet(stop_event):
    try:
        while not stop_event.is_set() and keyboard.is_pressed(key_mapping['numpad3']):
            keyboard.press('shift')
            press_and_release('3')
            keyboard.release('shift')

            time.sleep(0.2)
            
        return True
        
    except Exception as e:
        print(f"Error in summon healpet: {e}")
        return False

def summon_manapet(stop_event):
    try:
        while not stop_event.is_set() and keyboard.is_pressed(key_mapping['numpad6']):
            press_and_release('3')

            time.sleep(0.2)
            
        return True
        
    except Exception as e:
        print(f"Error in summon healpet: {e}")
        return False            
    
def run(stop_event):
    while not stop_event.is_set():
        if keyboard.is_pressed(key_mapping['numpad2']):
            summon_shield(stop_event)
        if keyboard.is_pressed(key_mapping['numpad3']):
            summon_healpet(stop_event)
        if keyboard.is_pressed(key_mapping['numpad4']):
            summon_attack(stop_event)
        if keyboard.is_pressed(key_mapping['numpad6']):
            summon_manapet(stop_event)    
        time.sleep(0.1)