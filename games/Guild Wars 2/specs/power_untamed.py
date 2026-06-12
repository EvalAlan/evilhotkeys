"""
Untamed - Power Untamed Build for Guild Wars 2
Based on: https://metabattle.com/wiki/Build:Untamed_-_Power_Untamed

Key ideas from the guide:
- Stay Unleashed (ranger mode) for Vow of the Untamed damage bonus.
- Use Unleashed Ambush on weapon swap (Let Loose resets cooldown each swap).
  * Axe Unleashed Ambush: Sundering Volley
  * Mace Unleashed Ambush: Rampant Growth
- Axe/Axe for damage, pull, projectile reflection.
- Mace/Mace for CC, barrier, stability, condition removal, healing.
  Mace skills reset via Nature's Strength trait — use them twice per weapon set.
- Pet cycle: Start unleashed, send pet attack with F1, then Unleash Ranger.
  When weapon swap is almost ready, Unleash Pet, cast F1/F2/F3, Unleash Ranger.
- Utilities: Frost Trap (damage + Predator's Onslaught), "Protect Me!" (stunbreak +
  barrier), Storm Spirit (AoE damage + vulnerability + fury).
- Heal: "We Heal As One!" — copies boons to pet, low CD.
- Elite: Forest's Fortification (defensive).

Pixel coordinates assume the same triple-monitor layout as existing specs.
Adjust if your resolution/font differs.
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

logger = get_logger('power_untamed')
logger.propagate = True

ENABLE_DETAILED_LOGGING = True


def log_and_print(level, msg):
    """Log and optionally print for debugging (matches healing_mechanist pattern)."""
    if level in ('error', 'warning') or ENABLE_DETAILED_LOGGING:
        getattr(logger, level)(msg)
        if ENABLE_DETAILED_LOGGING:
            print(f"[{level.upper()}] {msg}", flush=True)
            sys.stdout.flush()


# Pixel coordinates — same triple-monitor baseline as existing specs
DEFAULT_COORDS = {
    # Weapon skills (NumPad1-5)
    'weapon_1': (2587, 1013),
    'weapon_2': (2625, 1013),
    'weapon_3': (2686, 1013),
    'weapon_4': (2743, 1013),
    'weapon_5': (2801, 1013),

    # Utility bar (NumPad6-0)
    'utility_heal': (2652, 1013),     # "We Heal As One!"
    'utility_1': (3007, 1013),        # Frost Trap
    'utility_2': (3070, 1013),        # "Protect Me!"
    'utility_3': (3116, 1013),        # Storm Spirit
    'utility_elite': (3171, 1013),    # Forest's Fortification

    # Weapon swap indicator (bright when ready)
    'weapon_swap': (2530, 1010),

    # Weapon set indicator pixel
    #   Bright (>=220) = AXE, Dark (<=140) = MACE
    #   Same coordinate as soulbeast.py WEAPON_INDICATOR_PIXEL
    'weapon_set_indicator': (2820, 1049),

    # Unleashed Ambush cooldown pixel (slot-specific; we check both)
    # Axe ambush is on the same weapon bar as axe skills
    # Mace ambush is on the same weapon bar as mace skills
    'unleash_ambush_axe': (2587, 1013),    # checked on axe set
    'unleash_ambush_mace': (2587, 1013),   # checked on Mace set

    # Pet state indicator — bright when pet is unleashed
    'pet_unleashed': (2596, 970),

    # Pet skill pixels (F1-F3)
    'pet_skill_1': (2643, 943),    # F1 — Venomous Outburst / pet attack
    'pet_skill_2': (2685, 940),    # F2
    'pet_skill_3': (2742, 943),    # F3
}

# Pixel for detecting weapon set
WEAPON_INDICATOR_PIXEL = DEFAULT_COORDS['weapon_set_indicator']

# Unleashed Ambush ready pixel — bright when available
UNLEASHED_AMBUSH_PIXEL_AXE = (2743, 1013)   # weapon_4 slot when on axe
UNLEASHED_AMBUSH_PIXEL_MACE = (2743, 1013)  # weapon_4 slot when on mace


def resolve_key(path: str, default):
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
    chain = []
    for key in keys:
        if not key:
            continue
        if isinstance(key, (list, tuple)):
            for sub_key in key:
                if sub_key:
                    chain.append(sub_key)
        else:
            chain.append(key)
    return chain


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
UNLEASH_PET_KEYS = build_keychain(
    resolve_key('games.GuildWars2.keybinds.untamed.unleash_pet', key_mapping.get('f4', 'f4')),
    key_mapping.get('f4', 'f4'),
)

UNLEASH_RANGER_KEYS = build_keychain(
    resolve_key('games.GuildWars2.keybinds.untamed.unleash_ranger', key_mapping.get('f5', 'f5')),
    key_mapping.get('f5', 'f5'),
)

WEAPON_SWAP_KEYS = build_keychain(
    resolve_key('games.GuildWars2.keybinds.untamed.weapon_swap', key_mapping.get('f1', 'f1')),
    key_mapping.get('f1', 'f1'),
    key_mapping.get('numpad7', 'numpad7'),
    'tab',
)

# Pet skill keys (F1-F3)
PET_SKILL_KEYS = {
    'pet_skill_1': build_keychain(
        resolve_key('games.GuildWars2.keybinds.untamed.pet_skill_1', key_mapping.get('f1', 'f1')),
        key_mapping.get('f1', 'f1'),
    ),
    'pet_skill_2': build_keychain(
        resolve_key('games.GuildWars2.keybinds.untamed.pet_skill_2', key_mapping.get('f2', 'f2')),
        key_mapping.get('f2', 'f2'),
    ),
    'pet_skill_3': build_keychain(
        resolve_key('games.GuildWars2.keybinds.untamed.pet_skill_3', key_mapping.get('f3', 'f3')),
        key_mapping.get('f3', 'f3'),
    ),
}

# Timing constants (seconds)
UTILITY_STAGGER = {
    'utility_elite': 45.0,    # Forest's Fortification
    'utility_1': 20.0,        # Frost Trap
    'utility_2': 16.0,        # "Protect Me!"
    'utility_3': 30.0,        # Storm Spirit
    'utility_heal': 23.0,     # "We Heal As One!"
}
UTILITY_FORCE_INTERVAL = {
    'utility_elite': 70.0,
    'utility_1': 35.0,
    'utility_2': 24.0,
    'utility_3': 40.0,
    'utility_heal': 45.0,
}

SKILL_READY_PIXEL_MIN = 40
SKILL_ON_COOLDOWN_MAX = 75
WEAPON_SET_MIN_TIME = 5.0
UNLEASH_AMBUSH_THRESHOLD = 180  # brightness threshold for unleashed ambush availability

STOP_KEY = key_mapping.get('numpad1', 'numpad1')

# Axe skill priority order (soulbeast reference)
AXE_PRIORITY = ['weapon_4', 'weapon_5', 'weapon_3', 'weapon_2']
# Mace skill priority order
MACE_PRIORITY = ['weapon_2', 'weapon_3', 'weapon_4', 'weapon_5']

# Timeout overrides per slot for cast_skill wait
AXE_TIMEOUT_OVERRIDES = {
    'weapon_2': (1.0, 0.04),
    'weapon_3': (1.0, 0.04),
    'weapon_4': (1.2, 0.06),
    'weapon_5': (1.2, 0.06),
}
MACE_TIMEOUT_OVERRIDES = {
    'weapon_2': (1.1, 0.05),
    'weapon_3': (1.2, 0.06),
    'weapon_4': (1.4, 0.08),
    'weapon_5': (2.2, 0.1),
}

LAST_WEAPON_SET = 'axe'
LAST_UTILITY_TIMES = {name: 0.0 for name in DEFAULT_COORDS if name.startswith('utility')}


def check_stop_condition(stop_event):
    """Stop if NumPad1 released or requested via stop_event."""
    return not keyboard.is_pressed(STOP_KEY) or stop_event.is_set()


def check_skill_available(coords, threshold=210):
    """Return True if the skill pixel is bright enough to imply readiness."""
    color = pixel_get_color(coords[0], coords[1])
    if color is None:
        return False
    brightness = sum(color)
    return brightness > SKILL_READY_PIXEL_MIN


def get_skill_brightness(name):
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


def wait_until_on_cooldown(coords, timeout_seconds=1.2, poll_seconds=0.05, min_wait_after=0.0):
    """Wait for a skill to go on cooldown (pixel goes dark)."""
    if coords is None:
        return True
    start = time.time()
    went_on_cooldown = False
    while (time.time() - start) < timeout_seconds:
        color = pixel_get_color(coords[0], coords[1])
        if color is None:
            break
        if sum(color) <= SKILL_ON_COOLDOWN_MAX:
            went_on_cooldown = True
            break
        time.sleep(poll_seconds)

    if went_on_cooldown and min_wait_after > 0:
        time.sleep(min_wait_after)
    elif not went_on_cooldown and min_wait_after > 0:
        time.sleep(min_wait_after)

    elapsed = time.time() - start
    return went_on_cooldown or (elapsed >= timeout_seconds * 0.7)


def cast_skill(key_candidates, coords, presses=3, delay=0.05, wait_timeout=1.0, min_wait_after=0.0):
    """Cast a skill by pressing keys and waiting for it to go on cooldown."""
    if not key_candidates:
        return False
    for key in key_candidates:
        if isinstance(key, (list, tuple)):
            # key already built by build_keychain; flatten
            pass
        if button_mash(key, presses=presses, delay=delay, stop_check=None):
            skill_went_on_cooldown = wait_until_on_cooldown(coords, timeout_seconds=wait_timeout, min_wait_after=min_wait_after)
            return skill_went_on_cooldown
    return False


def tap_keys(key_candidates, presses=1, delay=0.03):
    for key in key_candidates:
        if button_mash(key, presses=presses, delay=delay, stop_check=None):
            return True
    return False


def detect_weapon_set():
    """
    Detect current weapon set via indicator pixel.
    Bright (>=220) = AXE, Dark (<=140) = MACE.
    """
    global LAST_WEAPON_SET
    color = pixel_get_color(*WEAPON_INDICATOR_PIXEL)
    if not color:
        log_and_print('debug', f"Weapon set pixel read failed, keeping {LAST_WEAPON_SET}")
        return LAST_WEAPON_SET

    brightness = sum(color)

    if brightness <= 140:
        LAST_WEAPON_SET = 'mace'
        return LAST_WEAPON_SET

    if brightness >= 220:
        LAST_WEAPON_SET = 'axe'
        return LAST_WEAPON_SET

    return LAST_WEAPON_SET


def ensure_weapon_swap(current_set):
    """Attempt weapon swap and verify the set actually changed."""
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


def is_pet_unleashed():
    """Check if pet is currently unleashed via pixel color."""
    color = pixel_get_color(*DEFAULT_COORDS.get('pet_unleashed', (2596, 970)))
    if not color:
        return False
    brightness = sum(color)
    return brightness > 100


def unleash_pet():
    """Send Unleash Pet command."""
    log_and_print('info', "Unleashing pet")
    tap_keys(UNLEASH_PET_KEYS)
    time.sleep(0.3)


def unleash_ranger():
    """Send Unleash Ranger command (return to ranger mode)."""
    log_and_print('info', "Unleashing ranger")
    tap_keys(UNLEASH_RANGER_KEYS)
    time.sleep(0.3)


def send_pet_attack():
    """Send pet F1 attack command."""
    log_and_print('debug', "Sending pet attack (F1)")
    tap_keys(['f1'])
    time.sleep(0.2)


def unleash_pet_cycle(stop_event):
    """
    Full pet cycle per the metabattle guide:
    1. Start with pet unleashed (unleash_pet)
    2. Send pet attack (F1)
    3. Unleash Ranger
    """
    wait_if_paused()
    if check_stop_condition(stop_event):
        return False
    unleash_pet()
    if check_stop_condition(stop_event):
        return False
    send_pet_attack()
    if check_stop_condition(stop_event):
        return False
    unleash_ranger()
    return True


def cast_unleashed_ambush(stop_event):
    """
    Cast the Unleashed Ambush skill for the current weapon set.
    Uses weapon_4 key (standard slot for unleashed ambush after weapon swap)
    with brightness-based availability check.
    """
    ambush_pixel = UNLEASHED_AMBUSH_PIXEL_AXE  # same coord for both sets
    color = pixel_get_color(*ambush_pixel)
    brightness = sum(color) if color else 0

    if brightness < UNLEASH_AMBUSH_THRESHOLD:
        log_and_print('danger', f"Unleashed Ambush pixel brightness too low ({brightness}), skipping")
        return False

    log_and_print('info', ">>> PRIORITY: Unleashed Ambush")
    # Unleash ambush typically on weapon_4 key
    if cast_skill(WEAPON_KEY_OPTIONS['weapon_4'], ambush_pixel, presses=3, delay=0.05, wait_timeout=1.5):
        log_and_print('debug', "Unleashed Ambush cast OK")
        return True
    else:
        log_and_print('debug', "Unleashed Ambush cast failed")
        return False


def cast_weapon_skills(current_set, weapon_ready, stop_event):
    """Cast weapon skills in priority order for the given set."""
    if current_set == 'axe':
        priority = AXE_PRIORITY
        overrides = AXE_TIMEOUT_OVERRIDES
    else:
        priority = MACE_PRIORITY
        overrides = MACE_TIMEOUT_OVERRIDES

    triggered = False
    for slot in priority:
        if weapon_ready.get(slot, False):
            label = f"Weapon Skill {slot[-1]} ({current_set.upper()})"
            log_and_print('info', f">>> PRIORITY: {label}")
            wait_timeout, delay = overrides.get(slot, (1.4, 0.05))
            if cast_skill(WEAPON_KEY_OPTIONS[slot], DEFAULT_COORDS[slot], presses=3, delay=delay, wait_timeout=wait_timeout):
                triggered = True
                break
            else:
                log_and_print('debug', f"{label} cast failed")
    return triggered


def cast_utility_if_needed(util_name, current_time, last_use_times, utilities_ready, stop_event):
    """Check and cast a utility skill if it's ready and off stagger/force interval."""
    time_since = current_time - last_use_times[util_name]

    if utilities_ready[util_name] and time_since > UTILITY_STAGGER[util_name]:
        label = {
            'utility_elite': "Forest's Fortification",
            'utility_1': "Frost Trap",
            'utility_2': '"Protect Me!"',
            'utility_3': "Storm Spirit",
            'utility_heal': '"We Heal As One!"',
        }[util_name]
        log_and_print('info', f">>> PRIORITY: {label}")
        start_brightness = get_skill_brightness(util_name)
        if cast_skill(UTILITY_KEY_OPTIONS[util_name], DEFAULT_COORDS[util_name], presses=3, delay=0.05, wait_timeout=2.0):
            last_use_times[util_name] = current_time
            return True
        end_brightness = get_skill_brightness(util_name)
        if end_brightness < start_brightness - 40:
            log_and_print('debug', f"Brightness drop suggests {label} landed (pre={start_brightness}, post={end_brightness})")
            last_use_times[util_name] = current_time
            return True
        return False
    elif time_since > UTILITY_FORCE_INTERVAL[util_name]:
        brightness = get_skill_brightness(util_name)
        if brightness < 25:
            log_and_print('debug', f"Skipping forced {util_name} due to low brightness ({brightness})")
            return False
        label = {
            'utility_elite': "Forest's Fortification (Force)",
            'utility_1': "Frost Trap (Force)",
            'utility_2': '"Protect Me!" (Force)',
            'utility_3': "Storm Spirit (Force)",
            'utility_heal': '"We Heal As One!" (Force)',
        }[util_name]
        log_and_print('debug', f"Forcing {label} (brightness={brightness})")
        if cast_skill(UTILITY_KEY_OPTIONS[util_name], DEFAULT_COORDS[util_name], presses=3, delay=0.05, wait_timeout=2.0):
            last_use_times[util_name] = current_time
            return True
        return False
    return False


def cast_pet_skills_if_ready(stop_event):
    """Cast any pet skills (F1-F3) that are ready."""
    for name, keys in PET_SKILL_KEYS.items():
        coords = DEFAULT_COORDS.get(name)
        if not coords:
            continue
        color = pixel_get_color(*coords)
        if color and sum(color) > SKILL_READY_PIXEL_MIN:
            log_and_print('info', f">>> PET SKILL: {name}")
            tap_keys(keys)
            time.sleep(0.15)
            wait_if_paused()
            if check_stop_condition(stop_event):
                return


def power_untamed_rotation(stop_event):
    """
    Power Untamed rotation following the metabattle guide.

    General rotation per the guide:
    1. Start with pet unleashed. Send pet attack, Unleash Ranger.
    2. Unleashed Ambush (Sundering Volley on axe, Rampant Growth on mace)
    3. Use all weapon skills
    4. Weapon swap
    5. Unleashed Ambush
    6. Use all weapon skills (mace skills reset via Nature's Strength — use them again)
    7. When weapon swap almost ready: Unleash Pet, cast pet skills, Unleash Ranger
    8. Unleashed Ambush
    9. Repeat from step 3

    It's better to start fights in the axe weapon set.
    """
    global LAST_UTILITY_TIMES

    rotation_count = 0
    last_utility_times = dict(LAST_UTILITY_TIMES)
    last_weapon_swap = 0.0
    last_set_seen = detect_weapon_set()

    log_and_print('debug', f"Starting rotation — initial weapon set: {last_set_seen.upper()}")

    # Step 1: Pet cycle — start with pet unleashed, send attack, then unleash ranger
    unleash_pet_cycle(stop_event)
    if check_stop_condition(stop_event):
        return

    # Set initial weapon set (prefer axe to start)
    current_set = detect_weapon_set()
    if current_set != 'axe':
        log_and_print('info', "Not on axe set — weapon swapping to start in axe")
        ensure_weapon_swap(current_set)
        time.sleep(0.3)
        current_set = detect_weapon_set()
        log_and_print('debug', f"Initial weapon set after swap attempt: {current_set.upper()}")

    # Step 2: Unleashed Ambush at start
    cast_unleashed_ambush(stop_event)
    if check_stop_condition(stop_event):
        return

    while not stop_event.is_set():
        rotation_count += 1
        wait_if_paused()
        if check_stop_condition(stop_event):
            log_and_print('debug', "Stop condition detected — exiting rotation")
            break

        current_time = time.time()
        current_set = detect_weapon_set()

        # --- Log status ---
        weapon_ready = {}
        for slot in ['weapon_2', 'weapon_3', 'weapon_4', 'weapon_5']:
            weapon_ready[slot] = check_skill_available(DEFAULT_COORDS[slot], threshold=None)
        utilities_ready = {}
        for name in ['utility_elite', 'utility_1', 'utility_2', 'utility_3', 'utility_heal']:
            utilities_ready[name] = check_skill_available(DEFAULT_COORDS[name], threshold=None)

        weapon_brightness = {slot: get_skill_brightness(slot) for slot in ['weapon_2', 'weapon_3', 'weapon_4', 'weapon_5']}
        utility_brightness = {name: get_skill_brightness(name) for name in ['utility_elite', 'utility_1', 'utility_2', 'utility_3', 'utility_heal']}

        log_and_print(
            'info',
            (
                f"--- LOOP {rotation_count} ---\n"
                f"Set={current_set.upper()} | WeaponReady={weapon_ready} brightness={weapon_brightness}\n"
                f"UtilitiesReady={utilities_ready} brightness={utility_brightness}\n"
                f"PetUnleashed={is_pet_unleashed()}"
            )
        )

        # --- Utilities / buffs ---
        utility_cast = False
        for util in ['utility_elite', 'utility_3', 'utility_2', 'utility_1', 'utility_heal']:
            if cast_utility_if_needed(util, current_time, last_utility_times, utilities_ready, stop_event):
                utility_cast = True
                break
            if check_stop_condition(stop_event):
                break

        if check_stop_condition(stop_event):
            break

        if utility_cast:
            continue

        # --- Weapon skills in priority order ---
        triggered = cast_weapon_skills(current_set, weapon_ready, stop_event)
        if check_stop_condition(stop_event):
            break
        if triggered:
            # Mace Nature's Strength reset: after casting priority skills,
            # give one more pass for mace skills that may have reset
            if current_set == 'mace':
                log_and_print('debug', "Mace: checking for Nature's Strength reset skills")
                time.sleep(0.2)
                mace_secondary_triggered = False
                for slot in MACE_PRIORITY:
                    if check_skill_available(DEFAULT_COORDS[slot]):
                        wait_timeout, delay = MACE_TIMEOUT_OVERRIDES.get(slot, (1.4, 0.05))
                        log_and_print('info', f">>> MACE RESET: Weapon Skill {slot[-1]}")
                        if cast_skill(WEAPON_KEY_OPTIONS[slot], DEFAULT_COORDS[slot], presses=3, delay=delay, wait_timeout=wait_timeout):
                            mace_secondary_triggered = True
                            break
                if check_stop_condition(stop_event):
                    break
            continue

        # --- Weapon swap cadence ---
        time_since_swap = current_time - last_weapon_swap
        if time_since_swap > WEAPON_SET_MIN_TIME:
            # Step 7: Before weapon swap, do pet cycle if weapon swap is almost ready
            if is_pet_unleashed():
                log_and_print('debug', "Pet is already unleashed — casting pet skills before Unleash Ranger")
                cast_pet_skills_if_ready(stop_event)
                if check_stop_condition(stop_event):
                    break
                unleash_ranger()
                time.sleep(0.25)

            if ensure_weapon_swap(current_set):
                last_weapon_swap = time.time()
                last_set_seen = detect_weapon_set()
                log_and_print('debug', f"Weapon swap complete — new set: {last_set_seen.upper()}")

                # Step 5: Unleashed Ambush after weapon swap
                time.sleep(0.25)
                cast_unleashed_ambush(stop_event)
                if check_stop_condition(stop_event):
                    break

                # Pet cycle: Unleash Pet, send attack, skills, Unleash Ranger
                pet_unleash_done = False
                if not is_pet_unleashed():
                    unleash_pet()
                    send_pet_attack()
                    cast_pet_skills_if_ready(stop_event)
                    if check_stop_condition(stop_event):
                        break
                    unleash_ranger()
                    pet_unleash_done = True
                    if check_stop_condition(stop_event):
                        break

                continue
            else:
                log_and_print('debug', "Weapon swap failed, trying again next loop")
        else:
            log_and_print('debug', f"Weapon swap not ready ({time_since_swap:.1f}s / {WEAPON_SET_MIN_TIME}s)")

        # --- Auto-attack filler ---
        if cast_skill(WEAPON_KEY_OPTIONS['weapon_1'], DEFAULT_COORDS['weapon_1'], presses=1, delay=0.02, wait_timeout=0.6):
            log_and_print('debug', "Auto-attack filler (weapon 1)")

        time.sleep(0.15)

    log_and_print('info', "Stopping Power Untamed rotation")


def run(stop_event):
    """
    Entry point for the Power Untamed spec.
    Hold NumPad1 to run the rotation; release to stop.
    """
    logger.info("Power Untamed spec started")
    log_and_print('info', "=" * 70)
    log_and_print('info', "POWER UNTAMED — AXE/AXE + MACE/MACE")
    log_and_print('info', "Hold NumPad1 to run rotation")
    log_and_print('info', "=" * 70)

    while not stop_event.is_set():
        wait_if_paused()
        if stop_event.is_set():
            break
        if keyboard.is_pressed(STOP_KEY):
            log_and_print('info', "NumPad1 pressed — starting rotation loop")
            try:
                power_untamed_rotation(stop_event)
            except Exception as exc:
                log_and_print('error', f"Unexpected error in Power Untamed rotation: {exc}")
                raise
        time.sleep(0.05)

    logger.info("Power Untamed spec ended")
