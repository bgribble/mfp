## MFP -- Music For Programmers, version 0.8.6

I'm happy to announce the next release in the MFP 0.8 series,
including a new audio buffer editor, along with other 
improvements and bug fixes.

A summary of changes is below.  Please see the GitHub project page
for complete details:

  http://github.com/bgribble/mfp

I still recommend cloning and building from source. The build
process is improved and does a better job of isolating the MFP
install into the `--prefix` destination.

If you simply can't get the build dependencies working, I have
made a start on a CD process using Github Actions. There is a
binary package for amd64 architectures (most AMD and Intel
processors) with an install script that should be built and
associated with the release. Versions of the installable packages
are built for Python 3.10, 3.11, 3.12, and 3.13; pick whichever
one is appropriate for you. Since MFP includes both Python and C
components, I am not very confident that this binary package will
work. Please let me know if you have success (or failure) with
it.


### Significant changes since release v0.8.5

* Audio wave editor for `[buffer~]` objects
    * `C-b` toggles the buffer editor; hamburger menu has editing options. 
    * Left click to place playhead, left click and drag to scroll, right 
      click and drag to select, scroll wheel to zoom, double click to zoom
      to whole buffer
    * Note that inputs must be connected to the buffer~ if you wish to record,
      but outputs are automatically connected to the 2 "auditioner" outputs
    * Auditioner outputs default to outputs 0 and 1 but can be set with the 
      `--audition-outputs` command line option
* `[buffer~]` objects can export contents to audio files (type determined from 
  filename)
* The first 2 inputs and outputs are automatically connected to hardware
  i/o. Disable this behavior with `--no-default-audio`
* Processor type can be the result of an expression. When creating a processor, 
  a processor type name enclosed in `{}` will be evaluated as an expression before
  creating the object. This enables "wrapper" patches to create different types of 
  elements based on their arguments.
* More processor-type-specific attributes appear in the "Params" tab of the 
  info panel
* Lots of bug fixes


### About MFP

MFP is an environment for visually composing computer programs,
with an emphasis on music and real-time audio synthesis and
analysis.  It's very much inspired by Miller Puckette's Pure Data
(Pd) and Max/MSP, with a bit of LabView and TouchOSC for good
measure.  It is targeted at musicians, recording engineers, and
software developers who like the "patching" dataflow metaphor for
coding up audio synthesis, processing, and analysis.

MFP is a completely new code base, written in Python and C. It
has been under development by a solo developer (me!), as a
spare-time project for several years.

Compared to Pure Data, its nearest relative, MFP is superficially
pretty similar but differs in a few key ways:

 * MFP uses Python data natively.  Any literal data entered in the
   UI is parsed by the Python evaluator, and any Python value is a
   legitimate "message" on the dataflow network. This makes it much
   easier to make patches that work like conventional "programs".

 * MFP provides fairly raw access to Python constructs if
   desired. For example, a built-in editor allows live coding of
   Python functions as patch elements at runtime.

 * Name resolution and namespacing are addressed more robustly,
   with explicit support for lexical scoping.  This allows patches
   to have a dynamic number of inputs and outputs, with hygienic
   layer copying preserving the lexical structure of each "voice"

 * The UI is largely keyboard-driven, with a modal input system
   that feels a bit like vim.  The graphical presentation is a
   single-window style with layers and a tiled workspace rather
   than multiple windows.

 * There is fairly deep integration of Open Sound Control (OSC), with
   every patch element having an OSC address and the ability to learn
   any other desired address.  MIDI controller learning is also robustly
   supported.

 * MFP has just a fraction of the builtin and addon functionality
   provided by Pd.  It's not up to being a replacement except in
   limited cases!

The code and issue tracker are hosted on GitHub:

    https://github.com/bgribble/mfp

Help can be found in the app; I recommend starting with the
Tutorial and proceeding to the Reference mentioned in the Help
menu.

You can find two white papers about MFP (one accepted to the 2013
edition of the Linux Audio Conference, and one submitted for the
2025 edition), some sample patches, and a few other bits of
documentation in the doc directory of the GitHub repo.  The
README files at the top level of the source tree contain
dependency, build, and getting-started information.

Where's it going?
----------------------------------------

I've been working on MFP as a spare time project for almost 14
years now.  The likelihood that it will ever have more than a few
users is low.  Luckily, that doesn't bother me much; MFP is a
tool I am building mainly for my own use and education.

That being said, if there's something about it that appeals to
you, I welcome your interest and participation.

Thanks,
Bill Gribble <grib@billgribble.com>



