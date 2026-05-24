"""
Condition Mechanist (Spear + Grenade Kit)
Based on the existing working condition_mechanist spec, with light reliability/speed improvements.

Design goals:
- Keep the same proven behavior pattern.
- Improve responsiveness a bit without turning into animation-clipping chaos.
- Keep fallback logic simple and robust.
"""

import os
import time
import keyboard

from libs.pixel_search import pixel_search
from libs.pixel_get_color import get_color as pixel_get_color
from libs.keyboard_actions import button_mash
from libs.key_mapping import key_mapping

STOP_KEY = key_mapping.get("numpad1", "numpad1")
DEBUG = os.getenv("EHK_CONDI_DEBUG", "0") == "1"

# Slightly faster than legacy 0.5s but still conservative.
POST_CAST_DELAY = 0.35
LOOP_DELAY = 0.08


def debug(msg: str):
    if DEBUG:
        print(f"[CONDI-SPEAR] {msg}", flush=True)


def check_stop_condition(stop_event):
    return stop_event.is_set() or not keyboard.is_pressed(STOP_KEY)


def is_ready(x, y):
    c = pixel_get_color(x, y)
    return bool(c and c != (0, 0, 0))


def cast(key, stop_event, presses=1, delay=0.04, wait=POST_CAST_DELAY):
    if check_stop_condition(stop_event):
        return False
    ok = button_mash(key, presses=presses, delay=delay, stop_check=lambda: check_stop_condition(stop_event))
    if not ok:
        return False
    time.sleep(wait)
    return not check_stop_condition(stop_event)


def in_grenade_kit():
    # Existing kit check from original spec.
    return pixel_search((255, 255, 255), 2170, 2045, 2205, 2080)


def condition_mechanist_spear_rotation(stop_event):
    while not stop_event.is_set():
        if check_stop_condition(stop_event):
            break

        # Keep mech commands rolling.
        cast('2', stop_event, wait=0.12)
        cast('1', stop_event, wait=0.12)
        cast('3', stop_event, wait=0.12)

        if check_stop_condition(stop_event):
            break

        if in_grenade_kit():
            # Grenade kit priorities
            s2_ready = is_ready(2630, 1017)  # Shrapnel-like slot
            s4_ready = is_ready(2743, 1017)  # Freeze/utility grenade
            s5_ready = is_ready(2797, 1017)  # Poison-like slot
            signet_ready = is_ready(3063, 1015)

            debug(f"kit=grenade s2={s2_ready} s4={s4_ready} s5={s5_ready} signet={signet_ready}")

            if s2_ready:
                if not cast(key_mapping['numpad2'], stop_event):
                    break

            if s5_ready:
                if not cast(key_mapping['numpad5'], stop_event):
                    break

            if signet_ready:
                if not cast(key_mapping['numpad8'], stop_event, wait=0.20):
                    break

            if s4_ready:
                if not cast(key_mapping['numpad4'], stop_event):
                    break

            # Nothing useful in kit => exit kit (weapon swap)
            if not s2_ready and not s4_ready and not s5_ready:
                debug("grenade empty -> weapon swap out")
                if not cast(key_mapping['f1'], stop_event, wait=0.25):
                    break

            # Keep auto-attack pressure
            if not cast(key_mapping['numpad1'], stop_event, wait=0.08):
                break

        else:
            # Spear priorities (mirrors old pistol-side structure, same slots)
            s2_ready = is_ready(2630, 1017)
            s3_ready = is_ready(2686, 1017)
            s4_ready = is_ready(2743, 1017)

            debug(f"kit=spear s2={s2_ready} s3={s3_ready} s4={s4_ready}")

            if s2_ready:
                if not cast(key_mapping['numpad2'], stop_event):
                    break

            if s4_ready:
                if not cast(key_mapping['numpad4'], stop_event):
                    break

            if s3_ready:
                if not cast(key_mapping['numpad3'], stop_event):
                    break

            # If nothing on spear side is lit, go grenade kit.
            if not s2_ready and not s3_ready and not s4_ready:
                debug("spear empty -> grenade kit")
                if not cast(key_mapping['numpad7'], stop_event, wait=0.30):
                    break

            if not cast(key_mapping['numpad1'], stop_event, wait=0.08):
                break

        time.sleep(LOOP_DELAY)


def run(stop_event):
    while not stop_event.is_set():
        if keyboard.is_pressed(STOP_KEY):
            condition_mechanist_spear_rotation(stop_event)
        time.sleep(0.1)
