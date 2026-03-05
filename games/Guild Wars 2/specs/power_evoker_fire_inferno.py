try:
    from libs.config_manager import get_config_manager
except ImportError:
    get_config_manager = None
"""
Power Evoker - Fire Inferno build for Guild Wars 2
Based on: https://metabattle.com/wiki/Build:Evoker_-_Power_Evoker_Fire_Inferno

Key ideas from the guide:
- Specialise in Fire attunement (Specialized Elements) and spam fire weapon skills.
- Use Ignite (F5) every ~2 weapon skills to reduce cooldowns.
- After 3 Ignites, spend the Conflagration detonation for a large burst and further reductions.
- Keep Flamewall up for combo interactions, then drop Dragon's Tooth and Phoenix inside it.
- Use Fox's Fury, Signet of Fire (active), and Armor of Earth off cooldown, Glyph of Elementals on cooldown.

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

logger = get_logger('power_evoker_fire_inferno')
logger.propagate = True

# Enable/disable detailed logging
ENABLE_DETAILED_LOGGING = False


def log_and_print(level, msg):
    """Log and optionally print for debugging."""
    getattr(logger, level)(msg)
    if ENABLE_DETAILED_LOGGING:
        print(f"[{level.upper()}] {msg}", flush=True)
        sys.stdout.flush()


# Pixel coordinates for skill detection (match the standard amalgam layout)
DEFAULT_COORDS = {
    # Weapon skills (NumPad1-5)
    'weapon_1': (2587, 1013),  # Flame Burst (auto)
    'weapon_2': (2625, 1013),  # Dragon's Tooth
    'weapon_3': (2686, 1013),  # Phoenix
    'weapon_4': (2743, 1013),  # Focus 4 - Flamewall
    'weapon_5': (2801, 1013),  # Focus 5 - Fire Shield

    # Utility bar (NumPad6-0)
    'utility_heal': (2652, 1013),    # NumPad6 - Rejuvenate (default)
    'utility_1': (3007, 1013),       # NumPad7 - Fox's Fury
    'utility_2': (3070, 1013),       # NumPad8 - Signet of Fire (active)
    'utility_3': (3116, 1013),       # NumPad9 - Armor of Earth
    'utility_elite': (3171, 1013),   # NumPad0 - Glyph of Elementals

    # Profession mechanic (Ignite / Conflagration icons)
    # These coordinates may need adjustment depending on UI scale.
    'ignite': (2735, 950),
    'conflagration': (2795, 950),
}

# Keys for profession mechanic (adjust if rebound)
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


IGNITE_KEY = resolve_key('games.GuildWars2.keybinds.evoker.ignite', key_mapping.get('f5', 'f5'))
CONFLAGRATION_KEY = resolve_key('games.GuildWars2.keybinds.evoker.conflagration', key_mapping.get('f6', 'f6'))

# Timing constants (seconds)
IGNITE_MIN_INTERVAL = 2.0          # Minimum spacing between Ignites
IGNITE_FORCE_INTERVAL = 6.0        # Force Ignite if it hasn't fired by this time
CONFLAGRATION_FORCE_INTERVAL = 15.0
WEAPON_CAST_GAP = 0.05
FLAMEWALL_COOLDOWN = 12.0
FIRE_SHIELD_COOLDOWN = 18.0
DRAGON_TOOTH_COOLDOWN = 6.0
PHOENIX_COOLDOWN = 6.0
FOX_FURY_COOLDOWN = 18.0
SIGNET_FIRE_COOLDOWN = 20.0
ARMOR_EARTH_COOLDOWN = 25.0
GLYPH_ELEMENTALS_COOLDOWN = 90.0

SKILL_READY_PIXEL_MIN = 40        # Treat any non-black/dim icon as ready
SKILL_ON_COOLDOWN_MAX = 75        # Brightness threshold to consider skill back on cooldown

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

IGNITE_KEYS = build_keychain(IGNITE_KEY, '5')
CONFLAGRATION_KEYS = build_keychain(CONFLAGRATION_KEY, '6')


def check_stop_condition(stop_event):
    """Stop if NumPad1 released or requested via stop_event."""
    return not keyboard.is_pressed(key_mapping['numpad1']) or stop_event.is_set()


def check_skill_available(coords, threshold=210):
    """Return True if the skill pixel is bright enough to imply readiness."""
    color = pixel_get_color(coords[0], coords[1])
    if color is None:
        return False
    brightness = sum(color)
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
    coords = DEFAULT_COORDS.get(name)
    if not coords:
        return 0
    color = pixel_get_color(coords[0], coords[1])
    return sum(color) if color else 0


def cast_skill(key_candidates, coords, presses=3, delay=0.05, wait_timeout=1.5):
    """Attempt to cast a skill using a list of possible keybinds."""
    for key in key_candidates:
        button_mash(key, presses=presses, delay=delay)
        if coords is None:
            return True
        if wait_until_on_cooldown(coords, timeout_seconds=wait_timeout):
            return True
    return False


def power_evoker_rotation(stop_event):
    """
    Fire-only rotation for Power Evoker Fire Inferno.

    Priority outline:
    1. Maintain Flamewall and drop Dragon's Tooth / Phoenix inside it.
    2. Use Fire Shield defensively/off cooldown for burning + aura uptime.
    3. Fire Ignite after at least two weapon casts; after third Ignite, detonate with Conflagration.
    4. Use Fox's Fury, Signet of Fire, Armor of Earth, Glyph of Elementals off cooldown.
    5. Auto-attack filler when nothing else is ready.
    """
    rotation_count = 0
    last_ignite = 0.0
    last_conflagration = 0.0
    last_dragon_tooth = 0.0
    last_phoenix = 0.0
    last_flamewall = 0.0
    last_fire_shield = 0.0
    last_fox_fury = 0.0
    last_signet_fire = 0.0
    last_armor_earth = 0.0
    last_glyph_elementals = 0.0
    last_ignite_attempt = 0.0
    weapon_casts_since_ignite = 0
    ignite_stacks = 0

    while not stop_event.is_set():
        rotation_count += 1
        wait_if_paused()
        if check_stop_condition(stop_event):
            break

        current_time = time.time()

        # Read skill readiness
        weapon2_ready = check_skill_available(DEFAULT_COORDS['weapon_2'])
        weapon3_ready = check_skill_available(DEFAULT_COORDS['weapon_3'])
        weapon4_ready = check_skill_available(DEFAULT_COORDS['weapon_4'])
        weapon5_ready = check_skill_available(DEFAULT_COORDS['weapon_5'])
        ignite_ready = check_skill_available(DEFAULT_COORDS['ignite'], threshold=150)
        conflagration_ready = check_skill_available(DEFAULT_COORDS['conflagration'], threshold=180)
        fox_fury_ready = check_skill_available(DEFAULT_COORDS['utility_1'], threshold=170)
        signet_fire_ready = check_skill_available(DEFAULT_COORDS['utility_2'], threshold=180)
        armor_earth_ready = check_skill_available(DEFAULT_COORDS['utility_3'], threshold=190)
        glyph_elementals_ready = check_skill_available(DEFAULT_COORDS['utility_elite'], threshold=190)

        time_since_ignite = current_time - last_ignite if last_ignite > 0 else 999.0
        time_since_conflag = current_time - last_conflagration if last_conflagration > 0 else 999.0
        time_since_dragon = current_time - last_dragon_tooth if last_dragon_tooth > 0 else 999.0
        time_since_phoenix = current_time - last_phoenix if last_phoenix > 0 else 999.0
        time_since_flamewall = current_time - last_flamewall if last_flamewall > 0 else 999.0
        time_since_fire_shield = current_time - last_fire_shield if last_fire_shield > 0 else 999.0
        time_since_fox_fury = current_time - last_fox_fury if last_fox_fury > 0 else 999.0
        time_since_signet = current_time - last_signet_fire if last_signet_fire > 0 else 999.0
        time_since_armor = current_time - last_armor_earth if last_armor_earth > 0 else 999.0
        time_since_glyph = current_time - last_glyph_elementals if last_glyph_elementals > 0 else 999.0

        log_and_print(
            'info',
            (
                f"--- LOOP {rotation_count} ---\n"
                f"WeaponReady -> DT={weapon2_ready}({get_skill_brightness('weapon_2')}) "
                f"PH={weapon3_ready}({get_skill_brightness('weapon_3')}) "
                f"FW={weapon4_ready}({get_skill_brightness('weapon_4')}) "
                f"FS={weapon5_ready}({get_skill_brightness('weapon_5')})\n"
                f"IgniteReady={ignite_ready}({get_skill_brightness('ignite')}) stacks={ignite_stacks} "
                f"ConflagReady={conflagration_ready}({get_skill_brightness('conflagration')})\n"
                f"Utilities -> Fox={fox_fury_ready}({get_skill_brightness('utility_1')}) "
                f"Signet={signet_fire_ready}({get_skill_brightness('utility_2')}) "
                f"Armor={armor_earth_ready}({get_skill_brightness('utility_3')}) "
                f"Glyph={glyph_elementals_ready}({get_skill_brightness('utility_elite')})"
            )
        )

        # Utilities
        if fox_fury_ready and time_since_fox_fury > FOX_FURY_COOLDOWN:
            log_and_print('info', '>>> PRIORITY: Fox’s Fury (NumPad7)')
            if cast_skill(UTILITY_KEY_OPTIONS['utility_1'], DEFAULT_COORDS['utility_1'], presses=3, delay=0.04):
                last_fox_fury = time.time()
                continue
            log_and_print('debug', "Fox's Fury cast attempt failed (pixel stayed bright)")
        elif time_since_fox_fury > FOX_FURY_COOLDOWN + 6.0:
            log_and_print('debug', f'Forcing Fox’s Fury (brightness={get_skill_brightness("utility_1")})')
            if cast_skill(UTILITY_KEY_OPTIONS['utility_1'], DEFAULT_COORDS['utility_1'], presses=3, delay=0.04):
                last_fox_fury = time.time()
                continue

        if signet_fire_ready and time_since_signet > SIGNET_FIRE_COOLDOWN:
            log_and_print('info', '>>> PRIORITY: Signet of Fire (NumPad8)')
            if cast_skill(UTILITY_KEY_OPTIONS['utility_2'], DEFAULT_COORDS['utility_2'], presses=3, delay=0.04):
                last_signet_fire = time.time()
                continue
        elif time_since_signet > SIGNET_FIRE_COOLDOWN + 8.0:
            log_and_print('debug', f'Forcing Signet of Fire (brightness={get_skill_brightness("utility_2")})')
            if cast_skill(UTILITY_KEY_OPTIONS['utility_2'], DEFAULT_COORDS['utility_2'], presses=3, delay=0.04):
                last_signet_fire = time.time()
                continue

        if armor_earth_ready and time_since_armor > ARMOR_EARTH_COOLDOWN:
            log_and_print('info', '>>> PRIORITY: Armor of Earth (NumPad9)')
            if cast_skill(UTILITY_KEY_OPTIONS['utility_3'], DEFAULT_COORDS['utility_3'], presses=3, delay=0.04):
                last_armor_earth = time.time()
                continue
        elif time_since_armor > ARMOR_EARTH_COOLDOWN + 10.0:
            log_and_print('debug', f'Forcing Armor of Earth (brightness={get_skill_brightness("utility_3")})')
            if cast_skill(UTILITY_KEY_OPTIONS['utility_3'], DEFAULT_COORDS['utility_3'], presses=3, delay=0.04):
                last_armor_earth = time.time()
                continue

        if glyph_elementals_ready and time_since_glyph > GLYPH_ELEMENTALS_COOLDOWN:
            log_and_print('info', '>>> PRIORITY: Glyph of Elementals (NumPad0)')
            if cast_skill(UTILITY_KEY_OPTIONS['utility_elite'], DEFAULT_COORDS['utility_elite'], presses=4, delay=0.05, wait_timeout=3.0):
                last_glyph_elementals = time.time()
                continue
        elif time_since_glyph > GLYPH_ELEMENTALS_COOLDOWN + 20.0:
            log_and_print('debug', f'Forcing Glyph of Elementals (brightness={get_skill_brightness("utility_elite")})')
            if cast_skill(UTILITY_KEY_OPTIONS['utility_elite'], DEFAULT_COORDS['utility_elite'], presses=4, delay=0.05, wait_timeout=3.0):
                last_glyph_elementals = time.time()

        # Profession mechanic
        should_force_ignite = (not ignite_ready and time_since_ignite > IGNITE_FORCE_INTERVAL)
        should_cast_ignite = ignite_ready and (
            weapon_casts_since_ignite >= 2 or time_since_ignite > IGNITE_FORCE_INTERVAL
        )
        if (should_cast_ignite or should_force_ignite) and (current_time - last_ignite_attempt) > 0.75:
            last_ignite_attempt = current_time
            if should_force_ignite and not ignite_ready:
                log_and_print('debug', f'Forcing Ignite due to timeout (brightness={get_skill_brightness("ignite")})')
            else:
                log_and_print('info', '>>> PRIORITY: Ignite (F5)')
            ignite_success = cast_skill(IGNITE_KEYS, DEFAULT_COORDS['ignite'], presses=2, delay=0.05, wait_timeout=1.2)
            if ignite_success:
                last_ignite = time.time()
                weapon_casts_since_ignite = 0
                ignite_stacks = min(ignite_stacks + 1, 3)
                continue
            else:
                log_and_print('debug', 'Ignite attempt did not register (icon brightness unchanged)')
                # Fall through to weapons/utilities so we don't stall rotation

        if not ignite_ready and time_since_ignite > IGNITE_FORCE_INTERVAL + 2.0:
            log_and_print('debug', f'Ignite pixel still dim (brightness={get_skill_brightness("ignite")})')

        if ignite_stacks >= 3 and (conflagration_ready or time_since_conflag > CONFLAGRATION_FORCE_INTERVAL):
            log_and_print('info', '>>> PRIORITY: Conflagration Detonate (F6)')
            if cast_skill(CONFLAGRATION_KEYS, DEFAULT_COORDS['conflagration'], presses=2, delay=0.05, wait_timeout=1.2):
                last_conflagration = time.time()
                ignite_stacks = 0
                continue

        # Weapon priorities
        if weapon4_ready:
            log_and_print('info', ">>> PRIORITY: Flamewall (Warhorn/Focus 4 - NumPad4)")
            if cast_skill(WEAPON_KEY_OPTIONS['weapon_4'], DEFAULT_COORDS['weapon_4'], presses=3, delay=0.05):
                last_flamewall = time.time()
                weapon_casts_since_ignite += 1
                time.sleep(WEAPON_CAST_GAP)
                continue
            log_and_print('debug', "Flamewall cast attempt failed (pixel stayed bright)")

        if weapon2_ready:
            log_and_print('info', ">>> PRIORITY: Dragon's Tooth (NumPad2)")
            if cast_skill(WEAPON_KEY_OPTIONS['weapon_2'], DEFAULT_COORDS['weapon_2'], presses=3, delay=0.05):
                last_dragon_tooth = time.time()
                weapon_casts_since_ignite += 1
                time.sleep(WEAPON_CAST_GAP)
                continue
            log_and_print('debug', "Dragon's Tooth cast attempt failed (pixel stayed bright)")

        if weapon3_ready:
            log_and_print('info', ">>> PRIORITY: Phoenix (NumPad3)")
            if cast_skill(WEAPON_KEY_OPTIONS['weapon_3'], DEFAULT_COORDS['weapon_3'], presses=3, delay=0.05):
                last_phoenix = time.time()
                weapon_casts_since_ignite += 1
                time.sleep(WEAPON_CAST_GAP)
                continue
            log_and_print('debug', "Phoenix cast attempt failed (pixel stayed bright)")

        if weapon5_ready:
            log_and_print('info', ">>> PRIORITY: Fire Shield (Focus 5 - NumPad5)")
            if cast_skill(WEAPON_KEY_OPTIONS['weapon_5'], DEFAULT_COORDS['weapon_5'], presses=3, delay=0.05):
                last_fire_shield = time.time()
                weapon_casts_since_ignite += 1
                time.sleep(WEAPON_CAST_GAP)
                continue
            log_and_print('debug', "Fire Shield cast attempt failed (pixel stayed bright)")

        # Filler
        log_and_print('debug', "No high-priority action - letting auto attacks continue")
        time.sleep(0.25)

    log_and_print('info', "Stopping Power Evoker rotation")


def run(stop_event):
    """
    Entry point for the spec. Hold NumPad1 to start the rotation loop.
    """
    logger.info("Power Evoker Fire Inferno spec started")
    log_and_print('info', "=" * 68)
    log_and_print('info', "POWER EVOKER - FIRE INFERNO BUILD")
    log_and_print('info', "Hold NumPad1 to run rotation")
    log_and_print('info', "=" * 68)

    while not stop_event.is_set():
        wait_if_paused()
        if stop_event.is_set():
            break
        if keyboard.is_pressed(key_mapping['numpad1']):
            log_and_print('info', "NumPad1 pressed - starting rotation loop")
            try:
                power_evoker_rotation(stop_event)
            except Exception as exc:
                log_and_print('error', f"Unexpected error in Power Evoker rotation: {exc}")
                raise
        time.sleep(0.05)

    logger.info("Power Evoker Fire Inferno spec ended")


