from libs.keyboard_actions import press_and_release
from libs.key_mapping import key_mapping
import time
import keyboard
import pyautogui

def shaman_buff():
    try:
        pyautogui.click()  # Left click
        
        keyboard.press('shift')
        press_and_release('3')
        keyboard.release('shift')
        time.sleep(4)

        keyboard.press('shift')
        press_and_release('4')
        keyboard.release('shift')
        time.sleep(4)

        keyboard.press('shift')
        press_and_release('5')
        keyboard.release('shift')
        
    except Exception as e:
        print(f"Error in shaman buffs: {e}")

def shaman_stream():
    try:
        pyautogui.click()  # Left click
        press_and_release('1')
        
    except Exception as e:
        print(f"Error in shaman stream: {e}")

def shaman_replenish():
    try:
        pyautogui.click()  # Left click
        press_and_release('2')
        
    except Exception as e:
        print(f"Error in shaman replenish: {e}")

def shaman_echo():
    try:
        pyautogui.click()  # Left click
        press_and_release('3')
        
    except Exception as e:
        print(f"Error in shaman echo: {e}")

def shaman_debuff():
    try:
        keyboard.press('alt')
        press_and_release('3')
        keyboard.release('alt')
        time.sleep(2)

        press_and_release('4')
        time.sleep(4) 

        press_and_release('5')
        time.sleep(4) 

    except Exception as e:
        print(f"Error in shaman debuff: {e}")

def shaman_dot():
    try:
        press_and_release('`')
        time.sleep(0.2)

        press_and_release('6')
        time.sleep(3)

        press_and_release('7')
        time.sleep(3)

    except Exception as e:
        print(f"Error in shaman dot: {e}")

def shaman_bang():
    try:
        keyboard.press('alt')
        press_and_release('2')
        keyboard.release('alt')
        time.sleep(1)

        press_and_release('8')
        
    except Exception as e:
        print(f"Error in shaman bang: {e}")

def run(stop_event):
    running_states = {
        'numpad1': False,
        'numpad2': False,
        'numpad3': False,
        'numpad4': False,
        'numpad5': False,
        'numpad6': False,
        'numpad7': False
    }

    while not stop_event.is_set():
        if keyboard.is_pressed(key_mapping['numpad1']):
            if not running_states['numpad1']:
                running_states['numpad1'] = True
                shaman_stream()
            while keyboard.is_pressed(key_mapping['numpad1']) and not stop_event.is_set():
                time.sleep(0.05)
            running_states['numpad1'] = False

        if keyboard.is_pressed(key_mapping['numpad2']):
            if not running_states['numpad2']:
                running_states['numpad2'] = True
                shaman_replenish()
            while keyboard.is_pressed(key_mapping['numpad2']) and not stop_event.is_set():
                time.sleep(0.05)
            running_states['numpad2'] = False

        if keyboard.is_pressed(key_mapping['numpad3']):
            if not running_states['numpad3']:
                running_states['numpad3'] = True
                shaman_echo()
            while keyboard.is_pressed(key_mapping['numpad3']) and not stop_event.is_set():
                time.sleep(0.05)
            running_states['numpad3'] = False

        if keyboard.is_pressed(key_mapping['numpad4']):
            if not running_states['numpad4']:
                running_states['numpad4'] = True
                shaman_debuff()
            while keyboard.is_pressed(key_mapping['numpad4']) and not stop_event.is_set():
                time.sleep(0.05)
            running_states['numpad4'] = False

        if keyboard.is_pressed(key_mapping['numpad5']):
            if not running_states['numpad5']:
                running_states['numpad5'] = True
                shaman_dot()
            while keyboard.is_pressed(key_mapping['numpad5']) and not stop_event.is_set():
                time.sleep(0.05)
            running_states['numpad5'] = False

        if keyboard.is_pressed(key_mapping['numpad6']):
            if not running_states['numpad6']:
                running_states['numpad6'] = True
                shaman_buff()
            while keyboard.is_pressed(key_mapping['numpad6']) and not stop_event.is_set():
                time.sleep(0.05)
            running_states['numpad6'] = False

        if keyboard.is_pressed(key_mapping['numpad7']):
            if not running_states['numpad7']:
                running_states['numpad7'] = True
                shaman_bang()
            while keyboard.is_pressed(key_mapping['numpad7']) and not stop_event.is_set():
                time.sleep(0.05)
            running_states['numpad7'] = False

        time.sleep(0.05)