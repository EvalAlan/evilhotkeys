import os
import subprocess

# If running as root, configure the DISPLAY and XAUTHORITY settings
if os.geteuid() == 0:
    if "SUDO_USER" in os.environ:
        user = os.environ["SUDO_USER"]
        os.environ["DISPLAY"] = os.environ.get("DISPLAY", ":0")
        xauth_path = f"/home/{user}/.Xauthority"
        if os.path.exists(xauth_path):
            os.environ["XAUTHORITY"] = xauth_path
        else:
            print(f"Warning: Xauthority file not found at {xauth_path}.")
            print("Attempting to grant root access to the X server using xhost...")
            try:
                subprocess.run(["sudo", "-u", user, "xhost", "+SI:localuser:root"], check=True)
                print("xhost command executed successfully.")
            except Exception as e:
                print("Failed to run xhost command:", e)

# Attempt to override the screenshot method with one using mss
try:
    import mss
    from PIL import Image

    def mss_screenshot(region=None):
        with mss.mss() as sct:
            if region:
                # region should be a dict: {'top': y, 'left': x, 'width': w, 'height': h}
                sct_img = sct.grab(region)
            else:
                sct_img = sct.grab(sct.monitors[0])
            return Image.frombytes("RGB", sct_img.size, sct_img.rgb)

    # Import pyautogui and override its screenshot function
    import pyautogui
    pyautogui.screenshot = mss_screenshot
except ImportError:
    print("mss library not found; falling back to default screenshot method.")
    import pyautogui

import time
import threading
import keyboard
import sys
import os

# Add the parent directory to the path so we can import our libs
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from libs.pixel_get_color import get_color

# Tool to spy on the pixel color at the current cursor position
def pixel_spy():
    prev_x, prev_y = None, None
    try:
        while True:
            # Get the current position of the cursor
            x, y = pyautogui.position()

            # Only fetch the color and print if the cursor has moved
            if (x, y) != (prev_x, prev_y):
                # Get the color of the pixel at the cursor position using our custom function
                pixel_color = get_color(x, y)

                # Print the cursor position and color
                print(f"Cursor Position: ({x}, {y}) - Pixel Color (RGB): {pixel_color}")

                # Update previous coordinates
                prev_x, prev_y = x, y

            # Add a delay to prevent excessive CPU usage
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nExiting pixel spy gracefully.")

# Function to monitor for exit key
def exit_listener():
    keyboard.wait('esc')
    print("\nExit key pressed. Stopping pixel spy.")
    raise KeyboardInterrupt

# Start the pixel spy in a separate thread
pixel_spy_thread = threading.Thread(target=pixel_spy, daemon=True)
pixel_spy_thread.start()

# Start the exit listener in the main thread
exit_listener()
