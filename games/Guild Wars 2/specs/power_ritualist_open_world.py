"""
Ritualist - Power Ritualist (Open World)
MetaBattle reference: https://metabattle.com/wiki/Build:Ritualist_-_Power_Ritualist_open_world
Focus: Strike damage, Shroud weaving, simple utility uptime
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

logger = get_logger('power_ritualist')
logger.propagate = True

ENABLE_DETAILED_LOGGING = False


def log_and_print(level, msg):
    getattr(logger, level)(msg)
    if ENABLE_DETAILED_LOGGING:
        print(f"[{level.upper()}] {msg}", flush=True)
        sys.stdout.flush()


# Coordinates tuned to match existing triple-monitor baseline used in other specs
DEFAULT_COORDS = {
    # Weapon bar 1-5
    'slot_1': (2587, 1013),
    'slot_2': (2625, 1013),
    'slot_3': (2686, 1013),
    'slot_4': (2743, 1013),
    'slot_5': (2801, 1013),

    # Utility (6-0)
    'utility_heal': (2652, 1013),   # Heal
    'utility_1': (3007, 1013),      # Bone Minions (default)
    'utility_2': (3070, 1013),      # Splinter Weapon
    'utility_3': (3116, 1013),      # Nightmare Weapon
    'utility_elite': (3171, 1013),  # Summon Flesh Golem (or preferred elite)

    # Shroud indicator pixel (non-black => in shroud)
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


def ensure_iterable(value):
    return value if isinstance(value, (list, tuple)) else [value]


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


def is_key_in_chain(chain, target: str) -> bool:
    target_norm = normalize_key_value(target)
    for key in ensure_iterable(chain):
        if key == target_norm:
            return True
    return False


# Default to numpad 1-5 to match prior specs; override in config
WEAPON_KEY_OPTIONS = {
    'slot_1': build_keychain(resolve_key('games.GuildWars2.keybinds.ritualist.weapon_1', key_mapping.get('numpad1')), key_mapping.get('numpad1')),
    'slot_2': build_keychain(resolve_key('games.GuildWars2.keybinds.ritualist.weapon_2', key_mapping.get('numpad2')), key_mapping.get('numpad2')),
    'slot_3': build_keychain(resolve_key('games.GuildWars2.keybinds.ritualist.weapon_3', key_mapping.get('numpad3')), key_mapping.get('numpad3')),
    'slot_4': build_keychain(resolve_key('games.GuildWars2.keybinds.ritualist.weapon_4', key_mapping.get('numpad4')), key_mapping.get('numpad4')),
    'slot_5': build_keychain(resolve_key('games.GuildWars2.keybinds.ritualist.weapon_5', key_mapping.get('numpad5')), key_mapping.get('numpad5')),
}

UTILITY_KEY_OPTIONS = {
    'heal': build_keychain(resolve_key('games.GuildWars2.keybinds.ritualist.heal', key_mapping.get('numpad6')), key_mapping.get('numpad6')),
    'utility_1': build_keychain(resolve_key('games.GuildWars2.keybinds.ritualist.utility_1', key_mapping.get('numpad7')), key_mapping.get('numpad7')),
    'utility_2': build_keychain(resolve_key('games.GuildWars2.keybinds.ritualist.utility_2', key_mapping.get('numpad8')), key_mapping.get('numpad8')),
    'utility_3': build_keychain(resolve_key('games.GuildWars2.keybinds.ritualist.utility_3', key_mapping.get('numpad9')), key_mapping.get('numpad9')),
    'elite': build_keychain(resolve_key('games.GuildWars2.keybinds.ritualist.elite', key_mapping.get('numpad0')), key_mapping.get('numpad0')),
}

# Shroud toggle: default to '1' (like Reaper customization you preferred), override if needed
RITUALIST_KEYS = {
    # User binding: shroud on '1' (number row). Override via config if needed.
    'shroud_toggle': build_keychain(resolve_key('games.GuildWars2.keybinds.ritualist.shroud', '1'), '1'),
}

# Shroud bar mapping per user (NumPad activates the bar while in shroud):
# NumPad1 Essence Blast, NumPad2 Anguish, NumPad3 Wanderlust, NumPad4 Preservation, NumPad5 Summon Spirits
SHROUD_KEYS = {
    'slot_1': build_keychain(resolve_key('games.GuildWars2.keybinds.ritualist.shroud_1', key_mapping.get('numpad1')), key_mapping.get('numpad1')),
    'slot_2': build_keychain(resolve_key('games.GuildWars2.keybinds.ritualist.shroud_2', key_mapping.get('numpad2')), key_mapping.get('numpad2')),
    'slot_3': build_keychain(resolve_key('games.GuildWars2.keybinds.ritualist.shroud_3', key_mapping.get('numpad3')), key_mapping.get('numpad3')),
    'slot_4': build_keychain(resolve_key('games.GuildWars2.keybinds.ritualist.shroud_4', key_mapping.get('numpad4')), key_mapping.get('numpad4')),
    'slot_5': build_keychain(resolve_key('games.GuildWars2.keybinds.ritualist.shroud_5', key_mapping.get('numpad5')), key_mapping.get('numpad5')),
}

# Timings and knobs (configurable)
CONFIG_DEFAULTS = {
    'gs_thresholds': {'heavy': 250, 'mid': 220},
    'shroud_window_seconds': 6.0,
    'shroud_attempt_interval': 9.0,
    'min_shroud_time': 2.5,
    'shroud_settle_ms': 350,
    'press_delay': 0.06,
    'presses_gs_heavy': 4,
    'presses_gs_mid': 3,
    'presses_shroud_1': 4,
    'presses_shroud_2': 4,
    'presses_shroud_3': 2,
    'presses_shroud_4': 2,
    'presses_shroud_5': 2,
    'enable_minions': True,
    'enable_heal': False,
    'heal_interval_seconds': 30.0,
}


def get_knob(path, fallback_key):
    if get_config_manager:
        try:
            cfg = get_config_manager()
            val = cfg.get(path, None)
            if val is not None:
                return val
        except Exception:
            pass
    return CONFIG_DEFAULTS[fallback_key]


GS_READY_THRESHOLD_HEAVY = int(get_knob('games.GuildWars2.ritualist.gs_thresholds.heavy', 'gs_thresholds')['heavy']
                               if isinstance(get_knob('games.GuildWars2.ritualist.gs_thresholds', 'gs_thresholds'), dict)
                               else CONFIG_DEFAULTS['gs_thresholds']['heavy'])
GS_READY_THRESHOLD_MID = int(get_knob('games.GuildWars2.ritualist.gs_thresholds.mid', 'gs_thresholds')['mid']
                             if isinstance(get_knob('games.GuildWars2.ritualist.gs_thresholds', 'gs_thresholds'), dict)
                             else CONFIG_DEFAULTS['gs_thresholds']['mid'])

SHROUD_WINDOW_SECONDS = float(get_knob('games.GuildWars2.ritualist.shroud.window_seconds', 'shroud_window_seconds'))
SHROUD_ATTEMPT_INTERVAL = float(get_knob('games.GuildWars2.ritualist.shroud.interval', 'shroud_attempt_interval'))
MIN_SHROUD_TIME = float(get_knob('games.GuildWars2.ritualist.shroud.min_active', 'min_shroud_time'))
SHROUD_SETTLE_MS = int(get_knob('games.GuildWars2.ritualist.shroud.settle_ms', 'shroud_settle_ms'))
GLOBAL_PRESS_DELAY = float(get_knob('games.GuildWars2.ritualist.presses.delay', 'press_delay'))
ENABLE_MINIONS = bool(get_knob('games.GuildWars2.ritualist.enable_minions', 'enable_minions'))
ENABLE_HEAL = bool(get_knob('games.GuildWars2.ritualist.enable_heal', 'enable_heal'))
HEAL_INTERVAL = float(get_knob('games.GuildWars2.ritualist.heal_interval_seconds', 'heal_interval_seconds'))

# Utility recast timers (simple cadence model, avoids pixel dependency)
COOLDOWNS = {
    'heal': 22.0,
    'utility_1': 15.0,     # Bone Minions re-summon (slightly tighter to avoid downtime)
    'utility_2': 18.0,     # Splinter Weapon
    'utility_3': 18.0,     # Nightmare Weapon
    'elite': 60.0,         # Flesh Golem active
}

# Brightness gates
SKILL_ON_COOLDOWN_MAX = 75

# Stop key (hold to run)
STOP_KEY = key_mapping.get('numpad1', 'numpad1')


def check_stop_condition(stop_event):
    return not keyboard.is_pressed(STOP_KEY) or stop_event.is_set()


def get_brightness(x, y):
    color = pixel_get_color(x, y)
    return sum(color) if color else 0


def is_shroud_active():
    sx, sy = DEFAULT_COORDS['shroud_indicator']
    return get_brightness(sx, sy) > 5


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


def cast_skill(key_candidates, coords, presses=2, delay=None, wait_timeout=1.0):
    if not key_candidates:
        return False
    use_delay = GLOBAL_PRESS_DELAY if delay is None else delay
    for key in ensure_iterable(key_candidates):
        if button_mash(key, presses=presses, delay=use_delay, stop_check=None):
            if coords is None or wait_until_on_cooldown(coords, timeout_seconds=wait_timeout):
                return True
    return False


def tap_keys(key_candidates, presses=1, delay=None):
    use_delay = GLOBAL_PRESS_DELAY if delay is None else delay
    for key in ensure_iterable(key_candidates):
        if button_mash(key, presses=presses, delay=use_delay, stop_check=None):
            return True
    return False


def check_skill_available(coords, threshold=250):
    color = pixel_get_color(coords[0], coords[1])
    if color is None:
        return False
    brightness = sum(color)
    return brightness >= threshold


def ritualist_shroud_burst(burst_seconds=None, adaptive_exit=True, min_shroud_time=None, last_use=None):
    """
    Timed Shroud window.
    IMPORTANT: If shroud toggle is bound to '1', DO NOT press '1' while in shroud.
    Otherwise (recommended per MetaBattle), spam 1 (Anguish) three times, then leave after ~1s.
    Adaptive exit: leave shroud if GS5 looks ready (to re-burst with Greatsword)
    """
    if burst_seconds is None:
        burst_seconds = SHROUD_WINDOW_SECONDS
    if min_shroud_time is None:
        min_shroud_time = MIN_SHROUD_TIME

    start = time.time()
    log_and_print('info', f"SHROUD: start burst window={burst_seconds:.2f}s, settle={SHROUD_SETTLE_MS}ms")
    time.sleep(SHROUD_SETTLE_MS / 1000.0)  # settle into shroud (avoid accidental re-toggle)

    toggle_is_one = is_key_in_chain(RITUALIST_KEYS['shroud_toggle'], '1')
    log_and_print('info', f"SHROUD: toggle_is_one={toggle_is_one}")

    # Force-weave Splinter/Nightmare at shroud entry to avoid starvation by Anguish
    if tap_keys(UTILITY_KEY_OPTIONS['utility_2'], presses=2, delay=0.05):
        log_and_print('info', ">>> SPLINTER WEAPON (entry weave - forced)")
        if last_use is not None:
            last_use['utility_2'] = time.time()
    if tap_keys(UTILITY_KEY_OPTIONS['utility_3'], presses=2, delay=0.05):
        log_and_print('info', ">>> NIGHTMARE WEAPON (entry weave - forced)")
        if last_use is not None:
            last_use['utility_3'] = time.time()

    # MetaBattle burst adapted to user's mapping (Anguish is slot 2 on NumPad):
    anguish_presses = int(get_knob('games.GuildWars2.ritualist.presses.shroud_2', 'presses_shroud_2'))
    log_and_print('info', f"SHROUD: sequence -> ANGUISH (slot2) x3 (presses={max(anguish_presses,3)}) delay=0.05")
    for _ in range(3):
        tap_keys(SHROUD_KEYS['slot_2'], presses=max(anguish_presses, 3), delay=0.05)
        time.sleep(0.12)
    time.sleep(0.9)
    # Optional: prime other spirits to autoattack
    tap_keys(SHROUD_KEYS['slot_3'], presses=int(get_knob('games.GuildWars2.ritualist.presses.shroud_3', 'presses_shroud_3')), delay=GLOBAL_PRESS_DELAY)
    tap_keys(SHROUD_KEYS['slot_4'], presses=int(get_knob('games.GuildWars2.ritualist.presses.shroud_4', 'presses_shroud_4')), delay=GLOBAL_PRESS_DELAY)

    last_weave_attempt = time.time()
    while True:
        elapsed = time.time() - start
        # End if time expired; ignore any UI state and force full window
        if elapsed >= burst_seconds:
            break

        # Optional adaptive exit disabled by default here for stability (force full window)
        if adaptive_exit and elapsed >= min_shroud_time:
            pass

        if toggle_is_one:
            # Spam 2/3; weave 4 on cooldown. Never press 1 in shroud (it's the toggle for this user).
            log_and_print('info', "SHROUD: loop -> 2,3,4")
            tap_keys(SHROUD_KEYS['slot_2'], presses=int(get_knob('games.GuildWars2.ritualist.presses.shroud_2', 'presses_shroud_2')), delay=GLOBAL_PRESS_DELAY)
            tap_keys(SHROUD_KEYS['slot_3'], presses=int(get_knob('games.GuildWars2.ritualist.presses.shroud_3', 'presses_shroud_3')), delay=GLOBAL_PRESS_DELAY)
            tap_keys(SHROUD_KEYS['slot_4'], presses=int(get_knob('games.GuildWars2.ritualist.presses.shroud_4', 'presses_shroud_4')), delay=GLOBAL_PRESS_DELAY)

        # While in shroud, also fire the Weapon Spell utilities on NumPad (Splinter/Nightmare)
        # to enable/refresh Innervate effects on spirits.
        if last_use is not None:
            now_ts = time.time()
            # Bone Minions: attempt mid-shroud as well so they don't sit dead
            if now_ts - last_use.get('utility_1', 0.0) >= COOLDOWNS['utility_1']:
                if cast_skill(UTILITY_KEY_OPTIONS['utility_1'], DEFAULT_COORDS['utility_1'], presses=2, delay=0.05, wait_timeout=1.5):
                    last_use['utility_1'] = now_ts
                    log_and_print('info', ">>> SUMMON BONE MINIONS (in shroud)")
            # Periodically re-attempt Splinter/Nightmare in shroud (every ~1.4s), forced taps
            if now_ts - last_weave_attempt >= 1.4:
                if tap_keys(UTILITY_KEY_OPTIONS['utility_2'], presses=1, delay=0.05):
                    log_and_print('info', ">>> SPLINTER WEAPON (in shroud - forced)")
                    if last_use is not None:
                        last_use['utility_2'] = now_ts
                if tap_keys(UTILITY_KEY_OPTIONS['utility_3'], presses=1, delay=0.05):
                    log_and_print('info', ">>> NIGHTMARE WEAPON (in shroud - forced)")
                    if last_use is not None:
                        last_use['utility_3'] = now_ts
                last_weave_attempt = now_ts
        time.sleep(0.06)


def power_ritualist_rotation(stop_event):
    """
    Open world DPS loop with Greatsword, weaving Shroud on a cadence and based on GS4/5 readiness.
    Utilities are timer-based (non-pixel) to maintain simple uptime.
    """
    loop_count = 0
    last_use = {name: 0.0 for name in COOLDOWNS}
    last_shroud_attempt = 0.0

    while not stop_event.is_set():
        wait_if_paused()
        if check_stop_condition(stop_event):
            break

        loop_count += 1
        now = time.time()

        slot_brightness = {
            2: get_brightness(*BAR_SLOTS['slot_2']),
            3: get_brightness(*BAR_SLOTS['slot_3']),
            4: get_brightness(*BAR_SLOTS['slot_4']),
            5: get_brightness(*BAR_SLOTS['slot_5']),
        }
        log_and_print('info', f"--- LOOP {loop_count} --- Slots={{2:{slot_brightness[2]}, 3:{slot_brightness[3]}, 4:{slot_brightness[4]}, 5:{slot_brightness[5]}}}")

        # Utilities (timer-driven; avoid pixel dependencies for reliability)
        if ENABLE_MINIONS and (now - last_use['utility_1'] >= COOLDOWNS['utility_1']):
            if cast_skill(UTILITY_KEY_OPTIONS['utility_1'], DEFAULT_COORDS['utility_1'], presses=2, delay=0.05, wait_timeout=1.5):
                last_use['utility_1'] = now
                log_and_print('info', ">>> SUMMON BONE MINIONS")

        # Optional heal usage on a long cadence (NumPad6)
        if ENABLE_HEAL and (now - last_use['heal'] >= max(HEAL_INTERVAL, COOLDOWNS['heal'])):
            if tap_keys(UTILITY_KEY_OPTIONS['heal'], presses=2, delay=0.05):
                last_use['heal'] = now
                log_and_print('info', ">>> HEAL")

        # Splinter/Nightmare weapon cadence outside shroud (tighter 18s)
        if now - last_use['utility_2'] >= COOLDOWNS['utility_2']:
            if tap_keys(UTILITY_KEY_OPTIONS['utility_2'], presses=2, delay=0.05):
                last_use['utility_2'] = now
                log_and_print('info', ">>> SPLINTER WEAPON (out of shroud)")

        if now - last_use['utility_3'] >= COOLDOWNS['utility_3']:
            if tap_keys(UTILITY_KEY_OPTIONS['utility_3'], presses=2, delay=0.05):
                last_use['utility_3'] = now
                log_and_print('info', ">>> NIGHTMARE WEAPON (out of shroud)")

        # Align elite to shroud entries (fire if at least 50s since last use)
        time_since_shroud = now - last_shroud_attempt
        if time_since_shroud >= SHROUD_ATTEMPT_INTERVAL * 0.8 and (now - last_use['elite']) >= 50.0:
            if tap_keys(UTILITY_KEY_OPTIONS['elite'], presses=2, delay=0.06):
                last_use['elite'] = now
                log_and_print('info', ">>> ELITE")

        # Shroud: try when GS5 and GS4 are not bright (spend lifeforce, do spirit burst)
        if (now - last_shroud_attempt) >= SHROUD_ATTEMPT_INTERVAL:
            gs5_ready = slot_brightness[5] >= GS_READY_THRESHOLD_HEAVY
            gs4_ready = slot_brightness[4] >= GS_READY_THRESHOLD_HEAVY
            if not gs5_ready and not gs4_ready:
                # Pre-shroud elite if available to align bursts
                log_and_print('info', f"SHROUD: attempt (since_last={now-last_shroud_attempt:.2f}s) gs5={slot_brightness[5]} gs4={slot_brightness[4]}")
                if (now - last_use['elite']) >= COOLDOWNS['elite']:
                    if tap_keys(UTILITY_KEY_OPTIONS['elite'], presses=2, delay=0.06):
                        last_use['elite'] = now
                        log_and_print('info', ">>> ELITE (pre-shroud)")
                # Also weave Splinter/Nightmare right before shroud if ready
                if now - last_use['utility_2'] >= COOLDOWNS['utility_2']:
                    if tap_keys(UTILITY_KEY_OPTIONS['utility_2'], presses=1, delay=0.05):
                        last_use['utility_2'] = now
                        log_and_print('info', ">>> SPLINTER WEAPON (pre-shroud)")
                if now - last_use['utility_3'] >= COOLDOWNS['utility_3']:
                    if tap_keys(UTILITY_KEY_OPTIONS['utility_3'], presses=1, delay=0.05):
                        last_use['utility_3'] = now
                        log_and_print('info', ">>> NIGHTMARE WEAPON (pre-shroud)")

                if tap_keys(RITUALIST_KEYS['shroud_toggle'], presses=1, delay=0.05):
                    log_and_print('info', ">>> ENTER SHROUD")
                    ritualist_shroud_burst(adaptive_exit=False, last_use=last_use)
                    time.sleep(0.12)
                    tap_keys(RITUALIST_KEYS['shroud_toggle'], presses=1, delay=0.05)
                    log_and_print('info', ">>> EXIT SHROUD")
                    # Snap GS5 -> GS4 if available immediately after shroud for burst alignment
                    post_brightness = {
                        4: get_brightness(*BAR_SLOTS['slot_4']),
                        5: get_brightness(*BAR_SLOTS['slot_5']),
                    }
                    if post_brightness[5] >= GS_READY_THRESHOLD_HEAVY:
                        if cast_skill(WEAPON_KEY_OPTIONS['slot_5'], BAR_SLOTS['slot_5'],
                                      presses=int(get_knob('games.GuildWars2.ritualist.presses.gs_heavy', 'presses_gs_heavy')),
                                      delay=GLOBAL_PRESS_DELAY, wait_timeout=1.3):
                            log_and_print('info', ">>> GS 5 (post-shroud)")
                    if post_brightness[4] >= GS_READY_THRESHOLD_HEAVY:
                        if cast_skill(WEAPON_KEY_OPTIONS['slot_4'], BAR_SLOTS['slot_4'],
                                      presses=int(get_knob('games.GuildWars2.ritualist.presses.gs_heavy', 'presses_gs_heavy')),
                                      delay=GLOBAL_PRESS_DELAY, wait_timeout=1.3):
                            log_and_print('info', ">>> GS 4 (post-shroud)")
                    last_shroud_attempt = now
                    time.sleep(0.1)
                    continue

        # Greatsword priority (assume GS): 5 > 4 > 2 > 3; thresholds heavy/mid
        did_cast = False
        for label, threshold in [('5', GS_READY_THRESHOLD_HEAVY), ('4', GS_READY_THRESHOLD_HEAVY),
                                 ('2', GS_READY_THRESHOLD_MID), ('3', GS_READY_THRESHOLD_MID)]:
            coords = BAR_SLOTS[f'slot_{label}']
            if check_skill_available(coords, threshold=threshold):
                presses = int(get_knob('games.GuildWars2.ritualist.presses.gs_heavy', 'presses_gs_heavy')) if label in ('5', '4') else int(get_knob('games.GuildWars2.ritualist.presses.gs_mid', 'presses_gs_mid'))
                if cast_skill(WEAPON_KEY_OPTIONS[f'slot_{label}'], coords, presses=presses, delay=GLOBAL_PRESS_DELAY, wait_timeout=1.3):
                    log_and_print('info', f">>> GS {label}")
                    did_cast = True
                    break
        if not did_cast:
            # Auto filler (GS1)
            if cast_skill(WEAPON_KEY_OPTIONS['slot_1'], DEFAULT_COORDS['slot_1'], presses=1, delay=0.03, wait_timeout=0.4):
                log_and_print('info', ">>> GS 1 (auto)")

        time.sleep(0.06)

    log_and_print('info', "Stopping Ritualist Power Open World rotation")


def run(stop_event):
    logger.info("Power Ritualist spec started")
    log_and_print('info', "=" * 67)
    log_and_print('info', "RITUALIST - POWER RITUALIST (OPEN WORLD)")
    log_and_print('info', "Hold NumPad1 to run rotation")
    log_and_print('info', "=" * 67)

    while not stop_event.is_set():
        wait_if_paused()
        if stop_event.is_set():
            break
        if keyboard.is_pressed(STOP_KEY):
            log_and_print('info', "NumPad1 pressed - starting rotation loop")
            try:
                power_ritualist_rotation(stop_event)
            except Exception as exc:
                log_and_print('error', f"Unexpected error in Ritualist rotation: {exc}")
                raise
        time.sleep(0.05)

    logger.info("Power Ritualist spec ended")


