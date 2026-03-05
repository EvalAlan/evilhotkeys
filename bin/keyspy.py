import keyboard
import threading
import time

# Tool to spy on the keyboard events
def print_event(e):
    print(f"Key: {e.name}, Scan Code: {e.scan_code}, Time: {e.time}")

# Function to start the key spying process
def start_key_spy():
    print("Starting key spy. Press 'Esc' to stop.")
    # Hook the print_event function to the keyboard events
    keyboard.hook(print_event)
    # Wait for the 'esc' key to be pressed
    keyboard.wait('esc')
    print("\nKey spy stopped.")

# Function to run the key spy in a separate thread
def run_key_spy():
    try:
        key_spy_thread = threading.Thread(target=start_key_spy, daemon=True)
        key_spy_thread.start()
        # Keep the main thread alive to allow monitoring
        while key_spy_thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting key spy gracefully.")

# Start the key spy process
if __name__ == "__main__":
    run_key_spy()
