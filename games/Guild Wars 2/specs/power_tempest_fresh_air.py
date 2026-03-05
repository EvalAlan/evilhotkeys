"""
Power Tempest - Fresh Air Build for Guild Wars 2
Based on: https://metabattle.com/wiki/Build:Tempest_-_Fresh_Air

Build Overview:
- Weapons: Scepter/Warhorn (Fresh Air Tempest)
- Focus: Power burst with Overload Air spam and supplemental Fire attunement skills
- Utilities: Glyph of Elemental Harmony (heal), Signet of Fire (passive), "Feel the Burn!" (NumPad7), "Aftershock!" (NumPad8), Glyph of Elementals (NumPad9)

Rotation Snapshot (priority style):
1. Stay in Air attunement whenever Overload Air, Lightning Orb, or Cyclone are available.
2. Cast Overload Air on cooldown (channel fully for damage, boons, and Fresh Air resets).
3. Use Lightning Orb (Warhorn 4), Cyclone (Warhorn 5), Lightning Strike (Scepter 2), and Blinding Flash (Scepter 3) whenever ready.
4. Dip into Fire attunement to cast Dragon's Tooth (Scepter 2), Phoenix (Scepter 3), Heat Sync (Warhorn 4), and Wildfire (Warhorn 5), then immediately return to Air.
5. Use "Feel the Burn!" off cooldown for Might and damage, "Aftershock!" for CC/reflects, and Glyph of Elementals whenever ready.

Keybind Expectations (matches amalgam rifle layout):
- NumPad1-5: Weapon skills (Scepter/Warhorn)
- NumPad6-9: Heal/Utilities (NumPad6=Heal, NumPad7=Feel the Burn, NumPad8=Aftershock, NumPad9=Glyph of Elementals)
- Keys 1-4: Fire, Water, Air, Earth attunements
- Hold NumPad1 to keep the rotation running (stop condition)
"""

import sys
import time
import keyboard
from libs.pixel_get_color import get_color as pixel_get_color
from libs.keyboard_actions_monitored import button_mash
from libs.key_mapping import key_mapping
from libs.logger import get_logger
from libs.pause import wait_if_paused

logger = get_logger('power_tempest_fresh_air')
logger.propagate = True

# Enable/disable detailed logging
ENABLE_DETAILED_LOGGING = False

def log_and_print(level, msg):
    """Log and also print to ensure visibility"""
    getattr(logger, level)(msg)
    if ENABLE_DETAILED_LOGGING:
        print(f"[{level.upper()}] {msg}", flush=True)
        sys.stdout.flush()

# Coordinates for skill availability detection (matching amalgam rifle layout)
DEFAULT_COORDS = {
    # Weapon skills (bottom bar, numpad1-5)
    'weapon_1': (2587, 1013),  # Auto-attack slot (Arc Lightning / Flame Burst)
    'weapon_2': (2625, 1013),  # Scepter skill 2 (Lightning Strike / Dragon's Tooth, etc.)
    'weapon_3': (2686, 1013),  # Scepter skill 3 (Blinding Flash / Phoenix, etc.)
    'weapon_4': (2743, 1013),  # Warhorn skill 4 (Lightning Orb / Heat Sync)
    'weapon_5': (2801, 1013),  # Warhorn skill 5 (Cyclone / Wildfire / Overload)

    # Utility skills (numpad6-0)
    'utility_heal': (2652, 1013),    # NumPad6 - Glyph of Elemental Harmony
    'utility_1': (3007, 1013),       # NumPad7 - "Feel the Burn!"
    'utility_2': (3070, 1013),       # NumPad8 - "Aftershock!"
    'utility_3': (3116, 1013),       # NumPad9 - (unused / optional)
    'utility_elite': (3171, 1013),   # NumPad0 - Glyph of Elementals
}

# Attunement icon positions (lit when attunement is active)
ATTUNEMENT_COORDS = {
    'fire': (2577, 983),
    'water': (2623, 983),
    'air': (2656, 983),
    'earth': (2691, 983),
}

# Attunement key mapping (user binds attunements to number keys 1-4)
ATTUNEMENT_KEYS = {
    'fire': '1',
    'water': '2',
    'air': '3',
    'earth': '4',
}

# Timing constants
ATTUNEMENT_SWAP_DELAY = 0.35
OVERLOAD_AIR_CHANNEL_TIME = 4.2
LIGHTNING_ORB_CAST_TIME = 0.4
CYCLONE_CAST_TIME = 0.6
LIGHTNING_STRIKE_CAST_TIME = 0.2
BLINDING_FLASH_CAST_TIME = 0.2
FIRE_SKILL_CAST_TIME = 0.45
GLYPH_ELEMENTALS_CAST_TIME = 0.6
AIR_OVERLOAD_COOLDOWN = 10.0       # Seconds between Overload casts
AIR_OVERLOAD_MIN_AIR_TIME = 3.0    # Minimum time to sit in Air before overloading
ATTUNEMENT_ACTIVE_THRESHOLD = 70   # Pixel brightness threshold to consider attunement active
ATTUNEMENT_BRIGHTNESS_TOLERANCE = 100  # Allow differences when judging active attunement
ATTUNEMENT_BRIGHTNESS_DELTA = 40       # Required increase vs previous brightness to confirm swap
ATTUNEMENT_MIN_SIGNAL = 45             # Minimal brightness to keep previous attunement assumption
WATER_CYCLE_INTERVAL = 18.0           # Seconds between water dips
WATER_SKILL_COOLDOWN = 6.0            # Minimum spacing between water skills
GLYPH_FORCE_INTERVAL = 90.0           # Force Glyph usage if it hasn't fired in this many seconds

def check_stop_condition(stop_event):
    """Check if we should stop the rotation"""
    return not keyboard.is_pressed(key_mapping['numpad1']) or stop_event.is_set()

def check_skill_available(coords):
    """Check if a skill is available (not on cooldown)"""
    color = pixel_get_color(coords[0], coords[1])
    return color is not None and color != (0, 0, 0) and sum(color) > 200

def wait_until_on_cooldown(coords, timeout_seconds: float = 2.0, poll_seconds: float = 0.05) -> bool:
    """Wait until the given skill pixel turns dark (goes on cooldown)."""
    initial_color = pixel_get_color(coords[0], coords[1])
    initial_sum = sum(initial_color) if initial_color else 0
    start = time.time()

    while (time.time() - start) < timeout_seconds:
        color = pixel_get_color(coords[0], coords[1])
        if color is None:
            return True
        current_sum = sum(color)

        # Skill is on cooldown if completely black or below threshold
        if color == (0, 0, 0) or current_sum <= 300:
            return True

        time.sleep(poll_seconds)

    return False

def get_attunement_color(attunement: str):
    coords = ATTUNEMENT_COORDS.get(attunement)
    if not coords:
        return None
    return pixel_get_color(coords[0], coords[1])


def get_attunement_brightness() -> dict[str, int]:
    """Return brightness (sum of RGB) for each attunement icon."""
    brightness = {}
    for attunement, (x, y) in ATTUNEMENT_COORDS.items():
        color = pixel_get_color(x, y)
        brightness[attunement] = sum(color) if color else 0
    return brightness


def detect_current_attunement(previous: str | None = None) -> tuple[str | None, dict[str, int]]:
    """Infer current attunement by picking the brightest icon."""
    brightness = get_attunement_brightness()
    if not brightness:
        return None, {}

    max_attunement = max(brightness, key=brightness.get)
    max_value = brightness[max_attunement]

    if max_value < ATTUNEMENT_ACTIVE_THRESHOLD:
        if previous and brightness.get(previous, 0) >= ATTUNEMENT_MIN_SIGNAL:
            return previous, brightness
        if max_value >= ATTUNEMENT_MIN_SIGNAL:
            return max_attunement, brightness
        return None, brightness

    candidates = [
        att for att, value in brightness.items()
        if max_value - value <= ATTUNEMENT_BRIGHTNESS_TOLERANCE and value >= ATTUNEMENT_ACTIVE_THRESHOLD
    ]

    if not candidates and max_value >= ATTUNEMENT_MIN_SIGNAL:
        return max_attunement, brightness

    if previous and previous in candidates:
        return previous, brightness

    return max_attunement, brightness

def power_tempest_rotation(stop_event, force_fire_on_start: bool = False):
    """
    Main rotation for Power Tempest (Fresh Air)
    Priority highlights (simplified):
    - Stay in Air when something meaningful is available (Overload, Lightning Orb, Cyclone, Lightning Strike, Blinding Flash).
    - Do short Fire dips (Dragon's Tooth, Phoenix, Heat Sync, Wildfire) when Air bar is empty, then instantly return to Air.
    - Maintain utility usage per guide.
    """
    rotation_count = 0
    current_attunement = None
    last_attunement_swap = 0.0
    attunement_last_used = {
        'fire': -999.0,
        'water': -999.0,
        'air': -999.0,
        'earth': -999.0,
    }
    attunement_enter_time = {
        'fire': -999.0,
        'water': -999.0,
        'air': -999.0,
        'earth': -999.0,
    }
    # Approximate recharge windows (seconds). Fresh Air resets Air quickly, so keep minimal gate.
    ATTUNEMENT_RECHARGE = {
        'fire': 10.0,
        'water': 10.0,
        'air': 0.75,
        'earth': 10.0,
    }

    detected, brightness_snapshot = detect_current_attunement()
    if detected:
        current_attunement = detected
        attunement_enter_time[detected] = time.time()
        log_and_print('info', f"Detected starting attunement: {detected.upper()} (brightness={brightness_snapshot})")
    else:
        log_and_print('warning', f"Unable to detect starting attunement (brightness={brightness_snapshot})")

    # Track last use times to avoid spamming
    last_overload_air = 0.0
    last_lightning_orb = 0.0
    last_cyclone = 0.0
    last_lightning_strike = 0.0
    last_blinding_flash = 0.0

    last_fire_cycle = 0.0
    last_dragon_tooth = 0.0
    last_phoenix = 0.0
    last_heat_sync = 0.0
    last_wildfire = 0.0

    last_feel_burn = 0.0
    last_aftershock = 0.0
    last_glyph_elementals = 0.0
    last_water_cycle = 0.0
    last_tidal_surge = 0.0
    last_water_trident = 0.0
    last_water_globe = 0.0

    def ensure_attunement(target: str) -> bool:
        nonlocal current_attunement, last_attunement_swap, attunement_last_used, attunement_enter_time
        if current_attunement == target:
            return True

        key = ATTUNEMENT_KEYS.get(target)
        if not key:
            log_and_print('error', f"Unknown attunement requested: {target}")
            return False

        now = time.time()
        # Respect approximate recharge so we aren't spamming keys while still locked
        attunement_cd = ATTUNEMENT_RECHARGE.get(target, 4.0)
        time_since_target = now - attunement_last_used.get(target, -999.0)
        if time_since_target < attunement_cd:
            remaining = attunement_cd - time_since_target
            log_and_print('debug', f"{target.title()} attunement still recharging ({remaining:.2f}s left)")
            return False

        log_and_print('info', f"Switching attunement -> {target.upper()}")
        # Record the attunement we are leaving to enforce its cooldown window
        previous_attunement = current_attunement
        previous_last_used = attunement_last_used.get(previous_attunement) if previous_attunement else None
        previous_enter = attunement_enter_time.get(previous_attunement) if previous_attunement else None
        if previous_attunement:
            attunement_last_used[previous_attunement] = now
            attunement_enter_time[previous_attunement] = -999.0

        # Capture brightness before we press the key (baseline for delta comparisons)
        previous_brightness = get_attunement_brightness()

        # Press and release the attunement key twice for reliability
        keyboard.press(key)
        time.sleep(0.05)
        keyboard.release(key)
        time.sleep(0.05)
        keyboard.press(key)
        time.sleep(0.05)
        keyboard.release(key)

        swap_deadline = time.time() + 1.5  # give UI time to update
        while time.time() < swap_deadline:
            time.sleep(ATTUNEMENT_SWAP_DELAY)
            detected, brightness = detect_current_attunement(current_attunement)
            target_brightness = brightness.get(target, 0)
            max_brightness = max(brightness.values()) if brightness else 0
            previous_target_brightness = previous_brightness.get(target, 0)
            brightness_increase = target_brightness - previous_target_brightness
            within_tolerance = target_brightness >= max_brightness - ATTUNEMENT_BRIGHTNESS_TOLERANCE
            above_threshold = target_brightness >= ATTUNEMENT_ACTIVE_THRESHOLD

            if detected == target or (
                above_threshold and (within_tolerance or brightness_increase >= ATTUNEMENT_BRIGHTNESS_DELTA)
            ):
                last_attunement_swap = time.time()
                attunement_last_used[target] = last_attunement_swap
                attunement_enter_time[target] = last_attunement_swap
                current_attunement = target
                log_and_print('debug', f"Confirmed attunement swap -> {target.upper()} (brightness={brightness})")
                return True

        brightness = get_attunement_brightness()
        log_and_print(
            'warning',
            (
                f"Failed to confirm attunement swap to {target.upper()} (icon stayed dark) | "
                f"brightness={brightness}"
            )
        )
        # Revert timers because swap did not complete
        if previous_attunement:
            if previous_last_used is not None:
                attunement_last_used[previous_attunement] = previous_last_used
            if previous_enter is not None:
                attunement_enter_time[previous_attunement] = previous_enter
        current_attunement = previous_attunement
        return False

    def perform_water_cycle(current_time: float) -> bool:
        """Execute a short Water dip for utility/CC before returning to Air."""
        nonlocal last_water_cycle, last_tidal_surge, last_water_trident, last_water_globe

        if (current_time - last_water_cycle) < WATER_CYCLE_INTERVAL:
            return False

        if not ensure_attunement('water'):
            log_and_print('debug', "Water attunement not ready - delaying water burst")
            return False

        log_and_print('info', ">>> WATER BURST: Tidal Surge -> Water Globe -> Water Trident")
        time.sleep(0.15)

        fired_any = False

        if check_skill_available(DEFAULT_COORDS['weapon_4']) and (time.time() - last_tidal_surge) > WATER_SKILL_COOLDOWN:
            log_and_print('info', "Casting Tidal Surge (Warhorn 4 - NumPad4)")
            button_mash(key_mapping['numpad4'], presses=3, delay=0.05)
            last_tidal_surge = time.time()
            fired_any = True
            time.sleep(0.45)
            wait_until_on_cooldown(DEFAULT_COORDS['weapon_4'], timeout_seconds=1.5)
            if check_stop_condition(stop_event):
                return True

        if check_skill_available(DEFAULT_COORDS['weapon_5']) and (time.time() - last_water_globe) > WATER_SKILL_COOLDOWN:
            log_and_print('info', "Casting Water Globe (Warhorn 5 - NumPad5)")
            button_mash(key_mapping['numpad5'], presses=3, delay=0.05)
            last_water_globe = time.time()
            fired_any = True
            time.sleep(0.45)
            wait_until_on_cooldown(DEFAULT_COORDS['weapon_5'], timeout_seconds=1.5)
            if check_stop_condition(stop_event):
                return True

        if check_skill_available(DEFAULT_COORDS['weapon_2']) and (time.time() - last_water_trident) > WATER_SKILL_COOLDOWN:
            log_and_print('info', "Casting Water Trident (Scepter 2 - NumPad2)")
            button_mash(key_mapping['numpad2'], presses=3, delay=0.05)
            last_water_trident = time.time()
            fired_any = True
            time.sleep(0.35)
            wait_until_on_cooldown(DEFAULT_COORDS['weapon_2'], timeout_seconds=1.5)
            if check_stop_condition(stop_event):
                return True

        if fired_any:
            last_water_cycle = time.time()

        for _ in range(4):
            if ensure_attunement('air'):
                break
            time.sleep(0.1)

        return fired_any

    def perform_fire_cycle(current_time: float) -> bool:
        """Execute a short Fire burst and return to Air."""
        nonlocal last_fire_cycle, last_dragon_tooth, last_phoenix, last_heat_sync, last_wildfire

        if (current_time - last_fire_cycle) < 6.0:
            return False

        if not ensure_attunement('fire'):
            log_and_print('debug', "Fire attunement not ready - delaying fire burst")
            return False

        log_and_print('info', ">>> FIRE BURST: Dragon's Tooth -> Phoenix -> Heat Sync -> Wildfire")
        time.sleep(0.2)

        fired_any = False

        if check_skill_available(DEFAULT_COORDS['weapon_2']) and (current_time - last_dragon_tooth) > 4.0:
            log_and_print('info', "Casting Dragon's Tooth (NumPad2)")
            button_mash(key_mapping['numpad2'], presses=3, delay=0.05)
            last_dragon_tooth = time.time()
            fired_any = True
            time.sleep(FIRE_SKILL_CAST_TIME)
            wait_until_on_cooldown(DEFAULT_COORDS['weapon_2'], timeout_seconds=1.5)
            if check_stop_condition(stop_event): 
                return True

        if check_skill_available(DEFAULT_COORDS['weapon_3']) and (time.time() - last_phoenix) > 4.0:
            log_and_print('info', "Casting Phoenix (NumPad3)")
            button_mash(key_mapping['numpad3'], presses=3, delay=0.05)
            last_phoenix = time.time()
            fired_any = True
            time.sleep(FIRE_SKILL_CAST_TIME)
            wait_until_on_cooldown(DEFAULT_COORDS['weapon_3'], timeout_seconds=1.5)
            if check_stop_condition(stop_event): 
                return True

        if check_skill_available(DEFAULT_COORDS['weapon_4']) and (time.time() - last_heat_sync) > 12.0:
            log_and_print('info', "Casting Heat Sync (Warhorn 4 - NumPad4) for Might copy")
            button_mash(key_mapping['numpad4'], presses=3, delay=0.05)
            last_heat_sync = time.time()
            fired_any = True
            time.sleep(FIRE_SKILL_CAST_TIME)
            wait_until_on_cooldown(DEFAULT_COORDS['weapon_4'], timeout_seconds=1.5)
            if check_stop_condition(stop_event): 
                return True

        if check_skill_available(DEFAULT_COORDS['weapon_5']) and (time.time() - last_wildfire) > 12.0:
            log_and_print('info', "Casting Wildfire (Warhorn 5 - NumPad5)")
            button_mash(key_mapping['numpad5'], presses=3, delay=0.05)
            last_wildfire = time.time()
            fired_any = True
            time.sleep(FIRE_SKILL_CAST_TIME)
            wait_until_on_cooldown(DEFAULT_COORDS['weapon_5'], timeout_seconds=1.5)
            if check_stop_condition(stop_event): 
                return True

        if fired_any:
            last_fire_cycle = time.time()

        # Return to Air (retry a few times in case attunement still recharging)
        for _ in range(4):
            if ensure_attunement('air'):
                break
            time.sleep(0.15)
        return fired_any

    initial_fire_attempted = not force_fire_on_start

    while not stop_event.is_set():
        rotation_count += 1
        current_time = time.time()

        wait_if_paused()
        if check_stop_condition(stop_event):
            break

        detected_attunement, brightness_snapshot = detect_current_attunement(current_attunement)
        if detected_attunement and detected_attunement != current_attunement:
            log_and_print('debug', f"Detected attunement change: {detected_attunement.upper()} (brightness={brightness_snapshot})")
            if current_attunement:
                attunement_last_used[current_attunement] = current_time
                attunement_enter_time[current_attunement] = -999.0
            current_attunement = detected_attunement
            attunement_enter_time[current_attunement] = current_time

        if not initial_fire_attempted:
            initial_fire_attempted = True
            if current_attunement != 'fire':
                log_and_print('info', "Initial check: not in FIRE, attempting to swap at rotation start")
                if ensure_attunement('fire'):
                    current_attunement = 'fire'
                else:
                    log_and_print('debug', "Initial fire swap attempt failed or delayed; continuing with current attunement")
                    # reset attempt flag to retry next loop only if still not fire but no swap attempted
                    if current_attunement != 'fire':
                        initial_fire_attempted = False

        # Skill availability checks (re-used across attunements)
        weapon2_ready = check_skill_available(DEFAULT_COORDS['weapon_2'])
        weapon3_ready = check_skill_available(DEFAULT_COORDS['weapon_3'])
        weapon4_ready = check_skill_available(DEFAULT_COORDS['weapon_4'])
        weapon5_ready = check_skill_available(DEFAULT_COORDS['weapon_5'])

        feel_burn_color = pixel_get_color(*DEFAULT_COORDS['utility_1'])
        feel_burn_brightness = sum(feel_burn_color) if feel_burn_color else 0
        aftershock_color = pixel_get_color(*DEFAULT_COORDS['utility_2'])
        aftershock_brightness = sum(aftershock_color) if aftershock_color else 0
        glyph_elementals_color = pixel_get_color(*DEFAULT_COORDS['utility_elite'])
        glyph_elementals_brightness = sum(glyph_elementals_color) if glyph_elementals_color else 0

        feel_burn_ready = feel_burn_brightness > 120
        aftershock_ready = aftershock_brightness > 150
        glyph_elementals_ready = glyph_elementals_brightness > 150

        time_since_overload = current_time - last_overload_air if last_overload_air > 0 else 999.0
        time_since_orb = current_time - last_lightning_orb if last_lightning_orb > 0 else 999.0
        time_since_cyclone = current_time - last_cyclone if last_cyclone > 0 else 999.0
        time_since_strike = current_time - last_lightning_strike if last_lightning_strike > 0 else 999.0
        time_since_flash = current_time - last_blinding_flash if last_blinding_flash > 0 else 999.0
        time_since_fire = current_time - last_fire_cycle if last_fire_cycle > 0 else 999.0
        time_since_feel_burn = current_time - last_feel_burn if last_feel_burn > 0 else 999.0
        time_since_aftershock = current_time - last_aftershock if last_aftershock > 0 else 999.0
        time_since_glyph_elementals = current_time - last_glyph_elementals if last_glyph_elementals > 0 else 999.0
        time_in_air = current_time - attunement_enter_time['air'] if attunement_enter_time['air'] > 0 else 999.0
        air_overload_ready = (
            current_attunement == 'air'
            and (current_time - last_overload_air) > AIR_OVERLOAD_COOLDOWN
            and time_in_air > AIR_OVERLOAD_MIN_AIR_TIME
        )

        log_and_print(
            'info',
            (
                f"--- LOOP {rotation_count} ---\n"
                f"Attunement={current_attunement or 'UNKNOWN'} | OverloadReady={air_overload_ready} "
                f"| Orb={weapon4_ready} | Cyclone={weapon5_ready} | Strike={weapon2_ready} | Flash={weapon3_ready}\n"
                f"Utilities -> FeelTheBurn={feel_burn_ready}({feel_burn_brightness}) "
                f"Aftershock={aftershock_ready}({aftershock_brightness}) "
                f"GlyphElementals={glyph_elementals_ready}({glyph_elementals_brightness})\n"
                f"Timers -> Overload={time_since_overload:.1f}s Orb={time_since_orb:.1f}s Cyclone={time_since_cyclone:.1f}s "
                f"Strike={time_since_strike:.1f}s FireCycle={time_since_fire:.1f}s"
            )
        )

        # Utilities first (per guide, Signet of Fire is passive so we skip it)
        if feel_burn_ready and time_since_feel_burn > 12.0:
            log_and_print('info', '>>> PRIORITY: "Feel the Burn!" (NumPad7)')
            button_mash(key_mapping['numpad7'], presses=3, delay=0.05)
            last_feel_burn = time.time()
            time.sleep(0.4)
            wait_until_on_cooldown(DEFAULT_COORDS['utility_1'], timeout_seconds=1.5)
            if check_stop_condition(stop_event):
                break
            continue
        elif time_since_feel_burn > 18.0:
            log_and_print('debug', f'Forcing "Feel the Burn!" cast (brightness={feel_burn_brightness})')
            button_mash(key_mapping['numpad7'], presses=3, delay=0.05)
            last_feel_burn = time.time()
            time.sleep(0.4)
            wait_until_on_cooldown(DEFAULT_COORDS['utility_1'], timeout_seconds=1.5)
            if check_stop_condition(stop_event):
                break
            continue

        if aftershock_ready and time_since_aftershock > 20.0:
            log_and_print('info', '>>> PRIORITY: "Aftershock!" (NumPad9)')
            button_mash(key_mapping['numpad8'], presses=3, delay=0.05)
            last_aftershock = time.time()
            time.sleep(0.5)
            wait_until_on_cooldown(DEFAULT_COORDS['utility_2'], timeout_seconds=1.5)
            if check_stop_condition(stop_event):
                break
            continue
        elif time_since_aftershock > 28.0:
            log_and_print('debug', f'Forcing "Aftershock!" cast (brightness={aftershock_brightness})')
            button_mash(key_mapping['numpad8'], presses=3, delay=0.05)
            last_aftershock = time.time()
            time.sleep(0.5)
            wait_until_on_cooldown(DEFAULT_COORDS['utility_2'], timeout_seconds=1.5)
            if check_stop_condition(stop_event):
                break
            continue

        if glyph_elementals_ready and time_since_glyph_elementals > 60.0:
            log_and_print('info', ">>> PRIORITY: Glyph of Elementals (NumPad0)")
            button_mash(key_mapping['numpad0'], presses=3, delay=0.05)
            last_glyph_elementals = time.time()
            time.sleep(GLYPH_ELEMENTALS_CAST_TIME)
            wait_until_on_cooldown(DEFAULT_COORDS['utility_elite'], timeout_seconds=2.5)
            if check_stop_condition(stop_event):
                break
            continue
        elif time_since_glyph_elementals > GLYPH_FORCE_INTERVAL:
            log_and_print('debug', f'Forcing Glyph of Elementals cast (brightness={glyph_elementals_brightness})')
            button_mash(key_mapping['numpad0'], presses=3, delay=0.05)
            last_glyph_elementals = time.time()
            time.sleep(GLYPH_ELEMENTALS_CAST_TIME)
            wait_until_on_cooldown(DEFAULT_COORDS['utility_elite'], timeout_seconds=2.5)
            if check_stop_condition(stop_event):
                break
            continue

        # Air priorities
        if ensure_attunement('air'):
            if air_overload_ready:
                log_and_print('info', ">>> PRIORITY: Overload Air (attunement key)")
                keyboard.press(ATTUNEMENT_KEYS['air'])
                time.sleep(0.1)
                keyboard.release(ATTUNEMENT_KEYS['air'])
                time.sleep(OVERLOAD_AIR_CHANNEL_TIME)
                last_overload_air = time.time()
                attunement_last_used['air'] = last_overload_air
                attunement_enter_time['air'] = last_overload_air
                if check_stop_condition(stop_event):
                    break
                continue

            if weapon4_ready and time_since_orb > 5.0:
                log_and_print('info', ">>> PRIORITY: Lightning Orb (Warhorn 4 - NumPad4)")
                button_mash(key_mapping['numpad4'], presses=3, delay=0.05)
                last_lightning_orb = time.time()
                time.sleep(LIGHTNING_ORB_CAST_TIME)
                wait_until_on_cooldown(DEFAULT_COORDS['weapon_4'], timeout_seconds=1.5)
                if check_stop_condition(stop_event):
                    break
                continue

            if weapon5_ready and time_since_cyclone > 8.0:
                log_and_print('info', ">>> PRIORITY: Cyclone (Warhorn 5 - NumPad5)")
                button_mash(key_mapping['numpad5'], presses=3, delay=0.05)
                last_cyclone = time.time()
                time.sleep(CYCLONE_CAST_TIME)
                wait_until_on_cooldown(DEFAULT_COORDS['weapon_5'], timeout_seconds=1.5)
                if check_stop_condition(stop_event):
                    break
                continue

            if weapon2_ready and time_since_strike > 2.0:
                log_and_print('info', ">>> PRIORITY: Lightning Strike (Scepter 2 - NumPad2)")
                button_mash(key_mapping['numpad2'], presses=3, delay=0.05)
                last_lightning_strike = time.time()
                time.sleep(LIGHTNING_STRIKE_CAST_TIME)
                wait_until_on_cooldown(DEFAULT_COORDS['weapon_2'], timeout_seconds=1.5)
                if check_stop_condition(stop_event):
                    break
                continue

            if weapon3_ready and time_since_flash > 2.0:
                log_and_print('info', ">>> PRIORITY: Blinding Flash (Scepter 3 - NumPad3)")
                button_mash(key_mapping['numpad3'], presses=3, delay=0.05)
                last_blinding_flash = time.time()
                time.sleep(BLINDING_FLASH_CAST_TIME)
                wait_until_on_cooldown(DEFAULT_COORDS['weapon_3'], timeout_seconds=1.5)
                if check_stop_condition(stop_event):
                    break
                continue

        # If Air bar is dry, execute Fire burst to recharge Fresh Air
        if perform_water_cycle(current_time):
            continue

        if perform_fire_cycle(current_time):
            continue

        # Otherwise idle briefly (auto-attack)
        log_and_print('debug', "No higher priority skill ready - letting auto-attack tick")
        time.sleep(0.2)

    log_and_print('info', "Stopping Power Tempest rotation")

def run(stop_event):
    """
    Entry point for the spec.
    Hold NumPad1 to run the rotation (same convention as other specs).
    """
    logger.info("Power Tempest (Fresh Air) spec started")
    log_and_print('info', "=" * 70)
    log_and_print('info', "POWER TEMPEST - FRESH AIR BUILD")
    log_and_print('info', "Hold NumPad1 to run rotation")
    log_and_print('info', "=" * 70)

    last_rotation_start = 0.0

    while not stop_event.is_set():
        if stop_event.is_set():
            break

        if keyboard.is_pressed(key_mapping['numpad1']):
            log_and_print('info', "NumPad1 pressed - starting rotation loop")
            rotation_start = time.time()
            force_fire_on_start = (rotation_start - last_rotation_start) > 10.0
            last_rotation_start = rotation_start
            try:
                power_tempest_rotation(stop_event, force_fire_on_start=force_fire_on_start)
            except Exception as exc:
                log_and_print('error', f"Unexpected error in Power Tempest rotation: {exc}")
                raise

        time.sleep(0.05)

    logger.info("Power Tempest spec ended")

