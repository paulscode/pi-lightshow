from omxplayer.player import OMXPlayer
from pathlib import Path
from time import sleep
from threading import Thread

class Player:
    def __init__(self, path, endCallback = None, syncCallback = None):
        self.player = False
        self.finished = False
        self.path = Path( path )
        self.syncCallback = syncCallback
        self.endCallback = endCallback
        self.musicThread = Thread( target = self.play )
        self.musicThread.start()

    def play(self):
        self.player = OMXPlayer( self.path, args = "-o local" )
        self.player.exitEvent = self.exitEvent
        self.player.stopEvent = self.stopEvent
        while not self.finished:
            sleep( 0.5 )
            if self.syncCallback and not self.finished:
                self.syncCallback( self.player.position() )
        self.player.quit()

    def stop(self):
        if self.player != False:
            self.player.quit()

    def position(self):
        if self.player != False:
            return self.player.position()
        return -1

    def exitEvent(self, player, exit_status):
        self.finished = True
        if self.endCallback:
            self.endCallback()

    def stopEvent(self, player):
        self.finished = True
        if self.endCallback:
            self.endCallback()





"""
def syncCb( position ):
    print ("Position " + str(position))

def endCb():
    print ("END")

player = Player( "/home/pi/lightshow/madrussian.mp3", endCb, syncCb )
# player = Player( "/home/pi/lightshow/carol.mp3" )

input( "Press Enter to quit" )
player.stop()
"""
