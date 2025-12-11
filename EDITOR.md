# Song Editor for Pi Lightshow

A visual GUI editor for creating and editing lightshow choreography files for the Pi Lightshow system.

## Features

### Visual Timeline Editor
- **Vertical scrolling timeline** - Similar to rhythm games like Guitar Hero, with audio visualization moving upward as it plays
- **Waveform visualization** - See your audio waveform for visual reference when placing lights
- **10-channel columns** - One column for each light channel, matching the physical layout
- **Beat-synchronized editing** - Place lights on specific beats with visual beat markers

### Comprehensive Editing Tools

#### File Management
- **Open MP3** - Load an MP3 file and create/edit its song data
- **Open JSON** - Load an existing JSON file (finds its referenced MP3)
- **Save / Save As** - Save your work with flexible file naming
- **Close Song** - Return to welcome screen to load a different song

#### Metadata Panel
- Edit song title, artist, and description
- Automatic JSON file association with MP3 files
- Load existing songs or create new ones

#### Section Management
- Create multiple sections (prelude, main, finale, etc.)
- **Two structure types:**
  - **Simple sections** - Single timing (start_time, tempo, total_beats)
  - **Segmented sections** - Multiple segments with different timings (for tempo changes)
- Convert between simple and segmented structures
- Edit section properties and manage sequences
- Visual section boundaries on timeline

#### Segment Management (for Multi-Tempo Sections)
- Add multiple segments within a section
- Each segment has its own start_time, tempo, and total_beats
- Ideal for songs with tempo changes or time signature shifts

#### Sequence Editor
- Define when actions occur:
  - **Single beat** - Execute on one specific beat
  - **Multiple beats** - Comma-separated list of beats (e.g., 1,5,9,13)
  - **All beats** - Execute on every beat in the section/segment
- Add multiple actions per sequence
- Full CRUD operations (Create, Read, Update, Delete)

#### Action Editor
- **Six action types supported:**
  - **note** - Single channel activation with timing
  - **phrase** - Reference to reusable note pattern
  - **all_channels** - Flash all 10 channels simultaneously
  - **step_up** - Sequential activation moving up channels
  - **step_down** - Sequential activation moving down channels
  - **flash_mode** - Change flash mode during playback
- Flexible timing options:
  - Absolute values (seconds)
  - Multipliers (relative to tempo)
- Channel selection (0-9)
- Duration and delay control

#### Phrase Library
- Create reusable note patterns (phrases)
- Edit phrase descriptions
- **Phrase Notes Editor:**
  - Add/edit/delete notes within phrases
  - Set channel for each note
  - Define delay_multiplier (when note starts relative to tempo)
  - Define duration_multiplier (how long note lasts relative to tempo)
- Reference phrases by ID across multiple sections
- Support for both `notes` (legacy) and `sequences` formats

#### Channel Tools
- **Select Tool (S)** - Click and drag to select/move items
- **Hand Tool (H)** - Pan through the timeline
- **Beat Marker Tool (B)** - Add beat markers at specific times
- **Channel Note Tool (N)** - Add channel activations (notes)

#### Playback Controls
- **Play/Pause button** - Start/pause audio with synchronized visualization (Space key)
- **Rewind button** - Jump to beginning (keeps playing if was playing)
- **Playback position indicator** - Green line shows current position (always visible)
- **Position display** - Live "Position: M:SS.S" indicator in top-right corner (green text)
- **Click-to-seek** - Click anywhere on waveform visualizer to jump to that position
- **Seek preview** - Hover over waveform to see yellow preview line and timestamp
- **Auto-follow** - View automatically scrolls to follow playback position (70% threshold)
- **Beat-accurate timing** - Position synced with actual audio playback using dual-loop system (60fps interpolation)
- **End-of-song handling** - Automatically stops and rewinds when song finishes

### Interactive Editing Features

#### Click-to-Edit
- **Left-click on action rectangles** - Opens Sequence Editor with that action's sequence pre-selected
- **Left-click on phrase notes** - Opens dialog to edit individual note within phrase (channel, delay, duration)
- **Left-click on waveform** - Seeks to that time position
- **Drag waveform splitter** - Resize waveform column width (50-400 pixels)

#### Right-Click Context Menus
- **Right-click on any action** - Opens hierarchical context menu with options:
  - Edit Action - Opens dialog for the specific action
  - Edit Sequence - Opens Sequence Editor with all actions for that beat pattern
  - Edit Segment - Opens Segment Editor (if action is in a segmented section)
  - Edit Section - Opens Section Editor for the containing section
- **Auto-selects segment** - When editing section via context menu, automatically selects the relevant segment
- **Auto-dismisses** - Menu closes automatically on next click

#### Waveform Controls  
- **Scroll wheel over waveform** - Zoom amplitude (100% to 1000%) for better visibility of quiet sections
- **Amplitude indicator** - "Amp: 100%" display shows current waveform zoom level
- **Drag splitter** - Resize waveform column dynamically

#### Visual Enhancements
- **Enhanced phrase visualization** - Individual notes shown as rectangles in correct channels with proper timing
- **Step up/down visualization** - Detailed sequential channel activation patterns with timing
- **Phrase note alignment** - Notes positioned exactly at their playback time on timeline
- **Transparency simulation** - Phrase backgrounds use stipple pattern for pseudo-transparency (50%)
- **Interactive tooltips** - Hover over actions to see detailed information

### Smart Features
- Automatic JSON file detection when loading MP3
- **Open JSON directly** - Load JSON files that reference different MP3 names
- **Format preservation** - Maintains both simple and segmented section structures
- **Structure conversion** - Convert between simple and segmented sections
- **Color-coded timeline** - Visual representation of all action types:
  - Green bars: Individual channel notes
  - Purple bars: Phrases (hover to see details)
  - Orange bars: All channels flash
  - Blue bars: Step up patterns
  - Cyan bars: Step down patterns
  - Yellow/red bars: Flash mode changes
  - Red lines: Section boundaries
  - Yellow dashed lines: Beat markers
- **Interactive tooltips** - Hover over actions to see details
- **Legend bar** - Color reference at top of timeline
- Zoom in/out for precise editing
- Keyboard shortcuts (Ctrl+S to save, Space to play/pause, Delete to remove)
- Real-time preview of channel layout matching simulator
- **Deep editing** - Full hierarchical editing capability: access any level (Section → Segment → Sequence → Action) from any entry point, with automatic context selection
- **Validation** - Comprehensive JSON validation on load
- **Built-in help** - Help → Quick Start for tips and documentation

## Installation

### Prerequisites
The editor requires Python 3 and several dependencies that are NOT needed on the Raspberry Pi. This is intentional - the editor is designed to run on your development PC (Linux Mint, Ubuntu, etc.), not on the Raspberry Pi.

### Setup on Development PC

1. **Install system dependencies:**
   ```bash
   sudo apt-get install python3-tk ffmpeg
   ```

2. **Run the setup script:**
   ```bash
   ./setup-editor.sh
   ```

   This will install the required Python packages:
   - pygame (audio playback)
   - pydub (audio processing)
   - numpy (waveform processing)

### Manual Installation
If you prefer to install dependencies manually:
```bash
pip3 install -r requirements-editor.txt
```

## Usage

### Starting the Editor
```bash
python3 song_editor.py
```

### Quick Workflow Overview

1. **Load Audio** - File → Open MP3... or Open JSON...
2. **Set Metadata** - Fill in Title, Artist, Description
3. **Create Sections** - Define timing structure (simple or segmented)
4. **Add Sequences** - Specify which beats trigger actions
5. **Add Actions** - Define what happens (notes, phrases, effects)
6. **Create Phrases** (Optional) - Build reusable patterns
7. **Save** - Ctrl+S to save JSON file

For a detailed walkthrough, see the "Tutorial: Creating Your First Lightshow" section below.

### Using the Visual Timeline

The timeline provides a rich visual representation of your choreography with extensive interactivity:

1. **Understanding the display:**
   - Each vertical column represents one of the 10 channels
   - Time flows downward (like Guitar Hero)
   - Green line shows current playback position (60fps smooth updates)
   - Actions appear as colored bars at their timing positions
   - Position indicator (top-right) shows current time in M:SS.S format

2. **Navigating:**
   - **Click waveform** (right side) to seek to any position instantly
   - **Hover over waveform** to preview position with yellow line and timestamp tooltip
   - **View auto-scrolls** during playback (starts scrolling at 70% down visible area)
   - **Scroll wheel** zooms waveform amplitude when over waveform area
   - **Scroll wheel** over timeline scrolls vertically (normal scroll behavior)
   - **Zoom controls** (+/-) adjust timeline vertical scale for precision

3. **Interactive editing:**
   - **Left-click actions** - Opens Sequence Editor for that action's sequence
   - **Left-click phrase notes** - Directly edit individual notes in phrases
   - **Right-click actions** - Context menu with hierarchical editing options:
     * Edit Action (single action)
     * Edit Sequence (all actions at those beats)
     * Edit Segment (all sequences in segment, if applicable)
     * Edit Section (entire timing section)
   - **Context menu auto-selects** - Automatically selects the relevant segment when editing

4. **Visual elements:**
   - **Green bars**: Individual channel notes in their column (clickable)
   - **Purple backgrounds**: Phrases spanning channels with semi-transparent effect
     * Individual phrase notes shown as light purple rectangles
     * Click individual notes to edit them directly
   - **Orange bars**: All channels activations
   - **Blue bars**: Step up patterns (shows sequential activation with timing)
   - **Cyan bars**: Step down patterns (shows increasing durations)
   - **Yellow bars**: Flash mode changes
   - **Red lines**: Section boundaries with section names
   - **Yellow dashed lines**: Beat markers with beat numbers

5. **Color legend:**
   - **Top bar** shows color key for all action types
   - **Position indicator** (green) displays current playback time
   - **Amp indicator** shows current waveform zoom level (100-1000%)

### Editing Existing Songs

1. **Load the song:**
   - **Option A**: File → Open MP3... (will prompt to load matching JSON)
   - **Option B**: File → Open JSON... (will load referenced MP3)

2. **Edit Section Properties:**
   - Select a section from the list
   - Click "Edit Section"
   - Modify name, timing, or structure type
   - **For segmented sections**: Use "Edit Segment" to modify individual timing blocks
   - Click "Edit Sequences..." to manage sequence data

3. **Edit Sequences:**
   - Select section, click "Edit Sequences..."
   - Select a sequence, click "Edit Sequence"
   - Modify beat specification or actions
   - Add/delete actions as needed

4. **Edit Phrases:**
   - Edit → Manage Phrases...
   - Select a phrase and click "Edit"
   - Modify description or notes
   - Add/edit/delete notes within the phrase

5. **Save Changes:**
   - File → Save (Ctrl+S) - Overwrites original file
   - File → Save As... - Creates a new JSON file
   - Note: "Save As" changes the save location but preserves the original mp3_file reference

**Important**: The editor preserves structures it doesn't modify. If a section uses segments, the segment data is fully preserved even if you only edit the section name.

### Keyboard Shortcuts

- **Ctrl+S** - Save song
- **Space** - Play/Pause audio
- **Delete** - Delete selected items
- **S** - Select tool
- **H** - Hand (pan) tool
- **B** - Beat marker tool
- **N** - Channel note tool

### Getting Help

- **Help → Quick Start** - Comprehensive quick start guide with workflow, shortcuts, and tips
- **Help → About** - Version and feature information
- **EDITOR.md** - Complete documentation (this file)
- **Example files** - songs/carol.json and songs/madrussian.json for reference

## Tutorial: Creating Your First Lightshow

This tutorial will walk you through creating a simple lightshow from scratch, demonstrating the core features of the editor.

### Prerequisites

Before starting, make sure you have:
1. Installed the editor dependencies: `./setup-editor.sh`
2. An MP3 file in the `songs/` folder

### Step 1: Launch the Editor

```bash
python3 song_editor.py
```

### Step 2: Load Your MP3 File

1. Click **File → Open MP3...**
2. Navigate to the `songs/` folder
3. Select your MP3 file
4. If a JSON file exists with the same name, you'll be asked if you want to load it
   - Click **No** for this tutorial (we're creating from scratch)

### Step 3: Fill in Metadata

In the left panel:
1. **Title**: Enter your song title
2. **Artist**: Enter the artist name
3. **Description**: Enter a brief description like "Simple beat pattern lightshow"

### Step 4: Create Your First Section

1. In the **Sections & Timing** panel, click **Add Section**
2. Fill in the dialog:
   - **Section Name**: "intro"
   - **Start Time**: 0.0 (starts at beginning)
   - **Tempo**: 0.5 (seconds per beat - this is 120 BPM)
   - **Total Beats**: 16 (4 bars of 4 beats)
   - Leave "has multiple segments" unchecked
3. Click **OK**

You should now see "intro" in the section list and beat markers appear on the timeline.

### Step 5: Understanding the Timeline

The timeline shows:
- **Left side**: Time markers (in seconds)
- **Center**: 10 columns representing the 10 light channels
- **Right side**: Audio waveform
- **Yellow dashed lines**: Beat markers (where you can place lights)
- **Red line**: Section start marker with section name
- **Green line**: Current playback position

### Step 6: Add Actions Using the Section Editor

The editor provides comprehensive editing dialogs for creating sequences and actions:

1. **Open section editor:**
   - Select your "intro" section in the left panel
   - Click the "Edit" button in the Sections & Timing panel
   - Click "Edit Sequences..." button in the section dialog

2. **Add a sequence:**
   - Click "Add Sequence" in the Sequences dialog
   - Choose beat specification:
     * **All beats** - Execute on every beat (we'll use this)
     * **Single beat** - Execute on one specific beat
     * **Multiple beats** - Execute on specific beats (e.g., 1,5,9,13)
   - Select the "All beats" radio button
   - Click OK (or continue to add actions)

3. **Add an action:**
   - With your sequence created, click "Add Action"
   - Select action type from dropdown: "all_channels"
   - Set duration: 0.25 seconds
   - Click OK

4. **Save and view:**
   - Click OK to close all dialogs
   - You'll see orange bars appear on the timeline at each beat (all_channels actions)

### Step 7: Interactive Timeline Features

Now explore the click-to-edit features:

1. **Left-click to edit:**
   - Left-click any orange bar on the timeline
   - This opens the Sequence Editor with that action's sequence pre-selected
   - Make changes and click OK to apply them immediately

2. **Right-click context menu:**
   - Right-click any action bar for hierarchical editing options:
     * Edit Action - Edit this specific action
     * Edit Sequence - Edit all actions at these beats
     * Edit Section - Edit the entire section timing
   - Try it now - right-click an orange bar and explore the menu

3. **Seek and preview:**
   - Click anywhere on the waveform (right side column) to jump to that time
   - Hover over waveform to see yellow preview line and timestamp tooltip
   - The green horizontal line shows current playback position

4. **Waveform zoom:**
   - Scroll mouse wheel over waveform to zoom amplitude (100-1000%)
   - "Amp: X%" indicator shows current zoom level
   - Useful for seeing quiet sections more clearly

### Step 8: Test Playback

1. Click the **▶ Play** button (or press Space bar)
2. Watch the green playback position line move through your timeline (60fps smooth)
3. Live position indicator (top-right green text) shows current time
4. View auto-scrolls to follow playback
5. Click waveform to seek to any position
6. Adjust zoom with **+/-** buttons to see more or less detail

### Step 9: Save Your Song

1. Click **File → Save** or press **Ctrl+S**
2. The JSON file is automatically saved to `songs/` folder with same name as your MP3
3. You'll see a "Saved" confirmation message

### Step 10: Test in the Simulator

Close the editor and test your lightshow:

```bash
python3 lightshow.py --simulate
```

1. Click the green **Lightshow** button
2. Your song should play with the lights synchronized to your choreography

## Common Patterns

Here are some useful patterns you can create in the editor. Each shows how to build it using the dialogs.

### Pattern 1: Simple Beat Flash

**Goal:** Flash all channels on every beat

**How to create:**
1. Edit Section → Edit Sequences
2. Add Sequence → Choose "All beats" → OK
3. Add Action → Type: "all_channels", Duration: 0.25 → OK

**Resulting JSON:**
```json
{
  "all_beats": true,
  "actions": [
    {"type": "all_channels", "duration": 0.25}
  ]
}
```

### Pattern 2: Alternating Channels

**Goal:** Channels 1-5 on odd beats, 6-10 on even beats

**How to create:**
1. Edit Section → Edit Sequences
2. Add Sequence → Choose "Multiple beats", enter "1,3,5,7" → OK
3. Add 5 Actions: Type "note", channel 0-4, duration 0.5 each
4. Repeat with new sequence for beats "2,4,6,8" using channels 5-9

**Resulting JSON (first sequence):**
```json
{
  "beats": [1, 3, 5, 7],
  "actions": [
    {"type": "note", "channel": 0, "duration": 0.5},
    {"type": "note", "channel": 1, "duration": 0.5},
    {"type": "note", "channel": 2, "duration": 0.5},
    {"type": "note", "channel": 3, "duration": 0.5},
    {"type": "note", "channel": 4, "duration": 0.5}
  ]
}
```

### Pattern 3: Wave Effect

**Goal:** Lights cascade from channel 1 to 10

**How to create:**
1. Edit Section → Edit Sequences
2. Add Sequence → Choose "Single beat", enter beat number → OK
3. Add Action → Type: "step_up" → OK

**Resulting JSON:**
```json
{
  "beat": 1,
  "actions": [
    {"type": "step_up"}
  ]
}
```

### Advanced: Creating Reusable Phrases

Phrases are patterns you can reuse multiple times. Here's how to create and use them:

#### Creating a Phrase

1. Click **Edit → Manage Phrases...**
2. Click **Add Phrase**
3. Enter a phrase ID (e.g., "0" or "main_riff")
4. Click **Edit Notes** to add notes to the phrase
5. Add individual notes with:
   - **channel**: Which channel (0-9)
   - **delay_multiplier**: When to trigger (relative to beat, e.g., 0.0 = start of beat)
   - **duration_multiplier**: How long to stay on (relative to tempo, e.g., 0.25 = quarter beat)

**Example phrase** - Rising pattern across 4 channels:

```json
{
  "description": "Rising pattern",
  "notes": [
    {"channel": 0, "delay_multiplier": 0.0, "duration_multiplier": 0.25},
    {"channel": 1, "delay_multiplier": 0.25, "duration_multiplier": 0.25},
    {"channel": 2, "delay_multiplier": 0.5, "duration_multiplier": 0.25},
    {"channel": 3, "delay_multiplier": 0.75, "duration_multiplier": 0.25}
  ]
}
```

#### Using a Phrase

**Method 1: Via dialogs**
1. Edit Section → Edit Sequences → Add Sequence
2. Choose beat(s) for the phrase
3. Add Action → Type: "phrase", Phrase ID: "0" → OK

**Method 2: Right-click on phrase action**
- If you already have a phrase action on the timeline
- Right-click it → "Edit Phrase Notes..."
- This opens the Phrase Notes editor directly
- Make changes and they apply everywhere that phrase is used

**Resulting JSON:**
```json
{
  "beat": 5,
  "actions": [
    {"type": "phrase", "id": "0"}
  ]
}
```

**Benefit**: Change the phrase once, all references update automatically!

## Understanding the JSON Format

The editor creates and edits JSON files with comprehensive structure support. For complete JSON format documentation, see the main README.md file.

### Two Main Section Types

**Simple Sections** (single tempo):
- Direct timing properties: `start_time`, `tempo`, `total_beats`
- Used when tempo is consistent throughout the section
- Example: `songs/carol.json`

**Segmented Sections** (multiple tempos):
- Contains array of `segments`, each with own timing
- Used when tempo changes within a section
- Example: `songs/madrussian.json`

### Key Concepts Quick Reference

- **Channels** - 0-indexed (channel 0 = physical channel 1)
- **Start Time** - Absolute time in seconds from beginning of song
- **Tempo** - Seconds per beat (e.g., 0.5 = 120 BPM)
- **Sections** - Major divisions of the song (can be simple or segmented)
- **Segments** - Sub-divisions within a section with different timings
- **Sequences** - Define when actions occur (specific beats, beat lists, or all beats)
- **Actions** - What happens at that beat (note, phrase, all_channels, etc.)
- **Phrases** - Reusable note patterns with timing relative to tempo
- **Multipliers** - Timing relative to tempo (delay_multiplier × tempo = actual delay)
- **Absolute values** - Timing in actual seconds (delay, duration)

## Channel Layout

The editor displays channels in the same order as the simulator and physical hardware:

```
10   9   2   7   6   4   3   5   8   1
|-----| |---------| |-----| |-----|
 10+9      2+7+6      4+3     5+8    1
```

Groups indicate channels that are physically close together.

## Tips & Best Practices

### Getting Started

1. **Start with sections** - Define your song structure first (intro, verse, chorus, etc.)

2. **Choose the right structure**:
   - Use **simple sections** for consistent tempo
   - Use **segmented sections** for tempo changes or time signature shifts

3. **Build hierarchically** - Work from top to bottom:
   - Sections → Segments (if needed) → Sequences → Actions

4. **Start simple** - Begin with just beat markers and simple patterns, then gradually add complexity

### Creating Better Lightshows

5. **Match the music**:
   - Use the waveform to identify loud/quiet sections
   - Place more lights on strong beats
   - Use fewer lights during verses, more during chorus

6. **Use sections wisely**:
   - Create separate sections for intro, verse, chorus, bridge, outro
   - Each section can have different tempos and patterns

7. **Use phrases for patterns** - If you have a repeating pattern, create it as a phrase and reference it:
   - Reference the phrase by ID instead of repeating the notes
   - Easier to edit - change the phrase, all references update

### Timing and Technical

8. **Multipliers vs absolute values**:
   - Use **multipliers** in phrases (portable across different tempos)
   - Use **absolute values** for precise timing that doesn't change with tempo

9. **Test in the editor** - Use sequences for beat-specific patterns, actions for specific effects

10. **Measure exact timing** - Use Audacity for precise beat timing:
    1. Open MP3 in Audacity
    2. Use the waveform to find beat locations
    3. Note the time (in seconds) for each beat
    4. Calculate tempo: (time_of_beat_2 - time_of_beat_1)

### Workflow

11. **Test often** - Save and test your JSON file in the simulator frequently:
    ```bash
    python3 lightshow.py --simulate
    ```
    It's easier to fix small issues than debug a complete song

12. **Save frequently** - Use Ctrl+S to save your work often

13. **Learn from examples** - Open carol.json or madrussian.json to see complex structures

## Advanced Features

### Segments (Multi-Tempo Sections)

Some songs change tempo within a section. Use segments for this:

```json
{
  "name": "main",
  "segments": [
    {
      "start_time": 10.0,
      "tempo": 0.5,
      "total_beats": 16,
      "sequences": [...]
    },
    {
      "start_time": 18.0,
      "tempo": 0.4,
      "total_beats": 16,
      "sequences": [...]
    }
  ]
}
```

### Beat Patterns

- **Specific beat**: `"beat": 5` - Execute only on beat 5
- **Multiple beats**: `"beats": [1, 5, 9, 13]` - Execute on listed beats
- **All beats**: `"all_beats": true` - Execute on every beat

### Action Types

All action types are fully supported with dedicated editing dialogs:

#### Note (Single Channel)
Activate a single channel with precise timing.
```json
{
  "type": "note",
  "channel": 0,
  "delay": 0.0,
  "duration": 0.5
}
```
Or use multipliers (relative to tempo):
```json
{
  "type": "note",
  "channel": 0,
  "delay_multiplier": 0.5,
  "duration_multiplier": 0.33
}
```

#### Phrase (Reusable Pattern)
Reference a phrase from the phrase library.
```json
{
  "type": "phrase",
  "id": 0,
  "description": "Optional description"
}
```

#### All Channels
Activate all 10 channels simultaneously.
```json
{
  "type": "all_channels",
  "duration": 0.25
}
```
Or with multiplier:
```json
{
  "type": "all_channels",
  "duration_multiplier": 0.33
}
```

#### Step Up / Step Down
Sequential channel activation patterns.
```json
{"type": "step_up"}
```
```json
{"type": "step_down"}
```

#### Flash Mode
Change flash mode during playback.
```json
{
  "type": "flash_mode",
  "mode": 3
}
```
Use mode -1 to disable flash mode.

## Troubleshooting

### Installation Issues

#### "No module named 'pygame'"
Run the setup script: `./setup-editor.sh`

#### "ffmpeg not found"
Install ffmpeg: `sudo apt-get install ffmpeg`

### Audio Playback Issues

#### Audio doesn't play
- Check that pygame is installed: `pip3 list | grep pygame`
- Verify the MP3 file is valid and not corrupted
- Try reloading the MP3 file (File → Open MP3...)
- Check terminal output for pygame/mixer errors
- Restart the editor if playback was previously working

#### "Failed to load MP3 file"
- Make sure the file is a valid MP3
- Check that ffmpeg is installed: `which ffmpeg`
- Try converting the file: `ffmpeg -i input.mp3 output.mp3`

#### Playback doesn't work
- Verify pygame is installed: `pip3 list | grep pygame`
- Check MP3 file is valid
- Restart the editor

#### Playback position doesn't sync with audio
- This should not occur with current dual-loop implementation (60fps)
- If it does happen, try restarting the editor
- Test Play/Pause several times to verify pygame mixer is responding
- Report as a bug if issue persists

### Visual Display Issues

#### Waveform doesn't display
- Make sure pydub and numpy are installed: `./setup-editor.sh`
- Check that ffmpeg is installed: `which ffmpeg`
- Verify the MP3 file is not corrupted
- Check terminal for audio loading errors
- Try with a different MP3 file to isolate the issue

#### Timeline is blank
- Make sure you've opened an MP3 file first
- Try zooming out with the **-** button
- Verify sections exist with sequences and actions
- Check that you're scrolled to the correct time position

#### Can't see beat markers
- Make sure you've created a section
- Check that the section has a start_time and total_beats > 0
- Try scrolling down on the timeline
- Ensure the section is selected in the left panel

#### Waveform amplitude zoom doesn't work
- Make sure mouse cursor is over the waveform area (right side) when scrolling
- On Linux, uses Button-4/Button-5 events (standard scroll wheel)
- Zoom range is 100% (1.0x) to 1000% (10.0x)
- Check that waveform is visible - try dragging splitter to widen area
- "Amp: X%" indicator in legend shows current zoom level

### Editing Issues

#### Can't see or click on actions
- Make sure you've loaded an MP3 or JSON file first
- Verify that sections exist with sequences and actions
- Try zooming in/out to see if actions are visible
- Check that you're scrolled to the correct time position
- Ensure the section is selected in the left panel

#### Can't edit segments/sequences/actions
- Make sure you've loaded an MP3 or JSON file first
- Check that the section is properly created
- For segmented sections: Use "Edit Segment" to access segment sequences
- For simple sections: Use "Edit Sequences..." from the section editor

#### Context menu doesn't appear
- Make sure you're right-clicking directly on an action rectangle (colored bars)
- Try clicking in the center of the action, not the edge
- If actions overlap, zoom in for better precision
- All action types are clickable: green notes, purple phrase backgrounds, orange/blue/cyan bars

#### Phrase notes don't show on timeline
- Verify the phrase ID exists in the phrases dictionary (Edit → Manage Phrases)
- Check that the phrase has notes defined (not empty list)
- Ensure delay_multiplier and duration_multiplier values are reasonable (typically 0.0-1.0)
- The phrase must be referenced by a phrase action in a sequence
- Check that the sequence is on a beat within the visible timeline range

### Data and File Issues

#### Changes don't appear in lightshow
- Make sure you saved the JSON file (Ctrl+S)
- Check the status bar for "Saved" confirmation  
- Verify the JSON file is in the `songs/` folder or correct location
- Check that the `mp3_file` field matches your MP3 filename exactly
- If you used "Save As" with a different name, make sure the player is loading the new JSON file
- Test in the simulator first: `python3 lightshow.py --simulate`

#### Lights don't sync in simulator
- Verify you saved the JSON file (Ctrl+S)
- Check that start_time and tempo are correct
- Use Audacity to measure exact timing:
  1. Open MP3 in Audacity
  2. Use the waveform to find beat locations
  3. Note the time (in seconds) for each beat
  4. Calculate tempo: (time_of_beat_2 - time_of_beat_1)

#### JSON validation errors when loading
- The editor validates JSON structure on load
- Common issues:
  - Missing required fields (mp3_file, name, etc.)
  - Invalid tempo values (must be positive numbers)
  - Malformed JSON syntax
- Check error message for specific issues
- Use a JSON validator if needed

#### Section shows as "has segments" but can't edit timing
- This is expected - segmented sections manage timing at the segment level
- Click "Edit Section" → select a segment → "Edit Segment" to modify timing
- Or convert to simple structure using the Structure toggle (data from first segment will be kept)

## Next Steps

Once you're comfortable with the basics:

1. **Study the example files**
   - Look at `songs/carol.json` - complex multi-section song
   - Look at `songs/madrussian.json` - uses segments with varying tempos

2. **Experiment with action types**
   - Try `step_up` and `step_down` for wave effects
   - Use `all_channels` for impact moments
   - Create complex phrases

3. **Advanced timing**
   - Use segments for songs with tempo changes
   - Add delay to notes for off-beat effects
   - Vary duration for different visual effects

4. **Share your work**
   - Consider contributing your song files (without MP3s)
   - Report bugs and suggest features

## Architecture & Technical Details

### Visual Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  Menu: File | Edit                                                   │
├─────────────────┬───────────────────────────────────────────────────┤
│                 │  Channel Indicators & Groups                       │
│  Metadata       │  ┌─────────────────────────────────────────────┐  │
│  ┌───────────┐  │  │ 10  9   2   7   6   4   3   5   8   1      │  │
│  │Title      │  │  │  o  o   o   o   o   o   o   o   o   o       │  │
│  │Artist     │  │  │ |──| |─────────| |───| |───| |─|             │  │
│  │Description│  │  └─────────────────────────────────────────────┘  │
│  └───────────┘  │                                                    │
│                 ├────────────────────────────────────────────────────┤
│  Playback       │  Timeline Editor (Interactive)                     │
│  ▶ Play/Pause   │  ┌──────────────────────────────────────────┐     │
│  ⏹ Stop         │  │Time │ 10 9 2 7 6 4 3 5 8 1 │ Waveform   │     │
│                 │  ├─────┼────────────────────────┼────────────┤     │
│  Sections       │  │0.0s │                        │ ▌          │  ↑  │
│  ┌───────────┐  │  │     │    ▶ Section Start     │ █          │  │  │
│  │• Intro    │  │  │1.0s ├────────────────────────┤ ▌          │  │  │
│  │  Main     │  │  │     │ Beat 1 - - - - - - - - │ █          │  │  │
│  │  Finale   │  │  │2.0s │ [====] [====]          │ █          │  E  │
│  └───────────┘  │  │     │ Beat 2 - - - - - - - - │ ▌          │  a  │
│  Add | Edit | ✕ │  │3.0s │ [====]     [====]      │ █          │  r  │
│                 │  │     │ Beat 3 - - - - - - - - │ ▌          │  l  │
│  Timing Info    │  │4.0s │ [========]             │ █          │  i  │
│  Start: 0.5s    │  │     │ Beat 4 - - - - - - - - │ ▌          │  e  │
│  Tempo: 0.5s    │  │5.0s │                        │ █          │  r  │
│  Beats: 32      │  │     │                        │            │  │  │
│                 │  │     └────────────────────────┴────────────┘  │  │
│  Zoom: [-][+]   │  │                                              ↓  │
│                 │  │  [====] = Channel activation (left-click to edit)│
│  Amp: 100%      │  │  - - -  = Beat marker lines (yellow dashes)    │
│  Position: 1.23s│  │  ▶      = Section boundary (red line)          │
│                 │  │  ▌█     = Audio waveform (scroll to zoom)      │
│                 │  │  Right-click actions for context menu          │
│                 │  └────────────────────────────────────────────────┘
│                 │
└─────────────────┴───────────────────────────────────────────────────┘

Interaction Features:
• Left-click any action bar → Opens Sequence Editor dialog
• Right-click any action → Hierarchical context menu (Edit Action/Sequence/Section)
• Click waveform → Seek to that position
• Hover waveform → Preview line with timestamp tooltip
• Scroll over waveform → Zoom amplitude (100-1000%)
• Space bar → Play/Pause
• Auto-scroll follows playback
```

### Component Architecture

```
SongEditor (Main Application)
├── UI Layout
│   ├── Left Panel
│   │   ├── MetadataPanel (Title, Artist, Description, MP3 File)
│   │   ├── PlaybackPanel (Play/Pause, Stop)
│   │   └── SectionPanel
│   │       ├── Section Listbox
│   │       ├── Management Buttons (Add/Edit/Delete)
│   │       ├── Timing Info Label
│   │       ├── Zoom Controls (+/- buttons)
│   │       ├── Amplitude Indicator (Amp: X%)
│   │       └── Position Indicator (live during playback)
│   │
│   └── Right Panel
│       ├── ChannelBar (Canvas)
│       │   ├── Bulb Indicators (live during playback)
│       │   ├── Channel Labels (physical layout)
│       │   └── Group Brackets
│       │
│       └── TimelineCanvas (Canvas - Interactive)
│           ├── Waveform Display
│           │   ├── Amplitude bars
│           │   ├── Scroll-to-zoom amplitude
│           │   ├── Click-to-seek
│           │   └── Hover preview line with tooltip
│           ├── Channel Columns (10 channels)
│           ├── Time Grid
│           ├── Section Markers (red lines)
│           ├── Beat Markers (yellow dashes)
│           ├── Action Rectangles (color-coded by type)
│           ├── Playback Position (green line, 60fps smooth)
│           └── Auto-scroll following playback
│
├── Data Management
│   ├── song_data (JSON structure)
│   ├── audio_data (AudioSegment)
│   ├── waveform_data (numpy array)
│   ├── sections list
│   ├── phrases dict
│   └── update_id (invalidation tracking)
│
└── Dialog Classes
    ├── SectionDialog (Name, timing, segments, Edit Sequences)
    ├── SequenceEditorDialog (Beats, Add/Edit/Delete Actions)
    ├── ActionDialog (Type-specific fields)
    ├── PhraseLibraryDialog (Add/Edit/Delete phrases)
    └── PhraseNotesDialog (Add/Edit/Delete notes)
```

### Data Flow

```
    MP3 File                            JSON File
       │                                    ↑
       │ Load                               │ Save
       ↓                                    │
    ┌──────────────┐                   ┌───────────┐
    │ AudioSegment │                   │ song_data │
    │  (pydub)     │                   │  (dict)   │
    └──────┬───────┘                   └─────↑─────┘
           │                                 │
           │ Extract samples                 │
           ↓                                 │
    ┌──────────────┐                        │
    │ numpy array  │                        │
    │ (waveform)   │                        │
    └──────┬───────┘                        │
           │                                 │
           │ Render                          │
           ↓                                 │
    ┌──────────────────────────────────────────────┐
    │         Timeline Canvas                      │
    │  • Waveform bars                             │
    │  • Channel columns                           │
    │  • Beat markers                              │
    │  • Section boundaries                        │
    │  • Action rectangles                         │
    └──────────────────────────────────────────────┘
                      │
                      │ User Interaction
                      ↓
              ┌───────────────┐
              │ Mouse/Keyboard│ → Modify song_data
              │ Events        │   (sections, sequences, actions)
              └───────────────┘
```

### System Integration

```
┌─────────────────────────────────────────────────────────────────────┐
│           EDITOR ←→ LIGHTSHOW INTEGRATION                           │
└─────────────────────────────────────────────────────────────────────┘

    Song Editor                      Lightshow System
    ───────────                      ────────────────

    1. Create/Edit                   
       song_data                     
          │                          
          ↓                          
    2. Save JSON ───────────────────→ songs/song.json
                                          │
                                          ↓
                                     3. SongLoader
                                        reads JSON
                                          │
                                          ↓
                                     4. SongInterpreter
                                        executes sequences
                                          │
                                          ↓
                                     5. Channel control
                                        (GPIO or simulator)

    No direct code dependencies!
    Communication via JSON file format only.
```

### Technical Implementation

**Dependencies:**
- **tkinter** - GUI framework (Python built-in)
- **pygame** - Audio playback
- **pydub** - Audio processing (MP3 to waveform)
- **numpy** - Waveform data manipulation
- **ffmpeg** - Audio codec support (system dependency)

**Data Processing Pipeline:**
1. Load MP3 → AudioSegment (pydub)
2. Extract samples → numpy array
3. Normalize → waveform_data
4. Render → Canvas visualization
5. User edits → song_data structure (dict)
6. Save → JSON file

### Design Decisions

**1. Separation from Raspberry Pi**
- Editor runs only on development PC
- Dependencies NOT installed on Pi
- Keeps Pi installation minimal
- setup-editor.sh checks for Pi and warns

**2. Timeline Orientation & Interaction**
- Vertical scrolling (up = earlier, down = later)
- Matches rhythm game conventions
- Natural feel for beat-based editing
- Click-to-edit paradigm for direct manipulation
- Context menus provide hierarchical access

**3. Channel Layout**
- Matches physical hardware arrangement
- Groups visually indicated
- Consistent with simulator display
- Channel order: 10, 9, 2, 7, 6, 4, 3, 5, 8, 1

**4. Dialog-Based Editing**
- Comprehensive editing dialogs for all elements
- Clear hierarchy: Section → Sequence → Action
- Changes apply immediately on OK
- Right-click provides quick access

**5. Section-Based Structure**
- Sections define timing structure
- Support for varying tempos (segments)
- Each section has own beat grid
- Allows complex song structures

## Development Notes

The editor is intentionally separate from the main lightshow code to avoid adding unnecessary dependencies to the Raspberry Pi. The editor requires:
- pygame (large package with SDL dependencies)
- pydub (audio processing)
- numpy (array processing)
- ffmpeg (system dependency)

None of these are needed for running the lightshow itself, which keeps the Pi installation minimal.

## Future Enhancements

The editor includes many interactive features (click-to-edit, context menus, waveform seek, phrase visualization, auto-scroll, etc.). Future versions may include:

- [ ] Drag-and-drop timeline editing (drag notes, resize durations)
- [ ] Copy/paste sequences
- [ ] Undo/redo support
- [ ] Real-time light preview during editing (like simulator)
- [ ] Automatic beat detection from audio
- [ ] Timeline markers and labels
- [ ] Multi-selection and bulk edit
- [ ] Templates and presets for common patterns
- [ ] BPM calculator (convert BPM ↔ seconds per beat)
- [ ] Phrase preview (test phrase without full playback)

## Contributing

If you'd like to improve the editor, contributions are welcome! Some areas that could use enhancement:
- Better waveform rendering
- Visual timeline representation of sequences/actions
- More intuitive beat marker placement
- Drag-and-drop editing
- Keyboard navigation
- Accessibility features
- Performance optimization for large files
- Additional export formats

## License

This editor is part of the Pi Lightshow project. See LICENSE file for details.
