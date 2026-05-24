"""
Herald - Power Herald Open World Build
MetaBattle reference: https://metabattle.com/wiki/Build:Herald_-_Power_Herald

Build Overview:
- Weapon: Greatsword (main), Staff (for CC)
- Legends: Glint (Dragon) + Shiro (Assassin)
- Provides permanent Quickness, Fury, and Might (25 self, ~12 allies)
- Key mechanic: Maintain 6+ energy upkeep cost for permanent Quickness via Elevated Compassion trait

Rotation (per MetaBattle):
- Swap legends off cooldown for energy
- Dragon Stance: Maintain Facet of Nature (key 2), Facet of Darkness (NumPad7), Facet of Strength (NumPad9)
  - Consume Facet of Elements (NumPad8) off cooldown for damage
- Assassin Stance: Maintain Impossible Odds (NumPad9)
- Greatsword: Use skills 5, 3, 2, 1 (SKIP skill 4 - Imperial Guard - save for emergencies)

Keybinds:
- Weapon skills: NumPad1-5
- Utility skills: NumPad6-0 (CHANGE with legend)
  - Dragon Stance (Glint): Facet of Light(6), Darkness(7), Elements(8), Strength(9), Chaos(0)
  - Assassin Stance (Shiro): Enchanted Daggers(6), Riposting Shadows(7), Phase Traversal(8), Impossible Odds(9), Jade Winds(0)
- F-key abilities:
  - Key 1 = Legend swap (F1)
  - Key 2 = Facet of Nature (F2)
- Weapon swap: TAB

Detection:
- Pixel at (2617, 950): BLACK = Assassin Stance, BRIGHT = Dragon Stance
- Pixel at (2815, 1037): BLACK = Greatsword, BRIGHT = Staff
"""

import sys
import time
import keyboard
from libs.pixel_get_color import get_color as pixel_get_color
from libs.keyboard_actions import button_mash
from libs.key_mapping import key_mapping
from libs.logger import get_logger
from libs.pause import wait_if_paused

try:
    from libs.config_manager import get_config_manager
except ImportError:
    get_config_manager = None

logger = get_logger('power_herald')
logger.propagate = True

ENABLE_DETAILED_LOGGING = False  # Set to True for debugging

def log_and_print(level, msg):
    """Simplified logging"""
    if level in ('error', 'warning', 'info') or ENABLE_DETAILED_LOGGING:
        getattr(logger, level)(msg)
        if ENABLE_DETAILED_LOGGING or level == 'info':
            print(f"[{level.upper()}] {msg}", flush=True)
            sys.stdout.flush()


# Default coordinates for skill detection
DEFAULT_COORDS = {
    # Greatsword weapon skills (NumPad1-5)
    # User-provided coordinates: skill ready when pixel is NOT black
    'weapon_1': (2587, 1013),  # NumPad1 - Mist Swing
    'weapon_2': (2625, 1013),  # NumPad2 - Mist Unleashed
    'weapon_3': (2686, 1013),  # NumPad3 - Phantom's Onslaught
    'weapon_4': (2742, 1015),  # NumPad4 - Imperial Guard (SKIP - save for emergency)
    'weapon_5': (2797, 1021),  # NumPad5 - Eternity's Requiem (HIGHEST PRIORITY)
    
    # Utility skills (NumPad6-0) - CHANGE with legend!
    # Dragon Stance: Facets | Assassin Stance: Shiro skills
    # User-provided coordinates: skill ready when pixel is NOT black
    'utility_6': (2956, 1024),     # NumPad6 - Facet of Light / Enchanted Daggers
    'utility_7': (2992, 1011),     # NumPad7 - Facet of Darkness / Riposting Shadows
    'utility_8': (3057, 1027),     # NumPad8 - Facet of Elements / Phase Traversal
    'utility_9': (3118, 1024),     # NumPad9 - Facet of Strength / Impossible Odds
    'utility_0': (3173, 1029),     # NumPad0 - Facet of Chaos / Jade Winds
    
    # F-key abilities (keys 1-2)
    'f1_legend_swap': (2750, 950),    # Key 1 - Legend swap (F1)
    'f2_facet_nature': (2521, 950),   # Key 2 - Facet of Nature (F2)
    
    # Detection pixels
    'legend_detector': (2617, 950),   # BLACK = Assassin Stance, BRIGHT = Dragon Stance
    'weapon_detector': (2815, 1037),  # BLACK = Greatsword, BRIGHT = Staff
}

# Track state
current_legend_is_shiro = False
last_legend_swap_time = 0
facets_activated = {'nature': False, 'darkness': False, 'strength': False, 'elements': False}
impossible_odds_active = False
last_detected_weapon = 'greatsword'


def check_stop_condition(stop_event):
    """Check if we should stop the rotation"""
    return not keyboard.is_pressed(key_mapping['numpad1']) or stop_event.is_set()


def check_skill_available(coords):
    """
    Check if a skill is available (not on cooldown)
    User-provided coordinates: skill ready when pixel is NOT black
    Black = (0,0,0) or very dark (sum < 30)
    NOT black = any color with sum >= 30
    """
    color = pixel_get_color(coords[0], coords[1])
    if color is None:
        return False
    
    brightness = sum(color)
    # Threshold: 30 - if pixel is NOT black (has any color), skill is ready
    return brightness >= 30


def detect_active_weapon():
    """
    Detect which weapon set is active
    Returns 'greatsword' or 'staff'
    Pixel at (2815, 1037) is BLACK when Greatsword is equipped
    """
    global last_detected_weapon
    
    weapon_color = pixel_get_color(*DEFAULT_COORDS['weapon_detector'])
    brightness = sum(weapon_color) if weapon_color else 0
    
    # BLACK = Greatsword (sum < 50), VERY BRIGHT = Staff (sum > 600)
    # Stricter threshold to avoid false positives from skill animations
    # Skill effects can make pixel temporarily bright but not pure white
    current_weapon = 'staff' if brightness > 600 else 'greatsword'
    
    # Log only on weapon change
    if current_weapon != last_detected_weapon:
        log_and_print('info', f"Weapon changed: {last_detected_weapon} -> {current_weapon} (detector: {weapon_color}, brightness: {brightness})")
        last_detected_weapon = current_weapon
    
    return current_weapon


def detect_active_legend():
    """
    Detect which legend is active
    Returns 'dragon' (Glint) or 'assassin' (Shiro)
    Pixel at (2617, 950) is BLACK when in Assassin Stance
    """
    legend_color = pixel_get_color(*DEFAULT_COORDS['legend_detector'])
    brightness = sum(legend_color) if legend_color else 0
    
    # BLACK = Assassin Stance (sum < 50), BRIGHT = Dragon Stance
    # Using strict threshold since user said it's BLACK for assassin
    return 'assassin' if brightness < 50 else 'dragon'


def cast_skill(key, skill_name, coords=None, check_cooldown=True, delay=0.3):
    """
    Cast a skill with optional cooldown check
    Returns True if cast, False if on cooldown or failed
    """
    if check_cooldown and coords:
        if not check_skill_available(coords):
            # Skill on cooldown, don't spam logs
            return False
    
    log_and_print('info', f"Casting {skill_name}")
    
    # Get the actual key to press
    actual_key = key_mapping.get(key, key)
    button_mash(actual_key)
    time.sleep(delay)
    return True


def swap_legend(stop_event):
    """
    Swap legends (F1 = key 1) for energy regeneration
    Swapping gives you 50 energy and allows upkeep management
    """
    global current_legend_is_shiro, last_legend_swap_time, facets_activated, impossible_odds_active
    
    current_time = time.time()
    time_since_last_swap = current_time - last_legend_swap_time
    
    # Swap legends roughly every 10-12 seconds (need time to use skills!)
    # MetaBattle: "swap legends pretty much off cooldown for energy"
    if time_since_last_swap < 10.0:
        return False
    
    current_legend_before = detect_active_legend()
    legend_color_before = pixel_get_color(*DEFAULT_COORDS['legend_detector'])
    
    log_and_print('info', f"Swapping legend (currently {current_legend_before}, detector color: {legend_color_before}, time since last: {time_since_last_swap:.1f}s)")
    button_mash('1')  # F1 = key 1
    time.sleep(1.2)  # Wait for legend swap animation
    
    # Detect legend after swap
    current_legend_after = detect_active_legend()
    legend_color_after = pixel_get_color(*DEFAULT_COORDS['legend_detector'])
    
    # If swap failed, try once more
    if current_legend_after == current_legend_before:
        log_and_print('warning', f"Legend swap failed (still {current_legend_after}), retrying...")
        button_mash('1')
        time.sleep(1.2)
        current_legend_after = detect_active_legend()
        legend_color_after = pixel_get_color(*DEFAULT_COORDS['legend_detector'])
    
    log_and_print('info', f"Legend swap complete: {current_legend_before} -> {current_legend_after} (detector: {legend_color_before} -> {legend_color_after})")
    
    # Toggle legend state
    current_legend_is_shiro = (current_legend_after == 'assassin')
    last_legend_swap_time = current_time
    
    # Reset facet/upkeep tracking when swapping
    if current_legend_is_shiro:
        # Switched to Assassin - reset Glint facets
        facets_activated = {'nature': False, 'darkness': False, 'strength': False, 'elements': False}
        log_and_print('info', "Reset facets (switched to Assassin)")
    else:
        # Switched to Dragon - reset Shiro upkeep
        impossible_odds_active = False
        log_and_print('info', "Reset impossible_odds (switched to Dragon)")
    
    if check_stop_condition(stop_event):
        return False
    
    return True


def activate_glint_facets(stop_event):
    """
    Activate and maintain Glint facets for permanent Quickness
    MetaBattle: Maintain Facet of Nature (key 2), Facet of Darkness (NumPad7), Facet of Strength (NumPad9)
    Consume Facet of Elements (NumPad8) for damage
    """
    global facets_activated
    
    # Check availability of facets
    nature_ready = check_skill_available(DEFAULT_COORDS['f2_facet_nature'])
    darkness_ready = check_skill_available(DEFAULT_COORDS['utility_7'])
    strength_ready = check_skill_available(DEFAULT_COORDS['utility_9'])
    elements_ready = check_skill_available(DEFAULT_COORDS['utility_8'])
    
    nature_color = pixel_get_color(*DEFAULT_COORDS['f2_facet_nature'])
    darkness_color = pixel_get_color(*DEFAULT_COORDS['utility_7'])
    strength_color = pixel_get_color(*DEFAULT_COORDS['utility_9'])
    elements_color = pixel_get_color(*DEFAULT_COORDS['utility_8'])
    
    # Activate Facet of Nature (key 2) - provides +20% boon duration (MAINTAIN)
    # This is CRITICAL for permanent Quickness per MetaBattle!
    if 'nature' not in facets_activated:
        facets_activated['nature'] = False
    
    if not facets_activated['nature']:
        if nature_ready:
            log_and_print('info', f"Activating Facet of Nature (key 2 - CRITICAL for Quickness!, color={nature_color})")
            cast_skill('2', 'Facet of Nature (key 2 - activate)', DEFAULT_COORDS['f2_facet_nature'], delay=0.3)
            facets_activated['nature'] = True
            if check_stop_condition(stop_event): return False
    
    # Activate Facet of Darkness (NumPad7) - provides Fury (MAINTAIN)
    if not facets_activated['darkness']:
        darkness_sum = sum(darkness_color) if darkness_color else 0
        log_and_print('debug', f"Checking Facet of Darkness: ready={darkness_ready}, color={darkness_color}, sum={darkness_sum}, coord={DEFAULT_COORDS['utility_7']}")
        if darkness_ready:
            log_and_print('info', f"Activating Facet of Darkness (ready, color={darkness_color})")
            cast_skill('numpad7', 'Facet of Darkness (NumPad7 - activate)', DEFAULT_COORDS['utility_7'], delay=0.3)
            facets_activated['darkness'] = True
            if check_stop_condition(stop_event): return False
    
    # Activate Facet of Strength (NumPad9) - provides Might (MAINTAIN)
    if not facets_activated['strength']:
        strength_sum = sum(strength_color) if strength_color else 0
        log_and_print('debug', f"Checking Facet of Strength: ready={strength_ready}, color={strength_color}, sum={strength_sum}, coord={DEFAULT_COORDS['utility_9']}")
        if strength_ready:
            log_and_print('info', f"Activating Facet of Strength (ready, color={strength_color})")
            cast_skill('numpad9', 'Facet of Strength (NumPad9 - activate)', DEFAULT_COORDS['utility_9'], delay=0.3)
            facets_activated['strength'] = True
            if check_stop_condition(stop_event): return False
    
    # Consume Facet of Elements (NumPad8) off cooldown for damage (CONSUME for burst)
    elements_sum = sum(elements_color) if elements_color else 0
    log_and_print('debug', f"Checking Facet of Elements: ready={elements_ready}, color={elements_color}, sum={elements_sum}")
    if elements_ready:
        cast_skill('numpad8', 'Facet of Elements (NumPad8 - consume for damage)', DEFAULT_COORDS['utility_8'], delay=0.3)
        if check_stop_condition(stop_event): return False
    
    return True


def activate_shiro_upkeep(stop_event):
    """
    Activate Impossible Odds (Shiro upkeep) for damage buff
    This is NumPad9 on Assassin Stance
    """
    global impossible_odds_active
    
    # Only activate once, then maintain
    if not impossible_odds_active:
        odds_ready = check_skill_available(DEFAULT_COORDS['utility_9'])
        odds_color = pixel_get_color(*DEFAULT_COORDS['utility_9'])
        odds_sum = sum(odds_color) if odds_color else 0
        
        log_and_print('debug', f"Checking Impossible Odds: ready={odds_ready}, color={odds_color}, sum={odds_sum}, coord={DEFAULT_COORDS['utility_9']}")
        
        if odds_ready:
            log_and_print('info', f"Activating Impossible Odds (ready, color={odds_color})")
            cast_skill('numpad9', 'Impossible Odds (NumPad9 - activate upkeep)', DEFAULT_COORDS['utility_9'], delay=0.3)
            impossible_odds_active = True
            if check_stop_condition(stop_event): return False
    
    return True


def use_weapon_skills(stop_event):
    """
    Use Greatsword skills in priority order
    Use ONE skill per call: 5 > 3 > 2 > 1 (SKIP 4 - Imperial Guard saved for emergencies)
    Assumes we're on Greatsword - if on Staff, skills just won't be available (no harm)
    """
    # No weapon detection - just use Greatsword skills
    # Priority: 5 > 3 > 2 > 1 (SKIP 4)
    
    # Check all skill availability with color debugging
    skill_5_color = pixel_get_color(*DEFAULT_COORDS['weapon_5'])
    skill_3_color = pixel_get_color(*DEFAULT_COORDS['weapon_3'])
    skill_2_color = pixel_get_color(*DEFAULT_COORDS['weapon_2'])
    
    skill_5_ready = check_skill_available(DEFAULT_COORDS['weapon_5'])
    skill_3_ready = check_skill_available(DEFAULT_COORDS['weapon_3'])
    skill_2_ready = check_skill_available(DEFAULT_COORDS['weapon_2'])
    
    # Log once per 10 attempts to show skill states
    import random
    if random.randint(1, 10) == 1:
        log_and_print('debug', f"Weapon skills: 5={skill_5_ready}({skill_5_color}), 3={skill_3_ready}({skill_3_color}), 2={skill_2_ready}({skill_2_color})")
    
    # Greatsword 5 - Eternity's Requiem (highest priority)
    if skill_5_ready:
        cast_skill('numpad5', 'Greatsword 5 - Eternity\'s Requiem', DEFAULT_COORDS['weapon_5'])
        return True
    
    # Greatsword 3 - Phantom's Onslaught
    if skill_3_ready:
        cast_skill('numpad3', 'Greatsword 3 - Phantom\'s Onslaught', DEFAULT_COORDS['weapon_3'])
        return True
    
    # Greatsword 2 - Mist Unleashed
    if skill_2_ready:
        cast_skill('numpad2', 'Greatsword 2 - Mist Unleashed', DEFAULT_COORDS['weapon_2'])
        return True
    
    # Use auto-attack (skill 1 - Mist Swing) if no other skills available
    # Log when we have to fall back to auto-attack
    if random.randint(1, 20) == 1:
        log_and_print('debug', "All weapon skills on cooldown, using auto-attack")
    button_mash(key_mapping['numpad1'], presses=1)
    time.sleep(0.1)
    
    return True


def power_herald_rotation(stop_event):
    """
    Main rotation loop for Power Herald
    
    Rotation priority:
    1. Ensure we're on Greatsword (swap from Staff if needed)
    2. Swap legends off cooldown for energy (~8s)
    3. Activate facets/upkeeps ONCE based on active legend
    4. Use weapon skills (Greatsword 5, 4, 2)
    5. Auto-attack filler
    """
    global current_legend_is_shiro, last_legend_swap_time
    
    loop_count = 0
    
    # Log initial state
    initial_legend = detect_active_legend()
    legend_color = pixel_get_color(*DEFAULT_COORDS['legend_detector'])
    log_and_print('info', f"Starting rotation: Legend={initial_legend} (detector={legend_color}), Weapon=greatsword (assumed)")
    
    while not stop_event.is_set():
        loop_count += 1
        wait_if_paused()
        
        if check_stop_condition(stop_event):
            log_and_print('info', "Stop condition detected")
            break
        
        # Log every 50 loops
        if loop_count % 50 == 0:
            active_legend = detect_active_legend()
            legend_name = 'Assassin (Shiro)' if active_legend == 'assassin' else 'Dragon (Glint)'
            time_since_swap = time.time() - last_legend_swap_time
            
            # Check skill availability
            skill_5 = check_skill_available(DEFAULT_COORDS['weapon_5'])
            skill_3 = check_skill_available(DEFAULT_COORDS['weapon_3'])
            skill_2 = check_skill_available(DEFAULT_COORDS['weapon_2'])
            
            nature_ready = check_skill_available(DEFAULT_COORDS['f2_facet_nature'])
            util_7 = check_skill_available(DEFAULT_COORDS['utility_7'])
            util_9 = check_skill_available(DEFAULT_COORDS['utility_9'])
            
            log_and_print('debug', f"Loop {loop_count}: Legend={legend_name}, Weapon=greatsword, Time since swap={time_since_swap:.1f}s")
            log_and_print('debug', f"  GS skills: 5={skill_5}, 3={skill_3}, 2={skill_2} | Facet Nature (key2)={nature_ready}, Util 7={util_7}, 9={util_9}")
        
        # Priority 1: Swap legends for energy (roughly every 10+ seconds)
        # swap_legend handles the timing check internally
        legend_swapped = swap_legend(stop_event)
        if legend_swapped:
            # Legend was swapped, give UI time to update
            if check_stop_condition(stop_event): break
            continue  # Skip to next loop iteration after swapping
        
        # Priority 2: Activate facets/upkeeps based on DETECTED legend (not tracked state)
        active_legend = detect_active_legend()
        
        # Log legend-specific actions every 25 loops for debugging
        if loop_count % 25 == 0:
            log_and_print('debug', f"Active legend: {active_legend}, facets_activated={facets_activated}, impossible_odds={impossible_odds_active}")
        
        if active_legend == 'assassin':
            # On Assassin (Shiro): activate Impossible Odds once
            activate_shiro_upkeep(stop_event)
            if check_stop_condition(stop_event): break
        else:
            # On Dragon (Glint): activate facets once, consume Facet of Elements for damage
            activate_glint_facets(stop_event)
            if check_stop_condition(stop_event): break
        
        # Priority 3: Use weapon skills (swap back to Greatsword if on Staff)
        if loop_count % 10 == 0:
            log_and_print('debug', "Attempting weapon skills...")
        
        use_weapon_skills(stop_event)
        if check_stop_condition(stop_event): break
        
        # Small delay between rotation loops
        time.sleep(0.15)


def run(stop_event):
    """
    Main entry point for Power Herald spec
    Hold NumPad1 to activate the rotation
    """
    global current_legend_is_shiro, last_legend_swap_time, last_detected_weapon, facets_activated, impossible_odds_active
    
    log_and_print('info', "======================================================================")
    log_and_print('info', "HERALD - POWER HERALD OPEN WORLD")
    log_and_print('info', "Hold NumPad1 to run rotation")
    log_and_print('info', "Build: Permanent Quickness/Fury/Might | Greatsword DPS")
    log_and_print('info', "======================================================================")
    
    # Initialize state
    current_legend_is_shiro = False
    last_legend_swap_time = time.time()
    last_detected_weapon = 'greatsword'
    facets_activated = {'nature': False, 'darkness': False, 'strength': False, 'elements': False}
    impossible_odds_active = False
    
    while not stop_event.is_set():
        wait_if_paused()
        
        if stop_event.is_set():
            log_and_print('info', "Stop event detected")
            break
        
        # Activate rotation when NumPad1 is pressed
        if keyboard.is_pressed(key_mapping['numpad1']):
            log_and_print('info', "NumPad1 pressed - starting rotation loop")
            power_herald_rotation(stop_event)
        
        time.sleep(0.05)
    
    log_and_print('info', "Stopping Power Herald rotation")

