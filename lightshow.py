#!/usr/bin/env python3
"""
Pi Lightshow Main Application

Christmas lightshow controller using JSON-based song definitions and hardware abstraction.
Supports both Raspberry Pi GPIO control and GUI simulation for development.
"""

import sys
import os
import json
from time import sleep
from threading import Timer
from random import random
from subprocess import Popen
from typing import Optional
import argparse

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from song_loader import SongLoader, SongInterpreter
from hardware.channel_interface import (
    create_channels, create_buttons, setup_gpio, cleanup_gpio
)
from player_interface import create_player


def load_config(config_path: str = "config.json") -> dict:
    """
    Load configuration from JSON file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Dictionary containing configuration, or empty dict if file not found
    """
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load config file: {e}")
    return {}


class LightshowController:
    """Main controller for the lightshow system."""
    
    def __init__(self, simulated: bool = False, songs_dir: str = "songs"):
        """
        Initialize the lightshow controller.
        
        Args:
            simulated: If True, run in simulation mode (no GPIO, uses GUI)
            songs_dir: Directory containing song JSON files
        """
        self.simulated = simulated
        self.songs_dir = songs_dir
        
        # Setup GPIO or simulation mode
        # In hardware mode, configure Raspberry Pi GPIO pins
        # In simulation mode, skip GPIO setup entirely
        if not simulated:
            setup_gpio()
        
        # Initialize GUI simulator if in simulated mode
        # The simulator provides a visual representation of the 10 light channels
        # and three control buttons for development without hardware
        self.simulator = None
        if simulated:
            from simulator.gui_simulator import LightshowSimulator
            self.simulator = LightshowSimulator()
            self.simulator.set_button_callback(self._button_callback)
            # Note: GUI will run on main thread (handled in run() method)
        
        # Create channels with callback for simulator
        # channel_callback updates the visual display when lights change state
        channel_callback = None
        if simulated and self.simulator:
            channel_callback = self.simulator.update_channel
        
        # Create 10 light channels (GPIO pins or simulated)
        self.channels = create_channels(simulated, channel_callback)
        
        # Create 3 control buttons (GPIO pins or simulated)
        # Button 0: Power/Shutdown, Button 1: Mode, Button 2: Lightshow
        self.buttons = create_buttons(simulated, self._button_callback)
        
        # Flash timers for light pattern modes
        # Each channel gets its own timer for independent random flashing
        self.flash_timers = [Timer(0.1, lambda: None) for _ in range(10)]
        
        # State variables
        self.light_mode = 1  # Current mode: 0=always on, 1=slow flash, 2=medium flash, 3=fast flash, 4=song playing
        self.previous_light_mode = 1  # Mode to restore after lightshow completes
        self.auto_play = False  # Whether to automatically advance to next song after current finishes
        self.debounce = False  # Button debounce flag to prevent multiple rapid presses
        self.player = None  # Current audio player instance (VLC, OMXPlayer, or simulated)
        self.interpreter = None  # Current song interpreter instance (executes lightshow sequences)
        self.current_song_id = None  # ID of currently playing song
        
        # Song loader - reads JSON files from songs directory
        self.song_loader = SongLoader(songs_dir)
        self.available_songs = self.song_loader.list_songs()  # List of song IDs in playlist order
        self.current_song_index = 0  # Index into available_songs list
        
        # Integration API endpoints (optional)
        # These allow external systems to trigger the lightshow via HTTP
        # Priority: config.json > environment variables > empty (disabled)
        config = load_config()
        api_config = config.get("api", {})
        
        self.integration_check = (
            api_config.get("integration_check_url") or 
            os.getenv("INTEGRATION_CHECK_URL", "")
        )
        self.integration_done = (
            api_config.get("integration_done_url") or 
            os.getenv("INTEGRATION_DONE_URL", "")
        )
        
        print("=" * 60)
        print("Pi Lightshow Initialized")
        print(f"Mode: {'SIMULATED' if simulated else 'HARDWARE'}")
        print(f"Available songs: {len(self.available_songs)}")
        for song_id in self.available_songs:
            info = self.song_loader.get_song_info(song_id)
            print(f"  - {info['title']} by {info['artist']}")
        print("=" * 60)
        
        # Start in light pattern mode
        self._flash_lights(self.light_mode)
        self._update_status()
    
    def _update_status(self):
        """Update status display (for simulator)."""
        if self.simulator:
            if self.light_mode == 4:
                song_info = self.song_loader.get_song_info(self.current_song_id)
                if song_info:
                    self.simulator.set_status(f"Playing: {song_info['title']}")
            else:
                modes = ["Always On", "Slow Flash", "Medium Flash", "Fast Flash"]
                if self.light_mode < len(modes):
                    self.simulator.set_status(f"Light Mode: {modes[self.light_mode]}")
    
    def _button_callback(self, index: int, state: bool):
        """
        Handle button press/release events.
        
        Args:
            index: Button index (0=Power, 1=Mode, 2=Lightshow)
            state: True for button press, False for button release
        """
        # Ignore button releases and debounced presses
        if not state or self.debounce:
            return
        
        # Debounce: prevent multiple rapid button presses
        # After a button press, ignore all presses for 0.5 seconds
        self.debounce = True
        Timer(0.5, self._clear_debounce).start()
        
        # Check if we're currently playing a song
        previous_mode = self.light_mode
        was_playing = (previous_mode == 4) and (self.player is not None)
        
        # Button 0: Power (shutdown)
        if index == 0:
            print("Shutting down...")
            self._flash_lights(-1)  # Turn off all lights
            if self.simulator:
                self.simulator.set_status("Shutting down...")
            cleanup_gpio(self.simulated)
            
            if not self.simulated:
                # On Raspberry Pi: execute system shutdown
                Popen(['shutdown', '-h', 'now'])
            else:
                # In simulation: just close the GUI
                print("(Simulated shutdown - closing in 2 seconds)")
                sleep(2)
                if self.simulator:
                    self.simulator.destroy()
                sys.exit(0)
        
        # Button 1: Mode (cycle through light patterns)
        elif index == 1:
            if was_playing:
                # If playing: stop the song and restore previous light pattern
                print("Stopping playback...")
                self.auto_play = False  # Disable auto-advance to prevent next song from starting
                self._stop_song()
                self.light_mode = self.previous_light_mode
                sleep(1)
            else:
                # If not playing: cycle through light modes (0->1->2->3->0)
                self.light_mode = (self.light_mode + 1) % 4
            
            print(f"Light mode: {self.light_mode}")
            self._flash_lights(self.light_mode)
            self._update_status()
        
        # Button 2: Lightshow (start music)
        elif index == 2:
            if was_playing:
                # If already playing: skip to next song
                print("Already playing, skipping to next song...")
                self._stop_song()
                sleep(1)
            else:
                # If not playing: save current mode to restore after all songs finish
                self.previous_light_mode = self.light_mode
            
            self._flash_lights(-1)  # Turn off all lights before starting
            self.light_mode = 4  # Set to "song playing" mode
            self.auto_play = True  # Enable auto-advance through playlist
            self._start_next_song()
            self._update_status()
    
    def _clear_debounce(self):
        """Clear button debounce flag after 0.5s timeout.
        
        Called by Timer after button press to re-enable button responsiveness.
        """
        self.debounce = False
    
    def _start_next_song(self):
        """Start playing the next song in the playlist.
        
        Loads the song JSON, creates the audio player, and initializes the interpreter.
        If the MP3 file is missing, falls back to timing simulation without audio.
        """
        if not self.available_songs:
            print("No songs available!")
            self.light_mode = 1
            self._flash_lights(self.light_mode)
            return
        
        # Load song data from JSON file via song_loader
        song_id = self.available_songs[self.current_song_index]
        song_data = self.song_loader.get_song(song_id)  # Full JSON with beats/phrases
        song_info = self.song_loader.get_song_info(song_id)  # Metadata (title, artist, mp3_file)
        
        self.current_song_id = song_id
        
        print(f"\n{'='*60}")
        print(f"Starting: {song_info['title']}")
        print(f"Artist: {song_info['artist']}")
        print(f"{'='*60}\n")
        
        # Locate MP3 file (try relative to songs_dir first, then absolute path)
        mp3_path = os.path.join(self.songs_dir, song_info['mp3_file'])
        if not os.path.exists(mp3_path):
            mp3_path = song_info['mp3_file']  # Try absolute path
        
        mp3_exists = os.path.exists(mp3_path)
        if not mp3_exists:
            print(f"WARNING: MP3 file not found: {mp3_path}")
            print("Lightshow will run with timing simulation only (no audio)")
        
        # Use simulated player only if MP3 doesn't exist
        # When --simulate flag is used with existing MP3, try VLC for audio
        # (SimulatedPlayer uses internal timing, VLCPlayer synchronizes to audio)
        use_simulated = not mp3_exists
        
        self.player = create_player(
            mp3_path,
            end_callback=self._song_ended,  # Called when song finishes
            sync_callback=self._sync_callback,  # Called periodically with playback position
            simulated=use_simulated
        )
        
        # Create interpreter to execute beat sequences from JSON
        self.interpreter = SongInterpreter(self.channels, self.player)
        self.interpreter.load_song(song_data)
        
        # Wait for player to initialize audio device (prevents initial timing drift)
        sleep(0.5)
    
    def _sync_callback(self, position: float):
        """Called periodically with current playback position.
        
        Args:
            position: Current playback time in seconds (from player)
        
        This callback detects when the player has started and triggers the interpreter
        to begin executing beat sequences. Only acts on the first sync event.
        """
        if self.interpreter and not self.interpreter.section_states:
            # First sync - interpreter hasn't started yet (section_states is empty)
            # Start the interpreter to begin scheduling beat timers
            self.interpreter.start(finished_callback=None)
    
    def _song_ended(self):
        """Called when a song finishes playing.
        
        Handles playlist advancement:
        - If auto_play is enabled: advance to next song, or loop back to previous mode
        - If auto_play is disabled (Mode button pressed): just stop
        """
        print(f"\n{'='*60}")
        print("Song finished")
        print(f"{'='*60}\n")
        
        # Cleanup interpreter and player resources
        if self.interpreter:
            self.interpreter.stop()
            self.interpreter = None
        
        self.player = None
        
        # Only continue if auto-play is enabled
        # (Mode button sets auto_play=False to stop playback)
        if not self.auto_play:
            return
        
        # Move to next song in playlist
        self.current_song_index = (self.current_song_index + 1) % len(self.available_songs)
        
        # Check if we've looped back to the beginning (all songs complete)
        if self.current_song_index == 0:
            # All songs finished - restore the light mode from before Lightshow button was pressed
            print("All songs complete. Returning to previous light mode.")
            self.light_mode = self.previous_light_mode
            self.auto_play = False
            self._flash_lights(self.light_mode)
            self._update_status()
        else:
            # More songs to play - brief pause before next song
            sleep(1)
            self._start_next_song()
    
    def _stop_song(self):
        """Stop currently playing song and cleanup resources.
        
        Cancels all pending beat timers and stops audio playback.
        Called when Mode button is pressed during playback.
        """
        if self.interpreter:
            self.interpreter.stop()  # Cancel all pending beat timers
            self.interpreter = None
        
        if self.player:
            self.player.stop()  # Stop audio playback
            self.player = None
        
        self.current_song_id = None
    
    def _flash_lights(self, mode: int):
        """Set light pattern mode.
        
        Args:
            mode: -1=all off, 0=all on (always), 1=slow flash (5s scale),
                  2=medium flash (3s scale), 3=fast flash (0.5s scale)
        
        Flash modes use recursive timers to create continuous random patterns.
        Each channel flashes independently at random intervals within the time scale.
        """
        # Cancel existing flash timers to prevent overlapping patterns
        for timer in self.flash_timers:
            timer.cancel()
        
        if mode == -1:
            # Turn all off (used during shutdown and before song start)
            for channel in self.channels:
                channel.off()
        elif mode == 0:
            # Always on (no flashing)
            for channel in self.channels:
                channel.on()
        else:
            # Random flashing at different speeds (modes 1-3)
            # Start each channel's flash pattern independently
            for i, channel in enumerate(self.channels):
                self._flash_off(i, mode)
    
    def _flash_off(self, channel_idx: int, mode: int):
        """Turn channel off and schedule next flash on.
        
        Args:
            channel_idx: Index of channel to control (0-9)
            mode: Flash mode (1=slow, 2=medium, 3=fast)
        
        Creates recursive timer pattern: off -> (random delay) -> on -> off -> ...
        Random delay is scaled by mode (slow=5s, medium=3s, fast=0.5s).
        """
        if mode == 0:
            # Mode 0 (always on) shouldn't reach here, but handle defensively
            self._flash_on(channel_idx, mode)
            return
        
        # Map mode to time scale: 1=slow (5s), 2=medium (3s), 3=fast (0.5s)
        scaler = {1: 5.0, 2: 3.0, 3: 0.5}.get(mode, 3.0)
        r = random()  # Random value 0.0-1.0
        
        self.channels[channel_idx].off()
        
        # Schedule next flash_on after random delay (0 to scaler seconds)
        self.flash_timers[channel_idx] = Timer(
            r * scaler, self._flash_on, [channel_idx, mode]
        )
        self.flash_timers[channel_idx].start()
    
    def _flash_on(self, channel_idx: int, mode: int):
        """Turn channel on and schedule next flash off.
        
        Args:
            channel_idx: Index of channel to control (0-9)
            mode: Flash mode (0=always on, 1=slow, 2=medium, 3=fast)
        
        Creates recursive timer pattern: on -> (random delay) -> off -> on -> ...
        If mode=0 (always on), does not schedule flash_off (stops recursion).
        """
        self.channels[channel_idx].on()
        
        if mode != 0:
            # Schedule next flash_off after random delay (continues recursion)
            scaler = {1: 5.0, 2: 3.0, 3: 0.5}.get(mode, 3.0)
            r = random()  # Random value 0.0-1.0
            
            self.flash_timers[channel_idx] = Timer(
                r * scaler, self._flash_off, [channel_idx, mode]
            )
            self.flash_timers[channel_idx].start()
    
    def run(self):
        """Main run loop.
        
        In simulation mode: runs the Tkinter GUI (blocking until window closed)
        In hardware mode: infinite loop checking for API triggers every second
        
        API Integration:
        - Environment variables LIGHTSHOW_CHECK and LIGHTSHOW_DONE can specify URLs
        - Every second, checks LIGHTSHOW_CHECK URL
        - If response is "1", calls LIGHTSHOW_DONE and triggers lightshow
        - Allows external systems (home automation, web API) to start lightshow
        """
        try:
            if self.simulator:
                # In simulation mode, run the GUI (blocks until window closed)
                print("Running in simulation mode. Close window to exit.")
                self.simulator.run()
            else:
                # In hardware mode, keep running and check for API triggers
                while True:
                    sleep(1)
                    
                    # Check integration API if configured
                    # Only check when not playing (light_mode != 4)
                    if self.light_mode != 4 and self.integration_check:
                        try:
                            import requests
                            # Check if external system wants to trigger lightshow
                            r = requests.get(self.integration_check, timeout=5)
                            if r.text == "1":
                                # Acknowledge the trigger by calling done URL
                                try:
                                    requests.get(self.integration_done, timeout=5)
                                    # Simulate Lightshow button press
                                    self._button_callback(2, True)
                                except:
                                    print("Problem connecting to done API")
                                    sleep(10)
                        except:
                            print("Problem connecting to check API")
                            sleep(10)
        
        except KeyboardInterrupt:
            print("\nShutting down...")
        
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """Cleanup resources on shutdown.
        
        Performs orderly shutdown:
        1. Stop any playing song (cancel timers, stop audio)
        2. Turn off all lights
        3. Release GPIO pins (on Pi hardware)
        4. Close GUI window (in simulation)
        5. Force exit to terminate all threads
        """
        print("Cleaning up...")
        
        # Stop any playing song (cancels beat timers, stops audio)
        if self.player:
            self._stop_song()
        
        # Turn off all lights
        self._flash_lights(-1)
        
        # Cleanup GPIO pins (releases hardware resources on Pi)
        cleanup_gpio(self.simulated)
        
        # Close simulator window
        if self.simulator:
            try:
                self.simulator.destroy()
            except:
                pass
        
        print("Goodbye!")
        
        # Force exit to ensure all threads (timers, GUI) are stopped
        import os
        os._exit(0)


def main():
    """Main entry point.
    
    Command-line arguments:
    --simulate: Run with GUI simulator instead of GPIO hardware
    --songs-dir: Specify directory containing song JSON files (default: songs)
    
    Usage:
    python lightshow.py --simulate                    # Test on any computer
    python lightshow.py --songs-dir /path/to/songs    # Use custom song directory
    sudo python lightshow.py                           # Run on Raspberry Pi (sudo needed for GPIO)
    """
    parser = argparse.ArgumentParser(description='Pi Lightshow Controller')
    parser.add_argument(
        '--simulate',
        action='store_true',
        help='Run in simulation mode with GUI (no hardware required)'
    )
    parser.add_argument(
        '--songs-dir',
        default='songs',
        help='Directory containing song JSON files (default: songs)'
    )
    
    args = parser.parse_args()
    
    controller = LightshowController(
        simulated=args.simulate,
        songs_dir=args.songs_dir
    )
    
    controller.run()


if __name__ == "__main__":
    main()
