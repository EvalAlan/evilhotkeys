from libs.pixel_search import pixel_search
from libs.pixel_get_color import get_color as pixel_get_color
from libs.keyboard_actions import press_and_release, press, release, button_mash
from libs.key_mapping import key_mapping
import time
import keyboard

def check_stop_condition(stop_event):
    """Check if we should stop the rotation"""
    return not keyboard.is_pressed(key_mapping['numpad1']) or stop_event.is_set()

def healing_mechanist_rotation(stop_event):
    while not stop_event.is_set():  
        if check_stop_condition(stop_event):
            break

        button_mash(key_mapping['numpad1'], stop_check=lambda: check_stop_condition(stop_event))
        button_mash('1', stop_check=lambda: check_stop_condition(stop_event))
        button_mash('2', stop_check=lambda: check_stop_condition(stop_event))
        button_mash('3', stop_check=lambda: check_stop_condition(stop_event))
        time.sleep(0.5)
        
        if check_stop_condition(stop_event):
            break

        if pixel_get_color(3015, 1035) == (255, 255, 255):
            if pixel_get_color(2742, 1015) != (0, 0, 0):
                if not button_mash(key_mapping['numpad4'], stop_check=lambda: check_stop_condition(stop_event)): break  # Acid Bomb
                time.sleep(0.5)
                if check_stop_condition(stop_event): break
                
                if not button_mash(key_mapping['f1'], stop_check=lambda: check_stop_condition(stop_event)): break  # Weapon Swap
                time.sleep(0.5)
                if check_stop_condition(stop_event): break
                continue

            if pixel_get_color(2799, 1015) != (0, 0, 0):
                if not button_mash(key_mapping['numpad5'], stop_check=lambda: check_stop_condition(stop_event)): break  # Super Elixir
                time.sleep(0.5)
                if check_stop_condition(stop_event): break
                continue

            if not button_mash(key_mapping['numpad0'], stop_check=lambda: check_stop_condition(stop_event)): break  # Switch to Mortar
            time.sleep(0.5)
            if check_stop_condition(stop_event): break

        elif pixel_get_color(3080, 1035) == (255, 255, 255):
            if pixel_get_color(2799, 1015) != (0, 0, 0):
                if not button_mash(key_mapping['numpad5'], stop_check=lambda: check_stop_condition(stop_event)): break  # Elixir Shell
                time.sleep(0.5)
                if check_stop_condition(stop_event): break
            else:
                if not button_mash(key_mapping['numpad6'], stop_check=lambda: check_stop_condition(stop_event)): break  # Switch to MedKit
                time.sleep(0.5)
                if check_stop_condition(stop_event): break
            time.sleep(0.5)
            if check_stop_condition(stop_event): break

        elif pixel_get_color(2960, 1035) == (255, 255, 255):
            if pixel_get_color(2799, 1015) != (0, 0, 0):
                if not button_mash(key_mapping['numpad5'], stop_check=lambda: check_stop_condition(stop_event)): break  # Infusion Bomb
                time.sleep(0.5)
                if check_stop_condition(stop_event): break
            else:
                if not button_mash(key_mapping['f1'], stop_check=lambda: check_stop_condition(stop_event)): break  # Weapon Swap
                time.sleep(0.5)
                if check_stop_condition(stop_event): break
            time.sleep(0.5)
            if check_stop_condition(stop_event): break

        else:
            if pixel_get_color(2742, 1015) != (0, 0, 0):
                if not button_mash(key_mapping['numpad4'], stop_check=lambda: check_stop_condition(stop_event)): break  # Magnetic Shield
                time.sleep(0.5)
                if check_stop_condition(stop_event): break
            elif pixel_get_color(2799, 1015) != (0, 0, 0):
                if not button_mash(key_mapping['numpad5'], stop_check=lambda: check_stop_condition(stop_event)): break  # Static Shield
                time.sleep(0.5)
                if check_stop_condition(stop_event): break
                
                if not button_mash(key_mapping['numpad2'], stop_check=lambda: check_stop_condition(stop_event)): break  # Energizing Slam
                time.sleep(0.5)
                if check_stop_condition(stop_event): break
            else:
                if not button_mash(key_mapping['numpad7'], stop_check=lambda: check_stop_condition(stop_event)): break  # Switch to Elixir Gun
                time.sleep(0.5)
                if check_stop_condition(stop_event): break
            time.sleep(0.5)
            if check_stop_condition(stop_event): break

        if not button_mash(key_mapping['numpad8'], stop_check=lambda: check_stop_condition(stop_event)): break
        time.sleep(0.5)
        if check_stop_condition(stop_event): break

def run(stop_event):
    while not stop_event.is_set():  
        if keyboard.is_pressed(key_mapping['numpad1']):
            healing_mechanist_rotation(stop_event)  
        time.sleep(0.1)  