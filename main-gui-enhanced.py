#!/usr/bin/env python3
"""
EvilHotKeys - Enhanced GUI with Performance Monitoring
Shows real-time spec activity, APM, and performance metrics
"""
import signal
import sys
import threading
import os
from importlib import import_module, reload
from libs.menu_customization import customize_menu, customize_specs
from libs.logger import get_logger
from libs.spec_monitor import get_monitor, reset_monitor
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from PIL import Image, ImageTk
import time

logger = get_logger('main-gui-enhanced')


# Function to run the spec with monitoring
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
        # Don't call messagebox from worker thread - GUI will handle via exception
        raise
    except AttributeError as e:
        logger.error(f"Spec '{selected_spec}' AttributeError: {e}")
        # Don't call messagebox from worker thread - GUI will handle via exception
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in spec: {e}")
        # Don't call messagebox from worker thread - GUI will handle via exception
        raise
    finally:
        # Stop monitoring
        monitor = get_monitor()
        monitor.stop()


# Enhanced GUI Application Class
class EnhancedSpecRunnerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("EvilHotKeys - Enhanced Monitoring")
        self.root.geometry("900x700")
        
        # Set custom window icon
        icon_path = "./assets/pentagram-icon.png"
        try:
            img = Image.open(icon_path)
            photo = ImageTk.PhotoImage(img)
            self.root.iconphoto(False, photo)
        except Exception as e:
            logger.warning(f"Failed to load icon: {e}")

        # Handle window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.stop_event = threading.Event()
        self.monitor = get_monitor()
        self.update_job = None
        
        self.setup_ui()
        self.load_games()

    def setup_ui(self):
        """Setup the enhanced UI with monitoring"""
        # Main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - Controls
        left_panel = ttk.LabelFrame(main_container, text="Controls", padding="10")
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        # Game selection
        game_frame = ttk.Frame(left_panel)
        game_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(game_frame, text="Game:").pack(side='left', padx=(0, 5))
        self.game_combo = ttk.Combobox(game_frame, state="readonly", width=20)
        self.game_combo.pack(side='left', padx=(0, 5))
        self.game_combo.bind("<<ComboboxSelected>>", self.load_specs)
        
        self.refresh_button = ttk.Button(game_frame, text="🔄", command=self.refresh_specs, width=3)
        self.refresh_button.pack(side='left')
        
        # Spec selection
        ttk.Label(left_panel, text="Spec:").pack(anchor='w', pady=(10, 2))
        self.spec_combo = ttk.Combobox(left_panel, state="readonly", width=28)
        self.spec_combo.pack(fill=tk.X, pady=(0, 10))
        self.spec_combo['state'] = 'disabled'
        
        # Control buttons
        button_frame = ttk.Frame(left_panel)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.run_button = ttk.Button(button_frame, text="▶ Run Spec", command=self.run_selected_spec)
        self.run_button.pack(fill=tk.X, pady=2)
        
        self.stop_button = ttk.Button(button_frame, text="⏹ Stop Spec", command=self.stop_spec, state='disabled')
        self.stop_button.pack(fill=tk.X, pady=2)
        
        # Status indicator
        status_frame = ttk.LabelFrame(left_panel, text="Status", padding="10")
        status_frame.pack(fill=tk.X, pady=10)
        
        self.status_canvas = tk.Canvas(status_frame, width=20, height=20, bg='gray', highlightthickness=0)
        self.status_canvas.pack(side='left', padx=(0, 10))
        self.status_canvas.create_oval(2, 2, 18, 18, fill='gray', tags='indicator')
        
        self.status_label = ttk.Label(status_frame, text="Idle", font=('Arial', 10, 'bold'))
        self.status_label.pack(side='left')
        
        # Right panel - Monitoring
        right_panel = ttk.Frame(main_container)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        # Performance metrics
        metrics_frame = ttk.LabelFrame(right_panel, text="Performance Metrics", padding="10")
        metrics_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Create metric displays in a grid
        metrics_grid = ttk.Frame(metrics_frame)
        metrics_grid.pack(fill=tk.X)
        
        # APM
        ttk.Label(metrics_grid, text="APM:", font=('Arial', 9, 'bold')).grid(row=0, column=0, sticky='w', padx=5)
        self.apm_label = ttk.Label(metrics_grid, text="0.0", font=('Courier', 12, 'bold'), foreground='blue')
        self.apm_label.grid(row=0, column=1, sticky='w', padx=5)
        
        # Runtime
        ttk.Label(metrics_grid, text="Runtime:", font=('Arial', 9, 'bold')).grid(row=0, column=2, sticky='w', padx=5)
        self.runtime_label = ttk.Label(metrics_grid, text="0:00", font=('Courier', 11))
        self.runtime_label.grid(row=0, column=3, sticky='w', padx=5)
        
        # Keys pressed
        ttk.Label(metrics_grid, text="Keys:", font=('Arial', 9, 'bold')).grid(row=1, column=0, sticky='w', padx=5)
        self.keys_label = ttk.Label(metrics_grid, text="0", font=('Courier', 11))
        self.keys_label.grid(row=1, column=1, sticky='w', padx=5)
        
        # Interrupts
        ttk.Label(metrics_grid, text="Interrupts:", font=('Arial', 9, 'bold')).grid(row=1, column=2, sticky='w', padx=5)
        self.interrupts_label = ttk.Label(metrics_grid, text="0", font=('Courier', 11), foreground='red')
        self.interrupts_label.grid(row=1, column=3, sticky='w', padx=5)
        
        # Last action
        action_frame = ttk.LabelFrame(right_panel, text="Current Action", padding="10")
        action_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.last_action_label = ttk.Label(
            action_frame,
            text="No action yet",
            font=('Courier', 11),
            wraplength=500,
            justify='left'
        )
        self.last_action_label.pack(fill=tk.X)
        
        # Activity log
        log_frame = ttk.LabelFrame(right_panel, text="Activity Log", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.activity_log = scrolledtext.ScrolledText(
            log_frame,
            height=15,
            width=50,
            font=('Courier', 9),
            state='disabled',
            wrap=tk.WORD
        )
        self.activity_log.pack(fill=tk.BOTH, expand=True)
        
        # Configure tag for interrupts (highlight in red)
        self.activity_log.tag_config('interrupt', foreground='red', font=('Courier', 9, 'bold'))
        
        # Configure grid weights
        main_container.columnconfigure(0, weight=0, minsize=300)
        main_container.columnconfigure(1, weight=1)
        main_container.rowconfigure(0, weight=1)
        
        # Status bar
        self.statusbar = ttk.Label(
            self.root,
            text="Ready",
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=(5, 2)
        )
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)

    def load_games(self):
        """Load available games"""
        try:
            games = customize_menu('./games')
            if games:
                self.game_combo['values'] = games
                self.game_combo.current(0)
                self.load_specs(None)
            else:
                raise FileNotFoundError("No games available.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load games: {e}")

    def load_specs(self, event):
        """Load specs for selected game"""
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
        """Refresh spec list"""
        current_game = self.game_combo.get()
        if current_game:
            try:
                self.refresh_button.config(state='disabled')
                
                if hasattr(self, 'spec_thread') and self.spec_thread.is_alive():
                    self.stop_spec()
                
                self.load_specs(None)
                
                messagebox.showinfo("Success", "Specs refreshed successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to refresh specs: {e}")
            finally:
                self.refresh_button.config(state='normal')
        else:
            messagebox.showwarning("Warning", "Please select a game first.")

    def run_selected_spec(self):
        """Run the selected spec"""
        selected_game = self.game_combo.get()
        selected_spec = self.spec_combo.get()

        if not selected_game or not selected_spec:
            messagebox.showwarning("Warning", "Please select both a game and a spec.")
            return

        # Reset and start monitor BEFORE starting thread
        reset_monitor()
        self.monitor = get_monitor()
        self.monitor.start()  # Start monitoring immediately

        self.stop_event.clear()
        self.run_button.config(state='disabled')
        self.stop_button.config(state='normal')
        
        # Update status
        self.update_status("Running", "green")
        self.clear_activity_log()

        def run_in_thread():
            try:
                run_spec(selected_game, selected_spec, self.stop_event)
            except Exception as e:
                logger.exception(f"Spec crashed: {e}")
                # Show error dialog in main thread
                error_msg = str(e)
                self.root.after(0, lambda: messagebox.showerror("Spec Error", f"Spec crashed: {error_msg}"))
                self.root.after(0, lambda: self.on_spec_error(error_msg))
            finally:
                self.root.after(0, self.on_spec_complete)

        self.spec_thread = threading.Thread(target=run_in_thread, daemon=True)
        self.spec_thread.start()
        
        # Start UI updates
        self.start_monitoring_updates()

    def start_monitoring_updates(self):
        """Start periodic UI updates for monitoring"""
        self.update_monitoring_display()

    def update_monitoring_display(self):
        """Update the monitoring display"""
        if self.monitor.is_running:
            stats = self.monitor.get_stats()
            
            # Update APM
            self.apm_label.config(text=f"{stats['apm']:.1f}")
            
            # Update runtime
            runtime = stats['runtime']
            minutes = int(runtime // 60)
            seconds = int(runtime % 60)
            self.runtime_label.config(text=f"{minutes}:{seconds:02d}")
            
            # Update counts
            self.keys_label.config(text=str(stats['total_keys_pressed']))
            self.interrupts_label.config(text=str(stats['total_interrupts']))
            
            # Update last action
            self.last_action_label.config(text=stats['last_action'])
            
            # Update activity log
            self.update_activity_log()
            
            # Schedule next update
            self.update_job = self.root.after(250, self.update_monitoring_display)
        else:
            self.update_job = None

    def update_activity_log(self):
        """Update the activity log with recent actions"""
        recent_actions = self.monitor.get_recent_actions(15)
        
        self.activity_log.config(state='normal')
        self.activity_log.delete('1.0', tk.END)
        
        for action in recent_actions:
            if '⚡ INTERRUPT' in action:
                self.activity_log.insert(tk.END, action + '\n', 'interrupt')
            else:
                self.activity_log.insert(tk.END, action + '\n')
        
        self.activity_log.config(state='disabled')
        self.activity_log.see(tk.END)

    def clear_activity_log(self):
        """Clear the activity log"""
        self.activity_log.config(state='normal')
        self.activity_log.delete('1.0', tk.END)
        self.activity_log.config(state='disabled')

    def update_status(self, text, color):
        """Update status indicator"""
        self.status_label.config(text=text)
        self.status_canvas.itemconfig('indicator', fill=color)

    def on_spec_complete(self):
        """Handle spec completion"""
        self.run_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.update_status("Stopped", "orange")
        logger.info("Spec execution completed")
        
        # Cancel update job
        if self.update_job:
            self.root.after_cancel(self.update_job)
            self.update_job = None

    def on_spec_error(self, error_msg):
        """Handle spec errors"""
        logger.error(f"Spec error: {error_msg}")
        self.update_status("Error", "red")

    def stop_spec(self):
        """Stop the running spec"""
        logger.info("Stop button clicked - stop_event.set() called")
        self.stop_event.set()
        
        # Update UI immediately to show we're stopping
        self.update_status("Stopping...", "yellow")
        self.root.update()  # Force UI update
        logger.info("UI updated to show 'Stopping...'")
        
        # Give spec time to stop gracefully
        if hasattr(self, 'spec_thread') and self.spec_thread.is_alive():
            logger.info("Spec thread is alive, waiting for termination...")
            
            # Use a more aggressive approach - check every 0.5 seconds
            for i in range(6):  # 6 * 0.5 = 3 seconds total
                if not self.spec_thread.is_alive():
                    logger.info("Spec thread terminated")
                    break
                time.sleep(0.5)
                
            if self.spec_thread.is_alive():
                logger.warning("Spec thread did not terminate after 3 seconds - forcing stop")
                # Force re-enable buttons even if thread is stuck
                self.run_button.config(state='normal')
                self.stop_button.config(state='disabled')
                self.update_status("Force Stopped", "red")
            else:
                logger.info("Spec stopped successfully")
                self.run_button.config(state='normal')
                self.stop_button.config(state='disabled')
                self.update_status("Stopped", "orange")
        else:
            logger.info("No spec thread or thread already dead")
            self.run_button.config(state='normal')
            self.stop_button.config(state='disabled')
            self.update_status("Stopped", "orange")
        
        # Cancel monitoring updates
        if self.update_job:
            self.root.after_cancel(self.update_job)
            self.update_job = None
            logger.info("Monitoring updates cancelled")

    def on_close(self):
        """Handle window close"""
        logger.info("Window close requested")
        self.stop_event.set()
        
        # Cancel monitoring updates
        if self.update_job:
            self.root.after_cancel(self.update_job)
        
        # Try to wait for thread to stop, but don't block forever
        if hasattr(self, 'spec_thread') and self.spec_thread.is_alive():
            logger.info("Waiting for spec thread to terminate...")
            self.spec_thread.join(timeout=1)
            if self.spec_thread.is_alive():
                logger.warning("Spec thread still running after 1 second, forcing exit")
        
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
    app = EnhancedSpecRunnerApp(root)
    root.mainloop()