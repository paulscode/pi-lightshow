from RPi import GPIO
from threading import Timer

class Channel:
    def __init__(self, pin):
        self.pin = pin
        GPIO.setup(self.pin, GPIO.OUT)
    
    def on(self, duration = 0):
        GPIO.output(self.pin, GPIO.HIGH)
        if duration > 0:
            t = Timer(duration, self.off)
            t.start()
    
    def off(self):
        GPIO.output(self.pin, GPIO.LOW)


"""
from time import sleep
GPIO.setmode(GPIO.BCM)

channelPins = [4,17,27,22,5,6,13,19,26,21]
channels = []
for x in range(10):
    channels.append(Channel(channelPins[x]))

for x in range(4):
    channels[2].on(0.33)
    sleep(0.33)
    channels[1].on(0.16)
    sleep(0.16)
    channels[2].on(0.16)
    sleep(0.16)
    channels[0].on(0.33)
    sleep(0.33)

for y in range(5):
    for x in range(10):
        channels[x].on(0.33)
    sleep(1)
    
GPIO.cleanup()
"""