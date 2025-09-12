#  mscore/scripts/ms_info.py
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
"""
Show various information about a MuseScore3 score file.
"""
import logging, sys, argparse
from mscore import Score, CC_NAMES

def main():
	p = argparse.ArgumentParser()
	p.add_argument('Filename', type = str, nargs = '+',
		help = "MuseScore3 file (.mscz or .mscx)")
	p.add_argument('-p', '--parts', action="store_true")
	p.add_argument('-i', '--instruments', action="store_true")
	p.add_argument('-c', '--channels', action="store_true")
	p.add_argument('-s', '--staffs', action="store_true")
	p.add_argument('-l', '--length', action="store_true")
	p.add_argument('-m', '--meta', action="store_true")
	p.add_argument('--controllers', action="store_true",
		help = 'Show constant controller (CC) values, such as volume and pan settings')
	p.add_argument('--channel-switches', action="store_true",
		help = 'Show channel switches used. These are staff text which set the channel to be used.')
	p.add_argument("--verbose", "-v", action="store_true",
		help="Show more detailed debug information")
	p.epilog = __doc__
	options = p.parse_args()
	logging.basicConfig(
		level = logging.DEBUG if options.verbose else logging.ERROR,
		format = "[%(filename)24s:%(lineno)3d] %(message)s"
	)

	for filename in options.Filename:
		score = Score(filename)
		if options.length:
			print(f'{filename}: {score.length} measures')
		chanlen = max(len(chan.name) for chan in score.channels())
		chanfmt = '    {0:%ds} | port {1:02d} | channel {2:02d}' % chanlen
		if options.meta:
			for tag in score.meta_tags():
				print(f"{tag.name}\t{tag.value or ''}")
		for part in score.parts():
			if options.parts or options.channel_switches:
				print(part.name)
			if options.channel_switches:
				switches = part.channel_switches_used()
				print('  Channel switches used: ' + (', '.join(switches) if switches else 'None'))
			if options.staffs:
				for staff in part.staffs():
					print(f'  Staff {staff.id} | {staff.type} | {staff.clef} clef | {len(staff.measures())} measures')
			if options.instruments or options.channels or options.controllers:
				inst = part.instrument()
				print(f'  {inst.name}')
				if options.channels or options.controllers:
					for chan in inst.channels():
						print(chanfmt.format(chan.name, chan.midi_port, chan.midi_channel))
						if options.controllers:
							print('      ' + ', '.join(f'{name}: {chan.controller_value(cc)}'
								for cc, name in CC_NAMES.items() ))

if __name__ == "__main__":
	main()

#  end mscore/scripts/ms_info.py
