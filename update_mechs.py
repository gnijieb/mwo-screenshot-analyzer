#!/usr/bin/env python
# This file is part of mwo-screenshot-analyzer.
#
# mwo-screenshot-analyzer is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# mwo-screenshot-analyzer is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with mwo-screenshot-analyzer.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2016 gnijieb@gmail.com

import sys
import json
import urllib

def main():
	url = "http://mwo.smurfy-net.de/api/data/mechs.json"
	response = urllib.urlopen(url)
	data = json.load(response)

	Mechs = []
	
	for entry in data.values():
		Mechs.append(entry["translated_short_name"])
	Mechs.sort()
	
	with open("./basedata/mechs.txt", "w") as myfile:
		for mech in Mechs:
			if "(L)" in mech:
				mech = mech[:-3]
				myfile.write(mech+"\n")
			elif "(" not in mech:
				myfile.write(mech+"\n")
	print("Done")
	return
	
if __name__ == "__main__":
	main()