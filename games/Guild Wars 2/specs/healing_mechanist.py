"""
Mechanist - Alacrity Support Healer
MetaBattle reference: https://metabattle.com/wiki/Build:Mechanist_-_Alacrity_Support_Healer
"""

import sys
import time
import keyboard
from libs.pixel_get_color import get_color as pixel_get_color
from libs.keyboard_actions import button_mash, press, release
from libs.key_mapping import key_mapping
from libs.logger import get_logger
from libs.pause import wait_if_paused

try:
    from libs.config_manager import get_config_manager
except ImportError:
    get_config_manager = None

logger = get_logger('healing_mechanist')
logger.propagate = True

ENABLE_DETAILED_LOGGING = True  # Simplified logging like heal_mech2.py


def log_and_print(level, msg):
    """Simplified logging - only log important events"""
    if level in ('error', 'warning') or ENABLE_DETAILED_LOGGING:
        getattr(logger, level)(msg)
        if ENABLE_DETAILED_LOGGING:
            print(f"[{level.upper()}] {msg}", flush=True)
            sys.stdout.flush()


# Screen space references (triple-monitor baseline, matches previous specs)
DEFAULT_COORDS = {
    # Weapon/kit bar - matching heal_mech2.py coordinates
    'slot_1': (2587, 1013),
    'slot_2': (2625, 1013),
    'slot_3': (2686, 1013),
    'slot_4': (2742, 1015),  # Updated to match heal_mech2.py
    'slot_5': (2799, 1015),  # Updated to match heal_mech2.py

    # Utility toggles (6-0)
    'utility_heal': (2652, 1013),     # Med Kit toggle / heal slot
    'utility_1': (3007, 1013),        # Elixir Gun
    'utility_2': (3070, 1013),        # Barrier Signet
    'utility_3': (3116, 1013),        # Shift Signet (optional)
    'utility_elite': (3171, 1013),    # Mortar Kit

    # Profession skill area (left of weapon bar)
    'barrier_burst': (2478, 984),     # Barrier Burst icon
    'crisis_zone': (2436, 984),       # Crisis Zone / stunbreak

    # Kit state indicators (bright/white when active) - matching heal_mech2.py coordinates
    'indicator_med_kit': (2960, 1035),
    'indicator_elixir_gun': (3015, 1035),
    'indicator_mortar_kit': (3080, 1035),  # Updated to match heal_mech2.py
    'indicator_mortar_dark': (3180, 1025),
    'kit_active_indicator': (2535, 1030),  # If white, we're on a kit (not main weapon)
}

BAR_SLOTS = {
    'slot_1': DEFAULT_COORDS['slot_1'],
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


WEAPON_KEY_OPTIONS = {
    'slot_1': build_keychain(resolve_key('games.GuildWars2.keybinds.mechanist.weapon_1', key_mapping.get('numpad1')), key_mapping.get('numpad1')),
    'slot_2': build_keychain(resolve_key('games.GuildWars2.keybinds.mechanist.weapon_2', key_mapping.get('numpad2')), key_mapping.get('numpad2')),
    'slot_3': build_keychain(resolve_key('games.GuildWars2.keybinds.mechanist.weapon_3', key_mapping.get('numpad3')), key_mapping.get('numpad3')),
    'slot_4': build_keychain(resolve_key('games.GuildWars2.keybinds.mechanist.weapon_4', key_mapping.get('numpad4')), key_mapping.get('numpad4')),
    'slot_5': build_keychain(resolve_key('games.GuildWars2.keybinds.mechanist.weapon_5', key_mapping.get('numpad5')), key_mapping.get('numpad5')),
}

UTILITY_KEY_OPTIONS = {
    'utility_heal': build_keychain(resolve_key('games.GuildWars2.keybinds.mechanist.med_kit', key_mapping.get('numpad6')), key_mapping.get('numpad6')),
    'utility_1': build_keychain(resolve_key('games.GuildWars2.keybinds.mechanist.elixir_gun', key_mapping.get('numpad7')), key_mapping.get('numpad7')),
    'utility_2': build_keychain(resolve_key('games.GuildWars2.keybinds.mechanist.barrier_signet', key_mapping.get('numpad8')), key_mapping.get('numpad8')),
    'utility_3': build_keychain(resolve_key('games.GuildWars2.keybinds.mechanist.shift_signet', key_mapping.get('numpad9')), key_mapping.get('numpad9')),
    'utility_elite': build_keychain(resolve_key('games.GuildWars2.keybinds.mechanist.mortar_kit', key_mapping.get('numpad0')), key_mapping.get('numpad0')),
}

KIT_KEY_OPTIONS = {
    'shortbow': [],  # weapon set, no toggle required
    'med_kit': UTILITY_KEY_OPTIONS['utility_heal'],
    'elixir_gun': UTILITY_KEY_OPTIONS['utility_1'],
    'mortar_kit': UTILITY_KEY_OPTIONS['utility_elite'],
}

DROP_BUNDLE_KEYS = build_keychain(
    resolve_key('games.GuildWars2.keybinds.mechanist.drop_bundle', 'f'),
    'f'
)

MECH_COMMAND_KEYS = {
    'barrier_burst': build_keychain(resolve_key('games.GuildWars2.keybinds.mechanist.barrier_burst', '3'), '3'),
    'crisis_zone': build_keychain(resolve_key('games.GuildWars2.keybinds.mechanist.crisis_zone', '2'), '2'),
}

COOLDOWNS = {
    'barrier_burst': 10.0,
    'crisis_zone': 25.0,
    'super_elixir': 16.0,      # Elixir Gun 5
    'acid_bomb': 20.0,         # Elixir Gun 4
    'elixir_shell': 15.0,      # Mortar Kit 5
    'mortar_flash': 18.0,      # Mortar Kit 3
    'mortar_poison': 20.0,     # Mortar Kit 2
    'bandage_blast': 12.0,     # Med Kit toolbelt
    'infusion_bomb': 12.0,     # Med Kit 5 - key for burst healing
    'vital_blast': 12.0,       # Med Kit 4
    'med_pack_drop': 18.0,     # Med Kit 5
    'barrier_signet': 25.0,
    'shortbow_2': 5.75,        # Essence of Animated Sand
    'shortbow_3': 8.0,         # Essence of Living Shadows
    'shortbow_4': 12.0,        # Essence of Liquid Wrath
    'shortbow_5': 15.0,        # Essence of Borrowed Time
}
FORCE_INTERVALS = {
    'barrier_signet': 40.0,
}

SKILL_READY_PIXEL_MIN = 40
SKILL_ON_COOLDOWN_MAX = 75
KIT_ACTIVE_THRESHOLD = 600
MORTAR_INACTIVE_MAX = 320

STOP_KEY = key_mapping.get('numpad1', 'numpad1')


def check_stop_condition(stop_event):
    return not keyboard.is_pressed(STOP_KEY) or stop_event.is_set()


def get_slot_brightness(slot_name):
    coords = BAR_SLOTS.get(slot_name)
    if not coords:
        return 0
    color = pixel_get_color(coords[0], coords[1])
    return sum(color) if color else 0


def get_coord_brightness(coord_name):
    coords = DEFAULT_COORDS.get(coord_name)
    if not coords:
        return 0
    color = pixel_get_color(coords[0], coords[1])
    return sum(color) if color else 0


def check_skill_available(coords, threshold=None):
    """Check if skill is ready - simpler approach: not black means ready"""
    color = pixel_get_color(coords[0], coords[1])
    if color is None:
        return False
    # Simple check: if pixel is not black, skill is ready (like heal_mech2.py)
    return color != (0, 0, 0)


def cancel_acid_bomb_movement(stop_event):
    """Cancel Acid Bomb movement by immediately weapon swapping like heal_mech2.py"""
    # Immediately weapon swap to cancel the backward movement
    weapon_swap_key = resolve_key('games.GuildWars2.keybinds.mechanist.weapon_swap', key_mapping.get('f1'))
    if weapon_swap_key:
        button_mash(weapon_swap_key, presses=1, delay=0.02, stop_check=None)
    else:
        # Fallback to F1
        button_mash('f1', presses=1, delay=0.02, stop_check=None)
    time.sleep(0.1)  # Brief wait for swap to register


def detect_active_kit(debug=False):
    """Detect active kit: if (2535, 1030) is white, we're on a kit, otherwise shortbow"""
    kit_active_color = pixel_get_color(*DEFAULT_COORDS['kit_active_indicator'])
    
    # If kit_active_indicator is not white, we're on main weapon (shortbow)
    if not kit_active_color or kit_active_color != (255, 255, 255):
        if debug:
            log_and_print('debug', f"Kit active indicator: {kit_active_color} - on SHORTBOW")
        return 'shortbow'
    
    # We're on a kit, now check which one
    elixir_color = pixel_get_color(*DEFAULT_COORDS['indicator_elixir_gun'])
    mortar_color = pixel_get_color(*DEFAULT_COORDS['indicator_mortar_kit'])
    med_color = pixel_get_color(*DEFAULT_COORDS['indicator_med_kit'])
    
    if debug:
        log_and_print('debug', f"On a kit - Elixir: {elixir_color}, Mortar: {mortar_color}, Med: {med_color}")
    
    # Elixir Gun and Med Kit are white when active
    if elixir_color == (255, 255, 255):
        return 'elixir_gun'
    
    if med_color == (255, 255, 255):
        return 'med_kit'
    
    # Mortar Kit is greenish/white when active - higher threshold to avoid false positives
    mortar_brightness = sum(mortar_color) if mortar_color else 0
    if mortar_brightness > 200:  # Greenish (147,221,131) = 499 brightness
        return 'mortar_kit'

    # Fallback: if kit_active_indicator is white but no specific kit detected, default to shortbow
    if debug:
        log_and_print('warning', f"Kit active but no specific kit detected - defaulting to SHORTBOW")
    return 'shortbow'


def wait_until_on_cooldown(coords, timeout_seconds=1.2, poll_seconds=0.05, min_wait_after=0.0):
    """
    Wait for a skill to go on cooldown (pixel goes dark).
    After the skill goes on cooldown, wait an additional min_wait_after seconds
    to ensure the full animation/AOE completes.
    Returns True if skill went on cooldown OR if we've waited long enough (forgiving).
    """
    if coords is None:
        return True
    start = time.time()
    went_on_cooldown = False
    while (time.time() - start) < timeout_seconds:
        color = pixel_get_color(coords[0], coords[1])
        if color is None:
            # Pixel read failed - assume success after minimum wait
            break
        if sum(color) <= SKILL_ON_COOLDOWN_MAX:
            went_on_cooldown = True
            break
        time.sleep(poll_seconds)
    
    # If skill went on cooldown, wait additional time for animation to complete
    if went_on_cooldown and min_wait_after > 0:
        time.sleep(min_wait_after)
    elif not went_on_cooldown and min_wait_after > 0:
        # Even if pixel didn't go dark, wait for animation to complete
        time.sleep(min_wait_after)
    
    # Return True if skill went on cooldown OR if we've waited at least 70% of timeout
    # This is forgiving - sometimes pixel detection isn't perfect but skill still fired
    elapsed = time.time() - start
    return went_on_cooldown or (elapsed >= timeout_seconds * 0.7)


def cast_skill(key_candidates, coords, presses=2, delay=0.05, wait_timeout=1.0, min_wait_after=0.0):
    """
    Cast a skill by pressing keys and waiting for it to go on cooldown.
    Returns True if button was pressed AND (skill went on cooldown OR waited long enough).
    This is forgiving - if we pressed the button, we consider it successful even if pixel detection fails.
    """
    if not key_candidates:
        return False
    for key in ensure_iterable(key_candidates):
        if button_mash(key, presses=presses, delay=delay, stop_check=None):
            # Button was pressed - wait for cooldown (forgiving)
            # wait_until_on_cooldown returns True if skill went on cooldown OR waited at least 70% of timeout
            skill_went_on_cooldown = wait_until_on_cooldown(coords, timeout_seconds=wait_timeout, min_wait_after=min_wait_after)
            # Return True if button was pressed AND (skill went on cooldown OR waited long enough)
            # This matches the docstring contract and uses the wait result
            return skill_went_on_cooldown
    return False


def tap_keys(key_candidates, presses=1, delay=0.03):
    for key in ensure_iterable(key_candidates):
        if button_mash(key, presses=presses, delay=delay, stop_check=None):
            return True
    return False


def wait_for_kit_switch(target_kit, timeout=2.0):
    """Wait for kit switch to complete by checking pixel colors"""
    # Give the game time to process the kit switch input
    time.sleep(0.3)
    
    # Check immediately with debug
    initial_detected = detect_active_kit(debug=True)
    log_and_print('debug', f"Initial detection after kit switch: {initial_detected} (wanting {target_kit})")
    
    start = time.time()
    while (time.time() - start) < timeout:
        detected = detect_active_kit()
        if detected == target_kit:
            log_and_print('debug', f"Successfully detected {target_kit} after {time.time() - start:.2f}s")
            return True
        # Log what we're detecting if it's not the target (but not every iteration to avoid spam)
        if (time.time() - start) < 0.5:  # Only log in first 0.5 seconds
            log_and_print('debug', f"Waiting for {target_kit}, currently detecting: {detected}")
        time.sleep(0.1)
    
    # Final check with debug
    final_detected = detect_active_kit(debug=True)
    log_and_print('warning', f"Kit switch timeout: wanted {target_kit}, final detection: {final_detected}")
    return False


def healing_mechanist_rotation(stop_event):
    """
    Priority system tuned for Mechanist Alacrity Support Healer.
    Focus: Short Bow sustain (Might/Barrier/Protection/Aegis), Barrier Burst uptime,
    Elixir Gun cleanses, Med Kit bursts, Mortar blast finishers, Barrier Signet.

    Per MetaBattle guide:
    - Barrier Burst: Use off cooldown (10s base, 14s with Mechanical Genius penalty)
    - Short Bow 2-5: Use off cooldown for Might, Barrier, Protection, CC
    - Short Bow 2 (Essence of Animated Sand): Might + Barrier
    - Short Bow 3 (Essence of Living Shadows): Barrier + Healing
    - Short Bow 4 (Essence of Liquid Wrath): Protection + Aegis
    - Short Bow 5 (Essence of Borrowed Time): CC + Superspeed
    - Elixir Gun 4 (Acid Bomb): Condition cleanse + knockback (F1 cancel to avoid knockback)
    - Elixir Gun 5 (Super Elixir): Rapid healing
    - Med Kit 4 (Vital Blast): Burst heal
    - Med Kit 5 (Infusion Bomb): Regeneration + boons

    Meta reference: MetaBattle (July 27 2024, up-to-date for June 2 2026 patch).
    """
    loop_count = 0
    med_important_skills_used = False  # Track whether Vital Blast/Infused Bomb have been cast this Med visit
    current_kit = 'shortbow'  # Internal state tracking: 'shortbow', 'elixir_gun', 'mortar_kit', 'med_kit'
    kit_priority = 0  # Rotating priority for which kit to visit when Shortbow has nothing
    while not stop_event.is_set():
        loop_count += 1
        wait_if_paused()
        if check_stop_condition(stop_event):
            log_and_print('debug', "Stop condition detected - exiting rotation")
            break

        # Always cast Barrier Burst and weapon skills 1, 2, 3 first (exactly like heal_mech2.py)
        log_and_print('debug', f"Loop {loop_count}: Casting Barrier Burst and weapon skills 1, 2, 3")
        button_mash(MECH_COMMAND_KEYS['barrier_burst'][0] if MECH_COMMAND_KEYS['barrier_burst'] else key_mapping.get('3', '3'),
                   stop_check=lambda: check_stop_condition(stop_event))
        if check_stop_condition(stop_event): break

        button_mash('1', stop_check=lambda: check_stop_condition(stop_event))
        if check_stop_condition(stop_event): break

        button_mash('2', stop_check=lambda: check_stop_condition(stop_event))
        if check_stop_condition(stop_event): break

        button_mash('3', stop_check=lambda: check_stop_condition(stop_event))
        if check_stop_condition(stop_event): break

        time.sleep(0.35)
        if check_stop_condition(stop_event): break

        # Log current kit state
        log_and_print('debug', f"Active kit: {current_kit}")

        # Handle kit-specific logic based on internal state
        if current_kit == 'elixir_gun':
            # Elixir Gun - slot 4 (Acid Bomb) + slot 5 (Super Elixir)
            slot_4_color = pixel_get_color(*BAR_SLOTS['slot_4'])
            slot_4_ready = slot_4_color and slot_4_color != (0, 0, 0)

            if slot_4_ready:
                # Acid Bomb (Elixir Gun 4) - condition cleanse + knockback
                # F1 cancel prevents backward launch
                log_and_print('info', "Casting Acid Bomb (Elixir Gun 4)")
                if not button_mash(key_mapping['numpad4'], stop_check=lambda: check_stop_condition(stop_event)): break
                time.sleep(0.6)  # Wait for ability + cancel to complete
                if check_stop_condition(stop_event): break
                # Cancel with F1
                log_and_print('info', "Canceling with F1")
                if not button_mash(key_mapping['f1'], stop_check=lambda: check_stop_condition(stop_event)): break
                time.sleep(0.35)
                if check_stop_condition(stop_event): break
                continue

            slot_5_color = pixel_get_color(*BAR_SLOTS['slot_5'])
            slot_5_ready = slot_5_color and slot_5_color != (0, 0, 0)

            if slot_5_ready:
                log_and_print('info', "Casting Super Elixir (Elixir Gun 5)")
                if not button_mash(key_mapping['numpad5'], stop_check=lambda: check_stop_condition(stop_event)): break
                time.sleep(0.6)  # Wait for ability to complete
                if check_stop_condition(stop_event): break
                continue

            # No skills ready — swap back to Shortbow
            log_and_print('info', "Elixir Gun: No skills ready, swapping back to Shortbow")
            if not button_mash(key_mapping['f1'], stop_check=lambda: check_stop_condition(stop_event)): break
            time.sleep(0.35)
            if check_stop_condition(stop_event): break
            current_kit = 'shortbow'

        elif current_kit == 'mortar_kit':
            # Mortar Kit - slot 1 (Mortar Shot), slot 5 (Elixir Shell)
            # Cast what's ready, then wait briefly before swapping back.
            # DO NOT auto-switch to Med Kit — let the next loop decide.
            slot_1_color = pixel_get_color(*BAR_SLOTS['slot_1'])
            slot_1_ready = slot_1_color and slot_1_color != (0, 0, 0)

            if slot_1_ready:
                log_and_print('info', "Casting Mortar Shot (Mortar Kit 1)")
                if not button_mash(key_mapping['numpad1'], stop_check=lambda: check_stop_condition(stop_event)): break
                time.sleep(0.6)  # Wait for ability to complete before checking next
                if check_stop_condition(stop_event): break

            slot_5_color = pixel_get_color(*BAR_SLOTS['slot_5'])
            slot_5_ready = slot_5_color and slot_5_color != (0, 0, 0)

            if slot_5_ready:
                log_and_print('info', "Casting Elixir Shell (Mortar Kit 5)")
                if not button_mash(key_mapping['numpad5'], stop_check=lambda: check_stop_condition(stop_event)): break
                time.sleep(0.6)  # Wait for ability to complete
                if check_stop_condition(stop_event): break

            # Swap back to Shortbow
            log_and_print('info', "Mortar Kit: done, swapping back to Shortbow")
            if not button_mash(key_mapping['f1'], stop_check=lambda: check_stop_condition(stop_event)): break
            time.sleep(0.35)
            if check_stop_condition(stop_event): break
            current_kit = 'shortbow'

        elif current_kit == 'med_kit':
            # Med Kit - slot 1 (Med Blaster), slot 4 (Vital Blast), slot 5 (Infusion Bomb)
            # Cast burst skills (4/5) first, then Med Blaster as filler.
            # Only swap back after burst skills are used or if nothing is ready at all.
            slot_1_color = pixel_get_color(*BAR_SLOTS['slot_1'])
            slot_1_ready = slot_1_color and slot_1_color != (0, 0, 0)

            slot_4_color = pixel_get_color(*BAR_SLOTS['slot_4'])
            slot_4_ready = slot_4_color and slot_4_color != (0, 0, 0)

            slot_5_color = pixel_get_color(*BAR_SLOTS['slot_5'])
            slot_5_ready = slot_5_color and slot_5_color != (0, 0, 0)

            # If NOTHING is ready, swap out immediately
            if not slot_1_ready and not slot_4_ready and not slot_5_ready:
                log_and_print('info', "Med Kit: no skills ready, swapping back to Shortbow")
                if not button_mash(key_mapping['f1'], stop_check=lambda: check_stop_condition(stop_event)): break
                time.sleep(0.35)
                if check_stop_condition(stop_event): break
                current_kit = 'shortbow'
                med_important_skills_used = False
            else:
                # Cast burst skills first
                if slot_4_ready:
                    log_and_print('info', "Casting Vital Blast (Med Kit 4)")
                    if not button_mash(key_mapping['numpad4'], stop_check=lambda: check_stop_condition(stop_event)): break
                    time.sleep(0.35)
                    if check_stop_condition(stop_event): break
                    med_important_skills_used = True

                if slot_5_ready:
                    log_and_print('info', "Casting Infusion Bomb (Med Kit 5)")
                    if not button_mash(key_mapping['numpad5'], stop_check=lambda: check_stop_condition(stop_event)): break
                    time.sleep(0.35)
                    if check_stop_condition(stop_event): break
                    med_important_skills_used = True

                # Med Blaster as filler (only if we already cast a burst skill)
                if slot_1_ready and med_important_skills_used:
                    log_and_print('info', "Casting Med Blaster (Med Kit 1)")
                    if not button_mash(key_mapping['numpad1'], stop_check=lambda: check_stop_condition(stop_event)): break
                    time.sleep(0.35)
                    if check_stop_condition(stop_event): break

                # Swap back after using burst skills
                if med_important_skills_used:
                    log_and_print('info', "Med Kit: weapon swapping back to Shortbow")
                    if not button_mash(key_mapping['f1'], stop_check=lambda: check_stop_condition(stop_event)): break
                    time.sleep(0.35)
                    if check_stop_condition(stop_event): break
                    current_kit = 'shortbow'
                    med_important_skills_used = False

        else:  # shortbow
            # Short Bow: Cast ALL ready skills 2-5
            # Slot 2: Essence of Animated Sand (Might)
            # Slot 3: Essence of Living Shadows (Barrier)
            # Slot 4: Essence of Liquid Wrath (Protection/Aegis)
            # Slot 5: Essence of Borrowed Time (CC/Superspeed)

            slot_2_color = pixel_get_color(*BAR_SLOTS['slot_2'])
            slot_2_ready = slot_2_color and slot_2_color != (0, 0, 0)

            slot_3_color = pixel_get_color(*BAR_SLOTS['slot_3'])
            slot_3_ready = slot_3_color and slot_3_color != (0, 0, 0)

            slot_4_color = pixel_get_color(*BAR_SLOTS['slot_4'])
            slot_4_ready = slot_4_color and slot_4_color != (0, 0, 0)

            slot_5_color = pixel_get_color(*BAR_SLOTS['slot_5'])
            slot_5_ready = slot_5_color and slot_5_color != (0, 0, 0)

            log_and_print('debug', f"Shortbow: S2={slot_2_ready} S3={slot_3_ready} S4={slot_4_ready} S5={slot_5_ready}")

            # Cast slot 2 (Essence of Animated Sand) — Might + Barrier
            if slot_2_ready:
                log_and_print('info', "Casting Essence of Animated Sand (Shortbow 2)")
                if not button_mash(key_mapping['numpad2'], stop_check=lambda: check_stop_condition(stop_event)):
                    break
                time.sleep(0.35)
                if check_stop_condition(stop_event): break

            # Cast slot 3 (Essence of Living Shadows) — Barrier + Healing
            if slot_3_ready:
                log_and_print('info', "Casting Essence of Living Shadows (Shortbow 3)")
                if not button_mash(key_mapping['numpad3'], stop_check=lambda: check_stop_condition(stop_event)):
                    break
                time.sleep(0.35)
                if check_stop_condition(stop_event): break

            # Cast slot 4 (Essence of Liquid Wrath) — Protection + Aegis
            if slot_4_ready:
                log_and_print('info', "Casting Essence of Liquid Wrath (Shortbow 4)")
                if not button_mash(key_mapping['numpad4'], stop_check=lambda: check_stop_condition(stop_event)):
                    break
                time.sleep(0.35)
                if check_stop_condition(stop_event): break

            # Cast slot 5 (Essence of Borrowed Time) — CC + Superspeed
            if slot_5_ready:
                log_and_print('info', "Casting Essence of Borrowed Time (Shortbow 5)")
                if not button_mash(key_mapping['numpad5'], stop_check=lambda: check_stop_condition(stop_event)):
                    break
                time.sleep(0.35)
                if check_stop_condition(stop_event): break

            # After shortbow: visit a kit if no skills were ready
            # Use rotating priority to ensure all kits get visited over time
            any_ready = slot_2_ready or slot_3_ready or slot_4_ready or slot_5_ready
            if not any_ready:
                # Rotate through kits: 0=Elixir, 1=Mortar, 2=Med
                if kit_priority == 0:
                    # Try Elixir Gun
                    log_and_print('info', "Shortbow: No skills ready, switching to Elixir Gun")
                    if not button_mash(key_mapping['numpad7'], stop_check=lambda: check_stop_condition(stop_event)):
                        break
                    time.sleep(0.35)
                    if check_stop_condition(stop_event): break
                    current_kit = 'elixir_gun'
                elif kit_priority == 1:
                    # Try Mortar Kit
                    log_and_print('info', "Shortbow: No skills ready, switching to Mortar Kit")
                    if not button_mash(key_mapping['numpad0'], stop_check=lambda: check_stop_condition(stop_event)):
                        break
                    time.sleep(0.35)
                    if check_stop_condition(stop_event): break
                    current_kit = 'mortar_kit'
                else:
                    # Try Med Kit
                    log_and_print('info', "Shortbow: No skills ready, switching to Med Kit")
                    if not button_mash(key_mapping['numpad6'], stop_check=lambda: check_stop_condition(stop_event)):
                        break
                    time.sleep(0.35)
                    if check_stop_condition(stop_event): break
                    current_kit = 'med_kit'

                # Advance priority for next time
                kit_priority = (kit_priority + 1) % 3

        # Always cast Barrier Signet at the end (like heal_mech2.py)
        log_and_print('debug', "Casting Barrier Signet")
        if not button_mash(key_mapping['numpad8'], stop_check=lambda: check_stop_condition(stop_event)):
            break
        time.sleep(0.35)
        if check_stop_condition(stop_event): break

    log_and_print('info', "Stopping Mechanist Alacrity Support Healer rotation")


def run(stop_event):
    logger.info("Healing Mechanist spec started")
    log_and_print('info', "=" * 70)
    log_and_print('info', "MECHANIST - ALACRITY SUPPORT HEALER")
    log_and_print('info', "Hold NumPad1 to run rotation")
    log_and_print('info', "=" * 70)

    while not stop_event.is_set():
        wait_if_paused()
        if stop_event.is_set():
            break
        if keyboard.is_pressed(STOP_KEY):
            log_and_print('info', "NumPad1 pressed - starting rotation loop")
            try:
                healing_mechanist_rotation(stop_event)
            except Exception as exc:
                log_and_print('error', f"Unexpected error in Healing Mechanist rotation: {exc}")
                raise
            # CRITICAL: Wait for key release before re-arming
            # Prevents infinite start/stop loop when start_key == stop_key
            while keyboard.is_pressed(STOP_KEY) and not stop_event.is_set():
                time.sleep(0.05)
        time.sleep(0.05)

    logger.info("Healing Mechanist spec ended")
