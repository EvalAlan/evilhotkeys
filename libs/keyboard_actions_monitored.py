"""
Monitored Keyboard Actions
Drop-in replacement for keyboard_actions that automatically records activity
"""
import keyboard
import time
from libs.keyboard_actions import press as _press, release as _release
from libs.spec_monitor import get_monitor
from libs.logger import get_logger

logger = get_logger('keyboard_actions_monitored')


def press_and_release(key, delay=0.02):
    """Press and release a key with monitoring"""
    keyboard.press_and_release(key)
    
    # Record to monitor
    monitor = get_monitor()
    if monitor.is_running:
        monitor.record_key_press(key)
    
    if delay > 0:
        time.sleep(delay)


def hold_key_while_pressed(hotkey, keys_to_press, delay=0.02):
    """Hold down a key while a hotkey is pressed with monitoring"""
    while keyboard.is_pressed(hotkey):
        for key in keys_to_press:
            press_and_release(key, delay)
        time.sleep(0.05)


def press(key):
    """Press a key with monitoring"""
    _press(key)
    
    # Record to monitor
    monitor = get_monitor()
    if monitor.is_running:
        monitor.record_key_press(key)


def release(key):
    """Release a key (no monitoring needed)"""
    _release(key)


def button_mash(key, presses=3, delay=0.05, stop_check=None):
    """Mash a button multiple times with monitoring"""
    for _ in range(presses):
        if stop_check and stop_check():
            return False
        press(key)
        release(key)
        time.sleep(delay)
    return True


def record_interrupt(target=None):
    """Convenience function to record an interrupt"""
    monitor = get_monitor()
    if monitor.is_running:
        monitor.record_interrupt(target)

