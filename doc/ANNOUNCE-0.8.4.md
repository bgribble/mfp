## MFP -- Music For Programmers, version 0.8.4

I'm happy to announce a followup release to 0.8.3,
including bug fixes and new features I added in the runup to
LAC-2025.

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


### Significant changes since release v0.8.3

* Add `[table]` plot object. This is an interactive editable barchart similar
  to `[itable]` in Max
* Add `[messagerec]` builtin. This is a clocked record/playback sequencer that
  can be used to record any kind of message.
* Added infrastructure for preset save/load via the `@preset` method.
    * Send the message `@preset("preset name", save=True)` to an object to create
      or save a preset
    * Send `@preset("preset name")` to load the preset
    * Send to a via named `self` will save a preset for the whole patch and all children
* Support slices as element addresses in `[get]` and `[set!]`
* Fix bugs in MIDI event handling
* Fix bugs in panel-mode displays
* Fix bugs in `[faust~]` creation


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



