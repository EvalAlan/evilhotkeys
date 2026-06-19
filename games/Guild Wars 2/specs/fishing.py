"""
Fishing - Automated GW2 Fishing Bot for Guild Wars 2
Based on: https://www.elitepvpers.com/forum/guild-wars-2/5013886-fishing-bot.html

State machine:
  IDLE -> EQUIP -> CAST -> WAIT_FOR_BITE -> REEL -> repeat

Pixel detection uses color-tolerance matching (not exact RGB) to handle
different biomes, lighting, and gamma settings.

Coordinates are for triple-monitor 1080p (5760x1080 virtual desktop).
Adjust FISHING_*_COORDS if your layout differs.
"""

import sys
import time
import keyboard
from libs.pixel_get_color import get_color as pixel_get_color
from libs.keyboard_actions import press_and_release, press, release
from libs.key_mapping import key_mapping
from libs.logger import get_logger
from libs.pause import wait_if_paused

logger = get_logger('fishing')
logger.propagate = True

ENABLE_DETAILED_LOGGING = True  # Disable after validation


def log_and_print(level, msg):
    """Log and optionally print for debugging."""
    if level in ('error', 'warning') or ENABLE_DETAILED_LOGGING:
        getattr(logger, level)(msg)
        if ENABLE_DETAILED_LOGGING:
            print(f"[{level.upper()}] {msg}", flush=True)
            sys.stdout.flush()


# ──────────────────────────────────────────────────────────────────────
# Pixel coordinates (triple 1080p — adjust for your layout)
#
# These cover the fishing interaction UI:
#   - CATCH_INDICATOR: the red/pink "bite" flash — region (2770, 328) to (2985, 485)
#   - REEL_GREEN: the green zone in the fishing reel mini-game bar — region (2745, 802) to (3020, 825)
#   - REEL_ORANGE: the orange "fish" block you chase in the reel mini-game — same region
# ──────────────────────────────────────────────────────────────────────
CATCH_INDICATOR_COORDS = (2877, 353)      # center of the bite flash region (y=353 from bite detection)
REEL_GREEN_COORDS = (2882, 813)           # center of the green reel zone
REEL_ORANGE_COORDS = (2882, 813)          # same region — we look for orange vs green

# Search regions for pixel_search-style detection (fallback)
CATCH_REGION = (2770, 328, 2985, 485)     # (x1, y1, x2, y2) — WAIT_FOR_BITE
REEL_REGION = (2745, 802, 3020, 825)      # reel bar region — REEL actions

# ──────────────────────────────────────────────────────────────────────
# Color targets and tolerances
# ──────────────────────────────────────────────────────────────────────
CATCH_TARGET_COLOR = (188, 69, 112)      # bright pink/red bite flash (tuned from detected bite)
CATCH_TOLERANCE = 50                       # generous — different biomes vary

REEL_GREEN_TARGET = (129, 220, 101)       # green reel zone (empirical)
REEL_GREEN_TOLERANCE = 40

REEL_ORANGE_TARGET = (242, 212, 90)       # bright orange/yellow fish marker; dark brown body matches too much UI
REEL_ORANGE_TOLERANCE = 35

# Bobber detection — the bobber is a bright white/blue dot on water
BOBBER_TARGET_COLOR = (200, 210, 220)
BOBBER_TOLERANCE = 50

# ──────────────────────────────────────────────────────────────────────
# Keybinds
# ──────────────────────────────────────────────────────────────────────
FISHING_MODE_KEY = 'j'                                  # open/equip fishing mode/tool
FISHING_ROD_KEY = key_mapping.get('numpad2', 80)         # switches/equips fishing rod after mounting
INTERACT_KEY = key_mapping.get('numpad1', 79)            # cast/recast/hook
MOUNT_SKIMMER_KEY = key_mapping.get('f8', 'f8')          # sends Alt+Shift+K
MOUNT_SKIFF_KEY = key_mapping.get('f9', 'f9')            # dismount skimmer, then sends Ctrl+Shift+K

# ──────────────────────────────────────────────────────────────────────
# Timing constants
# ──────────────────────────────────────────────────────────────────────
CAST_DELAY = 2.5          # wait after pressing "Begin Fishing" for the cast animation
BITE_CHECK_INTERVAL = 0.1 # how often to check for a bite
REEL_CHECK_INTERVAL = 0.05
REEL_TIMEOUT = 60.0       # max seconds to chase fish before giving up; hard catches can run long
EQUIP_DELAY = 2.5         # wait after equipping fishing rod
LOOP_DELAY = 0.5          # delay between fishing attempts


def check_stop_condition(stop_event):
    """Return True if we should stop."""
    return stop_event.is_set()


def colors_close(color, target, tolerance):
    """Check if two colors are within tolerance of each other."""
    if color is None:
        return False
    return all(abs(c - t) <= tolerance for c, t in zip(color, target))


def detect_catch_indicator():
    """Check if the catch indicator is showing (fish is biting)."""
    color = pixel_get_color(*CATCH_INDICATOR_COORDS)
    if color is None:
        return False
    return colors_close(color, CATCH_TARGET_COLOR, CATCH_TOLERANCE)


def detect_bobber_present():
    """Check if the bobber is visible on screen."""
    color = pixel_get_color(*CATCH_INDICATOR_COORDS)
    if color is None:
        return False
    brightness = sum(color)
    # Bobber is bright; water is dark. If brightness is high, bobber is out.
    return brightness > 100


def detect_reel_green():
    """Check if we're in the green zone of the reel mini-game."""
    color = pixel_get_color(*REEL_GREEN_COORDS)
    if color is None:
        return False
    return colors_close(color, REEL_GREEN_TARGET, REEL_GREEN_TOLERANCE)


def detect_reel_orange():
    """Check if the orange fish block is visible in the reel mini-game."""
    color = pixel_get_color(*REEL_ORANGE_COORDS)
    if color is None:
        return False
    return colors_close(color, REEL_ORANGE_TARGET, REEL_ORANGE_TOLERANCE)


def get_reel_positions():
    """Get approximate x-positions of green zone and orange block in the reel bar.

    The green zone is not reliably on the vertical centerline. In screenshots it
    often lives in the upper half of the reel region while the orange fish block
    crosses the centerline, so scan the whole rectangle and return bbox centers.
    Returns (green_x, orange_x) or (None, None).
    """
    x1, y1, x2, y2 = REEL_REGION

    green_points = []
    orange_points = []

    try:
        from PIL import ImageGrab
        image = ImageGrab.grab(bbox=(x1, y1, x2, y2))
        if image is not None:
            image = image.convert('RGB')
            for local_y in range(0, y2 - y1, 2):
                for local_x in range(0, x2 - x1, 2):
                    color = image.getpixel((local_x, local_y))
                    screen_x = x1 + local_x
                    if colors_close(color, REEL_GREEN_TARGET, REEL_GREEN_TOLERANCE):
                        green_points.append(screen_x)
                    if colors_close(color, REEL_ORANGE_TARGET, REEL_ORANGE_TOLERANCE):
                        orange_points.append(screen_x)
    except Exception as exc:
        log_and_print('warning', f"Reel screenshot scan failed, falling back to point scan: {exc}")
        for y in range(y1, y2, 2):
            for x in range(x1, x2, 2):
                color = pixel_get_color(x, y)
                if color is None:
                    continue
                if colors_close(color, REEL_GREEN_TARGET, REEL_GREEN_TOLERANCE):
                    green_points.append(x)
                if colors_close(color, REEL_ORANGE_TARGET, REEL_ORANGE_TOLERANCE):
                    orange_points.append(x)

    green_x = (min(green_points) + max(green_points)) // 2 if green_points else None
    orange_x = (min(orange_points) + max(orange_points)) // 2 if orange_points else None

    if ENABLE_DETAILED_LOGGING:
        log_and_print('debug',
            f"Reel scan: green_x={green_x} matches={len(green_points)} | "
            f"orange_x={orange_x} matches={len(orange_points)}"
        )

    return green_x, orange_x


def pixel_search_in_region(color, x1, y1, x2, y2, tolerance=0):
    """Search for a color in a region with tolerance.
    
    This is a fallback for when single-point detection isn't enough.
    Uses PIL directly to avoid the exact-match limitation of pixel_search.
    """
    try:
        from PIL import ImageGrab
        image = ImageGrab.grab(bbox=(x1, y1, x2, y2))
        if image is None:
            return None
        
        pixels = list(image.getdata())
        width = x2 - x1
        
        for i, pixel in enumerate(pixels):
            if tolerance == 0:
                if pixel[:3] == color:
                    y, x = divmod(i, width)
                    return (x1 + x, y1 + y)
            else:
                r, g, b = pixel[:3]
                if (abs(r - color[0]) <= tolerance and
                    abs(g - color[1]) <= tolerance and
                    abs(b - color[2]) <= tolerance):
                    y, x = divmod(i, width)
                    return (x1 + x, y1 + y)
        return None
    except Exception as e:
        log_and_print('error', f"pixel_search_in_region failed: {e}")
        return None


def fishing_rotation(stop_event, equip_rod=True):
    """Main fishing state machine.
    
    States:
      1. EQUIP — press key to equip fishing rod
      2. CAST — press key to cast the line
      3. WAIT_FOR_BITE — loop checking for the catch indicator
      4. REEL — interact + chase the orange block into the green zone
    """
    # Step 1: Optionally equip fishing rod
    if equip_rod:
        # After mounting, GW2 needs the fishing mode/tool key first, then the
        # rod/weapon swap key. The macro runner may consume the physical start
        # key, so synthesize both game inputs explicitly.
        log_and_print('info', "Equipping fishing mode via J...")
        press_and_release(FISHING_MODE_KEY)
        time.sleep(0.4)
        if check_stop_condition(stop_event):
            return

        log_and_print('info', "Switching to fishing rod via NumPad2...")
        press(FISHING_ROD_KEY)
        release(FISHING_ROD_KEY)
        time.sleep(EQUIP_DELAY)
        if check_stop_condition(stop_event):
            return
    else:
        log_and_print('debug', "Skipping fishing rod equip — starting from current equipment")

    # Step 2: Cast the line
    log_and_print('info', "Casting fishing line...")
    interact_key = INTERACT_KEY
    press(interact_key)
    release(interact_key)
    time.sleep(CAST_DELAY)
    if check_stop_condition(stop_event):
        return

    # Step 3: Wait for bite
    log_and_print('info', "Waiting for bite...")
    bite_detected = False
    wait_start = time.time()
    max_wait = 30.0  # max seconds to wait before re-casting
    
    while not stop_event.is_set():
        wait_if_paused()
        if stop_event.is_set():
            break
        
        # Check for catch indicator via region search (bite flash moves within region)
        catch_pos = pixel_search_in_region(
            CATCH_TARGET_COLOR,
            CATCH_REGION[0], CATCH_REGION[1], CATCH_REGION[2], CATCH_REGION[3],
            tolerance=CATCH_TOLERANCE
        )
        if catch_pos:
            bite_detected = True
            # Read the actual color from the screenshot for debug
            from PIL import ImageGrab
            img = ImageGrab.grab(bbox=(CATCH_REGION[0], CATCH_REGION[1], CATCH_REGION[2], CATCH_REGION[3]))
            if img:
                dx = catch_pos[0] - CATCH_REGION[0]
                dy = catch_pos[1] - CATCH_REGION[1]
                actual_color = img.getpixel((dx, dy))[:3]
                log_and_print('info', f"BITE DETECTED at {catch_pos}! actual_color={actual_color}")
            else:
                log_and_print('info', f"BITE DETECTED at {catch_pos}!")
            break
        
        elapsed = time.time() - wait_start
        if elapsed > max_wait:
            log_and_print('info', f"No bite after {max_wait}s — re-casting...")
            break
        
        if ENABLE_DETAILED_LOGGING and int(elapsed * 10) % 10 == 0:  # log every ~1s
            color = pixel_get_color(*CATCH_INDICATOR_COORDS)
            log_and_print('debug', f"  waiting... {elapsed:.1f}s | pixel={color}")
        
        time.sleep(BITE_CHECK_INTERVAL)
    
    if not bite_detected and not stop_event.is_set():
        # Timed out — re-cast
        return
    
    if stop_event.is_set():
        return

    # Step 4: Press interact to hook the fish
    log_and_print('info', "Hooking fish — pressing interact...")
    press(interact_key)
    release(interact_key)
    time.sleep(0.5)
    if check_stop_condition(stop_event):
        return

    # Step 5: Reel mini-game — chase the orange block into the green zone
    log_and_print('info', "Starting reel mini-game...")
    reel_start = time.time()
    held_direction = None
    missing_reel_frames = 0
    missing_green_frames = 0
    previous_green_x = None

    REEL_CENTER_DEADBAND = 18       # close enough; avoid twitchy overcorrection
    REEL_LEAD_FACTOR = 3            # velocity lead compensation, px/frame -> px error

    def set_reel_direction(direction):
        """Hold A/D continuously until the controller changes direction."""
        nonlocal held_direction
        if direction == held_direction:
            return
        if held_direction:
            release(held_direction)
        held_direction = direction
        if held_direction:
            press(held_direction)
            log_and_print('debug', f"Holding reel direction: {held_direction.upper()}")
        else:
            log_and_print('debug', "Released reel direction")

    try:
        while not stop_event.is_set():
            wait_if_paused()
            if stop_event.is_set():
                break

            elapsed = time.time() - reel_start
            if elapsed > REEL_TIMEOUT:
                log_and_print('warning', f"Reel timeout after {REEL_TIMEOUT}s — fish escaped")
                break

            # Get positions of green zone and orange block
            green_x, orange_x = get_reel_positions()

            if green_x is None and orange_x is None:
                # Neither found — count a few missing frames before declaring the reel UI gone.
                missing_reel_frames += 1
                log_and_print('debug', f"Neither green nor orange found — missing frame {missing_reel_frames}")
                set_reel_direction(None)
                if missing_reel_frames >= 3:
                    log_and_print('info', "Reel mini-game ended")
                    break
                time.sleep(REEL_CHECK_INTERVAL)
                continue

            missing_reel_frames = 0

            if green_x is None:
                missing_green_frames += 1
                log_and_print('debug', f"Green zone not found, orange at x={orange_x} — missing green frame {missing_green_frames}")
                set_reel_direction(None)
                if missing_green_frames >= 8:
                    log_and_print('info', "Green zone lost for multiple frames — reel mini-game likely ended/failed")
                    break
                time.sleep(REEL_CHECK_INTERVAL)
                continue

            missing_green_frames = 0

            if orange_x is None:
                log_and_print('debug', f"Orange block not found, green at x={green_x}")
                set_reel_direction(None)
                time.sleep(REEL_CHECK_INTERVAL)
                continue

            diff = orange_x - green_x
            green_velocity = 0 if previous_green_x is None else green_x - previous_green_x
            previous_green_x = green_x
            control_error = diff - (green_velocity * REEL_LEAD_FACTOR)

            if ENABLE_DETAILED_LOGGING and int(elapsed * 20) % 5 == 0:
                log_and_print('debug',
                    f"  reel: green_x={green_x} | orange_x={orange_x} | "
                    f"diff={diff} | green_velocity={green_velocity} | control_error={control_error}"
                )

            # Predictive continuous-hold controller. Positive error means the
            # fish is right of the green zone; in GW2 fishing, A moves the green
            # zone right and D moves it left. Velocity lead prevents overshoot.
            if control_error > REEL_CENTER_DEADBAND:
                set_reel_direction('a')
            elif control_error < -REEL_CENTER_DEADBAND:
                set_reel_direction('d')
            else:
                set_reel_direction(None)
                log_and_print('debug',
                    f"Orange centered/controlled (orange_x={orange_x}, green_x={green_x}, "
                    f"control_error={control_error}) — holding steady"
                )

            time.sleep(REEL_CHECK_INTERVAL)
    finally:
        set_reel_direction(None)

    log_and_print('info', "Reel sequence ended. Waiting before next cast...")
    stop_event.wait(LOOP_DELAY)


def run(stop_event):
    """Entry point — two start hotkeys.

    NumPad2: equip/swap to fishing rod, then perform one cast/reel rotation.
    NumPad1: perform one cast/reel rotation without equipping first.
    F8: mount skimmer via Alt+Shift+K.
    F9: dismount skimmer via Alt+Shift+K, then mount skiff via Ctrl+Shift+K.
    Cast/interact: NumPad1 is also used by the bot for cast/hook during that rotation.
    Stop: stop_event set by the macro runner.
    """
    EQUIP_AND_START_KEY = key_mapping.get('numpad2', 'numpad2')
    START_ONLY_KEY = key_mapping.get('numpad1', 'numpad1')

    log_and_print('info', "Fishing bot ready — NumPad2 equips+casts, NumPad1 casts, F8 skimmer, F9 skiff")

    def wait_for_key_release(key):
        while keyboard.is_pressed(key) and not stop_event.is_set():
            stop_event.wait(0.05)

    def send_combo(description, modifiers, key):
        """Send a hotkey using explicit key down/up events.

        keyboard.press_and_release('alt+shift+k') is not reliable for GW2 here,
        so hold modifiers manually, tap the key, then release in reverse order.
        """
        combo = '+'.join([*modifiers, key])
        log_and_print('info', f"{description} — sending {combo}")
        try:
            for modifier in modifiers:
                keyboard.press(modifier)
                time.sleep(0.03)
            keyboard.press(key)
            time.sleep(0.05)
            keyboard.release(key)
        finally:
            for modifier in reversed(modifiers):
                keyboard.release(modifier)
                time.sleep(0.03)
        stop_event.wait(0.2)

    def mount_skimmer():
        send_combo("F8 pressed — mounting skimmer", ['alt', 'shift'], 'k')

    def mount_skiff_from_skimmer():
        send_combo("F9 pressed — dismounting skimmer", ['alt', 'shift'], 'k')
        stop_event.wait(0.6)
        if stop_event.is_set():
            return
        send_combo("F9 pressed — mounting skiff", ['ctrl', 'shift'], 'k')

    while not stop_event.is_set():
        wait_if_paused()
        if stop_event.is_set():
            break

        if keyboard.is_pressed(MOUNT_SKIMMER_KEY):
            wait_for_key_release(MOUNT_SKIMMER_KEY)
            mount_skimmer()

        elif keyboard.is_pressed(MOUNT_SKIFF_KEY):
            wait_for_key_release(MOUNT_SKIFF_KEY)
            mount_skiff_from_skimmer()

        elif keyboard.is_pressed(EQUIP_AND_START_KEY):
            log_and_print('info', "NumPad2 pressed — equipping fishing rod and starting one cast")
            wait_for_key_release(EQUIP_AND_START_KEY)
            try:
                fishing_rotation(stop_event, equip_rod=True)
                log_and_print('info', "Fishing rotation complete — waiting for next NumPad1/NumPad2 cast")
            except Exception as exc:
                log_and_print('error', f"Unexpected error: {exc}")
                raise

        elif keyboard.is_pressed(START_ONLY_KEY):
            log_and_print('info', "NumPad1 pressed — starting one cast without equipping")
            wait_for_key_release(START_ONLY_KEY)
            try:
                fishing_rotation(stop_event, equip_rod=False)
                log_and_print('info', "Fishing rotation complete — waiting for next NumPad1/NumPad2 cast")
            except Exception as exc:
                log_and_print('error', f"Unexpected error: {exc}")
                raise

        stop_event.wait(0.05)
