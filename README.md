# mscore3

A python library for opening/inspecting/modifying MuseScore3 files.

## Importing

The import name is "mscore"

## Simple usage

	from mscore import Score

	score = Score(argv[1])
	for part in score.parts():
		if part.name == "Harp":
			for channel in part.instrument().channels():
				channel.port = 4

## Formats

Reads/writes both .mscx and .mscz files.
