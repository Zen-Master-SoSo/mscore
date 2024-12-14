#  mscore/test.py
#
#  Copyright 2024 liyang <liyang@veronica>
#
import os, logging
from pprint import pprint
from mscore import Score

if __name__ == "__main__":
	log_format = "[%(filename)24s:%(lineno)-4d] %(levelname)-8s %(message)s"
	logging.basicConfig(level = logging.DEBUG, format = log_format)
	pprint(Score.user_soundfont_dirs())
	pprint(Score.user_soundfonts())
	pprint(Score.system_soundfont_dirs())
	pprint(Score.system_soundfonts())
	s = Score(os.path.join(os.path.dirname(__file__), 'res', 'score.mscz'))
	pprint(s.sound_fonts())
	pprint(s.part_names())
	pprint(s.instrument_names())



#  end mscore/test.py
