#  mscore/test.py
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
import logging
from pathlib import Path
from shutil import copyfile
from tempfile import mkstemp
from subprocess import run, CalledProcessError
from mscore import (Score, user_soundfont_dirs, user_soundfonts,
	system_soundfont_dirs, system_soundfonts)


def pprint(list_):
	for item in list_:
		print(f'  {item}')
	print()

def channel_repr(check_score):
	return [ f'{check_chan.midi_port}:{check_chan.midi_channel}' \
		for check_chan in check_score.channels() ]

def assert_channel_sequence(check_score):
	check_port = 1
	check_chan = 1
	for chan_object in check_score.channels():
		assert chan_object.midi_port == check_port
		assert chan_object.midi_channel == check_chan
		check_chan += 1
		if check_chan == 17:
			check_port += 1
			check_chan = 1


if __name__ == "__main__":
	logging.basicConfig(level = logging.DEBUG,
		format = "[%(filename)24s:%(lineno)-4d] %(levelname)-8s %(message)score")

	print('user_soundfont_dirs:')
	pprint(user_soundfont_dirs())
	print('user_soundfonts:')
	pprint(user_soundfonts())
	print('system_soundfont_dirs:')
	pprint(system_soundfont_dirs())
	print('system_soundfonts:')
	pprint(system_soundfonts())

	score_path = Path(__file__).parent.joinpath('mscore', 'res', 'score.mscz')
	score = Score(score_path)

	score_sound_fonts = score.sound_fonts()
	print('score_sound_fonts:')
	pprint(score_sound_fonts)
	instrument_names = score.instrument_names()
	print('instrument_names:')
	pprint(instrument_names)

	score_chan_repr = channel_repr(score)

	try:

		_, test_file = mkstemp(suffix = '.mscz')
		test_path = Path(test_file)
		copyfile(score_path, test_path)

		test_score = Score(test_path)
		assert test_score.sound_fonts() == score_sound_fonts
		assert test_score.instrument_names() == instrument_names
		assert channel_repr(test_score) == score_chan_repr

		print('Modifying ...')
		port = 1
		channel = 1
		for chan in test_score.channels():
			chan.midi_port = port
			chan.midi_channel = channel
			channel += 1
			if channel == 17:
				port += 1
				channel = 1
		test_chan_repr = channel_repr(test_score)
		assert test_chan_repr != score_chan_repr

		test_score.save()
		print('Test score saved at', test_path)

		reloaded_score = Score(test_path)
		assert reloaded_score.sound_fonts() == score_sound_fonts
		assert reloaded_score.instrument_names() == instrument_names
		reloaded_chan_repr = channel_repr(reloaded_score)

		assert_channel_sequence(reloaded_score)

		test_export_path = test_path.with_suffix('.mscx')
		try:
			run(['musescore3', '--export-to', test_export_path, test_path], check = True)
		except CalledProcessError as cpe:
			print(cpe)
		else:
			test_export_score = Score(test_export_path)
			assert_channel_sequence(test_export_score)
		finally:
			test_export_path.unlink()

	except Exception as e:
		print(e)
	else:
		print('No errors')
	finally:
		test_path.unlink()

#  end mscore/test.py
