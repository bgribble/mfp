
#    alsamidi.py - Helper functions for alsaseq module
#
#   Copyright (c) 2007 Patricio Paez <pp@pp.com.mx>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>

'''Helper functions to create and store ALSA events

Helper functions for the alsaseq module.

They provide frequent MIDI event funtions that return an ALSA event ready
to be sent with the alsaseq.output() function.  A class is also provided
to read and store events in text files.

noteevent() returns an ALSA event that is always queued by alsaseq.output().

noteonevent() and noteoffevent() return ALSA events to be processed directly
without queueing by alsaseq.output().

pgmchangeevent(), pitchbendevent() and chanpress() have the optional start
parameter.  If it is omitted the returned ALSA event will be processed directly
without queueing by alsaseq.output().  If it is used, the returned ALSA event
will be queued by alsaseq.output().

All events contain queue value of 0.  This is normally overwritten by 
alsaseq.output() for scheduled events.

All start and duration times are in milliseconds.
'''

TYPE = 0; FLAGS = 1; TAG = 2; QUEUE = 3; TIMESTAMP = 4; SOURCE = 5; DEST = 6; DATA = 7
SND_SEQ_QUEUE_DIRECT = 253

import alsaseq, sys, string
from midiinstruments import *

instrnames = dict( [(int(e[0]), e[1]  ) for e in [s.split('   ') for s in strinstrnames.splitlines()]] )
drumnames  = dict( [(int(e[0]), e[1]  ) for e in [s.split('   ') for s in strdrumnames.splitlines()]] )

queue = 0

def noteevent( ch, key, vel, start, duration ):
    'Returns an ALSA event tuple to be scheduled by alsaseq.output().'
    
    return ( alsaseq.SND_SEQ_EVENT_NOTE, alsaseq.SND_SEQ_TIME_STAMP_REAL,
        0, queue, ( int( start/1000. ), int( start%1000 * 1000000 ) ),
        ( 0, 0 ), ( 0,0 ), ( ch, key, vel, 0, duration ) )

def noteonevent( ch, key, vel ):
    'Returns an ALSA event tuple to be sent directly with alsaseq.output().'

    return ( alsaseq.SND_SEQ_EVENT_NOTEON, alsaseq.SND_SEQ_TIME_STAMP_REAL,
        0, SND_SEQ_QUEUE_DIRECT, ( 0, 0),
        ( 0, 0 ), ( 0,0 ), ( ch, key, vel, 0, 0 ) )

def noteoffevent( ch, key, vel ):
    'Returns an ALSA event tuple to be sent directly with alsaseq.output().'

    return ( alsaseq.SND_SEQ_EVENT_NOTEOFF, alsaseq.SND_SEQ_TIME_STAMP_REAL,
        0, SND_SEQ_QUEUE_DIRECT, ( 0, 0),
        ( 0, 0 ), ( 0,0 ), ( ch, key, vel, 0, 0 ) )

def pgmchangeevent( ch, value, start=-1 ):
    '''Return an ALSA event tuple to be sent by alsaseq.output().
    
    If start is not used, the event will be sent directly.
    If start is provided, the event will be scheduled in a queue.'''

    if start < 0:
        return ( alsaseq.SND_SEQ_EVENT_PGMCHANGE, alsaseq.SND_SEQ_TIME_STAMP_REAL,
        0, SND_SEQ_QUEUE_DIRECT, ( 0, 0),
        ( 0, 0 ), ( 0,0 ), ( ch, 0, 0, 0, 0, value ) )
    else:
        return ( alsaseq.SND_SEQ_EVENT_PGMCHANGE, alsaseq.SND_SEQ_TIME_STAMP_REAL,
        0, queue, ( start/1000, start%1000 * 1000000),
        ( 0, 0 ), ( 0,0 ), ( ch, 0, 0, 0, 0, value ) )

def pitchbendevent( ch, value, start = -1 ):
    '''Return an ALSA event tuple to be sent by alsaseq.output().
    
    If start is not used, the event will be sent directly.
    If start is provided, the event will be scheduled in a queue.'''

    if start < 0:
        return ( alsaseq.SND_SEQ_EVENT_PITCHBEND, alsaseq.SND_SEQ_TIME_STAMP_REAL,
        0, SND_SEQ_QUEUE_DIRECT, ( start/1000, start%1000 * 1000000),
        ( 0, 0 ), ( 0,0 ), ( ch, 0, value ) )
    else:
        return ( alsaseq.SND_SEQ_EVENT_PITCHBEND, alsaseq.SND_SEQ_TIME_STAMP_REAL,
        0, queue, ( start/1000, start%1000 * 1000000),
        ( 0, 0 ), ( 0,0 ), ( ch, 0, value ) )

def chanpress( ch, value, start = -1 ):
    '''Return an ALSA event tuple to be sent by alsaseq.output().
    
    If start is not used, the event will be sent directly.
    If start is provided, the event will be scheduled in a queue.'''

    if start < 0:
        return ( alsaseq.SND_SEQ_EVENT_CHANPRESS, alsaseq.SND_SEQ_TIME_STAMP_REAL,
        0, SND_SEQ_QUEUE_DIRECT, ( start/1000, start%1000 * 1000000),
        ( 0, 0 ), ( 0,0 ), ( ch, 0, value ) )
    else:
        return ( alsaseq.SND_SEQ_EVENT_CHANPRESS, alsaseq.SND_SEQ_TIME_STAMP_REAL,
        0, queue, ( start/1000, start%1000 * 1000000),
        ( 0, 0 ), ( 0,0 ), ( ch, 0, value ) )

def tuple2time( timetuple ):
    '''Convert ( seconds, millionths ) tuple to float'''
    return timetuple[ 0 ] + timetuple[ 1 ] / 1000000000.

def time2tuple( timevalue ):
    '''Convert float time to ( seconds, millionths ) tuple'''
    return ( int( float( timevalue ) ), int( ( timevalue - int( timevalue )) * 1000000000 ) )

def modifyevent( event, timedelta=0, ch=0, dest=0, source=0, queue=0, keydelta=0 ):
    '''Returns event with one or more modified fields.
    
    Returns a list of events with the specified field(s)
    set to the value provided.
    
    timedelta  Add to time tuple.
    ch         Set MIDI channel (note and control events only).
    dest       Set destination client and port.
    source     Set source client and port.
    queue      Set queue.
    keydelta   Add to note value (noteon, noteoff and note events).

    '''
    temporal = list( event )
    if ch:
        temporal[ 7 ] = list( temporal[ 7 ] )
        temporal[ 7 ][ 0 ] = ch
    if dest:
        temporal[ DEST ] = dest
    if source:
        temporal[ SOURCE ] = source
    if queue:
        temporal[ QUEUE ] = queue
    if timedelta:
        temporal[ 4 ] = time2tuple( tuple2time( temporal[ 4 ] ) + timedelta )
    if keydelta and event[0] in [ 5, 6, 7]:
        data = list( temporal[ 7 ] )
        data[ 1 ] = data[ 1 ] + keydelta
        temporal[ 7 ] = data
    temporal[ 7 ] = tuple( temporal[ 7 ] )
    return tuple( temporal )

def modifyevents( events, timedelta=0, ch=0, dest=0, source=0, queue=0, keydelta=0 ):
    '''Modifies one or more fields in a list of events.'''
    modifiedevents = []
    for event in events:
        modifiedevents.append( modifyevent( event, timedelta, ch, 
        dest, source, queue, keydelta ) )
    return modifiedevents


def bytimestamp( a, b ):
    return cmp( a[4], b[4] )

def merge( tracks ):
    'Return one or more tracks joined and sorted into a single track.'
    singletrack = []
    for track in tracks:
        singletrack.extend( track )
    singletrack.sort( bytimestamp ) # order by timestamp
    return singletrack

def uniquenotes( events ):
    'Returns list of unique note values for each MIDI channel in events.'
    channels = {}
    notes = []
    for event in events:
        if event[ TYPE ] in [ 5,6,7 ]:
            channel = event[ DATA ][ 0 ]
            if channel not in channels:
                channels[ channel ] = []
            channels[ channel ].append( event[ DATA ][1] )
    for channel in list(channels.keys()):
        notes = list( set( channels[ channel ] ) )
        notes.sort()
        channels[ channel ] = notes
    return channels


class Seq:
    '''Read and write event tracks in ALSACSV files.
    
    ALSACSV is a text format for storing ALSA events.'''

    def __init__( self ):
        self.names = []
        self.tracks = []
        self.tags = []

    def info( self ):
        'Return info about Seq: tracks, header, instr.'
        names = self.names
        tracks = self.tracks
        tags = self.tags
        names = names + ['track'] * ( len(tracks) - len(names) )
        if tags: print(tags)
        for i, track in enumerate( tracks ):
          if track:
            inicio = track[ 0 ][ 4 ][ 0 ]
            final = track[ -1 ][ 4 ][ 0 ]
            druminsts = []
            if list(uniquenotes( track ).keys()) == [9]:
                for drumnumber in uniquenotes( track )[9]:
                    druminsts.append( drumnames[ int(drumnumber) ] )
            print(str(i) + ':', names[i].ljust( 15 ), final - inicio, 'Sec.', len(track), 'events,', uniquenotes( track ), ','.join( druminsts ))

    def read( self, path ):
        'Read data from ALSACSV file.'
        names = []
        tracks = []
        tags = {}
        orderedtags = []
        try:
            f = open( path )
            for line in f.readlines():
              if line[-1] == '\n': line = line[ :-1 ]
              if '=' in line:
                variable, valor = list(map( string.strip, line.split( '=' ) ))
                tags[ variable ] = valor
                orderedtags.append( variable )
              elif 'track' in line:
                names.append( line )
                tracks.append( [] )
              elif line:
                if not tracks:
                    tracks.append( [] )
                    names.append( 'Default' )
                campos = []
                for c in line.split( ',' ):
                    try:
                        campos.append( int(c) )
                    except:
                        campos.append( tuple( map( int, c.split() ) ) )
                tracks[ -1 ].append( tuple( campos ) )
        except:
            print('Error reading file', path)
            print(sys.exc_info()[1])
        self.names = names
        self.tracks = tracks
        self.tags = tags
        self.orderedtags = orderedtags

    def write( self, path ):
        'Write the tracks to ALSACSV file.'
        try:
            f = open( path, 'w' )
            tags = self.tags
            names = self.names
            if tags:
                for tag in self.orderedtags:
                    f.write( tag + '=' + tags[ tag ] + '\n' )
            for track in self.tracks:
                names = names + [''] * ( len(self.tracks) - len(names) )
                name = names[ self.tracks.index( track ) ]
                if name:
                    f.write( name + '\n' )
                else:
                    f.write( 'track\n' )
                for event in track:
                    l = []
                    for field in event:
                        if isinstance( field, int ):
                            l.append( str( field ) )
                        else:
                            l.append( ' '.join( map( str, field )) )
                    f.write( ','.join( l ) + '\n' )
        except:
            print('Error saving file', path)
            print(sys.exc_info()[1])

