#  mscore/__init__.py
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
A python library for opening/inspecting/modifying MuseScore3 files.
"""
import os, sys, logging
from configparser import ConfigParser, NoSectionError, NoOptionError
from io import BytesIO
from pathlib import Path
from xml.etree.ElementTree import SubElement, parse as parse_xml
try:
	from functools import cache
except ImportError:
	from functools import lru_cache as cache
from functools import reduce
from operator import or_, add
from zipfile import ZipFile
from copy import deepcopy
from appdirs import user_config_dir, user_data_dir
from console_quiet import ConsoleQuiet
from node_soso import SmartNode, SmartTree

__version__ = "1.19.0"


CHANNEL_NAMES = ['normal', 'open', 'mute', 'arco', 'tremolo', 'crescendo',
				 'marcato', 'staccato', 'flageoletti', 'slap', 'pop', 'pizzicato']

CC_VOLUME		= 7
CC_BALANCE		= 8
CC_PAN			= 10
CC_BANK_MSB		= 0
CC_BANK_LSB		= 32

CC_NAMES = {
	CC_VOLUME	: 'CC_VOLUME',
	CC_BALANCE	: 'CC_BALANCE',
	CC_PAN		: 'CC_PAN',
	CC_BANK_MSB	: 'CC_BANK_MSB',
	CC_BANK_LSB	: 'CC_BANK_LSB'
}
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
		self.voice = None if voice is None else voice.lower()

	def __str__(self):
		return f'{self.instrument_name} ({self.voice or DEFAULT_VOICE})'

	def __repr__(self):
		return f'<{self.instrument_name}:{self.voice or DEFAULT_VOICE}>'

	def __eq__(self, other):
		return self.instrument_name == other.instrument_name \
			and self.voice == other.voice


class ChannelMoniker:
	"""
	Simple hashable class which can be used to identify a single channel in the global score.
	"""

	def __init__(self, part_name, channel_name):
		self._part_name = part_name
		self._channel_name = channel_name

	@property
	def part_name(self):
		return self._part_name

	@property
	def channel_name(self):
		return self._channel_name

	def __repr__(self):
		return f'<{self.part_name}:{self.channel_name}>'


def is_score(filename):
	"""
	Returns True if the given filename appears to be a MuseScore score.
	"""
	return Path(filename).suffix.lower() in ['.mscx', '.mscz']

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
	path = Path(user_config_dir('MuseScore')) / 'MuseScore3.ini'
	config = ConfigParser()
	config.read(path)
	return config

def instruments_file():
	"""
	Returns (Path) path to "instruments.xml"
	"""
	for key in ['paths\\instrumentlist1', 'paths\\instrumentlist2']:
		try:
			path = Path(ini_file().get('application', key))
			if path.exists():
				return path
		except NoSectionError, NoOptionError:
			pass
	for path in Path('/usr/share').glob('mscore*'):
		if path.is_dir():
			if path.joinpath('instruments.xml').exists():
				return path.joinpath('instruments.xml')
			if path.joinpath('instruments', 'instruments.xml').exists():
				return path.joinpath('instruments', 'instruments.xml')
	return None

@cache
def default_sound_fonts():
	"""
	Returns a list of Path objects, each pointing to one of the default soundfonts
	loaded when MuseScore starts.
	"""
	path = Path(user_data_dir('MuseScore')) / 'MuseScore3' / 'synthesizer.xml'
	if path.exists():
		return [ node.text for node in parse_xml(path).findall('.//Fluid/val') ]

@cache
def user_soundfont_dirs():
	"""
	Returns a list of Path objects, each pointing to one of the soundfont
	directories defined by the user.
	"""
	try:
		return [ Path(filename)
			for filename in ini_file()['application']['paths\\mySoundfonts'].strip('"').split(';') ]
	except KeyError, NoSectionError, NoOptionError:
		return []

@cache
def system_soundfont_dirs():
	"""
	Returns a list of Path objects, each pointing to one of the common system
	soundfont directories.
	"""
	return [ Path('/usr/share/sounds/sf2') ]

@cache
def user_soundfonts():
	"""
	Returns a list of Path objects, each pointing to one of the soundfonts found in
	the user -defined soundfount directories.
	"""
	return list(_iter_sf_paths(user_soundfont_dirs()))

@cache
def system_soundfonts():
	"""
	Returns a list of Path objects, each pointing to one of the soundfonts found in
	one of the common system soundfont directories
	"""
	return list(_iter_sf_paths(system_soundfont_dirs()))

def _iter_sf_paths(paths):
	for path in paths:
		yield from path.glob('*.sf2')


# ----------------------------
# MuseScore classes

class Score(SmartTree):
	"""
	Object -oriented interface to MuseScore score file (.mscx or .mscz)
	"""

	__default_sfnames = None
	__user_sfpaths = None
	__sys_sfpaths = None
	__sf2s = {}

	__zip_entries = None
	__zip_mscx_index = None

	USER_SF2 = 0
	SYSTEM_SF2 = 1
	MISSING_SF2 = 3

	# pylint: disable-next = super-init-not-called
	def __init__(self, filename):
		self._path = Path(filename)
		if self.extension == '.mscx':
			self.tree = parse_xml(filename)
		elif self.extension == '.mscz':
			with ZipFile(self.filename, 'r') as zipfile:
				self.__zip_entries = [
					{
						'info'	:info,
						'data'	:zipfile.read(info.filename)
					} for info in zipfile.infolist()
				]
			for idx, entry in enumerate(self.__zip_entries):
				if Path(entry['info'].filename).suffix.lower() == '.mscx':
					self.__zip_mscx_index = idx
					break
			if self.__zip_mscx_index is None:
				raise RuntimeError("No mscx entries found in zip file")
			with BytesIO(self.__zip_entries[self.__zip_mscx_index]['data']) as bob:
				self.tree = parse_xml(bob)
		else:
			raise ValueError(f'Unsupported file extension: "{self.extension}"')
		self.element = self.tree.getroot() # Necessary member of SmartTree
		self._score_node = self.element.find('./Score')
		self._parts = { part.name:part \
			for part in Part.from_elements(self.findall('./Part'), self) }

	# -----------------------------
	# Basic node functions

	def score_node(self):
		return self._score_node

	def find(self, path):
		return self._score_node.find(path)

	def findall(self, path):
		return self._score_node.findall(path)

	# -----------------------------
	# Save functions

	def save_as(self, filename):
		path = Path(filename)
		if path.suffix.lower() == '.mscz' and self.extension == '.mscx':
			raise RuntimeError('Cannot save score imported from .mscx to .mscz format')
		self._path = Path(filename)
		self.save()

	def save(self):
		if self.extension == '.mscx':
			self.tree.write(self.filename, xml_declaration = True, encoding = 'utf-8')
		elif self.extension == '.mscz':
			with BytesIO() as bob:
				self.tree.write(bob)
				self.__zip_entries[self.__zip_mscx_index]['data'] = bob.getvalue()
			with ZipFile(self.filename, 'w') as zipfile:
				for entry in self.__zip_entries:
					zipfile.writestr(entry['info'], entry['data'])

	@property
	def filename(self):
		return str(self._path)

	@property
	def name(self):
		return self._path.name

	@property
	def filetitle(self):
		return self._path.stem

	@property
	def extension(self):
		return self._path.suffix.lower()

	# -----------------------------
	# Element retrieval functions

	def parts(self):
		return self._parts.values()

	def instruments(self):
		return [ part.instrument() for part in self.parts() ]

	def channels(self):
		return [ channel \
			for instrument in self.instruments() \
			for channel in instrument.channels() ]

	def channel(self, part_name, channel_name):
		"""
		Returns Channel object.
		"""
		return self.part(part_name).instrument().channel(channel_name)

	def empty_channels(self):
		"""
		Returns a list of ChannelMoniker
		"""
		return reduce(add, [ part.empty_channels() for part in self.parts() ])

	def staffs(self):
		return [ staff \
			for part in self.parts() \
			for staff in part.staffs() ]

	def tempo_changes(self):
		"""
		Returns list of element.
		"""
		changes = [ ]
		for measure_number, measure_node in enumerate(self.findall('./Staff[@id="1"]/Measure')):
			for voice in measure_node.findall('./voice'):
				elem_list = list(voice)
				for index, node in enumerate(elem_list):
					if node.tag == 'Tempo':
						changes.append(TempoChange(node, measure_number,
							elem_list[index - 1] if index > 0 else None))
		return changes

	# -----------------------------
	# Informational functions

	@property
	def length(self):
		return list(self._parts.values())[0].staffs()[0].length

	def part(self, name):
		return self._parts[name]

	def part_names(self):
		return [ part.name for part in self.parts() ]

	def duplicate_part_names(self):
		a = self.part_names()
		return [ name for name in set(a) if a.count(name) > 1]

	def has_duplicate_part_names(self):
		return len(self.duplicate_part_names()) > 0

	def empty_parts(self):
		"""
		Returns list of (str) part names.
		"""
		return [ part.name for part in self.parts() if part.is_empty() ]

	def instrument_names(self):
		return [ p.instrument().name for p in self.parts() ]

	def channel_monikers(self):
		"""
		Returns a list of ChannelMoniker.
		"""
		return [ ChannelMoniker(part.name, channel.name) \
			for part in self.parts() \
			for channel in part.channels() ]

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

	# -----------------------------
	# Modification functions

	def concatenate_measures(self, source_score):
		"""
		Concatenates the measures from "source_score" at the end of this scores measures.
		"""
		for staff in self.findall('./Staff'):
			staff_id = staff.attrib['staff_id']
			source_measures = source_score.findall(f'./Staff[@staff_id="{staff_id}"]/Measure')
			staff.extend(source_measures)

	def remove_channel_synths(self):
		"""
		Removes all synthesizer related nodes in every channel. This includes MIDI
		program and assigned synthesizer.
		"""
		for channel in self.findall('Channel'):
			for node in channel.findall('controller'):
				channel.remove(node)
			for node in channel.findall('program'):
				channel.remove(node)
			for node in channel.findall('synti'):
				channel.remove(node)

	def disable_synth_effects(self):
		"""
		Disables reverb and chorus effects.
		Functions by setting nodes in //Synthesizer/master to "NoEffect"
		"""
		for path in ['./Synthesizer/master/val[@id="0"]',
			'./Synthesizer/master/val[@id="1"]']:
			for node in self.findall(path):
				node.text = 'NoEffect'

	def remove_solo_mute(self):
		"""
		Removes "solo" and "mute" flags for every channel.
		"""
		for channel in self.channels():
			channel.remove_solo_mute()

	def solo(self, part_name):
		"""
		Mute every channel in every part except the given part.
		"""
		for channel in self.channels():
			channel.solo(channel.part_name == part_name)
			channel.mute(channel.part_name != part_name)

	# -----------------------------
	# Pythony funcs

	def __repr__(self):
		return f'<Score "{self._path}">'


class Part(SmartNode):
	"""
	Represents a part in the score.

	Contains a single Instrument.
	"""

	def __init__(self, element, parent):
		super().__init__(element, parent)
		self._instrument = Instrument.from_element(self.find('./Instrument'), self)

	def delete(self):
		for staff in self.staffs():
			for element in self._parent.findall(f'./Staff[@id="{staff.id}"]'):
				self._parent.score_node().remove(element)
		self._parent.score_node().remove(self.element)

	def instrument(self):
		return self._instrument

	def channels(self):
		return self._instrument.channels()

	def replace_instrument(self, instrument):
		if not isinstance(instrument, Instrument):
			raise ValueError('Can only copy Instrument')
		new_instrument_node = deepcopy(instrument.element)
		old_instrument_node = self.find('Instrument')
		self.element.remove(old_instrument_node)
		self.element.append(new_instrument_node)

	def staffs(self):
		return Staff.from_elements(self.findall('Staff'), self)

	def staff(self, staff_id):
		for staff in self.staffs():
			if staff.staff_id == staff_id:
				return staff
		raise IndexError

	def is_empty(self):
		return all(staff.is_empty() for staff in self.staffs())

	def channel_switches_used(self):
		"""
		Returns a set of (str) StaffText/channelSwitch values
		"""
		sets = [ staff.channel_switches_used() for staff in self.staffs() ]
		return reduce(or_, sets, set())

	def channel_monikers(self):
		"""
		Returns a list of ChannelMoniker.
		"""
		return [ ChannelMoniker(self.name, channel.name)
			for channel in self.channels() ]

	def empty_channels(self):
		"""
		Returns a list of ChannelMoniker for channels that are never switched to.
		"""
		if self.is_empty():
			return self.channel_monikers()
		switches = self.channel_switches_used()
		default_name = self.instrument().default_channel().name
		return [ ChannelMoniker(self.name, channel.name) \
			for channel in self.channels() \
			if channel.name != default_name and channel.name not in switches ]

	@property
	def name(self):
		return self.element_text('trackName')

	# -----------------------------
	# Modification functions

	def copy_clef(self, source_part):
		"""
		Copy the staff definition from the given source_part to this Part.
		"""
		for source_staff, target_staff in zip(source_part.staffs(), self.staffs()):
			for node_name in ['defaultClef', 'defaultConcertClef', 'defaultTransposingClef']:
				source_node = source_staff.child(node_name, False)
				if not source_node is None:
					target_node = target_staff.child(node_name, True)
					target_node.text = source_node.text

	def center_pan(self):
		"""
		Centers the pan value for all channels in this Part.
		"""
		for channel in self.channels():
			channel.pan = 63

	# -----------------------------
	# Pythony funcs

	def __str__(self):
		return f'<Part "{self.name}">'


class Instrument(SmartNode):
	"""
	Represents an Instrument which plays a Part.
	"""

	def __init__(self, element, parent):
		super().__init__(element, parent)
		self._init_channels()

	def _init_channels(self):
		self._channels = { channel.name:channel \
			for channel in Channel.from_elements(self.findall('./Channel'), self) }

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

	def default_channel(self):
		"""
		Returns Channel object; the first defined channel.
		"""
		return Channel(self.find('./Channel[1]'), self)

	def channel_names(self):
		"""
		Returns all channels' name, including duplicates, if any.
		"""
		return [ channel.name for channel in
			Channel.from_elements(self.findall('./Channel'), self) ]

	def duplicate_channel_names(self):
		names = self.channel_names()
		return [ name for name in set(names) if names.count(name) > 1]

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
		"""
		Tries "long_name" and falls back on "track_name"
		"""
		return self.long_name or self.track_name

	@property
	def short_name(self):
		return self.element_text('shortName')

	@property
	def long_name(self):
		return self.element_text('longName')

	@property
	def track_name(self):
		return self.element_text('trackName')

	@property
	def musicxml_id(self):
		return self.element_text('instrumentId')

	@property
	def description(self):
		return self.element_text('description')

	@property
	def clef(self):
		"""
		Returns (str) like "G"
		Possible values are :
			G, F, PERC, G8vb, G8va, F8vb, G15ma, F8va, C1, C2, C3, C4, C5
		"""
		return self.element_text('clef')

	@property
	def barline_span(self):
		"""
		Returns (int) number of bars this instrument usually receives.
		"""
		return int(self.element_text('barlineSpan'))

	@property
	def amateur_pitch_range(self):
		"""
		Returns (tuple) the lowest pitch and the highest pitch which an ameteur is
		expected to be able to play.
		"""
		if s := self.element_text('aPitchRange'):
			lo, hi = s.split('-')
			return int(lo), int(hi)
		return None

	@property
	def professional_pitch_range(self):
		"""
		Returns (tuple) the lowest pitch and the highest pitch which a professional
		should be able to play.
		"""
		if s := self.element_text('pPitchRange'):
			lo, hi = s.split('-')
			return int(lo), int(hi)
		return None

	@property
	def transpose_diatonic(self):
		return self.element_text('transposeDiatonic')

	@property
	def transpose_chromatic(self):
		return self.element_text('transposeChromatic')

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
		new_channel_node = SubElement(self.element, 'Channel')
		new_channel_node.set('name', name)
		self._init_channels()
		return self.channel(name)

	def __str__(self):
		return f'<Instrument "{self.name}">'


class Channel(SmartNode):
	"""
	Represents a single audio channel. An instrument may contain multiple Channels,
	one for each articulation. These are set using "staff text" in MuseScore.
	"""

	def delete(self):
		self._parent.element.remove(self.element)

	def program(self):
		el = self.find('program')
		return None if el is None else int(el.attrib['value'])

	def bank_msb(self):
		return self.controller_value(CC_BANK_MSB, int)

	def bank_lsb(self):
		return self.controller_value(CC_BANK_LSB, int)

	def controller_value(self, ccid, type_ = None):
		el = self.find(f'controller[@ctrl="{ccid}"]')
		return None if el is None \
			else el.attrib['value'] if type_ is None \
			else type_(el.attrib['value'])

	def set_controller_value(self, ccid, value):
		if not 0 <= int(value) <= 127:
			raise ValueError('Invalid CC value')
		el = self.find(f'controller[@ctrl="{ccid}"]')
		if el is None:
			el = SubElement(self.element, 'controller')
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
		return self._parent.name

	@property
	def part_name(self):
		return self._parent._parent.name

	@property
	def moniker(self):
		return ChannelMoniker(self.part_name, self.name)

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
		value = int(value)
		if value < 1:
			raise ValueError('Channel midi_port must be greater than 0')
		node = self.child('midiPort')
		node.text = str(value - 1)

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
		value = int(value)
		if not 1 <= value <= 16:
			raise ValueError('Channel midi_channel must be betwen 1 and 16, inclusive')
		node = self.find('midiChannel')
		if node is None:
			node = SubElement(self.element, 'midiChannel')
		node.text = str(value - 1)

	@property
	def volume(self):
		return self.controller_value(CC_VOLUME, int)

	@volume.setter
	def volume(self, value):
		self.set_controller_value(CC_VOLUME, str(value))

	@property
	def balance(self):
		return self.controller_value(CC_BALANCE, int)

	@balance.setter
	def balance(self, value):
		self.set_controller_value(CC_BALANCE, str(value))

	@property
	def pan(self):
		return self.controller_value(CC_PAN, int)

	@pan.setter
	def pan(self, value):
		self.set_controller_value(CC_PAN, str(value))

	# -----------------------------
	# Modification functions

	def remove_solo_mute(self):
		"""
		Remove "solo" and "mute" child nodes.
		"""
		for path in ['solo', 'mute']:
			for node in self.findall(path):
				self.element.remove(node)

	def solo(self, enable = True):
		"""
		Creates a "solo" child node (if not exists)
		"""
		self.child('solo').text = '1' if enable else '0'

	def mute(self, enable = True):
		"""
		Create "solo" child node.
		"""
		self.child('mute').text = '1' if enable else '0'

	def __str__(self):
		return f'<Channel "{self.voice_name}">'


class Staff(SmartNode):
	"""
	Represents an entire staff of a Part, containing multiple Measures.
	"""

	def measures(self):
		score = self._parent.parent
		return Measure.from_elements(score.findall(f'./Staff[@id="{self.id}"]/Measure'))

	def is_empty(self):
		return all(measure.is_empty() for measure in self.measures())

	@property
	def length(self):
		return len(self.measures())

	def empty(self):
		"""
		Removes all but the first measure, and removes all chords and rests within it.
		"""
		score = self._parent.parent
		staff_node = score.find(f'./Staff[@id="{self.id}"]')
		measure_nodes = staff_node.findall('./Measure')
		for node in measure_nodes[1:]:
			staff_node.remove(node)
		for node in measure_nodes[0].getchildren():
			measure_nodes[0].remove(node)
		voice_node = SubElement(measure_nodes[0], 'voice')
		rest_node = SubElement(voice_node, 'Rest')
		node = SubElement(rest_node, 'durationType')
		node.text = 'measure'
		node = SubElement(rest_node, 'duration')
		node.text = '4/4'

	def channel_switches_used(self):
		"""
		Returns a set of (str) StaffText/channelSwitch values
		"""
		sets = [ measure.channel_switches() for measure in self.measures() ]
		return reduce(or_, sets, set())

	def part(self):
		return self._parent

	@property
	def color(self):
		"""
		Returns a dictionary of RBG values.
		"""
		node = self.child('color', False)
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
	"""
	Represents a single measure (in a single staff).
	"""

	def is_empty(self):
		return len(self.findall('.//Note')) == 0

	def channel_switches(self):
		"""
		Returns a set of (str) StaffText/channelSwitch values
		"""
		nodes = self.findall('./voice/StaffText/channelSwitch')
		return set() if nodes is None else { node.attrib['name'] for node in nodes }


class TempoChange(SmartNode):
	"""
	//Tempo node
	"""

	def __init__(self, node, measure_number, previous_element):
		super().__init__(node)
		self.tempo = float(self.find('tempo').text)
		self.measure = float(measure_number)
		if previous_element and previous_element.tag == 'location':
			fractions_node = previous_element.find('fractions')
			if fractions_node is not None:
				numerator, denominator = fractions_node.text.split('/', 1)
				self.measure -= float(numerator) / float(denominator)

	def __repr__(self):
		return f'<TempoChange {self.tempo} at measure {self.measure}>'


class MetaTag(SmartNode):
	"""
	Tags which provide additional information for a Score.
	"""

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
