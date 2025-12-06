# Pi Lightshow

A Christmas lightshow controller for Raspberry Pi with JSON-based song definitions and development simulator.

## 🎄 Features

- **10-channel light control** via GPIO or simulated display
- **JSON-based song definitions** for easy customization
- **Graphical simulator** for development without Raspberry Pi hardware
- **Multiple operating modes**: Always on, slow/medium/fast random flashing, music lightshow
- **Button controls**: Power, Mode cycling, Lightshow start
- **Optional API integration** for external triggers

## 📁 Project Structure

```
pi-lightshow/
├── songs/                           # JSON song definitions
│   ├── carol-of-the-bells.json     # Trans-Siberian Orchestra
│   ├── mad-russian.json             # Mad Russian's Christmas
│   └── playlist.json                # Song playback order
├── src/
│   ├── song_loader.py               # Song loading and interpretation
│   ├── player_interface.py          # Audio player abstraction
│   ├── hardware/
│   │   └── channel_interface.py    # Hardware abstraction layer
│   └── simulator/
│       └── gui_simulator.py         # Graphical development simulator
├── lightshow.py                     # Main application
├── setup-dev.sh                     # Automated development setup
└── README.md                        # This file
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

### Raspberry Pi Setup

**IMPORTANT:** Currently requires Raspbian Buster (legacy) due to OMXPlayer dependency.

1. **Install system packages:**

```bash
sudo apt-get update
sudo apt-get upgrade
sudo apt-get install git omxplayer python3-pip
```

2. **Install Python packages:**

```bash
pip3 install --user dbus-python omxplayer-wrapper
```

3. **Clone repository:**

```bash
cd ~
git clone https://github.com/paulscode/pi-lightshow
cd pi-lightshow
```

4. **Add MP3 files:**

Place your MP3 files in the `songs/` directory, matching the filenames specified in each song's JSON file:
- `carol.mp3` for Carol of the Bells (referenced in `carol-of-the-bells.json`)
- `madrussian.mp3` for Mad Russian's Christmas (referenced in `mad-russian.json`)

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

### Controls

### Three Button Inputs

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
| 7       | GPIO 20  | Group 2, middle-left |
| 8       | GPIO 16  | Group 4, left |
| 9       | GPIO 12  | Group 1, right |
| 10      | GPIO 21  | Group 1, left |

### Physical Arrangement

```
 10   9   2   7   6   4   3   5   8   1
|------| |-----------| |-----| |-----|
10+9     2+7+6         4+3     5+8     (1)
```

## 🎵 Creating Custom Songs

Song definitions are JSON files in the `songs/` directory.

### Playlist Configuration

The `songs/playlist.json` file controls the order songs play:

```json
{
  "playlist": [
    "carol-of-the-bells",
    "mad-russian"
  ]
}
```

If `playlist.json` doesn't exist, songs will play in alphabetical order by filename.

### Audio Player Notes

The system uses different audio players depending on the environment:

| Environment | Player | Notes |
|------------|--------|-------|
| Raspberry Pi | OMXPlayer | Hardware-accelerated, low latency |
| Linux Mint/Ubuntu | VLC | Wall-clock timing (0.1s startup delay) |
| Simulated | Time-based | No actual audio, timing simulation |

**Timing Approach:** VLC uses wall-clock timing (`time.time() - playback_start_time`) instead of `vlc.get_time()` because VLC's internal timer lags 0.5-0.9s behind actual audio playback. After VLC reports `is_playing()`, the system waits an additional 0.1s for audio device initialization before recording the start time. This approach delivers near-zero timing error from the first beat.

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

**Channel Indexing:** 
- In JSON files: Use 0-indexed values (0-9) where 0 = physical channel 1, 9 = physical channel 10
- In documentation: Refer to channels as 1-10 for clarity
- Example: To control "Channel 1" (GPIO 17), use `"channel": 0` in JSON

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

Set environment variables to enable external triggering:

```bash
export INTEGRATION_CHECK_URL="https://example.com/api/check"
export INTEGRATION_DONE_URL="https://example.com/api/done"
```

The system will poll the check URL every second. If it returns "1", the lightshow starts and the done URL is called.

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

- [ ] Support for newer Raspbian with alternative to OMXPlayer
- [ ] Web interface for remote control
- [ ] Song editor GUI
- [ ] More song definitions
- [ ] MQTT integration
- [ ] Sound-reactive mode

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Trans-Siberian Orchestra for the amazing music
- The Raspberry Pi Foundation
- OMXPlayer developers
- Everyone who creates Christmas light displays

---

**Merry Christmas! 🎄✨**
