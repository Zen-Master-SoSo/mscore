#  mscore/__init__.py
#
#  Copyright 2024 liyang <liyang@veronica>
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
A python library for opening/inspecting/modifying MuseScore3 files.
"""
import os, sys, logging, configparser, glob, io
import xml.etree.ElementTree as et
from zipfile import ZipFile
from pathlib import Path
from sf2utils.sf2parse import Sf2File
from console_quiet import ConsoleQuiet
from node_soso import SmartNode, dump

__version__ = "1.0.0"

CHANNEL_NAMES = [	'normal', 'open', 'mute', 'arco', 'tremolo', 'crescendo',
					'marcato', 'staccato', 'flageoletti', 'slap', 'pop', 'pizzicato']


# ----------------------------
# MuseScore classes

class Part(SmartNode):

	def instrument(self):
		return Instrument.from_element(self.find('Instrument'))

	@property
	def name(self):
		return self.element_text('trackName')

	def __str__(self):
		return f'<Part "{self.name}">'


class Instrument(SmartNode):

	def channels(self):
		return Channel.from_elements(self.findall('Channel'))

	@property
	def name(self):
		name = self.element_text('longName')
		if name is None:
			name = self.element_text('trackName')
		return name

	def musicxml_id(self):
		return self.element_text('instrumentId')

	def __str__(self):
		return f'<Instrument "{self.name}">'


class Channel(SmartNode):

	CC_VOLUME		= 7;
	CC_PAN			= 10;
	CC_BANK_MSB		= 0;
	CC_BANK_LSB		= 32;

	def program(self):
		el = self.find('program')
		return None if el is None else el.attrib['value']

	def bank_msb(self):
		msb = self.controller_value(self.CC_BANK_MSB)
		return -1 if msb is None else msb

	def bank_lsb(self):
		lsb = self.controller_value(self.CC_BANK_LSB)
		return -1 if lsb is None else lsb

	def controller_value(self, ccid):
		el = self.find('controller[@ctrl="%s"]' % ccid)
		return None if el is None else el.attrib['value']

	def idstring(self):
		return '%02d:%02d:%02d' % (
			int(self.bank_msb()),
			int(self.bank_lsb()),
			int(self.program())
		)

	@property
	def name(self):
		xmlname = self.attribute_value('name')
		return 'normal' if xmlname is None else xmlname

	@property
	def midi_port(self):
		"""
		Always returns the public (1-based) channel number.
		"""
		text = self.element_text('midiPort')
		return -1 if text is None else int(text) + 1

	@midi_port.setter
	def midi_port(self, value):
		"""
		"value" must be the public (1-based) channel number.
		The actual node value is set to one less.
		"""
		node = self.find('midiPort')
		if node is None:
			node = et.SubElement(self.element, 'midiPort')
		node.text = str(int(value) - 1)

	@property
	def midi_channel(self):
		"""
		Always returns the public (1-based) channel number.
		"""
		text = self.element_text('midiChannel')
		return -1 if text is None else int(text) + 1

	@midi_channel.setter
	def midi_channel(self, value):
		"""
		"value" must be the public (1-based) channel number.
		The actual node value is set to one less.
		"""
		node = self.find('midiChannel')
		if node is None:
			node = et.SubElement(self.element, 'midiChannel')
		node.text = str(int(value) - 1)

	def __str__(self):
		return f'<Channel "{self.name}">'


class Score():

	__default_sfnames = None
	__user_sfpaths = None
	__sys_sfpaths = None
	__sf2s = {}

	__zip_entries = None
	__zip_mscx_index = None

	USER_SF2 = 0
	SYSTEM_SF2 = 1
	MISSING_SF2 = 3

	def __init__(self, filename):
		self.filename = filename
		self.ext = os.path.splitext(filename)[-1]
		if self.ext == '.mscx':
			self.tree = et.parse(filename)
		elif self.ext == '.mscz':
			with ZipFile(self.filename, 'r') as zipfile:
				self.__zip_entries = [
					{
						'info'	:info,
						'data'	:zipfile.read(info.filename)
					} for info in zipfile.infolist()
				]
			for idx in range(len(self.__zip_entries)):
				if os.path.splitext(self.__zip_entries[idx]['info'].filename)[-1] == '.mscx':
					self.__zip_mscx_index = idx
					break
			if self.__zip_mscx_index is None:
				raise Exception("No mscx entries found in zip file")
			with io.BytesIO(self.__zip_entries[self.__zip_mscx_index]['data']) as bob:
				self.tree = et.parse(bob)
		else:
			raise Exception("Unsupported file extension: " + self.ext)

	def save(self):
		if self.ext == '.mscx':
			self.tree.write(self.filename, xml_declaration=True, encoding='utf-8')
		elif self.ext == '.mscz':
			with io.BytesIO() as bob:
				self.tree.write(bob)
				self.__zip_entries[self.__zip_mscx_index]['data'] = bob.getvalue()
			with ZipFile(self.filename, 'w') as zipfile:
				for entry in self.__zip_entries:
					zipfile.writestr(entry['info'], entry['data'])

	def dump(self):
		dump(self.tree)

	def find(self, path):
		return self.tree.find(path)

	def findall(self, path):
		return self.tree.findall(path)

	def parts(self):
		return Part.from_elements(self.findall('./Score/Part'))

	def instruments(self):
		return Instrument.from_elements(self.findall('./Score/Part/Instrument'))

	def channels(self):
		return Channel.from_elements(self.findall('./Score/Part/Instrument/Channel'))

	def part(self, name):
		for p in self.parts():
			if p.name == name:
				return p

	def part_names(self):
		return [ p.name for p in self.parts() ]

	def duplicate_part_names(self):
		a = self.part_names()
		return [ name for name in list(set(a)) if a.count(name) > 1]

	def has_duplicate_part_names(self):
		return len(self.duplicate_part_names()) > 0

	def instrument_names(self):
		return [ p.instrument().name for p in self.parts() ]

	def sound_fonts(self):
		return list(set( el.text for el in self.findall('.//Trackesizer/Fluid/val') ))

	@classmethod
	def default_sound_fonts(cls):
		if cls.__default_sfnames is None:
			filename = os.path.join(str(Path.home()), '.local/share/MuseScore/MuseScore3/trackesizer.xml')
			cls.__default_sfnames = [ node.text for node in et.parse(filename).findall('.//Fluid/val') ]
		return cls.__default_sfnames

	@classmethod
	def ini_file(cls):
		filename = os.path.join(str(Path.home()), '.config/MuseScore/MuseScore3.ini')
		config = configparser.ConfigParser()
		config.read(filename)
		return config

	@classmethod
	def user_soundfont_dirs(cls):
		return cls.ini_file()['application']['paths\mySoundfonts'].strip('"').split(';')

	@classmethod
	def system_soundfont_dirs(cls):
		return ['/usr/share/sounds/sf2']

	@classmethod
	def _iter_sf_paths(cls, dirs):
		for d in dirs:
			yield from glob.glob(f'{d}/*.sf2')

	@classmethod
	def user_soundfonts(cls):
		return list(cls._iter_sf_paths(cls.user_soundfont_dirs()))

	@classmethod
	def system_soundfonts(cls):
		return list(cls._iter_sf_paths(cls.system_soundfont_dirs()))

	@classmethod
	def sf2(cls, sf_name):
		if cls.__user_sfpaths is None:
			cls.__user_sfpaths = { os.path.basename(path):path for path in cls.user_soundfonts() }
			cls.__sys_sfpaths = { os.path.basename(path):path for path in cls.system_soundfonts() }
		if sf_name not in cls.__sf2s:
			if sf_name in cls.__user_sfpaths:
				logging.debug('Inspecting user soundfont "%s"', sf_name)
				cls.__sf2s[sf_name] = cls._get_parsed_sf2(cls.__user_sfpaths[sf_name])
			elif sf_name in cls.__sys_sfpaths:
				logging.debug('Inspecting user system "%s"', sf_name)
				cls.__sf2s[sf_name] = cls._get_parsed_sf2(cls.__sys_sfpaths[sf_name])
			else:
				raise Exception('SoundFont "%s" not found', sf_name)
		return cls.__sf2s[sf_name]

	@classmethod
	def _get_parsed_sf2(cls, filename):
		with open(filename, 'rb') as file:
			with ConsoleQuiet():
				return Sf2File(file)

	@classmethod
	def is_score(cls, filename):
		return os.path.splitext(filename)[-1] in ['.mscx', '.mscz']

	def __str__(self):
		return f'<Score "{self.filename}">'


#  end mscore/__init__.py
