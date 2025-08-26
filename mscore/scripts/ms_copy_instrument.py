#  mscore/scripts/ms_copy_instrument.py
#
#  Copyright 2025 liyang <liyang@veronica>
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
Allows you to copy an instrument definition from one score to another.

If "--part" is given, this script will attempt to match the part name in both
Source and Target, and copy the best matching part. You will be prompted
to confirm the selection if there is no part name which matches exactly.

When not specifying a part to copy, the same scenario applies, but you will be
prompted for each replacement, for each part.
"""
import logging
import argparse
from rich.pretty import pprint
from mscore import Score, VoiceName
from mscore.fuzzy import FuzzyVoiceCandidate, score_candidates

options = None

def prompt_replacement(source_part, tgt_part):
	ans = input(f' Copy "{source_part}" from "{options.Source}" to "{tgt_part}" in "{options.Target}"? [y/N]')
	return ans[0].lower() == 'y'

def prompt_match(score, part):
	candidates = [ FuzzyVoiceCandidate(VoiceName(p.name, None), i) \
		for i, p in enumerate(score.parts()) ]
	results = score_candidates(VoiceName(part.name, None), candidates)
	pprint([
		(r.candidate.voice_name.instrument_name, r.score) \
		for r in results])

def main():
	p = argparse.ArgumentParser()
	p.add_argument('Source', type = str, nargs = 1,
		help = 'MuseScore3 score file to copy from')
	p.add_argument('Target', type = str, nargs = 1,
		help = 'MuseScore3 score file to copy to')
	p.add_argument('--part', '-p', type = str, nargs = '?',
		help = 'Part to copy')
	p.add_argument("--verbose", "-v", action = "store_true",
		help="Show more detailed debug information")
	p.epilog = __doc__
	options = p.parse_args()
	logging.basicConfig(
		level = logging.DEBUG if options.verbose else logging.ERROR,
		format = "[%(filename)24s:%(lineno)3d] %(message)s"
	)

	source = Score(options.Source[0])
	target = Score(options.Source[0])

	for part in source.parts():
		prompt_match(target, part)

if __name__ == "__main__":
	main()

#  end mscore/scripts/ms_colorize.py
