"""
Power Troubadour - Spear + Dagger/Sword Build for Guild Wars 2
Based on: https://metabattle.com/wiki/Build:Troubadour_-_Power_Troubadour

Build Overview:
- Weapons: Spear + Dagger/Sword
- Focus: Strike damage with Quickness support
- Provides: Quickness, Fury, and Might to self and nearby allies
- Rotation Priority:
  1. Lively Lute (off cooldown with 3 notes)
  2. Deafening Drum (spend extra notes for damage/CC)
  3. Tale of the Soulkeeper (off cooldown, cast while Lute playing with 1-0 notes)
  4. Flustering Flute + Tale of the Tortured Mastermind (one after the other)
  5. Crescendo (off cooldown, generates 1 note/sec for 5 seconds)

Key Mechanics:
- Notes replace clones (max 3 notes)
- Instruments replace shatters/F1–F5 (bound to 1–5)
- Always cast Lively Lute off cooldown with 3 notes
- Cast Tale of the Soulkeeper while Lute is playing with 1 or 0 notes (generates 2 notes)
- Cast Crescendo while other instruments are active to amplify them and generate notes

Your Keybinds:
Weapon Skills (Spear / Dagger-Sword): numpad1-5
  NumPad1 - Weapon Skill 1 (auto-attack)
  NumPad2 - Weapon Skill 2
  NumPad3 - Weapon Skill 3
  NumPad4 - Weapon Skill 4
  NumPad5 - Weapon Skill 5

Utilities: numpad6-0
  NumPad6 - Signet of the Ether (heal)
  NumPad7 - Tale of the Soulkeeper
  NumPad8 - Tale of the Tortured Mastermind
  NumPad9 - Blink / flex
  NumPad0 - Tale of the August Queen (elite)

Instruments (keys 1-5, replacing shatters/F1–F5):
  Key 1 - Lively Lute          (F1, damage, generates 1 note)
  Key 2 - Flustering Flute     (F2, damage, generates 1 note)
  Key 3 - Deafening Drum       (F4, damage/CC, consumes notes)
  Key 4 - Harmonious Harp      (F5, Distortion / support, amplifies instruments)
  Key 5 - Crescendo            (F3, boons, generates 1 note/sec for 5 seconds)

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

logger = get_logger('power_troubadour')
logger.propagate = True

# Enable/disable detailed logging
ENABLE_DETAILED_LOGGING = True

# Rotation feature toggles / tuning knobs
# Set these to True if you explicitly want them in the DPS loop.
USE_SIGNET_IN_ROTATION = False   # Signet of the Ether (heal) - defaults OFF for golem DPS
USE_BLINK_IN_ROTATION = False    # Blink - mobility/stunbreak, not used in DPS loop by default

# Approximate cooldown for Harmonious Harp (F5) usage in rotation (seconds)
HARMONIOUS_HARP_COOLDOWN = 0.5  # Reduced from 20.0 - fire as soon as available

# Minimum time between instrument casts (Lute/Flute/Drum/Crescendo/Harp/Queen)
# This is a soft "GCD" to avoid stepping on ongoing animations.
INSTRUMENT_GCD = 0.5  # Reduced from 1.2 - allow faster rotation
HEAVY_INSTRUMENT_GCD = 0.5  # Reduced from 1.5 - allow faster rotation

def log_and_print(level, msg):
    """Log and also print to ensure visibility"""
    getattr(logger, level)(msg)
    if ENABLE_DETAILED_LOGGING:
        print(f"[{level.upper()}] {msg}", flush=True)
        sys.stdout.flush()

# Coordinates for skill availability detection (matching standard layout)
DEFAULT_COORDS = {
    # Spear skills (bottom bar, numpad1-5)
    'weapon_1': (2587, 1013),  # Auto-attack - NumPad1
    'weapon_2': (2625, 1013),  # Skill 2 - NumPad2
    'weapon_3': (2686, 1013),  # Skill 3 - NumPad3
    'weapon_4': (2743, 1013),  # Skill 4 - NumPad4
    'weapon_5': (2801, 1013),  # Skill 5 - NumPad5
    
    # Dagger/Sword skills (bottom bar, numpad1-5) - same positions as Spear
    'dagger_sword_2': (2625, 1013),  # Skill 2 - NumPad2
    'dagger_sword_3': (2686, 1013),  # Skill 3 - NumPad3
    'dagger_sword_4': (2743, 1013),  # Skill 4 - NumPad4
    'dagger_sword_5': (2801, 1013),  # Skill 5 - NumPad5
    
    # Weapon set detection pixel
    'weapon_set_indicator': (2595, 1020),  # White when on Dagger/Sword
    
    # Utility skills (numpad6-0)
    'utility_heal': (2652, 1013),    # NumPad6 - Signet of the Ether
    'utility_1': (3007, 1013),       # NumPad7 - Tale of the Soulkeeper
    'utility_2': (3070, 1013),       # NumPad8 - Tale of the Tortured Mastermind
    'utility_3': (3116, 1013),       # NumPad9 - Blink
    'utility_elite': (3171, 1013),   # NumPad0 - Tale of the August Queen
    
    # Instruments (F1–F5 icons; keybinds remapped in-game to 1/2/3/4/5)
    'instrument_1': (2600, 950),     # F1 icon - Lively Lute (key 1)
    'instrument_2': (2645, 950),     # F2 icon - Flustering Flute (key 2)
    'instrument_3': (2790, 950),     # F4 icon - Deafening Drum (key 3) - matches docstring
    'instrument_4': (2736, 950),     # F5 icon - Harmonious Harp (key 4) - TODO: verify coordinate
    'instrument_5': (2690, 950),     # F3 icon - Crescendo (key 5) - matches docstring
}

def check_stop_condition(stop_event):
    """Check if we should stop the rotation"""
    return not keyboard.is_pressed(key_mapping['numpad1']) or stop_event.is_set()

def check_weapon_set_pixel():
    """Fallback pixel-based detection. Returns 'dagger_sword' or 'spear'."""
    indicator_coords = DEFAULT_COORDS['weapon_set_indicator']
    white_count = 0
    checks = 5
    brightness_values = []
    
    for _ in range(checks):
        color = pixel_get_color(indicator_coords[0], indicator_coords[1])
        if color is not None:
            brightness = sum(color)
            brightness_values.append(brightness)
            if brightness > 350:
                white_count += 1
        time.sleep(0.03)
    
    if ENABLE_DETAILED_LOGGING and len(brightness_values) > 0:
        avg_brightness = sum(brightness_values) / len(brightness_values)
        log_and_print('debug', f"Weapon set check: brightness={brightness_values}, avg={avg_brightness:.0f}, white_count={white_count}/{checks}")
    
    return 'dagger_sword' if white_count >= (checks // 2 + 1) else 'spear'

class WeaponSetTracker:
    """Tracks weapon set state using skill cooldowns and explicit swaps."""
    def __init__(self):
        self.current_set = 'spear'  # Start with Spear (default)
        self.last_swap_time = time.time()
        self.spear_4_last_used = 0.0
        self.spear_2_last_used = 0.0
        self.dagger_5_last_used = 0.0
        self.dagger_2_last_used = 0.0
        self.dagger_3_last_used = 0.0
    
    def swap(self):
        """Called when weapon swap occurs."""
        self.current_set = 'dagger_sword' if self.current_set == 'spear' else 'spear'
        self.last_swap_time = time.time()
        # Clear stale skill-use hints. The old code let a pre-swap Spear cast immediately
        # "correct" the tracker back to Spear after a successful swap. Brilliant, if the
        # goal was lying to ourselves.
        self.spear_4_last_used = 0.0
        self.spear_2_last_used = 0.0
        self.dagger_5_last_used = 0.0
        self.dagger_2_last_used = 0.0
        self.dagger_3_last_used = 0.0
        log_and_print('debug', f"Weapon swap detected - now on {self.current_set}")
    
    def update_from_skill_use(self, skill_name):
        """Update state when a weapon skill is used."""
        current_time = time.time()
        if skill_name == 'spear_4':
            self.spear_4_last_used = current_time
            if self.current_set != 'spear':
                log_and_print('debug', "Skill use indicates Spear set - correcting state")
                self.current_set = 'spear'
        elif skill_name == 'spear_2':
            self.spear_2_last_used = current_time
            if self.current_set != 'spear':
                log_and_print('debug', "Skill use indicates Spear set - correcting state")
                self.current_set = 'spear'
        elif skill_name == 'dagger_5':
            self.dagger_5_last_used = current_time
            if self.current_set != 'dagger_sword':
                log_and_print('debug', "Skill use indicates Dagger/Sword set - correcting state")
                self.current_set = 'dagger_sword'
        elif skill_name == 'dagger_2':
            self.dagger_2_last_used = current_time
            if self.current_set != 'dagger_sword':
                log_and_print('debug', "Skill use indicates Dagger/Sword set - correcting state")
                self.current_set = 'dagger_sword'
        elif skill_name == 'dagger_3':
            self.dagger_3_last_used = current_time
            if self.current_set != 'dagger_sword':
                log_and_print('debug', "Skill use indicates Dagger/Sword set - correcting state")
                self.current_set = 'dagger_sword'
    
    def validate_with_cooldowns(self, weapon_2_ready, weapon_3_ready, weapon_4_ready, weapon_5_ready):
        """Validate current set using skill cooldowns. Returns validated set."""
        current_time = time.time()
        
        # If we just swapped, trust the explicit swap before stale skill-cooldown hints.
        if current_time - self.last_swap_time < 2.0:
            return self.current_set

        # If we recently used a Spear skill, we must be on Spear
        if (current_time - self.spear_4_last_used < 2.0 or 
            current_time - self.spear_2_last_used < 2.0):
            if self.current_set != 'spear':
                log_and_print('debug', "Recent Spear skill use detected - correcting to Spear")
                self.current_set = 'spear'
            return 'spear'
        
        # If we recently used a Dagger skill, we must be on Dagger/Sword
        if (current_time - self.dagger_5_last_used < 2.0 or 
            current_time - self.dagger_2_last_used < 2.0 or
            current_time - self.dagger_3_last_used < 2.0):
            if self.current_set != 'dagger_sword':
                log_and_print('debug', "Recent Dagger/Sword skill use detected - correcting to Dagger/Sword")
                self.current_set = 'dagger_sword'
            return 'dagger_sword'
        
        # Pixel fallback is intentionally disabled by default for this spec. The sampled
        # coordinate changes with animation/UI state and was repeatedly flipping Spear <->
        # Dagger/Sword without a real weapon swap. Explicit swaps plus short cooldown hints
        # are less fancy and less wrong.
        return self.current_set
    
    def get(self):
        """Get current weapon set."""
        return self.current_set

def get_skill_brightness(coords):
    color = pixel_get_color(coords[0], coords[1])
    if isinstance(color, (tuple, list)):
        return sum(color)
    return 0


def check_skill_available(coords, threshold=300):
    """Check if a skill is available (not on cooldown)
    threshold: minimum brightness to consider skill available (default 300)"""
    color = pixel_get_color(coords[0], coords[1])
    if color is None:
        return False
    brightness = sum(color)
    is_available = color != (0, 0, 0) and brightness > threshold
    return is_available

def wait_until_on_cooldown(coords, timeout_seconds: float = 2.0, poll_seconds: float = 0.05, min_wait_after: float = 0.0) -> bool:
    """Wait until the given skill pixel turns dark (goes on cooldown).
    min_wait_after: Minimum time to wait after pixel goes dark (for cast animations to complete)."""
    initial_color = pixel_get_color(coords[0], coords[1])
    initial_sum = sum(initial_color) if initial_color else 0
    start = time.time()
    cooldown_detected_time = None
    
    while (time.time() - start) < timeout_seconds:
        color = pixel_get_color(coords[0], coords[1])
        if color is None:
            cooldown_detected_time = time.time()
            break
        current_sum = sum(color)
        
        # Skill is on cooldown if completely black or below threshold
        if color == (0, 0, 0) or current_sum <= 300:
            cooldown_detected_time = time.time()
            break
        
        time.sleep(poll_seconds)
    
    # If cooldown was detected, wait the minimum time to ensure cast completes
    if cooldown_detected_time and min_wait_after > 0:
        elapsed = time.time() - cooldown_detected_time
        if elapsed < min_wait_after:
            time.sleep(min_wait_after - elapsed)
    
    return cooldown_detected_time is not None

def power_troubadour_rotation(stop_event):
    """
    Main rotation for Power Troubadour (Spear + Dagger/Sword)
    Based on MetaBattle priority order:
    1. Lively Lute (off cooldown with 3 notes)
    2. Deafening Drum (spend extra notes for damage/CC)
    3. Tale of the Soulkeeper (off cooldown, cast while Lute playing with 1-0 notes)
    4. Flustering Flute + Tale of the Tortured Mastermind (one after the other)
    5. Crescendo (off cooldown, generates 1 note/sec for 5 seconds)
    """
    rotation_count = 0
    rotation_start_time = time.time()
    last_lively_lute_use = 0.0
    last_deafening_drum_use = 0.0
    last_tale_soulkeeper_use = 0.0
    last_flustering_flute_use = 0.0
    last_tale_mastermind_use = 0.0
    last_crescendo_use = 0.0
    last_auto_attack = 0.0
    last_blink_use = 0.0
    last_signet_ether_use = 0.0
    last_tale_queen_use = 0.0
    last_harp_use = 0.0            # Harmonious Harp (F5, key 4)
    last_weapon_swap = time.time() # Track manual Tab swaps to get Dagger/Sword set
    last_instrument_cast = 0.0     # Any F-skill style instrument cast (Lute/Flute/Crescendo/Drum/Harp/Queen)
    weapon_skill_count = 0         # Count weapon skills used since last swap
    last_weapon_skill_use = {
        'spear_2': 0.0,
        'spear_4': 0.0,
        'spear_5': 0.0,
        'dagger_2': 0.0,
        'dagger_3': 0.0,
        'dagger_5': 0.0,
    }
    # Pixels often remain bright for a loop or two after a successful cast. Trusting
    # only the pixel causes repeated Spear 2 / Spear 5 / Dagger 5 spam. These are
    # deliberately conservative recast guards, not exact GW2 cooldown modelling.
    WEAPON_INTERNAL_COOLDOWNS = {
        'spear_2': 2.5,
        'spear_4': 2.5,
        'spear_5': 2.5,
        'dagger_2': 2.5,
        'dagger_3': 2.5,
        'dagger_5': 2.5,
    }
    WEAPON_SWAP_INTERVAL = 8.0     # Swap weapons every 8 seconds
    WEAPON_SKILLS_PER_SWAP = 4    # Or after 4 weapon skills used
    
    # Initialize weapon set tracker
    weapon_tracker = WeaponSetTracker()
    
    # Track note generation (0-3 notes max)
    # Note generation sources:
    # - Tale of the Soulkeeper: generates 2 notes when cast while Lute is playing (1 note otherwise)
    # - Flustering Flute + Tale of Tortured Mastermind: generates 1 note
    # - Crescendo: generates 1 note per second for 5 seconds
    # Note consumption:
    # - Lively Lute: consumes 3 notes (cast when we have 3 notes)
    # - Deafening Drum: consumes 1 note
    crescendo_active = False
    crescendo_start_time = 0.0
    crescendo_last_note_time = 0.0
    crescendo_starting_notes = 0  # Track notes when Crescendo was cast
    estimated_notes = 0  # Track estimated note count (0-3)
    
    while not stop_event.is_set():
        rotation_count += 1
        current_time = time.time()
        
        if check_stop_condition(stop_event): break
        
        # Check all skill cooldowns
        lively_lute_ready = check_skill_available(DEFAULT_COORDS['instrument_1'])
        flustering_flute_ready = check_skill_available(DEFAULT_COORDS['instrument_2'])
        # Drum needs lower threshold - try 200 instead of 300
        deafening_drum_ready = check_skill_available(DEFAULT_COORDS['instrument_3'], threshold=200)
        harmonious_harp_ready = check_skill_available(DEFAULT_COORDS['instrument_4'])
        # Crescendo's icon reads dimmer than the other instruments in the logs; default
        # threshold=300 kept it False for the entire run, so it never even tried to cast.
        crescendo_ready = check_skill_available(DEFAULT_COORDS['instrument_5'], threshold=40)
        instrument_brightness = {
            'lute_1': get_skill_brightness(DEFAULT_COORDS['instrument_1']),
            'flute_2': get_skill_brightness(DEFAULT_COORDS['instrument_2']),
            'drum_3': get_skill_brightness(DEFAULT_COORDS['instrument_3']),
            'harp_4': get_skill_brightness(DEFAULT_COORDS['instrument_4']),
            'crescendo_5': get_skill_brightness(DEFAULT_COORDS['instrument_5']),
        }
        tale_soulkeeper_ready = check_skill_available(DEFAULT_COORDS['utility_1'])
        tale_mastermind_ready = check_skill_available(DEFAULT_COORDS['utility_2'])
        blink_ready = check_skill_available(DEFAULT_COORDS['utility_3'])
        signet_ether_ready = check_skill_available(DEFAULT_COORDS['utility_heal'])
        tale_queen_ready = check_skill_available(DEFAULT_COORDS['utility_elite'])
        
        # Calculate time since last uses
        time_since_lively_lute = current_time - last_lively_lute_use if last_lively_lute_use > 0 else 999.0
        time_since_deafening_drum = current_time - last_deafening_drum_use if last_deafening_drum_use > 0 else 999.0
        time_since_tale_soulkeeper = current_time - last_tale_soulkeeper_use if last_tale_soulkeeper_use > 0 else 999.0
        time_since_flustering_flute = current_time - last_flustering_flute_use if last_flustering_flute_use > 0 else 999.0
        time_since_tale_mastermind = current_time - last_tale_mastermind_use if last_tale_mastermind_use > 0 else 999.0
        time_since_crescendo = current_time - last_crescendo_use if last_crescendo_use > 0 else 999.0
        time_since_auto_attack = current_time - last_auto_attack if last_auto_attack > 0 else 999.0
        time_since_blink = current_time - last_blink_use if last_blink_use > 0 else 999.0
        time_since_signet_ether = current_time - last_signet_ether_use if last_signet_ether_use > 0 else 999.0
        time_since_tale_queen = current_time - last_tale_queen_use if last_tale_queen_use > 0 else 999.0
        time_since_harp = current_time - last_harp_use if last_harp_use > 0 else 999.0
        time_since_weapon_swap = current_time - last_weapon_swap if last_weapon_swap > 0 else 999.0
        time_since_instrument = current_time - last_instrument_cast if last_instrument_cast > 0 else 999.0
        
        # Track Crescendo active state (generates 1 note/sec for 5 seconds)
        # Crescendo generates exactly 1 note per second for 5 seconds (total 5 notes, but capped at 3 max notes)
        if crescendo_active:
            elapsed = current_time - crescendo_start_time
            if elapsed > 5.0:
                # Crescendo finished after 5 seconds
                crescendo_active = False
                log_and_print('debug', f"Crescendo finished - elapsed: {elapsed:.1f}s, final notes: {estimated_notes}/3")
            else:
                # Generate 1 note every second while Crescendo is active (up to 5 seconds)
                if (current_time - crescendo_last_note_time) >= 1.0:
                    estimated_notes = min(estimated_notes + 1, 3)  # Cap at 3 notes max
                    crescendo_last_note_time = current_time
                    log_and_print('debug', f"Crescendo note generated at {elapsed:.1f}s - notes now: {estimated_notes}/3")
        
        # Check for pause
        wait_if_paused()
        if check_stop_condition(stop_event): break
        
        # Check weapon skills for logging
        # Check weapon skills first, then validate weapon set using tracker
        weapon_2_ready = check_skill_available(DEFAULT_COORDS['weapon_2'], threshold=40)
        weapon_3_ready = check_skill_available(DEFAULT_COORDS['weapon_3'], threshold=40)
        weapon_4_ready = check_skill_available(DEFAULT_COORDS['weapon_4'], threshold=40)
        weapon_5_ready = check_skill_available(DEFAULT_COORDS['weapon_5'], threshold=40)
        weapon_brightness = {
            'weapon_2': get_skill_brightness(DEFAULT_COORDS['weapon_2']),
            'weapon_3': get_skill_brightness(DEFAULT_COORDS['weapon_3']),
            'weapon_4': get_skill_brightness(DEFAULT_COORDS['weapon_4']),
            'weapon_5': get_skill_brightness(DEFAULT_COORDS['weapon_5']),
        }
        
        # Validate weapon set using tracker (uses skill cooldowns and explicit swaps)
        current_weapon_set = weapon_tracker.validate_with_cooldowns(weapon_2_ready, weapon_3_ready, weapon_4_ready, weapon_5_ready)
        
        # Internal weapon cooldown gates. Pixel readiness alone is not enough; several
        # GW2 icons stay bright for a couple loops after the cast was accepted.
        weapon_internal_ready = {
            name: (current_time - last_time) >= WEAPON_INTERNAL_COOLDOWNS[name]
            for name, last_time in last_weapon_skill_use.items()
        }

        # Log current state (standard debug output)
        log_and_print('info', f"--- LOOP {rotation_count} ---")
        log_and_print('info', f"Instruments: Lively Lute(1)={lively_lute_ready} Flustering Flute(2)={flustering_flute_ready} Deafening Drum(3)={deafening_drum_ready} Harmonious Harp(4)={harmonious_harp_ready} Crescendo(5)={crescendo_ready} brightness={instrument_brightness}")
        log_and_print('info', f"Utilities: Tale Soulkeeper={tale_soulkeeper_ready} Tale Mastermind={tale_mastermind_ready} Blink={blink_ready} Signet Ether={signet_ether_ready} Tale Queen={tale_queen_ready}")
        weapon_set_name = "Dagger/Sword" if current_weapon_set == 'dagger_sword' else "Spear"
        log_and_print('info', f"Weapon Set: {weapon_set_name} | Skills: 2={weapon_2_ready} 3={weapon_3_ready} 4={weapon_4_ready} 5={weapon_5_ready} brightness={weapon_brightness} internal_ready={weapon_internal_ready}")
        log_and_print('info', f"Estimated Notes: {estimated_notes}/3 Crescendo Active: {crescendo_active}")
        log_and_print('info', f"Time since: Lively Lute={time_since_lively_lute:.1f}s Deafening Drum={time_since_deafening_drum:.1f}s Tale Soulkeeper={time_since_tale_soulkeeper:.1f}s Crescendo={time_since_crescendo:.1f}s Harp={time_since_harp:.1f}s LastInstrument={time_since_instrument:.1f}s WeaponSwap={time_since_weapon_swap:.1f}s Signet Ether={time_since_signet_ether:.1f}s")
        
        # Periodic weapon swap logic to rotate between Spear and Dagger/Sword.
        # This belongs before ALL cast priorities. Instruments/utilities also `continue`,
        # so putting this below them still lets the swap timer drift to 15-20s.
        should_swap = False
        swap_reason = ""
        if time_since_weapon_swap >= WEAPON_SWAP_INTERVAL:
            should_swap = True
            swap_reason = f"{time_since_weapon_swap:.1f}s elapsed"
        elif weapon_skill_count >= WEAPON_SKILLS_PER_SWAP:
            should_swap = True
            swap_reason = f"{weapon_skill_count} weapon skills used"

        if should_swap and time_since_weapon_swap > 2.0:
            log_and_print('info', f">>> WEAPON SWAP: {swap_reason}, swapping to alternate set (Tab)")
            press_and_release('tab', delay=0.05)
            last_weapon_swap = current_time
            weapon_skill_count = 0
            weapon_tracker.swap()
            time.sleep(0.5)
            if check_stop_condition(stop_event): break
            continue

        # Priority 1: Lively Lute (off cooldown with 3 notes)
        # Per MetaBattle: "Always cast Lively Lute off cooldown with three notes"
        # Only cast if we have 3 notes and haven't used it recently
        # Lively Lute generates 1 note when cast, so after consuming 3, we get 1 back
        if lively_lute_ready and estimated_notes >= 3 and time_since_lively_lute > 0.5 and time_since_instrument > 0.5:
            log_and_print('info', ">>> PRIORITY 2: Lively Lute (key 1) - casting with 3 notes")
            button_mash('1', presses=3, delay=0.05)
            last_lively_lute_use = current_time
            last_instrument_cast = current_time
            estimated_notes = 1  # Consumes 3 notes, generates 1 note back
            time.sleep(0.6)  # Wait for cast to start
            wait_until_on_cooldown(DEFAULT_COORDS['instrument_1'], timeout_seconds=2.5)
            time.sleep(0.3)  # Extra buffer after cooldown confirmed
            if check_stop_condition(stop_event): break
            continue
        
        # Priority 3: Tale of the Soulkeeper (off cooldown, cast while Lute playing with 1-0 notes)
        # Per MetaBattle: "Cast Tale of the Soulkeeper off cooldown for boons. You should always cast it with the Lute playing, and 1 or 0 notes, as it generates 2 notes when cast while the Lute is playing."
        # We'll cast it when ready and we have 0-1 notes (or if Lute is ready to play)
        if tale_soulkeeper_ready and estimated_notes <= 1 and time_since_tale_soulkeeper > 0.5:
            log_and_print('info', ">>> PRIORITY 3: Tale of the Soulkeeper (NumPad7) - casting for boons and note generation")
            button_mash(key_mapping['numpad7'], presses=3, delay=0.05)
            last_tale_soulkeeper_use = current_time
            # Generates 2 notes when cast while Lute is playing
            if lively_lute_ready or time_since_lively_lute < 5.0:
                estimated_notes = min(estimated_notes + 2, 3)
            else:
                estimated_notes = min(estimated_notes + 1, 3)  # Still generates 1 note if Lute not playing
            time.sleep(0.5)  # Wait for cast to start
            wait_until_on_cooldown(DEFAULT_COORDS['utility_1'], timeout_seconds=2.5)
            time.sleep(0.3)  # Extra buffer after cooldown confirmed
            if check_stop_condition(stop_event): break
            continue
        
        # Priority 4: Flustering Flute + Tale of the Tortured Mastermind (one after the other)
        # Per MetaBattle: "Cast Flustering Flute and Tale of the Tortured Mastermind one after the other. This generates 1 note."
        # Implementation note:
        #  - Pixel detection on Tale of the Tortured Mastermind can be unreliable (icon is dim),
        #    so we *always* follow Flustering Flute with NumPad8 rather than waiting for a bright pixel.
        #  - This ensures your Tale of the Tortured Mastermind actually fires in real combat.
        # Cast when we need notes (0-2 notes) to build to 3 for Lively Lute
        if flustering_flute_ready and estimated_notes <= 2 and time_since_flustering_flute > 0.5 and time_since_instrument > 0.5:
            log_and_print('info', ">>> PRIORITY 4: Flustering Flute + Tale of the Tortured Mastermind (combo)")
            # Cast Flustering Flute first
            log_and_print('info', "  Casting Flustering Flute (key 2)")
            button_mash('2', presses=3, delay=0.05)
            last_flustering_flute_use = current_time
            last_instrument_cast = current_time
            time.sleep(0.5)  # Wait for Flute cast to start
            wait_until_on_cooldown(DEFAULT_COORDS['instrument_2'], timeout_seconds=2.5)
            time.sleep(0.2)  # Brief pause before next cast
            if check_stop_condition(stop_event): break
            
            # Then blindly cast Tale of the Tortured Mastermind on NumPad8
            log_and_print('info', "  Casting Tale of the Tortured Mastermind (NumPad8)")
            button_mash(key_mapping['numpad8'], presses=3, delay=0.05)
            last_tale_mastermind_use = current_time
            estimated_notes = min(estimated_notes + 1, 3)  # Generates 1 note from the combo
            time.sleep(0.5)  # Wait for Tale cast to start
            wait_until_on_cooldown(DEFAULT_COORDS['utility_2'], timeout_seconds=2.5)
            time.sleep(0.3)  # Extra buffer after cooldown confirmed
            if check_stop_condition(stop_event): break
            continue
        
        # Priority 5: Deafening Drum (spend extra notes for damage/CC)
        # Per MetaBattle / Snow Crows: "Spend extra notes on Deafening Drum for damage and crowd control"
        # Cast whenever ready and we have 2+ notes - don't block it, let it fire to generate more notes
        # Fallback: If pixel check fails but it's been a while, try firing anyway
        drum_coords = DEFAULT_COORDS['instrument_3']
        drum_color_check = pixel_get_color(drum_coords[0], drum_coords[1])
        drum_is_not_black = drum_color_check is not None and drum_color_check != (0, 0, 0)
        # Use pixel check OR (not black AND enough time has passed)
        drum_should_fire = deafening_drum_ready or (drum_is_not_black and time_since_deafening_drum > 8.0)
        
        if ENABLE_DETAILED_LOGGING or (estimated_notes >= 2):
            log_and_print('info', f"[DRUM DEBUG] pixel_ready={deafening_drum_ready}, not_black={drum_is_not_black}, should_fire={drum_should_fire}, notes={estimated_notes}, time_since={time_since_deafening_drum:.1f}s, time_since_instrument={time_since_instrument:.1f}s, crescendo_active={crescendo_active}")
        
        # Cooldown requirement to prevent too rapid casting
        if drum_should_fire and estimated_notes >= 2 and time_since_deafening_drum > 0.5 and time_since_instrument > 0.5 and not crescendo_active:
            log_and_print('info', ">>> PRIORITY 5: Deafening Drum (key 3) - spending notes for damage/CC")
            button_mash('3', presses=3, delay=0.05)
            last_deafening_drum_use = current_time
            last_instrument_cast = current_time
            estimated_notes = max(estimated_notes - 1, 0)  # Consumes 1 note
            time.sleep(0.5)  # Wait for cast to start
            # Wait for the skill to go on cooldown (pixel goes dark) and ensure cast completes
            wait_until_on_cooldown(DEFAULT_COORDS['instrument_3'], timeout_seconds=2.5)
            time.sleep(0.3)  # Extra buffer after cooldown confirmed
            if check_stop_condition(stop_event): break
            continue
        
        # Priority 6: Harmonious Harp (F5, key 4) - amplify active instruments
        recent_instrument_playing = (
            time_since_lively_lute < 8.0
            or time_since_flustering_flute < 8.0
            or time_since_deafening_drum < 8.0
            or crescendo_active
        )
        if harmonious_harp_ready and time_since_harp > HARMONIOUS_HARP_COOLDOWN and time_since_instrument > 0.5 and recent_instrument_playing:
            log_and_print('info', ">>> PRIORITY 6: Harmonious Harp (key 4) - amplifying instruments")
            button_mash('4', presses=2, delay=0.05)
            last_harp_use = current_time
            last_instrument_cast = current_time
            time.sleep(0.5)  # Wait for cast to start
            wait_until_on_cooldown(DEFAULT_COORDS['instrument_4'], timeout_seconds=2.5)
            time.sleep(0.3)  # Extra buffer after cooldown confirmed
            if check_stop_condition(stop_event): break
            continue
        
        # Priority 7: Tale of the August Queen (elite) - activates all instruments
        # Per MetaBattle / Snow Crows: "Tale of the August Queen activates all instruments, activating Symphonic Resonance and Fortissimo"
        # Use sparingly in a DPS loop (long cooldown) rather than on every recharge tick.
        # Use it reasonably often for DPS (approx every 40 seconds) while instruments are actually doing work.
        if tale_queen_ready and time_since_tale_queen > 40.0 and time_since_instrument > 0.5 and (lively_lute_ready or flustering_flute_ready or crescendo_active):
            log_and_print('info', ">>> PRIORITY 7: Tale of the August Queen (NumPad0) - elite skill")
            button_mash(key_mapping['numpad0'], presses=3, delay=0.05)
            last_tale_queen_use = current_time
            last_instrument_cast = current_time
            time.sleep(0.6)  # Wait for cast to start
            wait_until_on_cooldown(DEFAULT_COORDS['utility_elite'], timeout_seconds=2.5)
            time.sleep(0.3)  # Extra buffer after cooldown confirmed
            if check_stop_condition(stop_event): break
            continue
        
        # Priority 8: Crescendo (off cooldown, generates 1 note/sec for 5 seconds)
        # Per Snow Crows: "Cast F1 and F5 whenever they Recharged" but "have them playing in the background for your next F5"
        # Burst rotation shows: Drum → Lute → Flute → Crescendo
        # We cast other instruments first, then Crescendo when instruments are active
        # Count how many instruments are ready or recently cast (within 8 seconds)
        active_instruments = 0
        if time_since_lively_lute < 8.0:
            active_instruments += 1
        if time_since_flustering_flute < 8.0:
            active_instruments += 1
        if time_since_harp < 8.0:
            active_instruments += 1
        if time_since_deafening_drum < 8.0:
            active_instruments += 1
        
        # Require at least 2 instruments to be ready/active before casting Crescendo
        has_multiple_instruments = active_instruments >= 2
        
        # Don't cast Crescendo when at max notes (3) - spend notes first (Drum/Lute) to avoid wasting note generation
        # Cast off cooldown - only wait if it's currently active (5s duration)
        if crescendo_ready and not crescendo_active and estimated_notes < 3 and time_since_instrument > 0.5 and has_multiple_instruments:
            log_and_print('info', f">>> PRIORITY 8: Crescendo (key 5) - casting for boons and note generation (current notes: {estimated_notes}/3)")
            button_mash('5', presses=3, delay=0.05)
            last_crescendo_use = current_time
            last_instrument_cast = current_time
            crescendo_active = True
            crescendo_start_time = current_time
            crescendo_last_note_time = current_time
            crescendo_starting_notes = estimated_notes  # Track starting note count
            time.sleep(0.6)  # Wait for cast to start
            wait_until_on_cooldown(DEFAULT_COORDS['instrument_5'], timeout_seconds=2.5)
            time.sleep(0.3)  # Extra buffer after cooldown confirmed
            if check_stop_condition(stop_event): break
            continue
        
        # Priority 9: Signet of the Ether (heal) - resets Phantasm skills
        # Per MetaBattle: "Signet of the Ether, an offensive heal that resets your Phantasm skills for much higher burst damage"
        # Default: OFF for pure DPS golem benchmarks; toggle USE_SIGNET_IN_ROTATION if you want it.
        if USE_SIGNET_IN_ROTATION and signet_ether_ready and time_since_signet_ether > 20.0:
            log_and_print('info', ">>> PRIORITY 9: Signet of the Ether (NumPad6) - heal and resets Phantasm skills")
            button_mash(key_mapping['numpad6'], presses=3, delay=0.05)
            last_signet_ether_use = current_time
            time.sleep(0.5)
            wait_until_on_cooldown(DEFAULT_COORDS['utility_heal'], timeout_seconds=1.5)
            if check_stop_condition(stop_event): break
            continue
        
        # Priority 10: Weapon-set skills (use damage skills off cooldown)
        # Weapon skills should be used for damage between instrument/utility cooldowns
        # Instruments are higher priority (1-8), so they'll fire first when available
        # Weapon skills fill gaps when instruments are on cooldown
        if current_weapon_set == 'spear':
            # MetaBattle: Mind the Gap first for Clarity, then use empowered spear skills,
            # especially Phantasmal Lancer. Imaginary Inversion is defensive/cleanse,
            # so we don't spam Spear 3 here.
            if weapon_2_ready and weapon_internal_ready['spear_2']:
                log_and_print('info', ">>> PRIORITY 10: Spear 2 / Mind the Gap (NumPad2)")
                button_mash(key_mapping['numpad2'], presses=2, delay=0.05)
                last_weapon_skill_use['spear_2'] = current_time
                weapon_tracker.update_from_skill_use('spear_2')
                weapon_skill_count += 1
                time.sleep(0.35)
                if check_stop_condition(stop_event): break
                continue

            if weapon_5_ready and weapon_internal_ready['spear_5']:
                log_and_print('info', ">>> PRIORITY 10: Spear 5 / Phantasmal Lancer (NumPad5)")
                button_mash(key_mapping['numpad5'], presses=2, delay=0.05)
                last_weapon_skill_use['spear_5'] = current_time
                weapon_skill_count += 1
                time.sleep(0.35)
                if check_stop_condition(stop_event): break
                continue

            if weapon_4_ready and weapon_internal_ready['spear_4']:
                log_and_print('info', ">>> PRIORITY 10: Spear 4 (NumPad4)")
                button_mash(key_mapping['numpad4'], presses=2, delay=0.05)
                last_weapon_skill_use['spear_4'] = current_time
                weapon_tracker.update_from_skill_use('spear_4')
                weapon_skill_count += 1
                time.sleep(0.35)  # Minimal wait - let next loop check if it went on cooldown
                if check_stop_condition(stop_event): break
                continue
        else:  # dagger_sword
            if weapon_5_ready and weapon_internal_ready['dagger_5']:
                log_and_print('info', ">>> PRIORITY 10: Dagger/Sword 5 (NumPad5)")
                button_mash(key_mapping['numpad5'], presses=2, delay=0.05)
                last_weapon_skill_use['dagger_5'] = current_time
                weapon_tracker.update_from_skill_use('dagger_5')
                weapon_skill_count += 1
                time.sleep(0.35)  # Minimal wait - let next loop check if it went on cooldown
                if check_stop_condition(stop_event): break
                continue
            
            if weapon_2_ready and weapon_internal_ready['dagger_2']:
                log_and_print('info', ">>> PRIORITY 10: Dagger/Sword 2 (NumPad2)")
                button_mash(key_mapping['numpad2'], presses=2, delay=0.05)
                last_weapon_skill_use['dagger_2'] = current_time
                weapon_tracker.update_from_skill_use('dagger_2')
                weapon_skill_count += 1
                time.sleep(0.35)
                if check_stop_condition(stop_event): break
                continue
            
            if weapon_3_ready and weapon_internal_ready['dagger_3']:
                log_and_print('info', ">>> PRIORITY 10: Dagger/Sword 3 (NumPad3)")
                button_mash(key_mapping['numpad3'], presses=2, delay=0.05)
                last_weapon_skill_use['dagger_3'] = current_time
                weapon_tracker.update_from_skill_use('dagger_3')
                weapon_skill_count += 1
                time.sleep(0.35)
                if check_stop_condition(stop_event): break
                continue
        
        # Priority 10: Blink (mobility/stunbreak) - only if really needed
        # Per MetaBattle: "Blink as a generic stun break and mobility skill"
        # Default: OFF for pure DPS golem benchmarks; toggle USE_BLINK_IN_ROTATION if you want it.
        if USE_BLINK_IN_ROTATION and blink_ready and time_since_blink > 30.0:
            log_and_print('info', ">>> PRIORITY 9: Blink (NumPad9) - mobility/stunbreak")
            button_mash(key_mapping['numpad9'], presses=3, delay=0.05)
            last_blink_use = current_time
            time.sleep(0.3)
            wait_until_on_cooldown(DEFAULT_COORDS['utility_3'], timeout_seconds=1.5)
            if check_stop_condition(stop_event): break
            continue
        
        # Filler: Auto-attack
        # Use when no other skills are ready
        if time_since_auto_attack > 1.0:
            log_and_print('debug', "Using auto-attack (NumPad1)")
            button_mash(key_mapping['numpad1'], presses=2, delay=0.05)
            last_auto_attack = current_time
            time.sleep(0.4)
            if check_stop_condition(stop_event): break
        
        # Small delay before next check
        time.sleep(0.1)

def run(stop_event):
    """
    Main entry point for Power Troubadour spec
    Hold numpad1 to activate the rotation
    """
    logger.info("Power Troubadour (Spear + Dagger/Sword) spec started")
    log_and_print('info', "=" * 70)
    log_and_print('info', "POWER TROUBADOUR - SPEAR + DAGGER/SWORD BUILD")
    log_and_print('info', "Hold NumPad1 to run rotation")
    log_and_print('info', "=" * 70)
    
    while not stop_event.is_set():
        if stop_event.is_set():
            logger.info("Stop event detected")
            break
        
        if keyboard.is_pressed(key_mapping['numpad1']):
            log_and_print('info', "NumPad1 pressed - starting rotation")
            power_troubadour_rotation(stop_event)
        
        time.sleep(0.05)
    
    logger.info("Power Troubadour spec ended")

