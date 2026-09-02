#  mscore/mscore/sigs.py
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
Provides functions used to identify a version of a score and its individual
channels, in order to skip parts which are unchanged since the last stem export.
"""
from node_soso import concise_xml
from hashlib import sha256
from pathlib import Path
from json import load, dump


def hashed(string):
	return sha256(string.encode()).hexdigest()

def part_signature(part):
	"""
	Returns a unique sha256 sum based on confguration + all staffs, useful for
	detecting changes to a part between current and previous versions
	"""
	xml = [ concise_xml(part.element) ]
	xml.extend([ concise_xml(measure.element)
		for staff in part.staffs()
		for measure in staff.measures() ])
	return hashed(''.join(xml))

def tempo_sig(score):
	"""
	Returns a unique sha256 sum.
	"""
	return hashed(''.join(f'{change.measure}{change.tempo}'
		for change in score.tempo_changes()))

def part_signatures(score):
	"""
	Returns a dictionary of { part_name, sha256 sum }
	"""
	return { part.name: part_signature(part) for part in score.parts() }


class ScoreSignature:
	"""
	Contains score signatures interpreted from a score.
	Reads and writes these signatures to a file, which is used to detect changes.
	"""

	def __init__(self, score):
		score_path = Path(score.filename)
		current_tempo_sig = tempo_sig(score)
		current_part_sigs = part_signatures(score)
		current_part_names = set(current_part_sigs.keys())
		self._sig_path = score_path.parent / ('.' + score_path.stem + '.sig')
		if self._sig_path.exists():
			with open(self._sig_path, 'r', encoding = 'utf-8') as fob:
				saved_sigs = load(fob)
			old_tempo_sig = saved_sigs['tempo_sig']
			old_part_sigs = saved_sigs['part_signatures']
			old_part_names = set(old_part_sigs.keys())
			self._deleted_parts = old_part_names - current_part_names
			self._new_parts = current_part_names - old_part_names
			intersection = current_part_names & old_part_names
			self._changed_parts = set(part_name for part_name in intersection
				if current_part_sigs[part_name] != old_part_sigs[part_name]
			) if current_tempo_sig == old_tempo_sig \
				else set(current_part_names)
		else:
			self._new_parts = current_part_names
			self._deleted_parts = set()
			self._changed_parts = set()
		self._new_sig = {
			'tempo_sig'			: current_tempo_sig,
			'part_signatures'	: current_part_sigs
		}

	def save(self):
		with open(self._sig_path, 'w', encoding = 'utf-8') as fob:
			dump(self._new_sig, fob)

	@property
	def new_parts(self):
		"""
		Returns a set of parts which are not in the .sig file.
		"""
		return self._new_parts

	@property
	def deleted_parts(self):
		"""
		Returns a set of parts in the .sig file which are not in the score.
		"""
		return self._deleted_parts

	@property
	def changed_parts(self):
		"""
		Returns a list of parts in the score whose signature has changed from the the
		.sig file.
		"""
		return self._changed_parts

	def __repr__(self):
		return f'<ScoreSignature at {self._sig_path}'


#  end mscore/mscore/sigs.py
