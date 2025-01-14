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
	instruments = score.instrument_names()

	_,temp_file = tempfile.mkstemp(suffix='.mscz')
	shutil.copyfile(score_file, temp_file)
	temp_score = Score(temp_file)
	part = temp_score.part('Soprano')
	temp_score.find('Score').remove(part.element)

	pprint(set(score.part_names()) - set(temp_score.part_names()))
	temp_score.save()

	temp_score = Score(temp_file)
	pprint(set(score.part_names()) - set(temp_score.part_names()))

	os.unlink(temp_file)

#  end mscore/test.py
