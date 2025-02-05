### MFP -- music for programmers

MFP is an environment for visually composing computer programs, with
an emphasis on music and real-time audio synthesis and analysis.  It's
very much inspired by Miller Puckette's Pure Data (pd) and MAX/MSP,
with a bit of LabView and TouchOSC for good measure.

Development of MFP has been ambling along at a part-time pace for
several years now.  It's by no means "1.0" but definitely there's
enough there that I use it in my own music-making.  As of now
it's pretty much a solo project but I welcome any feedback,
questions, or pull requests.

**What's happening now?** I am working on MFP pretty actively.
The main branch currently contains a WIP backend that uses [Dear
ImGUI](https://github.com/ocornut/imgui) for the UI, via the
excellent [imgui-bundle](https://github.com/pthom/imgui_bundle)
bindings. The ImGUI UI is now the default; to use the old Clutter
UI, be sure to build with it (see README.build) and launch with
the option `--gui-backend=clutter`.

The new UI looks quite a bit different. It's more like Max in the
visual presentation of patches and the addition of a right-side
parameter editing panel. It's already better than the Clutter UI
in important ways. Some big differences:

* A tiled patch display area, to allow multiple patches to be
  viewed/edited at once
* A menu bar that should reflect most available actions, and a
  popup context menu for the current selection
* Ability to directly edit object parameters and style in the
  "Info" panel
* Better plot support via
  [ImPlot](https://github.com/epezent/implot)

The most recent release (0.7) is the last release that will
exclusively support Gtk/Clutter for the UI. I will release 0.8 when I
feel that the Dear Imgui backend is at parity with the Clutter backend,
and then 0.9 will likely remove the Clutter backend.

### BUILDING

See README.build

### USAGE

Try:

    mfp -h for a command line arguments summary.
    mfp --help-builtins lists the name and tooltip of every builtin object.


**Hello, world:** Follow these steps to create a helloworld patch
using just the keyboard.  

You type | What happens
---------|----------------
a | Autoplace mode.  A symbol appears where the next object will go
m | Create message (literal data)
"hello world" RET| Put the string "hello, world" in the message
c | Connect mode (will connect selected object to something)
a | Autoplace mode again
p | Create a processor
print RET | Make it a [print] processor
RET | Make the connection
ESC | Enter Operate major mode
TAB | Select the message box
RET | Activate the message box

Below the patch editing area, in the "Log" tab, you will see the message
appear.

Clutter backend: the "Keybindings" tab to the left of the patch
editing area will show you all the active key bindings. If you
hover the mouse over any object, a tooltip with some
documentation will appear at the top of the canvas area.  Hold
down SHIFT to expand the tooltip to show current information
about the object, including assigned MIDI and OSC controllers.


Imgui backend: the status line at the bottom of the window shows
the currently active input modes, and the menus should reflect
which actions are available. Object tooltips will temporarily
overlay the status line at the bottom. Information about the
selected object is visible in the info panel on the right side.


## KNOWN BROKEN

There are a number of bugs, mostly in the Clutter backend, that I
hoped to get fixed by the last release (0.7) but have not.  Here are
some that I will just have to ask for your patience with:

Ticket | Description
-------| --------------
 #299 | If JACK isn't running and can't be started, launch fails ugly
 #298 | Occasional retry loop on quit
 #297 | Bad behavior on abort of file load
 #292 | In larger patches, selection and interaction may get messed up
 #291 | When editing a label, the cursor disappears
 #204 | Logging is broken when loaded as LV2 plugin
 #212 | Rendering of smooth curves on XY plot shows gaps
 #220 | 'waf install' can give error messages. Workaround: See the bottom of README.build; possibly no action is required.

See the tickets in GitHub for detail on what I know about these problems, and for
other potential workarounds.

## DOCUMENTATION

There is in-app help/documentation via the Help menu (a tutorial
and a reference doc) and context menus on patch elements. It's
not complete, but mostly what I am doing now is writing help
patches (they are great at flushing out bugs!) so the in-app help
will continue to improve. 

The Tutorial from the Help menu is probably the best place to
start to understand how to get around the program.

It covers basics about how to create, close, and open files
and make simple patches.  It also covers "patching patterns" for
things like iteration, conditionals, etc. 

(If you are using the Clutter backend, there's no Help menu; you
can find a Clutter version of the tutorial in `doc/tutorial.mfp`)

There's also some documentation in the doc/ directory of this
repository.

**LAC 2013 paper:** This paper (doc/lac2013/lac2013.pdf) gives a
high-level overview of what MFP is all about and a bit of
discussion about what it can do.

**README files:** There are some READMEs in doc which may be
useful if you want to know more about how MFP works.  Especially
note README.lv2 which describes how MFP patches can be saved as
LV2 plugins and loaded into an LV2 host.

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

**My patches:** There is a growing collection of patches that I
use in the repository bgribble/mfp-patches including:

 * 8 bus, 4 aux audio mixer
 * Step sequencer
 * Wrappers around LADSPA reverb plugins
 * Simple delay
 * Utility for communicatng with the KMI
   [QuNexus](https://www.keithmcmillen.com/products/qunexus/)
   keyboard controller

### SAVING FILES

There's no UI for saving yet, but there is a key mapping.
C-s (control-s) will prompt for a file to save in.  There's no checking for
overwrite, and the file is saved in the process working directory.

### REPORTING PROBLEMS

I'm using the GitHub hosted issue tracker.  It seems to be pretty
workable.

Enjoy!

Bill Gribble <grib@billgribble.com>
