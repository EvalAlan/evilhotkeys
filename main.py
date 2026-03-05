import signal
import sys
import threading
import time
import os
from importlib import import_module
from libs.menu_customization import customize_menu, customize_specs
from libs.environment import get_environment_info
from libs.logger import get_logger
from libs.config_manager import get_config_manager
import libs.pause  # Initialize pause system

logger = get_logger('main')
config = get_config_manager()

# Function to run the spec
def run_spec(selected_game, selected_spec, stop_event):
    try:
        logger.info(f"Running spec '{selected_spec}' for game '{selected_game}'")

        # Import and run the spec
        spec_module = import_module(f'games.{selected_game}.specs.{selected_spec}')
        if hasattr(spec_module, 'run'):
            spec_module.run(stop_event)
        else:
            logger.error(f"Spec '{selected_spec}' for game '{selected_game}' does not have a 'run' function")

    except ModuleNotFoundError as e:
        logger.error(f"Failed to load spec '{selected_spec}' for game '{selected_game}': {e}")
    except AttributeError as e:
        logger.error(f"Spec '{selected_spec}' for game '{selected_game}' encountered an AttributeError: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error running spec '{selected_spec}' for game '{selected_game}': {e}")

# Function to select a game
def select_game():
    games = customize_menu('./games')
    if not games:
        logger.warning("No games available")
        return None

    print("Available games:")
    for i, game in enumerate(games, 1):
        print(f"{i}. {game}")

    while True:
        try:
            selected_index = int(input("Select a game: ")) - 1
            if 0 <= selected_index < len(games):
                return games[selected_index]
            else:
                print("Invalid game selection. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")

# Function to select a spec
def select_spec(selected_game):
    spec_path = os.path.join('./games', selected_game, 'specs')
    specs = [f[:-3] for f in os.listdir(spec_path) if f.endswith('.py') and not f.startswith('__')]

    if selected_game == 'World of Warcraft':
        specs = customize_specs(specs)

    if not specs:
        logger.warning(f"No specs found for {selected_game}")
        return None

    print("Available specs:")
    for i, spec in enumerate(specs, 1):
        print(f"{i}. {spec}")

    while True:
        try:
            selected_index = int(input("Select a spec: ")) - 1
            if 0 <= selected_index < len(specs):
                return specs[selected_index]
            else:
                print("Invalid spec selection. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")

# Signal handler for graceful shutdown
def signal_handler(sig, frame):
    logger.info('\nCtrl+C pressed. Exiting gracefully.')
    stop_event.set()  # Ensure any running spec is stopped
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

stop_event = threading.Event()

# Display environment and configuration information
print("EvilHotKeys - Cross-platform automation tool")
print("=" * 50)

# Show environment info
env_info = get_environment_info()
print(f"Environment: {env_info['desktop']} on {env_info['session_type']}")
if env_info['is_gnome_wayland']:
    if env_info['gnome_screenshot_support']:
        print("✓ GNOME Wayland support detected and available")
    else:
        print("⚠️  GNOME Wayland detected but screenshot support unavailable")
elif env_info['is_wayland']:
    print("⚠️  Wayland detected - using X11 fallback for screenshots")
else:
    print("✓ X11 environment detected")

# Show configuration info
print()
print("Configuration:")
print(f"  Performance Profile: {config.get('performance.profile', 'balanced')}")
print(f"  Cache Duration: {config.get('performance.screenshot_cache_duration', 0.5)}s")
print(f"  Resolution: {config.get('display.resolution', '5760x1080')}")

# Apply performance profile
profile = config.get('performance.profile', 'balanced')
config.apply_performance_profile(profile)

print()
print("💡 Tip: Copy config.example.yaml to config.yaml to customize settings")
pause_key = config.get('keybinds.pause', 'end')
print(f"💡 Press {pause_key.upper()} to pause/unpause during spec execution")
print()

# Main loop
while True:
    selected_game = select_game()
    if not selected_game:
        continue

    while True:
        selected_spec = select_spec(selected_game)
        if selected_spec is None:
            print("Returning to game selection.")
            break

        stop_event.clear()
        spec_thread = threading.Thread(target=run_spec, args=(selected_game, selected_spec, stop_event))
        spec_thread.start()

        # Wait for user to stop the running spec manually using Ctrl+C
        while spec_thread.is_alive():
            time.sleep(0.05)  # Add a slight delay to avoid busy-waiting

            if stop_event.is_set():
                spec_thread.join(timeout=5)
                if spec_thread.is_alive():
                    logger.warning("The spec did not terminate as expected. You may experience some delay.")
                else:
                    logger.info("Spec stopped successfully")
                break

        logger.info("Returning to spec selection")
