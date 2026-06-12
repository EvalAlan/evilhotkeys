"""
Soulbeast - Power Soulbeast Build for Guild Wars 2
Based on: https://metabattle.com/wiki/Build:Soulbeast_-_Power_Soulbeast

Key ideas from the guide:
- Stay merged (Beastmode) for the Beastmastery bonuses and extra burst.
- Use One Wolf Pack, Moa Stance, "Sic 'Em!" and Dolyak Stance off cooldown to maintain boons and burst modifiers.
- Hammer set (Weaponmaster) delivers big AoE burst and crowd control; Axe/Axe provides sustained damage between hammer windows.
- Prioritise Path of Scars, Winter's Bite, Splitblade, and Whirling Defense on axe; Savage Shock Wave, Overbearing Smash, Wild Swing and Unleashed Thump on hammer.
- Use Beast skills (Worldly Impact / Maul) whenever available for massive burst, ideally during "Sic 'Em!" and One Wolf Pack.

This script assumes the standard EvilHotKeys bindings (NumPad1-5 weapons, NumPad6-0 utilities).
Adjust coordinates or keys in DEFAULT_COORDS / key constants if your layout differs.
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

logger = get_logger('power_soulbeast')
logger.propagate = True

# Enable/disable detailed logging
ENABLE_DETAILED_LOGGING = True


def log_and_print(level, msg):
    """Log and optionally print for debugging."""
    getattr(logger, level)(msg)
    if ENABLE_DETAILED_LOGGING:
        print(f"[{level.upper()}] {msg}", flush=True)
        sys.stdout.flush()


# Pixel coordinates (matching the standard amalgam layout)
DEFAULT_COORDS = {
    # Weapon skills (NumPad1-5)
    'weapon_1': (2587, 1013),
    'weapon_2': (2625, 1013),
    'weapon_3': (2686, 1013),
    'weapon_4': (2743, 1013),
    'weapon_5': (2801, 1013),

    # Utility bar (NumPad6-0)
    'utility_heal': (2652, 1013),    # We Heal As One! / Bear Stance
    'utility_1': (3007, 1013),       # Moa Stance
    'utility_2': (3070, 1013),       # "Sic 'Em!"
    'utility_3': (3116, 1013),       # Dolyak Stance
    'utility_elite': (3171, 1013),   # One Wolf Pack

    # Beast skills (F-skills while merged)
    'beast_skill_1': (2643, 943),    # Maul / Unleashed Bite (slot 1)
    'beast_skill_2': (2685, 940),    # Brutal Charge (slot 2)
    'beast_skill_3': (2742, 943),    # Worldly Impact (slot 3)

    # Beastmode indicator (grey when unmerged)
    'beastmode_icon': (2596, 970),

    # Weapon swap indicator (bright when ready)
    'weapon_swap': (2530, 1010),

    # Legacy hammer indicator kept for reference; live detection uses HUD pixel below
    'hammer_indicator': (2765, 1015),
}

HAMMER_INDICATOR_PIXEL = DEFAULT_COORDS['hammer_indicator'] if 'hammer_indicator' in DEFAULT_COORDS else None
WEAPON_INDICATOR_PIXEL = (2820, 1049)
ONE_WOLF_PACK_READY_PIXEL = (3172, 1020)


def resolve_key(path: str, default: str):
    if get_config_manager:
        try:
            config = get_config_manager()
            value = config.get(path, None)
            if value:
                return value
        except Exception:
            logger.warning(f"Failed to load key from config path '{path}'", exc_info=True)
    return default


def build_keychain(*keys):
    return [key for key in keys if key]


WEAPON_KEY_OPTIONS = {
    'weapon_1': build_keychain(key_mapping.get('numpad1'), '1'),
    'weapon_2': build_keychain(key_mapping.get('numpad2'), '2'),
    'weapon_3': build_keychain(key_mapping.get('numpad3'), '3'),
    'weapon_4': build_keychain(key_mapping.get('numpad4'), '4'),
    'weapon_5': build_keychain(key_mapping.get('numpad5'), '5'),
}

UTILITY_KEY_OPTIONS = {
    'utility_heal': build_keychain(key_mapping.get('numpad6'), '6'),
    'utility_1': build_keychain(key_mapping.get('numpad7'), '7'),
    'utility_2': build_keychain(key_mapping.get('numpad8'), '8'),
    'utility_3': build_keychain(key_mapping.get('numpad9'), '9'),
    'utility_elite': build_keychain(key_mapping.get('numpad0'), '0'),
}


# Configurable keybinds
MERGE_KEYS = build_keychain(
    '5',  # primary Beastmode key (per user)
    resolve_key('games.GuildWars2.keybinds.soulbeast.merge', '5'),
    resolve_key('games.GuildWars2.keybinds.soulbeast.merge_alt', key_mapping.get('f5', 'f5')),
    key_mapping.get('f5', 'f5'),
)
WEAPON_SWAP_KEYS = build_keychain(
    resolve_key('games.GuildWars2.keybinds.soulbeast.weapon_swap', key_mapping.get('f1', 'f1')),
    key_mapping.get('f1', 'f1'),
    key_mapping.get('numpad7', 'numpad7'),  # fallback to weapon swap key used in older script
    'tab',
)
BEAST_SKILL_KEYS = {
    'beast_skill_1': build_keychain(
        resolve_key('games.GuildWars2.keybinds.soulbeast.beast_skill_1', '1'),
        '1',
    ),
    'beast_skill_2': build_keychain(
        resolve_key('games.GuildWars2.keybinds.soulbeast.beast_skill_2', '2'),
        '2',
    ),
    'beast_skill_3': build_keychain(
        resolve_key('games.GuildWars2.keybinds.soulbeast.beast_skill_3', '3'),
        '3',
    ),
}

IGNITE_UNUSED_PLACEHOLDER = None  # Placeholder to mirror other specs (unused but kept for clarity)

# Timing constants (seconds)
UTILITY_STAGGER = {
    'utility_elite': 24.0,   # One Wolf Pack - faster recast window
    'utility_2': 18.0,       # "Sic 'Em!"
    'utility_1': 24.0,       # Moa Stance
    'utility_3': 28.0,       # Dolyak Stance
    'utility_heal': 23.0,    # Heal skill (We Heal As One! / Bear Stance)
}
UTILITY_FORCE_INTERVAL = {
    'utility_elite': 42.0,
    'utility_2': 26.0,
    'utility_1': 34.0,
    'utility_3': 50.0,
    'utility_heal': 65.0,  # allow more time before forcing heal
}

UTILITY_NO_CONFIRM = {'utility_elite', 'utility_2', 'utility_1', 'utility_3'}

SKILL_READY_PIXEL_MIN = 40
SKILL_ON_COOLDOWN_MAX = 75
# MetaBattle hammer + axe/axe loops are much longer than a 5.5s swap cadence.
# 5.5s caused the script to leave axe after only Path of Scars + Splitblade,
# skipping most of the Axe/Axe loop. Keep each set long enough to drain weapon skills.
WEAPON_SET_MIN_TIME = 10.0
BEASTMODE_TARGET_COLOR = (112, 112, 122)  # observed Beastmode-active color
BEASTMODE_TOLERANCE = 12

LAST_WEAPON_SET = 'axe'


def check_stop_condition(stop_event):
    """Stop if NumPad1 released or requested via stop_event."""
    return not keyboard.is_pressed(key_mapping['numpad1']) or stop_event.is_set()


def check_skill_available(coords, threshold: int | None = 210):
    """Return True if the skill pixel is bright enough to imply readiness."""
    color = pixel_get_color(coords[0], coords[1])
    if color is None:
        return False
    brightness = sum(color)
    if threshold is None:
        return brightness > SKILL_READY_PIXEL_MIN
    # special handling for beast skill 2 (Brutal Charge) which stays dim
    if coords == DEFAULT_COORDS.get('beast_skill_2'):
        return brightness > 25
    if threshold is None:
        return brightness > SKILL_READY_PIXEL_MIN
    return brightness > threshold or brightness > SKILL_READY_PIXEL_MIN


def wait_until_on_cooldown(coords, timeout_seconds=1.75, poll_seconds=0.05):
    """Wait until the skill pixel dims (indicating cooldown began)."""
    start = time.time()
    while (time.time() - start) < timeout_seconds:
        color = pixel_get_color(coords[0], coords[1])
        if color is None:
            return True
        if sum(color) <= SKILL_ON_COOLDOWN_MAX:
            return True
        time.sleep(poll_seconds)
    return False


def get_skill_brightness(name):
    if name == 'utility_elite':
        color = pixel_get_color(*ONE_WOLF_PACK_READY_PIXEL)
        if color:
            ready_brightness = sum(color)
            if ready_brightness > 0:
                return ready_brightness
        coords = DEFAULT_COORDS.get(name)
        if coords:
            color = pixel_get_color(coords[0], coords[1])
            return sum(color) if color else 0
        coords = DEFAULT_COORDS.get(name)
        if not coords:
            return 0
        color = pixel_get_color(coords[0], coords[1])
        return sum(color) if color else 0
    coords = DEFAULT_COORDS.get(name)
    if not coords:
        return 0
    color = pixel_get_color(coords[0], coords[1])
    return sum(color) if color else 0


def pixel_not_black(coords, threshold=12):
    color = pixel_get_color(*coords)
    if not color:
        return False
    return sum(color) > threshold


def cast_skill(key_candidates, coords, presses=3, delay=0.05, wait_timeout=1.5):
    """Attempt to cast a skill using a list of possible keybinds."""
    for key in key_candidates:
        if isinstance(key, tuple):
            for sub_key in key:
                button_mash(sub_key, presses=1, delay=0.02, stop_check=None)
        else:
            if not button_mash(key, presses=presses, delay=delay, stop_check=None):
                continue
        if coords is None:
            return True
        if wait_until_on_cooldown(coords, timeout_seconds=wait_timeout):
            return True
    return False


def colors_close(color, target, tolerance):
    return all(abs(c - t) <= tolerance for c, t in zip(color, target))


def get_beastmode_pixel():
    return pixel_get_color(*DEFAULT_COORDS['beastmode_icon'])


def beastmode_active():
    icon_color = get_beastmode_pixel()
    if not icon_color:
        return False
    return colors_close(icon_color, BEASTMODE_TARGET_COLOR, BEASTMODE_TOLERANCE)


def ensure_beastmode():
    if beastmode_active():
        return True
    log_and_print('info', f"Beastmode inactive - attempting to merge (pixel={get_beastmode_pixel()})")
    for attempt in range(3):
        for key in MERGE_KEYS:
            button_mash(key, presses=2, delay=0.05)
            time.sleep(0.45)
            if beastmode_active():
                log_and_print('info', f"Successfully merged with pet (pixel={get_beastmode_pixel()})")
                time.sleep(0.15)
                return True
        time.sleep(0.2)
    log_and_print('warning', f"Failed to enter Beastmode (pixel={get_beastmode_pixel()}) - check keybind")
    return False


def detect_weapon_set():
    global LAST_WEAPON_SET
    color = pixel_get_color(*WEAPON_INDICATOR_PIXEL)
    if not color:
        return LAST_WEAPON_SET

    brightness = sum(color)

    # Pixel leans very dark when on HAMMER (per latest coordinates/logs)
    if brightness <= 140:
        LAST_WEAPON_SET = 'hammer'
        return LAST_WEAPON_SET

    # Pixel goes fully bright when on AXE; allow settle window for swap animation
    if brightness >= 220:
        LAST_WEAPON_SET = 'axe'
        return LAST_WEAPON_SET

    # In the transition range, keep previous state
    return LAST_WEAPON_SET


def ensure_weapon_swap(current_set):
    indicator = pixel_get_color(*DEFAULT_COORDS['weapon_swap'])
    ready = not indicator or sum(indicator) > SKILL_READY_PIXEL_MIN
    if not ready:
        log_and_print('debug', "Weapon swap indicator dim - attempting swap anyway")
    for key in WEAPON_SWAP_KEYS:
        button_mash(key, presses=1, delay=0.05)
        time.sleep(0.45)
        new_set = detect_weapon_set()
        indicator_color = pixel_get_color(*WEAPON_INDICATOR_PIXEL)
        indicator_brightness = sum(indicator_color) if indicator_color else 0
        log_and_print('debug', f"Weapon swap attempt with key '{key}' -> detected set {new_set.upper()} (brightness={indicator_brightness})")
        if new_set != current_set:
            log_and_print('info', f"Swapped weapons -> {new_set.upper()}")
            return True
    log_and_print('warning', "Weapon swap attempt failed (set unchanged)")
    return False


def power_soulbeast_rotation(stop_event):
    """
    Power Soulbeast rotation focusing on Axe/Axe + Hammer (Weaponmaster).

    Key priorities:
    - Stay merged; spam One Wolf Pack + "Sic 'Em!" + Moa Stance off cooldown.
    - Use Beast skills on cooldown (Worldly Impact > Maul).
    - Axe set: Path of Scars > Whirling Defense > Winter's Bite > Splitblade.
    - Hammer set: Savage Shock Wave > Overbearing Smash > Wild Swing > Unleashed Thump.
    - Auto attack fills; swap weapons every few seconds to cycle cooldowns.
    """
    rotation_count = 0
    last_use_times = {name: 0.0 for name in DEFAULT_COORDS if name.startswith('utility')}
    last_use_times.update({'beast_skill_1': 0.0, 'beast_skill_2': 0.0, 'beast_skill_3': 0.0})
    last_weapon_swap = time.time()  # Start the swap timer now so we don't swap immediately
    last_set_seen = detect_weapon_set()

    while not stop_event.is_set():
        rotation_count += 1
        wait_if_paused()
        if check_stop_condition(stop_event):
            break

        current_time = time.time()
        current_set = detect_weapon_set()

        if not ensure_beastmode():
            time.sleep(0.2)
            continue

        # Skill readiness
        # Axe 3/5 have much dimmer ready pixels on this UI/theme than hammer skills.
        # Keep the global threshold conservative, but permit axe-specific dim reads so
        # Winter's Bite and Whirling Defense actually enter the rotation.
        if current_set == 'axe':
            weapon_ready = {
                'weapon_2': check_skill_available(DEFAULT_COORDS['weapon_2'], threshold=None),
                'weapon_3': check_skill_available(DEFAULT_COORDS['weapon_3'], threshold=15),
                'weapon_4': check_skill_available(DEFAULT_COORDS['weapon_4'], threshold=None),
                'weapon_5': check_skill_available(DEFAULT_COORDS['weapon_5'], threshold=20),
            }
        else:
            weapon_ready = {
                'weapon_2': check_skill_available(DEFAULT_COORDS['weapon_2'], threshold=None),
                'weapon_3': check_skill_available(DEFAULT_COORDS['weapon_3'], threshold=None),
                'weapon_4': check_skill_available(DEFAULT_COORDS['weapon_4'], threshold=None),
                'weapon_5': check_skill_available(DEFAULT_COORDS['weapon_5'], threshold=None),
            }
        beast_ready = {
            'beast_skill_1': check_skill_available(DEFAULT_COORDS['beast_skill_1'], threshold=None),
            'beast_skill_2': check_skill_available(DEFAULT_COORDS['beast_skill_2'], threshold=None),
            'beast_skill_3': check_skill_available(DEFAULT_COORDS['beast_skill_3'], threshold=None),
        }
        utilities_ready = {}
        for name in ['utility_elite', 'utility_2', 'utility_1', 'utility_3', 'utility_heal']:
            if name == 'utility_elite':
                ready_pixel_lit = pixel_not_black(ONE_WOLF_PACK_READY_PIXEL, threshold=12)
                backup_ready = check_skill_available(DEFAULT_COORDS[name], threshold=None)
                utilities_ready[name] = ready_pixel_lit or backup_ready
            else:
                utilities_ready[name] = check_skill_available(DEFAULT_COORDS[name], threshold=None)

        beast_status = {key: beast_ready[key] for key in beast_ready}
        beast_brightness = {
            key: get_skill_brightness(key) for key in ['beast_skill_1', 'beast_skill_2', 'beast_skill_3'] if key in DEFAULT_COORDS
        }
        weapon_brightness = {slot: get_skill_brightness(slot) for slot in ['weapon_2', 'weapon_3', 'weapon_4', 'weapon_5']}
        utility_brightness = {name: get_skill_brightness(name) for name in ['utility_elite', 'utility_2', 'utility_1', 'utility_3', 'utility_heal']}
        utility_status = {key: utilities_ready[key] for key in utilities_ready}
        beastmode_pixel = get_beastmode_pixel()
        log_and_print(
            'info',
            (
                f"--- LOOP {rotation_count} ---\n"
                f"Set={current_set.upper()} | WeaponReady={weapon_ready} brightness={weapon_brightness}\n"
                f"BeastReady={beast_status} brightness={beast_brightness} | BeastmodePixel={beastmode_pixel}\n"
                f"Utilities={utility_status} brightness={utility_brightness}"
            )
        )

        # Utilities / buffs — cast at most one
        util_cast = False
        for util in ['utility_elite', 'utility_2', 'utility_1', 'utility_3', 'utility_heal']:
            time_since = current_time - last_use_times[util]
            if utilities_ready[util] and time_since > UTILITY_STAGGER[util]:
                label = {
                    'utility_elite': "One Wolf Pack",
                    'utility_2': '"Sic \'Em!"',
                    'utility_1': "Moa Stance",
                    'utility_3': "Dolyak Stance",
                    'utility_heal': 'Heal Skill',
                }[util]
                log_and_print('info', f">>> PRIORITY: {label}")
                start_brightness = get_skill_brightness(util)
                if cast_skill(UTILITY_KEY_OPTIONS[util], DEFAULT_COORDS[util], presses=3, delay=0.05, wait_timeout=2.0):
                    last_use_times[util] = current_time
                    util_cast = True
                    break
                end_brightness = get_skill_brightness(util)
                if util in UTILITY_NO_CONFIRM and end_brightness <= SKILL_ON_COOLDOWN_MAX:
                    log_and_print('debug', f"Cooldown detected post-cast for {label} (brightness={end_brightness})")
                    last_use_times[util] = current_time
                    util_cast = True
                    break
                if util in UTILITY_NO_CONFIRM and end_brightness < start_brightness - 40:
                    log_and_print('debug', f"Brightness drop suggests {label} landed (pre={start_brightness}, post={end_brightness})")
                    last_use_times[util] = current_time
                    util_cast = True
                    break
            elif time_since > UTILITY_FORCE_INTERVAL[util]:
                brightness = get_skill_brightness(util)
                if util == 'utility_heal' and brightness < 25:
                    log_and_print('debug', f"Skipping forced Heal Skill due to low brightness ({brightness})")
                    continue
                if util == 'utility_elite' and brightness < 25:
                    log_and_print('debug', f"Skipping forced One Wolf Pack due to low brightness ({brightness})")
                    continue
                label = {
                    'utility_elite': "One Wolf Pack (Force)",
                    'utility_2': '"Sic \'Em!" (Force)',
                    'utility_1': "Moa Stance (Force)",
                    'utility_3': "Dolyak Stance (Force)",
                    'utility_heal': 'Heal Skill (Force)',
                }[util]
                log_and_print('debug', f"Forcing {label} (brightness={brightness})")
                start_brightness = brightness
                if cast_skill(UTILITY_KEY_OPTIONS[util], DEFAULT_COORDS[util], presses=3, delay=0.05, wait_timeout=2.0):
                    last_use_times[util] = current_time
                    util_cast = True
                    break
                end_brightness = get_skill_brightness(util)
                if util in UTILITY_NO_CONFIRM and end_brightness <= SKILL_ON_COOLDOWN_MAX:
                    log_and_print('debug', f"Cooldown detected post-force for {label} (brightness={end_brightness})")
                    last_use_times[util] = current_time
                    util_cast = True
                    break
                if util in UTILITY_NO_CONFIRM and end_brightness < start_brightness - 40:
                    log_and_print('debug', f"Brightness drop after force suggests {label} landed (pre={start_brightness}, post={end_brightness})")
                    last_use_times[util] = current_time
                    util_cast = True
                    break

        # Beast skills — cast at most one (independent of utilities)
        beast_cast = False
        if beast_ready['beast_skill_2'] and (current_time - last_use_times['beast_skill_2']) > 8.0:
            if beastmode_active() or ensure_beastmode():
                log_and_print('info', ">>> PRIORITY: Beast Skill 2 (Worldly Impact)")
                if cast_skill(BEAST_SKILL_KEYS['beast_skill_2'], DEFAULT_COORDS['beast_skill_2'], presses=2, delay=0.05, wait_timeout=1.5):
                    last_use_times['beast_skill_2'] = current_time
                    beast_cast = True
                else:
                    log_and_print('debug', f"Worldly Impact failed - beast pixel={get_beastmode_pixel()}")
                    if ensure_beastmode() and cast_skill(BEAST_SKILL_KEYS['beast_skill_2'], DEFAULT_COORDS['beast_skill_2'], presses=2, delay=0.05, wait_timeout=1.5):
                        last_use_times['beast_skill_2'] = time.time()
                        beast_cast = True

        if not beast_cast and beast_ready['beast_skill_1'] and (current_time - last_use_times['beast_skill_1']) > 5.0:
            if beastmode_active() or ensure_beastmode():
                log_and_print('info', ">>> PRIORITY: Beast Skill 1 (Maul)")
                if cast_skill(BEAST_SKILL_KEYS['beast_skill_1'], DEFAULT_COORDS['beast_skill_1'], presses=2, delay=0.05, wait_timeout=1.2):
                    last_use_times['beast_skill_1'] = current_time
                    beast_cast = True
                else:
                    log_and_print('debug', f"Maul failed - beast pixel={get_beastmode_pixel()}")
                    if ensure_beastmode() and cast_skill(BEAST_SKILL_KEYS['beast_skill_1'], DEFAULT_COORDS['beast_skill_1'], presses=2, delay=0.05, wait_timeout=1.2):
                        last_use_times['beast_skill_1'] = time.time()
                        beast_cast = True

        if not beast_cast and beast_ready['beast_skill_3'] and (current_time - last_use_times['beast_skill_3']) > 8.0:
            beast3_coords = DEFAULT_COORDS.get('beast_skill_3')
            if beast3_coords:
                if beastmode_active() or ensure_beastmode():
                    log_and_print('info', ">>> PRIORITY: Beast Skill 3")
                    if cast_skill(BEAST_SKILL_KEYS['beast_skill_3'], beast3_coords, presses=2, delay=0.05, wait_timeout=1.2):
                        last_use_times['beast_skill_3'] = current_time
                        beast_cast = True
                    else:
                        log_and_print('debug', f"Beast Skill 3 failed - beast pixel={get_beastmode_pixel()}")
                        if ensure_beastmode() and cast_skill(BEAST_SKILL_KEYS['beast_skill_3'], beast3_coords, presses=2, delay=0.05, wait_timeout=1.2):
                            last_use_times['beast_skill_3'] = time.time()
                            beast_cast = True

        # Weapon skill priorities — cast at most one (independent of utilities/beasts)
        if current_set == 'axe':
            priority = ['weapon_4', 'weapon_5', 'weapon_3', 'weapon_2']
            weapon_timeout_overrides = {
                'weapon_2': (1.0, 0.04),
                'weapon_3': (1.0, 0.04),
                'weapon_4': (1.2, 0.06),
                'weapon_5': (1.2, 0.06),
            }
        else:
            priority = ['weapon_2', 'weapon_3', 'weapon_4', 'weapon_5']
            weapon_timeout_overrides = {
                'weapon_2': (1.1, 0.05),
                'weapon_3': (1.2, 0.06),
                'weapon_4': (1.4, 0.08),
                'weapon_5': (2.2, 0.1),
            }

        weapon_cast = False
        for slot in priority:
            if weapon_ready.get(slot, False):
                label = f"Weapon Skill {slot[-1]} ({'AXE' if current_set == 'axe' else 'HAMMER'})"
                log_and_print('info', f">>> PRIORITY: {label}")
                wait_timeout, delay = weapon_timeout_overrides.get(slot, (1.4, 0.05))
                if cast_skill(WEAPON_KEY_OPTIONS[slot], DEFAULT_COORDS[slot], presses=3, delay=delay, wait_timeout=wait_timeout):
                    weapon_cast = True
                    break

        # Auto-attack filler only when no weapon skill fired this loop.
        if not weapon_cast and cast_skill(WEAPON_KEY_OPTIONS['weapon_1'], DEFAULT_COORDS['weapon_1'], presses=1, delay=0.02, wait_timeout=0.6):
            log_and_print('debug', "Auto-attack filler (weapon 1)")

        # Weapon swap cadence — always check
        time_since_swap = current_time - last_weapon_swap
        if time_since_swap > WEAPON_SET_MIN_TIME:
            if ensure_weapon_swap(current_set):
                last_weapon_swap = time.time()
                last_set_seen = detect_weapon_set()
                log_and_print('debug', f"Weapon swap -> {last_set_seen.upper()} (interval={time_since_swap:.1f}s)")
                time.sleep(0.25)
                continue

        time.sleep(0.15)

    log_and_print('info', "Stopping Power Soulbeast rotation")


def run(stop_event):
    """
    Entry point for the Soulbeast spec.
    Hold NumPad1 to run the rotation; release to stop.
    """
    logger.info("Power Soulbeast spec started")
    log_and_print('info', "=" * 70)
    log_and_print('info', "POWER SOULBEAST - HAMMER / AXE BUILD")
    log_and_print('info', "Hold NumPad1 to run rotation")
    log_and_print('info', "=" * 70)

    while not stop_event.is_set():
        wait_if_paused()
        if stop_event.is_set():
            break
        if keyboard.is_pressed(key_mapping['numpad1']):
            log_and_print('info', "NumPad1 pressed - starting rotation loop")
            try:
                power_soulbeast_rotation(stop_event)
            except Exception as exc:
                log_and_print('error', f"Unexpected error in Soulbeast rotation: {exc}")
                raise
        time.sleep(0.05)

    logger.info("Power Soulbeast spec ended")
