# mscore3

A python library for opening/inspecting/modifying MuseScore3 files.

## Installing

Currently only available from the PyPi repository. Make sure you have the "pip"
Python package installer on your system, and run this:

```bash
$ pip install mscore3
```

If you don't have pip, you can install it on debian -based systems using:

```bash
$ sudo apt-get install python3-pip
```

## Scripts

Installing this python package gives you the following command-line scripts:

*	ms-cleanup
*	ms-colorize
*	ms-concatenate
*	ms-copy-instrument
*	ms-create-template
*	ms-info
*	ms-port-partition
*	ms-stem


#### ms-cleanup

Removes unused elements from a MuseScore3 score.

May delete empty parts (which contain no notes in their measures). You can pass
multiple file names, and only delete the empty parts which are common to all of
the given scores. This is useful if you are working on a set of scores which
will be concatenated using "ms-concatenate".

You can use this script to delete the "Synth" node in a score. This removes any
reference to .sf2 soundfonts, useful if moving from SoundFont usage to .SFZ
usage. Scores load quicker without a soundfont defined.


#### ms-colorize

Changes the staff colors. By default, staff colors are changed to a medium
gray, allowing notes to stand out with lines still visible.

Unfortunately, there is no MuseScore style setting for these. This script works
around that limitation.

#### ms-concatenate

Concatenates the measures from two or more scores into another score. The
purpose of this script is to allow you to work on a section of a very long
composition, without "lag" slowing you down. When MuseScore has to interpret
and render a very long score, it gets a little slow. Breaking a long
composition down into parts gets around that, making your composing experience
more pleasant. Note that all sources MUST have the same part / instrument
structure.


#### ms-copy-instrument

Allows you to copy an instrument definition from one score to another. This
script will attempt to match the part name in both Source and Target, and copy
the best matching part. You will be prompted to confirm the selection if there
is no part name which matches exactly.

Useful if you have created a custom instrument which you would like to use in
another score.


#### ms-create-template

Creates an empty score to use as a template from the given score. The created
template is always saved in ".mscx" format. You can open it in MuseScore, and
save it with an .mscz format from there.


#### ms-info

Show various information about a MuseScore3 score file.

Info available includes:

| option | what is shown |
| ------ | ------------- |
| --parts | part names |
| --instruments | instrument names |
| --channels | channel name, port, and channel numbers |
| --staffs | the staff type, clef, and measure count |
| --length | measure count |
| --meta | tags, such as "composer", "copyright", and "creationDate" |
| --controllers | the "volume", "pan" and other controllers set per channel |
| --channel-switches | the "Staff Text" markups which change an instrument output channel |


#### ms-port-partition

Re-assigns MIDI port/channels grouped by instrument. Every instrument's
"voice" is assigned a sequential MIDI channel. If an instrument has more
"voices" (arco, staccato, tremolo, etc.) than there remaining channels on a
port, they are assigned to the next available port.


#### ms-stem

Exports each part to an individual audio file for mixing with a DAW.

Score "signatures" are saved after stemming, so that the next time this script
is run, only parts which have changed since the last time are exported.


## Programming API

### Importing

The import name is "mscore". The *package* name is "mscore3", only because of a
naming conflict in the pypi repository.

### Usage

Setting the MIDI channel of a "Harp":

```python
from mscore import Score

score = Score(argv[1])
for part in score.parts():
	if part.name == "Harp":
		for channel in part.channels():
			channel.port = 4
score.save()
```

Changing the "composer" tag on a bunch of scores:

```python
from mscore import Score, is_score
from pathlib import Path

for path in Path().iterdir():
	if is_score(path):
		score = Score(path)
		score.meta_tag('composer').value = 'Monkey Johnson'
		score.save()
```

Use "pydoc" to get more details:

```bash
pydoc mscore
```
