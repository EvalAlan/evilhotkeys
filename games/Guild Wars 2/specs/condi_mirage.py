"""
Condi Mirage - Staff-Staff Build for Guild Wars 2
Based on: https://metabattle.com/wiki/Build:Mirage_-_Condi_Mirage

Build Overview:
- Weapons: Staff (dual-wield, both with Sigil of Energy)
- Focus: Condition damage (Torment, Bleeding, Confusion)
- Provides: Permanent 25 Might, Fury, and Alacrity to self and allies
- Rotation Priority:
  1. Phantasmal Warlock (Staff 5)
  2. Dodge + Chaos Vortex (Ambush) + Winds of Chaos
  3. Chaos Armor (Staff 4)
  4. Chaos Storm (Staff 2)
  5. Phase Retreat (Staff 3) - only if clones needed

Key Mechanics:
- Maintain 3 clones at all times
- Auto-attack with Winds of Chaos between Chaos Vortex casts
- Weapon swap when under 50% endurance (restores via Sigil of Energy)
- Dodge frequently for Mirage Cloak and Ambush attacks

Your Keybinds:
Staff Skills (numpad1-5):
  NumPad1 - Winds of Chaos (auto-attack)
  NumPad2 - Chaos Storm
  NumPad3 - Phase Retreat
  NumPad4 - Chaos Armor
  NumPad5 - Phantasmal Warlock

Utilities:
  NumPad6 - False Oasis (heal)
  NumPad7 - Signet of Midnight
  NumPad8 - Signet of Domination
  NumPad9 - Crystal Sands
  NumPad0 - Jaunt (elite)

Dodge: V (default, or your dodge key)
Weapon Swap: Tab (default)
"""

import time
import keyboard
from libs.pixel_get_color import get_color as pixel_get_color
from libs.keyboard_actions_monitored import press_and_release, button_mash
from libs.key_mapping import key_mapping
from libs.logger import get_logger
from libs.pause import wait_if_paused
import sys

logger = get_logger('condi_mirage')
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
    # Staff skills (bottom bar, numpad1-5) - same layout as amalgam rifle
    'weapon_1': (2587, 1013),  # Winds of Chaos (auto) - NumPad1
    'weapon_2': (2625, 1013),  # Chaos Storm - NumPad2
    'weapon_3': (2686, 1013),  # Phase Retreat - NumPad3
    'weapon_4': (2743, 1013),  # Chaos Armor - NumPad4
    'weapon_5': (2801, 1013),  # Phantasmal Warlock - NumPad5
    
    # Utility skills (numpad6-0) - same layout as amalgam rifle
    'utility_heal': (2652, 1013),    # NumPad6 - False Oasis
    'utility_1': (3007, 1013),       # NumPad7 - Signet of Midnight
    'utility_2': (3070, 1013),       # NumPad8 - Signet of Domination
    'utility_3': (3116, 1013),       # NumPad9 - Crystal Sands
    'utility_elite': (3171, 1013),   # NumPad0 - Jaunt
    
    # Shatter skills (keys 1-4, not F-keys)
    # Note: User has shatters mapped to keys 1-4 instead of F1-F4
    'shatter_2': (2645, 950),        # Key 2 - Cry of Frustration (condition damage shatter)
}

# Dodge key - default is 'v', adjust if needed
DODGE_KEY = 'v'

# Weapon swap debounce (for endurance restore via Sigil of Energy)
last_weapon_swap = 0.0
WEAPON_SWAP_COOLDOWN = 15.0  # Minimum time between weapon swaps (endurance restore is the goal)

def check_stop_condition(stop_event):
    """Check if we should stop the rotation"""
    return not keyboard.is_pressed(key_mapping['numpad1']) or stop_event.is_set()

def check_skill_available(coords):
    """Check if a skill is available (not on cooldown)"""
    color = pixel_get_color(coords[0], coords[1])
    return color is not None and color != (0, 0, 0) and sum(color) > 300

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

def execute_ambush_combo(stop_event):
    """
    Execute dodge + Chaos Vortex (ambush) + Winds of Chaos
    Priority 2 from the guide
    """
    log_and_print('info', "Executing Ambush Combo: Dodge + Chaos Vortex + Winds of Chaos")
    
    # Dodge to trigger Mirage Cloak and Chaos Vortex ambush
    log_and_print('info', "Dodging...")
    press_and_release(DODGE_KEY, delay=0.1)
    time.sleep(0.3)  # Wait for dodge animation and ambush to fire
    if check_stop_condition(stop_event): return False
    
    # Follow up with Winds of Chaos (auto-attack)
    log_and_print('info', "Using Winds of Chaos (auto-attack)")
    press_and_release(key_mapping['numpad1'], delay=0.1)
    time.sleep(0.4)  # Allow auto-attack to complete
    if check_stop_condition(stop_event): return False
    
    return True

def weapon_swap_if_needed(stop_event):
    """
    Weapon swap when under 50% endurance (per guide)
    For now, we'll swap periodically or after bursts to restore endurance via Sigil of Energy
    """
    global last_weapon_swap
    current_time = time.time()
    
    # Only swap if enough time has passed since last swap
    if (current_time - last_weapon_swap) < WEAPON_SWAP_COOLDOWN:
        return False
    
    # Swap weapons (Tab key by default)
    # Using press_and_release with string key (works with keyboard library)
    log_and_print('info', "Weapon swapping to restore endurance (Sigil of Energy)")
    press_and_release('tab', delay=0.1)
    last_weapon_swap = current_time
    time.sleep(0.3)  # Brief pause after swap
    return True

def condi_mirage_rotation(stop_event):
    """
    Main rotation for Condi Mirage (Staff-Staff)
    Based on Metabattle priority order:
    1. Phantasmal Warlock (Staff 5)
    2. Dodge + Chaos Vortex + Winds of Chaos
    3. Chaos Armor (Staff 4)
    4. Chaos Storm (Staff 2)
    5. Phase Retreat (Staff 3) - only if clones needed
    """
    rotation_count = 0
    rotation_start_time = time.time()  # Track rotation start for relative times
    last_phase_retreat_use = 0.0
    last_crystal_sands_use = 0.0
    last_jaunt_use = 0.0
    last_chaos_armor_use = 0.0
    last_dodge_time = 0.0
    last_ambush_combo = 0.0
    last_winds_of_chaos = 0.0
    last_phantasmal_warlock_use = 0.0
    last_false_oasis_use = 0.0
    clones_need_refresh = False  # Track if we need to generate clones
    
    while not stop_event.is_set():
        rotation_count += 1
        current_time = time.time()
        
        if check_stop_condition(stop_event): break
        
        # Check all skill cooldowns
        phantasmal_warlock_ready = check_skill_available(DEFAULT_COORDS['weapon_5'])
        chaos_armor_ready = check_skill_available(DEFAULT_COORDS['weapon_4'])
        chaos_storm_ready = check_skill_available(DEFAULT_COORDS['weapon_2'])
        phase_retreat_ready = check_skill_available(DEFAULT_COORDS['weapon_3'])
        crystal_sands_ready = check_skill_available(DEFAULT_COORDS['utility_3'])
        jaunt_ready = check_skill_available(DEFAULT_COORDS['utility_elite'])
        false_oasis_ready = check_skill_available(DEFAULT_COORDS['utility_heal'])
        cry_of_frustration_ready = check_skill_available(DEFAULT_COORDS['shatter_2'])
        
        # Calculate time since last uses (handle initial values)
        time_since_dodge = current_time - last_dodge_time if last_dodge_time > 0 else 999.0
        time_since_phase_retreat = current_time - last_phase_retreat_use if last_phase_retreat_use > 0 else 999.0
        time_since_crystal_sands = current_time - last_crystal_sands_use if last_crystal_sands_use > 0 else 999.0
        time_since_jaunt = current_time - last_jaunt_use if last_jaunt_use > 0 else 999.0
        time_since_chaos_armor = current_time - last_chaos_armor_use if last_chaos_armor_use > 0 else 999.0
        time_since_ambush_combo = current_time - last_ambush_combo if last_ambush_combo > 0 else 999.0
        time_since_swap = current_time - last_weapon_swap if last_weapon_swap > 0 else 999.0
        time_since_warlock = current_time - last_phantasmal_warlock_use if last_phantasmal_warlock_use > 0 else 999.0
        
        # Check for pause
        wait_if_paused()
        if check_stop_condition(stop_event): break
        
        # Log current state (like amalgam rifle)
        log_and_print('info', f"--- LOOP {rotation_count} ---")
        log_and_print('info', f"Staff Skills: 2(Chaos Storm)={chaos_storm_ready} 3(Phase Retreat)={phase_retreat_ready} 4(Chaos Armor)={chaos_armor_ready} 5(Warlock)={phantasmal_warlock_ready}")
        log_and_print('info', f"Utilities: Crystal Sands={crystal_sands_ready} Jaunt={jaunt_ready} False Oasis={false_oasis_ready}")
        log_and_print('info', f"Shatter: Cry of Frustration (key 2)={cry_of_frustration_ready}")
        log_and_print('info', f"Time since: Dodge={time_since_dodge:.1f}s Ambush={time_since_ambush_combo:.1f}s Warlock={time_since_warlock:.1f}s Weapon Swap={time_since_swap:.1f}s")
        
        # Priority 1: Phantasmal Warlock (Staff 5)
        # Highest priority - generates clone and does damage
        # Per MetaBattle priority list - use when ready
        if phantasmal_warlock_ready:
            log_and_print('info', ">>> PRIORITY 1: Phantasmal Warlock (Staff 5)")
            button_mash(key_mapping['numpad5'], presses=3, delay=0.05)
            last_phantasmal_warlock_use = current_time
            time.sleep(0.5)  # Wait for cast
            wait_until_on_cooldown(DEFAULT_COORDS['weapon_5'], timeout_seconds=1.5)
            if check_stop_condition(stop_event): break
            continue
        
        # Priority 2: Dodge + Chaos Vortex (Ambush) + Winds of Chaos
        # Main damage rotation - dodge triggers ambush, then auto-attack
        # Dodge cooldown is ~10s, but with endurance regen we can dodge every ~8-9s
        # Only dodge if we have enough endurance (haven't dodged too recently)
        if time_since_dodge > 8.0:  # Wait for dodge cooldown (~10s, but allow some regen)
            log_and_print('info', ">>> PRIORITY 2: Ambush Combo (Dodge + Chaos Vortex + Winds of Chaos)")
            execute_ambush_combo(stop_event)
            last_dodge_time = current_time
            last_ambush_combo = current_time
            
            # Check if we should weapon swap after dodge (for endurance restore)
            # Swap if we've dodged several times and haven't swapped recently
            # This simulates being under 50% endurance after multiple dodges
            if time_since_swap > 15.0:  # Been dodging a lot, swap for endurance restore
                weapon_swap_if_needed(stop_event)
            
            if check_stop_condition(stop_event): break
            continue
        
        # Priority 3: Chaos Armor (Staff 4)
        # Provides Chaos Aura and damage increase - use off cooldown per MetaBattle
        if chaos_armor_ready:
            log_and_print('info', ">>> PRIORITY 3: Chaos Armor (Staff 4)")
            button_mash(key_mapping['numpad4'], presses=3, delay=0.05)
            last_chaos_armor_use = current_time
            time.sleep(0.4)
            wait_until_on_cooldown(DEFAULT_COORDS['weapon_4'], timeout_seconds=1.5)
            if check_stop_condition(stop_event): break
            continue
        
        # Priority 4: Chaos Storm (Staff 2)
        # AoE damage and combo field
        if chaos_storm_ready:
            log_and_print('info', ">>> PRIORITY 4: Chaos Storm (Staff 2)")
            button_mash(key_mapping['numpad2'], presses=3, delay=0.05)
            time.sleep(0.5)
            wait_until_on_cooldown(DEFAULT_COORDS['weapon_2'], timeout_seconds=1.5)
            if check_stop_condition(stop_event): break
            continue
        
        # Priority 5: Cry of Frustration (key 2 shatter) - BEFORE Phase Retreat
        # Per MetaBattle: "only uses Cry of Frustration when you can immediately generate 3 clones again"
        # Use BEFORE Phase Retreat so we can use Phase Retreat to regenerate clones after shattering
        # Note: Shatters are on keys 1-4, not F-keys
        if cry_of_frustration_ready:
            has_clone_gen = phantasmal_warlock_ready or phase_retreat_ready
            log_and_print('info', f"Priority 5 check: Cry ready={cry_of_frustration_ready}, Warlock={phantasmal_warlock_ready}, Phase Retreat={phase_retreat_ready}, has_clone_gen={has_clone_gen}")
            if has_clone_gen:
                log_and_print('info', ">>> PRIORITY 5: Using Cry of Frustration (key 2) - clones can be regenerated")
                button_mash('2', presses=3, delay=0.05)  # Key 2 (shatter, not F2)
                time.sleep(0.3)
                if check_stop_condition(stop_event): break
                continue
        
        # Priority 6: Phase Retreat (Staff 3) - only if clones needed
        # Use sparingly to generate clones when needed
        if phase_retreat_ready and (clones_need_refresh or time_since_phase_retreat > 15.0):
            log_and_print('info', ">>> PRIORITY 6: Phase Retreat (Staff 3) - generating clone")
            button_mash(key_mapping['numpad3'], presses=3, delay=0.05)
            last_phase_retreat_use = current_time
            clones_need_refresh = False
            time.sleep(0.4)
            wait_until_on_cooldown(DEFAULT_COORDS['weapon_3'], timeout_seconds=1.5)
            if check_stop_condition(stop_event): break
            continue
        
        # Priority 7: Jaunt (elite) - damage, teleport, condition cleanse
        # Use frequently when ready (has 3 charges, ~30s cooldown per charge)
        # Per MetaBattle: "deals good damage, can teleport you out of danger, cleanses 1 condition"
        if jaunt_ready and time_since_jaunt > 5.0:  # Reduced from 20.0 - use charges frequently
            log_and_print('info', ">>> PRIORITY 7: Using Jaunt (elite)")
            button_mash(key_mapping['numpad0'], presses=3, delay=0.05)
            last_jaunt_use = current_time
            time.sleep(0.4)
            wait_until_on_cooldown(DEFAULT_COORDS['utility_elite'], timeout_seconds=1.5)
            if check_stop_condition(stop_event): break
            continue
        
        # Priority 8: Crystal Sands - damage and more ambushes
        # Use off cooldown per MetaBattle: "Crystal Sands provides damage and more Ambushes"
        if crystal_sands_ready:
            log_and_print('info', ">>> PRIORITY 8: Using Crystal Sands (utility)")
            button_mash(key_mapping['numpad9'], presses=3, delay=0.05)
            last_crystal_sands_use = current_time
            time.sleep(0.4)
            wait_until_on_cooldown(DEFAULT_COORDS['utility_3'], timeout_seconds=1.5)
            if check_stop_condition(stop_event): break
            continue
        
        # Priority 9: False Oasis - heal and extra dodge
        # Per MetaBattle: "Use Chaos Armor, Crystal Sands and False Oasis off cooldown"
        # "False Oasis... provides an extra dodge for more damage"
        if false_oasis_ready:
            log_and_print('info', ">>> PRIORITY 9: Using False Oasis (heal - extra dodge for damage)")
            button_mash(key_mapping['numpad6'], presses=3, delay=0.05)
            last_false_oasis_use = current_time
            time.sleep(0.5)
            wait_until_on_cooldown(DEFAULT_COORDS['utility_heal'], timeout_seconds=1.5)
            if check_stop_condition(stop_event): break
            continue
        
        # Filler: Auto-attack (Winds of Chaos)
        # Between each Chaos Vortex, allow one Winds of Chaos (per guide)
        # Only use if we haven't used it too recently after an ambush combo
        time_since_winds = current_time - last_winds_of_chaos
        if time_since_winds > 1.0:  # Don't spam auto-attack
            log_and_print('debug', "Using Winds of Chaos (auto-attack)")
            button_mash(key_mapping['numpad1'], presses=2, delay=0.05)
            last_winds_of_chaos = current_time
            time.sleep(0.4)  # Allow auto-attack to complete
            if check_stop_condition(stop_event): break
        
        # Small delay before next check
        time.sleep(0.1)

def run(stop_event):
    """
    Main entry point for Condi Mirage spec
    Hold numpad1 to activate the rotation
    """
    logger.info("Condi Mirage (Staff-Staff) spec started")
    log_and_print('info', "=" * 70)
    log_and_print('info', "CONDI MIRAGE - STAFF-STAFF BUILD")
    log_and_print('info', "Hold NumPad1 to run rotation")
    log_and_print('info', "=" * 70)
    
    while not stop_event.is_set():
        if stop_event.is_set():
            logger.info("Stop event detected")
            break
        
        if keyboard.is_pressed(key_mapping['numpad1']):
            log_and_print('info', "NumPad1 pressed - starting rotation")
            condi_mirage_rotation(stop_event)
        
        time.sleep(0.05)
    
    logger.info("Condi Mirage spec ended")

