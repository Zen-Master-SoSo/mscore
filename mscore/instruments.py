#  mscore/instruments.py
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
Provides XML parsing and object-oriented interface for "instruments.xml"
"""
import logging
from node_soso import SmartNode, SmartTree
from mscore import instruments_file, Instrument as _Instrument


class Instruments(SmartTree):
	"""
	Root tree parsed from "instruments.xml"
	"""

	def __new__(cls):
		if not hasattr(cls, 'instance'):
			cls.instance = super().__new__(cls)
		return cls.instance

	def __init__(self):
		super().__init__(instruments_file())
		self._groups = { group.name:group for group in \
			InstrumentGroup.from_elements(self.findall('./InstrumentGroup'), self) }
		self._genres = { genre.id:genre for genre in \
			Genre.from_elements(self.findall('./Genre'), self) }
		for instrument in self.instruments():
			for id in instrument.genres():
				self._genres[id]._instruments.append(instrument)

	def groups(self):
		return self._groups.values()

	def group(self, name):
		if name in self._groups:
			return self._groups[name]
		raise IndexError

	def genres(self):
		return self._genres.values()

	def genre(self, id):
		if id in self._genres:
			return self._genres[id]
		raise IndexError

	def instruments(self):
		for group in self._groups.values():
			yield from group.instruments()


class Genre(SmartNode):
	"""
	Object parsed from top-level "Genre" node
	"""

	def __init__(self, element, parent):
		super().__init__(element, parent)
		self._instruments = []

	@property
	def id(self):
		return self.attribute_value('id')

	@property
	def name(self):
		return self.element_text('name')

	def instruments(self):
		return self._instruments


class InstrumentGroup(SmartNode):
	"""
	Object parsed from top-level "InstrumentGroup" node
	"""

	@property
	def name(self):
		return self.element_text('name')

	def instruments(self):
		return Instrument.from_elements(self.findall('./Instrument'), self)



class Instrument(_Instrument):
	"""
	Object parsed from top-level "Instrument" node
	"""

	def genres(self):
		nodes = self.findall('./genre')
		return [ node.text for node in nodes ]


#  end mscore/instruments.py
