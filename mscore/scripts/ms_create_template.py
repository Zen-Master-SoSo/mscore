#  mscore/scripts/ms_create_template.py
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
Creates an empty score to use as a template from the given score. The created
template is always saved in ".mscx" format. You can open it in MuseScore, and
save it with an .mscz format from there.
"""
import logging, sys, argparse
from mscore import Score

def main():
	p = argparse.ArgumentParser()
	p.add_argument('Filename', type = str, nargs = 1,
		help = 'MuseScore3 file (.mscz or .mscx)')
	p.add_argument('Target', type = str, nargs = '?',
		help = 'Target generated template (.mscx). If not given, "template.mscx" will be used')
	p.add_argument("--verbose", "-v", action="store_true",
		help="Show more detailed debug information")
	p.epilog = __doc__
	options = p.parse_args()
	logging.basicConfig(
		level = logging.DEBUG if options.verbose else logging.ERROR,
		format = "[%(filename)24s:%(lineno)3d] %(message)s"
	)

	score = Score(options.Filename[0])
	target = options.Target[0] if options.Target else 'template.mscx'
	for staff in score.staffs():
		staff.empty()
	score.save_as(target)


if __name__ == "__main__":
	main()

#  end mscore/scripts/ms_create_template.py
