from RPi import GPIO
from time import sleep
from threading import Timer
from random import randint

from player import Player
from channel import Channel

preludeStart = 0.3494857143
preludeTempo = 0.7365142857
preludeTotalBeats = 37
preludeCurrentBeat = 0

mainStart = 33.078
mainTempo = 0.96616875
mainTotalBeats = 175
mainCurrentBeat = 0

GPIO.setmode( GPIO.BCM )

channelPins = [17,27,22,13,19,26,21,20,16,12]
channels = []
for x in range(10):
    channels.append( Channel( channelPins[x] ) )
for x in range(10):
    channels[x].off()

started = False
preludeFinished = False
mainFinished = False
finished = False
def syncCb( position ):
    global started, player, preludeStart, preludeBeat, mainStart, mainBeat
    if not started:
        t1 = Timer( ( preludeStart - position ), preludeBeat )
        t2 = Timer( ( mainStart - position ), mainBeat )
        t1.start()
        t2.start()
        started = True
        player.syncCallback = None

def endCb():
    preludeFinished = True;
    mainFinished = True;
    finished = True;

def preludeBeat():
    global preludeFinished, preludeBeat, player, preludeStart, preludeTempo, preludeTotalBeats, preludeCurrentBeat, channels
    if preludeFinished:
        return True
    preludeCurrentBeat = preludeCurrentBeat + 1
    nextBeat = preludeStart + ( preludeCurrentBeat * preludeTempo )
    position = player.position()
    delay = nextBeat - position
    if( delay < 0 ):
        delay = 0
    if( preludeCurrentBeat == preludeTotalBeats - 2 ):
        # Final "God rest ye mer.." starting at normal tempo
        playNote( 3, preludeTempo * 0.5, preludeTempo * 0.33 )
        playNote( 2, preludeTempo, preludeTempo * 0.33 )
        playNote( 0, preludeTempo * 1.5, preludeTempo * 0.33 )
        playNote( 0, preludeTempo * 2, preludeTempo * 0.33 )
    elif( preludeCurrentBeat >= preludeTotalBeats ):
        preludeFinished = True
        # Last three measures of prelude are at a slowing tempo
        playNote( 5, 0.478, 0.351 )
        playNote( 6, 0.829, 0.518 )
        playNote( 1, 1.347, 0.569 )
        playNote( 6, 1.916, 0.62 )
        playNote( 5, 2.536, 2.5 )
        # Slowing down: "..ry gentlemen let"
        playNote( 2, 0.478, 0.351 )
        playNote( 3, 0.829, 0.518 )
        playNote( 7, 1.347, 0.569 )
        playNote( 4, 1.916, 0.5 )
        playNote( 4, 2.536, 2.5 )

    t = Timer( delay, preludeBeat )
    t.start()
        
    if( preludeCurrentBeat == 1 ):
        # First note is at the end of the first measure
        playNote( 5, preludeTempo * 0.5, preludeTempo * 0.5 )
    elif( ( preludeCurrentBeat % 2 ) == 0 ):
        # Background phrase repeats every two measures
        playPhrase( 0, preludeTempo )
    if( preludeCurrentBeat in [9, 23, 27, 31] ):
        # "God rest ye merry gentlemen" repeats four times
        playPhrase( 1, preludeTempo )
    if( preludeCurrentBeat == 13 ):
        # "Let nothing you dismay" is played by itself only once
        playPhrase( 2, preludeTempo )
    return True

def mainBeat():
    global mainFinished, mainBeat, player, mainStart, mainTempo, mainTotalBeats, mainCurrentBeat, channels
    if mainFinished:
        return True
    mainCurrentBeat = mainCurrentBeat + 1
    print( "M" + str( mainCurrentBeat ) )
    if( mainCurrentBeat < mainTotalBeats ):
        nextBeat = mainStart + ( mainCurrentBeat * mainTempo )
        position = player.position()
        delay = nextBeat - position
        if( delay < 0 ):
            delay = 0
        if( mainCurrentBeat >= mainTotalBeats ):
            mainFinished = True
        t = Timer( delay, mainBeat )
        t.start()
    if( mainCurrentBeat in [45, 141, 142, 143, 144, 145, 146, 147, 148, 157, 158, 159, 160, 165] ):
        # Pulse all channels
        for x in range( 10 ):
            channels[x].on( 0.25 )
    if( mainCurrentBeat in [8, 16, 64, 68, 72, 76, 80, 84] ):
        # Uneven "God rest ye merry gentlemen"
        playPhrase( 3, mainTempo )
    if( mainCurrentBeat in [9, 17, 73, 77, 81, 85, 97, 101, 105, 109] ):
        # Carol of the bells, "ding, dong, ding, dong"
        playPhrase( 4, mainTempo )
    if( mainCurrentBeat in [25, 26, 27, 28, 29, 30, 31, 32, 61, 62, 63, 64, 73, 105, 106, 107, 108, 109, 110, 111, 112, 121, 122, 123, 124, 125, 126, 127, 128, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175] ):
        # Carol of the bells, repeating theme
        playPhrase( 5, mainTempo )
    if( mainCurrentBeat in [29, 30, 31, 32] ):
        # Carol of the bells, repeating theme, dual notes
        playPhrase( 6, mainTempo )
    if( mainCurrentBeat in [33, 113, 129] ):
        # Carol of the bells, "gaily they ring"
        playPhrase( 7, mainTempo )
    if( mainCurrentBeat in [34, 114, 130] ):
        # Carol of the bells, "while people sing"
        playPhrase( 8, mainTempo )
    if( mainCurrentBeat in [35, 115, 131] ):
        # Carol of the bells, "songs of good cheer"
        playPhrase( 9, mainTempo )
    if( mainCurrentBeat in [36, 116, 132] ):
        # Carol of the bells, "Christmas is here"
        playPhrase( 10, mainTempo )
    if( mainCurrentBeat in [37, 39, 41, 42, 43, 44, 117, 119, 133, 135] ):
        # Carol of the bells, "merry, merry, merry.."
        playPhrase( 11, mainTempo )
    if( mainCurrentBeat in [38, 40, 118, 120, 134, 136, 137, 138, 139, 140] ):
        # Carol of the bells, "..merry Christmas"
        playPhrase( 12, mainTempo )
    if( mainCurrentBeat in [1, 2, 3, 4, 5, 6, 7, 8, 9, 13, 14, 15, 16, 21, 22, 23, 24, 89, 90, 91, 92, 93, 94, 95, 96] ):
        # Pulsing base
        playPhrase( 13, mainTempo )
    if( mainCurrentBeat in [44, 48, 52, 56] ):
        # Descent, part 1
        playPhrase( 14, mainTempo )
    if( mainCurrentBeat in [47, 51, 55, 59] ):
        # Descent, part 2
        playPhrase( 15, mainTempo )
    if( mainCurrentBeat in [161, 162, 163, 164] ):
        # Random notes
        playPhrase( 15, mainTempo )
    if( mainCurrentBeat in [149, 151, 153, 155] ):
        stepDown( mainTempo )
    if( mainCurrentBeat in [150, 152, 154, 156] ):
        stepUp( mainTempo )
        
    return True

def playNote( channel, delay, duration ):
    global channels
    t = Timer( delay, channels[channel].on, [duration] )
    t.start()
    return True

def randomNotes( tempo ):
    for x in range( 10 ):
        if( x == 0 ):
            channels[randint( 0, 9 )].on( tempo * 0.1 )
        else:
            t = Timer( tempo * 0.1 * float( x ), channels[randint( 0, 9 )].on, [tempo * 0.1] )
            t1.start()
    return True

def stepUp( tempo ):
    # light up all lights in order
    order = [9, 8, 1, 6, 5, 3, 2, 4, 7, 0]
    for x in range( 10 ):
        if( x == 0 ):
            channels[order[x]].on( tempo )
        else:
            t = Timer( tempo * 0.1 * float( x ), channels[order[x]].on, [tempo * (float(10 - x ) / 10.0)] )
            t.start()
    return True

def stepDown( tempo ):
    # turn off all lights in reverse order
    order = [0, 7, 4, 2, 3, 5, 6, 2, 8, 9]
    for x in range( 10 ):
        channels[order[x]].on( tempo * 0.1 * (float( x ) + 1) )
    return True

def playPhrase( phrase, tempo ):
    global channels
    if( phrase == 0 ):
        # Four notes that repeat at the beginning of the song
        channels[6].on( tempo * 0.5 )
        t1 = Timer( tempo * 0.5, channels[1].on, [tempo * 0.5] )
        t2 = Timer( tempo, channels[6].on, [tempo * 0.5] )
        t3 = Timer( tempo * 1.5, channels[5].on, [tempo * 0.5] )
        t1.start()
        t2.start()
        t3.start()
    elif( phrase == 1 ):
        # "Got rest ye merry gentlemen"
        t1 = Timer( tempo * 0.5, channels[3].on, [tempo * 0.33] )
        t2 = Timer( tempo, channels[2].on, [tempo * 0.33] )
        t3 = Timer( tempo * 1.5, channels[0].on, [tempo * 0.33] )
        t4 = Timer( tempo * 2, channels[0].on, [tempo * 0.33] )
        t5 = Timer( tempo * 2.5, channels[2].on, [tempo * 0.33] )
        t6 = Timer( tempo * 3, channels[3].on, [tempo * 0.33] )
        t7 = Timer( tempo * 3.5, channels[7].on, [tempo * 0.33] )
        t8 = Timer( tempo * 4, channels[4].on, [tempo * 0.33] )
        t1.start()
        t2.start()
        t3.start()
        t4.start()
        t5.start()
        t6.start()
        t7.start()
        t8.start()
    elif( phrase == 2 ):
        # "Let nothing you dismay"
        t1 = Timer( tempo * 0.5, channels[4].on, [tempo * 0.33] )
        t2 = Timer( tempo, channels[7].on, [tempo * 0.33] )
        t3 = Timer( tempo * 1.5, channels[3].on, [tempo * 0.33] )
        t4 = Timer( tempo * 2, channels[2].on, [tempo * 0.33] )
        t5 = Timer( tempo * 2.5, channels[0].on, [tempo * 0.33] )
        t6 = Timer( tempo * 3, channels[9].on, [tempo * 2] )
        t1.start()
        t2.start()
        t3.start()
        t4.start()
        t5.start()
        t6.start()
    elif( phrase == 3 ):
        # Uneven "God rest ye merry gentlemen"
        t1 = Timer( tempo * 0.66, channels[3].on, [tempo * 0.25] )
        t2 = Timer( tempo, channels[2].on, [tempo * 0.25] )
        t3 = Timer( tempo * 1.66, channels[0].on, [tempo * 0.25] )
        t4 = Timer( tempo * 2, channels[0].on, [tempo * 0.25] )
        t5 = Timer( tempo * 2.66, channels[2].on, [tempo * 0.25] )
        t6 = Timer( tempo * 3, channels[3].on, [tempo * 0.25] )
        t7 = Timer( tempo * 3.66, channels[7].on, [tempo * 0.25] )
        t8 = Timer( tempo * 4, channels[4].on, [tempo * 0.25] )
        t1.start()
        t2.start()
        t3.start()
        t4.start()
        t5.start()
        t6.start()
        t7.start()
        t8.start()
    elif( phrase == 4 ):
        # Carol of the bells, "ding, dong, ding, dong"
        channels[8].on( tempo )
        t1 = Timer( tempo, channels[1].on, [tempo] )
        t2 = Timer( tempo * 2, channels[6].on, [tempo] )
        t3 = Timer( tempo * 3, channels[5].on, [tempo * 2] )
        t1.start()
        t2.start()
        t3.start()
    elif( phrase == 5 ):
        # Carol of the bells, repeating theme
        channels[0].on( tempo * 0.166 )
        t1 = Timer( tempo * 0.33, channels[2].on, [tempo * 0.2] )
        t2 = Timer( tempo * 0.5, channels[0].on, [tempo * 0.2] )
        t3 = Timer( tempo * 0.66, channels[3].on, [tempo * 0.2] )
        t1.start()
        t2.start()
        t3.start()
    elif( phrase == 6 ):
        # Carol of the bells, repeating theme, dual notes
        channels[1].on( tempo * 0.166 )
        t1 = Timer( tempo * 0.33, channels[6].on, [tempo * 0.2] )
        t2 = Timer( tempo * 0.5, channels[1].on, [tempo * 0.2] )
        t3 = Timer( tempo * 0.66, channels[5].on, [tempo * 0.2] )
        t1.start()
        t2.start()
        t3.start()
    elif( phrase == 7 ):
        # Carol of the bells, "gaily they ring"
        channels[8].on( tempo * 0.166 )
        t1 = Timer( tempo * 0.33, channels[8].on, [tempo * 0.1] )
        t2 = Timer( tempo * 0.5, channels[8].on, [tempo * 0.166] )
        t3 = Timer( tempo * 0.66, channels[1].on, [tempo * 0.166] )
        t4 = Timer( tempo * 0.83, channels[6].on, [tempo * 0.166] )
        t1.start()
        t2.start()
        t3.start()
        t4.start()
    elif( phrase == 8 ):
        # Carol of the bells, "while people sing"
        channels[5].on( tempo * 0.166 )
        channels[0].on( tempo * 0.166 )
        t1 = Timer( tempo * 0.33, channels[5].on, [tempo * 0.1] )
        t2 = Timer( tempo * 0.33, channels[0].on, [tempo * 0.1] )
        t3 = Timer( tempo * 0.5, channels[5].on, [tempo * 0.166] )
        t4 = Timer( tempo * 0.5, channels[0].on, [tempo * 0.166] )
        t5 = Timer( tempo * 0.66, channels[3].on, [tempo * 0.166] )
        t6 = Timer( tempo * 0.66, channels[2].on, [tempo * 0.166] )
        t7 = Timer( tempo * 0.83, channels[4].on, [tempo * 0.166] )
        t8 = Timer( tempo * 0.83, channels[7].on, [tempo * 0.166] )
        t1.start()
        t2.start()
        t3.start()
        t4.start()
        t5.start()
        t6.start()
        t7.start()
        t8.start()
    elif( phrase == 9 ):
        # Carol of the bells, "songs of good cheer"
        channels[3].on( tempo * 0.166 )
        channels[2].on( tempo * 0.166 )
        t1 = Timer( tempo * 0.33, channels[3].on, [tempo * 0.1] )
        t2 = Timer( tempo * 0.33, channels[2].on, [tempo * 0.1] )
        t3 = Timer( tempo * 0.5, channels[3].on, [tempo * 0.166] )
        t4 = Timer( tempo * 0.5, channels[2].on, [tempo * 0.166] )
        t5 = Timer( tempo * 0.66, channels[5].on, [tempo * 0.166] )
        t6 = Timer( tempo * 0.66, channels[0].on, [tempo * 0.166] )
        t7 = Timer( tempo * 0.83, channels[3].on, [tempo * 0.166] )
        t8 = Timer( tempo * 0.83, channels[2].on, [tempo * 0.166] )
        t1.start()
        t2.start()
        t3.start()
        t4.start()
        t5.start()
        t6.start()
        t7.start()
        t8.start()
    elif( phrase == 10 ):
        # Carol of the bells, "Christmas is here"
        channels[4].on( tempo * 0.166 )
        channels[7].on( tempo * 0.166 )
        t1 = Timer( tempo * 0.33, channels[4].on, [tempo * 0.1] )
        t2 = Timer( tempo * 0.33, channels[7].on, [tempo * 0.1] )
        t3 = Timer( tempo * 0.5, channels[4].on, [tempo * 0.1] )
        t4 = Timer( tempo * 0.5, channels[7].on, [tempo * 0.1] )
        t5 = Timer( tempo * 0.66, channels[4].on, [tempo * 0.166] )
        t6 = Timer( tempo * 0.66, channels[7].on, [tempo * 0.166] )
        t1.start()
        t2.start()
        t3.start()
        t4.start()
        t5.start()
        t6.start()
    elif( phrase == 11 ):
        # Carol of the bells, "merry, merry, merry.."
        channels[7].on( tempo * 0.166 )
        t1 = Timer( tempo * 0.166, channels[4].on, [tempo * 0.166] )
        t2 = Timer( tempo * 0.33, channels[2].on, [tempo * 0.166] )
        t3 = Timer( tempo * 0.5, channels[3].on, [tempo * 0.166] )
        t4 = Timer( tempo * 0.66, channels[0].on, [tempo * 0.166] )
        t5 = Timer( tempo * 0.833, channels[5].on, [tempo * 0.166] )
        t1.start()
        t2.start()
        t3.start()
        t4.start()
        t5.start()
    elif( phrase == 12 ):
        # Carol of the bells, "..merry Christmas"
        channels[6].on( tempo * 0.166 )
        t1 = Timer( tempo * 0.166, channels[1].on, [tempo * 0.166] )
        t2 = Timer( tempo * 0.33, channels[6].on, [tempo * 0.33] )
        t3 = Timer( tempo * 0.66, channels[5].on, [tempo * 0.33] )
        t1.start()
        t2.start()
        t3.start()
    elif( phrase == 13 ):
        # Pulsing base
        for x in range( 10 ):
            channels[x].on( 0.166 )
        t1 = Timer( tempo * 0.33, channels[8].on, [tempo * 0.1] )
        t2 = Timer( tempo * 0.33, channels[9].on, [tempo * 0.1] )
        t3 = Timer( tempo * 0.5, channels[8].on, [tempo * 0.1] )
        t4 = Timer( tempo * 0.5, channels[9].on, [tempo * 0.1] )
        t5 = Timer( tempo * 0.66, channels[8].on, [tempo * 0.1] )
        t6 = Timer( tempo * 0.66, channels[9].on, [tempo * 0.1] )
        t7 = Timer( tempo * 0.833, channels[8].on, [tempo * 0.1] )
        t8 = Timer( tempo * 0.833, channels[9].on, [tempo * 0.1] )
        t1.start()
        t2.start()
        t3.start()
        t4.start()
        t5.start()
        t6.start()
        t7.start()
        t8.start()
    elif( phrase == 14 ):
        # Descent, part 1
        t1 = Timer( tempo * 0.66, channels[9].on, [tempo * 0.166] )
        t2 = Timer( tempo, channels[9].on, [tempo * 0.33] )
        t3 = Timer( tempo * 1.33, channels[8].on, [tempo * 0.33] )
        t4 = Timer( tempo * 1.66, channels[1].on, [tempo * 0.33] )
        t5 = Timer( tempo * 2, channels[1].on, [tempo * 0.33] )
        t6 = Timer( tempo * 2.33, channels[6].on, [tempo * 0.33] )
        t7 = Timer( tempo * 2.66, channels[5].on, [tempo * 0.33] )
        t1.start()
        t2.start()
        t3.start()
        t4.start()
        t5.start()
        t6.start()
        t7.start()
    elif( phrase == 15 ):
        # Descent, part 2
        channels[6].on( tempo * 0.33 )
        t1 = Timer( tempo * 0.33, channels[5].on, [tempo * 0.33] )
        t2 = Timer( tempo, channels[2].on, [tempo * 0.33] )
        t3 = Timer( tempo, channels[3].on, [tempo * 0.33] )
        t4 = Timer( tempo * 1.33, channels[2].on, [tempo * 0.33] )
        t5 = Timer( tempo * 1.33, channels[3].on, [tempo * 0.33] )
        t6 = Timer( tempo * 1.66, channels[4].on, [tempo * 0.33] )
        t7 = Timer( tempo * 1.66, channels[7].on, [tempo * 0.33] )
        t8 = Timer( tempo * 2, channels[0].on, [tempo * 0.166] )
        t9 = Timer( tempo * 2.33, channels[0].on, [tempo * 0.1] )
        t1.start()
        t2.start()
        t3.start()
        t4.start()
        t5.start()
        t6.start()
        t7.start()
        t8.start()
        t9.start()
        
    return True

player = Player( "/home/pi/pi-lightshow/carol.mp3", endCb, syncCb )

input( "Press Enter to quit" )
player.stop()
GPIO.cleanup()
