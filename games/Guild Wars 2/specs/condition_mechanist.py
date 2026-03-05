from libs.pixel_search import pixel_search
from libs.pixel_get_color import get_color as pixel_get_color
from libs.keyboard_actions import press_and_release, press, release, button_mash
from libs.key_mapping import key_mapping
import time
import keyboard

def check_stop_condition(stop_event):
    """Check if we should stop the rotation"""
    return not keyboard.is_pressed(key_mapping['numpad1']) or stop_event.is_set()

def condition_mechanist_rotation(stop_event):
    while not stop_event.is_set():  
        if check_stop_condition(stop_event):
            break
        
        button_mash('2', stop_check=lambda: check_stop_condition(stop_event))
        button_mash('1', stop_check=lambda: check_stop_condition(stop_event))
        button_mash('3', stop_check=lambda: check_stop_condition(stop_event))
        
        if check_stop_condition(stop_event):
            break
        
        if pixel_search((255, 255, 255), 2170, 2045, 2205, 2080):  # Grenade Kit
            sg = pixel_get_color(2630, 1017)
            pg = pixel_get_color(2797, 1017)
            signet = pixel_get_color(3063, 1015)
            fg = pixel_get_color(2743, 1017)
            
            if sg != (0, 0, 0):
                if not button_mash(key_mapping['numpad2'], stop_check=lambda: check_stop_condition(stop_event)): break
                time.sleep(0.5)
                if check_stop_condition(stop_event): break
                
            if pg != (0, 0, 0):
                if not button_mash(key_mapping['numpad5'], stop_check=lambda: check_stop_condition(stop_event)): break
                time.sleep(0.5)
                if check_stop_condition(stop_event): break
            
            if signet != (0, 0, 0):
                if not button_mash(key_mapping['numpad8'], stop_check=lambda: check_stop_condition(stop_event)): break
                time.sleep(0.5)
                if check_stop_condition(stop_event): break
            
            if fg != (0, 0, 0):
                if not button_mash(key_mapping['numpad4'], stop_check=lambda: check_stop_condition(stop_event)): break
                time.sleep(0.5)
                if check_stop_condition(stop_event): break
            
            if sg == (0, 0, 0) and pg == (0, 0, 0) and fg == (0, 0, 0):
                if not button_mash(key_mapping['f1'], stop_check=lambda: check_stop_condition(stop_event)): break
                time.sleep(0.5)
                if check_stop_condition(stop_event): break

            if not button_mash(key_mapping['numpad1'], stop_check=lambda: check_stop_condition(stop_event)): break
        
        else:
            pdv = pixel_get_color(2630, 1017)
            bt = pixel_get_color(2743, 1017)
            ss = pixel_get_color(2686, 1017)
            
            if pdv != (0, 0, 0):
                if not button_mash(key_mapping['numpad2'], stop_check=lambda: check_stop_condition(stop_event)): break
                time.sleep(0.5)
                if check_stop_condition(stop_event): break
            
            if bt != (0, 0, 0):
                if not button_mash(key_mapping['numpad4'], stop_check=lambda: check_stop_condition(stop_event)): break
                time.sleep(0.5)
                if check_stop_condition(stop_event): break
            
            if ss != (0, 0, 0):
                if not button_mash(key_mapping['numpad3'], stop_check=lambda: check_stop_condition(stop_event)): break
                time.sleep(0.5)
                if check_stop_condition(stop_event): break
            
            if pdv == (0, 0, 0) and bt == (0, 0, 0) and ss == (0, 0, 0):
                if not button_mash(key_mapping['numpad7'], stop_check=lambda: check_stop_condition(stop_event)): break
                time.sleep(0.5)
                if check_stop_condition(stop_event): break
            
            if not button_mash(key_mapping['numpad1'], stop_check=lambda: check_stop_condition(stop_event)): break

def run(stop_event):
    while not stop_event.is_set():
        if keyboard.is_pressed(key_mapping['numpad1']):
            condition_mechanist_rotation(stop_event)  
        time.sleep(0.1)  
