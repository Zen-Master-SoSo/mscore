#  mscore/scripts/channels.py
#
#  Copyright 2025 liyang <liyang@veronica>
#
"""
Displays a score's MIDI port/channels
"""
import logging
import argparse
from mscore import Score

def main():
	p = argparse.ArgumentParser()
	p.add_argument('filename', type=str, help="MuseScore4 .mscz / .mscx file")
	logging.basicConfig(
		level=logging.DEBUG,
		format="[%(filename)24s:%(lineno)3d] %(message)s"
	)
	options = p.parse_args()
	score = Score(options.filename)
	for part in score.parts():
		inst = part.instrument()
		print(part.name)
		for chan in inst.channels():
			print('  %2d %-2d %s %s' % (chan.midi_port, chan.midi_channel, inst.name, chan.name))

#  end mscore/scripts/channels.py
