#  mscore/scripts/ms_cleanup.py
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
Removes unused elements from a MuseScore3 score.
"""
import logging
import argparse
from operator import and_
from functools import reduce
from mscore import Score


def main():
	p = argparse.ArgumentParser()
	p.add_argument('Filename', type = str, nargs = '+',
		help = 'MuseScore3 file (.mscz or .mscx)')
	element_selection_group = p.add_mutually_exclusive_group(required = True)
	element_selection_group.add_argument("--parts", "-p", action = "store_true",
		help = "Delete empty parts")
	element_selection_group.add_argument("--channels", "-c", action = "store_true",
		help = """Delete empty instrument channels. A channel is considered "empty"
		when it is not referenced by a channel switch (staff text).""")
	element_selection_group.add_argument("--synth", "-s", action = "store_true",
		help = """Delete synth (FluidSynth or Zerberus) settings. Handy for when
		you are using an external synth such as MusecBox or LinuxSampler.""")
	p.add_argument('--batch', '-b', action = 'store_true',
		help = """When deleting parts or channels, and multiple files are given,
		only delete elements common to all files.""")
	p.add_argument('--dry-run', '-n', action = 'store_true',
		help = 'Do not delete anything - just show what would be deleted.')
	p.add_argument('--verbose', '-v', action = 'store_true',
		help = 'Show more detailed debug information')
	p.epilog = __doc__
	options = p.parse_args()
	logging.basicConfig(
		level = logging.DEBUG if options.verbose else logging.ERROR,
		format = "[%(filename)24s:%(lineno)3d] %(message)s"
	)

	if len(options.Filename) == 1 and options.batch:
		p.error('"--batch" mode requires more than one Filename')

	scores = [ Score(filename) for filename in options.Filename ]

	if options.synth:
		for score in scores:
			if options.dry_run:
				print(f'Will delete synth for "{score.filename}"')
			else:
				score.clear_synth()
				if verbose:
					print(f'Deleted synth for "{score.filename}"')
				score.save()

	elif options.parts:
		if options.batch:
			parts = sorted(reduce(and_, [ set(score.empty_parts()) for score in scores ]))
			if parts:
				if options.dry_run:
					print('Will delete the following parts from every score:\n  ' +
					'\n  '.join(parts))
				else:
					for score in scores:
						for part in parts:
							score.part(part).delete()
						if options.verbose:
							print(f'{score.filename} - deleted:\n  ' +
							'\n  '.join(parts))
						score.save()
			elif options.verbose:
				print('No empty parts common to all the given scores.')
		else:
			for score in scores:
				parts = score.empty_parts()
				if parts:
					if options.dry_run:
						print(f'{score.filename} - will delete:\n  ' +
						'\n  '.join(parts))
					else:
						for part in parts:
							score.part(part).delete()
						if options.verbose:
							print(f'{score.filename} - deleted:\n  ' +
							'\n  '.join(parts))
						score.save()
				elif options.verbose:
					print(f'{score.filename} - no empty parts.')

	elif options.channels:
		if options.batch:
			channels = sorted(reduce(and_, [ set(score.empty_channels()) for score in scores ]))
			if channels:
				if options.dry_run:
					print('Will delete the following channels from every score:\n  ' +
					'\n  '.join(channels))
				else:
					for score in scores:
						for channel in channels:
							score.channel(channel).delete()
						if options.verbose:
							print(f'{score.filename} - deleted:\n  ' +
							'\n  '.join(channels))
						score.save()
			elif options.verbose:
				print('No empty channels common to all the given scores.')
		else:
			for score in scores:
				channels = score.empty_channels()
				if channels:
					if options.dry_run:
						print(f'{score.filename} - will delete:\n  ' +
						'\n  '.join(channels))
					else:
						for channel in channels:
							score.channel(channel).delete()
						if options.verbose:
							print(f'{score.filename} - deleted:\n  ' +
							'\n  '.join(channels))
						score.save()
				elif options.verbose:
					print(f'{score.filename} - no empty channels.')


if __name__ == "__main__":
	main()

#  end mscore/scripts/ms_cleanup.py
