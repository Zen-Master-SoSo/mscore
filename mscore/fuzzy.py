#  mscore/fuzzy.py
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
import re, logging
from collections import namedtuple
try:
	from functools import cache
except ImportError:
	from functools import lru_cache as cache
from operator import attrgetter
from mscore import VoiceName

FuzzCandidate = namedtuple('FuzzCandidate', ['voice_name', 'index'])
FuzzResult = namedtuple('FuzzResult', ['score', 'candidate'])

# Strategies for handling voice or numbers:
IGNORE = 0
MATCH = 1
PREFER = 2

SPLIT_WORDS_REGEX = r'[\s]+'
SUBSTITUTIONS = [
	(r'f horn', 'french horn'),
	(r'elec', 'electric'),
	(r'\b([a-z])\s*(flat|b)\b', r'\1♭'),
	(r'([a-z])\s*(sharp|#)\b', r'\1♯')
]
NUMBERS = [
	['1', 'i', '1st', 'first', 'one'],
	['2', 'ii', '2nd', 'second', 'two'],
	['3', 'iii', '3rd', 'third', 'three'],
	['4', 'iv', '4th', 'fourth', 'four']
]

def score(voice_name1: VoiceName, voice_name2: VoiceName,
	numbers_strategy: int = MATCH, voice_strategy: int = MATCH) -> float:
	"""
	Returns a score based on how well the given instrument names match.
	"""
	assert numbers_strategy in [IGNORE, MATCH, PREFER]
	assert voice_strategy in [IGNORE, MATCH, PREFER]
	if voice_name1 == voice_name2:
		return 1.0
	if voice_strategy == MATCH and voice_name1.voice != voice_name2.voice:
		return 0.0
	num1, words1 = _name_parts(voice_name1.instrument_name)
	num2, words2 = _name_parts(voice_name2.instrument_name)
	if numbers_strategy == MATCH and num1 != num2:
		return 0.0
	long_list, short_list = (words1, words2) if len(words1) > len(words2) else (words2, words1)
	scores = [
		sorted([ _word_score(word1, word2) for word2 in short_list ]).pop() \
		for word1 in long_list ]
	f_score = sum(scores) / len(scores)
	if voice_strategy == PREFER and voice_name1.voice != voice_name2.voice:
		return f_score * 0.5
	if numbers_strategy == PREFER and num1 != num2:
		return f_score * 0.8
	return f_score

def _word_score(word1: str, word2: str) -> float:
	if word1 == word2:
		return 1.00
	if  word1 + 's' == word2 or \
		word2 + 's' == word1 or \
		word1 + 'es' == word2 or \
		word2 + 'es' == word1:
		return 0.75
	return 0.0

def score_candidates(ref: VoiceName, candidates: list,
	numbers_strategy: int = MATCH, voice_strategy: int = MATCH) -> list:
	"""
	Returns a list of FuzzResult (score, candidate).
	"candidates" must be a list of type FuzzCandidate.
	"""
	assert isinstance(ref, VoiceName)
	assert numbers_strategy in [IGNORE, MATCH, PREFER]
	assert voice_strategy in [IGNORE, MATCH, PREFER]
	return sorted([ FuzzResult(
		score(ref, candidate.voice_name, numbers_strategy, voice_strategy),
		candidate) for candidate in candidates ], key=attrgetter('score'), reverse = True)

def best_match(ref: VoiceName, candidates: list,
	numbers_strategy: int = MATCH, voice_strategy: int = MATCH) -> FuzzResult:
	"""
	Returns best matching FuzzResult (score, candidate)
	"candidates" must be a list of type FuzzCandidate.
	"""
	return score_candidates(ref, candidates, numbers_strategy, voice_strategy)[0]

@cache
def _name_parts(name: str) -> tuple:
	"""
	Returns a tuple(int, list), after the following is done:
		1. Lower case
		2. Substitute common abbreviations (like "F Horn")
		3. Split into words
		4. Strip out numeric words and return these as int

	(This is a cached function).
	"""
	name = name.lower()
	for sub in SUBSTITUTIONS:
		name = re.sub(sub[0], sub[1], name)
	words = re.split(SPLIT_WORDS_REGEX, name)
	for w_idx, word in enumerate(words):
		number = number_value(word)
		if number:
			words.pop(w_idx)
			break
	return (number, words)

@cache
def number_value(word: str) -> int:
	"""
	Returns a number value of the given word from NUMBERS.
	Returns 0 if not found.
	"""
	for i, list_ in enumerate(NUMBERS):
		if word in list_:
			return i + 1
	return 0


#  end mscore/fuzzy.py
