"""
Song Loader and Interpreter Module

This module loads song definition JSON files and interprets them
to generate lightshow commands for the channel controller.
"""

import json
import os
from threading import Timer
from typing import Dict, List, Any, Callable, Optional


class SongLoader:
    """Loads and parses song definition JSON files.
    
    Manages a library of songs stored as JSON files in the songs directory.
    Supports playlist ordering via playlist.json, otherwise uses alphabetical order.
    
    Attributes:
        songs_directory: Path to directory containing song JSON files
        songs: Dict mapping song_id to parsed JSON data
        playlist_order: List of song IDs in desired playback order
    """
    
    def __init__(self, songs_directory: str = "songs"):
        self.songs_directory = songs_directory
        self.songs = {}  # song_id -> full song JSON
        self.playlist_order = []  # ordered list of song IDs
        self.load_all_songs()
        self.load_playlist()
    
    def load_all_songs(self):
        """Load all JSON files from the songs directory.
        
        Scans the songs directory for .json files (excluding playlist.json)
        and loads each one into the songs dictionary. Song ID is derived from
        filename (e.g., 'carol-of-the-bells.json' -> 'carol-of-the-bells').
        """
        if not os.path.exists(self.songs_directory):
            print(f"Warning: Songs directory '{self.songs_directory}' does not exist")
            return
        
        for filename in os.listdir(self.songs_directory):
            if filename.endswith('.json') and filename != 'playlist.json':
                filepath = os.path.join(self.songs_directory, filename)
                try:
                    with open(filepath, 'r') as f:
                        song_data = json.load(f)
                        song_id = os.path.splitext(filename)[0]  # Remove .json extension
                        self.songs[song_id] = song_data
                        print(f"Loaded song: {song_data.get('title', song_id)}")
                except Exception as e:
                    print(f"Error loading {filename}: {e}")
    
    def load_playlist(self):
        """Load playlist order from playlist.json if it exists.
        
        playlist.json format:
        {
            "playlist": ["song-id-1", "song-id-2", ...]
        }
        
        If playlist.json doesn't exist, songs will play in alphabetical order.
        """
        playlist_path = os.path.join(self.songs_directory, 'playlist.json')
        if os.path.exists(playlist_path):
            try:
                with open(playlist_path, 'r') as f:
                    playlist_data = json.load(f)
                    self.playlist_order = playlist_data.get('playlist', [])
                    print(f"Loaded playlist with {len(self.playlist_order)} songs")
            except Exception as e:
                print(f"Error loading playlist.json: {e}")
                self.playlist_order = []
    
    def get_song(self, song_id: str) -> Optional[Dict]:
        """Get a specific song's full JSON data by its ID.
        
        Args:
            song_id: Song identifier (filename without .json)
        
        Returns:
            Dict containing song data (sections, timing, phrases, etc.) or None
        """
        return self.songs.get(song_id)
    
    def list_songs(self) -> List[str]:
        """List all available song IDs in playlist order (or alphabetical if no playlist).
        
        Returns:
            List of song IDs in playback order
        """
        if self.playlist_order:
            # Use playlist order, but only include songs that were actually loaded
            return [song_id for song_id in self.playlist_order if song_id in self.songs]
        else:
            # Fall back to alphabetical order
            return sorted(list(self.songs.keys()))
    
    def get_song_info(self, song_id: str) -> Optional[Dict]:
        """Get basic metadata about a song.
        
        Args:
            song_id: Song identifier
        
        Returns:
            Dict with keys: id, title, artist, description, mp3_file
        """
        song = self.get_song(song_id)
        if song:
            return {
                'id': song_id,
                'title': song.get('title', 'Unknown'),
                'artist': song.get('artist', 'Unknown'),
                'description': song.get('description', ''),
                'mp3_file': song.get('mp3_file', '')
            }
        return None


class SongInterpreter:
    """Interprets song definitions and executes lightshow sequences.
    
    Schedules beat-synchronized light actions using Threading.Timer.
    Supports multi-section songs with different tempos and segmented sections.
    
    Attributes:
        channels: List of channel objects (0-indexed, channels[0] = physical channel 1)
        player: Audio player providing playback position for synchronization
        song_data: Loaded song JSON (sections, phrases, timing)
        active_timers: List of pending Timer objects (cancelled on stop)
        section_states: Dict tracking beat progress for each section/segment
        finished_callback: Optional callback when all sections complete
    """
    
    def __init__(self, channels: List[Any], player: Any):
        """
        Initialize the interpreter.
        
        Args:
            channels: List of channel objects (0-indexed, channels[0] = channel 1)
            player: Audio player object with position() method for timing sync
        """
        self.channels = channels
        self.player = player
        self.song_data = None
        self.active_timers = []  # All pending timers (for cancellation)
        self.section_states = {}  # Tracks beat progress per section
        self.finished_callback = None
        
    def load_song(self, song_data: Dict):
        """Load a song definition from JSON.
        
        Args:
            song_data: Parsed JSON with sections, phrases, timing metadata
        """
        self.song_data = song_data
        self.section_states = {}  # Reset state for new song
        
    def start(self, finished_callback: Optional[Callable] = None):
        """Start playing the lightshow.
        
        Schedules all section/segment start times and begins beat execution.
        Uses player.position() to calculate delays relative to audio playback.
        
        Args:
            finished_callback: Optional callback when all sections complete
        """
        if not self.song_data:
            print("Error: No song loaded")
            return
        
        self.finished_callback = finished_callback
        self.cancel_all_timers()  # Clear any existing timers
        
        # Turn off all channels at start (clean slate)
        for channel in self.channels:
            channel.off()
        
        # Schedule section starts based on song structure
        for section in self.song_data.get('sections', []):
            section_name = section.get('name', 'unnamed')
            
            # Handle sections with segments (e.g., Mad Russian with varying tempos)
            if 'segments' in section:
                for seg_idx, segment in enumerate(section['segments']):
                    self._schedule_segment_start(section_name, seg_idx, segment)
            # Handle sections with single timing (e.g., Carol of the Bells)
            else:
                self._schedule_section_start(section_name, section)
    
    def _schedule_section_start(self, section_name: str, section: Dict):
        """Schedule the start of a section.
        
        Args:
            section_name: Identifier for this section (e.g., 'prelude', 'main')
            section: Section JSON data with start_time, tempo, sequences
        """
        start_time = section.get('start_time', 0)
        position = self.player.position()  # Current audio playback position
        delay = start_time - position  # How long until this section starts
        
        if delay < 0:
            delay = 0  # Don't try to schedule in the past
        
        # Create state tracker for this section
        state_key = section_name
        self.section_states[state_key] = {
            'current_beat': 0,  # Which beat we're on (0-indexed)
            'finished': False,  # Has this section completed?
            'tempo': section.get('tempo', 1.0),  # Seconds per beat
            'total_beats': section.get('total_beats', 0),  # Total beats in section
            'start_time': start_time,  # Absolute start time in song
            'sequences': section.get('sequences', []),  # Beat sequences to execute
            'phrases': self.song_data.get('phrases', {})  # Reusable phrases
        }
        
        # Schedule first beat execution after delay
        timer = Timer(delay, self._execute_beat, [state_key])
        timer.start()
        self.active_timers.append(timer)
    
    def _schedule_segment_start(self, section_name: str, seg_idx: int, segment: Dict):
        """Schedule the start of a segment within a section.
        
        Segments allow multi-tempo sections (e.g., Mad Russian has 3 segments
        with different tempos: prelude, main, finale).
        
        Args:
            section_name: Section identifier (e.g., 'main')
            seg_idx: Segment index within section (0, 1, 2, ...)
            segment: Segment JSON data with start_time, tempo, sequences
        """
        start_time = segment.get('start_time', 0)
        position = self.player.position()  # Current audio playback position
        delay = start_time - position  # How long until this segment starts
        
        if delay < 0:
            delay = 0  # Don't try to schedule in the past
        
        # Create state tracker for this segment (unique key per segment)
        state_key = f"{section_name}_{seg_idx}"
        self.section_states[state_key] = {
            'current_beat': 0,  # Which beat we're on (0-indexed)
            'finished': False,  # Has this segment completed?
            'tempo': segment.get('tempo', 1.0),  # Seconds per beat
            'total_beats': segment.get('total_beats', 0),  # Total beats in segment
            'start_time': start_time,  # Absolute start time in song
            'sequences': segment.get('sequences', [])  # Beat sequences to execute
        }
        
        # Schedule first beat execution after delay
        timer = Timer(delay, self._execute_beat, [state_key])
        timer.start()
        self.active_timers.append(timer)
    
    def _execute_beat(self, state_key: str):
        """Execute actions for the current beat.
        
        CRITICAL PATTERN: Schedule next beat FIRST, then execute current beat.
        This prevents cumulative timing drift from execution delays.
        
        Args:
            state_key: Section/segment identifier (e.g., 'main' or 'main_1')
        
        Flow:
        1. Increment beat counter
        2. Check if section is finished
        3. Calculate next beat's absolute time from section start + (beat * tempo)
        4. Schedule next beat's timer
        5. Execute current beat's actions
        
        This ensures timing is synchronized to audio playback, not cumulative delays.
        """
        if state_key not in self.section_states:
            return
        
        state = self.section_states[state_key]
        
        if state['finished']:
            return
        
        # Increment beat counter (starts at 1)
        state['current_beat'] += 1
        current_beat = state['current_beat']
        tempo = state['tempo']  # Seconds per beat
        total_beats = state['total_beats']
        
        # Check if this section/segment is finished
        if current_beat > total_beats:
            state['finished'] = True
            self._check_if_all_finished()  # See if entire song is done
            return
        
        # Calculate when the NEXT beat should occur (absolute time from section start)
        # This prevents drift: each beat is scheduled relative to section start, not previous beat
        next_beat_time = state['start_time'] + (current_beat * tempo)
        position = self.player.position()  # Current audio position
        delay = next_beat_time - position  # Delay until next beat
        
        if delay < 0:
            delay = 0
        
        # Schedule next beat FIRST (prevents cumulative drift)
        # This ensures timing is based on absolute song position, not execution delays
        timer = Timer(delay, self._execute_beat, [state_key])
        timer.start()
        self.active_timers.append(timer)
        
        # NOW execute actions for this beat
        # Iterate through all sequences to find which apply to current beat
        for sequence in state['sequences']:
            # Check if this sequence applies to current beat
            should_execute = False
            
            if sequence.get('all_beats', False):
                # Execute on every beat in this section
                should_execute = True
            elif 'beat' in sequence and sequence['beat'] == current_beat:
                # Execute on specific beat number
                should_execute = True
            elif 'beats' in sequence and current_beat in sequence['beats']:
                # Execute on any beat in the list
                should_execute = True
            
            if should_execute:
                # Execute all actions in this sequence
                for action in sequence.get('actions', []):
                    self._execute_action(action, tempo)
    
    def _execute_action(self, action: Dict, tempo: float):
        """Execute a single action.
        
        Action types:
        - 'note': Turn on a single channel for a duration
        - 'phrase': Execute a predefined sequence of notes (reusable pattern)
        - 'all_channels': Turn on all 10 channels simultaneously
        - 'step_up': Light channels sequentially in order
        - 'step_down': Turn off channels in reverse order
        
        Args:
            action: Action dict with 'type' and type-specific parameters
            tempo: Current section tempo (seconds per beat) for timing calculations
        """
        action_type = action.get('type')
        
        if action_type == 'note':
            # Single note on a specific channel
            # Channels are 0-indexed: 0 = physical channel 1, 9 = physical channel 10
            channel_idx = action.get('channel', 0)
            delay = action.get('delay', 0)  # Delay before turning on (seconds)
            duration = action.get('duration', 0.1)  # How long to stay on (seconds)
            
            if channel_idx < len(self.channels):
                # Schedule channel.on() after delay
                timer = Timer(delay, self.channels[channel_idx].on, [duration])
                timer.start()
                self.active_timers.append(timer)
        
        elif action_type == 'phrase':
            # Play a predefined phrase (reusable note sequence)
            # Phrases are defined in song JSON and referenced by ID
            phrase_id = str(action.get('id', 0))
            
            # Look up phrase from section state or song data
            phrases = self.section_states.get(list(self.section_states.keys())[0], {}).get('phrases', {})
            if not phrases:
                phrases = self.song_data.get('phrases', {})
            
            if phrase_id in phrases:
                self._execute_phrase(phrases[phrase_id], tempo)
        
        elif action_type == 'all_channels':
            # Turn on all channels simultaneously
            # Used for impactful moments (e.g., Mad Russian flashes every beat)
            duration = action.get('duration', 0.25)  # Fixed duration in seconds
            duration_multiplier = action.get('duration_multiplier', 1.0)  # Or multiply by tempo
            actual_duration = duration if duration > 0 else tempo * duration_multiplier
            
            for channel in self.channels:
                channel.on(actual_duration)
        
        elif action_type == 'step_up':
            # Light up channels in sequence (visual wave effect)
            self._step_up(tempo)
        
        elif action_type == 'step_down':
            # Turn off channels in reverse sequence
            self._step_down(tempo)
        
        elif action_type == 'flash_mode':
            # Reserved for future use (mode changes during song)
            pass
    
    def _execute_phrase(self, phrase: Dict, tempo: float):
        """Execute a phrase (sequence of notes).
        
        Phrases are reusable patterns defined in song JSON.
        Each note in the phrase has tempo-relative timing.
        
        Args:
            phrase: Phrase dict with 'notes' list
            tempo: Current section tempo for timing calculations
        """
        notes = phrase.get('notes', [])
        
        for note in notes:
            channel_idx = note.get('channel', 0)  # 0-indexed
            delay_multiplier = note.get('delay_multiplier', 0)  # Multiply by tempo
            duration_multiplier = note.get('duration_multiplier', 0.33)  # Multiply by tempo
            
            delay = tempo * delay_multiplier
            duration = tempo * duration_multiplier
            
            if channel_idx < len(self.channels):
                if delay == 0:
                    # Immediate execution
                    self.channels[channel_idx].on(duration)
                else:
                    # Scheduled execution
                    timer = Timer(delay, self.channels[channel_idx].on, [duration])
                    timer.start()
                    self.active_timers.append(timer)
    
    def _step_up(self, tempo: float):
        """Light up all channels in order (visual wave effect).
        
        Args:
            tempo: Current section tempo for timing
        
        Channel order: 10, 9, 2, 7, 6, 4, 3, 5, 8, 1 (based on physical layout)
        """
        order = [9, 8, 1, 6, 5, 3, 2, 4, 7, 0]  # 0-indexed channel numbers
        for x in range(10):
            if x == 0:
                # First channel turns on immediately
                self.channels[order[x]].on(tempo)
            else:
                # Subsequent channels turn on with staggered delays
                timer = Timer(tempo * 0.1 * float(x), self.channels[order[x]].on)
                timer.start()
                self.active_timers.append(timer)
    
    def _step_down(self, tempo: float):
        """Turn off all channels in reverse order.
        
        Args:
            tempo: Current section tempo for timing
        
        Channel order: 1, 8, 5, 3, 4, 6, 7, 2, 9, 10 (reverse of step_up)
        """
        order = [0, 7, 4, 2, 3, 5, 6, 1, 8, 9]  # 0-indexed channel numbers
        for x in range(10):
            if x == 9:
                # Last channel stays on indefinitely
                self.channels[order[9]].on()
            else:
                # Other channels turn on with increasing durations
                duration = tempo * 0.1 * (float(x) + 1)
                self.channels[order[x]].on(duration)
    
    def _check_if_all_finished(self):
        """Check if all sections are finished and call callback.
        
        Called after each section/segment finishes. If all are done,
        triggers the finished_callback (which advances to next song).
        """
        all_finished = all(
            state.get('finished', False) 
            for state in self.section_states.values()
        )
        
        if all_finished and self.finished_callback:
            self.finished_callback()
    
    def stop(self):
        """Stop the lightshow and cancel all timers.
        
        Called when Mode button is pressed or song is skipped.
        Cancels all pending beat timers and turns off all lights.
        """
        self.cancel_all_timers()
        for channel in self.channels:
            channel.off()
    
    def cancel_all_timers(self):
        """Cancel all active timers.
        
        Stops all pending Timer objects to prevent orphaned callbacks.
        """
        for timer in self.active_timers:
            timer.cancel()
        self.active_timers = []
