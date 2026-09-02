#  mscore/mscore/scripts/ms_stem.py
#
#  Copyright 2026 Leon Dionne <ldionne@dridesign.sh.cn>
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
Exports each part to an individual audio file for mixing with a DAW.

Score "signatures" are saved after stemming, so that the next time this script
is run, only parts which have changed since the last time are exported.
"""
import logging, sys, argparse
from tempfile import mkstemp, gettempdir
from pathlib import Path
from subprocess import run
from column_soso import StringColumns
from mscore import Score
from mscore.sigs import ScoreSignature


def confirm():
	while True:
		print('Continue? [Y/n]? ', end = '')
		key = input().lower()
		if key == 'n':
			return False
		if key in ('y', ''):
			return True


def _main():
	parser = argparse.ArgumentParser()
	parser.add_argument('Filename', type = str,
		help = 'MuseScore3 .mscz / .mscx file')
	parser.add_argument('Directory', type = str, nargs = '?',
		help = 'Directory to save files at (defaults to "<score name>-stems" score parent)')
	parser.add_argument('--format', '-f', choices = ['flac', 'wav', 'ogg', 'mp3'],
		default = 'flac', help = 'Export to the given format')
	parser.add_argument('--all', '-a', action = 'store_true',
		help = 'Export all, even if unchanged since the last export')
	parser.add_argument('--keep-pan', '-k', action = 'store_true',
		help = 'Leave pan values unchanged. Every part is centered by default, this overrides.')
	parser.add_argument('--verbose', '-v', action = 'store_true',
		help = 'Show more detailed debug information')
	parser.epilog = __doc__
	options = parser.parse_args()
	logging.basicConfig(
		level = logging.DEBUG if options.verbose else logging.ERROR,
		format = '[%(filename)24s:%(lineno)3d] %(message)s'
	)

	score_path = Path(options.Filename)
	if not score_path.exists():
		sys.stderr.write(f'"{score_path}" not found.\n')
		return 1
	if not score_path.suffix.lower() in ('.mscz', '.mscx'):
		sys.stderr.write(f'"{score_path}" doesn\'t appear to be a MuseScore score.\n')
		return 1
	dirpath = Path(options.Directory) if options.Directory else \
		score_path / f'{score_path.stem}-stems'

	score = Score(score_path)
	all_targets = { part_name: dirpath / f'{part_name}.{options.format}'
		for part_name in score.part_names() }
	sig = ScoreSignature(score)

	if sig.deleted_parts:
		print('These parts have been deleted:')
		StringColumns(sig.deleted_parts).print()
		delete_paths = [ path for part_name, path in all_targets.items() if part_name in sig.deleted_parts ]
		if delete_paths:
			print('\nDo you want to delete these stems?')
			for path in delete_paths:
				print(f'  {path}')
			if confirm():
				for path in delete_paths:
					path.unlink()
		print()

	missing_targets = set(path.stem for path in all_targets.values() if not path.exists())
	part_names = score.part_names() if options.all \
		else sorted(sig.new_parts | sig.changed_parts | missing_targets)

	if not part_names:
		print('''All signatures are up-to-date (nothing has changed since the last stemming).
You can re-run this script with the "--all" option to override this check.''')
		return 0

	print('Will export:')
	StringColumns(part_names).print()
	if confirm():
		_, tempfile = mkstemp(prefix = 'ms-stem-', suffix = '.mscx')
		score.disable_synth_effects()
		for part_name in part_names:
			part = score.part(part_name)
			if not options.keep_pan:
				part.center_pan()
			score.solo(part_name)
			score.save_as(tempfile)
			target_path = dirpath / f'{part_name}.{options.format}'
			print(f'  Exporting {target_path} ...', end = '')
			cp = run(['musescore3', '--export-to', target_path, tempfile],
				check = False, capture_output = True, text = True)
			if cp.returncode:
				print('ERRORED:')
				print(cp.stderr)
			else:
				print('Done')
			Path(tempfile).unlink()
		sig.save()


def main():
	try:
		return _main()
	except KeyboardInterrupt:
		print()
		return 0


if __name__ == "__main__":
	sys.exit(main() or 0)


#  mscore/mscore/scripts/ms_stem.py
