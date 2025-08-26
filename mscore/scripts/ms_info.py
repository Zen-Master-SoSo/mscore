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
from mscore import Score

def main():
	p = argparse.ArgumentParser()
	p.add_argument('Filename', type = str, nargs = '+',
		help = "MuseScore3 file (.mscz or .mscx)")
	p.add_argument('-p', '--parts', action="store_true")
	p.add_argument('-i', '--instruments', action="store_true")
	p.add_argument('-c', '--channels', action="store_true")
	p.add_argument('-s', '--staffs', action="store_true")
	p.add_argument('-m', '--meta', action="store_true")
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
		if options.meta:
			for tag in score.meta_tags():
				print(f"{tag.name}\t{tag.value or ''}")
		for part in score.parts():
			if options.parts:
				print(part.name)
			if options.staffs:
				for staff in part.staffs():
					print(f'  Staff {staff.id} "{staff.type}" {staff.clef} {len(staff.measures())} measures')
			if options.instruments or options.channels:
				inst = part.instrument()
				if options.instruments:
					print(f'  {inst.name}')
				if options.channels:
					for chan in inst.channels():
						if options.instruments:
							print(f'    {chan.name:24s}  {chan.midi_port:2d} {chan.midi_channel:2d}')
						else:
							print(f'  {inst.name:24s}  {chan.name:24s}  {chan.midi_port:2d} {chan.midi_channel:2d}')

if __name__ == "__main__":
	main()

#  end mscore/scripts/ms_info.py
