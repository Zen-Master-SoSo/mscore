#  mscore/scripts/port_partition.py
#
#  Copyright 2025 liyang <liyang@veronica>
#
"""
Re-assigns MIDI port/channels, grouped by instrument.
"""
import logging
import argparse
from mscore import Score

def main():
	p = argparse.ArgumentParser()
	p.add_argument('filename', type=str, help="MuseScore4 .mscz / .mscx file")
	p.add_argument("--compact", "-c", action="store_true", help="Reduce channels used by re-using channels for different parts using the same instrument")
	p.add_argument("--dry-run", "-n", action="store_true", help="Just show port/channel layout")
	logging.basicConfig(
		level = logging.DEBUG,
		format = "[%(filename)24s:%(lineno)3d] %(message)s"
	)
	options = p.parse_args()
	score = Score(options.filename)
	mapped_channels = {}			# key instrument_name.articulation, value tup(port_number, channel_number)
	port_number = 1
	channel_number = 1
	for part in score.parts():
		inst = part.instrument()
		inst_name = inst.name
		chans_to_map = [ chan for chan in inst.channels() \
			if not '{}.{}'.format(inst_name, chan.name) in mapped_channels ] \
			if options.compact else inst.channels()
		if channel_number + len(chans_to_map) > 17:
			port_number += 1
			channel_number = 1
		for chan in inst.channels():
			key = '{}.{}'.format(inst_name, chan.name)
			if options.compact and key in mapped_channels:
				chan.midi_port = mapped_channels[key][0]
				chan.midi_channel = mapped_channels[key][1]
			else:
				chan.midi_port = port_number
				chan.midi_channel = channel_number
				mapped_channels[key] = (port_number, channel_number)
				channel_number += 1

	for inst in score.instruments():
		print(inst.name)
		for chan in inst.channels():
			print('  %02d %02d %s' % (chan.midi_port, chan.midi_channel, chan.name))

	if not options.dry_run:
		score.save()


if __name__ == "__main__":
	main()

#  end mscore/scripts/port_partition.py
