#  mscore/fuzzy_match.py
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
Match instrument names in a sort of fuzzy way.
"""
import re
from collections import namedtuple
from functools import cache
from operator import itemgetter
from mscore import DEFAULT_VOICE


InstrumentVoice = namedtuple('InstrumentVoice', ['instrument_name', 'voice'])

SPLIT_WORDS_REGEX = '[^\w]'
NUMBER_EQUIVALENTS = [
	['1', 'i', '1st', 'first', 'one'],
	['2', 'ii', '2nd', 'second', 'two'],
	['3', 'iii', '3rd', 'third', 'three'],
	['4', 'iv', '4th', 'fourth', 'four']
]

def score(name1:str, name2:str) -> float:
	"""
	Returns a score based on how well the given instrument names match.
	"""
	parts1 = _name_parts(name1)
	parts2 = _name_parts(name2)
	common = parts1 & parts2
	diff = parts1 ^ parts2
	return len(common) / (len(common) + len(diff))


def score_sort(ref_name:str, instrument_names:list) -> list:
	"""
	Returns a list of tuples (score, instrument_name) for every given
	instrument_name.

	"instrument_names" must be a list of type str.
	"""
	return sorted([ (score(ref_name, instrument_name), instrument_name) \
		for instrument_name in instrument_names ],
		key=itemgetter(0), reverse = True)


def voice_match(name1:str, voice1:str, name2:str, voice2:str) -> float:
	"""
	Returns a score based on how well the given instrument names match.
	"""
	return 0 if voice1 != voice2 else score(name1, name2)


def voice_score_sort(ref_name:str, ref_voice:str, inst_voice_tuples:list) -> list:
	"""
	Returns a list of tuples (score, instrument_name, voice) for every given (instrument_name, voice) tuple.

	"inst_voice_tuples" must be a tuple of type InstrumentVoice.
	"""
	return sorted([ (voice_match(ref_name, ref_voice, tup.instrument_name, tup.voice), tup) \
		for tup in inst_voice_tuples ],
		key=itemgetter(0), reverse = True)


@cache
def _name_parts(instrument_name:str) -> set:
	"""
	Returns a set of parts, after the following is done:
		1. Lower case
		2. split words
		3. replace numeric words with int

	(This is a cached function).
	"""
	return set( _number(word) or word for word in re.split(SPLIT_WORDS_REGEX, instrument_name.lower()) )


@cache
def _number(word:str):
	"""
	Returns a number value of the given word from NUMBER_EQUIVALENTS.
	Returns None if not found.
	"""
	for i, list_ in enumerate(NUMBER_EQUIVALENTS):
		if word in list_:
			return i + 1
	return None


#  end mscore/fuzzy_match.py
