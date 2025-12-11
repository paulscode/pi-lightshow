"""
Hardware Abstraction Layer for Channels and Buttons

This module provides abstraction for controlling light channels and buttons,
with implementations for both Raspberry Pi GPIO and simulation.

Components:
- ChannelInterface: Abstract base for light channel control
  - RPiChannel: Raspberry Pi GPIO implementation
  - SimulatedChannel: In-memory simulation with callbacks
  
- ButtonInterface: Abstract base for button input
  - RPiButton: Raspberry Pi GPIO with event detection
  - SimulatedButton: Programmatic button simulation

Factory Functions:
- create_channels(): Creates 10 channel objects (hardware or simulated)
- create_buttons(): Creates 3 button objects (Power, Mode, Lightshow)
- setup_gpio(): Initializes GPIO in BCM mode (hardware only)
- cleanup_gpio(): Releases GPIO resources (hardware only)

GPIO Pin Mappings:
- Channels: [17, 27, 22, 13, 19, 26, 21, 20, 16, 12] (BCM mode)
- Buttons: [25=Power, 24=Mode, 23=Lightshow] (BCM mode)
"""

from abc import ABC, abstractmethod
from threading import Timer
from typing import Optional, Callable


class ChannelInterface(ABC):
    """Abstract base class for channel control."""
    
    @abstractmethod
    def on(self, duration: float = 0):
        """
        Turn the channel on.
        
        Args:
            duration: If > 0, automatically turn off after this many seconds
        """
        pass
    
    @abstractmethod
    def off(self):
        """Turn the channel off."""
        pass
    
    @abstractmethod
    def get_state(self) -> bool:
        """Get current state of the channel."""
        pass


class RPiChannel(ChannelInterface):
    """Channel implementation for Raspberry Pi GPIO."""
    
    def __init__(self, pin: int):
        """
        Initialize GPIO channel.
        
        Args:
            pin: GPIO pin number (BCM mode)
        """
        from RPi import GPIO
        self.pin = pin
        self.GPIO = GPIO
        self.GPIO.setup(self.pin, self.GPIO.OUT)
        self._timer: Optional[Timer] = None
    
    def on(self, duration: float = 0):
        """Turn the channel on."""
        self.GPIO.output(self.pin, self.GPIO.HIGH)
        if duration > 0:
            if self._timer:
                self._timer.cancel()
            self._timer = Timer(duration, self.off)
            self._timer.start()
    
    def off(self):
        """Turn the channel off."""
        if self._timer:
            self._timer.cancel()
            self._timer = None
        self.GPIO.output(self.pin, self.GPIO.LOW)
    
    def get_state(self) -> bool:
        """Get current state of the channel."""
        return self.GPIO.input(self.pin) == self.GPIO.HIGH


class SimulatedChannel(ChannelInterface):
    """Channel implementation for simulation (no hardware)."""
    
    def __init__(self, channel_number: int, state_callback: Optional[Callable] = None):
        """
        Initialize simulated channel.
        
        Args:
            channel_number: Channel number (1-10)
            state_callback: Optional callback function(channel_num, state) called on state changes
        """
        self.channel_number = channel_number
        self.state = False
        self.state_callback = state_callback
        self._timer: Optional[Timer] = None
    
    def on(self, duration: float = 0):
        """Turn the channel on."""
        self.state = True
        if self.state_callback:
            self.state_callback(self.channel_number, True)
        
        if duration > 0:
            if self._timer:
                self._timer.cancel()
            self._timer = Timer(duration, self.off)
            self._timer.start()
    
    def off(self):
        """Turn the channel off."""
        if self._timer:
            self._timer.cancel()
            self._timer = None
        
        self.state = False
        if self.state_callback:
            self.state_callback(self.channel_number, False)
    
    def get_state(self) -> bool:
        """Get current state of the channel."""
        return self.state


class ButtonInterface(ABC):
    """Abstract base class for button input."""
    
    @abstractmethod
    def cleanup(self):
        """Cleanup resources."""
        pass


class RPiButton(ButtonInterface):
    """Button implementation for Raspberry Pi GPIO."""
    
    def __init__(self, index: int, pin: int, callback: Callable):
        """
        Initialize GPIO button.
        
        Args:
            index: Button index (0-2)
            pin: GPIO pin number (BCM mode)
            callback: Callback function(index, state) where state is True for press, False for release
        """
        from RPi import GPIO
        self.index = index
        self.pin = pin
        self.callback = callback
        self.state = False
        self.GPIO = GPIO
        
        self.GPIO.setup(self.pin, self.GPIO.IN, pull_up_down=self.GPIO.PUD_UP)
        self.GPIO.add_event_detect(self.pin, self.GPIO.BOTH, self._internal_callback)
    
    def _internal_callback(self, channel):
        """Internal callback for GPIO events."""
        if self.GPIO.input(self.pin):
            if not self.state:
                self.state = True
                self.callback(self.index, self.state)
        else:
            if self.state:
                self.state = False
                self.callback(self.index, self.state)
    
    def cleanup(self):
        """Cleanup GPIO resources."""
        pass  # Will be handled by GPIO.cleanup()


class SimulatedButton(ButtonInterface):
    """Button implementation for simulation."""
    
    def __init__(self, index: int, name: str, callback: Callable):
        """
        Initialize simulated button.
        
        Args:
            index: Button index (0-2)
            name: Button name for display
            callback: Callback function(index, state)
        """
        self.index = index
        self.name = name
        self.callback = callback
        self.state = False
    
    def press(self):
        """Simulate button press."""
        if not self.state:
            self.state = True
            self.callback(self.index, True)
    
    def release(self):
        """Simulate button release."""
        if self.state:
            self.state = False
            self.callback(self.index, False)
    
    def toggle(self):
        """Toggle button state."""
        if self.state:
            self.release()
        else:
            self.press()
    
    def cleanup(self):
        """Cleanup resources."""
        pass


def create_channels(simulated: bool = False, state_callback: Optional[Callable] = None):
    """
    Create channel objects for hardware or simulation.
    
    Args:
        simulated: If True, create simulated channels, otherwise RPi GPIO channels
        state_callback: Optional callback for simulated channels
    
    Returns:
        List of 10 channel objects (0-indexed)
    """
    if simulated:
        return [SimulatedChannel(i + 1, state_callback) for i in range(10)]
    else:
        # GPIO pins for channels 1-10 (0-indexed list)
        channel_pins = [17, 27, 22, 13, 19, 26, 21, 20, 16, 12]
        return [RPiChannel(pin) for pin in channel_pins]


def create_buttons(simulated: bool = False, callback: Optional[Callable] = None):
    """
    Create button objects for hardware or simulation.
    
    Args:
        simulated: If True, create simulated buttons, otherwise RPi GPIO buttons
        callback: Callback function for button events
    
    Returns:
        Tuple of (power_button, mode_button, lightshow_button)
    """
    if simulated:
        return (
            SimulatedButton(0, "Power", callback),
            SimulatedButton(1, "Mode", callback),
            SimulatedButton(2, "Lightshow", callback)
        )
    else:
        return (
            RPiButton(0, 25, callback),  # Power button
            RPiButton(1, 24, callback),  # Mode button
            RPiButton(2, 23, callback)   # Lightshow button
        )


def setup_gpio(simulated: bool = False):
    """
    Setup GPIO if on Raspberry Pi.
    
    Args:
        simulated: If True, skip GPIO setup
    """
    if not simulated:
        from RPi import GPIO
        GPIO.setmode(GPIO.BCM)


def cleanup_gpio(simulated: bool = False):
    """
    Cleanup GPIO if on Raspberry Pi.
    
    Args:
        simulated: If True, skip GPIO cleanup
    """
    if not simulated:
        from RPi import GPIO
        GPIO.cleanup()
