import signal
import sys
import threading
import os
from importlib import import_module, reload
from libs.menu_customization import customize_menu, customize_specs
from libs.logger import get_logger
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image
from PIL import ImageTk

logger = get_logger('main-gui')


# Function to run the spec
def run_spec(selected_game, selected_spec, stop_event):
   try:
       logger.info(f"Running spec '{selected_spec}' for game '{selected_game}'")
       module_name = f'games.{selected_game}.specs.{selected_spec}'
       
       # If module is already imported, reload it
       if module_name in sys.modules:
           spec_module = sys.modules[module_name]
           spec_module = reload(spec_module)
       else:
           spec_module = import_module(module_name)
           
       if hasattr(spec_module, 'run'):
           spec_module.run(stop_event)
       else:
           raise AttributeError(f"Spec '{selected_spec}' is missing the 'run' function.")
   except ModuleNotFoundError as e:
       logger.error(f"Failed to load spec '{selected_spec}': {e}")
       messagebox.showerror("Error", f"Failed to load spec '{selected_spec}' for game '{selected_game}'.\n{e}")
       raise  # Re-raise so GUI can handle it
   except AttributeError as e:
       logger.error(f"Spec '{selected_spec}' AttributeError: {e}")
       messagebox.showerror("Error", f"Spec '{selected_spec}' encountered an AttributeError.\n{e}")
       raise  # Re-raise so GUI can handle it
   except Exception as e:
       logger.exception(f"Unexpected error in spec: {e}")
       messagebox.showerror("Unexpected Error", f"An unexpected error occurred: {e}")
       raise  # Re-raise so GUI can handle it


# GUI Application Class
class SpecRunnerApp:
   def __init__(self, root):
       self.root = root
       self.root.title("EvilHotKeys GUI")

       # Set custom window icon
       icon_path = "./assets/pentagram-icon.png"  # Path to your icon file
       try:
           img = Image.open(icon_path)
           photo = ImageTk.PhotoImage(img)
           self.root.iconphoto(False, photo)
       except Exception as e:
           logger.warning(f"Failed to load icon: {e}")

       # Handle window close event (X button)
       self.root.protocol("WM_DELETE_WINDOW", self.on_close)

       self.stop_event = threading.Event()

       # Create a frame for the game selection and refresh button
       game_frame = ttk.Frame(root)
       game_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky='w')

       # Game Selection
       self.game_label = ttk.Label(game_frame, text="Select a Game:")
       self.game_label.pack(side='left', padx=(0, 10))

       self.game_combo = ttk.Combobox(game_frame, state="readonly")
       self.game_combo.pack(side='left', padx=(0, 10))
       self.game_combo.bind("<<ComboboxSelected>>", self.load_specs)

       # Add Refresh Button
       self.refresh_button = ttk.Button(game_frame, text="🔄 Refresh", command=self.refresh_specs)
       self.refresh_button.pack(side='left')

       # Spec Selection
       self.spec_label = ttk.Label(root, text="Select a Spec:")
       self.spec_label.grid(row=1, column=0, padx=10, pady=10, sticky='w')

       self.spec_combo = ttk.Combobox(root, state="readonly")
       self.spec_combo.grid(row=1, column=1, padx=10, pady=10, sticky='w')
       self.spec_combo['state'] = 'disabled'

       # Run Button
       self.run_button = ttk.Button(root, text="Run Spec", command=self.run_selected_spec)
       self.run_button.grid(row=2, column=0, columnspan=2, pady=10)

       # Stop Button
       self.stop_button = ttk.Button(root, text="Stop Spec", command=self.stop_spec, state='disabled')
       self.stop_button.grid(row=3, column=0, columnspan=2, pady=10)

       # Load games initially
       self.load_games()

   def load_games(self):
       try:
           games = customize_menu('./games')
           if games:
               self.game_combo['values'] = games
               # Auto-select the first game in the list
               self.game_combo.current(0)
               # Load the specs for the selected game
               self.load_specs(None)
           else:
               raise FileNotFoundError("No games available.")
       except Exception as e:
           messagebox.showerror("Error", f"Failed to load games: {e}")

   def load_specs(self, event):
       self.spec_combo.set('')
       self.spec_combo['state'] = 'disabled'

       selected_game = self.game_combo.get()
       if not selected_game:
           return

       try:
           spec_path = os.path.join('./games', selected_game, 'specs')
           if not os.path.exists(spec_path) or not os.path.isdir(spec_path):
               raise FileNotFoundError(f"Spec directory not found for game '{selected_game}'.")

           specs = [f[:-3] for f in os.listdir(spec_path) if f.endswith('.py') and not f.startswith('__')]

           if selected_game == 'World of Warcraft':
               specs = customize_specs(specs)

           if specs:
               self.spec_combo['values'] = specs
               self.spec_combo['state'] = 'readonly'
           else:
               raise FileNotFoundError(f"No specs found for {selected_game}.")
       except Exception as e:
           messagebox.showerror("Error", f"Failed to load specs: {e}")

   def refresh_specs(self):
       current_game = self.game_combo.get()
       if current_game:
           try:
               # Temporarily disable the refresh button
               self.refresh_button.config(state='disabled')
               
               # Stop any running spec
               if hasattr(self, 'spec_thread') and self.spec_thread.is_alive():
                   self.stop_spec()
               
               # Reload the specs
               self.load_specs(None)
               
               messagebox.showinfo("Success", "Specs refreshed successfully!")
           except Exception as e:
               messagebox.showerror("Error", f"Failed to refresh specs: {e}")
           finally:
               # Re-enable the refresh button
               self.refresh_button.config(state='normal')
       else:
           messagebox.showwarning("Warning", "Please select a game first.")

   def run_selected_spec(self):
       selected_game = self.game_combo.get()
       selected_spec = self.spec_combo.get()

       if not selected_game or not selected_spec:
           messagebox.showwarning("Warning", "Please select both a game and a spec.")
           return

       self.stop_event.clear()
       self.run_button.config(state='disabled')
       self.stop_button.config(state='normal')

       def run_in_thread():
           try:
               run_spec(selected_game, selected_spec, self.stop_event)
           except Exception as e:
               logger.exception(f"Spec crashed: {e}")
               self.root.after(0, lambda: self.on_spec_error(str(e)))
           finally:
               # Always restore button state, even if spec crashes
               self.root.after(0, self.on_spec_complete)

       self.spec_thread = threading.Thread(target=run_in_thread, daemon=True)
       self.spec_thread.start()

   def on_spec_complete(self):
       self.run_button.config(state='normal')
       self.stop_button.config(state='disabled')
       logger.info("Spec execution completed")

   def on_spec_error(self, error_msg):
       """Handle spec errors"""
       logger.error(f"Spec error: {error_msg}")
       # Button state will be restored by on_spec_complete in finally block

   def stop_spec(self):
       self.stop_event.set()
       self.run_button.config(state='normal')
       self.stop_button.config(state='disabled')

       if self.spec_thread.is_alive():
           self.spec_thread.join(timeout=2)
           if self.spec_thread.is_alive():
               logger.warning("The spec did not terminate as expected. You may experience some delay.")
           else:
               logger.info("Spec stopped successfully")

   def on_close(self):
       self.stop_event.set()
       if hasattr(self, 'spec_thread') and self.spec_thread.is_alive():
           self.spec_thread.join(timeout=2)
       self.root.destroy()
       sys.exit(0)


# Signal handler for graceful shutdown
def signal_handler(sig, frame):
   logger.info('\nCtrl+C pressed. Exiting gracefully.')
   sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)

# Main function to start the GUI
if __name__ == "__main__":
   root = tk.Tk()
   app_runner = SpecRunnerApp(root)
   root.mainloop()