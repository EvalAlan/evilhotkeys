"""
Condition Mechanist (Spear + Grenade Kit)
Based on: https://metabattle.com/wiki/Build:Mechanist_-_Condition_Mechanist

MetaBattle priorities:
- Superconducting Signet freely on cooldown (J-Drive keeps passive effects).
- Conduit Surge + mech command together when available.
- Shrapnel Grenade, Devastator, Poison Grenade, Freeze Grenade.
- Enter Grenade Kit frequently for Shrapnel Grenade; use Poison/Freeze when available.

This script keeps the previously working spear/grenade behavior, but adds the same
high-verbosity logging style used by the Soulbeast and Untamed specs.
"""

import sys
import time
import keyboard

from libs.pixel_search import pixel_search
from libs.pixel_get_color import get_color as pixel_get_color
from libs.keyboard_actions import button_mash
from libs.key_mapping import key_mapping
from libs.logger import get_logger
from libs.pause import wait_if_paused

logger = get_logger('condition_mechanist_spear')
logger.propagate = True

STOP_KEY = key_mapping.get("numpad1", "numpad1")
ENABLE_DETAILED_LOGGING = True

# Slightly faster than legacy 0.5s but still conservative.
POST_CAST_DELAY = 0.35
LOOP_DELAY = 0.08

# Standard EvilHotKeys triple-monitor bar coordinates.
DEFAULT_COORDS = {
    'slot_1': (2587, 1013),
    'slot_2': (2630, 1017),
    'slot_3': (2686, 1017),
    'slot_4': (2743, 1017),
    'slot_5': (2797, 1017),
    'utility_heal': (2652, 1013),
    'utility_1': (3007, 1013),       # Grenade Kit toggle
    'utility_2': (3063, 1015),       # Superconducting Signet
    'utility_3': (3116, 1013),
    'utility_elite': (3171, 1013),
}

MECH_COMMANDS = {
    'mech_skill_1': '1',
    'mech_skill_2': '2',
    'mech_skill_3': '3',
}

# Internal stagger so always-lit utility pixels do not spam every loop.
UTILITY_STAGGER = {
    'superconducting_signet': 18.0,
}


def log_and_print(level, msg):
    """Log and print like the other GW2 debug specs."""
    if level in ('error', 'warning') or ENABLE_DETAILED_LOGGING:
        getattr(logger, level)(msg)
        if ENABLE_DETAILED_LOGGING:
            print(f"[{level.upper()}] {msg}", flush=True)
            sys.stdout.flush()


def check_stop_condition(stop_event):
    return stop_event.is_set() or not keyboard.is_pressed(STOP_KEY)


def get_brightness(name):
    coords = DEFAULT_COORDS.get(name)
    if not coords:
        return 0
    color = pixel_get_color(*coords)
    if isinstance(color, (tuple, list)):
        return sum(color)
    return 0


def is_ready_at(x, y):
    color = pixel_get_color(x, y)
    return bool(color and color != (0, 0, 0))


def is_ready(name):
    coords = DEFAULT_COORDS[name]
    return is_ready_at(*coords)


def cast(label, key, stop_event, presses=1, delay=0.04, wait=POST_CAST_DELAY):
    if check_stop_condition(stop_event):
        return False
    log_and_print('info', f">>> PRIORITY: {label}")
    ok = button_mash(key, presses=presses, delay=delay, stop_check=lambda: check_stop_condition(stop_event))
    if not ok:
        log_and_print('debug', f"Cast interrupted/failed: {label}")
        return False
    time.sleep(wait)
    return not check_stop_condition(stop_event)


def in_grenade_kit():
    # Existing kit check from original spec.
    return pixel_search((255, 255, 255), 2170, 2045, 2205, 2080)


def get_status(in_kit):
    slot_ready = {
        'slot_2': is_ready('slot_2'),
        'slot_3': is_ready('slot_3'),
        'slot_4': is_ready('slot_4'),
        'slot_5': is_ready('slot_5'),
    }
    slot_brightness = {
        'slot_2': get_brightness('slot_2'),
        'slot_3': get_brightness('slot_3'),
        'slot_4': get_brightness('slot_4'),
        'slot_5': get_brightness('slot_5'),
    }
    utilities_ready = {
        'grenade_kit': is_ready('utility_1'),
        'superconducting_signet': is_ready('utility_2'),
    }
    utility_brightness = {
        'grenade_kit': get_brightness('utility_1'),
        'superconducting_signet': get_brightness('utility_2'),
    }
    return {
        'mode': 'GRENADE' if in_kit else 'SPEAR',
        'slot_ready': slot_ready,
        'slot_brightness': slot_brightness,
        'utilities_ready': utilities_ready,
        'utility_brightness': utility_brightness,
    }


def log_status(loop_count, status):
    log_and_print(
        'info',
        (
            f"--- LOOP {loop_count} ---\n"
            f"Mode={status['mode']} | Slots={status['slot_ready']} brightness={status['slot_brightness']}\n"
            f"Utilities={status['utilities_ready']} brightness={status['utility_brightness']}"
        )
    )


def condition_mechanist_spear_rotation(stop_event):
    loop_count = 0
    last_use_times = {name: 0.0 for name in UTILITY_STAGGER}

    while not stop_event.is_set():
        wait_if_paused()
        if check_stop_condition(stop_event):
            break

        loop_count += 1
        current_time = time.time()
        grenade_mode = in_grenade_kit()
        status = get_status(grenade_mode)
        log_status(loop_count, status)

        # Keep mech commands rolling. MetaBattle pairs Conduit Surge with mech command;
        # we do this early every loop because these are top-row mech skills, not bar slots.
        for label, key in [
            ('Mech Skill 2 / Lightning Rod', MECH_COMMANDS['mech_skill_2']),
            ('Mech Skill 1 / Electric Artillery', MECH_COMMANDS['mech_skill_1']),
            ('Mech Skill 3', MECH_COMMANDS['mech_skill_3']),
        ]:
            if not cast(label, key, stop_event, wait=0.12):
                break

        if check_stop_condition(stop_event):
            break

        signet_ready = status['utilities_ready']['superconducting_signet']
        signet_elapsed = current_time - last_use_times['superconducting_signet']
        if signet_ready and signet_elapsed > UTILITY_STAGGER['superconducting_signet']:
            if not cast('Superconducting Signet', key_mapping['numpad8'], stop_event, wait=0.20):
                break
            last_use_times['superconducting_signet'] = time.time()

        if grenade_mode:
            # Grenade Kit priorities from MetaBattle: Shrapnel -> Poison -> Freeze.
            s2_ready = status['slot_ready']['slot_2']  # Shrapnel Grenade
            s4_ready = status['slot_ready']['slot_4']  # Freeze Grenade
            s5_ready = status['slot_ready']['slot_5']  # Poison Grenade

            if s2_ready:
                if not cast('Shrapnel Grenade (Kit 2)', key_mapping['numpad2'], stop_event):
                    break

            if s5_ready:
                if not cast('Poison Grenade (Kit 5)', key_mapping['numpad5'], stop_event):
                    break

            if s4_ready:
                if not cast('Freeze Grenade (Kit 4)', key_mapping['numpad4'], stop_event):
                    break

            # Nothing useful in kit => exit kit (weapon swap)
            if not s2_ready and not s4_ready and not s5_ready:
                if not cast('Grenade empty -> Weapon Swap out', key_mapping['f1'], stop_event, wait=0.25):
                    break

            if not cast('Auto-attack filler (Kit 1)', key_mapping['numpad1'], stop_event, wait=0.08):
                break

        else:
            # Spear priorities: Conduit Surge first, then Devastator and remaining damage skills.
            s2_ready = status['slot_ready']['slot_2']  # Conduit Surge
            s3_ready = status['slot_ready']['slot_3']
            s4_ready = status['slot_ready']['slot_4']  # Devastator-ish priority slot

            if s2_ready:
                if not cast('Conduit Surge (Spear 2)', key_mapping['numpad2'], stop_event):
                    break

            if s4_ready:
                if not cast('Devastator / Spear 4', key_mapping['numpad4'], stop_event):
                    break

            if s3_ready:
                if not cast('Spear 3', key_mapping['numpad3'], stop_event):
                    break

            # If nothing on spear side is lit, go grenade kit.
            if not s2_ready and not s3_ready and not s4_ready:
                if not cast('Spear empty -> Grenade Kit', key_mapping['numpad7'], stop_event, wait=0.30):
                    break

            if not cast('Auto-attack filler (Spear 1)', key_mapping['numpad1'], stop_event, wait=0.08):
                break

        time.sleep(LOOP_DELAY)

    log_and_print('info', "Stopping Condition Mechanist Spear rotation")


def run(stop_event):
    log_and_print('info', "=" * 70)
    log_and_print('info', "CONDITION MECHANIST - SPEAR / GRENADE KIT BUILD")
    log_and_print('info', "Hold NumPad1 to run rotation")
    log_and_print('info', "=" * 70)

    while not stop_event.is_set():
        wait_if_paused()
        if stop_event.is_set():
            break
        if keyboard.is_pressed(STOP_KEY):
            log_and_print('info', "NumPad1 pressed - starting rotation loop")
            condition_mechanist_spear_rotation(stop_event)
        time.sleep(0.1)
