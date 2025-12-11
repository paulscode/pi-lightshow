"""
Graphical Simulator for Pi Lightshow Development

This module provides a tkinter-based GUI for simulating the 10-channel lightshow
and button controls on a development machine without Raspberry Pi hardware.

Features:
- Visual representation of all 10 light channels with accurate physical layout
- Three interactive buttons (Power, Mode, Lightshow)
- Real-time channel state updates synchronized with song playback
- Status display showing current mode, song, and system state
- Clean dark theme matching the Christmas light aesthetic

Layout:
- Channels arranged to match physical installation: 10-9  2-7-6  4-3  5-8  1
- Channels light up in colors (green=on, dark=off) matching real behavior
- Status bar shows current light mode and playback information

Usage:
- Run lightshow.py with --simulate flag
- Click buttons to control the system as you would on hardware
- Window must remain open for simulation to continue
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional, List
import threading


class LightshowSimulator:
    """GUI simulator for the lightshow."""
    
    def __init__(self, channel_callback: Optional[Callable] = None):
        """
        Initialize the simulator.
        
        Args:
            channel_callback: Optional callback to receive channel state updates
        """
        self.channel_callback = channel_callback
        self.root = tk.Tk()
        self.root.title("Pi Lightshow Simulator")
        self.root.geometry("800x600")
        self.root.configure(bg='#1a1a1a')
        
        # Channel states
        self.channel_states = [False] * 10
        self.channel_widgets = []
        
        # Button callbacks (will be set by external code)
        self.button_callbacks = []
        
        self._create_ui()
        
    def _create_ui(self):
        """Create the user interface."""
        # Title
        title = tk.Label(
            self.root,
            text="🎄 Pi Lightshow Simulator 🎄",
            font=("Arial", 24, "bold"),
            bg='#1a1a1a',
            fg='#00ff00'
        )
        title.pack(pady=20)
        
        # Info text
        info = tk.Label(
            self.root,
            text="Channel arrangement matches physical layout",
            font=("Arial", 10),
            bg='#1a1a1a',
            fg='#888888'
        )
        info.pack()
        
        # Channels frame
        channels_frame = tk.Frame(self.root, bg='#1a1a1a')
        channels_frame.pack(pady=30)
        
        # Channel layout based on README:
        # 10   9   2   7   6   4   3   5   8   1
        # |------| |-----------| |-----| |-----|
        # 10+9     2+7+6         4+3     5+8     (1)
        
        channel_order = [10, 9, 2, 7, 6, 4, 3, 5, 8, 1]
        groups = [
            (0, 2, "10+9"),      # Channels 10, 9
            (2, 5, "2+7+6"),     # Channels 2, 7, 6
            (5, 7, "4+3"),       # Channels 4, 3
            (7, 9, "5+8"),       # Channels 5, 8
            (9, 10, "1")         # Channel 1 (standalone)
        ]
        
        row_frame = tk.Frame(channels_frame, bg='#1a1a1a')
        row_frame.pack()
        
        for i, channel_num in enumerate(channel_order):
            # Create light bulb widget
            bulb_frame = tk.Frame(row_frame, bg='#1a1a1a')
            bulb_frame.pack(side=tk.LEFT, padx=10)
            
            # Channel number label
            label = tk.Label(
                bulb_frame,
                text=f"Ch {channel_num}",
                font=("Arial", 10),
                bg='#1a1a1a',
                fg='#666666'
            )
            label.pack()
            
            # Light bulb
            canvas = tk.Canvas(
                bulb_frame,
                width=60,
                height=80,
                bg='#1a1a1a',
                highlightthickness=0
            )
            canvas.pack(pady=5)
            
            # Draw bulb shape
            bulb = canvas.create_oval(10, 10, 50, 60, fill='#333333', outline='#555555', width=2)
            base = canvas.create_rectangle(20, 55, 40, 70, fill='#444444', outline='#555555', width=2)
            
            self.channel_widgets.append({
                'canvas': canvas,
                'bulb': bulb,
                'channel_num': channel_num
            })
        
        # Grouping indicators
        group_frame = tk.Frame(channels_frame, bg='#1a1a1a')
        group_frame.pack(pady=10)
        
        # Create grouped bracket indicators with proper spacing
        bracket_frame = tk.Frame(group_frame, bg='#1a1a1a')
        bracket_frame.pack()
        
        # Group labels with spacing to match bulb layout
        # 10   9  |  2   7   6  |  4   3  |  5   8  |  1
        # Groups: 10+9,  2+7+6,    4+3,     5+8,    (1 alone)
        group_labels = [
            ("", 160),          # 2 bulbs (10, 9)
            ("", 240),          # 3 bulbs (2, 7, 6)
            ("", 160),          # 2 bulbs (4, 3)
            ("", 160),          # 2 bulbs (5, 8)
            ("", 80)            # 1 bulb (1) - no bracket
        ]
        
        for i, (label_text, width) in enumerate(group_labels):
            if i == 4:  # Last one (channel 1) has no bracket
                label = tk.Label(
                    bracket_frame,
                    text=" " * int(width/8),
                    font=("Courier", 10, "bold"),
                    bg='#1a1a1a',
                    fg='#444444',
                    width=int(width/8)
                )
            else:
                label = tk.Label(
                    bracket_frame,
                    text=f"|{'-' * int(width/10)}|",
                    font=("Courier", 10, "bold"),
                    bg='#1a1a1a',
                    fg='#444444',
                    width=int(width/8)
                )
            label.pack(side=tk.LEFT, padx=0)
        
        # Separator
        separator = tk.Frame(self.root, height=2, bg='#333333')
        separator.pack(fill=tk.X, padx=50, pady=20)
        
        # Control buttons
        controls_frame = tk.Frame(self.root, bg='#1a1a1a')
        controls_frame.pack(pady=20)
        
        tk.Label(
            controls_frame,
            text="Control Buttons:",
            font=("Arial", 14, "bold"),
            bg='#1a1a1a',
            fg='#00ff00'
        ).pack()
        
        buttons_frame = tk.Frame(controls_frame, bg='#1a1a1a')
        buttons_frame.pack(pady=10)
        
        # Power button (red)
        self.power_btn = tk.Button(
            buttons_frame,
            text="⏻ POWER\n(Shutdown)",
            font=("Arial", 12, "bold"),
            bg='#8b0000',
            fg='white',
            width=15,
            height=3,
            relief=tk.RAISED,
            cursor='hand2'
        )
        self.power_btn.pack(side=tk.LEFT, padx=10)
        self.power_btn.bind('<ButtonPress-1>', lambda e: self._button_press(0))
        self.power_btn.bind('<ButtonRelease-1>', lambda e: self._button_release(0))
        
        # Mode button (yellow)
        self.mode_btn = tk.Button(
            buttons_frame,
            text="◉ MODE\n(Light Patterns)",
            font=("Arial", 12, "bold"),
            bg='#ccaa00',
            fg='black',
            width=15,
            height=3,
            relief=tk.RAISED,
            cursor='hand2'
        )
        self.mode_btn.pack(side=tk.LEFT, padx=10)
        self.mode_btn.bind('<ButtonPress-1>', lambda e: self._button_press(1))
        self.mode_btn.bind('<ButtonRelease-1>', lambda e: self._button_release(1))
        
        # Lightshow button (green)
        self.lightshow_btn = tk.Button(
            buttons_frame,
            text="♪ LIGHTSHOW\n(Start Music)",
            font=("Arial", 12, "bold"),
            bg='#006400',
            fg='white',
            width=15,
            height=3,
            relief=tk.RAISED,
            cursor='hand2'
        )
        self.lightshow_btn.pack(side=tk.LEFT, padx=10)
        self.lightshow_btn.bind('<ButtonPress-1>', lambda e: self._button_press(2))
        self.lightshow_btn.bind('<ButtonRelease-1>', lambda e: self._button_release(2))
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = tk.Label(
            self.root,
            textvariable=self.status_var,
            font=("Arial", 10),
            bg='#2a2a2a',
            fg='#00ff00',
            anchor=tk.W,
            padx=10,
            pady=5
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def _button_press(self, button_index: int):
        """Handle button press."""
        buttons = [self.power_btn, self.mode_btn, self.lightshow_btn]
        buttons[button_index].config(relief=tk.SUNKEN)
        
        # Call the button callback if registered
        if button_index < len(self.button_callbacks) and self.button_callbacks[button_index]:
            self.button_callbacks[button_index](button_index, True)
    
    def _button_release(self, button_index: int):
        """Handle button release."""
        buttons = [self.power_btn, self.mode_btn, self.lightshow_btn]
        buttons[button_index].config(relief=tk.RAISED)
        
        # Call the button callback if registered
        if button_index < len(self.button_callbacks) and self.button_callbacks[button_index]:
            self.button_callbacks[button_index](button_index, False)
    
    def set_button_callback(self, callback: Callable):
        """
        Set callback for button events.
        
        Args:
            callback: Function(button_index, state) where state is True for press
        """
        self.button_callbacks = [callback, callback, callback]
    
    def update_channel(self, channel_num: int, state: bool):
        """
        Update the visual state of a channel.
        
        Args:
            channel_num: Channel number (1-10)
            state: True for on, False for off
        """
        # Check if GUI still exists
        try:
            if not self.root.winfo_exists():
                return
        except:
            return
        
        # Find the widget for this channel
        for widget in self.channel_widgets:
            if widget['channel_num'] == channel_num:
                canvas = widget['canvas']
                bulb = widget['bulb']
                
                if state:
                    # Channel is on - bright yellow/white
                    color = '#ffff00'
                    glow_color = '#ffcc00'
                else:
                    # Channel is off - dark gray
                    color = '#333333'
                    glow_color = '#555555'
                
                canvas.itemconfig(bulb, fill=color, outline=glow_color)
                break
        
        # Store state
        if 1 <= channel_num <= 10:
            self.channel_states[channel_num - 1] = state
    
    def set_status(self, message: str):
        """Update the status bar message."""
        self.status_var.set(message)
    
    def run(self):
        """Start the GUI event loop."""
        self.root.mainloop()
    
    def destroy(self):
        """Close the simulator window."""
        self.root.quit()
        self.root.destroy()


def run_simulator_in_thread(simulator: LightshowSimulator):
    """
    Run the simulator in a separate thread.
    Note: On Python 3.12+, tkinter must run on the main thread.
    This function is kept for backwards compatibility but may cause issues.
    
    Args:
        simulator: LightshowSimulator instance
    """
    import warnings
    warnings.warn("Running GUI in thread may cause issues on Python 3.12+. "
                  "Consider running GUI on main thread instead.", RuntimeWarning)
    thread = threading.Thread(target=simulator.run)
    thread.start()
    return thread


if __name__ == "__main__":
    # Test the simulator with random flashing
    from random import random
    import time
    from threading import Timer
    
    # Create simulator first
    simulator = None
    
    # State for test mode
    test_mode = -1  # -1=off, 0=on, 1=slow, 2=medium, 3=fast
    flash_timers = [None] * 10
    running = True
    
    def button_callback(index, state):
        global test_mode, running
        button_names = ["Power", "Mode", "Lightshow"]
        action = "pressed" if state else "released"
        print(f"{button_names[index]} button {action}")
        
        if state:  # Button pressed
            if index == 0:  # Power
                running = False
                simulator.destroy()
            elif index == 1:  # Mode - cycle through flash patterns
                test_mode = test_mode + 1
                if test_mode > 3:
                    test_mode = -1
                
                if test_mode == -1:
                    simulator.set_status("Test Mode: All Off")
                    print("Mode: All Off")
                else:
                    mode_names = ["Always On", "Slow Flash", "Medium Flash", "Fast Flash"]
                    simulator.set_status(f"Test Mode: {mode_names[test_mode]}")
                    print(f"Mode: {mode_names[test_mode]}")
                start_flash_pattern()
            elif index == 2:  # Lightshow
                simulator.set_status("No lightshow in standalone test mode. Run: python3 lightshow.py --simulate")
                print("Lightshow requires full application. Run: python3 lightshow.py --simulate")
    
    def channel_callback(channel_num, state):
        pass  # Don't spam console in test mode
    
    def flash_off(channel_idx, mode):
        """Turn channel off and schedule next on."""
        if mode == 0:
            return
        
        scaler = {1: 5.0, 2: 3.0, 3: 0.5}.get(mode, 3.0)
        r = random()
        
        simulator.update_channel(channel_idx + 1, False)
        
        if running:
            timer = Timer(r * scaler, flash_on, [channel_idx, mode])
            timer.start()
            flash_timers[channel_idx] = timer
    
    def flash_on(channel_idx, mode):
        """Turn channel on and schedule next off."""
        simulator.update_channel(channel_idx + 1, True)
        
        if mode != 0 and running:
            scaler = {1: 5.0, 2: 3.0, 3: 0.5}.get(mode, 3.0)
            r = random()
            
            timer = Timer(r * scaler, flash_off, [channel_idx, mode])
            timer.start()
            flash_timers[channel_idx] = timer
    
    def start_flash_pattern():
        """Start the current flash pattern."""
        # Cancel existing timers
        for timer in flash_timers:
            if timer:
                timer.cancel()
        
        if test_mode == -1:
            # Turn all off
            for i in range(1, 11):
                simulator.update_channel(i, False)
        elif test_mode == 0:
            # Always on
            for i in range(1, 11):
                simulator.update_channel(i, True)
        else:
            # Random flashing - start with lights ON
            for i in range(10):
                flash_on(i, test_mode)
    
    simulator = LightshowSimulator(channel_callback)
    simulator.set_button_callback(button_callback)
    
    simulator.set_status("Test mode - Click MODE button to cycle patterns, LIGHTSHOW for info")
    print("=" * 60)
    print("Standalone Test Mode")
    print("=" * 60)
    print("Click MODE button to cycle through flash patterns")
    print("Click POWER to exit")
    print("For full lightshow, run: python3 lightshow_v2.py --simulate")
    print("=" * 60)
    
    # Start with always on
    start_flash_pattern()
    
    simulator.run()
