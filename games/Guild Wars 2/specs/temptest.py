from libs.pixel_search import pixel_search
from libs.pixel_get_color import get_color as pixel_get_color
from libs.keyboard_actions import press_and_release, press, release
from libs.key_mapping import key_mapping
import time
import keyboard

def temptest_rotation(keys_to_watch, stop_event):
    while not stop_event.is_set():
        for key in keys_to_watch:
            if not keyboard.is_pressed(key_mapping[key]):
                continue

            if keyboard.is_pressed(key_mapping['numpad1']):
                press_and_release('1')
                press(key_mapping['numpad8'])
                release(key_mapping['numpad8'])
                press(key_mapping['numpad5'])
                release(key_mapping['numpad5'])
                press(key_mapping['numpad2'])
                release(key_mapping['numpad2'])
                press(key_mapping['numpad3'])
                release(key_mapping['numpad3'])
                press(key_mapping['numpad1'])
                release(key_mapping['numpad1'])
                press(key_mapping['numpad7'])
                release(key_mapping['numpad7'])
                
            elif keyboard.is_pressed(key_mapping['numpad5']):
                press_and_release('3')
                press(key_mapping['numpad8'])
                release(key_mapping['numpad8'])
                press(key_mapping['numpad5'])
                release(key_mapping['numpad5'])
                press(key_mapping['numpad3'])
                release(key_mapping['numpad3'])
                press(key_mapping['numpad1'])
                release(key_mapping['numpad1'])
                press(key_mapping['numpad7'])
                release(key_mapping['numpad7'])
                
            elif keyboard.is_pressed(key_mapping['numpad6']):
                press_and_release('2')
                press(key_mapping['numpad6'])
                release(key_mapping['numpad6'])
                press(key_mapping['numpad4'])
                release(key_mapping['numpad4'])
                press(key_mapping['numpad5'])
                release(key_mapping['numpad5'])
                press(key_mapping['numpad3'])
                release(key_mapping['numpad3'])
                press(key_mapping['numpad1'])
                release(key_mapping['numpad1'])
                press(key_mapping['numpad7'])
                release(key_mapping['numpad7'])
                
            elif keyboard.is_pressed(key_mapping['numpad7']):
                press_and_release('4')
                press(key_mapping['numpad8'])
                release(key_mapping['numpad8'])
                press(key_mapping['numpad4'])
                release(key_mapping['numpad4'])
                press(key_mapping['numpad5'])
                release(key_mapping['numpad5'])
                press(key_mapping['numpad3'])
                release(key_mapping['numpad3'])
                press(key_mapping['numpad1'])
                release(key_mapping['numpad1'])
                press(key_mapping['numpad7'])
                release(key_mapping['numpad7'])
                
            if stop_event.is_set():
                break

def run(stop_event):
    keys_to_watch = ['numpad1', 'numpad5', 'numpad6', 'numpad7']
    while not stop_event.is_set():
        temptest_rotation(keys_to_watch, stop_event)
        time.sleep(0.1)
