..    project.rst
..
..    Copyright (c) 2009 Patricio Paez <pp@pp.com.mx>
..
..    This program is free software; you can redistribute it and/or modify
..    it under the terms of the GNU General Public License as published by
..    the Free Software Foundation; either version 2 of the License, or
..    (at your option) any later version.
..
..    This program is distributed in the hope that it will be useful,
..    but WITHOUT ANY WARRANTY; without even the implied warranty of
..    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
..    GNU General Public License for more details.
..
..    You should have received a copy of the GNU General Public License
..    along with this program.  If not, see <http://www.gnu.org/licenses/>

alsaseq – ALSA sequencer bindings for Python 
============================================

*alsaseq* is a Python 3 and Python 2 module that allows to interact with ALSA
sequencer clients. It can create an ALSA client, connect to other
clients, send and receive ALSA events immediately or at a scheduled
time using a sequencer queue. It provides a subset of the ALSA
sequencer capabilities in a simplified model. It is implemented in
C language and licensed under the Gnu GPL license version 2 or
later.

The project is available at http://pp.com.mx/python/alsaseq

.. Contents::
   :depth: 1

Requirements
~~~~~~~~~~~~

The Python and the ALSA development header files, as well as the GNU C compiler
are needed to compile the module. If you use Debian or a distribution derived
from Debian like Ubuntu, make sure that the **python-dev** (for Python 2),
**python3-dev** (for Python 3), **libasound2-dev** and **gcc** packages are
installed. If you use Mandriva, check that the **libpython2.6-devel** (for Python 2),
**libpython3.1-devel** (for Python 3),  **libalsa2-devel** and **gcc** packages
are installed.


Installation
~~~~~~~~~~~~

Download the latest alsaseq.tar.gz file into a directory::

 $ wget http://pp.com.mx/python/alsaseq/alsaseq-<version>.tar.gz

Extract the contents::

 $ tar xf alsaseq-<version>.tar.gz 

Enter the folder alsaseq-<version> that was created::

 $ cd alsaseq-<version> 

To compile the module::

 $ python setup.py build

To install the module, execute as root:: 
 
 # python setup.py install

To test::

 $ python -c 'import alsaseq, alsamidi'

For python 3, the last three commands should be::

 $ python3 setup.py build

 # python3 setup.py install

 $ python3 -c 'import alsaseq, alsamidi'

It is possible to build and install the module for both Python 2 and 3, both
versions can coexist in the same system.

Interactive use
~~~~~~~~~~~~~~~

Create an ALSA sequencer client with one input port and one output
port, no queue::

 >>> import alsaseq 
 >>> alsaseq.client( 'Simple', 1, 1, False ) 

Port 0 is input, port 1 is output. Connect ALSA client 129 (could
be a musical keyboard or Virtual Keyboard) to the input port, and
connect output port to ALSA client 130 (a MIDI to sound converter
like Timidity)::

 >>> alsaseq.connectfrom( 0, 129, 0 ) 
 >>> alsaseq.connectto( 1, 130, 0 )

Check if there are events in the input port due to notes played in
the MIDI keyboard::

 >>> alsaseq.inputpending()
 2 

Read and display an ALSA event::

 >>> alsaseq.input() 
 (6, 1, 0, 253, (0, 0), (0, 0), (0, 0), (0, 60, 127, 0, 0))

ALSA events are tuples with 8 elements: (type, flags, tag, queue,
time stamp, source, destination, data). In a client without queue,
received events have no time information and are asigned dummy
queue number 253.

Save a received event to send it for immediate processing::

 >>> event = alsaseq.input()
 >>> alsaseq.output( event )

In a client with createqueue = True, you first start the queue in
order to schedule events for execution at a certain time: 

In order to time stamp received events and to schedule output
events for execution at a certain time, specify the client with
createqueue = True, and start the queue::

 >>> alsaseq.client( 'Simple', 1, 1, True )
 >>> alsaseq.start() 
 >>> alsaseq.output( (6, 1, 0, 1, (5, 0), (0, 0), (0, 0), (0, 60, 127, 0, 100)) ) 

The above output() schedules a C note at 5 seconds after the
start() command, for a duration of 100ms.
::

    >>> alsaseq.input() 
    (6, 1, 0, 1, ( 12, 125433), (0, 0), (0, 0), (0, 62, 120, 0, 100))) 

The above ALSA event was received in the input port 12 seconds and
123,433 millionths after the start() command. You can view the
status ( running, stopped ) of que queue, the current time, and the
number of events queued for output. You may also stop the queue::

 >>> alsaseq.status() 
 ( 1, ( 20, 546234 ), 0 ) 
 >>> alsaseq.stop() 

The status() shows the queue as running at 20 seconds, 546,234
millionths, with no events scheduled for output. 

ALSA events for common MIDI events can be created using helper
functions in alsamidi module::

 >>> alsamidi.noteevent( 1, 60, 120, 5000, 10 )
 (5, 1, 0, 0, (5, 0), (0, 0), (0, 0), (1, 60, 120, 0, 10))

 See help( alsamidi ) or pydoc( alsamidi ) for more information. 


Examples
~~~~~~~~

In these example scripts it is assumed that client 129 is a MIDI
keyboard, clients 130 and 131 are MIDI sound generation modules. 

MIDI through
^^^^^^^^^^^^
::

    import alsaseq 
    alsaseq.client( 'MIDI through', 1, 1, False ) 
    alsaseq.connectfrom( 1, 129, 0 ) 
    alsaseq.connectto( 0, 130, 0 ) 

    while 1: 
        if alsaseq.inputpending():
        ev = alsaseq.input()
        alsaseq.output( ev )

Press control + c to interrupt the loop. 

MIDI router
^^^^^^^^^^^
::

    import alsaseq 
    alsaseq.client( 'Router', 1, 2, False ) 
    alsaseq.connectfrom( 1, 129, 0 ) 
    alsaseq.connectto( 0, 130, 0 ) 
    alsaseq.connectto( 0, 131, 0 ) 

    while 1: 
        if alsaseq.inputpending():
           ev = list( alsaseq.input() )
           if ev[7][1] > 60: # if note is above C split limit,
               ev[5][0] = 2, # use second output port
           alsaseq.output( ev )
 
Press control + c to interrupt the loop. 

Recorder
^^^^^^^^
::

    import alsaseq, pickle 
    alsaseq.client( 'Recorder', 1, 0, True ) 
    alsaseq.connectfrom( 1, 129, 0 ) 
    alsaseq.start() 
    events = []

    while 1: 
      if alsaseq.inputpending():
      event = alsaseq.input()
      if event[7][1] == 56: # if note is central G#
        break # quit recording
      events.append( ev )

    pickle.dump( events, open( 'events.seq', 'w' ) ) 

Player
^^^^^^
::

    import alsaseq, pickle 
    events = pickle.load( open( ruta ) ) 
    alsaseq.client( 'Player', 0, 1, True ) 
    alsaseq.connectto( 0, 130, 0 ) 
    alsaseq.start()

    for event in events:
      alsaseq.output( event )


Appendix
~~~~~~~~

Manually build and install
^^^^^^^^^^^^^^^^^^^^^^^^^^

This is just provided for informational purposes, in case the setup.py
does not work or just for fun.  The following commands assume that Python 2.6
or Python 3.1 are installed; adjust the paths if a different version is used.

To compile the module::

 $ gcc -shared -Wall -I /usr/include/python2.6 -lasound -o alsaseq.so alsaseq.c

To install the module, copy the **alsaseq.so**, **alsamidi.py** and 
**midiinstruments.py** files to
/usr/local/lib/python2.6 as root::

 # install alsaseq.so alsamidi.py midiinstruments.py /usr/local/lib/python2.6/site-packages

For Python 3::

 $ gcc -shared -I /usr/include/python3.1 -lasound -o alsaseq.so alsaseq.c

 # install alsaseq.so alsamidi.py midiinstruments.py /usr/local/lib/python3.1/site-packages

Recommendations about MIDI software and hardware
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To hear notes played by the ALSA sequencer while being controlled
by alsaseq,
you will need a software sound renderer like Timidity, which you
can install from the **timidity** package in most distributions.
To input notes to the ALSA sequencer and read them with alsaseq
you may use a virtual keyboard like **vkeybd**, available from
a package with the same name.

If you have a MIDI keyboard or piano and/or a hardware MIDI sound
module, you may connect them to your PC using a *USB-to-MIDI interface*.
I use the **MIDI 1x1**  from *E-EMU* and the **MIDIsport UNO**
from *M-AUDIO* which work fine.


.. |date| date::
.. |time| date:: %H:%M

Document generated on |date| at |time| CST.

