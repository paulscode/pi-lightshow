# Pi Lightshow

A Christmas lightshow controller for Raspberry Pi with JSON-based song definitions and development simulator.

**Platform Support:**
- ✅ Raspberry Pi (all versions) - Buster (OMXPlayer), Bookworm/Trixie (VLC)
- ✅ Linux development systems (Ubuntu, Mint, etc.)
- ✅ Simulator mode on any platform with Python 3 and Tkinter

## 🎄 Features

- **10-channel light control** via GPIO or simulated display
- **JSON-based song definitions** for easy customization
- **Graphical simulator** for development without Raspberry Pi hardware
- **Visual song editor** for creating choreography with timeline interface
- **Multiple operating modes**: Always on, slow/medium/fast random flashing, music lightshow
- **Button controls**: Power, Mode cycling, Lightshow start
- **Optional API integration** for external triggers
- **Cross-platform audio**: VLC support for modern Raspberry Pi OS (Bookworm/Trixie) and development systems
- **Resource-efficient**: Automatic thread cleanup prevents exhaustion on Raspberry Pi

## 📁 Project Structure

```
pi-lightshow/
├── songs/                           # JSON song definitions and MP3 files
│   ├── carol.json                   # Trans-Siberian Orchestra
│   ├── madrussian.json              # Mad Russian's Christmas
│   └── playlist.json                # Song playback order
├── src/
│   ├── song_loader.py               # Song loading and interpretation
│   ├── player_interface.py          # Audio player abstraction
│   ├── hardware/
│   │   └── channel_interface.py    # Hardware abstraction layer
│   └── simulator/
│       └── gui_simulator.py         # Graphical development simulator
├── lightshow.py                     # Main application
├── song_editor.py                   # Visual song editor (dev only)
├── setup-dev.sh                     # Automated development setup
├── setup-pi.sh                      # Automated Raspberry Pi setup
├── setup-editor.sh                  # Song editor setup script
├── start-editor.sh                  # Launch script for song editor
├── requirements-editor.txt          # Python dependencies for editor
├── config-example.json              # Example configuration file
├── README.md                        # This file
├── EDITOR.md                        # Song editor documentation
├── LICENSE                          # MIT License
└── .gitignore                       # Git ignore rules
```

## 🚀 Quick Start

### Development Setup (Linux Mint / Ubuntu)

1. **Install Python dependencies:**

```bash
sudo apt-get update
sudo apt-get install python3 python3-pip python3-tk
```

2. **Install audio support (choose one):**

**Option A: With Audio Playback (Recommended)**
```bash
# Install VLC for audio playback
sudo apt-get install vlc libvlc-dev

# Install Python bindings (Ubuntu 24+/Mint 22+)
sudo apt-get install python3-vlc

# OR for older systems:
pip3 install --user python-vlc

# OR if needed:
pip3 install --user --break-system-packages python-vlc
```

**Option B: Visual-Only Mode (No Audio)**
```bash
# No additional packages needed
# Simulator will run in timing-simulation mode without playing audio
```

3. **Quick Install (All Dependencies):**

```bash
# Run the automated setup script
cd ~/workspace/pi-lightshow
./setup-dev.sh
```

4. **Run the simulator:**

```bash
cd ~/workspace/pi-lightshow
python3 lightshow.py --simulate
```

This will open a GUI showing the 10 channels arranged as they would be physically, with three control buttons.

**What to Expect:**
- If MP3 files are present and VLC is installed: Audio will play with synchronized lights
- If MP3 files are missing: Lightshow runs in timing-simulation mode (lights only, no audio)
- The simulator works either way - perfect for testing timing before adding music

**Note:** For creating custom songs, see the "Creating Custom Songs" section below. A visual song editor is available for easier choreography creation.

### Raspberry Pi Setup

**Automated Setup (Recommended):**

The automated setup script detects your Raspberry Pi OS version and installs the appropriate audio player:

```bash
cd ~/pi-lightshow
./setup-pi.sh
```

The script will:
- Detect your Raspberry Pi OS version (Buster, Bookworm, Trixie, etc.)
- Install OMXPlayer on Buster (legacy)
- Install VLC on Bookworm/Trixie (modern)
- Install all required Python dependencies
- Verify installations

**Manual Setup:**

<details>
<summary>Click to expand manual installation instructions</summary>

**For Raspberry Pi OS Buster (Legacy):**

```bash
sudo apt-get update
sudo apt-get upgrade
sudo apt-get install git omxplayer python3-pip python3-dbus
pip3 install --user omxplayer-wrapper
```

**For Raspberry Pi OS Bookworm/Trixie (Modern):**

```bash
sudo apt-get update
sudo apt-get upgrade
sudo apt-get install git vlc python3-vlc
```

</details>

3. **Clone repository (if not already cloned):**

```bash
cd ~
git clone https://github.com/paulscode/pi-lightshow
cd pi-lightshow
```

4. **Add MP3 files:**

Place your MP3 files in the `songs/` directory, matching the filenames specified in each song's JSON file:
- `carol.mp3` for Carol of the Bells (referenced in `carol.json`)
- `madrussian.mp3` for Mad Russian's Christmas (referenced in `madrussian.json`)

**Note:** The JSON files are included in the repository, but the MP3 files are NOT included due to copyright. You must provide your own MP3 files.

5. **Run the lightshow:**

```bash
sudo python3 lightshow.py
```

**Note:** `sudo` is required on Raspberry Pi for GPIO access.

### Auto-start on Boot (Raspberry Pi)

1. Create systemd service:

```bash
sudo nano /lib/systemd/system/lightshow.service
```

2. Add the following content:

```ini
[Unit]
Description=Christmas Light Show
After=multi-user.target

[Service]
Type=idle
User=pi
Group=pi
WorkingDirectory=/home/pi/pi-lightshow
ExecStart=/usr/bin/python3 /home/pi/pi-lightshow/lightshow.py

[Install]
WantedBy=multi-user.target
```

3. Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable lightshow.service
sudo reboot
```

## 🎮 Usage

### Command-Line Options

```bash
# Run on Raspberry Pi with hardware (requires sudo for GPIO)
sudo python3 lightshow.py

# Run simulator on any computer (no hardware needed)
python3 lightshow.py --simulate

# Use custom song directory
python3 lightshow.py --songs-dir /path/to/custom/songs

# Combine options
python3 lightshow.py --simulate --songs-dir /path/to/songs
```

**Arguments:**
- `--simulate`: Run with GUI simulator instead of GPIO hardware
- `--songs-dir <path>`: Specify directory containing song JSON files (default: `songs`)

### Button Controls

1. **Power Button** (GPIO 25 to Ground) - Red button in simulator
   - Press to initiate shutdown sequence
   - Wait 30 seconds before disconnecting power

2. **Mode Button** (GPIO 24 to Ground) - Yellow button in simulator
   - Cycles through light patterns:
     - Always on
     - Slow random flash
     - Medium random flash
     - Fast random flash
   - Stops music if playing

3. **Lightshow Button** (GPIO 23 to Ground) - Green button in simulator
   - Starts music lightshow
   - Cycles through available songs
   - Automatically continues to next song when finished

## 💡 Channel Configuration

### 10 Channels with GPIO Pins

| Channel | GPIO Pin | Description |
|---------|----------|-------------|
| 1       | GPIO 17  | Far right |
| 2       | GPIO 27  | Group 2, left |
| 3       | GPIO 22  | Group 3, left |
| 4       | GPIO 13  | Group 2, right |
| 5       | GPIO 19  | Group 3, right |
| 6       | GPIO 26  | Group 2, middle-right |
| 7       | GPIO 21  | Group 2, middle-left |
| 8       | GPIO 20  | Group 4, left |
| 9       | GPIO 16  | Group 1, right |
| 10      | GPIO 12  | Group 1, left |

### Physical Arrangement

```
 10   9   2   7   6   4   3   5   8   1
|------| |---------| |-----| |-----|
```
TODO: Add image of a real-world example


## 🎵 Creating Custom Songs

Songs can be created in two ways:
1. **Visual Editor** (recommended) - Use the GUI song editor for intuitive timeline-based editing
2. **Manual JSON editing** - Advanced users can edit JSON files directly

### Using the Song Editor (Recommended)

The visual song editor provides a timeline-based interface for choreographing light shows. See [EDITOR.md](EDITOR.md) for complete documentation.

**Quick Start:**

1. **Install editor dependencies:**
   ```bash
   ./setup-editor.sh
   ```

2. **Launch the editor:**
   ```bash
   python3 song_editor.py
   ```

3. **Create a new song:**
   - File → Open MP3... and select your audio file
   - Fill in metadata (title, artist, description)
   - Add sections with start times, tempos, and beat counts
   - Place channel activations on the timeline
   - Save (Ctrl+S)

**Editor Features:**
- Visual waveform display
- Timeline with 10 channel columns matching physical layout
- Beat-synchronized editing
- Section and phrase management
- Audio playback with synchronized visualization
- Zoom and pan controls
- Automatic JSON save/load

**Note:** The editor is designed for development PCs (Linux Mint, Ubuntu, etc.) and should NOT be installed on the Raspberry Pi. It requires pygame, pydub, numpy, and ffmpeg which are not needed for running lightshows.

### Manual JSON Editing

Song definitions are JSON files in the `songs/` directory.

### Playlist Configuration

Control song playback order with `songs/playlist.json`:

```json
{
  "playlist": [
    "carol",
    "madrussian"
  ]
}
```

**Notes:**
- List song names without the `.json` extension
- If `playlist.json` doesn't exist, songs play in alphabetical order by filename
- Invalid song names are skipped with a warning

### Audio Player Notes

The system uses different audio players depending on the environment:

| Environment | Player | Notes |
|------------|--------|-------|
| Raspberry Pi (Buster) | OMXPlayer | Hardware-accelerated, low latency (legacy) |
| Raspberry Pi (Bookworm/Trixie) | VLC | Modern replacement for OMXPlayer |
| Linux Mint/Ubuntu | VLC | Wall-clock timing (0.1s startup delay) |
| Simulated | Time-based | No actual audio, timing simulation |

**Platform Detection:** The system automatically detects if it's running on a Raspberry Pi and selects the appropriate player. On Buster, it tries OMXPlayer first and falls back to VLC if unavailable. On newer OS versions, it uses VLC directly.

**Timing Approach:** VLC uses wall-clock timing (`time.time() - playback_start_time`) instead of `vlc.get_time()` because VLC's internal timer lags 0.5-0.9s behind actual audio playback. After VLC reports `is_playing()`, the system waits an additional 0.1s for audio device initialization before recording the start time. This approach delivers near-zero timing error from the first beat.

**Thread Management:** The system uses Threading.Timer for beat-synchronized actions. On resource-constrained systems (like Raspberry Pi 3), completed timers are automatically cleaned up every 20 timer creations to prevent thread exhaustion. This allows long songs to play without hitting system thread limits (~380 threads on Pi 3).

**Important:** All song JSON files should use timing calibrated to actual audio playback, not VLC's position API. The wall-clock compensation happens automatically in the player interface.

### Basic Song Structure

```json
{
  "title": "Song Title",
  "artist": "Artist Name",
  "description": "Description of the lightshow",
  "mp3_file": "filename.mp3",
  "sections": [...],
  "phrases": {...}
}
```

### Sections

Sections define the timing structure of the song:

```json
{
  "name": "main",
  "start_time": 33.078,
  "tempo": 0.96616875,
  "total_beats": 175,
  "sequences": [...]
}
```

**Timing Calibration:**
- Use Audacity or similar audio editor to visualize waveforms
- `start_time`: When the section's first beat begins (seconds)
- `tempo`: Time between beats (seconds)
- Calculate tempo: (last_beat_timestamp - start_time) / total_beats

### Sequences

Sequences define what happens at specific beats:

```json
{
  "beats": [1, 2, 3, 4],
  "actions": [
    {
      "type": "phrase",
      "id": 0,
      "description": "Background phrase"
    }
  ]
}
```

### Action Types

- **`note`**: Single channel on/off
  ```json
  {"type": "note", "channel": 5, "delay": 0.5, "duration": 0.33}
  ```

- **`phrase`**: Pre-defined sequence of notes
  ```json
  {"type": "phrase", "id": 1, "description": "Main melody"}
  ```

- **`all_channels`**: Turn on all channels
  ```json
  {"type": "all_channels", "duration": 0.25}
  ```

- **`step_up`** / **`step_down`**: Sequential channel effects
  ```json
  {"type": "step_up"}
  ```

### Phrases

Reusable note patterns with timing relative to tempo:

```json
"phrases": {
  "0": {
    "description": "Background repeating phrase",
    "notes": [
      {"channel": 6, "delay_multiplier": 0.5, "duration_multiplier": 0.5},
      {"channel": 1, "delay_multiplier": 0.5, "duration_multiplier": 0.5}
    ]
  }
}
```

### Multi-Segment Songs

For songs with varying tempos (like Mad Russian), use segments:

```json
{
  "name": "prelude",
  "segments": [
    {
      "start_time": 0.7,
      "tempo": 0.624,
      "total_beats": 8,
      "sequences": [...]
    },
    {
      "start_time": 5.692,
      "tempo": 0.6295,
      "total_beats": 8,
      "sequences": [...]
    }
  ]
}
```

## 📖 JSON Format Reference

Complete reference for the Pi Lightshow JSON song format.

### File Structure

```json
{
  "title": "string",
  "artist": "string", 
  "description": "string",
  "mp3_file": "filename.mp3",
  "sections": [ ... ],
  "phrases": { ... }
}
```

### Sections

Two types of sections:

**Simple Section (Single Tempo):**

```json
{
  "name": "section_name",
  "start_time": 0.0,
  "tempo": 0.5,
  "total_beats": 32,
  "sequences": [ ... ]
}
```

**Multi-Tempo Section (With Segments):**

```json
{
  "name": "section_name",
  "segments": [
    {
      "start_time": 0.0,
      "tempo": 0.5,
      "total_beats": 16,
      "sequences": [ ... ]
    },
    {
      "start_time": 8.0,
      "tempo": 0.6,
      "total_beats": 16,
      "sequences": [ ... ]
    }
  ]
}
```

### Sequences

A sequence defines what happens at specific beats:

**Execute on Specific Beat:**

```json
{
  "beat": 5,
  "actions": [ ... ]
}
```

**Execute on Multiple Beats:**

```json
{
  "beats": [1, 5, 9, 13],
  "actions": [ ... ]
}
```

**Execute on All Beats:**

```json
{
  "all_beats": true,
  "actions": [ ... ]
}
```

### Actions

**Note (Single Channel):**

```json
{
  "type": "note",
  "channel": 0,
  "delay": 0.0,
  "duration": 0.5
}
```

- **channel**: 0-9 (channel 0 = physical channel 1)
- **delay**: Seconds to wait before turning on
- **duration**: Seconds to stay on

**Phrase (Reusable Pattern):**

```json
{
  "type": "phrase",
  "id": "0",
  "description": "Optional description"
}
```

- **id**: String or number matching phrase ID in phrases dictionary

**All Channels:**

```json
{
  "type": "all_channels",
  "duration": 0.25
}
```

Or with duration multiplier:

```json
{
  "type": "all_channels",
  "duration_multiplier": 0.5
}
```

**Step Up (Wave Effect):**

```json
{
  "type": "step_up"
}
```

Lights up all channels in sequence (visual wave)

**Step Down (Reverse Wave):**

```json
{
  "type": "step_down"
}
```

Turns off channels in reverse sequence

**Flash Mode (Mode Change):**

```json
{
  "type": "flash_mode",
  "mode": 3
}
```

Changes the flash mode during song:
- 0: Always on
- 1: Slow flash
- 2: Medium flash
- 3: Fast flash
- -1: Restore previous mode

### Phrases

Phrases are reusable note patterns:

```json
{
  "phrases": {
    "0": {
      "description": "Rising pattern",
      "notes": [
        {
          "channel": 0,
          "delay_multiplier": 0.0,
          "duration_multiplier": 0.25
        },
        {
          "channel": 1,
          "delay_multiplier": 0.25,
          "duration_multiplier": 0.25
        }
      ]
    }
  }
}
```

- **delay_multiplier**: Multiply by tempo to get delay in seconds
- **duration_multiplier**: Multiply by tempo to get duration in seconds

### Channel Numbers

Channels are 0-indexed in JSON but 1-indexed in physical layout:

| JSON | Physical | GPIO | Position |
|------|----------|------|----------|
| 0    | 1        | 17   | Far right |
| 1    | 2        | 27   | Group 2, left |
| 2    | 3        | 22   | Group 3, left |
| 3    | 4        | 13   | Group 2, right |
| 4    | 5        | 19   | Group 3, right |
| 5    | 6        | 26   | Group 2, middle-right |
| 6    | 7        | 21   | Group 2, middle-left |
| 7    | 8        | 20   | Group 4, left |
| 8    | 9        | 16   | Group 1, right |
| 9    | 10       | 12   | Group 1, left |

Physical layout:
```
 10   9   2   7   6   4   3   5   8   1
```

### Timing Calculations

**BPM to Tempo:**

```
tempo = 60 / BPM
```

Examples:
- 120 BPM = 0.5 seconds per beat
- 140 BPM = 0.4286 seconds per beat
- 90 BPM = 0.6667 seconds per beat

**Measuring Start Time:**

Use Audacity or similar:
1. Load MP3 in Audacity
2. Zoom to see waveform clearly
3. Place cursor at first beat
4. Read time at bottom (e.g., "0.349 sec")
5. Use this as start_time

**Measuring Tempo:**

1. Find two clear consecutive beats
2. Note their times (e.g., beat 1 at 0.5s, beat 2 at 1.0s)
3. Subtract: 1.0 - 0.5 = 0.5 seconds per beat
4. Use this as tempo

**Calculating Total Beats:**

```
section_duration = end_time - start_time
total_beats = section_duration / tempo
```

Round to nearest integer.

### Common Patterns

**Pulse on Every Beat:**

```json
{
  "all_beats": true,
  "actions": [
    {"type": "all_channels", "duration": 0.25}
  ]
}
```

**Alternating Channels:**

```json
{
  "beat": 1,
  "actions": [
    {"type": "note", "channel": 0, "duration": 0.5},
    {"type": "note", "channel": 2, "duration": 0.5},
    {"type": "note", "channel": 4, "duration": 0.5}
  ]
},
{
  "beat": 2,
  "actions": [
    {"type": "note", "channel": 1, "duration": 0.5},
    {"type": "note", "channel": 3, "duration": 0.5}
  ]
}
```

**Build Up Effect:**

```json
{
  "beats": [1, 3, 5, 7],
  "actions": [{"type": "step_up"}]
}
```

**Big Impact:**

```json
{
  "beat": 16,
  "actions": [
    {"type": "all_channels", "duration": 1.0}
  ]
}
```

**Cascading Phrase:**

Create a phrase:
```json
{
  "phrases": {
    "cascade": {
      "description": "Channels light in sequence",
      "notes": [
        {"channel": 0, "delay_multiplier": 0.0, "duration_multiplier": 0.1},
        {"channel": 1, "delay_multiplier": 0.1, "duration_multiplier": 0.1},
        {"channel": 2, "delay_multiplier": 0.2, "duration_multiplier": 0.1},
        {"channel": 3, "delay_multiplier": 0.3, "duration_multiplier": 0.1}
      ]
    }
  }
}
```

Use it:
```json
{
  "beats": [1, 5, 9, 13],
  "actions": [
    {"type": "phrase", "id": "cascade"}
  ]
}
```

### Validation Checklist

Before testing your song:

- [ ] mp3_file matches actual MP3 filename
- [ ] All section start_times are in ascending order
- [ ] Tempo values are positive (> 0)
- [ ] Total_beats matches actual song duration
- [ ] Channel numbers are 0-9 (not 1-10)
- [ ] All phrase IDs referenced in actions exist in phrases dict
- [ ] Duration values are reasonable (typically 0.1 to 2.0)
- [ ] No sections overlap (unless intentional)
- [ ] JSON syntax is valid (check with `python3 -m json.tool song.json`)

### Testing Tips

1. **Test in simulator first**
   ```bash
   python3 lightshow.py --simulate
   ```

2. **Check JSON syntax**
   ```bash
   python3 -m json.tool songs/your-song.json
   ```

3. **Verify timing**
   - First few beats should sync perfectly
   - If drift occurs, check start_time and tempo
   - Use Audacity to verify measurements

4. **Start simple**
   - Test with just one section
   - Add complexity gradually
   - Easier to debug small issues

### Example: Complete Simple Song

```json
{
  "title": "Test Song",
  "artist": "Test Artist",
  "description": "Simple test pattern",
  "mp3_file": "test.mp3",
  "sections": [
    {
      "name": "main",
      "start_time": 0.5,
      "tempo": 0.5,
      "total_beats": 16,
      "sequences": [
        {
          "all_beats": true,
          "actions": [
            {
              "type": "all_channels",
              "duration": 0.25
            }
          ]
        }
      ]
    }
  ],
  "phrases": {}
}
```

This makes all channels flash for 0.25 seconds on every beat, starting at 0.5 seconds into the song, with 16 beats at 120 BPM (0.5 seconds per beat).

### Resources

- **Audacity**: Free audio editor for timing measurements - https://www.audacityteam.org/
- **BPM Counter**: Online tools to detect song tempo (search "online BPM counter")
- **JSON Validator**: Check your JSON syntax at https://jsonlint.com/ or use `python3 -m json.tool your-song.json`

## 🔧 Hardware Setup

### Required Components

- Raspberry Pi 3B+ or newer
- 10x Solid State Relays (SSR)
- 10x Female power cables
- 3x Momentary push buttons
- Appropriate power supply for lights
- Wire for GPIO connections

### Wiring

1. **SSRs:** Connect control side between GPIO pins and Ground
   - When GPIO goes HIGH (3.3V), SSR activates
   - SSR load side switches mains power to lights

2. **Power cables:** SSR output switches the Line (hot) wire
   - Neutral and Ground pass through directly
   - Never switch the Neutral wire

3. **Buttons:** Connect between GPIO pin and Ground
   - Code uses internal pull-up resistors (GPIO defaults to HIGH)
   - Pressing button connects GPIO to Ground (reads as LOW)
   - GPIO pins: Power=25, Mode=24, Lightshow=23
   - No external resistors needed

### Safety

⚠️ **WARNING:** You are working with mains voltage! 
- Only qualified persons should perform electrical work
- Use appropriate enclosures and strain relief
- Test thoroughly before deployment
- Follow local electrical codes

## 🔌 API Integration (Optional)

Enable external triggering for home automation or web-based control systems.

### Configuration

You can configure API endpoints using either a config file (recommended) or environment variables.

**Option 1: Config File (Recommended)**

Create `config.json` in the project root (use `config-example.json` as a template):

```json
{
  "api": {
    "integration_check_url": "https://example.com/api/check",
    "integration_done_url": "https://example.com/api/done"
  }
}
```

**Option 2: Environment Variables**

```bash
export INTEGRATION_CHECK_URL="https://example.com/api/check"
export INTEGRATION_DONE_URL="https://example.com/api/done"
```

**Priority:** Config file settings take precedence over environment variables. If neither is configured, the lightshow operates normally without integration.

**How it works:**
- The system polls the check URL every second when not playing
- If the URL returns "1", the lightshow automatically starts
- When the show finishes, the done URL is called to notify the external system

**Use cases:**
- Integration with home automation platforms (Home Assistant, OpenHAB)
- Web-based remote control interfaces
- Coordinated multi-device displays

## 🐛 Development & Debugging

### Running Tests

Test individual components:

```bash
# Test GUI simulator
python3 src/simulator/gui_simulator.py

# Test with specific songs directory
python3 lightshow.py --simulate --songs-dir /path/to/songs
```

### Simulator Features

- Visual representation of 10 channels in correct physical order
- Clickable buttons for testing control logic
- Status bar showing current mode
- No hardware or Raspberry Pi required

### Common Issues

**Simulator won't start:**
- Ensure python3-tk is installed: `sudo apt-get install python3-tk`
- Check for errors in terminal output

**No audio in development:**
- Install VLC: `pip3 install python-vlc`
- On Ubuntu 24+/Mint 22+: Use `sudo apt-get install python3-vlc` (PEP 668 compliance)
- Or use `--simulate` flag for visual-only testing

**Python package installation errors ("externally-managed-environment"):**
- Modern Linux uses PEP 668 to prevent conflicts
- Solution 1: Use system packages: `sudo apt-get install python3-vlc`
- Solution 2: Use `--break-system-packages` flag (not recommended)
- Solution 3: Run `./setup-dev.sh` which handles this automatically

**GPIO permission errors on Raspberry Pi:**
- Must run with `sudo` to access GPIO pins
- Example: `sudo python3 lightshow.py`
- The shutdown button also requires sudo to execute `shutdown -h now`

**Songs not found or wrong order:**
- Verify song JSON files are in the `songs/` directory
- Check that MP3 filenames in JSON match actual MP3 files
- Edit `songs/playlist.json` to control playback order

**Timing issues:**
- Verify MP3 encoding matches calibration values
- Use Audacity to visualize beats and measure timestamps
- Adjust `start_time` and `tempo` values in JSON

**"RuntimeError: can't start new thread" on Raspberry Pi:**
- This occurs when the system runs out of thread resources
- Fixed in v2.1.1+ with automatic timer cleanup
- Ensure you're running the latest version
- If issue persists, the system may be resource-constrained

**"python-vlc not found" error on modern Raspberry Pi:**
- Newer Raspberry Pi OS (Bookworm/Trixie) requires VLC instead of OMXPlayer
- Install with: `sudo apt-get install vlc python3-vlc`
- Or run the automated setup: `./setup-pi.sh`
- The system will automatically use VLC on modern OS versions

## 📝 Architecture Overview

This lightshow uses a modular, JSON-based architecture for easy customization:

**Key Design Principles:**
1. **Song definitions:** JSON files (not hardcoded in Python)
2. **Hardware abstraction:** Same code runs on Pi or development machine
3. **Modular design:** Separate concerns (songs, hardware, player)
4. **Wall-clock timing:** Compensates for VLC lag automatically
5. **Schedule-then-execute:** Beats scheduled relative to song start, preventing cumulative drift

**Creating New Songs:**
1. Use Audacity to analyze audio and identify beat timestamps
2. Create JSON file following the examples in `songs/`
3. Test in simulator first: `python3 lightshow.py --simulate`
4. Deploy to Pi after confirming timing accuracy

## 🤝 Contributing

Contributions welcome! Areas for improvement:

- [x] Support for newer Raspbian with alternative to OMXPlayer (✓ Complete - VLC support added)
- [ ] Web interface for remote control
- [x] Song editor GUI (✓ Complete - see EDITOR.md)
- [ ] More song definitions
- [ ] MQTT integration
- [ ] Sound-reactive mode
- [ ] Drag-and-drop timeline editing in editor
- [ ] Beat detection automation
- [ ] Real-time hardware preview from editor

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Trans-Siberian Orchestra for the amazing music
- The Raspberry Pi Foundation
- OMXPlayer developers
- Everyone who creates Christmas light displays

---

**Merry Christmas! 🎄✨**
