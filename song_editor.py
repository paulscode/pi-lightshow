#!/usr/bin/env python3
"""
Song Editor for Pi Lightshow

A visual timeline editor for choreographing Christmas light displays synchronized to music.
This application allows you to create and edit JSON files that define when and how 
10 channels of lights activate during a song.

Key Features:
- Visual timeline with audio waveform display
- Beat-based sequence editing aligned to music tempo
- Reusable phrase patterns for common sequences
- Real-time playback preview with synchronized visualization
- Hierarchical editing: sections → segments → sequences → actions
- Interactive controls: click to edit, right-click for context menus

Architecture Overview:
- Song Data: Hierarchical JSON (sections → segments → sequences → actions)
- Timeline: Vertical scrolling canvas (time flows downward)
- Channels: 10 columns representing physical light channels
- Playback: Dual-loop system (16ms interpolation + 200ms sync correction)
- Tags: Canvas items tagged for click detection (seq_<sec>_<seg>_<seq>_<act>)

Core Concepts:
- Section: Song part with timing (intro, verse, etc.) 
- Tempo: Duration of one beat in seconds
- Sequence: Defines WHEN (beat numbers) actions execute
- Action: Defines WHAT happens (note, phrase, all_channels, step_up/down)
- Phrase: Reusable multi-note pattern stored in library
- Multipliers: Timing expressed as ratio × tempo for flexibility

Data Flow:
1. Load MP3 → Generate waveform → Enable editing
2. Create sections with start_time, tempo, total_beats
3. Add sequences specifying beat(s) for execution
4. Add actions defining channel activations
5. Save to JSON with relative MP3 path reference
6. Playback: pygame mixer + smooth 60fps position updates

Dependencies: tkinter, pygame, numpy, pydub
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import json
import os
from typing import Dict, List, Optional, Tuple, Any
import pygame
import numpy as np
from pydub import AudioSegment
from pydub.playback import play
import threading
import time


class SongEditor:
    """Main song editor application with visual timeline interface.
    
    Architecture:
    - Song Data: Hierarchical JSON structure (sections → segments → sequences → actions)
    - Timeline Canvas: Scrollable vertical timeline showing all sequences
    - Dual-Loop Playback: Fast interpolation (60fps) + slow sync (5Hz) for smooth playback
    - Tag System: Canvas items tagged for click detection and context menus
    """
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Pi Lightshow Song Editor")
        self.root.geometry("1400x900")
        self.root.configure(bg='#2b2b2b')
        
        # ========== Song Data Structure ==========
        # JSON format with metadata, timing sections, and reusable phrase library
        self.song_data = {
            "title": "",              # Song title
            "artist": "",             # Artist name
            "description": "",        # Optional notes
            "mp3_file": "",          # Relative path to audio file
            "sections": [],          # List of timing sections (see below)
            "phrases": {}            # Library of reusable note patterns (phrase_id → phrase_data)
        }
        # Section structure: {start_time, tempo, beats, segments?, sequences}
        # Segment structure: {start_beat, end_beat, sequences}
        # Sequence structure: {beat/beats/all_beats, actions}
        # Action structure: {type, channel?, delay?, duration?, ...}
        
        # ========== File and Audio State ==========
        self.mp3_path = None                # Absolute path to loaded MP3 file
        self.audio_data = None              # AudioSegment object (pydub) for waveform processing
        self.audio_duration = 0             # Total audio length in seconds (float)
        self.waveform_data = None           # numpy array of downsampled amplitude values
        self.current_json_path = None       # File path for save operations (None if unsaved)
        
        # ========== Editor State Variables ==========
        self.current_tool = "select"        # Active tool mode: "select", "hand", "channel", "beat_marker"
        self.current_section_index = 0      # Index of selected section in sidebar (0-based)
        self.current_segment_index = None   # Index of selected segment (None if viewing full section)
        self.zoom_level = 1.0               # Timeline vertical zoom: 1.0 = 100 pixels per second
        self.scroll_position = 0            # Vertical scroll offset in seconds (not pixels)
        
        # ========== Playback State ==========
        self.playback_position = 0          # Current playback time in seconds (interpolated)
        self.is_playing = False             # True when audio is actively playing
        self.update_id = 0                  # Incremented on each play start to invalidate old async loops
        self.playback_start_position = 0    # Position where current play() started (for calculating offsets)
        self.last_actual_position = 0       # Last position from pygame mixer (for interpolation baseline)
        self.last_update_time = 0           # time.time() when last_actual_position was updated
        self.interpolation_rate = 0.016     # Fast loop interval in seconds (~60fps for smooth animation)
        self.channel_states = [False] * 10  # Track active state of each channel (0-indexed)
        self.active_notes = []              # List of (channel, end_time) tuples for currently active notes
        self.current_flash_mode = -1        # Current flash mode (-1=off, 0=always on, 1=slow, 2=med, 3=fast)
        self.flash_random_seed = 12345      # Fixed seed for reproducible "random" flash patterns
        self.flash_channel_states = [False] * 10  # Random flash states (updated periodically)
        
        # ========== UI State ==========
        self.selected_items = []            # List of selected canvas item IDs (not currently used)
        self.waveform_width = 100           # Width of waveform column in pixels (resizable 50-400)
        self.waveform_zoom = 1.0            # Amplitude zoom factor: 1.0 = 100%, 10.0 = 1000% (scroll wheel)
        self.dragging_splitter = False      # True while user drags waveform splitter handle
        self.active_context_menu = None     # Reference to open tk.Menu (dismissed on canvas click)
        self.drag_start = None              # Mouse coordinates when drag started (x, y) tuple
        self.drag_item = None               # Canvas item ID being dragged (for select tool)
        self.last_mouse_x = 0               # Cached mouse X for preview restore after scroll
        self.last_mouse_y = 0               # Cached mouse Y for preview restore after scroll
        
        # ========== Channel Configuration ==========
        # Physical layout mapping for the 10 light channels
        # Order represents left-to-right visual arrangement in simulator and timeline
        self.channel_order = [10, 9, 2, 7, 6, 4, 3, 5, 8, 1]
        
        # Visual groupings for the channel indicator bar at top of timeline
        # Format: (start_column_index, end_column_index, display_label)
        # Used to draw colored group labels above timeline columns
        self.channel_groups = [
            (0, 2, "10+9"),      # Columns 0-1: channels 10 and 9
            (2, 5, "2+7+6"),     # Columns 2-4: channels 2, 7, and 6
            (5, 7, "4+3"),       # Columns 5-6: channels 4 and 3
            (7, 9, "5+8"),       # Columns 7-8: channels 5 and 8
            (9, 10, "1")         # Column 9: channel 1
        ]
        
        # Initialize pygame mixer for audio playback
        pygame.mixer.init()
        
        self._create_ui()
        
    def _create_ui(self):
        """Create the main user interface layout.
        
        Layout structure:
        - Top: Menu bar (File, Edit, Help)
        - Left panel (300px): Metadata, tools, section list
        - Right panel: Timeline canvas with waveform and sequence visualization
        """
        # Top menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open MP3...", command=self._open_mp3)
        file_menu.add_command(label="Open JSON...", command=self._open_json)
        file_menu.add_separator()
        file_menu.add_command(label="Save", command=self._save_song, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As...", command=self._save_song_as)
        file_menu.add_separator()
        file_menu.add_command(label="Close Song", command=self._close_song)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Manage Sections...", command=self._manage_sections)
        edit_menu.add_command(label="Manage Phrases...", command=self._manage_phrases)
        edit_menu.add_separator()
        edit_menu.add_command(label="Delete Selected", command=self._delete_selected, accelerator="Del")
        
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Quick Start", command=self._show_quick_start)
        help_menu.add_command(label="About", command=self._show_about)
        
        # Bind keyboard shortcuts
        self.root.bind('<Control-s>', lambda e: self._save_song())
        self.root.bind('<Delete>', lambda e: self._delete_selected())
        self.root.bind('<space>', lambda e: self._toggle_playback())
        
        # Main container
        main_container = tk.Frame(self.root, bg='#2b2b2b')
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel - Metadata and controls
        left_panel = tk.Frame(main_container, bg='#3c3c3c', width=300)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left_panel.pack_propagate(False)
        
        self._create_metadata_panel(left_panel)
        self._create_tools_panel(left_panel)
        self._create_section_panel(left_panel)
        
        # Right panel - Timeline editor
        right_panel = tk.Frame(main_container, bg='#2b2b2b')
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self._create_timeline_editor(right_panel)
        
    def _create_metadata_panel(self, parent):
        """Create metadata editing panel in left sidebar.
        
        Provides text fields for song information that gets saved to JSON:
        - Title: Song name
        - Artist: Artist/composer name  
        - Description: Optional notes
        - MP3 File: Display of loaded audio file path
        
        All fields sync with self.song_data when saving.
        """
        frame = tk.LabelFrame(parent, text="Song Metadata", bg='#3c3c3c', fg='white', font=('Arial', 10, 'bold'))
        frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Title
        tk.Label(frame, text="Title:", bg='#3c3c3c', fg='white').grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.title_var = tk.StringVar()
        tk.Entry(frame, textvariable=self.title_var, bg='#2b2b2b', fg='white', insertbackground='white').grid(
            row=0, column=1, sticky='ew', padx=5, pady=2)
        
        # Artist
        tk.Label(frame, text="Artist:", bg='#3c3c3c', fg='white').grid(row=1, column=0, sticky='w', padx=5, pady=2)
        self.artist_var = tk.StringVar()
        tk.Entry(frame, textvariable=self.artist_var, bg='#2b2b2b', fg='white', insertbackground='white').grid(
            row=1, column=1, sticky='ew', padx=5, pady=2)
        
        # Description
        tk.Label(frame, text="Description:", bg='#3c3c3c', fg='white').grid(row=2, column=0, sticky='nw', padx=5, pady=2)
        self.description_text = tk.Text(frame, height=3, bg='#2b2b2b', fg='white', insertbackground='white')
        self.description_text.grid(row=2, column=1, sticky='ew', padx=5, pady=2)
        
        # MP3 file
        tk.Label(frame, text="MP3 File:", bg='#3c3c3c', fg='white').grid(row=3, column=0, sticky='w', padx=5, pady=2)
        self.mp3_label = tk.Label(frame, text="No file loaded", bg='#2b2b2b', fg='#888', anchor='w')
        self.mp3_label.grid(row=3, column=1, sticky='ew', padx=5, pady=2)
        
        frame.columnconfigure(1, weight=1)
        
    def _create_tools_panel(self, parent):
        """Create tool selection panel in left sidebar.
        
        Tool modes:
        - Select (S): Default mode, click to select and edit items
        - Hand (H): Pan/scroll mode (currently implemented via mouse drag)
        - Beat Marker (B): Add beat markers (placeholder for future feature)
        - Channel Note (N): Add notes directly (placeholder for future feature)
        
        Note: Most functionality currently works through right-click context menus
        rather than requiring tool selection.
        """
        frame = tk.LabelFrame(parent, text="Tools", bg='#3c3c3c', fg='white', font=('Arial', 10, 'bold'))
        frame.pack(fill=tk.X, padx=5, pady=5)
        
        tools = [
            ("Select (S)", "select", "Select and move items"),
            ("Hand (H)", "hand", "Pan timeline"),
            ("Beat Marker (B)", "beat_marker", "Add beat markers"),
            ("Channel Note (N)", "channel", "Add channel activation")
        ]
        
        self.tool_var = tk.StringVar(value="select")
        
        for text, value, tooltip in tools:
            rb = tk.Radiobutton(frame, text=text, variable=self.tool_var, value=value,
                               bg='#3c3c3c', fg='white', selectcolor='#2b2b2b',
                               activebackground='#3c3c3c', activeforeground='white',
                               command=self._tool_changed)
            rb.pack(anchor='w', padx=5, pady=2)
            
        # Playback controls
        controls_frame = tk.Frame(frame, bg='#3c3c3c')
        controls_frame.pack(fill=tk.X, padx=5, pady=10)
        
        self.play_button = tk.Button(controls_frame, text="▶ Play", command=self._toggle_playback,
                                     bg='#4CAF50', fg='white', font=('Arial', 12, 'bold'))
        self.play_button.pack(fill=tk.X, pady=2)
        
        tk.Button(controls_frame, text="⏮ Rewind", command=self._rewind_playback,
                 bg='#2196F3', fg='white').pack(fill=tk.X, pady=2)
        
    def _create_section_panel(self, parent):
        """Create section/segment selection panel."""
        frame = tk.LabelFrame(parent, text="Sections & Timing", bg='#3c3c3c', fg='white', font=('Arial', 10, 'bold'))
        frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Section selector
        tk.Label(frame, text="Current Section:", bg='#3c3c3c', fg='white').pack(anchor='w', padx=5, pady=(5,2))
        
        self.section_listbox = tk.Listbox(frame, bg='#2b2b2b', fg='white', selectbackground='#0078d7', height=6)
        self.section_listbox.pack(fill=tk.X, padx=5, pady=2)
        self.section_listbox.bind('<<ListboxSelect>>', self._section_selected)
        
        # Section management buttons
        btn_frame = tk.Frame(frame, bg='#3c3c3c')
        btn_frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.add_section_btn = tk.Button(btn_frame, text="Add Section", command=self._add_section, bg='#555', fg='white')
        self.add_section_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        
        self.edit_section_btn = tk.Button(btn_frame, text="Edit", command=self._edit_section, bg='#555', fg='white')
        self.edit_section_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        
        self.delete_section_btn = tk.Button(btn_frame, text="Delete", command=self._delete_section, bg='#555', fg='white')
        self.delete_section_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        
        # Timing info for current section
        self.timing_label = tk.Label(frame, text="Start: 0.0s | Tempo: 1.0s | Beats: 0",
                                     bg='#2b2b2b', fg='#aaa', anchor='w', font=('Courier', 9))
        self.timing_label.pack(fill=tk.X, padx=5, pady=5)
        
        # Zoom controls
        tk.Label(frame, text="Zoom:", bg='#3c3c3c', fg='white').pack(anchor='w', padx=5, pady=(10,2))
        zoom_frame = tk.Frame(frame, bg='#3c3c3c')
        zoom_frame.pack(fill=tk.X, padx=5, pady=2)
        
        tk.Button(zoom_frame, text="-", command=self._zoom_out, bg='#555', fg='white', width=3).pack(side=tk.LEFT)
        self.zoom_label = tk.Label(zoom_frame, text="100%", bg='#2b2b2b', fg='white', width=8)
        self.zoom_label.pack(side=tk.LEFT, padx=5)
        tk.Button(zoom_frame, text="+", command=self._zoom_in, bg='#555', fg='white', width=3).pack(side=tk.LEFT)
        
    def _create_timeline_editor(self, parent):
        """Create the main timeline editor canvas and supporting UI elements.
        
        Layout structure (top to bottom):
        1. Channel bar: Shows 10 channel indicators with grouping labels
        2. Legend bar: Color key and live status indicators (position, amplitude)
        3. Timeline canvas: Main scrollable editing area showing:
           - Left: Time labels (vertical axis)
           - Center: 10 channel columns with actions
           - Right: Waveform visualization (resizable)
        
        Mouse interactions:
        - Left-click: Select/edit actions, seek in waveform
        - Right-click: Context menu for hierarchical editing
        - Drag: Resize waveform splitter, pan timeline
        - Scroll wheel: Zoom amplitude when over waveform, otherwise scroll
        - Hover: Show tooltips for actions
        """
        # Top bar with channel indicators
        self.channel_bar = tk.Canvas(parent, height=100, bg='#1a1a1a', highlightthickness=0)
        self.channel_bar.pack(fill=tk.X)
        
        # Legend bar
        legend_frame = tk.Frame(parent, bg='#2b2b2b', height=30)
        legend_frame.pack(fill=tk.X, pady=2)
        legend_frame.pack_propagate(False)
        
        tk.Label(legend_frame, text="Legend:", bg='#2b2b2b', fg='white', font=('Arial', 9, 'bold')).pack(side=tk.LEFT, padx=5)
        
        # Color indicators
        legends = [
            ('#4CAF50', 'Note'),
            ('#9C27B0', 'Phrase'),
            ('#FF9800', 'All Ch'),
            ('#03A9F4', 'Step Up'),
            ('#00BCD4', 'Step Dn'),
            ('#FFC107', 'Flash'),
            ('#FF5722', 'Section'),
            ('#FFC107', 'Beat')
        ]
        
        for color, label in legends:
            legend_item = tk.Frame(legend_frame, bg='#2b2b2b')
            legend_item.pack(side=tk.LEFT, padx=3)
            
            color_box = tk.Label(legend_item, bg=color, width=2, height=1, relief='solid', borderwidth=1)
            color_box.pack(side=tk.LEFT, padx=2)
            
            tk.Label(legend_item, text=label, bg='#2b2b2b', fg='#ccc', font=('Arial', 8)).pack(side=tk.LEFT)
        
        # Add waveform zoom indicator on the right side
        self.waveform_zoom_label = tk.Label(legend_frame, text="Amp: 100%", 
                                            bg='#2b2b2b', fg='#888', font=('Arial', 9))
        self.waveform_zoom_label.pack(side=tk.RIGHT, padx=10)
        
        # Add playback position indicator on the right side
        self.position_label = tk.Label(legend_frame, text="Position: 0:00.0", 
                                       bg='#2b2b2b', fg='#00FF00', font=('Arial', 9, 'bold'))
        self.position_label.pack(side=tk.RIGHT, padx=5)
        
        # Main scrollable timeline canvas
        canvas_frame = tk.Frame(parent)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbars
        v_scrollbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        h_scrollbar = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Timeline canvas
        self.timeline_canvas = tk.Canvas(canvas_frame, bg='#1e1e1e', 
                                        yscrollcommand=v_scrollbar.set,
                                        xscrollcommand=h_scrollbar.set,
                                        highlightthickness=0)
        self.timeline_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        v_scrollbar.config(command=self.timeline_canvas.yview)
        h_scrollbar.config(command=self.timeline_canvas.xview)
        
        # Bind mouse events
        self.timeline_canvas.bind('<Button-1>', self._canvas_click)
        self.timeline_canvas.bind('<B1-Motion>', self._canvas_drag)
        self.timeline_canvas.bind('<ButtonRelease-1>', self._canvas_release)
        self.timeline_canvas.bind('<Button-3>', self._canvas_right_click)  # Right-click context menu
        self.timeline_canvas.bind('<MouseWheel>', self._canvas_scroll)
        # Linux scroll wheel support
        self.timeline_canvas.bind('<Button-4>', self._canvas_scroll_linux)
        self.timeline_canvas.bind('<Button-5>', self._canvas_scroll_linux)
        self.timeline_canvas.bind('<Motion>', self._canvas_motion)
        
        # Bind window resize to redraw
        self.root.bind('<Configure>', self._on_window_resize)
        
        # Drawing state
        self.drag_start = None
        self.drag_item = None
        
        # Force initial layout update before drawing
        self.root.update_idletasks()
        
        self._update_ui_state()
        self._draw_channel_bar()
        self._draw_timeline()
        
        # Bind resize event to redraw channel bar
        self.channel_bar.bind('<Configure>', lambda e: self._on_channel_bar_resize())
    
    def _update_ui_state(self):
        """Update UI elements based on whether MP3 is loaded."""
        has_mp3 = bool(self.mp3_path)
        
        # Enable/disable section buttons
        state = tk.NORMAL if has_mp3 else tk.DISABLED
        self.add_section_btn.config(state=state)
        self.edit_section_btn.config(state=state)
        self.delete_section_btn.config(state=state)
        
        # Update button colors to show disabled state
        if has_mp3:
            self.add_section_btn.config(bg='#555')
            self.edit_section_btn.config(bg='#555')
            self.delete_section_btn.config(bg='#555')
        else:
            self.add_section_btn.config(bg='#333')
            self.edit_section_btn.config(bg='#333')
            self.delete_section_btn.config(bg='#333')
        
    def _on_channel_bar_resize(self):
        """Handle channel bar resize event."""
        # Redraw channel bar when window is resized
        self.root.after(10, self._draw_channel_bar)
        
    def _draw_channel_bar(self):
        """Draw the channel indicator bar at the top."""
        self.channel_bar.delete('all')
        
        canvas_width = self.channel_bar.winfo_width()
        if canvas_width <= 1:
            canvas_width = 1200
        left_margin = 60
        timeline_width = canvas_width - left_margin - self.waveform_width - 20
        channel_width = timeline_width / 10
        
        y_pos = 50
        
        # Draw bulbs and labels
        for i, channel_num in enumerate(self.channel_order):
            x = left_margin + i * channel_width + channel_width / 2
            
            # Bulb
            self.channel_bar.create_oval(x - 15, y_pos - 15, x + 15, y_pos + 15,
                                        fill='#333', outline='#666', width=2, tags=f'bulb_{channel_num}')
            
            # Channel number
            self.channel_bar.create_text(x, y_pos, text=str(channel_num), fill='#aaa', font=('Arial', 10, 'bold'))
            
            # Label below
            self.channel_bar.create_text(x, y_pos + 30, text=f"Ch {channel_num}", fill='#666', font=('Arial', 8))
        
        # Draw group indicators
        for start_idx, end_idx, label in self.channel_groups:
            x1 = left_margin + start_idx * channel_width
            x2 = left_margin + end_idx * channel_width
            y = 15
            
            # Group bracket
            self.channel_bar.create_line(x1, y, x1, y + 10, fill='#888', width=2)
            self.channel_bar.create_line(x1, y, x2, y, fill='#888', width=2)
            self.channel_bar.create_line(x2, y, x2, y + 10, fill='#888', width=2)
            
            # Group label
            self.channel_bar.create_text((x1 + x2) / 2, y - 5, text=label, fill='#888', font=('Arial', 9))
        
        # Time label area
        self.channel_bar.create_text(30, y_pos, text="Time", fill='#aaa', font=('Arial', 10, 'bold'))
    
    def _update_channel_bar_lights(self):
        """Update the channel bar bulbs to reflect current channel states.
        
        This method is called during playback to make the channel header bulbs
        light up in sync with the actual lightshow, matching the simulator behavior.
        """
        for i, channel_num in enumerate(self.channel_order):
            # channel_order uses 1-indexed numbers (1-10)
            # channel_states uses 0-indexed (0-9)
            channel_idx = channel_num - 1
            
            if channel_idx < len(self.channel_states):
                is_active = self.channel_states[channel_idx]
                tag = f'bulb_{channel_num}'
                
                if is_active:
                    # Channel is on - bright yellow/white with glow
                    self.channel_bar.itemconfig(tag, fill='#ffff00', outline='#ffcc00')
                else:
                    # Channel is off - dark gray
                    self.channel_bar.itemconfig(tag, fill='#333', outline='#666')
    
    def _draw_timeline(self):
        """Draw the complete timeline visualization with all elements.
        
        This is the main rendering function that creates the visual representation
        of the entire song choreography.
        
        Rendering order (z-order from bottom to top):
        1. Waveform background and amplitude bars (right column)
        2. Channel column separators (10 vertical lines)
        3. Time grid lines (horizontal, spacing based on zoom)
        4. Section boundaries (red lines) and beat markers (yellow dashed)
        5. Action rectangles (notes, phrases, steps, etc.)
        6. Playback position indicator (green line, separate update)
        
        Layout calculations:
        - left_margin = 60px for time labels
        - timeline_width = canvas_width - left_margin - waveform_width - 20
        - channel_width = timeline_width / 10 (equal columns)
        - timeline_height = audio_duration × zoom_level × 100 pixels
        
        Performance: Full redraw on zoom/edit/resize. Playback line updates
        separately at 60fps for smooth animation without full redraws.
        """
        self.timeline_canvas.delete('all')
        
        canvas_width = self.timeline_canvas.winfo_width()
        canvas_height = self.timeline_canvas.winfo_height()
        
        # Handle case where widget isn't fully rendered yet
        if canvas_width <= 1:
            canvas_width = 1200
        if canvas_height <= 1:
            canvas_height = 600
        
        if not self.audio_data:
            # Show instructions
            self.timeline_canvas.create_text(canvas_width / 2, canvas_height / 2,
                                            text="Open an MP3 file to begin editing\n(File → Open MP3...)",
                                            fill='#666', font=('Arial', 16), justify=tk.CENTER)
            return
        
        left_margin = 60
        timeline_width = canvas_width - left_margin - self.waveform_width - 20  # 20 for gap and padding
        
        # Calculate timeline height based on duration and zoom
        timeline_height = int(self.audio_duration * self.zoom_level * 100)  # pixels per second * 100
        
        self.timeline_canvas.configure(scrollregion=(0, 0, canvas_width, max(timeline_height, 600)))
        
        # Draw waveform background
        self._draw_waveform(left_margin, timeline_width, timeline_height)
        
        # Draw channel columns
        self._draw_channel_columns(left_margin, timeline_width, timeline_height)
        
        # Draw grid lines (time markers)
        self._draw_time_grid(left_margin, timeline_width, timeline_height)
        
        # Draw sections and beats
        self._draw_sections(left_margin, timeline_width)
        
        # Draw sequences/actions
        self._draw_sequences(left_margin, timeline_width)
        
        # Draw playback position (always show it, even when paused)
        self._draw_playback_position(left_margin, timeline_width)
    
    def _draw_waveform(self, left_margin, width, height):
        """Draw audio waveform visualization."""
        if self.waveform_data is None:
            return
        
        # Simple amplitude visualization
        channel_width = width / 10
        waveform_width = self.waveform_width
        
        x_offset = left_margin + width + 10
        
        # Draw background rectangle for waveform area (makes entire area clickable)
        self.timeline_canvas.create_rectangle(x_offset, 0, x_offset + waveform_width, height,
                                             fill='#1a1a1a', outline='#444', tags='waveform')
        
        # Draw draggable splitter on the left edge
        splitter_x = x_offset
        self.timeline_canvas.create_rectangle(splitter_x - 3, 0, splitter_x + 3, height,
                                             fill='#555', outline='#777', tags='waveform_splitter')
        
        # Draw waveform in a column to the right
        samples_per_pixel = len(self.waveform_data) / height
        
        for y in range(0, height, 2):
            sample_idx = int(y * samples_per_pixel)
            if sample_idx < len(self.waveform_data):
                amplitude = abs(self.waveform_data[sample_idx])
                bar_width = amplitude * waveform_width * self.waveform_zoom
                
                self.timeline_canvas.create_line(x_offset, y, x_offset + bar_width, y,
                                                fill='#2196F3', width=2, tags='waveform')
    
    def _draw_channel_columns(self, left_margin, width, height):
        """Draw vertical lines for each channel column."""
        channel_width = width / 10
        
        for i in range(11):
            x = left_margin + i * channel_width
            self.timeline_canvas.create_line(x, 0, x, height, fill='#333', width=1)
        
        # Highlight group boundaries
        for start_idx, end_idx, label in self.channel_groups:
            if start_idx > 0:
                x = left_margin + start_idx * channel_width
                self.timeline_canvas.create_line(x, 0, x, height, fill='#555', width=2)
    
    def _draw_time_grid(self, left_margin, width, height):
        """Draw horizontal grid lines for time markers."""
        seconds_per_line = 1.0 if self.zoom_level < 50 else 0.5 if self.zoom_level < 100 else 0.25
        
        for t in np.arange(0, self.audio_duration, seconds_per_line):
            y = int(t * self.zoom_level * 100)
            
            # Draw grid line
            self.timeline_canvas.create_line(0, y, left_margin + width, y, fill='#2a2a2a', width=1)
            
            # Draw time label
            self.timeline_canvas.create_text(30, y, text=f"{t:.2f}s", fill='#666', font=('Courier', 8))
    
    def _draw_sections(self, left_margin, width):
        """Draw section boundaries and beat marker lines.
        
        Visualizes the timing structure:
        - Red horizontal lines mark section start positions
        - Yellow dashed lines mark each beat within sections
        - Section names displayed on the left
        - Beat numbers labeled on the left
        
        Handles both simple sections and segmented sections (which have
        multiple tempo changes within one section).
        """
        if not self.song_data.get('sections'):
            return
        
        for section in self.song_data['sections']:
            # Handle sections with segments
            if 'segments' in section:
                for segment in section['segments']:
                    self._draw_section_beats(segment, left_margin, width, section.get('name', ''))
            else:
                self._draw_section_beats(section, left_margin, width, section.get('name', ''))
    
    def _draw_section_beats(self, timing_info, left_margin, width, section_name):
        """Draw beat markers for a section or segment."""
        start_time = timing_info.get('start_time', 0)
        tempo = timing_info.get('tempo', 1.0)
        total_beats = timing_info.get('total_beats', 0)
        
        # Draw section start line
        y_start = int(start_time * self.zoom_level * 100)
        self.timeline_canvas.create_line(0, y_start, left_margin + width, y_start,
                                        fill='#FF5722', width=3, tags='section_start')
        self.timeline_canvas.create_text(left_margin - 5, y_start, text=f"▶ {section_name}",
                                        fill='#FF5722', anchor='e', font=('Arial', 10, 'bold'))
        
        # Draw beat markers
        for beat in range(1, total_beats + 1):
            beat_time = start_time + (beat * tempo)
            y = int(beat_time * self.zoom_level * 100)
            
            # Beat line
            self.timeline_canvas.create_line(left_margin, y, left_margin + width, y,
                                            fill='#FFC107', width=1, dash=(4, 4), tags='beat_marker')
            
            # Beat number
            self.timeline_canvas.create_text(left_margin - 5, y, text=str(beat),
                                            fill='#FFC107', anchor='e', font=('Courier', 8))
    
    def _draw_sequences(self, left_margin, width):
        """Draw all action rectangles for sequences across all sections.
        
        Iterates through the song structure and renders each action:
        
        Song Structure Navigation:
          sections[] → segments[] (optional) → sequences[] → actions[]
        
        For each action, calls _draw_action() with:
        - Action data (type, channel, timing, parameters)
        - Position on timeline (calculated from beat number and timing)
        - Location tracking (section_idx, seg_idx, seq_idx, action_idx)
          Used for click handling and context menu operations
        
        Beat Number Conversion:
        - JSON uses 1-indexed beats (beat 1 = first beat)
        - _get_beat_numbers() converts to 0-indexed for calculations
        - beat_time = start_time + (beat_number × tempo)
        """
        if not self.song_data.get('sections'):
            return
        
        channel_width = width / 10
        
        for section_idx, section in enumerate(self.song_data['sections']):
            timing_list = []
            
            # Get timing info
            if 'segments' in section:
                for seg_idx, seg in enumerate(section['segments']):
                    timing_list.append((seg_idx, seg))
            else:
                timing_list.append((None, section))
            
            for seg_idx, timing_info in timing_list:
                start_time = timing_info.get('start_time', 0)
                tempo = timing_info.get('tempo', 1.0)
                
                for seq_idx, sequence in enumerate(timing_info.get('sequences', [])):
                    beat_nums = self._get_beat_numbers(sequence, timing_info.get('total_beats', 0))
                    
                    for beat_num in beat_nums:
                        beat_time = start_time + (beat_num * tempo)
                        y = int(beat_time * self.zoom_level * 100)
                        
                        # Draw actions with sequence location info
                        for action_idx, action in enumerate(sequence.get('actions', [])):
                            self._draw_action(action, y, left_margin, channel_width, tempo,
                                            section_idx, seg_idx, seq_idx, action_idx,
                                            beat_time, timing_info)
    
    def _get_beat_numbers(self, sequence, total_beats):
        """Extract beat numbers from a sequence and convert to 0-indexed for timing.
        
        JSON uses 1-indexed beats (beat 1 = first beat), but timing calculations
        use 0-indexed (beat 0 = start). This function handles the conversion.
        
        Args:
            sequence: Sequence dict with beat specification
            total_beats: Total beats in the timing section
            
        Returns:
            List of 0-indexed beat numbers when this sequence should execute
        """
        if sequence.get('all_beats'):
            return list(range(0, total_beats))
        elif 'beat' in sequence:
            # Single beat: convert 1-indexed to 0-indexed
            return [sequence['beat'] - 1]
        elif 'beats' in sequence:
            # Multiple beats: convert each from 1-indexed to 0-indexed
            return [b - 1 for b in sequence['beats']]
        return []
    
    def _draw_action(self, action, y_pos, left_margin, channel_width, tempo, section_idx, seg_idx, seq_idx, action_idx, beat_time=None, timing_info=None):
        """Draw a single action rectangle on the timeline with detailed visualization.
        
        Creates clickable visual representations of actions with proper positioning,
        coloring, and internal detail (e.g., phrase notes, step patterns).
        
        Args:
            action: Action dict with type and parameters
            y_pos: Vertical position in pixels (beat time on timeline)
            left_margin: Left edge of timeline area
            channel_width: Width of each channel column in pixels
            tempo: Current tempo for duration calculations
            section_idx: Section index for click tracking
            seg_idx: Segment index (None if not in segment)
            seq_idx: Sequence index within timing section
            action_idx: Action index within sequence
            beat_time: Actual time in seconds when this action occurs (for lookahead)
            timing_info: Full segment/section dict (for lookahead)
        """
        action_type = action.get('type')
        
        # Create unique tag for click handling: seq_<section>_<segment>_<sequence>_<action>
        if seg_idx is not None:
            seq_tag = f'seq_{section_idx}_{seg_idx}_{seq_idx}_{action_idx}'
        else:
            seq_tag = f'seq_{section_idx}_none_{seq_idx}_{action_idx}'
        
        if action_type == 'note':
            channel = action.get('channel', 0)
            
            # Calculate timing - support both absolute and multiplier
            if 'delay_multiplier' in action:
                delay = action.get('delay_multiplier', 0) * tempo
            else:
                delay = action.get('delay', 0)
                
            if 'duration_multiplier' in action:
                duration = action.get('duration_multiplier', 0.5) * tempo
            else:
                duration = action.get('duration', 0.1)
            
            y1 = y_pos + int(delay * self.zoom_level * 100)
            y2 = y1 + int(duration * self.zoom_level * 100)
            
            # Map channel to column
            col_idx = self.channel_order.index(channel + 1) if (channel + 1) in self.channel_order else 0
            x1 = left_margin + col_idx * channel_width + 2
            x2 = x1 + channel_width - 4
            
            # Draw rectangle with gradient effect
            rect = self.timeline_canvas.create_rectangle(x1, y1, x2, y2,
                                                         fill='#4CAF50', outline='#2E7D32', width=2,
                                                         tags=('action', 'note', f'ch{channel}', seq_tag))
            
            # Add channel number label if rectangle is tall enough
            if (y2 - y1) > 15:
                self.timeline_canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2,
                                                text=f"Ch{channel + 1}", fill='white',
                                                font=('Arial', 8, 'bold'), tags='action_label')
            
        elif action_type == 'phrase':
            # Draw phrase indicator: reusable pattern of notes across channels
            # Phrase notes are positioned at y_pos (beat time) + delay, allowing
            # them to align with the timeline exactly when they should play
            phrase_id = str(action.get('id', 0))
            desc = action.get('description', '')
            
            # Get phrase definition and calculate total vertical extent
            phrase_data = self.song_data.get('phrases', {}).get(phrase_id)
            phrase_duration = 0
            if phrase_data and 'notes' in phrase_data:
                # Find the end time of the longest note (delay + duration)
                for note in phrase_data['notes']:
                    delay = note.get('delay_multiplier', 0) * tempo
                    duration = note.get('duration_multiplier', 0.5) * tempo
                    note_end = delay + duration
                    phrase_duration = max(phrase_duration, note_end)
            else:
                # If phrase not found, use tempo as fallback height
                phrase_duration = tempo
            
            # Draw semi-transparent background spanning all channels
            # y_pos - 15: Space above for label
            # y_pos + phrase_duration + 5: Extend past last note for visual clarity
            x1 = left_margin + 2
            x2 = left_margin + channel_width * 10 - 2
            y1 = y_pos - 15  # Reserve space for phrase label
            y2 = y_pos + int(phrase_duration * self.zoom_level * 100) + 5
            
            # Dark purple background with stipple pattern (50% transparency simulation)
            # tkinter doesn't support true alpha transparency, so we use stipple='gray50'
            # which creates a checkerboard pattern allowing overlapping phrases to be visible
            self.timeline_canvas.create_rectangle(x1, y1, x2, y2,
                                                 fill='#7B1FA2', outline='#7B1FA2', width=2,
                                                 stipple='gray50',  # Checkerboard pattern for pseudo-transparency
                                                 tags=('action', 'phrase', f'phrase{phrase_id}', seq_tag))
            
            # Draw phrase label centered horizontally, positioned above y_pos
            label = f"Phrase {phrase_id}"
            if desc:
                label += f": {desc[:30]}"  # Truncate long descriptions
            self.timeline_canvas.create_text(left_margin + channel_width * 5, y_pos - 7,
                                            text=label, fill='white',
                                            font=('Arial', 9, 'bold'), tags='phrase_label')
            
            # Draw individual notes as separate rectangles in their respective channels
            # CRITICAL: Notes use y_pos + delay for positioning (aligned with beat time)
            # This differs from the label (y_pos - 7) which floats above the beat line
            if phrase_data and 'notes' in phrase_data:
                for note_idx, note in enumerate(phrase_data['notes']):
                    ch = note.get('channel', 0)
                    delay = note.get('delay_multiplier', 0) * tempo
                    duration = note.get('duration_multiplier', 0.5) * tempo
                    
                    # Position note exactly when it should play (y_pos = beat time)
                    note_y1 = y_pos + int(delay * self.zoom_level * 100)
                    note_y2 = note_y1 + int(duration * self.zoom_level * 100)
                    
                    # Map channel (0-indexed) to visual column using channel_order
                    # channel_order = [10, 9, 2, 7, 6, 4, 3, 5, 8, 1] (physical left-to-right layout)
                    col_idx = self.channel_order.index(ch + 1) if (ch + 1) in self.channel_order else 0
                    note_x1 = left_margin + col_idx * channel_width + 4  # 4px inset
                    note_x2 = note_x1 + channel_width - 8  # 8px total padding
                    
                    # Create unique tag for click handling (enables direct note editing)
                    note_tag = f'phrase_note_{phrase_id}_{note_idx}'
                    
                    # Draw note in light purple to contrast with dark purple background
                    self.timeline_canvas.create_rectangle(note_x1, note_y1, note_x2, note_y2,
                                                         fill='#CE93D8', outline='#BA68C8', width=1,
                                                         tags=('phrase_note', note_tag))
                    
                    # Show channel number inside note if tall enough (> 12px height)
                    if (note_y2 - note_y1) > 12:
                        self.timeline_canvas.create_text((note_x1 + note_x2) / 2, (note_y1 + note_y2) / 2,
                                                        text=f"{ch + 1}", fill='#4A148C',
                                                        font=('Arial', 7, 'bold'), tags='phrase_note_label')
        
        elif action_type == 'all_channels':
            # Calculate duration
            if 'duration_multiplier' in action:
                duration = action.get('duration_multiplier', 0.33) * tempo
            else:
                duration = action.get('duration', 0.25)
                
            y1 = y_pos
            y2 = y1 + int(duration * self.zoom_level * 100)
            
            # Draw across all channels
            x1 = left_margin + 2
            x2 = left_margin + channel_width * 10 - 2
            
            self.timeline_canvas.create_rectangle(x1, y1, x2, y2,
                                                 fill='#FF9800', outline='#E65100', width=2,
                                                 tags=('action', 'all_channels', seq_tag))
            
            # Add label if tall enough
            if (y2 - y1) > 15:
                self.timeline_canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2,
                                                text="ALL CHANNELS", fill='white',
                                                font=('Arial', 9, 'bold'), tags='action_label')
        
        elif action_type == 'step_up':
            # Draw step_up: sequential channel activation with staggered delays
            # First channel blinks (on then off), others turn on and stay on
            # Visual: shows "wave" of activation moving across channels
            # Order: [10, 9, 2, 7, 6, 4, 3, 5, 8, 1] (physical channel numbers)
            order = [9, 8, 1, 6, 5, 3, 2, 4, 7, 0]  # 0-indexed for code
            
            # Find when these channels get overridden (if timing_info available)
            if beat_time is not None and timing_info is not None:
                override_time = self._find_next_override_time(beat_time, timing_info, list(range(10)))
                total_duration = override_time - beat_time
            else:
                # Fallback if context not available
                total_duration = tempo * 2
            
            # Draw dark blue background spanning all channels
            x1 = left_margin + 2
            x2 = left_margin + channel_width * 10 - 2
            y1 = y_pos - 5  # Small space above
            y2 = y_pos + int(total_duration * self.zoom_level * 100) + 5
            
            self.timeline_canvas.create_rectangle(x1, y1, x2, y2,
                                                 fill='#01579B', outline='#0277BD', width=2,
                                                 tags=('action', 'step_up', seq_tag))
            
            # Add descriptive label at top of background
            self.timeline_canvas.create_text((x1 + x2) / 2, y_pos,
                                            text="STEP UP ▲", fill='white',
                                            font=('Arial', 8, 'bold'), tags='action_label')
            
            # Draw each channel activation as a light blue rectangle
            # First channel: activates then deactivates after tempo
            # Other channels: activate at staggered times and stay on until overridden
            for idx, ch in enumerate(order):
                delay = tempo * 0.1 * idx  # Staggered start time
                
                if idx == 0:
                    # First channel turns on then off
                    duration = tempo
                else:
                    # Other channels stay on until overridden
                    # Calculate duration from when this channel turns on to override time
                    channel_start = beat_time + delay if beat_time is not None else delay
                    if beat_time is not None and timing_info is not None:
                        override_time = self._find_next_override_time(beat_time, timing_info, [ch])
                        duration = override_time - channel_start
                    else:
                        duration = tempo * 2  # Fallback
                
                note_y1 = y_pos + int(delay * self.zoom_level * 100)
                note_y2 = note_y1 + int(duration * self.zoom_level * 100)
                
                # Map channel to column
                col_idx = self.channel_order.index(ch + 1) if (ch + 1) in self.channel_order else 0
                note_x1 = left_margin + col_idx * channel_width + 4
                note_x2 = note_x1 + channel_width - 8
                
                # Draw activation rectangle
                self.timeline_canvas.create_rectangle(note_x1, note_y1, note_x2, note_y2,
                                                     fill='#4FC3F7', outline='#29B6F6', width=1,
                                                     tags='step_note')
                
                # Add channel label if tall enough
                if (note_y2 - note_y1) > 12:
                    self.timeline_canvas.create_text((note_x1 + note_x2) / 2, (note_y1 + note_y2) / 2,
                                                    text=f"{ch + 1}", fill='#01579B',
                                                    font=('Arial', 7, 'bold'), tags='step_note_label')
        
        elif action_type == 'step_down':
            # Draw step_down: reverse sequential activation with increasing durations
            # Unlike step_up (staggered starts), all channels start simultaneously at y_pos
            # but have increasing durations creating a "staircase" visual effect
            # Order: [1, 8, 5, 3, 4, 6, 7, 2, 9, 10] (physical channel numbers)
            order = [0, 7, 4, 2, 3, 5, 6, 1, 8, 9]  # 0-indexed for code
            
            # Find when the last channel gets overridden (if timing_info available)
            last_channel = order[9]
            if beat_time is not None and timing_info is not None:
                override_time = self._find_next_override_time(beat_time, timing_info, [last_channel])
                max_duration = override_time - beat_time
            else:
                # Fallback if context not available
                max_duration = tempo * 2
            
            # Draw dark cyan background spanning all channels
            x1 = left_margin + 2
            x2 = left_margin + channel_width * 10 - 2
            y1 = y_pos - 5
            y2 = y_pos + int(max_duration * self.zoom_level * 100) + 5
            
            self.timeline_canvas.create_rectangle(x1, y1, x2, y2,
                                                 fill='#006064', outline='#0097A7', width=2,
                                                 tags=('action', 'step_down', seq_tag))
            
            # Add descriptive label at top of background
            self.timeline_canvas.create_text((x1 + x2) / 2, y_pos,
                                            text="STEP DOWN ▼", fill='white',
                                            font=('Arial', 8, 'bold'), tags='action_label')
            
            # Draw each channel with progressively longer duration
            # Channel 1-9: turn off at staggered times, Channel 10: stays on until overridden
            for idx, ch in enumerate(order):
                if idx == 9:
                    # Last channel stays on until overridden
                    duration = max_duration
                else:
                    # Each channel duration increases by 0.1*tempo
                    duration = tempo * 0.1 * (idx + 1)
                
                note_y1 = y_pos  # All start at same time (beat position)
                note_y2 = note_y1 + int(duration * self.zoom_level * 100)
                
                # Map 0-indexed channel to visual column position
                col_idx = self.channel_order.index(ch + 1) if (ch + 1) in self.channel_order else 0
                note_x1 = left_margin + col_idx * channel_width + 4
                note_x2 = note_x1 + channel_width - 8
                
                # Draw light cyan rectangle showing activation duration
                self.timeline_canvas.create_rectangle(note_x1, note_y1, note_x2, note_y2,
                                                     fill='#4DD0E1', outline='#26C6DA', width=1,
                                                     tags='step_note')
                
                # Show channel number if rectangle is tall enough
                if (note_y2 - note_y1) > 12:
                    self.timeline_canvas.create_text((note_x1 + note_x2) / 2, (note_y1 + note_y2) / 2,
                                                    text=f"{ch + 1}", fill='#006064',
                                                    font=('Arial', 7, 'bold'), tags='step_note_label')
        
        elif action_type == 'flash_mode':
            # Draw flash_mode indicator
            mode = action.get('mode', 0)
            x1 = left_margin + 2
            x2 = left_margin + channel_width * 10 - 2
            y1 = y_pos - 6
            y2 = y_pos + 6
            
            color = '#F44336' if mode == -1 else '#FFC107'
            self.timeline_canvas.create_rectangle(x1, y1, x2, y2,
                                                 fill=color, outline='#D32F2F' if mode == -1 else '#FFA000', width=2,
                                                 tags=('action', 'flash_mode', seq_tag))
            text = f"FLASH MODE: {'OFF' if mode == -1 else mode}"
            self.timeline_canvas.create_text((x1 + x2) / 2, y_pos,
                                            text=text, fill='white',
                                            font=('Arial', 8, 'bold'), tags='action_label')
    
    def _draw_playback_position(self, left_margin, width):
        """Draw the current playback position line."""
        y = int(self.playback_position * self.zoom_level * 100)
        self.timeline_canvas.create_line(0, y, left_margin + width, y,
                                        fill='#00FF00', width=3, tags='playback_pos')
    
    def _seek_to_position(self, y_pos):
        """Seek to a specific position on the timeline.
        
        Converts vertical canvas position to audio time and updates playback position.
        Preserves playback state (continues playing if already playing).
        
        Args:
            y_pos: Vertical pixel position on canvas (converted to seconds)
        """
        # Convert canvas pixels to time: y / (zoom_level * 100 pixels/second)
        new_position = y_pos / (self.zoom_level * 100)
        new_position = max(0, min(new_position, self.audio_duration))
        
        # Preserve playback state for seamless seeking during playback
        was_playing = self.is_playing
        
        # Stop current audio playback
        if self.is_playing:
            self.is_playing = False
            pygame.mixer.music.stop()
        
        # Update both current and start positions for sync
        self.playback_position = new_position
        self.playback_start_position = new_position
        
        # Update channel states for new position
        self._update_channel_states()
        self._update_channel_bar_lights()
        
        # Redraw timeline to show new position marker
        self._draw_timeline()
        
        # Resume playback if we were playing before seek
        if was_playing:
            self._start_playback()
    
    # ========== Event Handlers ==========
    
    def _canvas_click(self, event):
        """Handle mouse click on timeline canvas.
        
        Priority order for click handling:
        1. Waveform splitter (for resizing)
        2. Waveform area (for seeking)
        3. Phrase notes (for direct note editing)
        4. Actions (for sequence/action editing)
        5. Tool-specific actions (beat marker, channel note, etc.)
        
        Also dismisses any open context menu on click.
        """
        # Always dismiss context menu on any canvas click
        if self.active_context_menu:
            try:
                self.active_context_menu.unpost()
            except:
                pass
            self.active_context_menu = None
        
        # Convert event coordinates to canvas coordinates (accounting for scroll)
        x = self.timeline_canvas.canvasx(event.x)
        y = self.timeline_canvas.canvasy(event.y)
        
        # Find items under cursor (2px tolerance for easier clicking)
        items = self.timeline_canvas.find_overlapping(x-2, y-2, x+2, y+2)
        
        # Priority 1: Check for waveform splitter drag
        for item in items:
            if 'waveform_splitter' in self.timeline_canvas.gettags(item):
                self.dragging_splitter = True
                self.drag_start = (x, y)
                return
        
        # Priority 2: Check for waveform click (seek to position)
        for item in items:
            if 'waveform' in self.timeline_canvas.gettags(item):
                self._seek_to_position(y)
                # Restore preview by triggering motion event at current position
                self._canvas_motion(event)
                return
        
        # Priority 3: Check for phrase note click (direct note editing)
        for item in items:
            tags = self.timeline_canvas.gettags(item)
            if 'phrase_note' in tags:
                # Extract phrase_note_<phrase_id>_<note_idx> tag
                phrase_note_tag = None
                for tag in tags:
                    if tag.startswith('phrase_note_'):
                        phrase_note_tag = tag
                        break
                if phrase_note_tag:
                    self._edit_phrase_note_from_click(phrase_note_tag)
                    return
        
        # Priority 4: Check for action click (sequence/action editing)
        for item in items:
            tags = self.timeline_canvas.gettags(item)
            if 'action' in tags:
                # Extract seq_<section>_<segment>_<sequence>_<action> tag
                seq_info = None
                for tag in tags:
                    if tag.startswith('seq_'):
                        seq_info = tag
                        break
                if seq_info:
                    self._edit_action_from_click(seq_info)
                    return
        
        # Priority 5: Tool-specific click handling
        if self.current_tool == "select":
            # Check if clicking on an existing item for selection
            if items:
                self.drag_start = (x, y)
                self.drag_item = items[0]
            else:
                # Click on empty space: deselect all
                self.selected_items = []
                
        elif self.current_tool == "hand":
            self.drag_start = (x, y)
            
        elif self.current_tool == "beat_marker":
            # Add a beat marker at this position
            self._add_beat_at_position(y)
            
        elif self.current_tool == "channel":
            # Add a channel note
            self._add_channel_note_at_position(x, y)
    
    def _canvas_drag(self, event):
        """Handle mouse drag on timeline."""
        # Handle splitter dragging
        if self.dragging_splitter:
            canvas_width = self.timeline_canvas.winfo_width()
            x = self.timeline_canvas.canvasx(event.x)
            left_margin = 60
            
            # The splitter is at: left_margin + timeline_width + 10
            # timeline_width = canvas_width - left_margin - waveform_width - 10 - some padding
            # So: x = left_margin + (canvas_width - left_margin - waveform_width - 10)
            # Therefore: waveform_width = canvas_width - x + left_margin - 10
            # Simplified: waveform_width = canvas_width - x
            
            # But we want to grow left when dragging left, so:
            # new_width = canvas_width - x (distance from splitter to right edge)
            new_width = canvas_width - x
            new_width = max(50, min(new_width, canvas_width - left_margin - 100))  # Leave room for channels
            
            if new_width != self.waveform_width:
                self.waveform_width = new_width
                self._draw_channel_bar()
                self._draw_timeline()
            return
        
        if self.drag_start is None:
            return
        
        x = self.timeline_canvas.canvasx(event.x)
        y = self.timeline_canvas.canvasy(event.y)
        
        if self.current_tool == "hand":
            # Pan the view
            dx = x - self.drag_start[0]
            dy = y - self.drag_start[1]
            self.timeline_canvas.yview_scroll(int(-dy / 10), 'units')
            self.drag_start = (x, y)
    
    def _canvas_release(self, event):
        """Handle mouse release on timeline."""
        self.drag_start = None
        self.drag_item = None
        self.dragging_splitter = False
    
    def _edit_phrase_note_from_click(self, phrase_note_tag):
        """Edit a phrase note directly when clicked.
        
        Opens the PhraseNoteDialog for editing the clicked note within a phrase.
        Updates the phrase definition in song_data if changes are made.
        
        Args:
            phrase_note_tag: Tag string in format 'phrase_note_<phrase_id>_<note_idx>'
        """
        # Parse tag to extract phrase and note identifiers
        parts = phrase_note_tag.split('_')
        if len(parts) != 4:
            return
        
        phrase_id = parts[2]
        note_idx = int(parts[3])
        
        # Validate phrase exists in song data
        if phrase_id not in self.song_data.get('phrases', {}):
            return
        
        phrase = self.song_data['phrases'][phrase_id]
        if 'notes' not in phrase or note_idx >= len(phrase['notes']):
            return
        
        note = phrase['notes'][note_idx]
        
        # Open modal dialog for note editing
        dialog = PhraseNoteDialog(self.root, note)
        if dialog.result:
            # Update phrase definition with edited note
            phrase['notes'][note_idx] = dialog.result
            self._draw_timeline()  # Refresh visualization
    
    def _canvas_right_click(self, event):
        """Handle right-click for hierarchical context menu.
        
        Detects clicked action and displays menu with options to edit at different levels:
        - Action: Single action within sequence
        - Sequence: All actions in sequence
        - Segment: All sequences in segment (if applicable)
        - Section: Entire timing section
        """
        # Convert to canvas coordinates
        x = self.timeline_canvas.canvasx(event.x)
        y = self.timeline_canvas.canvasy(event.y)
        
        # Find items under cursor
        items = self.timeline_canvas.find_overlapping(x-2, y-2, x+2, y+2)
        
        # Look for action tags to determine context
        for item in items:
            tags = self.timeline_canvas.gettags(item)
            if 'action' in tags:
                # Extract seq_<section>_<segment>_<sequence>_<action> tag
                seq_info = None
                for tag in tags:
                    if tag.startswith('seq_'):
                        seq_info = tag
                        break
                if seq_info:
                    self._show_action_context_menu(event, seq_info)
                    return
    
    def _show_action_context_menu(self, event, seq_tag):
        """Display context menu with hierarchical editing options.
        
        Args:
            event: Mouse event for positioning menu
            seq_tag: Sequence tag string 'seq_<section>_<segment>_<sequence>_<action>'
        """
        # Parse sequence tag to extract indices
        parts = seq_tag.split('_')
        if len(parts) != 5:
            return
        
        section_idx = int(parts[1])
        seg_idx = None if parts[2] == 'none' else int(parts[2])
        seq_idx = int(parts[3])
        action_idx = int(parts[4])
        
        # Create dark-themed context menu
        context_menu = tk.Menu(self.root, tearoff=0, bg='#2b2b2b', fg='white',
                              activebackground='#0078d7', activeforeground='white')
        
        # Store reference for dismissal on next click
        self.active_context_menu = context_menu
        
        # Add menu items (unpost before handler to close menu)
        context_menu.add_command(label="Edit Action",
                                command=lambda: [context_menu.unpost(), self._edit_action_from_context(section_idx, seg_idx, seq_idx, action_idx)])
        context_menu.add_command(label="Edit Sequence",
                                command=lambda: [context_menu.unpost(), self._edit_sequence_from_context(section_idx, seg_idx, seq_idx, action_idx)])
        
        # Only show Edit Segment option if action is in a segment
        if seg_idx is not None:
            context_menu.add_command(label="Edit Segment",
                                    command=lambda: [context_menu.unpost(), self._edit_segment_from_context(section_idx, seg_idx)])
        
        context_menu.add_command(label="Edit Section",
                                command=lambda: [context_menu.unpost(), self._edit_section_from_context(section_idx, seg_idx)])
        
        # Display menu at mouse cursor position
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()
    
    def _edit_action_from_context(self, section_idx, seg_idx, seq_idx, action_idx):
        """Edit a single action from context menu."""
        # Navigate to the action
        section = self.song_data['sections'][section_idx]
        
        if seg_idx is not None and 'segments' in section:
            timing_info = section['segments'][seg_idx]
        else:
            timing_info = section
        
        sequence = timing_info['sequences'][seq_idx]
        action = sequence['actions'][action_idx]
        tempo = timing_info.get('tempo', 1.0)
        
        # Open action editor dialog
        dialog = ActionDialog(self.root, action, tempo)
        if dialog.result:
            sequence['actions'][action_idx] = dialog.result
            self._draw_timeline()
    
    def _edit_sequence_from_context(self, section_idx, seg_idx, seq_idx, action_idx):
        """Edit sequence from context menu (same as left-click)."""
        if seg_idx is not None:
            seq_tag = f'seq_{section_idx}_{seg_idx}_{seq_idx}_{action_idx}'
        else:
            seq_tag = f'seq_{section_idx}_none_{seq_idx}_{action_idx}'
        self._edit_action_from_click(seq_tag)
    
    def _edit_segment_from_context(self, section_idx, seg_idx):
        """Edit segment from context menu."""
        section = self.song_data['sections'][section_idx]
        if 'segments' not in section or seg_idx >= len(section['segments']):
            return
        
        segment = section['segments'][seg_idx]
        dialog = SegmentDialog(self.root, segment)
        if dialog.result:
            section['segments'][seg_idx] = dialog.result
            self._draw_timeline()
    
    def _edit_section_from_context(self, section_idx, seg_idx=None):
        """Edit section from context menu."""
        if section_idx >= len(self.song_data['sections']):
            return
        
        section = self.song_data['sections'][section_idx]
        dialog = SectionDialog(self.root, section, initial_segment_idx=seg_idx)
        if dialog.result:
            self.song_data['sections'][section_idx] = dialog.result
            self._refresh_section_list()
            self._update_timing_label()
            self._draw_timeline()
    
    def _edit_action_from_click(self, seq_tag):
        """Edit a sequence based on the clicked action's sequence tag."""
        # Parse sequence tag: seq_<section>_<segment>_<sequence>_<action>
        parts = seq_tag.split('_')
        if len(parts) != 5:
            return
        
        section_idx = int(parts[1])
        seg_idx = None if parts[2] == 'none' else int(parts[2])
        seq_idx = int(parts[3])
        action_idx = int(parts[4])
        
        # Navigate to the sequence
        section = self.song_data['sections'][section_idx]
        
        if seg_idx is not None and 'segments' in section:
            timing_info = section['segments'][seg_idx]
        else:
            timing_info = section
        
        sequence = timing_info['sequences'][seq_idx]
        tempo = timing_info.get('tempo', 1.0)
        total_beats = timing_info.get('total_beats', 0)
        
        # Open sequence editor dialog with the clicked action selected
        dialog = SequenceDialog(self.root, sequence, tempo, total_beats, initial_action_idx=action_idx)
        if dialog.result:
            # Update the sequence with edited data
            timing_info['sequences'][seq_idx] = dialog.result
            self._draw_timeline()
    
    def _canvas_scroll(self, event):
        """Handle mouse wheel scroll."""
        if event.state & 0x0004:  # Control key
            # Zoom
            if event.delta > 0:
                self._zoom_in()
            else:
                self._zoom_out()
        else:
            # Check if mouse is over waveform area for horizontal zoom
            x = self.timeline_canvas.canvasx(event.x)
            y = self.timeline_canvas.canvasy(event.y)
            items = self.timeline_canvas.find_overlapping(x, y, x, y)
            is_over_waveform = any('waveform' in self.timeline_canvas.gettags(item) for item in items)
            
            if is_over_waveform:
                # Waveform horizontal zoom
                if event.delta > 0:
                    self.waveform_zoom = min(self.waveform_zoom * 1.2, 10.0)
                else:
                    self.waveform_zoom = max(self.waveform_zoom / 1.2, 1.0)
                self.waveform_zoom_label.config(text=f"Amp: {int(self.waveform_zoom * 100)}%")
                self._draw_timeline()  # Redraw to apply zoom
            else:
                # Normal scroll
                self.timeline_canvas.yview_scroll(int(-event.delta / 120), 'units')
    
    def _canvas_scroll_linux(self, event):
        """Handle mouse wheel scroll on Linux (Button-4/5)."""
        # Button-4 is scroll up, Button-5 is scroll down
        scroll_up = (event.num == 4)
        
        if event.state & 0x0004:  # Control key
            # Zoom
            if scroll_up:
                self._zoom_in()
            else:
                self._zoom_out()
        else:
            # Check if mouse is over waveform area for horizontal zoom
            x = self.timeline_canvas.canvasx(event.x)
            y = self.timeline_canvas.canvasy(event.y)
            items = self.timeline_canvas.find_overlapping(x, y, x, y)
            is_over_waveform = any('waveform' in self.timeline_canvas.gettags(item) for item in items)
            
            if is_over_waveform:
                # Waveform horizontal zoom
                if scroll_up:
                    self.waveform_zoom = min(self.waveform_zoom * 1.2, 10.0)
                else:
                    self.waveform_zoom = max(self.waveform_zoom / 1.2, 1.0)
                self.waveform_zoom_label.config(text=f"Amp: {int(self.waveform_zoom * 100)}%")
                self._draw_timeline()  # Redraw to apply zoom
            else:
                # Normal scroll
                if scroll_up:
                    self.timeline_canvas.yview_scroll(-1, 'units')
                else:
                    self.timeline_canvas.yview_scroll(1, 'units')
    
    def _on_window_resize(self, event):
        """Handle window resize events."""
        # Only handle resize of the main window, not child widgets
        if event.widget != self.root:
            return
        
        # Cancel any pending resize redraw
        if hasattr(self, '_resize_timer'):
            self.root.after_cancel(self._resize_timer)
        
        # Debounce - schedule redraw after 100ms of no resize events
        if self.audio_data:
            self._resize_timer = self.root.after(100, self._do_resize_redraw)
    
    def _do_resize_redraw(self):
        """Actually perform the resize redraw."""
        if self.audio_data:
            self._draw_channel_bar()
            self._draw_timeline()
    
    def _canvas_motion(self, event):
        """Handle mouse motion for tooltips and cursor changes."""
        x = self.timeline_canvas.canvasx(event.x)
        y = self.timeline_canvas.canvasy(event.y)
        
        # Store mouse position for later updates
        self.last_mouse_x = event.x
        self.last_mouse_y = event.y
        
        # Check if hovering over an action
        items = self.timeline_canvas.find_overlapping(x-2, y-2, x+2, y+2)
        
        # Check if hovering over splitter and change cursor
        hovering_splitter = False
        for item in items:
            if 'waveform_splitter' in self.timeline_canvas.gettags(item):
                hovering_splitter = True
                self.timeline_canvas.config(cursor='sb_h_double_arrow')
                break
        
        if not hovering_splitter:
            self.timeline_canvas.config(cursor='arrow')
        
        # Remove existing tooltip and waveform preview
        self.timeline_canvas.delete('tooltip')
        self.timeline_canvas.delete('waveform_preview')
        
        # Check if hovering over waveform
        hovering_waveform = False
        for item in items:
            if 'waveform' in self.timeline_canvas.gettags(item):
                hovering_waveform = True
                break
        
        if hovering_waveform:
            # Draw preview line at cursor position
            canvas_width = self.timeline_canvas.winfo_width()
            self.timeline_canvas.create_line(0, y, canvas_width, y,
                                            fill='#FFEB3B', width=2, dash=(4, 4),
                                            tags='waveform_preview')
            
            # Calculate and display timestamp
            time_pos = y / (self.zoom_level * 100)
            time_pos = max(0, min(time_pos, self.audio_duration))
            
            # Format timestamp as MM:SS.mmm
            minutes = int(time_pos // 60)
            seconds = time_pos % 60
            time_text = f"{minutes}:{seconds:06.3f}"
            
            # Draw timestamp near cursor
            text_item = self.timeline_canvas.create_text(
                x - 80, y - 20, text=time_text,
                fill='#FFEB3B', font=('Courier', 11, 'bold'), anchor='w',
                tags='waveform_preview'
            )
            
            # Add background to timestamp
            bbox = self.timeline_canvas.bbox(text_item)
            if bbox:
                padding = 3
                bg_item = self.timeline_canvas.create_rectangle(
                    bbox[0] - padding, bbox[1] - padding,
                    bbox[2] + padding, bbox[3] + padding,
                    fill='#333', outline='#FFEB3B', tags='waveform_preview'
                )
                self.timeline_canvas.tag_lower(bg_item, text_item)
            return
        
        for item in items:
            tags = self.timeline_canvas.gettags(item)
            
            # Show tooltip for actions
            if 'action' in tags:
                # Create tooltip background
                tooltip_text = self._get_item_tooltip(tags)
                if tooltip_text:
                    # Position tooltip near cursor
                    tooltip_x = x + 10
                    tooltip_y = y - 10
                    
                    # Create tooltip
                    text_item = self.timeline_canvas.create_text(
                        tooltip_x, tooltip_y, text=tooltip_text,
                        fill='white', font=('Arial', 9), anchor='nw',
                        tags='tooltip'
                    )
                    
                    # Get text bounds for background
                    bbox = self.timeline_canvas.bbox(text_item)
                    if bbox:
                        padding = 4
                        bg_item = self.timeline_canvas.create_rectangle(
                            bbox[0] - padding, bbox[1] - padding,
                            bbox[2] + padding, bbox[3] + padding,
                            fill='#333', outline='#666', tags='tooltip'
                        )
                        self.timeline_canvas.tag_lower(bg_item, text_item)
                break
    
    def _get_item_tooltip(self, tags):
        """Generate tooltip text based on item tags."""
        if 'note' in tags:
            # Extract channel from tags
            for tag in tags:
                if tag.startswith('ch'):
                    ch = tag[2:]
                    return f"Note: Channel {int(ch) + 1}\nClick to edit"
        elif 'phrase' in tags:
            # Try to extract phrase ID and show details
            for tag in tags:
                if tag.startswith('phrase'):
                    phrase_id = tag[6:]  # Remove 'phrase' prefix
                    phrase_data = self.song_data.get('phrases', {}).get(phrase_id)
                    if phrase_data:
                        desc = phrase_data.get('description', '')
                        note_count = len(phrase_data.get('notes', []))
                        return f"Phrase {phrase_id}: {desc}\n{note_count} notes\nClick to edit sequence"
            return "Phrase Action\nClick to edit sequence"
        elif 'all_channels' in tags:
            return "All Channels\nFlash all 10 channels\nClick to edit"
        elif 'step_up' in tags:
            return "Step Up\nSequential activation up\nClick to edit"
        elif 'step_down' in tags:
            return "Step Down\nSequential activation down\nClick to edit"
        elif 'flash_mode' in tags:
            return "Flash Mode\nMode change\nClick to edit"
        return None
    
    # ========== Tool Functions ==========
    
    def _tool_changed(self):
        """Handle tool selection change."""
        self.current_tool = self.tool_var.get()
    
    def _add_beat_at_position(self, y_pos):
        """Add a beat marker at the given Y position."""
        if not self.mp3_path:
            messagebox.showwarning("No Audio Loaded", "Please load an MP3 file first.\n(File → Open MP3...)")
            return
        
        # Convert Y position to time
        time = y_pos / (self.zoom_level * 100)
        
        # Find which section this belongs to
        # This is a simplified version - would need more logic for proper section management
        messagebox.showinfo("Add Beat", f"Would add beat at time {time:.3f}s")
    
    def _add_channel_note_at_position(self, x_pos, y_pos):
        """Add a channel note at the given position."""
        if not self.mp3_path:
            messagebox.showwarning("No Audio Loaded", "Please load an MP3 file first.\n(File → Open MP3...)")
            return
        # Determine which channel column was clicked
        canvas_width = self.timeline_canvas.winfo_width() or 1200
        left_margin = 60
        timeline_width = canvas_width - left_margin - 100
        channel_width = timeline_width / 10
        
        col_idx = int((x_pos - left_margin) / channel_width)
        if 0 <= col_idx < 10:
            channel_num = self.channel_order[col_idx]
            time = y_pos / (self.zoom_level * 100)
            
            # Add note to current section
            # This is simplified - full implementation would need dialog for duration, etc.
            messagebox.showinfo("Add Note", f"Would add note on channel {channel_num} at time {time:.3f}s")
    
    # ========== Playback Controls ==========
    
    def _toggle_playback(self):
        """Toggle between play and pause states."""
        if self.is_playing:
            self._pause_playback()
        else:
            self._start_playback()
    
    def _start_playback(self):
        """Start or resume audio playback from current position.
        
        Implements dual-loop playback system:
        - Slow loop (200ms): Checks actual pygame position and corrects drift
        - Fast loop (16ms): Interpolates position for smooth 60fps updates
        
        Both loops use update_id to detect when playback is stopped/restarted.
        """
        if not self.mp3_path:
            messagebox.showwarning("No Audio", "Please load an MP3 file first.")
            return
        
        # Set playback state and invalidate old update loops
        self.is_playing = True
        self.update_id += 1  # Any loops with old ID will exit
        self.play_button.config(text="⏸ Pause", bg='#FF9800')
        
        # Initialize channel states for playback start
        self._update_channel_states()
        self._update_channel_bar_lights()
        
        # Load audio and start from current position
        pygame.mixer.music.load(self.mp3_path)
        pygame.mixer.music.play(start=self.playback_position)
        
        # Initialize position tracking for drift correction
        self.playback_start_position = self.playback_position
        self.last_actual_position = self.playback_position
        self.last_update_time = time.time()
        
        # Auto-scroll timeline to keep playback marker visible
        self._scroll_to_playback_position()
        
        # Start both update loops with current update_id
        self._interpolate_playback_position(self.update_id)  # 60fps smooth updates
        self._update_playback_position(self.update_id)  # Periodic drift correction
    
    def _pause_playback(self):
        """Pause audio playback and update UI state.
        
        Stopping the music ensures clean state for future play() calls.
        """
        self.is_playing = False
        self.play_button.config(text="▶ Play", bg='#4CAF50')
        
        # Stop pygame mixer completely
        pygame.mixer.music.stop()
        
        # Reset channel states (all off when paused)
        self.channel_states = [False] * 10
        self.active_notes = []
        self._update_channel_bar_lights()
        self.active_notes = []
        self._update_channel_bar_lights()
    
    def _rewind_playback(self):
        """Rewind to beginning of song, preserving playback state.
        
        If playing when rewind is called, will resume playing from start.
        If paused, will just reset position without playing.
        """
        was_playing = self.is_playing
        
        # Stop playback completely before resetting position
        self.is_playing = False
        pygame.mixer.music.stop()
        
        # Reset position to start
        self.playback_position = 0
        self.playback_start_position = 0
        
        # Update channel states for start position (all off)
        self._update_channel_states()
        self._update_channel_bar_lights()
        
        # Refresh visualization and scroll to top
        self._draw_timeline()
        self.timeline_canvas.yview_moveto(0)
        
        # Resume playing if we were playing before rewind
        if was_playing:
            self._start_playback()
    
    def _update_playback_position(self, my_update_id):
        """Periodically check actual playback position and correct drift (200ms interval).
        
        This is the "slow loop" that provides accurate position from pygame mixer.
        Runs every 200ms to check mixer.music.get_pos() and update tracking variables.
        
        Args:
            my_update_id: Captured update_id value - exits if doesn't match current
        """
        # Exit if this loop has been invalidated by new playback start
        if my_update_id != self.update_id:
            return
        
        if self.is_playing:
            # Get actual position from pygame mixer (milliseconds → seconds)
            mixer_pos = pygame.mixer.music.get_pos() / 1000.0
            
            # Calculate absolute playback position
            if mixer_pos >= 0:
                actual_position = self.playback_start_position + mixer_pos
                
                # Update tracking variables for interpolation loop
                self.last_actual_position = actual_position
                self.last_update_time = time.time()
                
                # Apply correction if drift exceeds 100ms threshold
                if abs(actual_position - self.playback_position) > 0.1:
                    self.playback_position = actual_position
            
            # Check for end of song
            if self.playback_position >= self.audio_duration:
                # CRITICAL: Set is_playing=False BEFORE rewind to prevent auto-restart
                # _rewind_playback() checks was_playing and would loop otherwise
                self.is_playing = False
                pygame.mixer.music.stop()
                self.play_button.config(text="▶ Play", bg='#4CAF50')
                self._rewind_playback()
            else:
                # Continue checking position every 200ms
                self.root.after(200, lambda: self._update_playback_position(my_update_id))
    
    def _interpolate_playback_position(self, my_update_id):
        """Smoothly interpolate playback position for 60fps updates (16ms interval).
        
        This is the "fast loop" that provides smooth animation between position checks.
        Estimates position based on elapsed time since last_actual_position update.
        
        Args:
            my_update_id: Captured update_id value - exits if doesn't match current
        """
        # Exit if this loop has been invalidated by new playback start
        if my_update_id != self.update_id:
            return
        
        if self.is_playing:
            # Estimate position based on time elapsed since last position check
            current_time = time.time()
            time_elapsed = current_time - self.last_update_time
            
            # Interpolate assuming real-time playback (1:1 ratio)
            self.playback_position = self.last_actual_position + time_elapsed
            
            # Update flash pattern if in flash mode
            if self.current_flash_mode > 0:
                self._update_flash_pattern()
            
            # Update channel states and visual elements
            self._update_channel_states()
            self._update_channel_bar_lights()
            
            # Update only playback line (much faster than full timeline redraw)
            self._update_playback_line()
            self._scroll_to_playback_position()
            
            # Continue interpolation at ~60fps (16ms interval)
            self.root.after(16, lambda: self._interpolate_playback_position(my_update_id))
    
    def _update_playback_line(self):
        """Update playback position indicator without full timeline redraw.
        
        Fast update method for smooth 60fps animation. Only redraws the green
        playback line without recalculating action positions or waveform.
        """
        # Remove previous playback line
        self.timeline_canvas.delete('playback_pos')
        
        # Calculate new line position
        canvas_width = self.timeline_canvas.winfo_width()
        if canvas_width <= 1:
            return
        
        left_margin = 60
        timeline_width = canvas_width - left_margin - self.waveform_width - 20
        y = int(self.playback_position * self.zoom_level * 100)  # Convert time to pixels
        
        # Draw green horizontal line across timeline
        self.timeline_canvas.create_line(0, y, left_margin + timeline_width, y,
                                        fill='#00FF00', width=3, tags='playback_pos')
        
        # Update position label
        minutes = int(self.playback_position // 60)
        seconds = self.playback_position % 60
        self.position_label.config(text=f"Position: {minutes}:{seconds:04.1f}")
        
        # Update channel states and visual indicators
        self._update_channel_states()
        self._update_channel_bar_lights()
    
    def _scroll_to_playback_position(self):
        """Scroll timeline to follow playback position."""
        if not self.is_playing:
            return
        
        # Get canvas height and scrollable region
        canvas_height = self.timeline_canvas.winfo_height()
        scrollregion = self.timeline_canvas.cget('scrollregion').split()
        if len(scrollregion) < 4:
            return
        
        total_height = float(scrollregion[3])
        
        # Calculate playback line position in pixels
        playback_y = int(self.playback_position * self.zoom_level * 100)
        
        # Get current visible area
        yview = self.timeline_canvas.yview()
        visible_top = yview[0] * total_height
        visible_bottom = yview[1] * total_height
        
        # Define threshold (70% down the visible area before starting to scroll)
        scroll_threshold = visible_top + (canvas_height * 0.7)
        
        # Only scroll if playback line is below threshold or off screen
        if playback_y > scroll_threshold or playback_y < visible_top:
            # Center the playback line at 30% from top of visible area
            target_top = playback_y - (canvas_height * 0.3)
            target_top = max(0, min(target_top, total_height - canvas_height))
            
            # Scroll to position
            self.timeline_canvas.yview_moveto(target_top / total_height)
            
            # Update waveform preview with new canvas coordinates
            if self.last_mouse_x > 0 and self.last_mouse_y > 0:
                # Create a fake event with stored mouse position
                class FakeEvent:
                    def __init__(self, x, y):
                        self.x = x
                        self.y = y
                
                fake_event = FakeEvent(self.last_mouse_x, self.last_mouse_y)
                # Trigger motion handler to update preview
                self.root.after(10, lambda: self._canvas_motion(fake_event))
    
    def _find_next_override_time(self, beat_time: float, timing_info: Dict, channels: List[int]) -> float:
        """Find when the specified channels get overridden by a later action.
        
        Args:
            beat_time: Start time of the current action
            timing_info: Segment/section dict with sequences
            channels: List of channel numbers (0-9) to check
            
        Returns:
            Time in seconds when channels are overridden, or beat_time + 1000 if never
        """
        start_time = timing_info.get('start_time', 0)
        tempo = timing_info.get('tempo', 1.0)
        total_beats = timing_info.get('total_beats', 0)
        
        override_time = beat_time + 1000  # Default to far future
        
        # Collect all future actions that could affect these channels
        sequences = timing_info.get('sequences', [])
        for sequence in sequences:
            # Determine which beats this sequence applies to
            beats_to_check = []
            if 'beat' in sequence:
                beats_to_check = [sequence['beat']]
            elif 'beats' in sequence:
                beats_to_check = sequence['beats']
            elif sequence.get('all_beats'):
                beats_to_check = list(range(1, total_beats + 1))
            
            # Check each beat
            for beat in beats_to_check:
                action_time = start_time + ((beat - 1) * tempo)
                
                # Only consider actions after current beat_time
                if action_time <= beat_time:
                    continue
                
                # Check if any action at this beat affects our channels
                for action in sequence.get('actions', []):
                    action_type = action.get('type')
                    
                    # These actions affect all channels
                    if action_type in ['all_channels', 'step_up', 'step_down']:
                        override_time = min(override_time, action_time)
                        break
                    
                    # Note actions affect specific channels
                    elif action_type == 'note':
                        if action.get('channel') in channels:
                            override_time = min(override_time, action_time)
                    
                    # Phrase actions affect specific channels
                    elif action_type == 'phrase':
                        phrase_id = str(action.get('id'))
                        if 'phrases' in self.song_data:
                            phrase = self.song_data['phrases'].get(phrase_id, {})
                            for note in phrase.get('notes', []):
                                if note.get('channel') in channels:
                                    override_time = min(override_time, action_time)
                                    break
        
        return override_time
    
    def _update_channel_states(self):
        """Calculate which channels should be active at current playback position.
        
        This method traverses the song structure to determine which notes/actions
        are currently playing based on the playback_position. Updates self.channel_states
        and self.active_notes to track what's currently on.
        
        Also tracks flash_mode changes to apply random flashing to inactive channels.
        """
        if not self.song_data or not self.song_data.get('sections'):
            return
        
        current_time = self.playback_position
        new_states = [False] * 10
        active_notes = []
        
        # Track the most recent flash mode (default -1 = all off unless explicitly set)
        flash_mode = -1  # Start with all off
        
        # Iterate through all sections to find active notes and flash mode changes
        for section in self.song_data['sections']:
            # Handle sections with segments (varying tempo)
            if 'segments' in section:
                for segment in section['segments']:
                    flash_mode = self._check_segment_for_active_channels(
                        segment, current_time, new_states, active_notes, flash_mode
                    )
            # Handle sections with single timing
            else:
                flash_mode = self._check_segment_for_active_channels(
                    section, current_time, new_states, active_notes, flash_mode
                )
        
        # Update flash mode if changed
        if flash_mode != self.current_flash_mode:
            self.current_flash_mode = flash_mode
            self._update_flash_pattern()  # Generate new random pattern
        
        # Apply flash mode to inactive channels
        if self.current_flash_mode > 0:  # Mode 1, 2, or 3 (random flashing)
            for ch in range(10):
                if not new_states[ch]:  # Channel not active from song actions
                    new_states[ch] = self.flash_channel_states[ch]
        elif self.current_flash_mode == 0:  # Mode 0 (always on)
            # Channels not explicitly controlled stay on
            for ch in range(10):
                if not new_states[ch]:
                    new_states[ch] = True
        # Mode -1 (all off) - inactive channels stay off (default)
        
        # Update channel states
        self.channel_states = new_states
        self.active_notes = active_notes
    
    def _check_segment_for_active_channels(self, segment: Dict, current_time: float, 
                                           states: List[bool], active_notes: List, flash_mode: int = -1):
        """Check a segment/section for notes active at current_time.
        
        Args:
            segment: Section or segment dict with start_time, tempo, sequences
            current_time: Current playback position in seconds
            states: List of 10 booleans to update (channel active states)
            active_notes: List to append (channel, end_time) tuples
            flash_mode: Current flash mode from previous segments
            
        Returns:
            Updated flash_mode value (if flash_mode actions encountered)
        """
        start_time = segment.get('start_time', 0)
        tempo = segment.get('tempo', 1.0)
        total_beats = segment.get('total_beats', 0)
        
        # Skip if current time is before this segment starts
        if current_time < start_time:
            return flash_mode
        
        # Collect all actions with their beat times for proper chronological ordering
        # This is needed for step_up/step_down which can override each other
        actions_with_times = []
        
        # Check all sequences in this segment
        sequences = segment.get('sequences', [])
        for sequence in sequences:
            # Determine which beats this sequence applies to
            beats_to_check = []
            if 'beat' in sequence:
                beats_to_check = [sequence['beat']]
            elif 'beats' in sequence:
                beats_to_check = sequence['beats']
            elif sequence.get('all_beats'):
                # For all_beats, check every beat from 1 to total_beats
                beats_to_check = list(range(1, total_beats + 1))
            
            # Collect actions with their beat start times
            for beat in beats_to_check:
                beat_start_time = start_time + ((beat - 1) * tempo)
                for action in sequence.get('actions', []):
                    actions_with_times.append((beat_start_time, action))
        
        # Sort by time so we process chronologically
        actions_with_times.sort(key=lambda x: x[0])
        
        # Track most recent activation for each channel: (start_time, end_time)
        # Later actions override earlier ones
        channel_activations = {}  # {channel: (start_time, end_time)}
        
        # Process actions chronologically, tracking flash_mode changes
        for beat_start_time, action in actions_with_times:
            if beat_start_time > current_time:
                break  # No need to process future actions
            
            # Track flash_mode changes
            if action.get('type') == 'flash_mode':
                mode = action.get('mode', 0)
                flash_mode = mode
            
            self._process_action_activation(
                action, beat_start_time, current_time, tempo, channel_activations
            )
        
        # Now determine which channels are currently active
        for ch in range(10):
            if ch in channel_activations:
                # Check all activations for this channel
                for start_time, end_time in channel_activations[ch]:
                    if start_time <= current_time < end_time:
                        states[ch] = True
                        active_notes.append((ch, end_time))
                        break  # Only need to mark as active once
        
        return flash_mode
    
    def _update_flash_pattern(self):
        """Update flash channel states with seeded random pattern.
        
        Uses fixed seed combined with playback position to generate reproducible
        "random" flash patterns that remain consistent across playback.
        """
        import random
        
        # Use fixed seed combined with time to generate reproducible pattern
        # Quantize time to flash mode interval for stable patterns
        if self.current_flash_mode == 1:  # Slow
            interval = 0.5  # Update pattern every 0.5s
        elif self.current_flash_mode == 2:  # Medium
            interval = 0.3
        elif self.current_flash_mode == 3:  # Fast
            interval = 0.1
        else:
            return  # No flashing for modes 0 or -1
        
        # Quantize playback position to interval
        time_slot = int(self.playback_position / interval)
        seed = self.flash_random_seed + time_slot
        
        # Generate random pattern for each channel
        random.seed(seed)
        for ch in range(10):
            self.flash_channel_states[ch] = random.random() > 0.5
    
    def _process_action_activation(self, action: Dict, beat_start_time: float,
                                   current_time: float, tempo: float,
                                   channel_activations: Dict):
        """Process an action and update channel activations.
        
        For each action, we record all note activations. When an action is processed,
        its beat_start_time determines override behavior - if a later action affects
        the same channel, it will appear later in chronological order and override.
        
        Args:
            action: Action dict
            beat_start_time: When the beat starts (seconds)
            current_time: Current playback position
            tempo: Current tempo
            channel_activations: Dict mapping channel to list of (start_time, end_time) tuples
        """
        action_type = action.get('type')
        
        if action_type == 'note':
            channel = action.get('channel', 0)
            delay = action.get('delay', 0)
            duration = action.get('duration', 0.25)
            
            note_start = beat_start_time + delay
            note_end = note_start + duration
            
            # Clear any existing activations for this channel from earlier actions
            # (this simulates the hardware override behavior)
            if channel not in channel_activations:
                channel_activations[channel] = []
            else:
                # Keep only activations from this beat time or later
                channel_activations[channel] = [
                    (s, e) for s, e in channel_activations[channel]
                    if s >= beat_start_time
                ]
            
            channel_activations[channel].append((note_start, note_end))
        
        elif action_type == 'phrase':
            phrase_id = str(action.get('id', ''))
            if phrase_id in self.song_data.get('phrases', {}):
                phrase = self.song_data['phrases'][phrase_id]
                
                # Collect all notes from this phrase
                phrase_notes = []
                for note in phrase.get('notes', []):
                    channel = note.get('channel', 0)
                    delay_mult = note.get('delay_multiplier', 0)
                    duration_mult = note.get('duration_multiplier', 0.25)
                    
                    note_start = beat_start_time + (tempo * delay_mult)
                    note_end = note_start + (tempo * duration_mult)
                    phrase_notes.append((channel, note_start, note_end))
                
                # Group notes by channel to handle multiple notes per channel correctly
                channels_in_phrase = set(ch for ch, _, _ in phrase_notes)
                
                # Clear activations from earlier actions for channels used in this phrase
                for ch in channels_in_phrase:
                    if ch not in channel_activations:
                        channel_activations[ch] = []
                    else:
                        # Keep only activations from this beat time or later
                        # (remove activations from earlier beat times that this action overrides)
                        channel_activations[ch] = [
                            (s, e) for s, e in channel_activations[ch]
                            if s >= beat_start_time
                        ]
                
                # Now add all phrase notes
                for channel, note_start, note_end in phrase_notes:
                    channel_activations[channel].append((note_start, note_end))
        
        elif action_type == 'all_channels':
            duration = action.get('duration')
            if duration is None:
                duration_mult = action.get('duration_multiplier', 0.25)
                duration = tempo * duration_mult
            
            for ch in range(10):
                note_start = beat_start_time
                note_end = note_start + duration
                
                if ch not in channel_activations:
                    channel_activations[ch] = []
                else:
                    channel_activations[ch] = [
                        (s, e) for s, e in channel_activations[ch]
                        if s >= beat_start_time
                    ]
                
                channel_activations[ch].append((note_start, note_end))
        
        elif action_type == 'step_up':
            # step_up: Channels turn on sequentially, stay on indefinitely
            # First channel blinks (duration=tempo), others stay on
            order = [9, 8, 1, 6, 5, 3, 2, 4, 7, 0]
            for x in range(10):
                delay = tempo * 0.1 * x
                note_start = beat_start_time + delay
                
                if x == 0:
                    # First channel has finite duration
                    duration = tempo
                    note_end = note_start + duration
                else:
                    # Other channels stay on until overridden
                    note_end = current_time + 1000
                
                ch = order[x]
                if ch not in channel_activations:
                    channel_activations[ch] = []
                else:
                    channel_activations[ch] = [
                        (s, e) for s, e in channel_activations[ch]
                        if s >= beat_start_time
                    ]
                
                channel_activations[ch].append((note_start, note_end))
        
        elif action_type == 'step_down':
            # step_down: All channels turn on, then turn off sequentially
            order = [0, 7, 4, 2, 3, 5, 6, 1, 8, 9]
            for x in range(10):
                note_start = beat_start_time
                
                if x == 9:
                    # Last channel stays on indefinitely
                    note_end = current_time + 1000
                else:
                    # Other channels have increasing durations
                    duration = tempo * 0.1 * (x + 1)
                    note_end = note_start + duration
                
                ch = order[x]
                if ch not in channel_activations:
                    channel_activations[ch] = []
                else:
                    channel_activations[ch] = [
                        (s, e) for s, e in channel_activations[ch]
                        if s >= beat_start_time
                    ]
                
                channel_activations[ch].append((note_start, note_end))
    
    
    # ========== Zoom Controls ==========
    
    def _zoom_in(self):
        """Zoom in on timeline."""
        self.zoom_level = min(self.zoom_level * 1.2, 20)
        self.zoom_label.config(text=f"{int(self.zoom_level * 100)}%")
        self._draw_timeline()
    
    def _zoom_out(self):
        """Zoom out on timeline."""
        self.zoom_level = max(self.zoom_level / 1.2, 0.1)
        self.zoom_label.config(text=f"{int(self.zoom_level * 100)}%")
        self._draw_timeline()
    
    # ========== Section Management ==========
    
    def _section_selected(self, event):
        """Handle section selection from listbox."""
        selection = self.section_listbox.curselection()
        if selection:
            self.current_section_index = selection[0]
            self._update_timing_label()
            self._draw_timeline()
    
    def _update_timing_label(self):
        """Update the timing info label for current section."""
        if self.song_data['sections'] and self.current_section_index < len(self.song_data['sections']):
            section = self.song_data['sections'][self.current_section_index]
            
            # Get timing from section or first segment
            if 'segments' in section:
                if section['segments']:
                    seg = section['segments'][0]
                    start = seg.get('start_time', 0)
                    tempo = seg.get('tempo', 1.0)
                    beats = seg.get('total_beats', 0)
                else:
                    start, tempo, beats = 0, 1.0, 0
            else:
                start = section.get('start_time', 0)
                tempo = section.get('tempo', 1.0)
                beats = section.get('total_beats', 0)
            
            self.timing_label.config(text=f"Start: {start:.2f}s | Tempo: {tempo:.3f}s | Beats: {beats}")
        else:
            self.timing_label.config(text="No section selected")
    
    def _refresh_section_list(self):
        """Refresh the section listbox."""
        self.section_listbox.delete(0, tk.END)
        for section in self.song_data['sections']:
            name = section.get('name', 'Unnamed')
            self.section_listbox.insert(tk.END, name)
    
    def _add_section(self):
        """Add a new section."""
        if not self.mp3_path:
            messagebox.showwarning("No Audio Loaded", "Please load an MP3 file first.\n(File → Open MP3...)")
            return
        
        dialog = SectionDialog(self.root, None)
        result = dialog.result
        
        if result:
            self.song_data['sections'].append(result)
            self._refresh_section_list()
            self._draw_timeline()
    
    def _edit_section(self):
        """Edit the selected section."""
        if not self.mp3_path:
            messagebox.showwarning("No Audio Loaded", "Please load an MP3 file first.\n(File → Open MP3...)")
            return
        if not self.song_data['sections'] or self.current_section_index >= len(self.song_data['sections']):
            messagebox.showwarning("No Selection", "Please select a section to edit.")
            return
        
        section = self.song_data['sections'][self.current_section_index]
        dialog = SectionDialog(self.root, section)
        result = dialog.result
        
        if result:
            self.song_data['sections'][self.current_section_index] = result
            self._refresh_section_list()
            self._update_timing_label()
            self._draw_timeline()
    
    def _delete_section(self):
        """Delete the selected section."""
        if not self.song_data['sections'] or self.current_section_index >= len(self.song_data['sections']):
            messagebox.showwarning("No Selection", "Please select a section to delete.")
            return
        
        if messagebox.askyesno("Confirm Delete", "Delete this section?"):
            del self.song_data['sections'][self.current_section_index]
            self._refresh_section_list()
            self._draw_timeline()
    
    def _manage_sections(self):
        """Open section management dialog."""
        if not self.mp3_path:
            messagebox.showwarning("No Audio Loaded", "Please load an MP3 file first.\n(File → Open MP3...)")
            return
        messagebox.showinfo("Section Management", "Use the Section panel to add, edit, or delete sections.")
    
    def _manage_phrases(self):
        """Open phrase library management dialog."""
        if not self.mp3_path:
            messagebox.showwarning("No Audio Loaded", "Please load an MP3 file first.\n(File → Open MP3...)")
            return
        dialog = PhraseLibraryDialog(self.root, self.song_data.get('phrases', {}))
        if dialog.result:
            self.song_data['phrases'] = dialog.result
    
    def _delete_selected(self):
        """Delete selected items."""
        if not self.selected_items:
            return
        
        # Implement deletion logic
        messagebox.showinfo("Delete", "Would delete selected items")
    
    # ========== File Operations ==========
    
    def _close_song(self):
        """Close the current song and return to initial state."""
        if self.mp3_path and messagebox.askyesno("Close Song", "Close current song? Unsaved changes will be lost."):
            self.song_data = {
                "title": "",
                "artist": "",
                "description": "",
                "mp3_file": "",
                "sections": [],
                "phrases": {}
            }
            self.mp3_path = None
            self.audio_data = None
            self.waveform_data = None
            self.audio_duration = 0
            self.current_json_path = None
            self.title_var.set("")
            self.artist_var.set("")
            self.description_text.delete('1.0', tk.END)
            self.mp3_label.config(text="No file loaded", fg='#888')
            self._refresh_section_list()
            self._update_ui_state()
            self._draw_channel_bar()
            self._draw_timeline()
    
    def _open_json(self):
        """Open a JSON song file and load its referenced MP3."""
        filepath = filedialog.askopenfilename(
            title="Select JSON File",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            initialdir="songs"
        )
        
        if not filepath:
            return
        
        # Exclude playlist.json (it's not a song file)
        if os.path.basename(filepath) == "playlist.json":
            messagebox.showwarning(
                "Invalid Selection",
                "playlist.json is not a song file. Please select a song JSON file instead."
            )
            return
        
        try:
            # Load JSON first
            with open(filepath, 'r') as f:
                json_data = json.load(f)
            
            # Validate JSON structure
            validation_errors = []
            
            # Check required fields
            if not json_data.get('mp3_file'):
                validation_errors.append("Missing required field: 'mp3_file'")
            
            # Tempo can be at root level OR at section/segment level
            has_root_tempo = 'tempo' in json_data
            has_section_tempo = False
            
            # Check sections structure if present
            if 'sections' in json_data:
                if not isinstance(json_data['sections'], list):
                    validation_errors.append("'sections' must be a list")
                else:
                    for i, section in enumerate(json_data['sections']):
                        if not isinstance(section, dict):
                            validation_errors.append(f"Section {i} is not a valid object")
                            continue
                        if 'name' not in section:
                            validation_errors.append(f"Section {i} missing 'name'")
                        
                        # Section can have start_time OR segments with start_time
                        has_section_start = 'start_time' in section
                        has_segments = 'segments' in section
                        
                        if not has_section_start and not has_segments:
                            validation_errors.append(f"Section {i} must have either 'start_time' or 'segments'")
                        
                        if has_section_start:
                            if not isinstance(section['start_time'], (int, float)) or section['start_time'] < 0:
                                validation_errors.append(f"Section {i} 'start_time' must be a non-negative number")
                        
                        # Check if tempo exists at section level
                        if 'tempo' in section:
                            has_section_tempo = True
                            if not isinstance(section['tempo'], (int, float)) or section['tempo'] <= 0:
                                validation_errors.append(f"Section {i} 'tempo' must be a positive number")
                        
                        # Check segments if present
                        if has_segments:
                            if not isinstance(section['segments'], list):
                                validation_errors.append(f"Section {i} 'segments' must be a list")
                            else:
                                for j, segment in enumerate(section['segments']):
                                    if not isinstance(segment, dict):
                                        validation_errors.append(f"Section {i}, Segment {j} is not a valid object")
                                        continue
                                    if 'start_time' not in segment:
                                        validation_errors.append(f"Section {i}, Segment {j} missing 'start_time'")
                                    if 'tempo' in segment:
                                        has_section_tempo = True
                                        if not isinstance(segment['tempo'], (int, float)) or segment['tempo'] <= 0:
                                            validation_errors.append(f"Section {i}, Segment {j} 'tempo' must be a positive number")
            
            # Tempo must exist somewhere (root, section, or segment level)
            if not has_root_tempo and not has_section_tempo:
                validation_errors.append("Missing 'tempo' field (must be at root, section, or segment level)")
            
            # Check phrases structure if present (can use 'sequences' or 'notes')
            if 'phrases' in json_data:
                if not isinstance(json_data['phrases'], dict):
                    validation_errors.append("'phrases' must be an object/dictionary")
                else:
                    for phrase_name, phrase_data in json_data['phrases'].items():
                        if not isinstance(phrase_data, dict):
                            validation_errors.append(f"Phrase '{phrase_name}' is not a valid object")
                            continue
                        # Phrases can have either 'sequences' or 'notes' (legacy format)
                        has_sequences = 'sequences' in phrase_data
                        has_notes = 'notes' in phrase_data
                        if not has_sequences and not has_notes:
                            validation_errors.append(f"Phrase '{phrase_name}' must have either 'sequences' or 'notes'")
                        elif has_sequences and not isinstance(phrase_data['sequences'], list):
                            validation_errors.append(f"Phrase '{phrase_name}' 'sequences' must be a list")
                        elif has_notes and not isinstance(phrase_data['notes'], list):
                            validation_errors.append(f"Phrase '{phrase_name}' 'notes' must be a list")
            
            # If there are validation errors, show them and abort
            if validation_errors:
                error_msg = "Invalid song JSON file:\n\n" + "\n".join(f"• {err}" for err in validation_errors)
                messagebox.showerror("Validation Error", error_msg)
                return
            
            # Get MP3 filename from JSON
            mp3_filename = json_data.get('mp3_file')
            if not mp3_filename:
                messagebox.showerror("Error", "JSON file does not specify an mp3_file.")
                return
            
            # Try to find MP3 in songs folder
            mp3_path = os.path.join('songs', mp3_filename)
            if not os.path.exists(mp3_path):
                # Try relative to JSON file location
                json_dir = os.path.dirname(filepath)
                mp3_path = os.path.join(json_dir, mp3_filename)
                if not os.path.exists(mp3_path):
                    messagebox.showerror(
                        "MP3 Not Found",
                        f"Could not find MP3 file: {mp3_filename}\n\n"
                        f"Tried:\n- songs/{mp3_filename}\n- {os.path.join(json_dir, mp3_filename)}"
                    )
                    return
            
            # Load the MP3 audio
            self.mp3_path = mp3_path
            self.audio_data = AudioSegment.from_mp3(mp3_path)
            self.audio_duration = len(self.audio_data) / 1000.0
            
            # Generate waveform
            samples = np.array(self.audio_data.get_array_of_samples())
            if self.audio_data.channels == 2:
                samples = samples.reshape((-1, 2)).mean(axis=1)
            self.waveform_data = samples / np.max(np.abs(samples))
            
            # Load the JSON data
            self.song_data = json_data
            self.current_json_path = filepath
            
            # Update UI
            self.mp3_label.config(text=mp3_filename, fg='white')
            self.title_var.set(self.song_data.get('title', ''))
            self.artist_var.set(self.song_data.get('artist', ''))
            self.description_text.delete('1.0', tk.END)
            self.description_text.insert('1.0', self.song_data.get('description', ''))
            
            self._refresh_section_list()
            self._update_ui_state()
            self._draw_channel_bar()
            self._draw_timeline()
            
        except json.JSONDecodeError as e:
            messagebox.showerror("Invalid JSON", f"Failed to parse JSON file:\n\n{e}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load JSON file:\n{e}")
    
    def _open_mp3(self):
        """Open an MP3 file and check for corresponding JSON.
        
        Process:
        1. Shows file dialog to select MP3 from songs/ folder
        2. Loads audio using pydub (AudioSegment)
        3. Generates waveform visualization data
        4. Checks for matching JSON file (same name, .json extension)
        5. If JSON exists, prompts to load it; otherwise starts fresh
        6. Initializes pygame mixer for playback
        
        After loading:
        - Updates UI with audio metadata
        - Enables section editing controls
        - Draws initial timeline visualization
        """
        filepath = filedialog.askopenfilename(
            title="Select MP3 File",
            filetypes=[("MP3 Files", "*.mp3"), ("All Files", "*.*")],
            initialdir="songs"
        )
        
        if not filepath:
            return
        
        try:
            # Load audio
            self.mp3_path = filepath
            self.audio_data = AudioSegment.from_mp3(filepath)
            self.audio_duration = len(self.audio_data) / 1000.0  # Convert to seconds
            
            # Generate waveform data
            samples = np.array(self.audio_data.get_array_of_samples())
            if self.audio_data.channels == 2:
                samples = samples.reshape((-1, 2)).mean(axis=1)
            
            # Normalize
            self.waveform_data = samples / np.max(np.abs(samples))
            
            # Update UI
            filename = os.path.basename(filepath)
            self.mp3_label.config(text=filename, fg='white')
            self.song_data['mp3_file'] = filename
            
            # Check for existing JSON
            json_path = filepath.replace('.mp3', '.json')
            if os.path.exists(json_path):
                if messagebox.askyesno("Load Existing", f"Found {os.path.basename(json_path)}. Load it?"):
                    self._load_json(json_path)
            
            self._update_ui_state()
            self._draw_channel_bar()
            self._draw_timeline()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load MP3 file:\n{e}")
    
    def _load_json(self, filepath):
        """Load song data from JSON file."""
        try:
            with open(filepath, 'r') as f:
                self.song_data = json.load(f)
            
            # Track the JSON path for future saves
            self.current_json_path = filepath
            
            # Update UI
            self.title_var.set(self.song_data.get('title', ''))
            self.artist_var.set(self.song_data.get('artist', ''))
            self.description_text.delete('1.0', tk.END)
            self.description_text.insert('1.0', self.song_data.get('description', ''))
            
            self._refresh_section_list()
            self._draw_timeline()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load JSON file:\n{e}")
    
    def _save_song(self):
        """Save the current song data to JSON file.
        
        Process:
        1. Validates MP3 is loaded (required for save)
        2. Syncs UI fields (title, artist, description) to song_data dict
        3. Uses current_json_path if available, otherwise generates name from MP3
        4. Writes JSON with pretty formatting (indent=2)
        5. Shows success confirmation
        
        JSON Structure:
        {
          "title": "Song Name",
          "artist": "Artist Name", 
          "description": "Notes",
          "mp3_file": "filename.mp3",  // Filename only, not full path
          "sections": [...],            // Timing sections array
          "phrases": {...}              // Reusable patterns library
        }
        
        Note: mp3_file stores only the filename, assuming JSON and MP3 are
        in the same directory (typically songs/ folder).
        """
        if not self.song_data.get('mp3_file'):
            messagebox.showwarning("No MP3", "Please load an MP3 file first.")
            return
        
        # Update metadata from UI
        self.song_data['title'] = self.title_var.get()
        self.song_data['artist'] = self.artist_var.get()
        self.song_data['description'] = self.description_text.get('1.0', tk.END).strip()
        
        # Determine save path - use current_json_path if available (from load or save as)
        if self.current_json_path:
            json_path = self.current_json_path
        else:
            json_filename = os.path.splitext(self.song_data['mp3_file'])[0] + '.json'
            json_path = os.path.join('songs', json_filename)
            self.current_json_path = json_path
        
        try:
            with open(json_path, 'w') as f:
                json.dump(self.song_data, f, indent=2)
            messagebox.showinfo("Saved", f"Song saved to {json_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save song:\n{e}")
    
    def _save_song_as(self):
        """Save the song with a new filename."""
        if not self.song_data.get('mp3_file'):
            messagebox.showwarning("No MP3", "Please load an MP3 file first.")
            return
        
        filepath = filedialog.asksaveasfilename(
            title="Save Song As",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            initialdir="songs"
        )
        
        if not filepath:
            return
        
        # Update metadata
        self.song_data['title'] = self.title_var.get()
        self.song_data['artist'] = self.artist_var.get()
        self.song_data['description'] = self.description_text.get('1.0', tk.END).strip()
        
        try:
            with open(filepath, 'w') as f:
                json.dump(self.song_data, f, indent=2)
            # Update current path so future saves go to this location
            self.current_json_path = filepath
            messagebox.showinfo("Saved", f"Song saved to {filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save song:\n{e}")
    
    def _show_quick_start(self):
        """Display quick start guide."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Quick Start Guide")
        dialog.geometry("700x600")
        dialog.configure(bg='#2b2b2b')
        
        # Make dialog modal
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Create scrollable text area
        frame = tk.Frame(dialog, bg='#2b2b2b')
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        text = tk.Text(frame, wrap=tk.WORD, bg='#1e1e1e', fg='#d4d4d4',
                      font=('Courier', 10), yscrollcommand=scrollbar.set)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=text.yview)
        
        # Quick start content
        content = """PI LIGHTSHOW SONG EDITOR - QUICK START GUIDE

GETTING STARTED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Place your MP3 files in the songs/ folder

2. Load audio:
   • File → Open MP3... (loads audio, checks for matching JSON)
   • File → Open JSON... (loads song data and its referenced MP3)

3. Fill in song metadata (Title, Artist, Description)


CORE CONCEPTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Song Structure (hierarchical):
  Section → Contains timing information for a song part
    Segment → Optional sub-sections with different tempos
      Sequence → Defines WHEN actions happen (which beats)
        Action → Defines WHAT happens (which lights, how long)

Timing System:
  • Sections divide the song (intro, verse, chorus, etc.)
  • start_time: When section begins (in seconds)
  • tempo: Duration of one beat (in seconds)
  • total_beats: How many beats in this section
  • Beat 1 = first beat (JSON uses 1-indexed beats)


BASIC WORKFLOW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Create Sections
   Click "Add Section" to define song parts
   Choose structure:
   • Simple - Single timing (consistent tempo throughout)
   • Segments - Multiple timings (for tempo changes within section)
   
   Example: Verse at 120 BPM (tempo=0.5s), 16 beats

2. Add Sequences
   Define WHEN things happen using beat numbers:
   • Single beat: Beat 1 (fires once)
   • Multiple beats: Beats 1,5,9,13 (fires four times)
   • All beats: Every beat in section (fires every beat)

3. Add Actions
   Define WHAT happens at those beats:
   • note - Single channel activates (specify channel, delay, duration)
   • phrase - References reusable pattern from phrase library
   • all_channels - All 10 channels flash simultaneously
   • step_up - Sequential activation pattern (channels turn on in order)
   • step_down - Reverse cascade (all start, turn off in order)
   • flash_mode - Hardware mode change

4. Create Phrases (optional)
   Build reusable patterns:
   • Edit → Manage Phrases...
   • Each phrase contains multiple notes
   • Notes use delay_multiplier and duration_multiplier (× tempo)
   • Example: delay_multiplier=0.5 means note starts halfway through beat


INTERACTIVE EDITING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Left-Click Actions:
  • Click waveform area → Seek to that time position
  • Click action rectangle → Edit that sequence
  • Click phrase note → Edit individual note in phrase

Right-Click Menu (Hierarchical editing):
  • Edit Action → Single action within sequence
  • Edit Sequence → All actions for specific beats
  • Edit Segment → All sequences in segment (if applicable)
  • Edit Section → Entire timing section and all sequences


PLAYBACK CONTROLS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• Play/Pause button or Space - Start/stop audio playback
• Rewind button - Jump to beginning of song
• Click waveform - Seek to any time position
• Hover waveform - Preview seek position (shows timestamp tooltip)
• Green line - Current playback position (updates at 60fps)
• Position display - Shows current time (top right, green text)


ZOOM CONTROLS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Timeline Zoom (vertical):
  • +/- buttons - Zoom timeline in/out (10% to 2000%)
  • Changes pixels per second (higher = more vertical space)
  • Useful for precise editing or overview

Waveform Amplitude Zoom:
  • Scroll wheel over waveform - Zoom amplitude (100% to 1000%)
  • Makes quiet sections more visible
  • Helps align sequences to audio features


KEYBOARD SHORTCUTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Ctrl+S       Save song
Space        Play/Pause audio
Delete       Delete selected items
S            Select tool (default)
H            Hand/pan tool
B            Beat marker tool
N            Channel note tool


TIMELINE VISUALIZATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The vertical timeline shows your choreography visually:

Color Legend:
• Green rectangles - Individual channel notes (click to edit)
• Purple background - Phrases with individual note rectangles inside
• Orange bars - All channels flash action
• Blue bars - Step up (sequential activation up)
• Cyan bars - Step down (sequential deactivation)
• Yellow bars - Flash mode changes
• Red horizontal lines - Section boundaries
• Yellow dashed lines - Beat marker lines

Channel Layout (left to right):
  10, 9, 2, 7, 6, 4, 3, 5, 8, 1
  
Groups shown in header:
  [10+9] [2+7+6] [4+3] [5+8] [1]

Hover over any action to see detailed tooltip!
Click to edit, right-click for context menu.


TIMING MULTIPLIERS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Most timing uses multipliers for flexibility:

delay_multiplier:
  • How long after beat before note starts
  • delay_multiplier=0.0 → starts immediately at beat
  • delay_multiplier=0.5 → starts halfway through beat
  • Actual delay = delay_multiplier × tempo

duration_multiplier:
  • How long note stays on
  • duration_multiplier=0.5 → half beat duration
  • duration_multiplier=1.0 → full beat duration
  • Actual duration = duration_multiplier × tempo

Example:
  tempo=0.5s, delay_multiplier=0.2, duration_multiplier=0.8
  → starts 0.1s after beat, stays on 0.4s


TIPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• Save frequently with Ctrl+S
• Use phrases for repeating patterns
• Test in simulator: python3 lightshow.py --simulate songs/yourfile.json
• Click waveform to jump to specific timestamps
• Timeline auto-scrolls to follow playback
• Right-click actions for hierarchical editing options
• Zoom in for precision, zoom out for overview
• Start simple: one section, one sequence, one note
• Build complexity gradually as you learn the system
• Use multipliers in phrases (portable across tempos)
• Use absolute values for precise timing


DOCUMENTATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Complete documentation available in:
• EDITOR.md - Full feature documentation
• Example files: songs/carol.json, songs/madrussian.json


CHANNEL LAYOUT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  10   9   2   7   6   4   3   5   8   1
  |-----| |---------| |-----| |-----|
   10+9      2+7+6      4+3     5+8    1

Groups indicate physically close channels.
"""
        
        text.insert('1.0', content)
        text.config(state=tk.DISABLED)
        
        # Close button
        btn_frame = tk.Frame(dialog, bg='#2b2b2b')
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Close", command=dialog.destroy,
                 bg='#555', fg='white', padx=20).pack()
    
    def _show_about(self):
        """Display about dialog."""
        messagebox.showinfo("About Song Editor",
                           "Pi Lightshow Song Editor\n\n"
                           "Visual editor for creating lightshow choreography\n\n"
                           "Version 2.1.0\n\n"
                           "Features:\n"
                           "• Visual timeline with waveform\n"
                           "• 10-channel editing\n"
                           "• Comprehensive JSON format support\n"
                           "• Real-time playback preview\n"
                           "• Phrase library for reusable patterns\n\n"
                           "See EDITOR.md for complete documentation.")
    
    def run(self):
        """Run the editor application."""
        self.root.mainloop()


class SectionDialog:
    """Dialog for editing section properties and managing segments/sequences."""
    
    def __init__(self, parent, section_data, initial_segment_idx=None):
        self.result = None
        self.parent = parent
        self.initial_segment_idx = initial_segment_idx
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Section Editor")
        self.dialog.geometry("800x600")
        self.dialog.configure(bg='#2b2b2b')
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Initialize with existing data or defaults
        if section_data:
            self.data = section_data.copy()
            # Deep copy segments and sequences to avoid reference issues
            if 'segments' in self.data:
                self.data['segments'] = [seg.copy() for seg in self.data['segments']]
            if 'sequences' in self.data:
                self.data['sequences'] = [seq.copy() for seq in self.data['sequences']]
        else:
            self.data = {
                "name": "",
                "start_time": 0.0,
                "tempo": 1.0,
                "total_beats": 0,
                "sequences": []
            }
        
        # Check if this section has segments (different structure)
        self.has_segments = 'segments' in self.data
        
        self._create_ui()
        
        self.dialog.wait_window()
    
    def _create_ui(self):
        """Create dialog UI."""
        # Top frame for basic properties
        top_frame = tk.Frame(self.dialog, bg='#2b2b2b')
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Section name
        tk.Label(top_frame, text="Section Name:", bg='#2b2b2b', fg='white').grid(row=0, column=0, sticky='w', pady=5)
        self.name_var = tk.StringVar(value=self.data.get('name', ''))
        tk.Entry(top_frame, textvariable=self.name_var, bg='#3c3c3c', fg='white', insertbackground='white').grid(
            row=0, column=1, sticky='ew', pady=5, padx=5)
        
        # Structure type selector
        tk.Label(top_frame, text="Structure:", bg='#2b2b2b', fg='white').grid(row=1, column=0, sticky='w', pady=5)
        self.structure_var = tk.StringVar(value='segments' if self.has_segments else 'simple')
        structure_frame = tk.Frame(top_frame, bg='#2b2b2b')
        structure_frame.grid(row=1, column=1, sticky='w', pady=5)
        tk.Radiobutton(structure_frame, text="Simple (single timing)", variable=self.structure_var, value='simple',
                      bg='#2b2b2b', fg='white', selectcolor='#3c3c3c', command=self._toggle_structure).pack(side=tk.LEFT)
        tk.Radiobutton(structure_frame, text="Segments (multiple timings)", variable=self.structure_var, value='segments',
                      bg='#2b2b2b', fg='white', selectcolor='#3c3c3c', command=self._toggle_structure).pack(side=tk.LEFT, padx=10)
        
        top_frame.columnconfigure(1, weight=1)
        
        # Main content frame
        self.content_frame = tk.Frame(self.dialog, bg='#2b2b2b')
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Bottom button frame
        btn_frame = tk.Frame(self.dialog, bg='#2b2b2b')
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(btn_frame, text="Edit Sequences...", command=self._edit_sequences, 
                 bg='#2196F3', fg='white', width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="OK", command=self._ok, bg='#4CAF50', fg='white', width=10).pack(side=tk.RIGHT, padx=5)
        tk.Button(btn_frame, text="Cancel", command=self._cancel, bg='#f44336', fg='white', width=10).pack(side=tk.RIGHT, padx=5)
        
        self._update_content()
    
    def _toggle_structure(self):
        """Toggle between simple and segments structure."""
        new_structure = self.structure_var.get()
        
        if new_structure == 'segments' and 'segments' not in self.data:
            # Convert to segments structure
            if messagebox.askyesno("Convert to Segments", 
                "This will convert the section to use segments. Continue?"):
                segment = {
                    "start_time": self.data.get('start_time', 0.0),
                    "tempo": self.data.get('tempo', 1.0),
                    "total_beats": self.data.get('total_beats', 0),
                    "sequences": self.data.get('sequences', [])
                }
                self.data['segments'] = [segment]
                # Remove simple fields
                self.data.pop('start_time', None)
                self.data.pop('tempo', None)
                self.data.pop('total_beats', None)
                self.data.pop('sequences', None)
                self.has_segments = True
            else:
                self.structure_var.set('simple')
                return
        elif new_structure == 'simple' and 'segments' in self.data:
            # Convert to simple structure
            if messagebox.askyesno("Convert to Simple", 
                "This will convert the section to simple structure. Only the first segment will be kept. Continue?"):
                if self.data['segments']:
                    seg = self.data['segments'][0]
                    self.data['start_time'] = seg.get('start_time', 0.0)
                    self.data['tempo'] = seg.get('tempo', 1.0)
                    self.data['total_beats'] = seg.get('total_beats', 0)
                    self.data['sequences'] = seg.get('sequences', [])
                del self.data['segments']
                self.has_segments = False
            else:
                self.structure_var.set('segments')
                return
        
        self._update_content()
    
    def _update_content(self):
        """Update the content area based on structure type."""
        # Clear content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        if self.has_segments:
            self._create_segments_ui()
        else:
            self._create_simple_ui()
    
    def _create_simple_ui(self):
        """Create UI for simple section structure."""
        frame = tk.Frame(self.content_frame, bg='#2b2b2b')
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Start time
        tk.Label(frame, text="Start Time (s):", bg='#2b2b2b', fg='white').grid(row=0, column=0, sticky='w', pady=5)
        self.start_var = tk.DoubleVar(value=self.data.get('start_time', 0.0))
        tk.Entry(frame, textvariable=self.start_var, bg='#3c3c3c', fg='white', insertbackground='white').grid(
            row=0, column=1, sticky='ew', pady=5, padx=5)
        
        # Tempo
        tk.Label(frame, text="Tempo (s/beat):", bg='#2b2b2b', fg='white').grid(row=1, column=0, sticky='w', pady=5)
        self.tempo_var = tk.DoubleVar(value=self.data.get('tempo', 1.0))
        tk.Entry(frame, textvariable=self.tempo_var, bg='#3c3c3c', fg='white', insertbackground='white').grid(
            row=1, column=1, sticky='ew', pady=5, padx=5)
        
        # Total beats
        tk.Label(frame, text="Total Beats:", bg='#2b2b2b', fg='white').grid(row=2, column=0, sticky='w', pady=5)
        self.beats_var = tk.IntVar(value=self.data.get('total_beats', 0))
        tk.Entry(frame, textvariable=self.beats_var, bg='#3c3c3c', fg='white', insertbackground='white').grid(
            row=2, column=1, sticky='ew', pady=5, padx=5)
        
        frame.columnconfigure(1, weight=1)
    
    def _create_segments_ui(self):
        """Create UI for segments-based section structure."""
        frame = tk.Frame(self.content_frame, bg='#2b2b2b')
        frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(frame, text="Segments:", bg='#2b2b2b', fg='white', font=('Arial', 10, 'bold')).pack(anchor='w', pady=5)
        
        # Segments list
        list_frame = tk.Frame(frame, bg='#2b2b2b')
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.segments_listbox = tk.Listbox(list_frame, bg='#3c3c3c', fg='white', 
                                          selectbackground='#0078d7', yscrollcommand=scrollbar.set)
        self.segments_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.segments_listbox.yview)
        
        # Populate segments
        self._refresh_segments_list()
        
        # Select initial segment if specified
        if self.initial_segment_idx is not None and 'segments' in self.data:
            if 0 <= self.initial_segment_idx < len(self.data['segments']):
                self.segments_listbox.selection_set(self.initial_segment_idx)
                self.segments_listbox.see(self.initial_segment_idx)
        
        # Buttons
        btn_frame = tk.Frame(frame, bg='#2b2b2b')
        btn_frame.pack(fill=tk.X, pady=5)
        
        tk.Button(btn_frame, text="Add Segment", command=self._add_segment,
                 bg='#4CAF50', fg='white').pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Edit Segment", command=self._edit_segment,
                 bg='#2196F3', fg='white').pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Delete Segment", command=self._delete_segment,
                 bg='#f44336', fg='white').pack(side=tk.LEFT, padx=2)
    
    def _refresh_segments_list(self):
        """Refresh the segments listbox."""
        if not hasattr(self, 'segments_listbox'):
            return
        self.segments_listbox.delete(0, tk.END)
        if 'segments' in self.data:
            for i, seg in enumerate(self.data['segments']):
                start = seg.get('start_time', 0)
                tempo = seg.get('tempo', 1.0)
                beats = seg.get('total_beats', 0)
                self.segments_listbox.insert(tk.END, f"Segment {i+1}: {start}s, tempo={tempo}, beats={beats}")
    
    def _add_segment(self):
        """Add a new segment."""
        dialog = SegmentDialog(self.dialog, None)
        if dialog.result:
            if 'segments' not in self.data:
                self.data['segments'] = []
            self.data['segments'].append(dialog.result)
            self._refresh_segments_list()
    
    def _edit_segment(self):
        """Edit selected segment."""
        selection = self.segments_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a segment to edit.")
            return
        
        idx = selection[0]
        dialog = SegmentDialog(self.dialog, self.data['segments'][idx])
        if dialog.result:
            self.data['segments'][idx] = dialog.result
            self._refresh_segments_list()
    
    def _delete_segment(self):
        """Delete selected segment."""
        selection = self.segments_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a segment to delete.")
            return
        
        if messagebox.askyesno("Confirm", "Delete this segment?"):
            idx = selection[0]
            del self.data['segments'][idx]
            self._refresh_segments_list()
    
    def _edit_sequences(self):
        """Open sequences editor for this section."""
        if self.has_segments:
            messagebox.showinfo("Segments Structure", 
                "This section uses segments. Edit sequences within each segment using 'Edit Segment'.")
            return
        
        dialog = SequencesDialog(self.dialog, self.data.get('sequences', []), 
                                self.data.get('tempo', 1.0), self.data.get('total_beats', 0))
        if dialog.result is not None:
            self.data['sequences'] = dialog.result
    
    def _ok(self):
        """Save and close."""
        self.data['name'] = self.name_var.get()
        
        # Update timing fields for simple structure
        if not self.has_segments:
            self.data['start_time'] = self.start_var.get()
            self.data['tempo'] = self.tempo_var.get()
            self.data['total_beats'] = self.beats_var.get()
        
        self.result = self.data
        self.dialog.destroy()
    
    def _cancel(self):
        """Close without saving."""
        self.result = None
        self.dialog.destroy()


class PhraseLibraryDialog:
    """Dialog for managing phrase library."""
    
    def __init__(self, parent, phrases):
        self.result = None
        self.phrases = phrases.copy()
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Phrase Library")
        self.dialog.geometry("700x500")
        self.dialog.configure(bg='#2b2b2b')
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self._create_ui()
        
        self.dialog.wait_window()
    
    def _create_ui(self):
        """Create dialog UI."""
        frame = tk.Frame(self.dialog, bg='#2b2b2b')
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Phrase list
        list_frame = tk.Frame(frame, bg='#2b2b2b')
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        tk.Label(list_frame, text="Phrases:", bg='#2b2b2b', fg='white', font=('Arial', 10, 'bold')).pack(anchor='w')
        
        self.phrase_listbox = tk.Listbox(list_frame, bg='#3c3c3c', fg='white', selectbackground='#0078d7')
        self.phrase_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Refresh list
        self._refresh_phrase_list()
        
        # Buttons
        btn_frame = tk.Frame(list_frame, bg='#2b2b2b')
        btn_frame.pack(fill=tk.X, pady=5)
        
        tk.Button(btn_frame, text="Add Phrase", command=self._add_phrase, bg='#555', fg='white').pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        tk.Button(btn_frame, text="Edit", command=self._edit_phrase, bg='#555', fg='white').pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        tk.Button(btn_frame, text="Delete", command=self._delete_phrase, bg='#555', fg='white').pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        
        # Close button
        tk.Button(frame, text="Done", command=self._done, bg='#4CAF50', fg='white', width=15).pack(pady=10)
    
    def _refresh_phrase_list(self):
        """Refresh phrase listbox."""
        self.phrase_listbox.delete(0, tk.END)
        for phrase_id, phrase_data in sorted(self.phrases.items()):
            desc = phrase_data.get('description', f'Phrase {phrase_id}')
            note_count = len(phrase_data.get('notes', []))
            self.phrase_listbox.insert(tk.END, f"{phrase_id}: {desc} ({note_count} notes)")
    
    def _add_phrase(self):
        """Add a new phrase."""
        phrase_id = simpledialog.askstring("New Phrase", "Enter phrase ID:")
        if phrase_id:
            self.phrases[phrase_id] = {
                "description": f"Phrase {phrase_id}",
                "notes": []
            }
            self._refresh_phrase_list()
    
    def _edit_phrase(self):
        """Edit selected phrase."""
        selection = self.phrase_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a phrase to edit.")
            return
        
        # Get phrase ID from selection
        phrase_ids = sorted(self.phrases.keys())
        if selection[0] < len(phrase_ids):
            phrase_id = phrase_ids[selection[0]]
            dialog = PhraseDialog(self.dialog, phrase_id, self.phrases[phrase_id])
            if dialog.result:
                self.phrases[phrase_id] = dialog.result
                self._refresh_phrase_list()
    
    def _delete_phrase(self):
        """Delete selected phrase."""
        selection = self.phrase_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a phrase to delete.")
            return
        
        phrase_ids = sorted(self.phrases.keys())
        if selection[0] < len(phrase_ids):
            phrase_id = phrase_ids[selection[0]]
            if messagebox.askyesno("Confirm Delete", f"Delete phrase {phrase_id}?"):
                del self.phrases[phrase_id]
                self._refresh_phrase_list()
    
    def _done(self):
        """Close and save."""
        self.result = self.phrases
        self.dialog.destroy()


class PhraseDialog:
    """Dialog for editing a single phrase (notes or sequences)."""
    
    def __init__(self, parent, phrase_id, phrase_data):
        self.result = None
        self.phrase_id = phrase_id
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Edit Phrase: {phrase_id}")
        self.dialog.geometry("700x600")
        self.dialog.configure(bg='#2b2b2b')
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Deep copy phrase data
        if phrase_data:
            self.data = phrase_data.copy()
            if 'notes' in self.data:
                self.data['notes'] = [note.copy() for note in self.data['notes']]
            if 'sequences' in self.data:
                self.data['sequences'] = [seq.copy() for seq in self.data['sequences']]
        else:
            self.data = {
                "description": f"Phrase {phrase_id}",
                "notes": []
            }
        
        self._create_ui()
        
        self.dialog.wait_window()
    
    def _create_ui(self):
        """Create dialog UI."""
        frame = tk.Frame(self.dialog, bg='#2b2b2b')
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Description
        tk.Label(frame, text="Description:", bg='#2b2b2b', fg='white').pack(anchor='w', pady=5)
        self.desc_var = tk.StringVar(value=self.data.get('description', ''))
        tk.Entry(frame, textvariable=self.desc_var, bg='#3c3c3c', fg='white', insertbackground='white').pack(
            fill=tk.X, pady=5)
        
        # Notes list
        tk.Label(frame, text="Notes:", bg='#2b2b2b', fg='white', font=('Arial', 10, 'bold')).pack(anchor='w', pady=5)
        
        list_frame = tk.Frame(frame, bg='#2b2b2b')
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.notes_listbox = tk.Listbox(list_frame, bg='#3c3c3c', fg='white',
                                       selectbackground='#0078d7', yscrollcommand=scrollbar.set)
        self.notes_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.notes_listbox.yview)
        
        self._refresh_notes()
        
        # Buttons for notes
        btn_frame = tk.Frame(frame, bg='#2b2b2b')
        btn_frame.pack(fill=tk.X, pady=5)
        
        tk.Button(btn_frame, text="Add Note", command=self._add_note,
                 bg='#4CAF50', fg='white').pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Edit Note", command=self._edit_note,
                 bg='#2196F3', fg='white').pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Delete Note", command=self._delete_note,
                 bg='#f44336', fg='white').pack(side=tk.LEFT, padx=2)
        
        # Bottom buttons
        bottom_frame = tk.Frame(frame, bg='#2b2b2b')
        bottom_frame.pack(fill=tk.X, pady=10)
        
        tk.Button(bottom_frame, text="OK", command=self._ok, bg='#4CAF50', fg='white', width=10).pack(side=tk.RIGHT, padx=5)
        tk.Button(bottom_frame, text="Cancel", command=self._cancel, bg='#f44336', fg='white', width=10).pack(side=tk.RIGHT, padx=5)
    
    def _refresh_notes(self):
        """Refresh notes list."""
        self.notes_listbox.delete(0, tk.END)
        for i, note in enumerate(self.data.get('notes', [])):
            ch = note.get('channel', '?')
            delay_m = note.get('delay_multiplier', '-')
            dur_m = note.get('duration_multiplier', '-')
            self.notes_listbox.insert(tk.END, f"Note {i+1}: ch{ch}, delay_mult={delay_m}, dur_mult={dur_m}")
    
    def _add_note(self):
        """Add new note."""
        dialog = PhraseNoteDialog(self.dialog, None)
        if dialog.result:
            if 'notes' not in self.data:
                self.data['notes'] = []
            self.data['notes'].append(dialog.result)
            self._refresh_notes()
    
    def _edit_note(self):
        """Edit selected note."""
        selection = self.notes_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a note to edit.")
            return
        
        idx = selection[0]
        dialog = PhraseNoteDialog(self.dialog, self.data['notes'][idx])
        if dialog.result:
            self.data['notes'][idx] = dialog.result
            self._refresh_notes()
    
    def _delete_note(self):
        """Delete selected note."""
        selection = self.notes_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a note to delete.")
            return
        
        if messagebox.askyesno("Confirm", "Delete this note?"):
            idx = selection[0]
            del self.data['notes'][idx]
            self._refresh_notes()
    
    def _ok(self):
        """Save and close."""
        self.data['description'] = self.desc_var.get()
        self.result = self.data
        self.dialog.destroy()
    
    def _cancel(self):
        """Close without saving."""
        self.dialog.destroy()


class PhraseNoteDialog:
    """Dialog for editing a single note within a phrase.
    
    Allows editing of channel, delay_multiplier, and duration_multiplier for
    individual notes in phrase definitions. Used when clicking phrase notes
    in the timeline visualization.
    """
    
    def __init__(self, parent, note_data):
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Edit Phrase Note")
        self.dialog.geometry("400x300")
        self.dialog.configure(bg='#2b2b2b')
        self.dialog.transient(parent)
        
        # Initialize with copy of existing note data or create defaults
        if note_data:
            self.data = note_data.copy()
        else:
            self.data = {
                "channel": 0,
                "delay_multiplier": 0.0,
                "duration_multiplier": 0.5
            }
        
        self._create_ui()
        
        # CRITICAL: Grab focus after UI is created and rendered
        # update_idletasks() ensures widgets are visible before grab_set()
        self.dialog.update_idletasks()
        self.dialog.grab_set()
        
        # Block until dialog is closed
        self.dialog.wait_window()
    
    def _create_ui(self):
        """Create dialog UI with channel and timing controls."""
        frame = tk.Frame(self.dialog, bg='#2b2b2b')
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Channel selector (0-indexed, 0-9)
        tk.Label(frame, text="Channel (0-9):", bg='#2b2b2b', fg='white').grid(row=0, column=0, sticky='w', pady=5)
        self.channel_var = tk.IntVar(value=self.data.get('channel', 0))
        tk.Spinbox(frame, from_=0, to=9, textvariable=self.channel_var, width=10,
                  bg='#3c3c3c', fg='white', insertbackground='white', buttonbackground='#3c3c3c').grid(
            row=0, column=1, sticky='w', pady=5, padx=5)
        
        # Delay multiplier (start time offset from beat)
        tk.Label(frame, text="Delay Multiplier:", bg='#2b2b2b', fg='white').grid(row=1, column=0, sticky='w', pady=5)
        self.delay_mult_var = tk.DoubleVar(value=self.data.get('delay_multiplier', 0.0))
        tk.Entry(frame, textvariable=self.delay_mult_var, bg='#3c3c3c', fg='white', insertbackground='white').grid(
            row=1, column=1, sticky='ew', pady=5, padx=5)
        
        tk.Label(frame, text="(Delay = multiplier × tempo)", bg='#2b2b2b', fg='#888', font=('Arial', 8)).grid(
            row=2, column=0, columnspan=2, sticky='w', pady=2)
        
        # Duration multiplier (how long note stays on)
        tk.Label(frame, text="Duration Multiplier:", bg='#2b2b2b', fg='white').grid(row=3, column=0, sticky='w', pady=5)
        self.duration_mult_var = tk.DoubleVar(value=self.data.get('duration_multiplier', 0.5))
        tk.Entry(frame, textvariable=self.duration_mult_var, bg='#3c3c3c', fg='white', insertbackground='white').grid(
            row=3, column=1, sticky='ew', pady=5, padx=5)
        
        tk.Label(frame, text="(Duration = multiplier × tempo)", bg='#2b2b2b', fg='#888', font=('Arial', 8)).grid(
            row=4, column=0, columnspan=2, sticky='w', pady=2)
        
        frame.columnconfigure(1, weight=1)
        
        # OK/Cancel buttons
        btn_frame = tk.Frame(frame, bg='#2b2b2b')
        btn_frame.grid(row=5, column=0, columnspan=2, pady=20)
        
        tk.Button(btn_frame, text="OK", command=self._ok, bg='#4CAF50', fg='white', width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", command=self._cancel, bg='#f44336', fg='white', width=10).pack(side=tk.LEFT, padx=5)
    
    def _ok(self):
        """Save changes and close dialog."""
        self.data['channel'] = self.channel_var.get()
        self.data['delay_multiplier'] = self.delay_mult_var.get()
        self.data['duration_multiplier'] = self.duration_mult_var.get()
        
        self.result = self.data
        self.dialog.destroy()
    
    def _cancel(self):
        """Close dialog without saving changes."""
        self.dialog.destroy()


class SegmentDialog:
    """Dialog for editing segment properties within a section."""
    
    def __init__(self, parent, segment_data):
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Segment Editor")
        self.dialog.geometry("600x500")
        self.dialog.configure(bg='#2b2b2b')
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Initialize with existing data or defaults
        if segment_data:
            self.data = segment_data.copy()
            if 'sequences' in self.data:
                self.data['sequences'] = [seq.copy() for seq in self.data['sequences']]
        else:
            self.data = {
                "start_time": 0.0,
                "tempo": 1.0,
                "total_beats": 0,
                "sequences": []
            }
        
        self._create_ui()
        
        self.dialog.wait_window()
    
    def _create_ui(self):
        """Create dialog UI."""
        frame = tk.Frame(self.dialog, bg='#2b2b2b')
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Start time
        tk.Label(frame, text="Start Time (s):", bg='#2b2b2b', fg='white').grid(row=0, column=0, sticky='w', pady=5)
        self.start_var = tk.DoubleVar(value=self.data.get('start_time', 0.0))
        tk.Entry(frame, textvariable=self.start_var, bg='#3c3c3c', fg='white', insertbackground='white').grid(
            row=0, column=1, sticky='ew', pady=5, padx=5)
        
        # Tempo
        tk.Label(frame, text="Tempo (s/beat):", bg='#2b2b2b', fg='white').grid(row=1, column=0, sticky='w', pady=5)
        self.tempo_var = tk.DoubleVar(value=self.data.get('tempo', 1.0))
        tk.Entry(frame, textvariable=self.tempo_var, bg='#3c3c3c', fg='white', insertbackground='white').grid(
            row=1, column=1, sticky='ew', pady=5, padx=5)
        
        # Total beats
        tk.Label(frame, text="Total Beats:", bg='#2b2b2b', fg='white').grid(row=2, column=0, sticky='w', pady=5)
        self.beats_var = tk.IntVar(value=self.data.get('total_beats', 0))
        tk.Entry(frame, textvariable=self.beats_var, bg='#3c3c3c', fg='white', insertbackground='white').grid(
            row=2, column=1, sticky='ew', pady=5, padx=5)
        
        # Buttons
        btn_frame = tk.Frame(frame, bg='#2b2b2b')
        btn_frame.grid(row=3, column=0, columnspan=2, pady=20)
        
        tk.Button(btn_frame, text="Edit Sequences...", command=self._edit_sequences,
                 bg='#2196F3', fg='white', width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="OK", command=self._ok, bg='#4CAF50', fg='white', width=10).pack(side=tk.RIGHT, padx=5)
        tk.Button(btn_frame, text="Cancel", command=self._cancel, bg='#f44336', fg='white', width=10).pack(side=tk.RIGHT, padx=5)
        
        frame.columnconfigure(1, weight=1)
    
    def _edit_sequences(self):
        """Open sequences editor."""
        dialog = SequencesDialog(self.dialog, self.data.get('sequences', []),
                                self.data.get('tempo', 1.0), self.data.get('total_beats', 0))
        if dialog.result is not None:
            self.data['sequences'] = dialog.result
    
    def _ok(self):
        """Save and close."""
        self.data['start_time'] = self.start_var.get()
        self.data['tempo'] = self.tempo_var.get()
        self.data['total_beats'] = self.beats_var.get()
        
        self.result = self.data
        self.dialog.destroy()
    
    def _cancel(self):
        """Close without saving."""
        self.result = None
        self.dialog.destroy()


class SequencesDialog:
    """Dialog for managing sequences within a section/segment."""
    
    def __init__(self, parent, sequences, tempo, total_beats):
        self.result = None
        self.sequences = [seq.copy() for seq in sequences] if sequences else []
        self.tempo = tempo
        self.total_beats = total_beats
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Sequences Editor")
        self.dialog.geometry("900x600")
        self.dialog.configure(bg='#2b2b2b')
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self._create_ui()
        
        self.dialog.wait_window()
    
    def _create_ui(self):
        """Create dialog UI."""
        frame = tk.Frame(self.dialog, bg='#2b2b2b')
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        tk.Label(frame, text="Sequences:", bg='#2b2b2b', fg='white', font=('Arial', 10, 'bold')).pack(anchor='w', pady=5)
        
        # Sequences list
        list_frame = tk.Frame(frame, bg='#2b2b2b')
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.sequences_listbox = tk.Listbox(list_frame, bg='#3c3c3c', fg='white',
                                           selectbackground='#0078d7', yscrollcommand=scrollbar.set)
        self.sequences_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.sequences_listbox.yview)
        
        self._refresh_list()
        
        # Buttons
        btn_frame = tk.Frame(frame, bg='#2b2b2b')
        btn_frame.pack(fill=tk.X, pady=5)
        
        tk.Button(btn_frame, text="Add Sequence", command=self._add_sequence,
                 bg='#4CAF50', fg='white').pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Edit Sequence", command=self._edit_sequence,
                 bg='#2196F3', fg='white').pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Delete Sequence", command=self._delete_sequence,
                 bg='#f44336', fg='white').pack(side=tk.LEFT, padx=2)
        
        # Bottom buttons
        bottom_frame = tk.Frame(frame, bg='#2b2b2b')
        bottom_frame.pack(fill=tk.X, pady=10)
        
        tk.Button(bottom_frame, text="OK", command=self._ok, bg='#4CAF50', fg='white', width=10).pack(side=tk.RIGHT, padx=5)
        tk.Button(bottom_frame, text="Cancel", command=self._cancel, bg='#f44336', fg='white', width=10).pack(side=tk.RIGHT, padx=5)
    
    def _refresh_list(self):
        """Refresh the sequences listbox."""
        self.sequences_listbox.delete(0, tk.END)
        for i, seq in enumerate(self.sequences):
            # Format display
            if 'beat' in seq:
                beats_str = f"beat {seq['beat']}"
            elif 'beats' in seq:
                beats_str = f"beats {seq['beats']}"
            elif 'all_beats' in seq and seq['all_beats']:
                beats_str = "all beats"
            else:
                beats_str = "no beats specified"
            
            actions_count = len(seq.get('actions', []))
            self.sequences_listbox.insert(tk.END, f"Seq {i+1}: {beats_str}, {actions_count} action(s)")
    
    def _add_sequence(self):
        """Add new sequence."""
        dialog = SequenceDialog(self.dialog, None, self.tempo, self.total_beats)
        if dialog.result:
            self.sequences.append(dialog.result)
            self._refresh_list()
    
    def _edit_sequence(self):
        """Edit selected sequence."""
        selection = self.sequences_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a sequence to edit.")
            return
        
        idx = selection[0]
        dialog = SequenceDialog(self.dialog, self.sequences[idx], self.tempo, self.total_beats)
        if dialog.result:
            self.sequences[idx] = dialog.result
            self._refresh_list()
    
    def _delete_sequence(self):
        """Delete selected sequence."""
        selection = self.sequences_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a sequence to delete.")
            return
        
        if messagebox.askyesno("Confirm", "Delete this sequence?"):
            idx = selection[0]
            del self.sequences[idx]
            self._refresh_list()
    
    def _ok(self):
        """Save and close."""
        self.result = self.sequences
        self.dialog.destroy()
    
    def _cancel(self):
        """Close without saving."""
        self.dialog.destroy()


class SequenceDialog:
    """Dialog for editing a single sequence and its actions.
    
    A sequence defines which beat(s) to execute actions on. Can specify:
    - Single beat (beat: 1)
    - Multiple beats (beats: [1, 3, 5])
    - All beats (all_beats: true)
    
    Contains list of actions to execute on those beats.
    """
    
    def __init__(self, parent, sequence_data, tempo, total_beats, initial_action_idx=None):
        self.result = None
        self.tempo = tempo
        self.total_beats = total_beats
        self.initial_action_idx = initial_action_idx  # For auto-selecting action when opened from click
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Sequence Editor")
        self.dialog.geometry("700x600")
        self.dialog.configure(bg='#2b2b2b')
        self.dialog.transient(parent)
        
        # Initialize with copy of existing data or create defaults
        if sequence_data:
            self.data = sequence_data.copy()
            # Deep copy actions list to avoid modifying original
            if 'actions' in self.data:
                self.data['actions'] = [act.copy() for act in self.data['actions']]
        else:
            self.data = {
                "beat": 1,
                "actions": []
            }
        
        self._create_ui()
        
        # CRITICAL: Grab focus after UI is created and rendered
        # update_idletasks() ensures widgets are visible before grab_set()
        self.dialog.update_idletasks()
        self.dialog.grab_set()
        
        # Block until dialog is closed
        self.dialog.wait_window()
    
    def _create_ui(self):
        """Create dialog UI with beat specification and actions list."""
        frame = tk.Frame(self.dialog, bg='#2b2b2b')
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Beat specification radio buttons
        beat_frame = tk.LabelFrame(frame, text="Beat Specification", bg='#2b2b2b', fg='white')
        beat_frame.pack(fill=tk.X, pady=5)
        
        self.beat_type_var = tk.StringVar(value=self._get_beat_type())
        
        # Option 1: Single beat
        tk.Radiobutton(beat_frame, text="Single beat:", variable=self.beat_type_var, value='beat',
                      bg='#2b2b2b', fg='white', selectcolor='#3c3c3c', command=self._update_beat_fields).grid(
            row=0, column=0, sticky='w', padx=5, pady=2)
        self.single_beat_var = tk.IntVar(value=self.data.get('beat', 1))
        self.single_beat_entry = tk.Entry(beat_frame, textvariable=self.single_beat_var, width=10,
                                         bg='#3c3c3c', fg='white', insertbackground='white')
        self.single_beat_entry.grid(row=0, column=1, sticky='w', padx=5, pady=2)
        
        # Option 2: Multiple beats (comma-separated)
        tk.Radiobutton(beat_frame, text="Multiple beats (comma-separated):", variable=self.beat_type_var, value='beats',
                      bg='#2b2b2b', fg='white', selectcolor='#3c3c3c', command=self._update_beat_fields).grid(
            row=1, column=0, sticky='w', padx=5, pady=2)
        beats_str = ','.join(map(str, self.data.get('beats', []))) if 'beats' in self.data else ""
        self.multi_beats_var = tk.StringVar(value=beats_str)
        self.multi_beats_entry = tk.Entry(beat_frame, textvariable=self.multi_beats_var, width=40,
                                         bg='#3c3c3c', fg='white', insertbackground='white')
        self.multi_beats_entry.grid(row=1, column=1, sticky='ew', padx=5, pady=2)
        
        # Option 3: All beats in section
        tk.Radiobutton(beat_frame, text="All beats", variable=self.beat_type_var, value='all_beats',
                      bg='#2b2b2b', fg='white', selectcolor='#3c3c3c', command=self._update_beat_fields).grid(
            row=2, column=0, sticky='w', padx=5, pady=2)
        
        beat_frame.columnconfigure(1, weight=1)
        self._update_beat_fields()  # Enable/disable fields based on selection
        
        # Actions list
        actions_frame = tk.LabelFrame(frame, text="Actions", bg='#2b2b2b', fg='white')
        actions_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        list_container = tk.Frame(actions_frame, bg='#2b2b2b')
        list_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = tk.Scrollbar(list_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.actions_listbox = tk.Listbox(list_container, bg='#3c3c3c', fg='white',
                                         selectbackground='#0078d7', yscrollcommand=scrollbar.set)
        self.actions_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.actions_listbox.yview)
        
        self._refresh_actions()
        
        # Auto-select initial action if specified (from click handling)
        if self.initial_action_idx is not None and 0 <= self.initial_action_idx < len(self.data.get('actions', [])):
            self.actions_listbox.selection_set(self.initial_action_idx)
            self.actions_listbox.see(self.initial_action_idx)
        
        # Action buttons
        action_btn_frame = tk.Frame(actions_frame, bg='#2b2b2b')
        action_btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Button(action_btn_frame, text="Add Action", command=self._add_action,
                 bg='#4CAF50', fg='white').pack(side=tk.LEFT, padx=2)
        tk.Button(action_btn_frame, text="Edit Action", command=self._edit_action,
                 bg='#2196F3', fg='white').pack(side=tk.LEFT, padx=2)
        tk.Button(action_btn_frame, text="Delete Action", command=self._delete_action,
                 bg='#f44336', fg='white').pack(side=tk.LEFT, padx=2)
        
        # Bottom buttons
        bottom_frame = tk.Frame(frame, bg='#2b2b2b')
        bottom_frame.pack(fill=tk.X, pady=10)
        
        tk.Button(bottom_frame, text="OK", command=self._ok, bg='#4CAF50', fg='white', width=10).pack(side=tk.RIGHT, padx=5)
        tk.Button(bottom_frame, text="Cancel", command=self._cancel, bg='#f44336', fg='white', width=10).pack(side=tk.RIGHT, padx=5)
    
    def _get_beat_type(self):
        """Determine the beat type from data."""
        if 'all_beats' in self.data and self.data['all_beats']:
            return 'all_beats'
        elif 'beats' in self.data:
            return 'beats'
        else:
            return 'beat'
    
    def _update_beat_fields(self):
        """Enable/disable beat fields based on selection."""
        beat_type = self.beat_type_var.get()
        
        self.single_beat_entry.config(state='normal' if beat_type == 'beat' else 'disabled')
        self.multi_beats_entry.config(state='normal' if beat_type == 'beats' else 'disabled')
    
    def _refresh_actions(self):
        """Refresh actions list."""
        self.actions_listbox.delete(0, tk.END)
        for i, action in enumerate(self.data.get('actions', [])):
            action_type = action.get('type', 'unknown')
            if action_type == 'note':
                ch = action.get('channel', '?')
                desc = f"Note: ch{ch}, delay={action.get('delay', 0)}, dur={action.get('duration', 0)}"
            elif action_type == 'phrase':
                ph_id = action.get('id', '?')
                desc = f"Phrase: id={ph_id}"
                if 'description' in action:
                    desc += f" ({action['description']})"
            elif action_type == 'all_channels':
                desc = f"All Channels: dur={action.get('duration', 0)}"
            elif action_type in ['step_up', 'step_down']:
                desc = action_type.replace('_', ' ').title()
            elif action_type == 'flash_mode':
                desc = f"Flash Mode: {action.get('mode', 0)}"
            else:
                desc = f"{action_type}"
            
            self.actions_listbox.insert(tk.END, f"{i+1}. {desc}")
    
    def _add_action(self):
        """Add new action."""
        dialog = ActionDialog(self.dialog, None, self.tempo)
        if dialog.result:
            if 'actions' not in self.data:
                self.data['actions'] = []
            self.data['actions'].append(dialog.result)
            self._refresh_actions()
    
    def _edit_action(self):
        """Edit selected action."""
        selection = self.actions_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an action to edit.")
            return
        
        idx = selection[0]
        dialog = ActionDialog(self.dialog, self.data['actions'][idx], self.tempo)
        if dialog.result:
            self.data['actions'][idx] = dialog.result
            self._refresh_actions()
    
    def _delete_action(self):
        """Delete selected action."""
        selection = self.actions_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an action to delete.")
            return
        
        if messagebox.askyesno("Confirm", "Delete this action?"):
            idx = selection[0]
            del self.data['actions'][idx]
            self._refresh_actions()
    
    def _ok(self):
        """Save and close."""
        # Clear old beat fields
        self.data.pop('beat', None)
        self.data.pop('beats', None)
        self.data.pop('all_beats', None)
        
        # Set appropriate beat field
        beat_type = self.beat_type_var.get()
        if beat_type == 'beat':
            self.data['beat'] = self.single_beat_var.get()
        elif beat_type == 'beats':
            beats_str = self.multi_beats_var.get().strip()
            if beats_str:
                try:
                    self.data['beats'] = [int(b.strip()) for b in beats_str.split(',')]
                except ValueError:
                    messagebox.showerror("Invalid Input", "Beats must be comma-separated integers.")
                    return
        elif beat_type == 'all_beats':
            self.data['all_beats'] = True
        
        self.result = self.data
        self.dialog.destroy()
    
    def _cancel(self):
        """Close without saving."""
        self.dialog.destroy()


class ActionDialog:
    """Dialog for editing a single action."""
    
    def __init__(self, parent, action_data, tempo):
        self.result = None
        self.tempo = tempo
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Action Editor")
        self.dialog.geometry("500x450")
        self.dialog.configure(bg='#2b2b2b')
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Initialize with existing data or defaults
        if action_data:
            self.data = action_data.copy()
        else:
            self.data = {
                "type": "note",
                "channel": 0,
                "delay": 0.0,
                "duration": 0.5
            }
        
        self._create_ui()
        
        self.dialog.wait_window()
    
    def _create_ui(self):
        """Create dialog UI."""
        frame = tk.Frame(self.dialog, bg='#2b2b2b')
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Action type
        tk.Label(frame, text="Action Type:", bg='#2b2b2b', fg='white').grid(row=0, column=0, sticky='w', pady=5)
        self.action_type_var = tk.StringVar(value=self.data.get('type', 'note'))
        type_combo = ttk.Combobox(frame, textvariable=self.action_type_var,
                                 values=['note', 'phrase', 'all_channels', 'step_up', 'step_down', 'flash_mode'],
                                 state='readonly')
        type_combo.grid(row=0, column=1, sticky='ew', pady=5, padx=5)
        type_combo.bind('<<ComboboxSelected>>', lambda e: self._update_fields())
        
        # Container for type-specific fields
        self.fields_frame = tk.Frame(frame, bg='#2b2b2b')
        self.fields_frame.grid(row=1, column=0, columnspan=2, sticky='ew', pady=10)
        
        frame.columnconfigure(1, weight=1)
        
        self._update_fields()
        
        # Buttons
        btn_frame = tk.Frame(frame, bg='#2b2b2b')
        btn_frame.grid(row=2, column=0, columnspan=2, pady=20)
        
        tk.Button(btn_frame, text="OK", command=self._ok, bg='#4CAF50', fg='white', width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", command=self._cancel, bg='#f44336', fg='white', width=10).pack(side=tk.LEFT, padx=5)
    
    def _update_fields(self):
        """Update fields based on action type."""
        # Clear existing fields
        for widget in self.fields_frame.winfo_children():
            widget.destroy()
        
        action_type = self.action_type_var.get()
        
        if action_type == 'note':
            self._create_note_fields()
        elif action_type == 'phrase':
            self._create_phrase_fields()
        elif action_type == 'all_channels':
            self._create_all_channels_fields()
        elif action_type == 'flash_mode':
            self._create_flash_mode_fields()
        # step_up and step_down have no additional fields
    
    def _create_note_fields(self):
        """Create fields for note action."""
        tk.Label(self.fields_frame, text="Channel (0-9):", bg='#2b2b2b', fg='white').grid(row=0, column=0, sticky='w', pady=5)
        self.channel_var = tk.IntVar(value=self.data.get('channel', 0))
        tk.Spinbox(self.fields_frame, from_=0, to=9, textvariable=self.channel_var, width=10,
                  bg='#3c3c3c', fg='white', insertbackground='white', buttonbackground='#3c3c3c').grid(
            row=0, column=1, sticky='w', pady=5, padx=5)
        
        tk.Label(self.fields_frame, text="Delay (seconds):", bg='#2b2b2b', fg='white').grid(row=1, column=0, sticky='w', pady=5)
        self.delay_var = tk.DoubleVar(value=self.data.get('delay', 0.0))
        tk.Entry(self.fields_frame, textvariable=self.delay_var, bg='#3c3c3c', fg='white', insertbackground='white').grid(
            row=1, column=1, sticky='ew', pady=5, padx=5)
        
        tk.Label(self.fields_frame, text="Duration (seconds):", bg='#2b2b2b', fg='white').grid(row=2, column=0, sticky='w', pady=5)
        self.duration_var = tk.DoubleVar(value=self.data.get('duration', 0.5))
        tk.Entry(self.fields_frame, textvariable=self.duration_var, bg='#3c3c3c', fg='white', insertbackground='white').grid(
            row=2, column=1, sticky='ew', pady=5, padx=5)
        
        # Optional: delay_multiplier and duration_multiplier
        tk.Label(self.fields_frame, text="OR use multipliers (relative to tempo):", bg='#2b2b2b', fg='#ff9800').grid(
            row=3, column=0, columnspan=2, sticky='w', pady=10)
        
        tk.Label(self.fields_frame, text="Delay Multiplier:", bg='#2b2b2b', fg='white').grid(row=4, column=0, sticky='w', pady=5)
        self.delay_mult_var = tk.DoubleVar(value=self.data.get('delay_multiplier', 0.0))
        tk.Entry(self.fields_frame, textvariable=self.delay_mult_var, bg='#3c3c3c', fg='white', insertbackground='white').grid(
            row=4, column=1, sticky='ew', pady=5, padx=5)
        
        tk.Label(self.fields_frame, text="Duration Multiplier:", bg='#2b2b2b', fg='white').grid(row=5, column=0, sticky='w', pady=5)
        self.duration_mult_var = tk.DoubleVar(value=self.data.get('duration_multiplier', 0.0))
        tk.Entry(self.fields_frame, textvariable=self.duration_mult_var, bg='#3c3c3c', fg='white', insertbackground='white').grid(
            row=5, column=1, sticky='ew', pady=5, padx=5)
        
        self.fields_frame.columnconfigure(1, weight=1)
    
    def _create_phrase_fields(self):
        """Create fields for phrase action."""
        tk.Label(self.fields_frame, text="Phrase ID:", bg='#2b2b2b', fg='white').grid(row=0, column=0, sticky='w', pady=5)
        self.phrase_id_var = tk.StringVar(value=self.data.get('id', '0'))
        tk.Entry(self.fields_frame, textvariable=self.phrase_id_var, bg='#3c3c3c', fg='white', insertbackground='white').grid(
            row=0, column=1, sticky='ew', pady=5, padx=5)
        
        tk.Label(self.fields_frame, text="Description (optional):", bg='#2b2b2b', fg='white').grid(row=1, column=0, sticky='w', pady=5)
        self.phrase_desc_var = tk.StringVar(value=self.data.get('description', ''))
        tk.Entry(self.fields_frame, textvariable=self.phrase_desc_var, bg='#3c3c3c', fg='white', insertbackground='white').grid(
            row=1, column=1, sticky='ew', pady=5, padx=5)
        
        self.fields_frame.columnconfigure(1, weight=1)
    
    def _create_all_channels_fields(self):
        """Create fields for all_channels action."""
        tk.Label(self.fields_frame, text="Duration (seconds):", bg='#2b2b2b', fg='white').grid(row=0, column=0, sticky='w', pady=5)
        self.duration_var = tk.DoubleVar(value=self.data.get('duration', 0.25))
        tk.Entry(self.fields_frame, textvariable=self.duration_var, bg='#3c3c3c', fg='white', insertbackground='white').grid(
            row=0, column=1, sticky='ew', pady=5, padx=5)
        
        tk.Label(self.fields_frame, text="Duration Multiplier (optional):", bg='#2b2b2b', fg='white').grid(row=1, column=0, sticky='w', pady=5)
        self.duration_mult_var = tk.DoubleVar(value=self.data.get('duration_multiplier', 0.0))
        tk.Entry(self.fields_frame, textvariable=self.duration_mult_var, bg='#3c3c3c', fg='white', insertbackground='white').grid(
            row=1, column=1, sticky='ew', pady=5, padx=5)
        
        self.fields_frame.columnconfigure(1, weight=1)
    
    def _create_flash_mode_fields(self):
        """Create fields for flash_mode action."""
        tk.Label(self.fields_frame, text="Mode (-1 to disable, or mode number):", bg='#2b2b2b', fg='white').grid(
            row=0, column=0, sticky='w', pady=5)
        self.mode_var = tk.IntVar(value=self.data.get('mode', 0))
        tk.Entry(self.fields_frame, textvariable=self.mode_var, bg='#3c3c3c', fg='white', insertbackground='white').grid(
            row=0, column=1, sticky='ew', pady=5, padx=5)
        
        self.fields_frame.columnconfigure(1, weight=1)
    
    def _ok(self):
        """Save and close."""
        action_type = self.action_type_var.get()
        self.data = {"type": action_type}
        
        if action_type == 'note':
            self.data['channel'] = self.channel_var.get()
            # Use multipliers if set, otherwise use absolute values
            delay_mult = self.delay_mult_var.get()
            duration_mult = self.duration_mult_var.get()
            if delay_mult > 0:
                self.data['delay_multiplier'] = delay_mult
            else:
                self.data['delay'] = self.delay_var.get()
            if duration_mult > 0:
                self.data['duration_multiplier'] = duration_mult
            else:
                self.data['duration'] = self.duration_var.get()
        
        elif action_type == 'phrase':
            phrase_id = self.phrase_id_var.get()
            # Try to convert to int if possible
            try:
                self.data['id'] = int(phrase_id)
            except ValueError:
                self.data['id'] = phrase_id
            desc = self.phrase_desc_var.get().strip()
            if desc:
                self.data['description'] = desc
        
        elif action_type == 'all_channels':
            duration_mult = self.duration_mult_var.get()
            if duration_mult > 0:
                self.data['duration_multiplier'] = duration_mult
            else:
                self.data['duration'] = self.duration_var.get()
        
        elif action_type == 'flash_mode':
            self.data['mode'] = self.mode_var.get()
        
        # step_up and step_down only have type
        
        self.result = self.data
        self.dialog.destroy()
    
    def _cancel(self):
        """Close without saving."""
        self.dialog.destroy()


if __name__ == '__main__':
    editor = SongEditor()
    editor.run()

