"""
Reaper - Power Greatsword Reaper (Open World)
MetaBattle reference: https://metabattle.com/wiki/Build:Reaper_-_Power_Greatsword_Reaper

Focus: Strike damage with high cleave; simple melee rotation.
Primary set: Greatsword. Secondary: Sword/Sword (optional; handled as same weapon bar)
Utilities (default): Well of Suffering, Well of Darkness, Spectral Grasp, Chilled to the Bone!, Your Soul Is Mine!
"""

import sys
import time
import keyboard
from libs.pixel_get_color import get_color as pixel_get_color
from libs.keyboard_actions_monitored import button_mash
from libs.key_mapping import key_mapping
from libs.logger import get_logger
from libs.pause import wait_if_paused

try:
    from libs.config_manager import get_config_manager
except ImportError:
    get_config_manager = None

logger = get_logger('power_reaper_greatsword')
logger.propagate = True

# Enable/disable detailed logging (keep default False; flip to True for verbose prints)
ENABLE_DETAILED_LOGGING = False


def log_and_print(level, msg):
    getattr(logger, level)(msg)
    if ENABLE_DETAILED_LOGGING:
        print(f"[{level.upper()}] {msg}", flush=True)
        sys.stdout.flush()


# Screen-space coordinates (matches our standard amalgam baseline)
DEFAULT_COORDS = {
    # Weapon bar (1-5)
    'slot_1': (2587, 1013),
    'slot_2': (2625, 1013),
    'slot_3': (2686, 1013),
    'slot_4': (2743, 1013),
    'slot_5': (2801, 1013),

    # Utility bar (6-0)
    'utility_heal': (2858, 1013),   # 6
    'utility_1': (2920, 1013),      # 7
    'utility_2': (2980, 1013),      # 8
    'utility_3': (3040, 1013),      # 9
    'utility_elite': (3100, 1013),  # 0
    # Shroud state indicator (non-black when in shroud)
    'shroud_indicator': (2027, 1026),
}

BAR_SLOTS = {
    'slot_2': DEFAULT_COORDS['slot_2'],
    'slot_3': DEFAULT_COORDS['slot_3'],
    'slot_4': DEFAULT_COORDS['slot_4'],
    'slot_5': DEFAULT_COORDS['slot_5'],
}


def resolve_key(path: str, default):
    if get_config_manager:
        try:
            config = get_config_manager()
            value = config.get(path, None)
            if value:
                return value
        except Exception:
            logger.warning(f"Failed to resolve config key '{path}'", exc_info=True)
    return default


def normalize_key_value(value):
    if value is None:
        return None
    if isinstance(value, int):
        return value
    key = str(value).strip().lower()
    if key in key_mapping:
        return key_mapping[key]
    return key


def build_keychain(*keys):
    chain = []
    for key in keys:
        if not key:
            continue
        if isinstance(key, (list, tuple)):
            for sub_key in key:
                normalized = normalize_key_value(sub_key)
                if normalized is not None:
                    chain.append(normalized)
        else:
            normalized = normalize_key_value(key)
            if normalized is not None:
                chain.append(normalized)
    return chain


def ensure_iterable(value):
    return value if isinstance(value, (list, tuple)) else [value]


# Weapon / utility keys (with config fallbacks)
WEAPON_KEY_OPTIONS = {
    'slot_1': build_keychain(resolve_key('games.GuildWars2.keybinds.reaper.weapon_1', key_mapping.get('numpad1')), key_mapping.get('numpad1')),
    'slot_2': build_keychain(resolve_key('games.GuildWars2.keybinds.reaper.weapon_2', key_mapping.get('numpad2')), key_mapping.get('numpad2')),
    'slot_3': build_keychain(resolve_key('games.GuildWars2.keybinds.reaper.weapon_3', key_mapping.get('numpad3')), key_mapping.get('numpad3')),
    'slot_4': build_keychain(resolve_key('games.GuildWars2.keybinds.reaper.weapon_4', key_mapping.get('numpad4')), key_mapping.get('numpad4')),
    'slot_5': build_keychain(resolve_key('games.GuildWars2.keybinds.reaper.weapon_5', key_mapping.get('numpad5')), key_mapping.get('numpad5')),
}

UTILITY_KEY_OPTIONS = {
    'heal': build_keychain(resolve_key('games.GuildWars2.keybinds.reaper.heal', key_mapping.get('numpad6')), key_mapping.get('numpad6')),
    'well_suffering': build_keychain(resolve_key('games.GuildWars2.keybinds.reaper.well_suffering', key_mapping.get('numpad7')), key_mapping.get('numpad7')),
    'well_darkness': build_keychain(resolve_key('games.GuildWars2.keybinds.reaper.well_darkness', key_mapping.get('numpad8')), key_mapping.get('numpad8')),
    'spectral_grasp': build_keychain(resolve_key('games.GuildWars2.keybinds.reaper.spectral_grasp', key_mapping.get('numpad9')), key_mapping.get('numpad9')),
    'elite': build_keychain(resolve_key('games.GuildWars2.keybinds.reaper.elite', key_mapping.get('numpad0')), key_mapping.get('numpad0')),
}

# Reaper shroud toggle; default to F1 if not overridden
REAPER_KEYS = {
    'shroud_toggle': build_keychain(resolve_key('games.GuildWars2.keybinds.reaper.shroud', '1'), '1'),
}

# Simple cooldown estimates (seconds) for utilities we press "on CD"
COOLDOWNS = {
    'well_suffering': 25.0,
    'well_darkness': 35.0,
    'spectral_grasp': 20.0,
    'elite': 60.0,
    'heal': 20.0,
}

# Pixel thresholds
SKILL_READY_PIXEL_MIN = 40
SKILL_ON_COOLDOWN_MAX = 75
GS_READY_THRESHOLD_HEAVY = 270   # GS5/GS4 bias slightly looser
GS_READY_THRESHOLD_MID = 240     # GS2/GS3 moderate threshold
MIN_SPECTRAL_INTERVAL = 7.0      # debounce for Spectral Grasp
ENABLE_SPECTRAL = False          # disable on golem for max DPS

# Control key to hold for loop
STOP_KEY = key_mapping.get('numpad1', 'numpad1')


def check_stop_condition(stop_event):
    return not keyboard.is_pressed(STOP_KEY) or stop_event.is_set()


def get_slot_brightness(slot_name):
    coords = BAR_SLOTS.get(slot_name)
    if not coords:
        return 0
    color = pixel_get_color(coords[0], coords[1])
    return sum(color) if color else 0


def check_skill_available(coords, threshold=None):
    color = pixel_get_color(coords[0], coords[1])
    if color is None:
        return False
    brightness = sum(color)
    if coords in BAR_SLOTS.values():
        return brightness > 30  # any non-black implies usable
    if threshold is None:
        return brightness > SKILL_READY_PIXEL_MIN
    return brightness > threshold or brightness > SKILL_READY_PIXEL_MIN


def is_shroud_active():
    """
    Determine if Reaper's Shroud is currently active by sampling a fixed UI pixel.
    Assumes DEFAULT_COORDS['shroud'] points to a non-black pixel when in shroud.
    """
    c = pixel_get_color(*DEFAULT_COORDS['shroud_indicator'])
    return bool(c) and sum(c) > 0


def wait_until_on_cooldown(coords, timeout_seconds=1.2, poll_seconds=0.05):
    if coords is None:
        return True
    start = time.time()
    while (time.time() - start) < timeout_seconds:
        color = pixel_get_color(coords[0], coords[1])
        if color is None:
            return True
        if sum(color) <= SKILL_ON_COOLDOWN_MAX:
            return True
        time.sleep(poll_seconds)
    return False


def cast_skill(key_candidates, coords, presses=2, delay=0.05, wait_timeout=1.0):
    if not key_candidates:
        return False
    for key in ensure_iterable(key_candidates):
        if button_mash(key, presses=presses, delay=delay, stop_check=None):
            if wait_until_on_cooldown(coords, timeout_seconds=wait_timeout):
                return True
    return False


def tap_keys(key_candidates, presses=1, delay=0.03):
    for key in ensure_iterable(key_candidates):
        if button_mash(key, presses=presses, delay=delay, stop_check=None):
            return True
    return False


def reaper_shroud_burst(burst_seconds=4.0, adaptive_exit=True, min_shroud_time=2.5):
    """
    Timed shroud window (no pixel detection for shroud state).
    Priority: 4 (Soul Spiral) > 5 (Exec Scythe for CC) > 3 (Death's Charge) > 2 > 1 spam
    """
    start = time.time()
    # Small settle to ensure shroud state is active before sending skills
    time.sleep(0.12)
    # Immediate openers
    tap_keys(WEAPON_KEY_OPTIONS['slot_4'], presses=4, delay=0.06)  # Soul Spiral
    tap_keys(WEAPON_KEY_OPTIONS['slot_5'], presses=3, delay=0.06)  # Exec Scythe
    tap_keys(WEAPON_KEY_OPTIONS['slot_3'], presses=3, delay=0.06)  # Death's Charge
    # Fill for remainder
    while True:
        elapsed = time.time() - start
        if elapsed >= burst_seconds:
            break
        # Optional adaptive exit: if GS5 appears ready (even during shroud bar),
        # exit early after a minimum shroud time to prioritise the next GS5.
        if adaptive_exit and elapsed >= min_shroud_time:
            gs5_bright = check_skill_available(BAR_SLOTS['slot_5'], threshold=GS_READY_THRESHOLD_HEAVY)
            if gs5_bright:
                break
        tap_keys(WEAPON_KEY_OPTIONS['slot_2'], presses=2, delay=0.05)
        tap_keys(WEAPON_KEY_OPTIONS['slot_1'], presses=1, delay=0.03)
        time.sleep(0.07)


def power_reaper_gs_rotation(stop_event):
    """
    Open World Power Reaper GS priority:
    Utilities on cooldown, GS priority 5 > 4 > 2 > 3, frequent shroud bursts.
    """
    last_use = {name: 0.0 for name in COOLDOWNS}
    last_shroud_attempt = 0.0
    shroud_attempt_interval = 8.0
    shroud_window_seconds = 7.0

    loop_count = 0
    while not stop_event.is_set():
        loop_count += 1
        wait_if_paused()
        if check_stop_condition(stop_event):
            break

        now = time.time()
        slot_brightness = {
            slot: get_slot_brightness(slot) for slot in ['slot_2', 'slot_3', 'slot_4', 'slot_5']
        }

        log_and_print(
            'info',
            (
                f"--- LOOP {loop_count} --- "
                f"Slots={{2:{slot_brightness['slot_2']}, 3:{slot_brightness['slot_3']}, "
                f"4:{slot_brightness['slot_4']}, 5:{slot_brightness['slot_5']}}}"
            )
        )

        # Utilities (DPS-focused): skip heal for max DPS

        # Pre-burst wells only (avoid stealing GS windows)
        if now - last_use['well_suffering'] >= COOLDOWNS['well_suffering']:
            gs5_ready_now = check_skill_available(BAR_SLOTS['slot_5'], threshold=GS_READY_THRESHOLD_HEAVY)
            gs4_ready_now = check_skill_available(BAR_SLOTS['slot_4'], threshold=GS_READY_THRESHOLD_HEAVY)
            near_shroud = (now - last_shroud_attempt) >= (shroud_attempt_interval - 0.4)
            if (not gs5_ready_now and not gs4_ready_now) or near_shroud:
                if cast_skill(UTILITY_KEY_OPTIONS['well_suffering'], None, presses=2, delay=0.06, wait_timeout=1.0):
                    last_use['well_suffering'] = now
                    log_and_print('info', ">>> WELL OF SUFFERING")

        if now - last_use['well_darkness'] >= COOLDOWNS['well_darkness']:
            gs5_ready_now = check_skill_available(BAR_SLOTS['slot_5'], threshold=GS_READY_THRESHOLD_HEAVY)
            gs4_ready_now = check_skill_available(BAR_SLOTS['slot_4'], threshold=GS_READY_THRESHOLD_HEAVY)
            near_shroud = (now - last_shroud_attempt) >= (shroud_attempt_interval - 0.4)
            if (not gs5_ready_now and not gs4_ready_now) or near_shroud:
                if cast_skill(UTILITY_KEY_OPTIONS['well_darkness'], None, presses=2, delay=0.06, wait_timeout=1.0):
                    last_use['well_darkness'] = now
                    log_and_print('info', ">>> WELL OF DARKNESS")

        # Debounced Spectral Grasp for minimal DPS disruption
        if ENABLE_SPECTRAL and now - last_use['spectral_grasp'] >= max(COOLDOWNS['spectral_grasp'], MIN_SPECTRAL_INTERVAL):
            gs5_ready_now = check_skill_available(BAR_SLOTS['slot_5'], threshold=GS_READY_THRESHOLD_HEAVY)
            gs4_ready_now = check_skill_available(BAR_SLOTS['slot_4'], threshold=GS_READY_THRESHOLD_HEAVY)
            if not gs5_ready_now and not gs4_ready_now:
                if cast_skill(UTILITY_KEY_OPTIONS['spectral_grasp'], None, presses=1, delay=0.05, wait_timeout=0.6):
                    last_use['spectral_grasp'] = now
                    log_and_print('info', ">>> SPECTRAL GRASP (pull)")

        # Elite: only meaningful as pre-shroud for golem DPS
        # handled below in pre-shroud alignment

        # Attempt a shroud burst based on timer or when heavy GS skills are not ready
        if (now - last_shroud_attempt) >= shroud_attempt_interval and not is_shroud_active():
            gs5_ready = check_skill_available(BAR_SLOTS['slot_5'], threshold=GS_READY_THRESHOLD_HEAVY)
            gs4_ready = check_skill_available(BAR_SLOTS['slot_4'], threshold=GS_READY_THRESHOLD_HEAVY)
            gs2_ready = check_skill_available(BAR_SLOTS['slot_2'], threshold=GS_READY_THRESHOLD_MID)
            # Prefer to use GS4/5 if available; otherwise, enter shroud.
            # If timer elapsed, allow shroud even if GS2 is ready to avoid sitting capped on lifeforce.
            if not gs5_ready and not gs4_ready:
                if now - last_use['elite'] >= COOLDOWNS['elite']:
                    if cast_skill(UTILITY_KEY_OPTIONS['elite'], None, presses=2, delay=0.06, wait_timeout=1.0):
                        last_use['elite'] = now
                        log_and_print('info', ">>> CHILLED TO THE BONE! (pre-shroud)")
                if tap_keys(REAPER_KEYS['shroud_toggle'], presses=1, delay=0.04):
                    log_and_print('info', ">>> ENTER SHROUD")
                    # Wait briefly for shroud indicator to confirm
                    t0 = time.time()
                    while time.time() - t0 < 0.3 and not is_shroud_active():
                        time.sleep(0.02)
                    reaper_shroud_burst(burst_seconds=shroud_window_seconds)
                    # Exit shroud only if still active
                    if is_shroud_active():
                        tap_keys(REAPER_KEYS['shroud_toggle'], presses=1, delay=0.04)
                    log_and_print('info', ">>> EXIT SHROUD")
                    last_shroud_attempt = now
                    time.sleep(0.1)
                    continue

        # GS priority (5 > 4 > 2 > 3), check readiness via pixel brightness
        priority = [('slot_5', '5'), ('slot_4', '4'), ('slot_2', '2'), ('slot_3', '3')]
        did_cast = False
        for slot_key, label in priority:
            coords = BAR_SLOTS[slot_key]
            threshold = GS_READY_THRESHOLD_HEAVY if label in ('5', '4') else GS_READY_THRESHOLD_MID
            if check_skill_available(coords, threshold=threshold):
                # Heavier hitters get more presses and slightly longer confirmation
                presses = 4 if label in ('5', '4') else 3
                if cast_skill(WEAPON_KEY_OPTIONS[f'slot_{label}'], coords, presses=presses, delay=0.06, wait_timeout=1.3):
                    log_and_print('info', f">>> GS {label}")
                    did_cast = True
                    break
        if not did_cast:
            # Filler auto
            cast_skill(WEAPON_KEY_OPTIONS['slot_1'], DEFAULT_COORDS['slot_1'], presses=1, delay=0.02, wait_timeout=0.4)

        time.sleep(0.16)

    log_and_print('info', "Stopping Power Reaper GS rotation")


def run(stop_event):
    logger.info("Power Reaper GS spec started")
    log_and_print('info', "=" * 68)
    log_and_print('info', "REAPER - POWER GREATSWORD (OPEN WORLD)")
    log_and_print('info', "Hold NumPad1 to run rotation")
    log_and_print('info', "=" * 68)

    while not stop_event.is_set():
        wait_if_paused()
        if stop_event.is_set():
            break
        if keyboard.is_pressed(STOP_KEY):
            log_and_print('info', "NumPad1 pressed - starting rotation loop")
            try:
                power_reaper_gs_rotation(stop_event)
            except Exception as exc:
                log_and_print('error', f"Unexpected error in Power Reaper GS rotation: {exc}")
                raise
        time.sleep(0.05)

    logger.info("Power Reaper GS spec ended")


