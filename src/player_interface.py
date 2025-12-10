"""<br/>Audio Player Abstraction

Provides implementations for audio playback on different platforms:
- OMXPlayerWrapper: Hardware-accelerated playback on Raspberry Pi
- VLCPlayer: Cross-platform playback for development (with wall-clock timing)
- SimulatedPlayer: Timing simulation without audio (for testing without MP3)

All players implement PlayerInterface for consistent API.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from time import sleep, time
from threading import Thread
from typing import Optional, Callable
import os


class PlayerInterface(ABC):
    """Abstract base class for audio players.
    
    All player implementations must provide:
    - position(): Current playback time in seconds
    - stop(): Stop playback and cleanup resources
    """
    
    @abstractmethod
    def position(self) -> float:
        """Get current playback position in seconds.
        
        Returns:
            Current playback time in seconds, or -1 if not playing
        """
        pass
    
    @abstractmethod
    def stop(self):
        """Stop playback and cleanup resources."""
        pass


class OMXPlayerWrapper(PlayerInterface):
    """Wrapper for OMXPlayer on Raspberry Pi.
    
    OMXPlayer is hardware-accelerated audio player optimized for Raspberry Pi.
    Runs in separate thread and provides callbacks for sync and completion.
    """
    
    def __init__(self, path: str, end_callback: Optional[Callable] = None, 
                 sync_callback: Optional[Callable] = None):
        """
        Initialize OMXPlayer.
        
        Args:
            path: Path to audio file (MP3, WAV, etc.)
            end_callback: Called when playback ends naturally
            sync_callback: Called periodically with current position for timing sync
        """
        from omxplayer.player import OMXPlayer
        
        self.player = None
        self.finished = False
        self.path = Path(path)
        self.sync_callback = sync_callback
        self.end_callback = end_callback
        
        # Start playback in separate thread (OMXPlayer is blocking)
        self.music_thread = Thread(target=self._play)
        self.music_thread.start()
    
    def _play(self):
        """Play the audio file in separate thread.
        
        Creates OMXPlayer instance, registers event handlers, and polls
        position every 0.5s for sync callback until playback finishes.
        """
        from omxplayer.player import OMXPlayer
        
        # Create player with local audio output (not HDMI)
        self.player = OMXPlayer(self.path, args="-o local")
        self.player.exitEvent = self._exit_event  # Called when playback ends
        self.player.stopEvent = self._stop_event  # Called when stopped manually
        
        # Poll position until finished
        while not self.finished:
            sleep(0.5)
            if self.sync_callback is not None and not self.finished:
                self.sync_callback(self.player.position())  # Report current position
        
        # Cleanup
        if self.player is not None:
            self.player.quit()
            self.player = None
    
    def position(self) -> float:
        """Get current playback position.
        
        Returns:
            Current playback time in seconds, or -1 if not playing
        """
        if self.player is not None:
            return self.player.position()
        return -1
    
    def stop(self):
        """Stop playback and cleanup."""
        if self.player is not None:
            self.player.quit()
            self.player = None
    
    def _exit_event(self, player, exit_status):
        """Handle player exit (playback complete)."""
        self.finished = True
        if self.end_callback is not None:
            self.end_callback()
            self.end_callback = None  # Prevent double-call
    
    def _stop_event(self, player):
        """Handle player stop (manual stop)."""
        self.finished = True
        if self.end_callback is not None:
            self.end_callback()
            self.end_callback = None  # Prevent double-call


class SimulatedPlayer(PlayerInterface):
    """Simulated audio player for development without actual audio playback.
    
    Provides accurate timing simulation without playing audio.
    Useful for:
    - Testing lightshow timing without MP3 files
    - Development on systems without audio hardware
    - Verifying beat synchronization logic
    
    Uses wall-clock time (time.time()) for position tracking.
    """
    
    def __init__(self, path: str, end_callback: Optional[Callable] = None,
                 sync_callback: Optional[Callable] = None, duration: float = 300.0):
        """
        Initialize simulated player.
        
        Args:
            path: Path to audio file (not actually played, just for reference)
            end_callback: Called when simulation duration completes
            sync_callback: Called periodically with simulated position
            duration: Total duration to simulate in seconds (default: 300s = 5 minutes)
        """
        self.path = Path(path)
        self.sync_callback = sync_callback
        self.end_callback = end_callback
        self.duration = duration
        self.start_time = time()  # Wall-clock start time
        self.finished = False
        self.stopped = False
        
        # Run simulation in separate thread
        self.playback_thread = Thread(target=self._simulate_playback)
        self.playback_thread.start()
        
        print(f"[SimulatedPlayer] Starting playback of {path}")
        print(f"[SimulatedPlayer] Duration: {duration:.1f}s")
    
    def _simulate_playback(self):
        """Simulate playback in a thread.
        
        Polls every 0.5s and calls sync_callback with current position.
        When duration is reached, calls end_callback.
        """
        while not self.stopped and not self.finished:
            sleep(0.5)
            
            current_pos = self.position()
            
            # Call sync callback periodically (like real player would)
            if self.sync_callback is not None and not self.finished:
                self.sync_callback(current_pos)
            
            # Check if we've reached the simulated end
            if current_pos >= self.duration:
                self.finished = True
                if self.end_callback is not None:
                    print(f"[SimulatedPlayer] Playback complete")
                    self.end_callback()
                    self.end_callback = None  # Prevent double-call
                break
    
    def position(self) -> float:
        """Get current playback position (wall-clock based).
        
        Returns:
            Elapsed time since start in seconds, or -1 if stopped
        """
        if self.stopped or self.finished:
            return -1
        return time() - self.start_time  # Wall-clock elapsed time
    
    def stop(self):
        """Stop playback simulation."""
        self.stopped = True
        print(f"[SimulatedPlayer] Stopped at {self.position():.1f}s")


class VLCPlayer(PlayerInterface):
    """VLC-based player for development on Linux.
    
    Uses wall-clock timing instead of VLC's get_time() for better accuracy.
    
    IMPORTANT TIMING NOTES:
    - VLC's get_time() lags 0.5-0.9s behind actual audio playback
    - Solution: Track playback_start_time and use wall-clock elapsed time
    - Waits for is_playing() + 0.1s before recording start time
    - This approach gives near-zero timing error from first beat
    
    Falls back to SimulatedPlayer if python-vlc is not installed.
    """
    
    def __init__(self, path: str, end_callback: Optional[Callable] = None,
                 sync_callback: Optional[Callable] = None):
        """
        Initialize VLC player.
        
        Args:
            path: Path to audio file (MP3, WAV, etc.)
            end_callback: Called when playback ends naturally
            sync_callback: Called periodically with current position for timing sync
        """
        try:
            import vlc
            self.vlc = vlc
        except ImportError:
            print("WARNING: python-vlc not installed. Falling back to simulated player.")
            # Fall back to simulated player
            self._fallback = SimulatedPlayer(path, end_callback, sync_callback)
            self.is_fallback = True
            return
        
        self.is_fallback = False
        self.path = Path(path)
        self.sync_callback = sync_callback
        self.end_callback = end_callback
        self.finished = False
        
        # Create VLC instance and player
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()
        
        # Load and play media
        media = self.instance.media_new(str(self.path))
        self.player.set_media(media)
        self.player.play()
        
        # Wait for VLC to actually start playing before recording start time
        # This ensures audio device is initialized and buffering has started
        from time import time, sleep
        max_wait = 2.0
        waited = 0.0
        while waited < max_wait:
            if self.player.is_playing():
                break
            sleep(0.01)
            waited += 0.01
        
        # Add a small additional delay to account for audio buffering/device init
        # This prevents timing issues at the very beginning of playback
        # Without this, first beat can be 0.1-0.2s early
        sleep(0.1)
        
        # Record wall-clock start time AFTER VLC has started and buffered
        # This is the reference point for all timing calculations
        self.playback_start_time = time()
        
        # Start monitoring thread for end detection and sync callbacks
        self.monitor_thread = Thread(target=self._monitor)
        self.monitor_thread.start()
        
        print(f"[VLCPlayer] Playing {path}")
    
    def _monitor(self):
        """Monitor playback and call callbacks.
        
        Runs in separate thread, polling VLC state every 0.5s.
        Calls sync_callback with current position and end_callback when finished.
        """
        while not self.finished:
            sleep(0.5)
            
            state = self.player.get_state()
            
            # Call sync callback with current position
            if self.sync_callback is not None and not self.finished:
                self.sync_callback(self.position())
            
            # Check if finished (VLC stopped or reached end)
            if state == self.vlc.State.Ended or state == self.vlc.State.Stopped:
                self.finished = True
                if self.end_callback is not None:
                    print(f"[VLCPlayer] Playback complete")
                    self.end_callback()
                    self.end_callback = None  # Prevent double-call
                break
    
    def position(self) -> float:
        """Get current playback position in seconds.
        
        CRITICAL: Uses wall-clock time, NOT VLC's get_time().
        
        VLC's get_time() lags 0.5-0.9s behind actual audio playback.
        Wall-clock approach: elapsed = time.time() - playback_start_time
        
        This gives accurate timing from the first beat (near-zero error).
        
        Returns:
            Elapsed time since playback started, or -1 if not playing
        """
        if self.is_fallback:
            return self._fallback.position()
        
        if self.player and not self.finished:
            # Use wall-clock time for more accurate sync
            # VLC's get_time() can lag behind actual playback by 0.5-0.9s
            from time import time
            elapsed = time() - self.playback_start_time
            return elapsed
        return -1
    
    def stop(self):
        """Stop playback and cleanup resources."""
        if self.is_fallback:
            self._fallback.stop()
            return
        
        self.finished = True
        if self.player:
            self.player.stop()
            self.player.release()  # Release VLC resources
        
        # Wait for monitor thread to finish (with timeout to prevent hanging)
        if hasattr(self, 'monitor_thread') and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)
        
        print(f"[VLCPlayer] Stopped")


def create_player(path: str, end_callback: Optional[Callable] = None,
                  sync_callback: Optional[Callable] = None, 
                  simulated: bool = False) -> PlayerInterface:
    """
    Create an appropriate player based on the environment.
    
    Factory function that selects the best player for the current platform:
    - Simulated: If simulated=True or MP3 doesn't exist
    - OMXPlayerWrapper: If running on Raspberry Pi (hardware-accelerated)
    - VLCPlayer: On other systems (Linux, Mac, Windows)
    
    Args:
        path: Path to audio file (MP3, WAV, etc.)
        end_callback: Called when playback ends naturally
        sync_callback: Called periodically with current position for timing sync
        simulated: If True, use simulated player (no actual audio)
    
    Returns:
        PlayerInterface instance (OMXPlayerWrapper, VLCPlayer, or SimulatedPlayer)
    """
    if simulated:
        # Use simulated player with estimated duration
        # Try to determine duration from filename or use default
        duration = 300.0  # Default 5 minutes
        if 'carol' in path.lower():
            duration = 220.0  # Approximate duration of Carol of the Bells
        elif 'russian' in path.lower():
            duration = 280.0  # Approximate duration of Mad Russian
        
        return SimulatedPlayer(path, end_callback, sync_callback, duration)
    
    # Try to detect if we're on a Raspberry Pi
    # Raspberry Pi has /proc/device-tree/model file with "Raspberry Pi" in it
    is_raspberry_pi = False
    try:
        with open('/proc/device-tree/model', 'r') as f:
            model = f.read()
            if 'Raspberry Pi' in model:
                is_raspberry_pi = True
    except:
        pass  # Not on Raspberry Pi or file doesn't exist
    
    # Try OMXPlayer on Raspberry Pi (optimized for Pi hardware)
    if is_raspberry_pi:
        try:
            print("Detected Raspberry Pi, attempting to use OMXPlayer...")
            return OMXPlayerWrapper(path, end_callback, sync_callback)
        except ImportError as e:
            print(f"WARNING: OMXPlayer not available ({e}). Falling back to VLC/simulated player.")
        except Exception as e:
            print(f"WARNING: OMXPlayer initialization failed ({e}). Falling back to VLC/simulated player.")
    
    # On other systems (Linux, Mac, Windows), try VLC
    try:
        return VLCPlayer(path, end_callback, sync_callback)
    except:
        # Fall back to simulated if VLC fails to load
        print("Falling back to simulated player")
        return SimulatedPlayer(path, end_callback, sync_callback)
