# pi-lightshow

This application is designed to run on a Raspberry Pi (tested on the 3B+) to control 10 channels of Christmas lights.  It operates in two modes: Music Lightshow, or Lights Patterns.  It is necessary to acquire a MP3 of the "Carol of the Bells" remix by the Trans-Siberian Orchestra and Metallica.  It should be named carol.mp3, and placed into the same folder as the source files.

Depending on how the .mp3 was encoded, it may be necessary to adjust the following values near the top of lightshow.py:

### preludeStart = 0.3494857143
    Time (in seconds) when the first note of the prelude begins
### preludeTempo = 0.7365142857
    Time (in seconds) between each beat in the prelude
    Calculate by subtracting timestamp of last beat in the prelude (before tempo slows) from preludeStart and dividing by total beats
### mainStart = 33.078
    Time (in seconds) when the first note of the main song begins
### mainTempo = 0.96616875
    Time (in seconds) between each beat in the main song
    Calculate by subtracting timestamp of last beat in the main song from mainStart and dividing by total beats

These values can be determined from any editor that visualizes the audio and displays timestamps, such as Audacity.

There are three button inputs:

### 1) Music Lightshow: Button between GPIO 23 and Ground
     After music finishes playing, automatically returns to lights only mode
### 2) Light Patterns: Button between GPIO 24 and Ground
     Press the button to cycle between
      - Always on
      - Slow flash speed
      - Medium flash speed
      - Fast flash speed
### 3) Power Off: Button between GPIO 25 and Ground
     Press the button and wait for 30 seconds to fully shut dow before disconnecting from power

There are 10 channels for controlling the Christmas lights:

### Chanel 1) GPIO 17
### Chanel 2) GPIO 27
### Chanel 3) GPIO 22
### Chanel 4) GPIO 13
### Chanel 5) GPIO 19
### Chanel 6) GPIO 26
### Chanel 7) GPIO 21
### Chanel 8) GPIO 20
### Chanel 9) GPIO 16
### Chanel 10) GPIO 12

Solid State Relays should be connected between the above listed GPIO pins and Ground.  The other end of the SSRs can switch the Line wires of 10 female power cables.

The lights controlled by the 10 channels should be arranged in a way that follows the following order and groupings:

     10   9   2   7   6   4   3   5   8   1
    |------| |---------| |-----| |-----|

(TODO: will attach an example drawing in the future)

Recommend running Raspbian Lite.
IMPORTANT NOTE: Support for OMX Player was discontinued in Raspbian Bullseye, so you must use legacy Raspbian Buster.
(TODO: will update this repo to support latest Raspbian version)

Upgrade and install required packages:

    sudo apt-get update
    sudo apt-get upgrade
    sudo apt-get install git libdbus-1-dev libglib2.0-dev omxplayer python-pip

Reboot

    sudo reboot

From the terminal run the following commands:

    cd ~
    git clone https://github.com/paulscode/pi-lightshow
    cd pi-lightshow
    pip install dbus-python omxplayer-wrapper pathlib

Then copy carol.mp3 into /home/pi/pi-lightshow/ (or wherever you downloaded the pi-lightshow repo)

The light show can be set up to auto start on boot:

    sudo nano /lib/systemd/system/lightshow.service

And enter the following contents (adjust if you downloaded the pi-lightshow repo into a different directory):

    [Unit]
      Description=Christmas Light Show
      After=multi-user.target
    
    [Service]
      Type=idle
      WorkingDirectory=/home/pi/pi-lightshow
      ExecStart=/usr/bin/python /home/pi/pi-lightshow/lightshow.py
    
    [Install]
      WantedBy=multi-user.target
