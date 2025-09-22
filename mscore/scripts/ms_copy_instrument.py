#  mscore/scripts/ms_copy_instrument.py
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
Allows you to copy an instrument definition from one score to another.

This script will attempt to match the part name in both Source and Target, and
copy the best matching part. You will be prompted to confirm the selection if
there is no part name which matches exactly.
"""
import logging, sys
import argparse
from os.path import realpath
from mscore import Score, VoiceName
from mscore.fuzzy import FuzzyCandidate, FuzzyName

options = None

def prompt_replacement(source_part, tgt_part):
	ans = input(f' Copy "{source_part}" from "{options.Source}" to "{tgt_part}" in "{options.Target}"? [y/N]')
	return ans[0].lower() == 'y'

def prompt_for_source(source, part_name):
	candidates = [ FuzzyCandidate(p.name, i) \
		for i, p in enumerate(source.parts()) ]
	results = FuzzyName(part_name).score_candidates(candidates)
	results = [ r.candidate.name for r in results if r.score > 0 ]
	print(f'Did not find "{part_name}" in "{source.basename}"')
	print('Did you mean one of the following?')
	for idx, result in enumerate(results):
		print(f' {idx + 1}. {result}')
	return _get_selection('Select the part to copy over: [1] ', results)

def prompt_for_target(source, target, part_name):
	candidates = [ FuzzyCandidate(p.name, i) \
		for i, p in enumerate(target.parts()) ]
	results = FuzzyName(part_name).score_candidates(candidates)
	if results[0].score < 1.0:
		results = [ r.candidate.name for r in results if r.score > 0 ]
		print(f'Confirm which part in "{target.basename}" you want to replace')
		print(f'with the instrument from "{source.basename}" "{part_name}":')
		print(f' "{part_name}" matches:')
		for idx, result in enumerate(results):
			print(f' {idx + 1}. {result}')
		return _get_selection('Select the target part (s to skip): [1] ', results)
	else:
		return results[0].candidate.name

def _get_selection(prompt, results):
	while True:
		try:
			selection = input(prompt).strip()
			if selection == 's':
				return None
			index = int(selection) - 1 if selection else 0
			print()
			return results[index]
		except KeyboardInterrupt:
			print()
			sys.exit(1)
		except IndexError:
			print(f'"{selection} is an invalid choice. Try again')

def main():
	p = argparse.ArgumentParser()
	p.add_argument('Source', type = str, nargs = 1,
		help = 'MuseScore3 score file to copy from')
	p.add_argument('Targets', type = str, nargs = '+',
		help = 'MuseScore3 score file to copy to')
	p.add_argument('--part', '-p', type = str, nargs = '*',
		help = 'Part to copy')
	p.add_argument("--clef", "-c", action = "store_true",
		help="Copy default clef definition as well")
	p.add_argument("--verbose", "-v", action = "store_true",
		help="Show more detailed debug information")
	p.epilog = __doc__
	options = p.parse_args()
	for tgt_filename in options.Targets:
		if realpath(options.Source[0]) == realpath(tgt_filename):
			p.error('Source is the same file as Target')
	logging.basicConfig(
		level = logging.DEBUG if options.verbose else logging.ERROR,
		format = "[%(filename)24s:%(lineno)3d] %(message)s"
	)

	source = Score(options.Source[0])
	src_parts = source.part_names()
	src_parts_lower = [ part_name.lower() for part_name in src_parts ]
	parts_to_replace = options.part or src_parts
	for tgt_filename in options.Targets:
		target = Score(tgt_filename)
		for part_name in parts_to_replace:
			part_name = part_name.lower()
			if part_name in src_parts_lower:
				part_name = src_parts[ src_parts_lower.index(part_name) ]
			else:
				part_name = prompt_for_source(source, part_name)
			tgt_part_name = prompt_for_target(source, target, part_name)
			if tgt_part_name:
				print(f'  *** Copy {source.basename} {part_name} to {target.basename} {tgt_part_name} ***')
				target.part(tgt_part_name).replace_instrument(source.part(part_name).instrument())
				if options.clef:
					print('      copy clef')
					target.part(tgt_part_name).copy_clef(source.part(part_name))
		target.save()
		print()

if __name__ == "__main__":
	main()


#  end mscore/scripts/ms_colorize.py
