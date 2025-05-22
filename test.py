#  mscore/test.py
#
#  Copyright 2024 liyang <liyang@veronica>
#
import os, logging, shutil, tempfile
from pprint import pprint
from mscore import Score

if __name__ == "__main__":
	log_format = "[%(filename)24s:%(lineno)-4d] %(levelname)-8s %(message)score"
	logging.basicConfig(level = logging.DEBUG, format = log_format)
	Score.user_soundfont_dirs()
	Score.user_soundfonts()
	Score.system_soundfont_dirs()
	Score.system_soundfonts()

	score_file = os.path.join(os.path.dirname(__file__), 'res', 'score.mscz')
	score = Score(score_file)
	sf_list = score.sound_fonts()
	print('sf_list:', sf_list)
	instrument_names = score.instrument_names()
	print('instrument_names:', instrument_names)
	score_channels = [ f'{channel.midi_port}:{channel.midi_channel}' \
		for channel in score.channels() ]

	_,temp_file = tempfile.mkstemp(suffix='.mscz')
	shutil.copyfile(score_file, temp_file)

	temp_score = Score(temp_file)
	assert(temp_score.sound_fonts() == sf_list)
	assert(temp_score.instrument_names() == instrument_names)
	temp_channels = [ f'{channel.midi_port}:{channel.midi_channel}' \
		for channel in score.channels() ]
	assert(temp_channels == score_channels)

	print('Modifying ...')
	port = 1
	channel = 1
	for chan in temp_score.channels():
		chan.midi_port = port
		chan.midi_channel = channel
		channel += 1
		if channel == 17:
			port += 1
			channel = 1
	temp_score.save()
	print('Temp score saved at', temp_file)

	reloaded = Score(temp_file)
	assert(reloaded.sound_fonts() == sf_list)
	assert(reloaded.instrument_names() == instrument_names)

	print('Original score_channels:')
	for channel in score.channels():
		print(f'{channel.name:24s} {channel.midi_port:02d}:{channel.midi_channel:02d}')
	print('Modified and reloaded score_channels:')
	for channel in reloaded.channels():
		print(f'{channel.name:24s} {channel.midi_port:02d}:{channel.midi_channel:02d}')

	port = 1
	channel = 1
	for chan in reloaded.channels():
		assert(chan.midi_port == port)
		assert(chan.midi_channel == channel)
		channel += 1
		if channel == 17:
			port += 1
			channel = 1

	os.unlink(temp_file)

#  end mscore/test.py
