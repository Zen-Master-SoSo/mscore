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
import os, logging, shutil, tempfile
from subprocess import run, CalledProcessError
from mscore import *


def channel_repr(score):
	return [ f'{channel.midi_port}:{channel.midi_channel}' \
		for channel in score.channels() ]

def assert_channel_sequence(score):
	port = 1
	channel = 1
	for chan in score.channels():
		assert(chan.midi_port == port)
		assert(chan.midi_channel == channel)
		channel += 1
		if channel == 17:
			port += 1
			channel = 1


if __name__ == "__main__":
	log_format = "[%(filename)24s:%(lineno)-4d] %(levelname)-8s %(message)score"
	logging.basicConfig(level = logging.DEBUG, format = log_format)
	print('user_soundfont_dirs', user_soundfont_dirs())
	print('user_soundfonts', user_soundfonts())
	print('system_soundfont_dirs', system_soundfont_dirs())
	print('system_soundfonts', system_soundfonts())

	score_file = os.path.join(os.path.dirname(__file__), 'res', 'score.mscz')
	score = Score(score_file)
	sf_list = score.sound_fonts()
	print('sf_list:', sf_list)
	instrument_names = score.instrument_names()
	print('instrument_names:', instrument_names)
	score_chan_repr = channel_repr(score)

	try:

		_,test_file = tempfile.mkstemp(suffix='.mscz')
		shutil.copyfile(score_file, test_file)

		test_score = Score(test_file)
		assert(test_score.sound_fonts() == sf_list)
		assert(test_score.instrument_names() == instrument_names)
		assert(channel_repr(test_score) == score_chan_repr)

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
		assert(test_chan_repr != score_chan_repr)

		test_score.save()
		print('Test score saved at', test_file)

		reloaded_score = Score(test_file)
		assert(reloaded_score.sound_fonts() == sf_list)
		assert(reloaded_score.instrument_names() == instrument_names)
		reloaded_chan_repr = channel_repr(reloaded_score)

		assert_channel_sequence(reloaded_score)

		test_export_file = os.path.splitext(test_file)[0] + '.mscx'
		try:
			run(['musescore3', '--export-to', test_export_file, test_file])
		except CalledProcessError as cpe:
			print(cpe)
		else:
			test_export_score = Score(test_export_file)
			assert_channel_sequence(test_export_score)
		finally:
			os.unlink(test_export_file)

	except Exception as e:
		print(e)
	finally:
		os.unlink(test_file)

#  end mscore/test.py
