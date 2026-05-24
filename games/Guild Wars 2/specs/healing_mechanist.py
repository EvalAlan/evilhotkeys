"""
Mechanist - Alacrity Support Healer
MetaBattle reference: https://metabattle.com/wiki/Build:Mechanist_-_Alacrity_Support_Healer

Intent:
- Maintain alacrity/barrier via Barrier Burst on cooldown.
- Prioritize Short Bow 2-4 off cooldown for sustain boons/healing.
- Pair key kit skills with matching short bow cooldown windows:
  * Short Bow 2 + Med Kit Bandage Blast
  * Short Bow 3 + Elixir Gun Super Elixir
  * Short Bow 4 + Med Kit Infusion Bomb
- Use Mortar 5 (Elixir Shell) as periodic water field; hold/skip if unstable.
- Preserve fast Acid Bomb-style cancel behavior when using blast leap (weapon swap instantly).
"""

import time
import keyboard

from libs.keyboard_actions import button_mash
from libs.key_mapping import key_mapping
from libs.logger import get_logger
from libs.pause import wait_if_paused
from libs.pixel_get_color import get_color as pixel_get_color

logger = get_logger("healing_mechanist")
logger.propagate = True

# Triple-monitor baseline used by existing specs.
COORDS = {
    "slot_2": (2625, 1013),
    "slot_3": (2686, 1013),
    "slot_4": (2742, 1015),
    "slot_5": (2799, 1015),
    "indicator_med_kit": (2960, 1035),
    "indicator_elixir_gun": (3015, 1035),
    "indicator_mortar_kit": (3080, 1035),
    "kit_active_indicator": (2535, 1030),
}

STOP_KEY = key_mapping.get("numpad1", "numpad1")

# Conservative cadence. Reliability over speed.
MIN_LOOP_DELAY = 0.12
KIT_SWITCH_SETTLE = 0.35
POST_CAST_DELAY = 0.18

# Priority cooldown gates (seconds). Deliberately slower than animation minimums.
GATES = {
    "barrier_burst": 10.5,
    "crisis_zone": 25.0,
    "barrier_signet": 24.0,
    "shortbow_2": 5.7,
    "shortbow_3": 8.0,
    "shortbow_4": 11.8,
    "med_4": 11.8,
    "med_5": 17.0,
    "elixir_5": 15.8,
    "elixir_4": 11.8,
    "mortar_5": 17.5,
    "acid_cancel": 19.0,
}


def check_stop_condition(stop_event):
    return stop_event.is_set() or not keyboard.is_pressed(STOP_KEY)


def is_ready(slot_name: str) -> bool:
    color = pixel_get_color(*COORDS[slot_name])
    return bool(color and color != (0, 0, 0) and sum(color) > 60)


def _press(key, presses=1, delay=0.04):
    return button_mash(key, presses=presses, delay=delay, stop_check=None)


def _tap_and_wait(key, presses=1, delay=0.04, wait=POST_CAST_DELAY):
    ok = _press(key, presses=presses, delay=delay)
    if ok:
        time.sleep(wait)
    return ok


def detect_active_kit() -> str:
    # White means we're on a kit bar, otherwise shortbow.
    kit_active = pixel_get_color(*COORDS["kit_active_indicator"])
    if kit_active != (255, 255, 255):
        return "shortbow"

    elixir = pixel_get_color(*COORDS["indicator_elixir_gun"])
    med = pixel_get_color(*COORDS["indicator_med_kit"])
    mortar = pixel_get_color(*COORDS["indicator_mortar_kit"])

    if elixir == (255, 255, 255):
        return "elixir_gun"
    if med == (255, 255, 255):
        return "med_kit"
    if mortar and sum(mortar) > 220:
        return "mortar_kit"
    return "shortbow"


def ensure_kit(target: str) -> bool:
    current = detect_active_kit()
    if current == target:
        return True

    if target == "shortbow":
        _tap_and_wait(key_mapping["f1"], wait=KIT_SWITCH_SETTLE)
    elif target == "med_kit":
        _tap_and_wait(key_mapping["numpad6"], wait=KIT_SWITCH_SETTLE)
    elif target == "elixir_gun":
        _tap_and_wait(key_mapping["numpad7"], wait=KIT_SWITCH_SETTLE)
    elif target == "mortar_kit":
        _tap_and_wait(key_mapping["numpad0"], wait=KIT_SWITCH_SETTLE)
    else:
        return False

    return detect_active_kit() == target


def cancel_acid_bomb_like_motion():
    # Keep this explicit and fast; do not globally speed the rotation.
    _press(key_mapping.get("f1", "f1"), presses=1, delay=0.02)
    time.sleep(0.10)


def try_cast(timers, tag, gate, key, slot=None, presses=1, wait=POST_CAST_DELAY):
    now = time.time()
    if now - timers.get(tag, 0) < gate:
        return False
    if slot and not is_ready(slot):
        return False
    if not _tap_and_wait(key, presses=presses, wait=wait):
        return False
    timers[tag] = now
    return True


def healing_mechanist_rotation(stop_event):
    timers = {k: 0.0 for k in GATES}

    while not stop_event.is_set():
        wait_if_paused()
        if check_stop_condition(stop_event):
            break

        # Always keep mech commands flowing first.
        try_cast(timers, "barrier_burst", GATES["barrier_burst"], key_mapping.get("3", "3"))
        try_cast(timers, "crisis_zone", GATES["crisis_zone"], key_mapping.get("2", "2"))

        # Short bow baseline (2-4), 5 intentionally held unless manually needed.
        ensure_kit("shortbow")
        try_cast(timers, "shortbow_2", GATES["shortbow_2"], key_mapping["numpad2"], slot="slot_2")
        try_cast(timers, "shortbow_3", GATES["shortbow_3"], key_mapping["numpad3"], slot="slot_3")
        sb4_cast = try_cast(timers, "shortbow_4", GATES["shortbow_4"], key_mapping["numpad4"], slot="slot_4")

        # Pairing: SB4 window -> Med Kit Infusion Bomb then Bandage Blast.
        if sb4_cast or (time.time() - timers["med_4"]) >= GATES["med_4"]:
            if ensure_kit("med_kit"):
                try_cast(timers, "med_4", GATES["med_4"], key_mapping["numpad4"], slot="slot_4")
                try_cast(timers, "med_5", GATES["med_5"], key_mapping["numpad5"], slot="slot_5")

        # Pairing: SB3 window -> Super Elixir, optional Fumigate.
        if (time.time() - timers["elixir_5"]) >= GATES["elixir_5"] or (time.time() - timers["shortbow_3"]) < 1.1:
            if ensure_kit("elixir_gun"):
                se_cast = try_cast(timers, "elixir_5", GATES["elixir_5"], key_mapping["numpad5"], slot="slot_5", wait=0.25)
                if se_cast:
                    # Light cleanse support.
                    try_cast(timers, "elixir_4", GATES["elixir_4"], key_mapping["numpad4"], slot="slot_4")

        # Mortar 5 periodic water field, then blast via Acid Bomb-style cancel path.
        if (time.time() - timers["mortar_5"]) >= GATES["mortar_5"]:
            if ensure_kit("mortar_kit"):
                mortar_cast = try_cast(timers, "mortar_5", GATES["mortar_5"], key_mapping["numpad5"], slot="slot_5", wait=0.25)
                if mortar_cast and ensure_kit("elixir_gun"):
                    # Controlled usage only; preserve explicit fast cancel.
                    if try_cast(timers, "acid_cancel", GATES["acid_cancel"], key_mapping["numpad4"], slot="slot_4", wait=0.16):
                        cancel_acid_bomb_like_motion()

        # Barrier Signet as periodic safety net / alacrity gap fill.
        try_cast(timers, "barrier_signet", GATES["barrier_signet"], key_mapping["numpad8"])

        # Return to shortbow as neutral state.
        ensure_kit("shortbow")
        time.sleep(MIN_LOOP_DELAY)

    logger.info("Stopping Mechanist Alacrity Support Healer rotation")


def run(stop_event):
    logger.info("Healing Mechanist spec started")
    while not stop_event.is_set():
        wait_if_paused()
        if keyboard.is_pressed(STOP_KEY):
            try:
                healing_mechanist_rotation(stop_event)
            except Exception:
                logger.exception("Unexpected error in Healing Mechanist rotation")
                raise
        time.sleep(0.05)
    logger.info("Healing Mechanist spec ended")
