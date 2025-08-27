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
from os.path import join, basename, splitext, exists
from appdirs import user_config_dir, user_data_dir
import xml.etree.ElementTree as et
try:
	from functools import cache
except ImportError:
	from functools import lru_cache as cache
from zipfile import ZipFile
from copy import deepcopy
from sf2utils.sf2parse import Sf2File
from console_quiet import ConsoleQuiet
from node_soso import SmartNode, SmartTree

__version__ = "1.12.0"

CHANNEL_NAMES = ['normal', 'open', 'mute', 'arco', 'tremolo', 'crescendo',
				 'marcato', 'staccato', 'flageoletti', 'slap', 'pop', 'pizzicato']
DEFAULT_VOICE	= 'normal'


class VoiceName:
	"""
	Simply holds a pair of properties:
		"instrument_name", "voice"
	...and provides a string representation.

	Comparison may be made with "==", i.e.
		if voicename1 == voicename2:
	"""

	def __init__(self, instrument_name, voice):
		self.instrument_name = instrument_name
		self.voice = voice

	def __str__(self):
		return f'{self.instrument_name} ({self.voice or DEFAULT_VOICE})'

	def __eq__(self, other):
		return self.instrument_name == other.instrument_name \
			and self.voice == other.voice

def is_score(filename):
	return splitext(filename)[-1] in ['.mscx', '.mscz']

def ini_file():
	"""
	Returns a ConfigParser object, which may be used like this:

	cp = ini_file()
	for section in cp.sections():
		print(f'Section "{section}"')
		for option in cp.options(section):
			print(f'  Option "{option}"')

	The ConfigParser may be used to modify the .ini file, but that is outside of
	the (current) scope of this project. USE AT YOUR OWN RISK!
	"""
	filename = join(user_config_dir('MuseScore'), 'MuseScore3.ini')
	config = configparser.ConfigParser()
	config.read(filename)
	return config

def instruments_file():
	"""
	Returns (str) path to "instruments.xml"
	"""
	for key in ['paths\instrumentlist1', 'paths\instrumentlist2']:
		filename = ini_file().get('application', key)
		if exists(filename):
			return filename

@cache
def default_sound_fonts():
	filename = join(user_data_dir('MuseScore'), 'MuseScore3', 'synthesizer.xml')
	return [ node.text for node in et.parse(filename).findall('.//Fluid/val') ]

@cache
def user_soundfont_dirs():
	return ini_file()['application']['paths\mySoundfonts'].strip('"').split(';')

@cache
def system_soundfont_dirs():
	return ['/usr/share/sounds/sf2']

@cache
def user_soundfonts():
	return list(_iter_sf_paths(user_soundfont_dirs()))

@cache
def system_soundfonts():
	return list(_iter_sf_paths(system_soundfont_dirs()))

@cache
def _user_sfpaths():
	return { basename(path):path for path in user_soundfonts() }

@cache
def _system_sfpaths():
	return { basename(path):path for path in system_soundfonts() }

@cache
def sf2(sf_name):
	if sf_name in _user_sfpaths():
		logging.debug('Inspecting user soundfont "%s"', sf_name)
		return _get_parsed_sf2(_user_sfpaths()[sf_name])
	if sf_name in _system_sfpaths():
		logging.debug('Inspecting user system "%s"', sf_name)
		return _get_parsed_sf2(_system_sfpaths()[sf_name])
	raise Exception(f'SoundFont "{sf_name}" not found')

def _iter_sf_paths(dirs):
	for d in dirs:
		yield from glob.glob(f'{d}/*.sf2')

def _get_parsed_sf2(filename):
	with open(filename, 'rb') as file:
		with ConsoleQuiet():
			return Sf2File(file)


# ----------------------------
# MuseScore classes

class Score(SmartTree):

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
		self.basename = basename(filename)
		self.ext = splitext(filename)[-1]
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
			for idx, entry in enumerate(self.__zip_entries):
				if splitext(entry['info'].filename)[-1] == '.mscx':
					self.__zip_mscx_index = idx
					break
			if self.__zip_mscx_index is None:
				raise RuntimeError("No mscx entries found in zip file")
			with io.BytesIO(self.__zip_entries[self.__zip_mscx_index]['data']) as bob:
				self.tree = et.parse(bob)
		else:
			raise ValueError('Unsupported file extension: "{self.ext}"')
		self.element = self.tree.getroot() # Necessary member of SmartTree
		self._score_node = self.element.find('./Score')
		self._parts = { part.name:part \
			for part in Part.from_elements(self.findall('./Part'), self) }

	def find(self, path):
		return self._score_node.find(path)

	def findall(self, path):
		return self._score_node.findall(path)

	def save_as(self, filename):
		ext = splitext(filename)[-1]
		if ext == '.mscz' and self.ext == '.mscx':
			raise RuntimeError('Cannot save score imported from .mscx to .mscz format')
		self.filename = filename
		self.ext = ext
		self.save()

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

	def parts(self):
		return self._parts.values()

	def instruments(self):
		return [ part.instrument() for part in self.parts() ]

	def channels(self):
		return [ channel \
			for instrument in self.instruments() \
			for channel in instrument.channels() ]

	def staffs(self):
		return [ staff \
			for part in self.parts() \
			for staff in part.staffs() ]

	def part(self, name):
		return self._parts[name]

	def part_names(self):
		return [ part.name for part in self.parts() ]

	def duplicate_part_names(self):
		a = self.part_names()
		return [ name for name in set(a) if a.count(name) > 1]

	def has_duplicate_part_names(self):
		return len(self.duplicate_part_names()) > 0

	def instrument_names(self):
		return [ p.instrument().name for p in self.parts() ]

	def concatenate_measures(self, source_score):
		for staff in self.findall('./Staff'):
			id = staff.attrib['id']
			source_measures = source_score.findall(f'./Staff[@id="{id}"]/Measure')
			staff.extend(source_measures)

	def meta_tags(self):
		"""
		Returns a list of MetaTag objects.
		"""
		return MetaTag.from_elements(self.findall('./metaTag'))

	def meta_tag(self, name):
		"""
		Returns a list of MetaTag objects.
		"""
		node = self.find(f'./metaTag[@name="{name}"]')
		return None if node is None else MetaTag(node)

	def sound_fonts(self):
		return list(set( el.text for el in self.findall('.//Synthesizer/Fluid/val') ))

	def __str__(self):
		return f'<Score "{self.filename}">'


class Part(SmartNode):

	def __init__(self, element, parent):
		super().__init__(element, parent)
		self._instrument = Instrument.from_element(self.find('./Instrument'), self)

	def instrument(self):
		return self._instrument

	def replace_instrument(self, instrument):
		if not isinstance(instrument, Instrument):
			raise ValueError('Can only copy Instrument')
		new_instrument_node = deepcopy(instrument.element)
		old_instrument_node = self.find('Instrument')
		self.element.remove(old_instrument_node)
		self.element.append(new_instrument_node)

	def staffs(self):
		return Staff.from_elements(self.findall('Staff'), self)

	def staff(self, id):
		for staff in self.staffs():
			if staff.id == id:
				return staff
		raise IndexError

	@property
	def name(self):
		return self.element_text('trackName')

	def __str__(self):
		return f'<Part "{self.name}">'


class Instrument(SmartNode):

	def __init__(self, element, parent):
		super().__init__(element, parent)
		self._init_channels()

	def _init_channels(self):
		self._channels = { chan.name:chan \
			for chan in Channel.from_elements(self.findall('Channel'), self) }

	def channels(self):
		"""
		Returns list of Channel objects.
		"""
		return self._channels.values()

	def channel(self, name):
		"""
		Returns list of Channel objects.
		"""
		return self._channels[name]

	def channel_names(self):
		"""
		Returns all channels' name, including duplicates, if any.
		"""
		return [ channel.name for channel in self.channels() ]

	def duplicate_channel_names(self):
		a = self.channel_names()
		return [ name for name in set(a) if a.count(name) > 1]

	def has_duplicate_channel_names(self):
		return len(self.duplicate_channel_names()) > 0

	def dedupe_channels(self):
		unique_channel_names = set(self.channel_names())
		channels = self.channels()
		for channel in channels:
			if channel.name in unique_channel_names:
				unique_channel_names.remove(channel.name)
			else:
				self.element.remove(channel.element)
		self._init_channels()

	@property
	def name(self):
		return self.long_name or self.track_name

	@property
	def long_name(self):
		return self.element_text('longName')

	@property
	def track_name(self):
		return self.element_text('trackName')

	@property
	def short_name(self):
		return self.element_text('shortName')

	@property
	def musicxml_id(self):
		return self.element_text('instrumentId')

	def clear_synth(self):
		for channel in self.findall('Channel'):
			for node in channel.findall('controller'):
				channel.remove(node)
			for node in channel.findall('program'):
				channel.remove(node)
			for node in channel.findall('synti'):
				channel.remove(node)

	def remove_channel(self, name):
		node = self.find(f'Channel[@name="{name}"]')
		if node:
			self.element.remove(node)
		self._init_channels()

	def add_channel(self, name):
		"""
		Returns Channel
		"""
		if self.find(f'Channel[@name="{name}"]'):
			raise RuntimeError(f'Channel "{name}" already exists')
		new_channel_node = et.SubElement(self.element, 'Channel')
		new_channel_node.set('name', name)
		self._init_channels()
		return self.channel(name)

	def __str__(self):
		return f'<Instrument "{self.name}">'


class Channel(SmartNode):

	CC_VOLUME		= 7
	CC_BALANCE		= 8
	CC_PAN			= 10
	CC_BANK_MSB		= 0
	CC_BANK_LSB		= 32

	def program(self):
		el = self.find('program')
		return None if el is None else int(el.attrib['value'])

	def bank_msb(self):
		return self.controller_value(self.CC_BANK_MSB, int)

	def bank_lsb(self):
		return self.controller_value(self.CC_BANK_LSB, int)

	def controller_value(self, ccid, type_ = None):
		el = self.find(f'controller[@ctrl="{ccid}"]')
		return None if el is None \
			else el.attrib['value'] if type_ is None \
			else type_(el.attrib['value'])

	def set_controller_value(self, ccid, value):
		el = self.find(f'controller[@ctrl="{ccid}"]')
		if el is None:
			el = et.SubElement(self.element, 'controller')
			el.set('ctrl', str(ccid))
		el.set('value', value)

	def idstring(self):
		return '%02d:%02d:%02d' % (
			self.bank_msb() or -1,
			self.bank_lsb() or -1,
			self.program() or -1
		)

	@property
	def name(self):
		return self.attribute_value('name', 'normal')

	@property
	def instrument_name(self):
		return self.parent.name

	@property
	def voice_name(self):
		return VoiceName(self.instrument_name, self.name)

	@property
	def midi_port(self):
		"""
		Always returns the public (1-based) channel number.
		"""
		text = self.element_text('midiPort')
		return None if text is None else int(text) + 1

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
		return None if text is None else int(text) + 1

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

	@property
	def volume(self):
		return self.controller_value(self.CC_VOLUME, int)

	@volume.setter
	def volume(self, value):
		self.set_controller_value(self.CC_VOLUME, str(value))

	@property
	def balance(self):
		return self.controller_value(self.CC_BALANCE, int)

	@balance.setter
	def balance(self, value):
		self.set_controller_value(self.CC_BALANCE, str(value))

	@property
	def pan(self):
		return self.controller_value(self.CC_PAN, int)

	@pan.setter
	def pan(self, value):
		self.set_controller_value(self.CC_PAN, str(value))

	def __str__(self):
		return f'<Channel "{self.name}">'


class Staff(SmartNode):

	def measures(self):
		score = self.parent.parent
		return Measure.from_elements(score.findall(f'./Staff[@id="{self.id}"]/Measure'))

	@property
	def color(self):
		"""
		Returns a dictionary of RBG values.
		"""
		node = self.find('color')
		return None if node is None else {
			'r'	: node.attrib['r'],
			'g'	: node.attrib['g'],
			'b'	: node.attrib['b'],
			'a'	: node.attrib['a']
		}

	@color.setter
	def color(self, rgba_dict):
		"""
		Set the color of this Staff.
		rgba_dict must be a dict containing "r", "g", "b" and "a" keys, having integer
		values in the range 0 - 255.
		"""
		node = self.child('color')
		node.set('r', str(rgba_dict['r']))
		node.set('g', str(rgba_dict['g']))
		node.set('b', str(rgba_dict['b']))
		node.set('a', str(rgba_dict['a']))

	@property
	def id(self):
		return self.attribute_value('id')

	@property
	def type(self):
		type_node = self.find('./StaffType')
		try:
			return f'{type_node.attrib["group"]} {self.element_text("./StaffType/name")}'
		except Exception:
			return ''

	@property
	def clef(self):
		return self.element_text('./defaultClef', self.element_text('./defaultConcertClef', 'G'))

	def __str__(self):
		return f'<Staff "{self.id}">'


class Measure(SmartNode):

	def is_empty(self):
		return len(self.find_all('.//Note')) == 0


class MetaTag(SmartNode):

	@property
	def name(self):
		return self.attribute_value('name')

	@property
	def value(self):
		return self.element.text

	@value.setter
	def value(self, value):
		self.element.text = str(value)

	def __str__(self):
		return f'{self.name}: {self.value}'


#  end mscore/__init__.py
