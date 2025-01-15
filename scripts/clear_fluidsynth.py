#  /mnt/data-drive/docs/MuseScore3/Templates/clear-fluid-settings.py
#
#  Copyright 2025 liyang <liyang@veronica>
#
import logging
import argparse
from mscore import Score

def main():
	p = argparse.ArgumentParser()
	p.add_argument('Filename', type=str, help="Required argument")
	logging.basicConfig(
		level=logging.DEBUG,
		format="[%(filename)24s:%(lineno)3d] %(message)s"
	)
	options = p.parse_args()
	score = Score(options.Filename)
	for instrument in score.instruments():
		for node in instrument.findall('Articulation[@name]'):
			instrument.element.remove(node)
		for node in instrument.findall('trackName'):
			instrument.element.remove(node)
		for channel in instrument.findall('Channel'):
			for node in channel.findall('controller'):
				channel.remove(node)
			for node in channel.findall('program'):
				node.attrib['value'] = '1'
			for node in channel.findall('synti'):
				node.text = 'Zerberus'
	score.save()

if __name__ == "__main__":
	main()

#  /mnt/data-drive/docs/MuseScore3/Templates/clear-fluid-settings.py
