"""
Power Amalgam Rifle (WvW) - WvW Build for Guild Wars 2
Based on: https://metabattle.com/wiki/Build:Amalgam_-_DPS_Amalgam

Build Overview:
- Weapon: Rifle
- Utilities: Elixir Gun Kit, Flamethrower Kit
- Rotation: Napalm > Acid Bomb > Morph skills > Filler (per Metabattle priority)
- Focus: High burst damage with multiple burst combos

Burst Priority (per Metabattle):
1. Napalm burst: Plasmatic State → Napalm
2. Acid Bomb burst: Jump Shot → Acid Bomb
3. Morph skills burst: Thorns → Obliterate → Demolish → Evolve → repeat
4. Filler burst: Flame Blast → Blunderbuss

Ideal Combined Burst (when multiple are ready):
Plasmatic State → Napalm → Jump Shot → Acid Bomb → Thorns → Obliterate → Demolish → Evolve → Obliterate → Demolish → Flame Blast → Blunderbuss

Your Keybinds:
Toolbelt (F1-F5): keys 1-5
  1 - Static Shock (or other F1 morph)
  2 - Offensive Protocol: Demolish (F2 morph)
  3 - Defensive Protocol: Thorns
  4 - Offensive Protocol: Obliterate
  5 - Evolve

Weapon Skills (Rifle): numpad1-5
  NumPad1 - Aimed Shot (auto)
  NumPad2 - Blunderbuss (skill 2)
  NumPad4 - (unused or other skill)
  NumPad5 - Jump Shot (skill 5)

Utilities: numpad6-0
  NumPad6 - Heal skill
  NumPad7 - Elixir Gun Kit (skill 4 = Acid Bomb)
  NumPad8 - Flamethrower Kit (skill 2 = Flame Blast, skill 5 = Napalm)
  NumPad9 - Plasmatic State (Utility 3)
  NumPad0 - Elite skill
"""

import time
import keyboard
from libs.pixel_get_color import get_color as pixel_get_color
from libs.keyboard_actions_monitored import press_and_release, button_mash
from libs.key_mapping import key_mapping
from libs.logger import get_logger
import sys

logger = get_logger('power_amalgam_rifle')
logger.propagate = True

# Enable/disable detailed logging (set to False to reduce log spam)
ENABLE_DETAILED_LOGGING = False

def log_and_print(level, msg):
    """Log and also print to ensure visibility"""
    getattr(logger, level)(msg)
    if ENABLE_DETAILED_LOGGING:
        print(f"[{level.upper()}] {msg}", flush=True)
        sys.stdout.flush()

# Coordinates for skill availability detection
DEFAULT_COORDS = {
    # Toolbelt skills (top bar, keys 1-5)
    'toolbelt_1': (2607, 950),  # 1 - Static Shock
    'toolbelt_2': (2645, 950),  # 2 - Offensive Protocol: Demolish
    'toolbelt_3': (2693, 950),  # 3 - Defensive Protocol: Thorns
    'toolbelt_4': (2739, 950),  # 4 - Offensive Protocol: Obliterate
    'toolbelt_5': (2787, 950),  # 5 - Evolve
    
    # Weapon/Kit skills (bottom bar, numpad)
    'weapon_2': (2625, 1013),  # Blunderbuss (Rifle 2) or Flame Blast (Flamethrower 2)
    'weapon_4': (2743, 1013),  # (Rifle 4 - unused) or Acid Bomb (Elixir Gun 4)
    'weapon_5': (2801, 1013),  # Jump Shot (Rifle 5) or Napalm (Flamethrower 5)
    
    # Utility skills (numpad6-0)
    'utility_heal': (2652, 1013),    # NumPad6 - Heal
    'utility_elixir': (3007, 1013),  # NumPad7 - Elixir Gun Kit
    'utility_flamethrower': (3070, 1034),  # NumPad8 - Flamethrower Kit
    'utility_3': (3116, 1013),       # NumPad9 - Plasmatic State
    'utility_elite': (3171, 1013),   # NumPad0 - Elite
}

# Debounce for kit toggles
DEBOUNCE_WINDOW_SECONDS = 0.6
last_kit_toggle_time = 0.0
kit_switch_in_progress = False

def just_toggled_recently() -> bool:
    """Return True if a kit toggle happened within the debounce window."""
    return (time.time() - last_kit_toggle_time) < DEBOUNCE_WINDOW_SECONDS

def check_stop_condition(stop_event):
    """Check if we should stop the rotation"""
    return not keyboard.is_pressed(key_mapping['numpad1']) or stop_event.is_set()

def check_skill_available(coords):
    """Check if a skill is available (not on cooldown)"""
    color = pixel_get_color(coords[0], coords[1])
    return color is not None and color != (0, 0, 0) and sum(color) > 300

def check_skill_available_multipoint(coords, offsets=[(0, 0), (-2, -2), (2, -2), (0, -5)], invert_logic=False):
    """Check if a skill is available by checking multiple points on the icon
    For some skills (like Napalm), ready state is indicated by BLACK pixel,
    while on cooldown shows colored/grayscale overlay"""
    for offset in offsets:
        x, y = coords[0] + offset[0], coords[1] + offset[1]
        color = pixel_get_color(x, y)
        if color is None:
            continue
        
        if invert_logic:
            # For Napalm: NOT black = ready, black = on cooldown
            # Check if it's NOT black (bright/colored means ready)
            if color != (0, 0, 0) and sum(color) > 100:
                return True, color, (x, y)
        else:
            # Traditional method: bright = ready, dark = on cooldown
            if sum(color) > 300:
                return True, color, (x, y)
    
    # If none of the points match, it's likely on cooldown
    center_color = pixel_get_color(coords[0], coords[1])
    return False, center_color, coords

def wait_until_on_cooldown(coords, timeout_seconds: float = 2.0, poll_seconds: float = 0.05) -> bool:
    """Wait until the given skill pixel turns dark (goes on cooldown).
    Returns True if skill went on cooldown, False if timeout.
    If skill gets brighter, it likely didn't fire - will return False after timeout.
    """
    initial_color = pixel_get_color(coords[0], coords[1])
    initial_sum = sum(initial_color) if initial_color else 0
    start = time.time()
    brightest_sum = initial_sum  # Track if it gets brighter (didn't fire)
    
    # For toolbelt skills, they might dim slightly or go dark
    # Check multiple conditions with varying strictness based on initial brightness
    while (time.time() - start) < timeout_seconds:
        color = pixel_get_color(coords[0], coords[1])
        if color is None:
            return True
        current_sum = sum(color)
        dim_amount = initial_sum - current_sum
        dim_percentage = (dim_amount / initial_sum) if initial_sum > 0 else 0
        
        # Track if skill got brighter (didn't fire)
        if current_sum > brightest_sum:
            brightest_sum = current_sum
        
        # Skill is on cooldown if:
        # 1. Completely black
        # 2. Below absolute threshold (300)
        if color == (0, 0, 0) or current_sum <= 300:
            return True
        
        # For bright toolbelt skills (initial_sum > 400), even small dimming can indicate cooldown
        # Accept if: dimmed by 5% OR dimmed by 10+ points OR dropped below 98% of initial
        if initial_sum > 400:
            if dim_percentage >= 0.05 or dim_amount >= 10 or current_sum < (initial_sum * 0.98):
                return True
        
        # For moderately bright skills (350-400), check for 10% dimming or below 350
        elif initial_sum > 350:
            if dim_percentage >= 0.10 or current_sum < 350:
                return True
        
        # For darker skills, check for 15% dimming
        else:
            if dim_percentage >= 0.15:
                return True
        
        time.sleep(poll_seconds)
    
    # Timeout - check final state for logging
    final_color = pixel_get_color(coords[0], coords[1])
    final_sum = sum(final_color) if final_color else 0
    dim_percentage = ((initial_sum - final_sum) / initial_sum * 100) if initial_sum > 0 else 0
    # If skill got brighter, it definitely didn't fire
    if brightest_sum > initial_sum:
        log_and_print('info', f"wait_until_on_cooldown timeout - skill got BRIGHTER (didn't fire): initial_sum={initial_sum}, brightest={brightest_sum}, final_sum={final_sum}, coords={coords}")
    else:
        log_and_print('info', f"wait_until_on_cooldown timeout: initial_sum={initial_sum}, final_sum={final_sum}, dim={dim_percentage:.1f}%, coords={coords}")
    return False

def is_kit_equipped(kit_coords):
    """Check if a kit is equipped by looking for white color"""
    color = pixel_get_color(kit_coords[0], kit_coords[1])
    if color is None:
        return False
    return color[0] > 200 and color[1] > 200 and color[2] > 200

def try_flux_state(stop_event):
    """
    Try to use Flux State (NumPad0 - Elite) at the start of bursts if available.
    Can be added onto any burst, preferably at the start per guide.
    Returns True if used, False if not available.
    Flux State uses INVERTED logic: NOT black = ready, black = on cooldown
    """
    # Use multipoint check with inverted logic (same as Napalm)
    # Flux State is on NumPad0 (elite utility slot)
    flux_ready, color, checked_coords = check_skill_available_multipoint(DEFAULT_COORDS['utility_elite'], invert_logic=True)
    log_and_print('info', f"Flux State ready check: {flux_ready}, color at {checked_coords}: {color}, sum: {sum(color) if color else 0}")
    if flux_ready:
        log_and_print('info', ">>> Using Flux State (NumPad0) - Pull")
        button_mash(key_mapping['numpad0'], presses=2, delay=0.05)
        time.sleep(0.2)  # Brief wait after Flux State
        if check_stop_condition(stop_event):
            return False
        return True
    return False

def execute_napalm_burst(stop_event):
    """
    Execute Napalm burst combo (Priority 1):
    1. Plasmatic State (damage modifier)
    2. Napalm (Flamethrower Skill 5)
    """
    log_and_print('info', "=" * 70)
    log_and_print('info', ">>> NAPALM BURST COMBO (Highest Priority)")
    log_and_print('info', "=" * 70)
    
    # Try Flux State at the start of burst (if available)
    try_flux_state(stop_event)
    
    # Switch to Flamethrower if needed
    if not is_kit_equipped(DEFAULT_COORDS['utility_flamethrower']):
        log_and_print('info', "Switching to Flamethrower for Napalm burst")
        ensure_flamethrower_mode(stop_event)
        if check_stop_condition(stop_event): return False
        time.sleep(0.8)  # Give more time for kit to equip and skill bar to update
    else:
        # Already in Flamethrower, but skill bar might need a moment to update
        time.sleep(0.3)  # Small wait to ensure skill bar is fully updated
        # Per Metabattle: Flame Blast can be added before burst combos due to travel time
        flame_blast_ready = check_skill_available(DEFAULT_COORDS['weapon_2'])
        if flame_blast_ready:
            log_and_print('info', ">>> PRE-BURST: Using Flame Blast (travels while we use other skills)")
            button_mash(key_mapping['numpad2'], presses=2, delay=0.05)
            time.sleep(0.2)  # Short wait, skill has travel time
    
    # Verify we're actually in Flamethrower mode
    in_flamethrower_check = is_kit_equipped(DEFAULT_COORDS['utility_flamethrower'])
    log_and_print('info', f"In Flamethrower mode check: {in_flamethrower_check}")
    
    # Check Napalm (Flamethrower Skill 5) with retries
    # Napalm uses INVERTED logic: NOT black = ready, black = on cooldown
    napalm_ready = False
    for attempt in range(6):  # More attempts to catch skill bar updates
        napalm_ready, color, checked_coords = check_skill_available_multipoint(DEFAULT_COORDS['weapon_5'], invert_logic=True)
        log_and_print('info', f"Napalm ready check (attempt {attempt+1}/6): {napalm_ready}, color at {checked_coords}: {color}, sum: {sum(color) if color else 0}")
        if napalm_ready:
            break
        elif attempt < 5:
            time.sleep(0.25)  # Slightly longer wait between retries
    
    if not napalm_ready:
        log_and_print('info', "Napalm not ready, skipping burst")
        return False
    
    # STEP 1: Plasmatic State (damage modifier)
    plasmatic_ready = check_skill_available(DEFAULT_COORDS['utility_3'])
    if plasmatic_ready:
        log_and_print('info', ">>> STEP 1/2: Using Plasmatic State (damage modifier)")
        # Retry logic to ensure it fires
        plasmatic_on_cd = False
        for retry_attempt in range(3):  # Try up to 3 times
            button_mash(key_mapping['numpad9'], presses=6, delay=0.05)  # Increased to 6 presses
            time.sleep(0.5)  # Increased wait for skill to register
            plasmatic_on_cd = not check_skill_available(DEFAULT_COORDS['utility_3'])
            if plasmatic_on_cd:
                if retry_attempt > 0:
                    log_and_print('info', f"Plasmatic State fired on retry attempt {retry_attempt+1}")
                log_and_print('info', "Plasmatic State confirmed fired")
                break
            elif retry_attempt < 2:
                log_and_print('info', f"Plasmatic State may not have fired, retrying... (attempt {retry_attempt+1}/3)")
                time.sleep(0.3)  # Wait before retry
        
        if not plasmatic_on_cd:
            log_and_print('info', "WARNING: Plasmatic State may not have fired after all retries")
        if check_stop_condition(stop_event): return False
    
    # STEP 2: Napalm
    log_and_print('info', ">>> STEP 2/2: Using Napalm (Flamethrower Skill 5)")
    button_mash(key_mapping['numpad5'], presses=2, delay=0.05)
    time.sleep(2.0)  # Increased wait for skill to register and animation to complete (~2s)
    wait_until_on_cooldown(DEFAULT_COORDS['weapon_5'], timeout_seconds=2.5)
    if check_stop_condition(stop_event): return False
    
    log_and_print('info', "=" * 70)
    log_and_print('info', "NAPALM BURST COMPLETE")
    log_and_print('info', "=" * 70)
    return True

def execute_acid_bomb_burst(stop_event):
    """
    Execute Acid Bomb burst combo (Priority 2):
    1. Jump Shot (Rifle Skill 4)
    2. Acid Bomb (Elixir Gun Skill 4) - MUST CANCEL with weapon swap
    """
    log_and_print('info', "=" * 70)
    log_and_print('info', ">>> ACID BOMB BURST COMBO")
    log_and_print('info', "=" * 70)
    
    # Try Flux State at the start of burst (if available)
    try_flux_state(stop_event)
    
    # Per Metabattle: Flame Blast can be added before burst combos if in Flamethrower
    if is_kit_equipped(DEFAULT_COORDS['utility_flamethrower']):
        flame_blast_ready = check_skill_available(DEFAULT_COORDS['weapon_2'])
        if flame_blast_ready:
            log_and_print('info', ">>> PRE-BURST: Using Flame Blast (travels while we do Jump Shot/Acid Bomb)")
            button_mash(key_mapping['numpad2'], presses=2, delay=0.05)
            time.sleep(0.2)  # Short wait, skill has travel time
    
    # STEP 1: Jump Shot
    log_and_print('info', ">>> STEP 1/2: Using Jump Shot (Rifle Skill 5)")
    # Ensure we're in Rifle mode FIRST - Jump Shot is only available in Rifle mode
    if is_kit_equipped(DEFAULT_COORDS['utility_flamethrower']) or is_kit_equipped(DEFAULT_COORDS['utility_elixir']):
        log_and_print('info', "Switching to Rifle for Jump Shot")
        ensure_rifle_mode(stop_event)
        if check_stop_condition(stop_event): return False
        time.sleep(0.8)  # Increased wait for weapon swap animation and skill bar to fully update
    
    # NOW check if Jump Shot is ready - retry in case skill bar is still updating
    jump_shot_ready = False
    for attempt in range(3):
        jump_shot_ready = check_skill_available(DEFAULT_COORDS['weapon_5'])
        log_and_print('info', f"Jump Shot ready check (after switching to Rifle, attempt {attempt+1}/3): {jump_shot_ready}")
        if jump_shot_ready:
            break
        elif attempt < 2:
            time.sleep(0.2)  # Wait for skill bar to update
    
    if not jump_shot_ready:
        log_and_print('info', "Jump Shot not ready after switching to Rifle, skipping burst")
        return False
    
    # Press Jump Shot with retry if it doesn't fire
    waited = False
    jump_shot_on_cd = False
    for retry_attempt in range(2):  # Try up to 2 times
        button_mash(key_mapping['numpad5'], presses=4, delay=0.05)  # Increased to 4 presses
        time.sleep(1.0)  # Wait for skill to register and animation to complete (1s for Jump Shot)
        waited = wait_until_on_cooldown(DEFAULT_COORDS['weapon_5'], timeout_seconds=2.5)
        time.sleep(0.5)  # Additional wait after cooldown check
        jump_shot_on_cd = not check_skill_available(DEFAULT_COORDS['weapon_5'])
        if waited or jump_shot_on_cd:
            if retry_attempt > 0:
                log_and_print('info', f"Jump Shot fired on retry attempt {retry_attempt+1}")
            log_and_print('info', f"Jump Shot confirmed fired: on_cooldown={jump_shot_on_cd}")
            break
        elif retry_attempt == 0:
            log_and_print('info', f"Jump Shot may not have fired, retrying...")
            time.sleep(0.3)  # Wait before retry
    
    if not waited and not jump_shot_on_cd:
        log_and_print('info', "WARNING: Jump Shot may not have fired after retries")
    else:
        # Block longer to ensure skill completes before continuing
        time.sleep(0.6)  # Additional wait after Jump Shot completes
    if check_stop_condition(stop_event): 
        log_and_print('info', "Stop condition detected after Jump Shot, exiting Acid Bomb burst")
        return False
    
    # STEP 2: Acid Bomb
    log_and_print('info', ">>> STEP 2/2: Using Acid Bomb (Elixir Gun Skill 4) - will cancel")
    ensure_elixir_gun_mode(stop_event)
    if check_stop_condition(stop_event): return False
    time.sleep(0.8)  # Wait for Elixir Gun kit to equip and skill bar to update
    
    # Check if Acid Bomb is ready - simple check without excessive verification
    acid_bomb_ready = check_skill_available(DEFAULT_COORDS['weapon_4'])
    log_and_print('info', f"Acid Bomb ready check: {acid_bomb_ready}")
    
    if acid_bomb_ready:
        log_and_print('info', "Pressing Acid Bomb (NumPad4)")
        button_mash(key_mapping['numpad4'], presses=2, delay=0.05)
        time.sleep(0.6)  # Wait for Acid Bomb to start casting
        # Cancel Acid Bomb with weapon swap (F1)
        log_and_print('info', "Canceling Acid Bomb with weapon swap (F1)")
        button_mash(key_mapping['f1'], presses=2, delay=0.05)
        time.sleep(0.5)  # Wait after cancel to ensure weapon swap completes
        if check_stop_condition(stop_event): return False
    else:
        log_and_print('info', "Acid Bomb not ready, skipping")
        return False
    
    log_and_print('info', "=" * 70)
    log_and_print('info', "ACID BOMB BURST COMPLETE")
    log_and_print('info', "=" * 70)
    return True

def execute_morph_burst(stop_event):
    """
    Execute Morph skills burst combo (Priority 3):
    1. Defensive Protocol: Thorns (F3)
    2. Offensive Protocol: Obliterate (F4)
    3. Offensive Protocol: Demolish (F2 if available)
    4. Evolve (F5) - resets morphs
    5. Offensive Protocol: Obliterate (F4) - again after Evolve
    6. Offensive Protocol: Demolish (F2) - again after Evolve
    """
    log_and_print('info', "=" * 70)
    log_and_print('info', ">>> MORPH SKILLS BURST COMBO")
    log_and_print('info', "=" * 70)
    
    # Try Flux State at the start of burst (if available)
    try_flux_state(stop_event)
    
    # Per Metabattle: Flame Blast can be added before burst combos if in Flamethrower
    if is_kit_equipped(DEFAULT_COORDS['utility_flamethrower']):
        flame_blast_ready = check_skill_available(DEFAULT_COORDS['weapon_2'])
        if flame_blast_ready:
            log_and_print('info', ">>> PRE-BURST: Using Flame Blast (travels while we stack morphs)")
            button_mash(key_mapping['numpad2'], presses=2, delay=0.05)
            time.sleep(0.2)  # Short wait, skill has travel time
    
    # Check if Evolve is ready
    evolve_ready = check_skill_available(DEFAULT_COORDS['toolbelt_5'])
    log_and_print('info', f"Evolve ready check in morph_burst: {evolve_ready}")
    if not evolve_ready:
        log_and_print('info', "Evolve not ready, skipping morph burst")
        return False
    
    # CRITICAL: Ensure we're in Rifle mode before using toolbelt skills (morphs and Evolve)
    # This prevents kit switches from interrupting the morph sequence
    if is_kit_equipped(DEFAULT_COORDS['utility_elixir']) or is_kit_equipped(DEFAULT_COORDS['utility_flamethrower']):
        log_and_print('info', "Ensuring Rifle mode before morph sequence (critical)")
        ensure_rifle_mode(stop_event)
        time.sleep(0.3)  # Give time for weapon swap to complete
    
    # STEP 1: Defensive Protocol: Thorns - with retry if it doesn't fire
    thorns_ready = check_skill_available(DEFAULT_COORDS['toolbelt_3'])
    if thorns_ready:
        log_and_print('info', ">>> STEP 1/6: Using Defensive Protocol: Thorns (F3)")
        time.sleep(0.15)  # Small delay to ensure we're not animation locked
        # Retry logic if skill doesn't fire
        for retry_attempt in range(2):  # Try up to 2 times
            button_mash('3', presses=6, delay=0.05)  # Increased to 6 presses
            time.sleep(0.15)  # Give time for skill to register
            waited = wait_until_on_cooldown(DEFAULT_COORDS['toolbelt_3'], timeout_seconds=1.5)
            time.sleep(0.15)  # Reduced wait
            thorns_on_cd = not check_skill_available(DEFAULT_COORDS['toolbelt_3'])
            if waited or thorns_on_cd:
                if retry_attempt > 0:
                    log_and_print('info', f"Thorns fired on retry attempt {retry_attempt+1}")
                break
            elif retry_attempt == 0:
                log_and_print('info', f"Thorns may not have fired, retrying...")
                time.sleep(0.2)  # Wait a bit before retry
        
        if not waited and not thorns_on_cd:
            log_and_print('info', "WARNING: Thorns may not have fired after retries")
        log_and_print('info', f"Thorns on cooldown: {thorns_on_cd}")
        # Don't check stop condition here - continue to Evolve even if button briefly releases
    else:
        log_and_print('info', "STEP 1 SKIP: Thorns not ready")
    
    # STEP 2: Offensive Protocol: Obliterate - with retry if it doesn't fire
    obliterate_ready = check_skill_available(DEFAULT_COORDS['toolbelt_4'])
    if obliterate_ready:
        log_and_print('info', ">>> STEP 2/6: Using Offensive Protocol: Obliterate (F4)")
        time.sleep(0.15)  # Small delay to ensure previous skill finished
        # Retry logic if skill doesn't fire
        waited = False
        obliterate_on_cd = False
        for retry_attempt in range(2):  # Try up to 2 times
            button_mash('4', presses=6, delay=0.05)  # Increased to 6 presses
            time.sleep(0.4)  # Increased wait for skill to register and animation to start
            waited = wait_until_on_cooldown(DEFAULT_COORDS['toolbelt_4'], timeout_seconds=2.0)
            time.sleep(0.3)  # Additional wait after cooldown check
            obliterate_on_cd = not check_skill_available(DEFAULT_COORDS['toolbelt_4'])
            if waited or obliterate_on_cd:
                if retry_attempt > 0:
                    log_and_print('info', f"Obliterate fired on retry attempt {retry_attempt+1}")
                break
            elif retry_attempt == 0:
                log_and_print('info', f"Obliterate may not have fired, retrying...")
                time.sleep(0.3)  # Wait before retry
        
        if not waited and not obliterate_on_cd:
            log_and_print('info', "WARNING: Obliterate may not have fired after retries")
        log_and_print('info', f"Obliterate on cooldown: {obliterate_on_cd}")
        # Don't check stop condition here - continue to Evolve
    else:
        log_and_print('info', "STEP 2 SKIP: Obliterate not ready")
    
    # STEP 3: Offensive Protocol: Demolish (F2 if available)
    demolish_ready = check_skill_available(DEFAULT_COORDS['toolbelt_2'])
    if demolish_ready:
        log_and_print('info', ">>> STEP 3/6: Using Offensive Protocol: Demolish (F2)")
        button_mash('2', presses=5, delay=0.05)  # Increased to 5 presses
        time.sleep(0.1)  # Reduced delay
        waited = wait_until_on_cooldown(DEFAULT_COORDS['toolbelt_2'], timeout_seconds=1.8)
        time.sleep(0.15)  # Reduced wait
        demolish_on_cd = not check_skill_available(DEFAULT_COORDS['toolbelt_2'])
        if not demolish_on_cd and waited:
            time.sleep(0.1)
            demolish_on_cd = not check_skill_available(DEFAULT_COORDS['toolbelt_2'])
        elif not waited:
            log_and_print('info', "WARNING: Demolish may not have fired (timeout)")
        log_and_print('info', f"Demolish on cooldown: {demolish_on_cd}")
        # Don't check stop condition here - continue to Evolve
    else:
        log_and_print('info', "STEP 3 SKIP: Demolish not ready")
    
    # STEP 4: Evolve (F5) - ALWAYS use if ready (resets morphs and grants stat boost)
    # Even if no morphs were ready, we should still use Evolve for the stat boost
    # CRITICAL: We're already in Rifle mode (ensured at start of morph burst) - don't switch again!
    # Don't switch modes in the middle of morph sequence as it can interrupt the skills
    log_and_print('info', ">>> STEP 4/6: Using Evolve (F5) - Stat boost + reset morphs")
    time.sleep(0.3)  # Small delay to ensure previous morph (Demolish) has finished casting
    button_mash('5', presses=3, delay=0.05)
    time.sleep(1.2)  # Increased wait - give Evolve extra time to fire and animation to complete (critical skill)
    # Only check stop condition after Evolve - this is the critical skill
    if check_stop_condition(stop_event): 
        log_and_print('info', "Stop condition detected after Evolve")
        return False
    
    # Wait for morphs to reset after Evolve - they can take a moment (server tick timing)
    log_and_print('info', "Waiting for morphs to reset after Evolve...")
    time.sleep(0.7)  # Increased initial wait for server to process reset
    
    # STEP 5: Offensive Protocol: Obliterate (again, after Evolve reset) - retry to catch reset
    obliterate_fired = False
    for attempt in range(10):  # Increased attempts (morphs can take 1-2s to reset)
        obliterate_ready = check_skill_available(DEFAULT_COORDS['toolbelt_4'])
        log_and_print('info', f"Post-Evolve Obliterate check (attempt {attempt+1}/10): {obliterate_ready}")
        if obliterate_ready:
            log_and_print('info', f">>> STEP 5/6: Using Offensive Protocol: Obliterate (F4) - post-Evolve")
            button_mash('4', presses=4, delay=0.05)  # Increased from 3 to 4 presses
            time.sleep(0.25)
            obliterate_fired = True
            if check_stop_condition(stop_event): return False
            break
        elif attempt < 9:
            time.sleep(0.25)  # Slightly longer wait between retries
    
    if not obliterate_fired:
        log_and_print('info', "Post-Evolve Obliterate not ready after all retries")
    
    # STEP 6: Offensive Protocol: Demolish (again, after Evolve reset) - retry to catch reset
    demolish_fired = False
    for attempt in range(8):  # Increased attempts since morphs can take time to reset
        demolish_ready = check_skill_available(DEFAULT_COORDS['toolbelt_2'])
        log_and_print('info', f"Post-Evolve Demolish check (attempt {attempt+1}/8): {demolish_ready}")
        if demolish_ready:
            log_and_print('info', f">>> STEP 6/6: Using Offensive Protocol: Demolish (F2) - post-Evolve")
            button_mash('2', presses=4, delay=0.05)  # Increased from 3 to 4 presses
            time.sleep(0.25)
            demolish_fired = True
            if check_stop_condition(stop_event): return False
            break
        elif attempt < 7:
            time.sleep(0.25)  # Slightly longer wait
    
    if not demolish_fired:
        log_and_print('info', "Post-Evolve Demolish not ready after retries")
    
    log_and_print('info', "=" * 70)
    log_and_print('info', "MORPH SKILLS BURST COMPLETE")
    log_and_print('info', "=" * 70)
    return True

def execute_filler_burst(stop_event):
    """
    Execute Filler burst combo (Priority 4):
    1. Flame Blast (Flamethrower Skill 2)
    2. Blunderbuss (Rifle Skill 2) - must switch back to Rifle
    """
    log_and_print('info', "=" * 70)
    log_and_print('info', ">>> FILLER BURST COMBO")
    log_and_print('info', "=" * 70)
    
    # Try Flux State at the start of burst (if available)
    try_flux_state(stop_event)
    
    # Switch to Flamethrower
    if not is_kit_equipped(DEFAULT_COORDS['utility_flamethrower']):
        log_and_print('info', "Switching to Flamethrower for filler burst")
        ensure_flamethrower_mode(stop_event)
        if check_stop_condition(stop_event): return False
        time.sleep(0.2)
    
    # STEP 1: Flame Blast (Flamethrower Skill 2)
    flame_blast_ready = check_skill_available(DEFAULT_COORDS['weapon_2'])
    if flame_blast_ready:
        log_and_print('info', ">>> STEP 1/2: Using Flame Blast (Flamethrower Skill 2)")
        button_mash(key_mapping['numpad2'], presses=2, delay=0.05)
        time.sleep(0.3)
        if check_stop_condition(stop_event): return False
    
    # STEP 2: Blunderbuss (Rifle Skill 2) - switch back to Rifle
    ensure_rifle_mode(stop_event)
    time.sleep(0.8)  # Increased wait for weapon swap animation and skill bar to fully update
    # Retry checking Blunderbuss in case skill bar is still updating
    blunderbuss_ready = False
    for attempt in range(3):
        blunderbuss_ready = check_skill_available(DEFAULT_COORDS['weapon_2'])
        if blunderbuss_ready:
            break
        elif attempt < 2:
            time.sleep(0.2)
    if blunderbuss_ready:
        log_and_print('info', ">>> STEP 2/2: Using Blunderbuss (Rifle Skill 2)")
        # Retry logic if skill doesn't fire
        waited = False
        blunderbuss_on_cd = False
        for retry_attempt in range(2):  # Try up to 2 times
            button_mash(key_mapping['numpad2'], presses=4, delay=0.05)  # Increased to 4 presses
            time.sleep(3.0)  # Increased wait for skill to register and animation to complete (3s for Blunderbuss)
            waited = wait_until_on_cooldown(DEFAULT_COORDS['weapon_2'], timeout_seconds=3.5)
            time.sleep(0.5)  # Additional wait after cooldown check
            blunderbuss_on_cd = not check_skill_available(DEFAULT_COORDS['weapon_2'])
            if waited or blunderbuss_on_cd:
                if retry_attempt > 0:
                    log_and_print('info', f"Blunderbuss fired on retry attempt {retry_attempt+1}")
                log_and_print('info', f"Blunderbuss confirmed fired: on_cooldown={blunderbuss_on_cd}")
                break
            elif retry_attempt == 0:
                log_and_print('info', f"Blunderbuss may not have fired, retrying...")
                time.sleep(0.2)  # Wait before retry
        
        if not waited and not blunderbuss_on_cd:
            log_and_print('info', "WARNING: Blunderbuss may not have fired after retries")
        else:
            # Block longer to ensure skill completes before continuing
            time.sleep(0.6)  # Additional wait after Blunderbuss completes
        
        if check_stop_condition(stop_event): return False
    
    log_and_print('info', "=" * 70)
    log_and_print('info', "FILLER BURST COMPLETE")
    log_and_print('info', "=" * 70)
    return True

def ensure_rifle_mode(stop_event):
    """Ensure we're in Rifle mode - cancel out of any kit"""
    global last_kit_toggle_time, kit_switch_in_progress
    
    if kit_switch_in_progress or just_toggled_recently():
        return True
    
    if is_kit_equipped(DEFAULT_COORDS['utility_flamethrower']):
        log_and_print('info', "Switching to Rifle (NumPad8)")
        kit_switch_in_progress = True
        press_and_release(key_mapping['numpad8'])
        last_kit_toggle_time = time.time()
        time.sleep(0.8)
        kit_switch_in_progress = False
        return True
    elif is_kit_equipped(DEFAULT_COORDS['utility_elixir']):
        log_and_print('info', "Switching to Rifle (NumPad7)")
        kit_switch_in_progress = True
        press_and_release(key_mapping['numpad7'])
        last_kit_toggle_time = time.time()
        time.sleep(0.8)
        kit_switch_in_progress = False
        return True
    else:
        return True

def ensure_flamethrower_mode(stop_event):
    """Ensure we're in Flamethrower mode"""
    global last_kit_toggle_time, kit_switch_in_progress
    
    if kit_switch_in_progress or just_toggled_recently():
        return True
    
    if is_kit_equipped(DEFAULT_COORDS['utility_flamethrower']):
        return True
    
    log_and_print('info', "Switching to Flamethrower Kit (NumPad8)")
    kit_switch_in_progress = True
    press_and_release(key_mapping['numpad8'])
    last_kit_toggle_time = time.time()
    time.sleep(0.8)
    kit_switch_in_progress = False
    
    switched = is_kit_equipped(DEFAULT_COORDS['utility_flamethrower'])
    log_and_print('info', f"Flamethrower switch result: {switched}")
    return switched

def is_elixir_gun_equipped():
    """Check if Elixir Gun is equipped"""
    return is_kit_equipped(DEFAULT_COORDS['utility_elixir'])

def ensure_elixir_gun_mode(stop_event):
    """Ensure we're in Elixir Gun mode"""
    global last_kit_toggle_time, kit_switch_in_progress
    
    if kit_switch_in_progress or just_toggled_recently():
        return True
    
    if is_elixir_gun_equipped():
        return True
    
    log_and_print('info', "Switching to Elixir Gun Kit (NumPad7)")
    kit_switch_in_progress = True
    press_and_release(key_mapping['numpad7'])
    last_kit_toggle_time = time.time()
    time.sleep(0.8)
    kit_switch_in_progress = False
    
    switched = is_elixir_gun_equipped()
    log_and_print('info', f"Elixir Gun switch result: {switched}")
    return switched

def execute_ideal_combined_burst(stop_event, napalm_ready, acid_bomb_ready, morph_ready, filler_ready):
    """
    Execute the IDEAL combined burst per Metabattle guide:
    1. Plasmatic State
    2. Napalm
    3. Jump Shot
    4. Acid Bomb
    5. Defensive Protocol: Thorns
    6. Offensive Protocol: Obliterate
    7. Offensive Protocol: Demolish
    8. Evolve
    9. Offensive Protocol: Obliterate (post-Evolve)
    10. Offensive Protocol: Demolish (post-Evolve)
    11. Flame Blast
    12. Blunderbuss
    
    Returns True if executed, False if not possible
    """
    log_and_print('info', "=" * 70)
    log_and_print('info', ">>> ATTEMPTING IDEAL COMBINED BURST")
    log_and_print('info', "=" * 70)
    
    # Try Flux State at the start of burst (if available)
    try_flux_state(stop_event)
    
    # STEP 1: Plasmatic State (if available)
    plasmatic_ready = check_skill_available(DEFAULT_COORDS['utility_3'])
    if plasmatic_ready:
        log_and_print('info', ">>> STEP 1/12: Using Plasmatic State")
        # Retry logic to ensure it fires
        plasmatic_on_cd = False
        for retry_attempt in range(3):  # Try up to 3 times
            button_mash(key_mapping['numpad9'], presses=6, delay=0.05)  # Increased to 6 presses
            time.sleep(0.5)  # Increased wait for skill to register
            plasmatic_on_cd = not check_skill_available(DEFAULT_COORDS['utility_3'])
            if plasmatic_on_cd:
                if retry_attempt > 0:
                    log_and_print('info', f"Plasmatic State fired on retry attempt {retry_attempt+1}")
                log_and_print('info', "Plasmatic State confirmed fired")
                break
            elif retry_attempt < 2:
                log_and_print('info', f"Plasmatic State may not have fired, retrying... (attempt {retry_attempt+1}/3)")
                time.sleep(0.3)  # Wait before retry
        
        if not plasmatic_on_cd:
            log_and_print('info', "WARNING: Plasmatic State may not have fired after all retries")
        if check_stop_condition(stop_event): return False
    
    # STEP 2: Napalm (if ready)
    if napalm_ready:
        log_and_print('info', ">>> STEP 2/12: Using Napalm (Flamethrower Skill 5)")
        if not is_kit_equipped(DEFAULT_COORDS['utility_flamethrower']):
            ensure_flamethrower_mode(stop_event)
            time.sleep(0.7)  # Give more time for kit to equip and skill bar to update
        else:
            # Already in Flamethrower, but skill bar might need a moment to update after other actions
            time.sleep(0.3)  # Small wait to ensure skill bar is fully updated
        
        # Verify we're actually in Flamethrower mode
        in_flamethrower_check = is_kit_equipped(DEFAULT_COORDS['utility_flamethrower'])
        log_and_print('info', f"In Flamethrower mode check: {in_flamethrower_check}")
        
        # Retry checking Napalm - skill bar might need time to update
        # Napalm uses INVERTED logic: NOT black = ready, black = on cooldown
        napalm_fired = False
        for attempt in range(6):  # More attempts to catch skill bar updates
            # Try multipoint check - check multiple spots on the skill icon
            napalm_check, color, checked_coords = check_skill_available_multipoint(DEFAULT_COORDS['weapon_5'], invert_logic=True)
            log_and_print('info', f"Napalm ready check after switch (attempt {attempt+1}/6): {napalm_check}")
            log_and_print('info', f"Napalm pixel color at {checked_coords}: {color}, sum: {sum(color) if color else 0}")
            
            if napalm_check:
                log_and_print('info', f">>> STEP 2/12: Using Napalm (Flamethrower Skill 5) - detected at {checked_coords}")
                button_mash(key_mapping['numpad5'], presses=2, delay=0.05)
                time.sleep(0.3)
                napalm_fired = True
                if check_stop_condition(stop_event): return False
                break
            elif attempt < 5:
                time.sleep(0.25)  # Slightly longer wait between retries
        
        if not napalm_fired:
            log_and_print('info', f"STEP 2 SKIP: Napalm not ready after switching to Flamethrower (all retries exhausted, color: {color})")
    
    # STEP 3: Jump Shot (if ready and we're doing the combo)
    # Try Jump Shot before Acid Bomb if both are ready
    jump_shot_ready = False
    if acid_bomb_ready:  # If acid_bomb_with_jump_shot combo is ready, try Jump Shot first
        jump_shot_ready = check_skill_available(DEFAULT_COORDS['weapon_5'])
        if jump_shot_ready:
            log_and_print('info', ">>> STEP 3/12: Using Jump Shot (Rifle Skill 5)")
            if is_kit_equipped(DEFAULT_COORDS['utility_flamethrower']) or is_kit_equipped(DEFAULT_COORDS['utility_elixir']):
                ensure_rifle_mode(stop_event)
                time.sleep(0.8)  # Increased wait for weapon swap animation and skill bar to fully update
            # Re-check after switching - retry in case skill bar is still updating
            jump_shot_ready = False
            for attempt in range(3):
                jump_shot_ready = check_skill_available(DEFAULT_COORDS['weapon_5'])
                if jump_shot_ready:
                    break
                elif attempt < 2:
                    time.sleep(0.2)
            
            if jump_shot_ready:
                # Press Jump Shot with retry if it doesn't fire
                waited = False
                jump_shot_on_cd = False
                for retry_attempt in range(2):  # Try up to 2 times
                    button_mash(key_mapping['numpad5'], presses=4, delay=0.05)  # Jump Shot is Rifle 5 = NumPad5
                    time.sleep(1.0)  # Wait for skill to register and animation to complete (1s for Jump Shot)
                    waited = wait_until_on_cooldown(DEFAULT_COORDS['weapon_5'], timeout_seconds=2.5)
                    time.sleep(0.3)  # Additional wait after cooldown check
                    js_color_check_25 = pixel_get_color(DEFAULT_COORDS['weapon_5'][0], DEFAULT_COORDS['weapon_5'][1])
                    jump_shot_on_cd = not (js_color_check_25 is not None and js_color_check_25 != (0, 0, 0) and sum(js_color_check_25) > 30)
                    if waited or jump_shot_on_cd:
                        if retry_attempt > 0:
                            log_and_print('info', f"Jump Shot fired on retry attempt {retry_attempt+1}")
                        log_and_print('info', f"Jump Shot confirmed fired: on_cooldown={jump_shot_on_cd}")
                        break
                    elif retry_attempt == 0:
                        log_and_print('info', f"Jump Shot may not have fired, retrying...")
                        time.sleep(0.3)  # Wait before retry
                
                if not waited and not jump_shot_on_cd:
                    log_and_print('info', "WARNING: Jump Shot may not have fired after retries")
                else:
                    # Block longer to ensure skill completes before continuing
                    time.sleep(0.4)  # Additional wait after Jump Shot completes (already waited 2s+)
                
                time.sleep(0.2)  # Additional wait after Jump Shot goes on cooldown before switching
                if check_stop_condition(stop_event): return False
                else:
                    log_and_print('info', "Jump Shot not ready after switching to Rifle")
    
    # STEP 4: Acid Bomb (always try if we're in ideal burst - Acid Bomb is high priority per guide)
    log_and_print('info', ">>> STEP 4/12: Using Acid Bomb (Elixir Gun Skill 4) - will cancel")
    ensure_elixir_gun_mode(stop_event)
    time.sleep(0.8)  # Wait for Elixir Gun kit to equip and skill bar to update
    
    # Simple check if Acid Bomb is ready
    acid_bomb_ready_check = check_skill_available(DEFAULT_COORDS['weapon_4'])
    log_and_print('info', f"Acid Bomb ready check: {acid_bomb_ready_check}")
    
    if acid_bomb_ready_check:
        log_and_print('info', ">>> STEP 4/12: Pressing Acid Bomb (NumPad4) - will cancel with F1")
        button_mash(key_mapping['numpad4'], presses=2, delay=0.05)
        time.sleep(0.6)  # Wait for Acid Bomb to start casting
        log_and_print('info', ">>> STEP 4/12: Canceling Acid Bomb with F1 (weapon swap)")
        button_mash(key_mapping['f1'], presses=2, delay=0.05)
        time.sleep(0.5)  # Wait after cancel to ensure weapon swap completes
        # Ensure we're back in Rifle mode before using toolbelt skills (Evolve)
        if is_kit_equipped(DEFAULT_COORDS['utility_elixir']) or is_kit_equipped(DEFAULT_COORDS['utility_flamethrower']):
            ensure_rifle_mode(stop_event)
            time.sleep(0.3)  # Wait for weapon swap to complete
        if check_stop_condition(stop_event): return False
    
    # STEP 5-10: Morph skills (ALWAYS check if Evolve is ready, regardless of morph_ready parameter)
    # Per Metabattle: Stack morphs before Evolve, then use them again after Evolve resets
    evolve_ready = check_skill_available(DEFAULT_COORDS['toolbelt_5'])
    if evolve_ready:
        log_and_print('info', "Evolve is ready - stacking morphs before Evolve")
        
        # Ensure we're in Rifle mode before using toolbelt skills (cleaner execution)
        if is_kit_equipped(DEFAULT_COORDS['utility_elixir']) or is_kit_equipped(DEFAULT_COORDS['utility_flamethrower']):
            log_and_print('info', "Ensuring Rifle mode before Evolve")
            ensure_rifle_mode(stop_event)
            time.sleep(0.6)  # Increased wait for weapon swap animation and skill bar to fully update
        
        # STEP 5: Thorns (if available) - with retry if it doesn't fire
        thorns_ready = check_skill_available(DEFAULT_COORDS['toolbelt_3'])
        if thorns_ready:
            log_and_print('info', ">>> STEP 5/12: Using Defensive Protocol: Thorns (F3) - pre-Evolve")
            time.sleep(0.25)  # Increased delay to ensure we're not animation locked
            # Retry logic if skill doesn't fire
            waited = False
            thorns_on_cd = False
            for retry_attempt in range(2):  # Try up to 2 times
                button_mash('3', presses=6, delay=0.05)  # Increased to 6 presses
                time.sleep(0.4)  # Increased wait for skill to register
                waited = wait_until_on_cooldown(DEFAULT_COORDS['toolbelt_3'], timeout_seconds=2.0)
                time.sleep(0.3)  # Increased wait after cooldown check
                thorns_on_cd = not check_skill_available(DEFAULT_COORDS['toolbelt_3'])
                if waited or thorns_on_cd:
                    if retry_attempt > 0:
                        log_and_print('info', f"Thorns fired on retry attempt {retry_attempt+1}")
                    break
                elif retry_attempt == 0:
                    log_and_print('info', f"Thorns may not have fired, retrying...")
                    time.sleep(0.3)  # Wait a bit before retry
            
            if not waited and not thorns_on_cd:
                log_and_print('info', "WARNING: Thorns may not have fired after retries")
            log_and_print('info', f"Thorns on cooldown: {thorns_on_cd}")
            if check_stop_condition(stop_event): return False
        else:
            log_and_print('info', "STEP 5 SKIP: Thorns not ready")
        
        # STEP 6: Obliterate (if available) - with retry if it doesn't fire
        obliterate_ready = check_skill_available(DEFAULT_COORDS['toolbelt_4'])
        if obliterate_ready:
            log_and_print('info', ">>> STEP 6/12: Using Offensive Protocol: Obliterate (F4) - pre-Evolve")
            time.sleep(0.4)  # Increased delay to ensure previous skill finished
            # Retry logic if skill doesn't fire
            waited = False
            obliterate_on_cd = False
            for retry_attempt in range(3):  # Try up to 3 times
                button_mash('4', presses=7, delay=0.05)  # Increased to 7 presses for reliability
                time.sleep(0.5)  # Increased wait for skill to register and animation to start
                waited = wait_until_on_cooldown(DEFAULT_COORDS['toolbelt_4'], timeout_seconds=2.5)
                time.sleep(0.4)  # Increased wait after cooldown check
                obliterate_on_cd = not check_skill_available(DEFAULT_COORDS['toolbelt_4'])
                if waited or obliterate_on_cd:
                    if retry_attempt > 0:
                        log_and_print('info', f"Obliterate fired on retry attempt {retry_attempt+1}")
                    break
                elif retry_attempt < 2:
                    log_and_print('info', f"Obliterate may not have fired, retrying... (attempt {retry_attempt+1}/3)")
                    time.sleep(0.4)  # Wait before retry
            
            if not waited and not obliterate_on_cd:
                log_and_print('info', "WARNING: Obliterate may not have fired after all retries")
            log_and_print('info', f"Obliterate on cooldown: {obliterate_on_cd}")
            if check_stop_condition(stop_event): return False
        else:
            log_and_print('info', "STEP 6 SKIP: Obliterate not ready")
        
        # STEP 7: Demolish (if available) - with retry if it doesn't fire
        demolish_ready = check_skill_available(DEFAULT_COORDS['toolbelt_2'])
        if demolish_ready:
            log_and_print('info', ">>> STEP 7/12: Using Offensive Protocol: Demolish (F2) - pre-Evolve")
            time.sleep(0.3)  # Increased delay to ensure previous skill finished
            # Retry logic if skill doesn't fire
            waited = False
            demolish_on_cd = False
            for retry_attempt in range(2):  # Try up to 2 times
                button_mash('2', presses=6, delay=0.05)  # Increased to 6 presses
                time.sleep(0.4)  # Increased wait for skill to register
                waited = wait_until_on_cooldown(DEFAULT_COORDS['toolbelt_2'], timeout_seconds=2.0)
                time.sleep(0.3)  # Increased wait after cooldown check
                demolish_on_cd = not check_skill_available(DEFAULT_COORDS['toolbelt_2'])
                if waited or demolish_on_cd:
                    if retry_attempt > 0:
                        log_and_print('info', f"Demolish fired on retry attempt {retry_attempt+1}")
                    break
                elif retry_attempt == 0:
                    log_and_print('info', f"Demolish may not have fired, retrying...")
                    time.sleep(0.3)  # Wait before retry
            
            if not waited and not demolish_on_cd:
                log_and_print('info', "WARNING: Demolish may not have fired after retries")
            log_and_print('info', f"Demolish on cooldown: {demolish_on_cd}")
            if check_stop_condition(stop_event): return False
        else:
            log_and_print('info', "STEP 7 SKIP: Demolish not ready")
        
        # STEP 8: Evolve - ALWAYS use if ready (resets morphs and grants stat boost)
        # CRITICAL: We're already in Rifle mode from the start of morph sequence - don't switch again!
        # Don't switch modes in the middle of morph sequence as it can interrupt the skills
        log_and_print('info', ">>> STEP 8/12: Using Evolve (F5) - Stat boost + reset morphs")
        # Small delay to ensure previous morph (Demolish) has finished casting
        time.sleep(0.3)
        button_mash('5', presses=3, delay=0.05)
        time.sleep(1.2)  # Increased wait - give Evolve extra time to fire and animation to complete (critical skill)
        if check_stop_condition(stop_event): return False
        
        # Wait for morphs to reset after Evolve - they can take a moment (server tick timing)
        log_and_print('info', "Waiting for morphs to reset after Evolve...")
        time.sleep(0.8)  # Increased initial wait for server to process reset
        
        # STEP 9: Obliterate (post-Evolve) - check multiple times to catch reset
        obliterate_fired = False
        for attempt in range(10):  # Try up to 10 times (morphs can take 1-2s to reset)
            obliterate_ready = check_skill_available(DEFAULT_COORDS['toolbelt_4'])
            log_and_print('info', f"Post-Evolve Obliterate check (attempt {attempt+1}/10): {obliterate_ready}")
            if obliterate_ready:
                log_and_print('info', f">>> STEP 9/12: Using Offensive Protocol: Obliterate (F4) - post-Evolve")
                button_mash('4', presses=4, delay=0.05)  # Increased from 3 to 4 presses
                time.sleep(0.25)
                obliterate_fired = True
                if check_stop_condition(stop_event): return False
                break
            elif attempt < 9:
                time.sleep(0.25)  # Slightly longer wait between retries
        
        if not obliterate_fired:
            log_and_print('info', "Post-Evolve Obliterate not ready after all retries")
        
        # STEP 10: Demolish (post-Evolve) - check multiple times
        demolish_fired = False
        for attempt in range(5):  # More attempts since Obliterate might have fired
            demolish_ready = check_skill_available(DEFAULT_COORDS['toolbelt_2'])
            if demolish_ready:
                log_and_print('info', f">>> STEP 10/12: Using Offensive Protocol: Demolish (F2) - post-Evolve (attempt {attempt+1})")
                button_mash('2', presses=4, delay=0.05)  # Increased from 3 to 4 presses
                time.sleep(0.25)
                demolish_fired = True
                if check_stop_condition(stop_event): return False
                break
            elif attempt < 4:
                time.sleep(0.2)
        
        if not demolish_fired:
            log_and_print('info', "Post-Evolve Demolish not ready after retries")
    
    # STEP 11-12: Filler burst (if available)
    if filler_ready:
        if not is_kit_equipped(DEFAULT_COORDS['utility_flamethrower']):
            ensure_flamethrower_mode(stop_event)
            time.sleep(0.2)
        
        flame_blast_ready = check_skill_available(DEFAULT_COORDS['weapon_2'])
        if flame_blast_ready:
            log_and_print('info', ">>> STEP 11/12: Using Flame Blast (Flamethrower Skill 2)")
            button_mash(key_mapping['numpad2'], presses=2, delay=0.05)
            time.sleep(0.25)
            if check_stop_condition(stop_event): return False
        
        # Blunderbuss is Rifle Skill 2 - switch to Rifle first
        ensure_rifle_mode(stop_event)
        time.sleep(0.8)  # Increased wait for weapon swap animation and skill bar to fully update
        # Retry checking Blunderbuss in case skill bar is still updating
        blunderbuss_ready = False
        for attempt in range(3):
            blunderbuss_ready = check_skill_available(DEFAULT_COORDS['weapon_2'])
            if blunderbuss_ready:
                break
            elif attempt < 2:
                time.sleep(0.2)
        
        if blunderbuss_ready:
            log_and_print('info', ">>> STEP 12/12: Using Blunderbuss (Rifle Skill 2)")
            # Retry logic if skill doesn't fire
            waited = False
            blunderbuss_on_cd = False
            for retry_attempt in range(2):  # Try up to 2 times
                button_mash(key_mapping['numpad2'], presses=4, delay=0.05)  # Increased to 4 presses
                time.sleep(3.0)  # Increased wait for skill to register and animation to complete (3s for Blunderbuss)
                waited = wait_until_on_cooldown(DEFAULT_COORDS['weapon_2'], timeout_seconds=3.5)
                time.sleep(0.3)  # Additional wait after cooldown check
                blunderbuss_on_cd = not check_skill_available(DEFAULT_COORDS['weapon_2'])
                if waited or blunderbuss_on_cd:
                    if retry_attempt > 0:
                        log_and_print('info', f"Blunderbuss fired on retry attempt {retry_attempt+1}")
                    log_and_print('info', f"Blunderbuss confirmed fired: on_cooldown={blunderbuss_on_cd}")
                    break
                elif retry_attempt == 0:
                    log_and_print('info', f"Blunderbuss may not have fired, retrying...")
                    time.sleep(0.3)  # Wait before retry
            
            if not waited and not blunderbuss_on_cd:
                log_and_print('info', "WARNING: Blunderbuss may not have fired after retries")
            else:
                # Block longer to ensure skill completes before continuing
                time.sleep(0.6)  # Additional wait after Blunderbuss completes
            
            if check_stop_condition(stop_event): return False
    
    log_and_print('info', "=" * 70)
    log_and_print('info', "IDEAL COMBINED BURST COMPLETE")
    log_and_print('info', "=" * 70)
    return True

def power_amalgam_rifle_rotation(stop_event):
    """
    Dynamic Rifle Power Amalgam rotation per Metabattle guide:
    Priority order: Napalm > Acid Bomb > Morph skills > Filler
    Tries to combine bursts when multiple are ready (ideal combo)
    """
    rotation_count = 0
    last_elixir_use = time.time()
    last_acid_bomb_use = 0  # Track Acid Bomb separately from Jump Shot
    last_evolve_use = 0
    last_jump_shot_use = 0
    last_napalm_check = 0
    last_napalm_use = 0
    last_kit_switch = 0  # Debounce kit switches
    
    while not stop_event.is_set():
        rotation_count += 1
        
        if check_stop_condition(stop_event): break
        
        # Check current mode
        in_flamethrower = is_kit_equipped(DEFAULT_COORDS['utility_flamethrower'])
        in_elixir = is_kit_equipped(DEFAULT_COORDS['utility_elixir'])
        current_mode_str = 'Flamethrower' if in_flamethrower else ('Elixir Gun' if in_elixir else 'Rifle')
        
        # Check all skill cooldowns
        current_time = time.time()
        evolve_ready = check_skill_available(DEFAULT_COORDS['toolbelt_5'])
        obliterate_ready = check_skill_available(DEFAULT_COORDS['toolbelt_4'])
        thorns_ready = check_skill_available(DEFAULT_COORDS['toolbelt_3'])
        demolish_ready = check_skill_available(DEFAULT_COORDS['toolbelt_2'])
        
        # CRITICAL: Only check Rifle skill readiness when in Rifle mode!
        # When in kit mode, weapon_2/weapon_5 show kit skills, not Rifle skills
        # Use lower threshold (100) to match Priority 6 detection - Rifle skills may be dimmer when ready
        rifle_5_ready = False  # Jump Shot (Rifle 5)
        rifle_2_ready = False  # Blunderbuss (Rifle 2)
        if not in_flamethrower and not in_elixir:
            # We're in Rifle mode - can safely check Rifle skills
            # Use same threshold as Priority 6 (not black = ready, sum > 100)
            jump_shot_color = pixel_get_color(DEFAULT_COORDS['weapon_5'][0], DEFAULT_COORDS['weapon_5'][1])
            blunderbuss_color = pixel_get_color(DEFAULT_COORDS['weapon_2'][0], DEFAULT_COORDS['weapon_2'][1])
            rifle_5_ready = jump_shot_color is not None and jump_shot_color != (0, 0, 0) and sum(jump_shot_color) > 100
            rifle_2_ready = blunderbuss_color is not None and blunderbuss_color != (0, 0, 0) and sum(blunderbuss_color) > 100
        
        elixir_ready = check_skill_available(DEFAULT_COORDS['utility_elixir'])
        # Flamethrower kit is always available to switch unless we're already in it or just switched
        # We can't use check_skill_available for kits - instead check if we can switch
        flamethrower_ready = not in_flamethrower  # Kit is "ready" if we can switch to it
        
        # Check Flamethrower skills
        flamethrower_napalm_ready = False
        if in_flamethrower:
            flamethrower_napalm_ready = check_skill_available_multipoint(DEFAULT_COORDS['weapon_5'], invert_logic=True)[0]  # Napalm uses inverted logic
        
        # Check Elixir Gun skills
        elixir_acid_bomb_ready = False
        if in_elixir:
            elixir_acid_bomb_ready = check_skill_available(DEFAULT_COORDS['weapon_4'])
        
        time_since_elixir = current_time - last_elixir_use
        
        # Log current state
        log_and_print('info', f"--- LOOP {rotation_count} | Mode: {current_mode_str} | Time since Elixir: {time_since_elixir:.1f}s ---")
        log_and_print('info', f"Evolve: {evolve_ready} | Morphs: F2={demolish_ready} F3={thorns_ready} F4={obliterate_ready}")
        log_and_print('info', f"Rifle: 2(Blunderbuss)={rifle_2_ready} 5(Jump Shot)={rifle_5_ready}")
        if in_flamethrower:
            log_and_print('info', f"Flamethrower: 5(Napalm)={flamethrower_napalm_ready}")
        if in_elixir:
            log_and_print('info', f"Elixir Gun: 4(Acid)={elixir_acid_bomb_ready}")
        log_and_print('info', f"Kits: Elixir={elixir_ready} Flamethrower={flamethrower_ready}")
        
        # Determine what's ready for bursts
        time_since_napalm_use = current_time - last_napalm_use if last_napalm_use > 0 else 999.0
        time_since_jump_shot = current_time - last_jump_shot_use if last_jump_shot_use > 0 else 999.0
        time_since_evolve = current_time - last_evolve_use if last_evolve_use > 0 else 999.0
        
        # Napalm is ready if cooldown is up - we can always try to switch to Flamethrower to check
        # Per Metabattle: "use Acid Bomb and Napalm as often as possible"
        napalm_burst_ready = time_since_napalm_use >= 8.0  # Reduced from 10.0 to check more frequently
        # Acid Bomb can be used without Jump Shot - per guide: "use Acid Bomb whenever available"
        # Track Acid Bomb separately from Jump Shot - use it whenever cooldown is up (6-8s)
        time_since_acid_bomb = current_time - last_acid_bomb_use if last_acid_bomb_use > 0 else 999.0
        acid_bomb_burst_ready = time_since_acid_bomb >= 6.0  # Acid Bomb cooldown is ~6-8s, check frequently
        # For acid_bomb_with_jump_shot, check both Acid Bomb AND Jump Shot are ready
        acid_bomb_with_jump_shot = acid_bomb_burst_ready and time_since_jump_shot >= 8.0  # Both need to be ready
        # Morph burst is ready when Evolve is available AND we have at least 2 morphs to stack (better value)
        # Also respect cooldown to prevent spamming Evolve too frequently
        morphs_count = sum([obliterate_ready, demolish_ready, thorns_ready])
        has_morphs_available = morphs_count >= 2  # Require at least 2 morphs for Evolve combo
        morph_burst_ready = evolve_ready and has_morphs_available and time_since_evolve >= 15.0
        
        # Check Plasmatic State availability (for Priority 3.5)
        plasmatic_ready = check_skill_available(DEFAULT_COORDS['utility_3'])
        
        # Check if Flamethrower/Rifle skills are ready for filler burst
        # Filler burst: Flame Blast (Flamethrower 2) + Blunderbuss (Rifle 2)
        flamethrower_flame_blast_ready = False
        rifle_blunderbuss_ready = False
        if in_flamethrower:
            flamethrower_flame_blast_ready = check_skill_available(DEFAULT_COORDS['weapon_2'])
        # Blunderbuss is a Rifle skill - only check if in Rifle mode
        if not in_flamethrower and not in_elixir:
            rifle_blunderbuss_ready = check_skill_available(DEFAULT_COORDS['weapon_2'])
        
        # Filler burst is ready if either Flame Blast (in Flamethrower) or Blunderbuss (in Rifle) is available
        filler_burst_ready = flamethrower_flame_blast_ready or rifle_blunderbuss_ready
        
        # Try ideal combined burst if multiple are ready
        # Prefer full combos (with Jump Shot) when possible
        if (napalm_burst_ready and acid_bomb_with_jump_shot and morph_burst_ready) or \
           (napalm_burst_ready and morph_burst_ready) or \
           (acid_bomb_with_jump_shot and morph_burst_ready):
            log_and_print('info', ">>> ATTEMPTING IDEAL COMBINED BURST")
            execute_ideal_combined_burst(stop_event, napalm_burst_ready, acid_bomb_with_jump_shot, morph_burst_ready, filler_burst_ready)
            if check_stop_condition(stop_event): break
            # Update tracking - only track if skills were actually ready (cooldown was up)
            if napalm_burst_ready:
                last_napalm_use = current_time
            # Only update Acid Bomb timestamp if cooldown was up (acid_bomb_burst_ready was True)
            # This means ideal burst tried it and it likely fired if ready
            # If cooldown wasn't up, preserve old timestamp so Priority 2b can still fire later
            if acid_bomb_burst_ready:
                last_acid_bomb_use = current_time
            if acid_bomb_with_jump_shot:
                last_jump_shot_use = current_time
            if morph_burst_ready:
                last_evolve_use = current_time
            continue
        
        # PRIORITY 0.5: Rifle skills (Jump Shot/Blunderbuss) - MUST run BEFORE Priority 1
        # When in Rifle mode with skills ready, fire them BEFORE switching to Flamethrower for Napalm
        # This prevents Priority 1 from interrupting Rifle skill usage
        if not in_flamethrower and not in_elixir and (rifle_5_ready or rifle_2_ready):
            # Re-check skills to get current state (not black = ready)
            jump_shot_color = pixel_get_color(DEFAULT_COORDS['weapon_5'][0], DEFAULT_COORDS['weapon_5'][1])
            blunderbuss_color = pixel_get_color(DEFAULT_COORDS['weapon_2'][0], DEFAULT_COORDS['weapon_2'][1])
            
            # Jump Shot may be darker when ready - use lower threshold (30 instead of 100)
            # Blunderbuss is brighter when ready - keep higher threshold (100)
            jump_shot_ready_check = jump_shot_color is not None and jump_shot_color != (0, 0, 0) and sum(jump_shot_color) > 30
            blunderbuss_ready_check = blunderbuss_color is not None and blunderbuss_color != (0, 0, 0) and sum(blunderbuss_color) > 100
            
            log_and_print('info', f"Priority 0.5 check - Jump Shot: color={jump_shot_color}, ready={jump_shot_ready_check}")
            log_and_print('info', f"Priority 0.5 check - Blunderbuss: color={blunderbuss_color}, ready={blunderbuss_ready_check}")
            
            # Try Jump Shot first (higher damage)
            if jump_shot_ready_check:
                log_and_print('info', ">>> PRIORITY 0.5: Using Jump Shot (Rifle Skill 5) - ready (not black)")
                # Press Jump Shot with retry if it doesn't fire
                waited = False
                jump_shot_on_cd = False
                for retry_attempt in range(2):  # Try up to 2 times
                    button_mash(key_mapping['numpad5'], presses=4, delay=0.05)  # Jump Shot is Rifle 5 = NumPad5
                    time.sleep(1.0)  # Wait for skill to register and animation to complete (1s for Jump Shot)
                    waited = wait_until_on_cooldown(DEFAULT_COORDS['weapon_5'], timeout_seconds=2.5)
                    time.sleep(0.5)  # Additional wait after cooldown check
                    js_color_check = pixel_get_color(DEFAULT_COORDS['weapon_5'][0], DEFAULT_COORDS['weapon_5'][1])
                    jump_shot_on_cd = not (js_color_check is not None and js_color_check != (0, 0, 0) and sum(js_color_check) > 30)
                    if waited or jump_shot_on_cd:
                        if retry_attempt > 0:
                            log_and_print('info', f"Jump Shot fired on retry attempt {retry_attempt+1}")
                        log_and_print('info', f"Jump Shot confirmed fired: on_cooldown={jump_shot_on_cd}")
                        last_jump_shot_use = current_time
                        break
                    elif retry_attempt == 0:
                        log_and_print('info', f"Jump Shot may not have fired, retrying...")
                        time.sleep(0.3)  # Wait before retry
                
                if not waited and not jump_shot_on_cd:
                    log_and_print('info', "WARNING: Jump Shot may not have fired after retries")
                else:
                    # Block longer to ensure skill completes before continuing
                    time.sleep(0.4)  # Additional wait after Jump Shot completes (already waited 2s+)
                
                if check_stop_condition(stop_event): break
                continue
            # Try Blunderbuss if Jump Shot not ready
            elif blunderbuss_ready_check:
                log_and_print('info', ">>> PRIORITY 0.5: Using Blunderbuss (Rifle Skill 2) - ready (not black)")
                # Initialize variables before retry loop
                waited = False
                blunderbuss_on_cd = False
                # Retry logic if skill doesn't fire
                for retry_attempt in range(2):  # Try up to 2 times
                    button_mash(key_mapping['numpad2'], presses=4, delay=0.05)  # Blunderbuss is Rifle 2 = NumPad2
                    time.sleep(3.0)  # Increased wait for skill to register and animation to complete (3s for Blunderbuss)
                    waited = wait_until_on_cooldown(DEFAULT_COORDS['weapon_2'], timeout_seconds=3.5)
                    time.sleep(0.5)  # Additional wait after cooldown check
                    bb_color_check = pixel_get_color(DEFAULT_COORDS['weapon_2'][0], DEFAULT_COORDS['weapon_2'][1])
                    blunderbuss_on_cd = not (bb_color_check is not None and bb_color_check != (0, 0, 0) and sum(bb_color_check) > 100)
                    if waited or blunderbuss_on_cd:
                        if retry_attempt > 0:
                            log_and_print('info', f"Blunderbuss fired on retry attempt {retry_attempt+1}")
                        log_and_print('info', f"Blunderbuss confirmed fired: on_cooldown={blunderbuss_on_cd}")
                        break
                    elif retry_attempt == 0:
                        log_and_print('info', f"Blunderbuss may not have fired, retrying...")
                        time.sleep(0.3)  # Wait before retry
                
                if not waited and not blunderbuss_on_cd:
                    log_and_print('info', "WARNING: Blunderbuss may not have fired after retries")
                else:
                    # Block longer to ensure skill completes before continuing
                    time.sleep(0.4)  # Additional wait after Blunderbuss completes (already waited 2s+)
                
                if check_stop_condition(stop_event): break
                continue
        
        # PRIORITY 0.75: Plasmatic State standalone (damage modifier) - use whenever ready, high priority
        # plasmatic_ready was already checked at the top of the loop
        if plasmatic_ready:
            log_and_print('info', ">>> PRIORITY 0.75: Using Plasmatic State (standalone)")
            # Retry logic to ensure it fires
            plasmatic_on_cd = False
            for retry_attempt in range(3):  # Try up to 3 times
                button_mash(key_mapping['numpad9'], presses=6, delay=0.05)  # Increased to 6 presses
                time.sleep(0.5)  # Increased wait for skill to register
                plasmatic_on_cd = not check_skill_available(DEFAULT_COORDS['utility_3'])
                if plasmatic_on_cd:
                    if retry_attempt > 0:
                        log_and_print('info', f"Plasmatic State fired on retry attempt {retry_attempt+1}")
                    log_and_print('info', "Plasmatic State confirmed fired")
                    break
                elif retry_attempt < 2:
                    log_and_print('info', f"Plasmatic State may not have fired, retrying... (attempt {retry_attempt+1}/3)")
                    time.sleep(0.3)  # Wait before retry
            
            if not plasmatic_on_cd:
                log_and_print('info', "WARNING: Plasmatic State may not have fired after all retries")
            if check_stop_condition(stop_event): break
            continue
        
        # PRIORITY 0.8: Use maintenance morphs (protocols) when available - high priority
        # Be very aggressive - use morphs unless Evolve is ready AND we're saving for ideal burst
        time_until_evolve = 15.0 - time_since_evolve if (time_since_evolve > 0 and time_since_evolve < 15.0) else 0.0
        # Use morphs if: Evolve is not ready OR (Evolve is ready but we have 2+ morphs and it's been a while since Evolve)
        # Only save if Evolve is ready AND it's been < 5s since last Evolve (already used recently)
        should_save_morphs = evolve_ready and time_since_evolve < 5.0
        
        # Debug logging for Priority 0.8 decision
        if (obliterate_ready or demolish_ready or thorns_ready):
            log_and_print('info', f"Priority 0.8 check: evolve_ready={evolve_ready}, time_since_evolve={time_since_evolve:.1f}s, morphs_count={morphs_count}, should_save={should_save_morphs}")
        
        if not should_save_morphs and (obliterate_ready or demolish_ready or thorns_ready):
            # Ensure we're in Rifle mode to use toolbelt skills (protocols)
            if is_kit_equipped(DEFAULT_COORDS['utility_flamethrower']) or is_kit_equipped(DEFAULT_COORDS['utility_elixir']):
                log_and_print('info', ">>> PRIORITY 0.8: Ensuring Rifle mode for protocols")
                ensure_rifle_mode(stop_event)
                time.sleep(0.6)  # Increased wait for weapon swap animation and skill bar to fully update
            
            # Re-check morph availability after switching (might have changed)
            obliterate_ready = check_skill_available(DEFAULT_COORDS['toolbelt_4'])
            demolish_ready = check_skill_available(DEFAULT_COORDS['toolbelt_2'])
            thorns_ready = check_skill_available(DEFAULT_COORDS['toolbelt_3'])
            
            morphs_fired = False
            
            # Use Obliterate first (highest damage) - with retry if it doesn't fire
            if obliterate_ready:
                log_and_print('info', ">>> PRIORITY 0.8: Using Offensive Protocol: Obliterate (F4)")
                time.sleep(0.4)  # Increased delay to ensure we're not animation locked
                # Retry logic if skill doesn't fire
                waited = False
                obliterate_on_cd = False
                for retry_attempt in range(3):  # Try up to 3 times
                    button_mash('4', presses=7, delay=0.05)  # Increased to 7 presses
                    time.sleep(0.5)  # Increased wait for skill to register and animation to start
                    waited = wait_until_on_cooldown(DEFAULT_COORDS['toolbelt_4'], timeout_seconds=2.5)
                    time.sleep(0.4)  # Increased wait after cooldown check
                    obliterate_on_cd = not check_skill_available(DEFAULT_COORDS['toolbelt_4'])
                    if waited or obliterate_on_cd:
                        if retry_attempt > 0:
                            log_and_print('info', f"Obliterate fired on retry attempt {retry_attempt+1}")
                        break
                    elif retry_attempt < 2:
                        log_and_print('info', f"Obliterate may not have fired, retrying... (attempt {retry_attempt+1}/3)")
                        time.sleep(0.4)  # Wait before retry
                
                if not waited and not obliterate_on_cd:
                    log_and_print('info', "WARNING: Obliterate may not have fired after all retries")
                log_and_print('info', f"Priority 0.8 Obliterate on cooldown: {obliterate_on_cd}")
                morphs_fired = True
                if check_stop_condition(stop_event): break
            
            # Then Demolish
            if demolish_ready:
                log_and_print('info', ">>> PRIORITY 0.8: Using Offensive Protocol: Demolish (F2)")
                button_mash('2', presses=5, delay=0.05)  # Increased to 5 presses
                time.sleep(0.1)  # Reduced delay
                waited = wait_until_on_cooldown(DEFAULT_COORDS['toolbelt_2'], timeout_seconds=1.8)
                time.sleep(0.15)  # Reduced wait
                # Check multiple times to confirm cooldown
                demolish_on_cd = not check_skill_available(DEFAULT_COORDS['toolbelt_2'])
                if not demolish_on_cd and waited:
                    time.sleep(0.1)
                    demolish_on_cd = not check_skill_available(DEFAULT_COORDS['toolbelt_2'])
                elif not waited:
                    log_and_print('info', "WARNING: Demolish may not have fired (timeout)")
                log_and_print('info', f"Priority 0.8 Demolish on cooldown: {demolish_on_cd}")
                morphs_fired = True
                if check_stop_condition(stop_event): break
            
            # Finally Thorns - with retry if it doesn't fire
            if thorns_ready:
                log_and_print('info', ">>> PRIORITY 0.8: Using Defensive Protocol: Thorns (F3)")
                time.sleep(0.25)  # Increased delay to ensure we're not animation locked
                # Retry logic if skill doesn't fire
                waited = False
                thorns_on_cd = False
                for retry_attempt in range(2):  # Try up to 2 times
                    button_mash('3', presses=6, delay=0.05)  # Increased to 6 presses
                    time.sleep(0.4)  # Increased wait for skill to register
                    waited = wait_until_on_cooldown(DEFAULT_COORDS['toolbelt_3'], timeout_seconds=2.0)
                    time.sleep(0.3)  # Increased wait after cooldown check
                    thorns_on_cd = not check_skill_available(DEFAULT_COORDS['toolbelt_3'])
                    if waited or thorns_on_cd:
                        if retry_attempt > 0:
                            log_and_print('info', f"Thorns fired on retry attempt {retry_attempt+1}")
                        break
                    elif retry_attempt == 0:
                        log_and_print('info', f"Thorns may not have fired, retrying...")
                        time.sleep(0.3)  # Wait a bit before retry
                
                if not waited and not thorns_on_cd:
                    log_and_print('info', "WARNING: Thorns may not have fired after retries")
                log_and_print('info', f"Priority 0.8 Thorns on cooldown: {thorns_on_cd}")
                morphs_fired = True
                if check_stop_condition(stop_event): break
            
            if morphs_fired:
                continue
        
        # PRIORITY 1: Napalm burst
        priority_1_switched = False  # Track if we switched in Priority 1
        if napalm_burst_ready:
            time_since_napalm_check = current_time - last_napalm_check
            if last_napalm_check == 0 or time_since_napalm_check > 2.0:
                if not in_flamethrower:
                    # Only switch if we haven't switched kits recently (debounce)
                    time_since_kit_switch = current_time - last_kit_switch
                    if last_kit_switch == 0 or time_since_kit_switch > 1.5:
                        log_and_print('info', ">>> PRIORITY 1: Switching to Flamethrower to check Napalm")
                        last_napalm_check = current_time
                        last_kit_switch = time.time()  # Use actual time, not current_time
                        priority_1_switched = True
                        ensure_flamethrower_mode(stop_event)
                        time.sleep(0.8)  # Give more time for kit to equip and skill bar to update
                        if check_stop_condition(stop_event): break
                        in_flamethrower = is_kit_equipped(DEFAULT_COORDS['utility_flamethrower'])
                    else:
                        log_and_print('info', f"Priority 1 SKIP: Only {time_since_kit_switch:.1f}s since last kit switch (debounce)")
                
                if in_flamethrower:
                    # If we didn't just switch, add a small wait for skill bar stability
                    if not priority_1_switched:
                        time.sleep(0.3)  # Small wait if already in Flamethrower
                    
                    # Retry checking Napalm - skill bar might need time to update
                    # Napalm uses INVERTED logic: NOT black = ready, black = on cooldown
                    flamethrower_napalm_ready = False
                    for attempt in range(5):  # More attempts to catch skill bar updates
                        flamethrower_napalm_ready, color, checked_coords = check_skill_available_multipoint(DEFAULT_COORDS['weapon_5'], invert_logic=True)
                        log_and_print('info', f"Priority 1 Napalm check (attempt {attempt+1}/5): {flamethrower_napalm_ready}, color at {checked_coords}: {color}, sum: {sum(color) if color else 0}")
                        if flamethrower_napalm_ready:
                            break
                        elif attempt < 4:
                            time.sleep(0.25)  # Slightly longer wait between retries
                    
                    if flamethrower_napalm_ready:
                        log_and_print('info', ">>> PRIORITY 1 TRIGGERED: Napalm burst")
                        last_napalm_use = current_time
                        execute_napalm_burst(stop_event)
                        if check_stop_condition(stop_event): break
                        continue
                    else:
                        log_and_print('info', "Priority 1: Napalm not ready after switching, will try again later")
        
        # PRIORITY 2: Acid Bomb burst (prefer with Jump Shot, but can use without)
        # Be more aggressive - check if Acid Bomb cooldown is up
        if acid_bomb_burst_ready:
            # Check if Jump Shot is actually ready (need to be in Rifle mode)
            jump_shot_actually_ready = False
            if not in_flamethrower and not in_elixir:
                # Already in Rifle mode - can check directly using lower threshold
                jump_shot_color_check = pixel_get_color(DEFAULT_COORDS['weapon_5'][0], DEFAULT_COORDS['weapon_5'][1])
                jump_shot_actually_ready = jump_shot_color_check is not None and jump_shot_color_check != (0, 0, 0) and sum(jump_shot_color_check) > 30
            # Don't optimistically assume Jump Shot is ready if we're not in Rifle mode
            # If not in Rifle mode, Priority 2b will handle standalone Acid Bomb instead
            
            if jump_shot_actually_ready:
                log_and_print('info', ">>> PRIORITY 2 TRIGGERED: Acid Bomb burst (with Jump Shot)")
                last_jump_shot_use = current_time
                last_acid_bomb_use = current_time
                result = execute_acid_bomb_burst(stop_event)
                log_and_print('info', f"Acid Bomb burst completed: {result}")
                if check_stop_condition(stop_event): break
                continue
            # If Jump Shot not ready, fall through to Priority 2b (standalone Acid Bomb)
        
        # PRIORITY 2b: Acid Bomb standalone (without Jump Shot) - use whenever cooldown is up
        # Per guide: "use Acid Bomb as often as possible"
        # IMPORTANT: Place this BEFORE Priority 3 to ensure Acid Bomb is used even when Evolve is ready
        # Debug: Always log Priority 2b check to see why it might not be triggering
        log_and_print('info', f"Priority 2b check: acid_bomb_burst_ready={acid_bomb_burst_ready}, time_since_acid_bomb={time_since_acid_bomb:.1f}s, elixir_ready={elixir_ready}, in_elixir={in_elixir}")
        if acid_bomb_burst_ready:
            # Check if Acid Bomb is actually available (in Elixir Gun)
            # We need to be able to switch to Elixir Gun to use it
            # Allow using even if already in Elixir (might have switched for other reasons)
            if elixir_ready:
                # Try to use Acid Bomb standalone (without Jump Shot)
                if in_elixir:
                    # Already in Elixir Gun - simple check and use
                    acid_bomb_standalone_ready = check_skill_available(DEFAULT_COORDS['weapon_4'])
                    if acid_bomb_standalone_ready:
                        log_and_print('info', ">>> PRIORITY 2b: Acid Bomb available (already in Elixir Gun), using standalone")
                        button_mash(key_mapping['numpad4'], presses=2, delay=0.05)
                        time.sleep(0.6)  # Wait for Acid Bomb to start casting
                        button_mash(key_mapping['f1'], presses=2, delay=0.05)
                        time.sleep(0.5)  # Wait after cancel
                        last_acid_bomb_use = current_time
                        if check_stop_condition(stop_event): break
                        continue
                elif not in_elixir:
                    # Not in Elixir - switch and use
                    log_and_print('info', ">>> PRIORITY 2b: Acid Bomb available, using standalone")
                    ensure_elixir_gun_mode(stop_event)
                    time.sleep(0.8)  # Wait for Elixir Gun kit to equip
                    acid_bomb_standalone_ready = check_skill_available(DEFAULT_COORDS['weapon_4'])
                    if acid_bomb_standalone_ready:
                        log_and_print('info', "Using Acid Bomb (standalone)")
                        button_mash(key_mapping['numpad4'], presses=2, delay=0.05)
                        time.sleep(0.6)  # Wait for Acid Bomb to start casting
                        button_mash(key_mapping['f1'], presses=2, delay=0.05)
                        time.sleep(0.5)  # Wait after cancel
                        last_acid_bomb_use = current_time
                        if check_stop_condition(stop_event): break
                        continue
        
        # PRIORITY 3: Morph skills burst (Evolve combo)
        if morph_burst_ready:
            log_and_print('info', ">>> PRIORITY 3 TRIGGERED: Morph skills burst (Evolve ready!)")
            last_evolve_use = current_time
            result = execute_morph_burst(stop_event)
            log_and_print('info', f"Morph skills burst completed: {result}")
            if check_stop_condition(stop_event): break
            continue
        
        # PRIORITY 2.5: Jump Shot standalone (per guide: "can be used at any time for a large hit")
        # Only attempt if cooldown suggests it might be ready (time-based check)
        # The function will switch to Rifle and verify it's actually ready
        # Use same threshold as Priority 0.5/6 (100) for consistency
        if time_since_jump_shot >= 8.0:
            log_and_print('info', ">>> PRIORITY 2.5: Using Jump Shot (standalone, Acid Bomb on CD)")
            if is_kit_equipped(DEFAULT_COORDS['utility_flamethrower']) or is_kit_equipped(DEFAULT_COORDS['utility_elixir']):
                ensure_rifle_mode(stop_event)
                time.sleep(0.8)  # Increased wait for weapon swap animation and skill bar to fully update
            # Re-check after switching - retry in case skill bar is still updating
            # Use same threshold as Priority 0.5/6 (not black, sum > 100)
            jump_shot_ready = False
            for attempt in range(3):
                jump_shot_color_check = pixel_get_color(DEFAULT_COORDS['weapon_5'][0], DEFAULT_COORDS['weapon_5'][1])
                jump_shot_ready = jump_shot_color_check is not None and jump_shot_color_check != (0, 0, 0) and sum(jump_shot_color_check) > 30
                if jump_shot_ready:
                    break
                elif attempt < 2:
                    time.sleep(0.2)
            
            if jump_shot_ready:
                # Press Jump Shot with retry if it doesn't fire
                waited = False
                jump_shot_on_cd = False
                for retry_attempt in range(2):  # Try up to 2 times
                    button_mash(key_mapping['numpad5'], presses=4, delay=0.05)  # Jump Shot is Rifle 5 = NumPad5
                    time.sleep(1.0)  # Wait for skill to register and animation to complete (1s for Jump Shot)
                    waited = wait_until_on_cooldown(DEFAULT_COORDS['weapon_5'], timeout_seconds=2.5)
                    time.sleep(0.3)  # Additional wait after cooldown check
                    js_color_check_25 = pixel_get_color(DEFAULT_COORDS['weapon_5'][0], DEFAULT_COORDS['weapon_5'][1])
                    jump_shot_on_cd = not (js_color_check_25 is not None and js_color_check_25 != (0, 0, 0) and sum(js_color_check_25) > 30)
                    if waited or jump_shot_on_cd:
                        if retry_attempt > 0:
                            log_and_print('info', f"Jump Shot fired on retry attempt {retry_attempt+1}")
                        log_and_print('info', f"Jump Shot confirmed fired: on_cooldown={jump_shot_on_cd}")
                        break
                    elif retry_attempt == 0:
                        log_and_print('info', f"Jump Shot may not have fired, retrying...")
                        time.sleep(0.3)  # Wait before retry
                
                if not waited and not jump_shot_on_cd:
                    log_and_print('info', "WARNING: Jump Shot may not have fired after retries")
                else:
                    last_jump_shot_use = current_time  # Only update if it fired
                    # Block longer to ensure skill completes before continuing
                    time.sleep(0.6)  # Additional wait after Jump Shot completes
                
                if check_stop_condition(stop_event): break
                continue
        
        # PRIORITY 5: Filler burst (only if skills are ready)
        if filler_burst_ready:
            log_and_print('info', ">>> PRIORITY 5 TRIGGERED: Filler burst")
            execute_filler_burst(stop_event)
            if check_stop_condition(stop_event): break
            # After filler burst, switch back to Rifle if no more Flamethrower skills ready
            if not flamethrower_flame_blast_ready and not flamethrower_napalm_ready:
                log_and_print('info', "No more Flamethrower skills ready, switching back to Rifle")
                ensure_rifle_mode(stop_event)
                time.sleep(0.3)
            continue
        
        # PRIORITY 5b: If stuck in Flamethrower with no skills, switch back to Rifle
        # Skip if Priority 1 just switched us here, or if we switched recently
        if in_flamethrower and not flamethrower_flame_blast_ready and not flamethrower_napalm_ready and not priority_1_switched:
            actual_time = time.time()  # Use actual time for debounce check
            time_since_kit_switch = actual_time - last_kit_switch
            if last_kit_switch == 0 or time_since_kit_switch > 1.5:
                log_and_print('info', ">>> PRIORITY 5b: No Flamethrower skills ready, switching back to Rifle")
                last_kit_switch = actual_time
                ensure_rifle_mode(stop_event)
                time.sleep(0.3)
                if check_stop_condition(stop_event): break
                continue
            else:
                log_and_print('info', f"Priority 5b SKIP: Only {time_since_kit_switch:.1f}s since last kit switch (debounce)")
        
        # PRIORITY 6: Sustained damage - Rifle skills
        # When in Rifle mode, check if skills are ready (not black) and fire them
        if not in_flamethrower and not in_elixir:
            # We're in Rifle mode - re-check skills to get current state (not black = ready)
            # Re-check to ensure we have the most current state
            jump_shot_color = pixel_get_color(DEFAULT_COORDS['weapon_5'][0], DEFAULT_COORDS['weapon_5'][1])
            blunderbuss_color = pixel_get_color(DEFAULT_COORDS['weapon_2'][0], DEFAULT_COORDS['weapon_2'][1])
            
            # Jump Shot may be darker when ready - use lower threshold (30 instead of 100)
            # Blunderbuss is brighter when ready - keep higher threshold (100)
            jump_shot_ready_check = jump_shot_color is not None and jump_shot_color != (0, 0, 0) and sum(jump_shot_color) > 30
            blunderbuss_ready_check = blunderbuss_color is not None and blunderbuss_color != (0, 0, 0) and sum(blunderbuss_color) > 100
            
            log_and_print('info', f"Priority 6 check - Jump Shot: color={jump_shot_color}, ready={jump_shot_ready_check}")
            log_and_print('info', f"Priority 6 check - Blunderbuss: color={blunderbuss_color}, ready={blunderbuss_ready_check}")
            
            # Try Jump Shot first (higher damage) - use lower threshold (100 instead of 300)
            if jump_shot_ready_check:
                log_and_print('info', ">>> PRIORITY 6: Using Jump Shot (Rifle Skill 5) - ready (not black)")
                # Press Jump Shot with retry if it doesn't fire
                waited = False
                jump_shot_on_cd = False
                for retry_attempt in range(2):  # Try up to 2 times
                    button_mash(key_mapping['numpad5'], presses=4, delay=0.05)  # Jump Shot is Rifle 5 = NumPad5
                    time.sleep(1.0)  # Wait for skill to register and animation to complete (1s for Jump Shot)
                    waited = wait_until_on_cooldown(DEFAULT_COORDS['weapon_5'], timeout_seconds=2.5)
                    time.sleep(0.5)  # Additional wait after cooldown check
                    jump_shot_on_cd = not check_skill_available(DEFAULT_COORDS['weapon_5'])
                    if waited or jump_shot_on_cd:
                        if retry_attempt > 0:
                            log_and_print('info', f"Jump Shot fired on retry attempt {retry_attempt+1}")
                        log_and_print('info', f"Jump Shot confirmed fired: on_cooldown={jump_shot_on_cd}")
                        last_jump_shot_use = current_time
                        break
                    elif retry_attempt == 0:
                        log_and_print('info', f"Jump Shot may not have fired, retrying...")
                        time.sleep(0.3)  # Wait before retry
                
                if not waited and not jump_shot_on_cd:
                    log_and_print('info', "WARNING: Jump Shot may not have fired after retries")
                else:
                    # Block longer to ensure skill completes before continuing
                    time.sleep(0.4)  # Additional wait after Jump Shot completes (already waited 2s+)
                
                if check_stop_condition(stop_event): break
                continue
            # Try Blunderbuss if Jump Shot not ready
            elif blunderbuss_ready_check:
                log_and_print('info', ">>> PRIORITY 6: Using Blunderbuss (Rifle Skill 2) - ready (not black)")
                # Initialize variables before retry loop
                waited = False
                blunderbuss_on_cd = False
                # Retry logic if skill doesn't fire
                for retry_attempt in range(2):  # Try up to 2 times
                    button_mash(key_mapping['numpad2'], presses=4, delay=0.05)  # Blunderbuss is Rifle 2 = NumPad2
                    time.sleep(3.0)  # Increased wait for skill to register and animation to complete (3s for Blunderbuss)
                    waited = wait_until_on_cooldown(DEFAULT_COORDS['weapon_2'], timeout_seconds=3.5)
                    time.sleep(0.5)  # Additional wait after cooldown check
                    blunderbuss_on_cd = not check_skill_available(DEFAULT_COORDS['weapon_2'])
                    if waited or blunderbuss_on_cd:
                        if retry_attempt > 0:
                            log_and_print('info', f"Blunderbuss fired on retry attempt {retry_attempt+1}")
                        log_and_print('info', f"Blunderbuss confirmed fired: on_cooldown={blunderbuss_on_cd}")
                        break
                    elif retry_attempt == 0:
                        log_and_print('info', f"Blunderbuss may not have fired, retrying...")
                        time.sleep(0.3)  # Wait before retry
                
                if not waited and not blunderbuss_on_cd:
                    log_and_print('info', "WARNING: Blunderbuss may not have fired after retries")
                else:
                    # Block longer to ensure skill completes before continuing
                    time.sleep(0.4)  # Additional wait after Blunderbuss completes (already waited 2s+)
                
                if check_stop_condition(stop_event): break
                continue
        
        # PRIORITY 7: Sustained damage - Auto-attack
        if in_flamethrower:
            log_and_print('info', ">>> PRIORITY 7: Flamethrower auto-attack (Flame Jet)")
            button_mash(key_mapping['numpad1'], presses=2, delay=0.05)
            time.sleep(0.6)
        elif in_elixir:
            log_and_print('info', ">>> PRIORITY 7: Canceling out of Elixir Gun")
            ensure_rifle_mode(stop_event)
            time.sleep(0.5)
        else:
            log_and_print('info', ">>> PRIORITY 7: Rifle auto-attack (Aimed Shot)")
            button_mash(key_mapping['numpad1'], presses=2, delay=0.05)
            time.sleep(0.6)
        
        time.sleep(0.1)

def run(stop_event):
    """Main entry point for Power Amalgam Rifle (WvW) spec"""
    log_and_print('info', "Power Amalgam Rifle (WvW) spec started")
    log_and_print('info', "Hold NumPad1 to activate rotation")
    log_and_print('info', "Focus: High burst damage with multiple burst combos")
    log_and_print('info', "Burst priority (per Metabattle): Napalm > Acid Bomb > Morph skills > Filler")
    log_and_print('info', "Toolbelt skills on keys 1-5, weapon/kit skills on numpad")
    
    while not stop_event.is_set():
        if stop_event.is_set():
            logger.info("Stop event detected")
            break
        
        if keyboard.is_pressed(key_mapping['numpad1']):
            log_and_print('info', "NumPad1 pressed - starting rotation")
            power_amalgam_rifle_rotation(stop_event)
        
        time.sleep(0.05)
    
    logger.info("Power Amalgam Rifle (WvW) spec ended")
