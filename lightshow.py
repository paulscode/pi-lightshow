from RPi import GPIO
from time import sleep
from threading import Timer

from player import Player
from channel import Channel

mainStart = 33.078
mainTempo = 0.96616875
mainTotalBeats = 161
mainCurrentBeat = 0

GPIO.setmode(GPIO.BCM)

channelPins = [4,17,27,22,5,6,13,19,26,21]
channels = []
for x in range(10):
    channels.append(Channel(channelPins[x]))
for x in range(10):
    channels[x].off()

started = False
finished = False
def syncCb( position ):
    global started, player, mainStart, mainBeat
    if not started:
        t = Timer((mainStart - position), mainBeat)
        t.start()
        started = True
        player.syncCallback = None
        print ("START: position " + str(position))

def endCb():
    print ("END")
    finished = True;

def mainBeat():
    global mainBeat, player, mainStart, mainTempo, mainTotalBeats, mainCurrentBeat, channels
    if finished:
        return True
    mainCurrentBeat = mainCurrentBeat + 1
    if( mainCurrentBeat < mainTotalBeats ):
        nextBeat = mainStart + (mainCurrentBeat * mainTempo)
        position = player.position()
        duration = nextBeat - position
        if( duration < 0 ):
            duration = 0
        t = Timer( duration, mainBeat )
        t.start()
    for x in range(10):
        channels[x].on(0.25)
    return True

player = Player( "/home/pi/pi-lightshow/carol.mp3", endCb, syncCb )

input( "Press Enter to quit" )
player.stop()
GPIO.cleanup()
