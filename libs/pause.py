import threading
import keyboard
import time
from libs.config_manager import get_config_manager
from libs.logger import get_logger
from libs.key_mapping import key_mapping

logger = get_logger('pause')
config = get_config_manager()

# Event to manage pause state
pause_event = threading.Event()

# Function to toggle the pause state
def toggle_pause():
    if pause_event.is_set():
        logger.info("Script unpaused")
        print("Script unpaused")
        pause_event.clear()
    else:
        logger.info("Script paused")
        print("Script paused")
        pause_event.set()

# Helper function for specs to wait if paused
def wait_if_paused():
    """Wait while script is paused. Returns immediately if not paused."""
    if pause_event.is_set():
        while pause_event.is_set():
            time.sleep(0.1)  # Small sleep to avoid busy-waiting

def _resolve_hotkey(value):
    """Return a keyboard recognisable hotkey from config value."""
    if value is None:
        return None
    if isinstance(value, int):
        return value

    if isinstance(value, str):
        key = value.strip().lower()
        if key in key_mapping:
            return key_mapping[key]
        return key

    return None


def _pause_listener():
    pause_key_raw = config.get('keybinds.pause', 'end')
    logger.info(f"Pause key configured as: {pause_key_raw}")

    candidates = []
    primary = _resolve_hotkey(pause_key_raw)
    if primary is not None:
        candidates.append(primary)

    # Always register the plain 'end' key as a safety net if not already
    if pause_key_raw is None or str(pause_key_raw).strip().lower() != 'end':
        fallback = _resolve_hotkey('end')
        if fallback is not None:
            candidates.append(fallback)

    if not candidates:
        logger.error("Failed to resolve pause hotkey; defaulting to 'end'")
        candidates = [_resolve_hotkey('end')]

    registered_keys = []
    for candidate in candidates:
        try:
            keyboard.add_hotkey(candidate, toggle_pause, suppress=False, trigger_on_release=False)
            registered_keys.append(candidate)
        except Exception as exc:
            logger.error(f"Failed to register pause hotkey '{candidate}': {exc}")

    if registered_keys:
        logger.info(f"Pause hotkey(s) active: {registered_keys}")
        print(f"Pause hotkey(s) active: {registered_keys}")
    else:
        logger.error("No pause hotkeys registered; pause functionality disabled")

    # Keep the thread alive while listening for pause events
    while True:
        time.sleep(1)

# Start the pause thread
pause_thread = threading.Thread(target=_pause_listener, daemon=True)
pause_thread.start()
