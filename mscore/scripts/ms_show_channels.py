#  mscore/scripts/ms_show_channels.py
#
#  Copyright 2025 Leon Dionne <ldionne@dridesign.sh.cn>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
#  mscore/mscore/scripts/ms_show_channels.py
#
#  Copyright 2025 Leon Dionne <ldionne@dridesign.sh.cn>
#
"""
Displays a score's MIDI port/channels
"""
import logging
import argparse
from mscore import Score

def main():
	p = argparse.ArgumentParser()
	p.add_argument('filename', type = str, help = "MuseScore4 .mscz / .mscx file")
	p.epilog = __doc__
	logging.basicConfig(
		level = logging.DEBUG,
		format = "[%(filename)24s:%(lineno)3d] %(message)s"
	)
	options = p.parse_args()
	score = Score(options.filename)
	for part in score.parts():
		inst = part.instrument()
		print(part.name)
		for chan in inst.channels():
			print('  %2d %-2d %s %s' % (chan.midi_port, chan.midi_channel, inst.name, chan.name))

if __name__ == "__main__":
	main()

#  end mscore/scripts/ms_show_channels.py
