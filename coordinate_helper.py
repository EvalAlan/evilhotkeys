#!/usr/bin/env python3
"""
EvilHotKeys Coordinate Helper Tool

Interactive GUI to capture and save pixel coordinates for game specs.
Click on screen elements to capture their coordinates and save to config.yaml
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import yaml
from pathlib import Path
from libs.pixel_get_color import get_color
from libs.logger import get_logger
from libs.config_manager import get_config_manager
import keyboard
import time
import threading

logger = get_logger('coordinate_helper')


class CoordinateHelperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("EvilHotKeys - Coordinate Helper")
        self.root.geometry("700x600")
        
        self.config = get_config_manager()
        self.capturing = False
        self.current_game = None
        self.current_coord_name = None
        
        self.setup_ui()
        self.load_games()
        
        # Start coordinate monitor thread
        self.monitor_thread = threading.Thread(target=self.monitor_mouse, daemon=True)
        self.monitor_thread.start()
    
    def setup_ui(self):
        """Setup the UI components"""
        # Title
        title_label = ttk.Label(
            self.root, 
            text="Coordinate Helper Tool",
            font=('Arial', 16, 'bold')
        )
        title_label.pack(pady=10)
        
        # Instructions
        instructions = ttk.Label(
            self.root,
            text="Hover over a UI element and press F9 to capture coordinates",
            font=('Arial', 10)
        )
        instructions.pack(pady=5)
        
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left side - Game and coordinate selection
        left_frame = ttk.LabelFrame(main_frame, text="Setup", padding="10")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Game selection
        ttk.Label(left_frame, text="Game:").grid(row=0, column=0, sticky="w", pady=5)
        self.game_combo = ttk.Combobox(left_frame, state="readonly", width=25)
        self.game_combo.grid(row=0, column=1, pady=5, padx=5)
        self.game_combo.bind("<<ComboboxSelected>>", self.on_game_selected)
        
        # Resolution
        ttk.Label(left_frame, text="Resolution:").grid(row=1, column=0, sticky="w", pady=5)
        self.resolution_var = tk.StringVar(value=self.config.get('display.resolution', '1920x1080'))
        self.resolution_entry = ttk.Entry(left_frame, textvariable=self.resolution_var, width=27)
        self.resolution_entry.grid(row=1, column=1, pady=5, padx=5)
        
        # Coordinate name
        ttk.Label(left_frame, text="Coordinate Name:").grid(row=2, column=0, sticky="w", pady=5)
        self.coord_name_var = tk.StringVar()
        self.coord_name_entry = ttk.Entry(left_frame, textvariable=self.coord_name_var, width=27)
        self.coord_name_entry.grid(row=2, column=1, pady=5, padx=5)
        
        # Common coordinate presets
        ttk.Label(left_frame, text="Presets:").grid(row=3, column=0, sticky="w", pady=5)
        preset_frame = ttk.Frame(left_frame)
        preset_frame.grid(row=3, column=1, pady=5, padx=5, sticky="w")
        
        presets = ["interrupt", "health_50", "health_35", "health_25", "health_75", "focus_health"]
        for i, preset in enumerate(presets):
            btn = ttk.Button(
                preset_frame, 
                text=preset.replace('_', ' ').title(),
                command=lambda p=preset: self.coord_name_var.set(p),
                width=12
            )
            btn.grid(row=i//2, column=i%2, padx=2, pady=2)
        
        # Right side - Current info and capture
        right_frame = ttk.LabelFrame(main_frame, text="Capture", padding="10")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        # Current mouse position
        ttk.Label(right_frame, text="Current Position:").grid(row=0, column=0, sticky="w", pady=5)
        self.position_label = ttk.Label(right_frame, text="(0, 0)", font=('Courier', 12, 'bold'))
        self.position_label.grid(row=0, column=1, pady=5, sticky="w")
        
        # Current color
        ttk.Label(right_frame, text="Current Color:").grid(row=1, column=0, sticky="w", pady=5)
        self.color_label = ttk.Label(right_frame, text="(0, 0, 0)", font=('Courier', 12))
        self.color_label.grid(row=1, column=1, pady=5, sticky="w")
        
        # Color preview
        self.color_canvas = tk.Canvas(right_frame, width=60, height=60, bg='black')
        self.color_canvas.grid(row=2, column=0, columnspan=2, pady=10)
        
        # Capture status
        self.status_label = ttk.Label(
            right_frame, 
            text="Press F9 to capture",
            font=('Arial', 10, 'italic')
        )
        self.status_label.grid(row=3, column=0, columnspan=2, pady=10)
        
        # Captured coordinate display
        ttk.Label(right_frame, text="Captured:").grid(row=4, column=0, sticky="w", pady=5)
        self.captured_label = ttk.Label(
            right_frame, 
            text="None", 
            font=('Courier', 12, 'bold'),
            foreground='green'
        )
        self.captured_label.grid(row=4, column=1, pady=5, sticky="w")
        
        # Buttons
        button_frame = ttk.Frame(right_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=10)
        
        self.save_btn = ttk.Button(
            button_frame,
            text="💾 Save to Config",
            command=self.save_coordinate,
            state='disabled'
        )
        self.save_btn.pack(side=tk.LEFT, padx=5)
        
        self.test_btn = ttk.Button(
            button_frame,
            text="🔍 Test Coordinate",
            command=self.test_coordinate,
            state='disabled'
        )
        self.test_btn.pack(side=tk.LEFT, padx=5)
        
        # Bottom - Saved coordinates list
        coords_frame = ttk.LabelFrame(main_frame, text="Saved Coordinates", padding="10")
        coords_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        
        # Scrolled text for coordinates
        self.coords_text = scrolledtext.ScrolledText(
            coords_frame,
            height=8,
            width=80,
            font=('Courier', 9)
        )
        self.coords_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure grid weights
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=0)
        
        # Status bar
        self.statusbar = ttk.Label(
            self.root, 
            text="Ready - Press F9 to capture coordinates",
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def load_games(self):
        """Load available games"""
        games_dir = Path('games')
        if games_dir.exists():
            games = [d.name for d in games_dir.iterdir() if d.is_dir() and not d.name.startswith('__')]
            self.game_combo['values'] = games
            if games:
                self.game_combo.current(0)
                self.on_game_selected()
    
    def on_game_selected(self, event=None):
        """Handle game selection"""
        self.current_game = self.game_combo.get()
        self.update_saved_coords()
    
    def monitor_mouse(self):
        """Monitor mouse position and capture on F9"""
        try:
            import pyautogui
            
            # Register F9 hotkey for capture
            keyboard.add_hotkey('f9', self.capture_coordinate)
            
            while True:
                if not self.capturing:
                    try:
                        # Get mouse position
                        x, y = pyautogui.position()
                        
                        # Update position label
                        self.position_label.config(text=f"({x}, {y})")
                        
                        # Get color at position
                        color = get_color(x, y)
                        if color:
                            self.color_label.config(text=f"{color}")
                            
                            # Update color preview
                            hex_color = '#{:02x}{:02x}{:02x}'.format(*color)
                            self.color_canvas.config(bg=hex_color)
                    except Exception as e:
                        pass
                
                time.sleep(0.05)  # Update 20 times per second
                
        except ImportError:
            logger.error("PyAutoGUI not available for mouse tracking")
    
    def capture_coordinate(self):
        """Capture current mouse coordinates"""
        try:
            import pyautogui
            x, y = pyautogui.position()
            
            self.captured_label.config(text=f"({x}, {y})")
            self.status_label.config(text="✓ Coordinate captured!", foreground='green')
            
            # Enable buttons
            self.save_btn.config(state='normal')
            self.test_btn.config(state='normal')
            
            # Update statusbar
            self.statusbar.config(text=f"Captured: ({x}, {y}) - Ready to save")
            
            logger.info(f"Captured coordinate: ({x}, {y})")
            
        except Exception as e:
            logger.error(f"Error capturing coordinate: {e}")
            messagebox.showerror("Error", f"Failed to capture coordinate: {e}")
    
    def save_coordinate(self):
        """Save captured coordinate to config"""
        coord_name = self.coord_name_var.get().strip()
        if not coord_name:
            messagebox.showwarning("Warning", "Please enter a coordinate name")
            return
        
        game = self.current_game
        if not game:
            messagebox.showwarning("Warning", "Please select a game")
            return
        
        captured_text = self.captured_label.cget("text")
        if captured_text == "None":
            messagebox.showwarning("Warning", "Please capture a coordinate first (F9)")
            return
        
        try:
            # Parse captured coordinates
            coord_text = captured_text.strip('()')
            x, y = map(int, coord_text.split(','))
            
            resolution = self.resolution_var.get()
            
            # Load current config
            config_path = Path('config.yaml')
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config_data = yaml.safe_load(f) or {}
            else:
                config_data = {}
            
            # Initialize structure if needed
            if 'games' not in config_data:
                config_data['games'] = {}
            if game not in config_data['games']:
                config_data['games'][game] = {}
            if 'coordinates' not in config_data['games'][game]:
                config_data['games'][game]['coordinates'] = {}
            if resolution not in config_data['games'][game]['coordinates']:
                config_data['games'][game]['coordinates'][resolution] = {}
            
            # Save coordinate
            config_data['games'][game]['coordinates'][resolution][coord_name] = [x, y]
            
            # Write back to file
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
            
            self.statusbar.config(text=f"✓ Saved {coord_name} = ({x}, {y}) to config.yaml")
            messagebox.showinfo("Success", f"Saved {coord_name} = ({x}, {y})\n\nTo: {game}/{resolution}")
            
            # Reload config
            self.config.load()
            self.update_saved_coords()
            
            # Reset capture
            self.captured_label.config(text="None")
            self.save_btn.config(state='disabled')
            self.test_btn.config(state='disabled')
            self.status_label.config(text="Press F9 to capture", foreground='black')
            
        except Exception as e:
            logger.error(f"Error saving coordinate: {e}")
            messagebox.showerror("Error", f"Failed to save coordinate: {e}")
    
    def test_coordinate(self):
        """Test the captured coordinate by reading its color"""
        captured_text = self.captured_label.cget("text")
        if captured_text == "None":
            messagebox.showwarning("Warning", "Please capture a coordinate first (F9)")
            return
        
        try:
            # Parse coordinates
            coord_text = captured_text.strip('()')
            x, y = map(int, coord_text.split(','))
            
            # Get color
            color = get_color(x, y)
            if color:
                hex_color = '#{:02x}{:02x}{:02x}'.format(*color)
                messagebox.showinfo(
                    "Coordinate Test",
                    f"Coordinate: ({x}, {y})\n"
                    f"Color: {color}\n"
                    f"Hex: {hex_color}\n\n"
                    f"If this is black (0, 0, 0) when it shouldn't be,\n"
                    f"the element might not be visible right now."
                )
            else:
                messagebox.showerror("Error", "Failed to read color at coordinate")
                
        except Exception as e:
            logger.error(f"Error testing coordinate: {e}")
            messagebox.showerror("Error", f"Failed to test coordinate: {e}")
    
    def update_saved_coords(self):
        """Update the saved coordinates display"""
        self.coords_text.delete('1.0', tk.END)
        
        if not self.current_game:
            return
        
        game_config = self.config.get_game_config(self.current_game)
        if not game_config or 'coordinates' not in game_config:
            self.coords_text.insert('1.0', f"No coordinates saved for {self.current_game} yet.\n\n")
            self.coords_text.insert('2.0', "Use F9 to capture coordinates and save them.")
            return
        
        coords = game_config['coordinates']
        
        output = f"Saved coordinates for {self.current_game}:\n"
        output += "=" * 70 + "\n\n"
        
        for resolution, coord_dict in coords.items():
            output += f"{resolution}:\n"
            for name, (x, y) in coord_dict.items():
                output += f"  {name:20} = ({x:4}, {y:4})\n"
            output += "\n"
        
        self.coords_text.insert('1.0', output)


def main():
    root = tk.Tk()
    app = CoordinateHelperApp(root)
    
    print("=" * 70)
    print("EvilHotKeys Coordinate Helper Tool")
    print("=" * 70)
    print()
    print("Instructions:")
    print("1. Select your game from the dropdown")
    print("2. Enter a name for the coordinate (or use a preset)")
    print("3. In your game, hover over the UI element")
    print("4. Press F9 to capture the coordinate")
    print("5. Click 'Save to Config' to save it")
    print()
    print("The coordinates will be automatically used by your specs!")
    print("=" * 70)
    print()
    
    root.mainloop()


if __name__ == "__main__":
    main()

