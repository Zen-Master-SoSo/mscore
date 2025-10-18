#  mscore/scripts/ms_colorize.py
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
Changes the staff colors.

By default, staff colors are changed to a medium gray, allowing notes to stand
out with lines still visible.
"""
import logging
import argparse
from mscore import Score

def main():
	p = argparse.ArgumentParser()
	p.add_argument('Filename', type = str, nargs = '+',
		help = "MuseScore3 file (.mscz or .mscx)")
	p.add_argument('-c', '--color', type = str, default = "#888",
		help = "Color value in #rgba format")
	p.add_argument("--verbose", "-v", action = "store_true",
		help = "Show more detailed debug information")
	p.epilog = __doc__
	options = p.parse_args()
	logging.basicConfig(
		level = logging.DEBUG if options.verbose else logging.ERROR,
		format = "[%(filename)24s:%(lineno)3d] %(message)s"
	)

	for filename in options.Filename:
		score = Score(filename)
		h = options.color.lstrip('#')
		if len(h) == 3:
			r, g, b = tuple(int(h[i], 16) * 16 + int(h[i], 16) for i in range(3))
			a = 255
		elif len(h) == 4:
			r, g, b, a = tuple(int(h[i], 16) * 16 + int(h[i], 16) for i in range(4))
		elif len(h) == 6:
			r, g, b = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
			a = 255
		elif len(h) == 8:
			r, g, b, a = tuple(int(h[i:i+2], 16) for i in (0, 2, 4, 6))
		else:
			p.error(f'"{options.Color}" is not a valid Color')
		color_dict = { 'r':r, 'g':g, 'b':b, 'a':a }
		for staff in score.staffs():
			staff.color = color_dict
		score.save()


#  end mscore/scripts/ms_colorize.py
