### MFP -- music for programmers 

MFP is an environment for visually composing computer programs, with
an emphasis on music and real-time audio synthesis and analysis.  It's
very much inspired by Miller Puckette's Pure Data (pd) and MAX/MSP,
with a bit of LabView and TouchOSC for good measure.  

MFP is in its early development phases.  Large pieces of core functionality
are not implemented yet, including:  undo, JACK MIDI, i18n, audio file
reading, etc etc etc.

What IS there is the basic program window and patch editor, enough
message and DSP processors to build some useful patches, a model for how
a mostly-keyboard-controlled GUI app will work, and the infrastructure
of the 3 separate processes (main, GUI, and DSP) that work together to
make MFP happen. 

### BUILDING

See README.build 

### USAGE

Try:  

    mfp -h for a command line arguments summary.  
    mfp --help-builtins lists the name and tooltip of every builtin object. 


**Hello, world:** Follow these steps to create a helloworld patch
using just the keyboard.  You do need a pointer to activate it. 

You type | What happens
---------|----------------
a | Autoplace mode.  A + appears where the next object will go
m | Create message (literal data)
"hello world" RET| Put the string "hello, world" in the message 
c | Connect mode (will connect selected object to something)
a | Autoplace mode again
p | Create a processor
print RET | Make it a [print] processor
RET | Make the connection
ESC | Enter Operate major mode 

Now click on the message box to send the "hello, world" string.  

Below the patch editing area, in the "Log" tab, you will see the message 
appear.

At any time, the "Keybindings" tab to the left of the patch editing area
will show you all the active key bindings.  Bindings nearer the top are 
chosen first, so if there are 2 listings for RET for instance the top one will
be used.

If you hover the mouse over any object, a tooltip with some
documentation will appear at the top of the canvas area.  Hold down
SHIFT to expand the tooltip to show current information about the
object, including assigned MIDI and OSC controllers. 

## KNOWN BROKEN 

There are a number of bugs that I hoped to get fixed by this
release (0.05) but have not.  Here are some that I will just have
to ask for your patience with: 

Ticket | Description 
-------| --------------
 #165 | Markup in comments does not render when patch is loaded.  Workaround: Click in another window. 
 #88 | Patch loading is slow.  Workaround: be patient.  
 #217 | MFP must be stopped with `kill -9` in (hopefully rare) error conditions. Workaround: ^Z
to stop the process from the shell, then `kill -9 %1` 
 #204 | Logging is broken when loaded as LV2 plugin 
98 | Selecting connections with click or box doesn't work well.  Workaround: Zoom in and click right on the line. 
 #212 | Rendering of smooth curves on XY plot shows gaps  

See the tickets in GitHub for detail on what I know about these problems, and for 
other potential workarounds.  

## DOCUMENTATION 

There's some documentation in the doc/ directory of this
repository.  

**LAC 2013 paper:** This paper (doc/lac2013/lac2013.pdf) gives a
high-level overview of what MFP is all about and a bit of
discussion about what it can do. 

**README files:** There are some READMEs in doc which may be
useful if you want to know more about how MFP works.  Especially
note README.lv2 which describes how MFP patches can be saved as
LV2 plugins and loaded into an LV2 host. 

**Tutorial:**  The file "tutorial.mfp" is a basic intro to
getting around the program.  

    $ mfp doc/tutorial.mfp 

It's not very complete, but it does cover a few basics about how
to create, close, and open files and make simple patches.  It also covers 
"patching patterns" for things like iteration, conditionals, etc. 

**Demo patches:** There are a few demo patches in doc/.

If your $PWD is in the doc/ directory, just run the demo patch by putting
the file name on the command line, i.e. 

    $ mfp hello_world.mfp

To run it from elsewhere, use the "-p" option to add the doc directory
to your MFP searchpath.  For example, from the top-level src
directory, 

    $ mfp -p doc hello_world.mfp


hello_world.mfp:  The classic 

simple_synth.mfp: A very basic MIDI-controlled synthesizer showing how to 
use MIDI note data and convert it to signal output.  Requires an external 
source of MIDI events, such as a keyboard or virtual keyboard, connected to the 
MFP app on its ALSA sequencer input. 

biquad_designer.mfp:  Click the "calculate" button to compute
biquad coefficients and audition them with a noise input source
(I run this into JAAA to check my calculations).  PGDN to shift
to the Graphs layer with pole/zero and analytical frequency
response.  You need to add doc/ to the patch search path for this
to load (it uses the "quadratic.mfp" patch).  From the directory
holding this README: 

    $ mfp -p doc doc/biquad_designer.mfp

oscope.mfp: Demo of the signal<-->control level bridge provided by
numpy and the buffer~ object.  A very basic oscilloscope. 

looper.mfp: A simple overdubbing loop sampler inspired by the Akai
Headrush, also built around a [buffer~].  

monomix.mfp: A demonstration of how to make a vanilla user patch with
variable numbers of inputs, determined by an init argument.  For
example, [monomix 4] makes a mixer with 4 signal inputs, 4 sliders,
and 1 signal output.  This makes use of the @clonescope method and the
concept of hygienic layer copying. 

togglegrid.mfp: Another demonstration of dynamic patch creation,
this time featuring the "grid=" argument to @clonescope which
allows dynamically-generated user interface elements to be
created with some level of control over placement.   

smix.mfp: A multichannel stereo mixer with panning and variable numbers of 
channels and aux sends per channel.  A more sophisticated version of monomix, 
using dynamic connections between objects as well as scope cloning

roll_test.mfp: Demonstrates the "roll" mode of the XY scatter
plotter, a smooth-scrolling capture mode useful for monitoring values
that are changing slowly over time

### SAVING FILES

There's no UI for saving yet, but there is a key mapping.
C-s (control-s) will prompt for a file to save in.  There's no checking for
overwrite, and the file is saved in the process working directory. 

### REPORTING PROBLEMS

I'm using the GitHub hosted issue tracker.  It seems to be pretty
workable.  

Enjoy! 

Bill Gribble <grib@billgribble.com>
