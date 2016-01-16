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
# Copyright 2015 gnijieb@gmail.com

from collections import namedtuple
from subprocess import call

# https://pypi.python.org/pypi/python-Levenshtein/0.12.0
# require package: python-dev, python-pip
# sudo pip install 'python-Levenshtein'
from Levenshtein import *

# https://pypi.python.org/pypi/pytesseract
# require package: python-imaging, tesseract-ocr
# sudo pip install 'pytesseract'
#try:
#	import Image, ImageFilter
#	print("Image imported")
#except ImportError:
from PIL import Image, ImageFilter, ImageOps, ImageEnhance
#	print("PIL Image imported")

import pytesseract

import re
import string
import shutil
from os import listdir
from os.path import isfile, join
import shutil
import time

DEBUG = 2
LOG   = 1
loglevel = DEBUG

RED    = "\033[91;1m"
GREEN  = "\033[92;1m"
YELLOW = "\033[93;1m"
ENDC   = "\033[0m"

class Configuration:
	player = None
	resinfo = None
	fnpattern = None
	dtformat = None
	
OffsetT = namedtuple("Offset", "x y")
SizeT = namedtuple("Size", "w h")
AreaT = namedtuple("Area", "offset size")
EntryT = namedtuple("Entry", "x, w")	# the x offset and width of e.g. playername in cropped entry
ImageT = namedtuple("Image", "resolution psr psrup psrdown psrnone map mode time result entrysize entryposx entryposy player mech status score kills assists damage cbills xp")

Image1920x1200 = ImageT("1920x1200",    # resolution
		OffsetT(1092, 677),		# psr pixel and corresponding color values for up/down/equal
		(168, 214, 96),			# psr up color (r,g,b)
		(255, 44, 44),			# psr down color (r,g,b)
		(255, 255, 0),			# psr none color (r,g,b)
        AreaT(OffsetT(845, 80), SizeT(252, 35)),         # map
        AreaT(OffsetT(1239, 80), SizeT(106, 35)),        # mode
        AreaT(OffsetT(1560, 80), SizeT(68, 35)),         # time
        AreaT(OffsetT(835, 165), SizeT(235, 45)),        # result
        SizeT(877, 23),                  # entry size
        650,                            # entry pos x
        [                               # entry pos y list
        240,         # entry 0
        266,         # entry 1
        292,         # entry 2
        318,         # entry 3

        350,         # entry 4
        376,         # entry 5
        402,         # entry 6
        428,         # entry 7

        461,         # entry 8
        487,         # entry 9
        512,         # entry 10
        537,         # entry 11

        576,         # entry 12
        603,         # entry 13
        629,         # entry 14
        655,         # entry 15

        687,         # entry 16
        712,         # entry 17
        738,         # entry 18
        764,         # entry 19

        798,         # entry 20
        823,         # entry 21
        849,         # entry 22
        874,         # entry 23
        ],
		EntryT(73, 240),		# player
		EntryT(315, 140),		# mech
		EntryT(457, 50),		# status (alive/dead)
		EntryT(595, 45),		# matchscore
		EntryT(692, 25),		# kills
		EntryT(757, 25),		# assists
		EntryT(827, 49),		# damage
		AreaT(OffsetT(350, 295), SizeT(300, 100)),		# cbills
		AreaT(OffsetT(1270, 295), SizeT(250, 100)),		# xp
        )

CONFIG = Configuration()
CONFIG.playername = "Beijing"
CONFIG.resinfo = Image1920x1200
CONFIG.fnpattern = r"\d{4}-\d{2}-\d{2} \d{2}-\d{2}-\d{2}" # FRAPS Screenshot filename datetime pattern
#CONFIG.fnpattern = r"\d{2}\.\d{2}\.\d{4}-\d{2}\.\d{2}\.\d{2}" # MWO Screenshot filename datetime pattern
CONFIG.dtformat = "%Y-%m-%d %H-%M-%S" # FRAPS Screenshot filename datetime format
#CONFIG.dtformat = "%m.%d.%Y-%H.%M.%S" # MWO Screenshot filename datetime format

Maps = (
	"Alpine Peaks",
	"Canyon Network",
	"Caustic Valley",
	"Crimson Strait",
	"Forest Colony",
	"Frozen City",
	"Frozen City Night",
	"HPG Manifold",
	"The Mining Collective",
	"River City",
	"Terra Therma",
	"Tourmaline Desert",
	"Viridian Bog"
)

Modes = (
	"Assault",
	"Conquest",
	"Skirmish"
)

PSR = (
	"Up",
	"Down",
	"None"
)

Mechs = (
	"LCT-1E", "LCT-1M", "LCT-1V", "LCT-1V(P)", "LCT-3M", "LCT-3S", "LCT-3V", "LCT-PB",
	"COM-1B", "COM-1D", "COM-2D", "COM-3A", "COM-TDK",
	"SDR-5D", "SDR-5K", "SDR-5K(C)", "SDR-5V", "SDR-A",
	"UM-R60", "UM-R60L", "UM-R63", "UM-R63(S)",
	"FS9-A", "FS9-E", "FS9-H", "FS9-K", "FS9-S", "FS9-S(C)",
	"JR7-D", "JR7-D(F)", "JR7-D(S)", "JR7-F", "JR7-F(C)", "JR7-K", "JR7-O",
	"PNT-10K", "PNT-10K(R)", "PNT-10P", "PNT-8Z", "PNT-9R",
	"RVN-2X", "RVN-3L", "RVN-3L(C)", "RVN-4X", "RVN-H",
	"WLF-1", "WLF-1A", "WLF-1B", "WLF-2", "WLF-2(R)",
	"MLX-A", "MLX-B", "MLX-C", "MLX-D", "MLX-PRIME", "MLX-PRIME(I)",
	"ACH-A", "ACH-B", "ACH-C", "ACH-PRIME", "ACH-PRIME(C)", "ACH-PRIME(I)",
	"KFX-C", "KFX-D", "KFX-PRIME", "KFX-PRIME(I)", "KFX-S",
	"ADR-A", "ADR-B", "ADR-D", "ADR-PRIME", "ADR-PRIME(I)",
	"JR7-IIC", "JR7-IIC(O)", "JR7-IIC-2", "JR7-IIC-3", "JR7-IIC-A",
	"CDA-2A", "CDA-2A(C)", "CDA-2B", "CDA-3C", "CDA-3F(L)", "CDA-3M", "CDA-X5",
	"BJ-1", "BJ-1(C)", "BJ-1DC", "BJ-1X", "BJ-3", "BJ-A",
	"VND-1AA", "VND-1R", "VND-1SIB", "VND-1X",
	"CN9-A", "CN9-A(C)", "CN9-AH", "CN9-AH(L)", "CN9-AL", "CN9-D", "CN9-YLW",
	"CRB-20", "CRB-27", "CRB-27(R)", "CRB-27B", "CRB-27SL",
	"ENF-4P", "ENF-4R", "ENF-4R(C)", "ENF-5D", "ENF-5D(R)", "ENF-5P",
	"HBK-4G", "HBK-4G(F)", "HBK-4H", "HBK-4J", "HBK-4P", "HBK-4P(C)", "HBK-4SP", "HBK-GI",
	"TBT-3C", "TBT-5J", "TBT-5N", "TBT-7K", "TBT-7M", "TBT-7M(C)", "TBT-LG",
	"GRF-1E", "GRF-1N", "GRF-1N(P)", "GRF-1S", "GRF-1S(C)", "GRF-2N", "GRF-3M",
	"KTO-18", "KTO-18(C)", "KTO-19", "KTO-20", "KTO-GB",
	"SHD-2D", "SHD-2D2", "SHD-2H", "SHD-2H(P)", "SHD-2H(C)", "SHD-2K", "SHD-5M", "SHD-GD",
	"WVR-6K", "WVR-6K(C)", "WVR-6R", "WVR-6R(P)", "WVR-7D(L)", "WVR-7K", "WVR-Q",
	"IFR-A", "IFR-B", "IFR-C", "IFR-D", "IFR-PRIME", "IFR-PRIME(I)",
	"SHC-A", "SHC-B", "SHC-P", "SHC-PRIME", "SHC-PRIME(I)",
	"HBK-IIC", "HBK-IIC(O)", "HBK-IIC-A", "HBK-IIC-B", "HBK-IIC-C",
	"NVA-A", "NVA-B", "NVA-C", "NVA-D(L)", "NVA-PRIME", "NVA-PRIME(I)", "NVA-S",
	"SCR-A", "SCR-B", "SCR-C", "SCR-D", "SCR-PRIME", "SCR-PRIME(I)", "SCR-PRIME(C)",
	"DRG-1C", "DRG-1N", "DRG-5N", "DRG-5N(C)", "DRG-FANG", "DRG-FLAME",
	"QKD-4G", "QKD-4G(C)", "QKD-4H", "QKD-5K", "QKD-IV4",
	"CPLT-A1", "CPLT-A1(C)", "CPLT-C1", "CPLT-C1(F)", "CPLT-C4", "CPLT-J", "CPLT-K2",
	"JM6-A", "JM6-A(C)", "JM6-DD", "JM6-FB", "JM6-S",
	"TDR-5S", "TDR-5S(P)", "TDR-TD", "TDR-5SS", "TDR-9S", "TDR-9SE", "TDR-9SE(C)",
	"CTF-0XP", "CTF-1X", "CTF-2X", "CTF-3D", "CTF-3D(C)", "CTF-4X", "CTF-IM",
	"GHR-5H", "GHR-5J", "GHR-5J(R)", "GHR-5N", "GHR-5P",
	"BL-6-KNT", "BL-6-KNT(R)", "BL-6B-KNT", "BL-7-KNT", "BL-7-KNT-L",
	"MAD-3R", "MAD-5D", "MAD-5M", "MAD-BH2",
	"ON1-K", "ON1-K(C)", "ON1-M", "ON1-P", "ON1-V", "ON1-VA",
	"MDD-A", "MDD-B", "MDD-C", "MDD-PRIME", "MDD-PRIME(I)",
	"EBJ-A", "EBJ-B", "EBJ-C", "EBJ-PRIME", "EBJ-PRIME(I)",
	"HBR-A", "HBR-B", "HBR-PRIME", "HBR-PRIME(I)",
	"SMN-B", "SMN-C", "SMN-D", "SMN-PRIME", "SMN-PRIME(I)",
	"ON1-IIC", "ON1-IIC(O)", "ON1-IIC-A", "ON1-IIC-B", "ON1-IIC-C",
	"TBR-A", "TBR-C", "TBR-C(C)", "TBR-D", "TBR-PRIME", "TBR-PRIME(I)", "TBR-S",
	"AWS-8Q", "AWS-8R", "AWS-8T", "AWS-8V", "AWS-9M", "AWS-PB",
	"VTR-9B", "VTR-9K", "VTR-9S", "VTR-9S(C)", "VTR-DS",
	"ZEU-5S", "ZEU-6S", "ZEU-6S(R)", "ZEU-6T", "ZEU-9S", "ZEU-9S2(L)",
	"BLR-1D", "BLR-1G", "BLR-1G(P)", "BLR-1GHE", "BLR-1S", "BLR-2C", "BLR-3M", "BLR-3C",
	"STK-3F", "STK-3F(C)", "STK-3H", "STK-4N", "STK-5M", "STK-5S", "STK-M",
	"HGN-732", "HGN-732B", "HGN-733", "HGN-733C", "HGN-733C(C)", "HGN-733P", "HGN-HM",
	"MAL-1P", "MAL-1R", "MAL-1R(R)", "MAL-2P", "MAL-MX90",
	"BNC-3E", "BNC-3M", "BNC-3M(C)", "BNC-3S", "BNC-LM",
	"AS7-BH", "AS7-D", "AS7-D(F)", "AS7-D-DC", "AS7-K", "AS7-RS", "AS7-RS(C)", "AS7-S", "AS7-S(L)",
	"KGC-000", "KGC-000(L)", "KGC-0000", "KGC-000B", "KGC-000B(C)",
	"GAR-A", "GAR-B", "GAR-C", "GAR-D", "GAR-PRIME", "GAR-PRIME(I)",
	"WHK-A", "WHK-B", "WHK-C", "WHK-PRIME", "WHK-PRIME(I)",
	"HGN-IIC", "HGN-IIC-A", "HGN-IIC-B", "HGN-IIC-C",
	"EXE-A", "EXE-B", "EXE-C(L)", "EXE-D", "EXE-PRIME", "EXE-PRIME(I)",
	"DWF-A", "DWF-B", "DWF-PRIME", "DWF-PRIME(I)", "DWF-S", "DWF-W", "DWF-W(C)",
)

def debug(txt):
	if loglevel >= DEBUG:
		print(YELLOW +	"[ DEBUG ] " + txt + ENDC)

def log(txt):
	if loglevel >= LOG:
		print(YELLOW +	"[  LOG  ] " + txt + ENDC)

def success(message):
	print(GREEN +	"[SUCCESS] " + message + ENDC)

def error(message):
	print(RED +		"[ ERROR ] " + message + ENDC)

def testlev(str1, str2):
	debug("Testing '" + str1 + "' against '" + str2 + "'")
	debug("Abs. Levenshtein distance: " + repr(distance(str1, str2)))
	debug("Jaro string similarity   : " + repr(jaro(str1, str2)))
	debug("String similarity        : " + repr(ratio(str1, str2)))

def test():
	debug(Config1920x1200.entryposy[0])

	goodstring = "Forest Colony"
	badstring =  "Bulimy_Rakers"
	halfgood =   "Boreal Felony"
	ocrstring =  "Fores1 Colony"

	testlev(goodstring, goodstring)

	testlev(goodstring, ocrstring)

	testlev(goodstring, halfgood)

	testlev(goodstring, badstring)

	testlev(goodstring, "Forest")
	testlev(goodstring, "Colony")

def isTimeFormat(input):
    try:
        time.strptime(input, "%M:%S")
        return True
    except ValueError:
        return False

def correctTimeFormat(input):
	mytime = time.strptime(input, "%M:%S")
	return time.strftime("%H:%M:%S", mytime)

def preprocess(img, id, part):
	R, G, B = 0, 1, 2
	tmp = img
	#source = tmp.split()
	#mask1 = source[R].point(lambda i: i == 255 and 255)
	#mask2 = source[G].point(lambda i: i > 150 and 255)
	#mask3 = source[B].point(lambda i: i > 150 and 255)
	#source[R].paste(mask1, None, None)
	#source[G].paste(mask2, None, None)
	#source[B].paste(mask3, None, None)
	#tmp = Image.merge(tmp.mode, source)
	# invert
	tmp = ImageOps.invert(tmp)
	# ENHANCE
	enhancer = ImageEnhance.Sharpness(tmp)
	tmp = enhancer.enhance(2.0)
	# convert to grayscale
	tmp = tmp.convert(mode="LA")
	# threshold greys to white
	tmp = tmp.point(lambda p: p > 60 and 255)
	#tmp.save("./intermediate/%s_part_%s.png" % (id, part))
	return tmp

def getmap(img, id, filename):
	(x, y, w, h) = (
		CONFIG.resinfo.map.offset.x,
		CONFIG.resinfo.map.offset.y,
		CONFIG.resinfo.map.size.w,
		CONFIG.resinfo.map.size.h
	)
	crop = img.crop((x, y, x+w, y+h))
	#crop.save("./intermediate/%s_map.png" % id)
	rawmap = pytesseract.image_to_string(crop, lang="eng", config="-psm 6")
	log("Raw Map: \"%s\" len=%s" % (rawmap, repr(len(rawmap))))
	# if map already matches an entry in the list, success
	for map in Maps:
		if rawmap.lower() == map.lower():
			success("Found Map: \"%s\" with distance=0" % map)
			return (0, map)
	
	dist = 100
	jaro_val = 0.0
	ratio_val = 0.0
	correctmap = None
	for mapname in Maps:
		#testlev(mapname.lower(), rawmap.lower())
		tmp = distance(mapname.lower(), rawmap.lower())
		if tmp < dist:
			dist = tmp
			jaro_val = jaro(mapname.lower(), rawmap.lower())
			ratio_val = ratio(mapname.lower(), rawmap.lower())
			correctmap = mapname

	# check the quality of the found string
	if dist > len(rawmap)*0.75 and jaro_val < 0.5 and ratio_val < 0.5:
		error("Could not determine map from input: \"%s\"" % rawmap)
		dist = None
	else:
		success("Found Map: \"%s\" with distance=%s" % (correctmap, repr(dist)))

	if dist == None:
		# Map could not be determined from input
		# ask for user input
		i = 0
		for mapname in Maps:
			print(repr(i+1) + ": " + mapname)
			i+=1
		x = -1
		print("Check image for map: " + filename)
		while x < 0 or x > len(Maps):
			x = int(input("Enter map number: "))
			log("Map entered: " + repr(x))
		correctmap = Maps[x-1]
		dist = 0

	return (dist, correctmap)

def getmode(img, id, filename):
	(x, y, w, h) = (
		CONFIG.resinfo.mode.offset.x,
		CONFIG.resinfo.mode.offset.y,
		CONFIG.resinfo.mode.size.w,
		CONFIG.resinfo.mode.size.h
	)
	crop = img.crop((x, y, x+w, y+h))
	#crop.save("./intermediate/%s_mode.png" % id)
	rawmode = pytesseract.image_to_string(crop, lang="eng", config="-psm 6")
	log("Raw Mode: \"%s\"" % rawmode)
	# if mode already matches an entry in the list, success
	for mode in Modes:
		if rawmode.lower() == mode.lower():
			success("Found Mode: \"%s\" with distance=0" % mode)
			return (0, mode)
	
	dist = 100
	jaro_val = 0.0
	ratio_val = 0.0
	correctmode = None
	for modename in Modes:
		#testlev(modename.lower(), rawmode.lower())
		tmp = distance(modename.lower(), rawmode.lower())
		if tmp < dist:
			dist = tmp
			jaro_val = jaro(modename.lower(), rawmode.lower())
			ratio_val = ratio(modename.lower(), rawmode.lower())
			correctmode = modename

	# check the quality of the found string
	if dist > 5 and jaro_val < 0.5 and ratio_val < 0.5:
		error("Could not determine mode from input: \"%s\"" % rawmode)
		dist = None
	else:
		success("Found Mode: \"%s\" with distance=%s" % (correctmode, repr(dist)))
	
	if dist == None:
		# Mode could not be determined from input
		# ask for user input
		i = 0
		for modename in Modes:
			print(repr(i+1) + ": " + modename)
			i+=1
		x = -1
		print("Check image for mode: " + filename)
		while x < 0 or x > len(Modes):
			x = int(input("Enter mode number: "))
			log("Mode entered: " + repr(x))
		correctmode = Modes[x-1]
		dist = 0

	return (dist, correctmode)

def gettime(img, id, filename):
	(x, y, w, h) = (
		CONFIG.resinfo.time.offset.x,
		CONFIG.resinfo.time.offset.y,
		CONFIG.resinfo.time.size.w,
		CONFIG.resinfo.time.size.h
	)
	crop = img.crop((x, y, x+w, y+h))
	#crop.save("./intermediate/%s_time.png" % id)
	rawtime = pytesseract.image_to_string(crop, lang="eng", config="-psm 6")
	log("Raw Time: \"%s\"" % rawtime)

	while not isTimeFormat(rawtime):
		error("Could not determine time from input: \"%s\"" % rawtime)
		print("Check image for time: " + filename)
		rawtime = raw_input("Enter time: ")
	
	return correctTimeFormat(rawtime)

def getplayerdata(img, id, filename):
	row = 0
	y = 0
	(x, w, h) =  (
		CONFIG.resinfo.entryposx,
		CONFIG.resinfo.entrysize.w,
		CONFIG.resinfo.entrysize.h
	)
	crop = None
	playerfound = None
	selectedrow = None
	dist = 100
	jaro_val = 0.0
	ratio_val = 0.0
	while row < 24:
		y = CONFIG.resinfo.entryposy[row]
		crop = img.crop((x, y, x+w, y+h))
		#debug("crop: " + repr(crop.size))
		#crop.load()
		#crop.save("./intermediate/%s_entry_%s.png" % (id, repr(row)))
		
		cropplayer = crop.crop((CONFIG.resinfo.player.x, 0, CONFIG.resinfo.player.w, h))
		#cropplayer.load()
		rawplayer = pytesseract.image_to_string(cropplayer, lang="eng", config="-psm 6")
		#debug("Raw Player: \"%s\"" % rawplayer)

		# if playername already matches, success
		if rawplayer.lower() == CONFIG.playername.lower():
			playerfound = rawplayer
			selectedrow = row
			dist = 0
			jaro_val = 1.0
			ratio_val = 1.0
			break

		#testlev(CONFIG.playername.lower(), rawplayer.lower())
		tmpdist = distance(CONFIG.playername.lower(), rawplayer.lower())
		tmpjaro_val = jaro(CONFIG.playername.lower(), rawplayer.lower())
		tmpratio_val = ratio(CONFIG.playername.lower(), rawplayer.lower())
		
		# check the quality of the found string
		if tmpdist <= dist and (tmpjaro_val >= 0.5 or tmpratio_val >= 0.5):
			playerfound = rawplayer
			selectedrow = row
			dist = tmpdist
			jaro_val = tmpjaro_val
			ratio_val = tmpratio_val
		row += 1
	
	success("Found Player: \"%s\" (searched for \"%s\") with distance=%s" % (playerfound, CONFIG.playername, repr(dist)))
	#crop.save("./intermediate/%s_player.png" % id)

	result = None
	if selectedrow < 12:
		result = "Victory"
	else:
		result = "Defeat"

	# get the data from selected entry row
	cropmech = crop.crop((CONFIG.resinfo.mech.x, 0, CONFIG.resinfo.mech.x + CONFIG.resinfo.mech.w, h))
	rawmech = pytesseract.image_to_string(cropmech, lang="eng", config="-psm 6")
	debug("Raw mech: \"%s\"" % rawmech)
	mechfound = False
	for mech in Mechs:
		if rawmech.lower() == mech.lower():
			mechfound = True
			correctmech = mech
			success("Found Mech: \"%s\" with distance=0" % mech)

	if not mechfound:
		dist = 100
		jaro_val = 0.0
		ratio_val = 0.0
		correctmech = None
		for mechname in Mechs:
			#testlev(modename.lower(), rawmode.lower())
			tmp = distance(mechname.lower(), rawmech.lower())
			if tmp < dist:
				dist = tmp
				jaro_val = jaro(mechname.lower(), rawmech.lower())
				ratio_val = ratio(mechname.lower(), rawmech.lower())
				correctmech = mechname

		# check the quality of the found string
		if dist > len(rawmech)*0.6 and jaro_val < 0.5 and ratio_val < 0.5:
			error("Could not determine mech from input: \"%s\"" % rawmech)
		else:
			mechfound = True
			success("Found Mech: \"%s\" with distance=%s" % (correctmech, repr(dist)))
		
		if not mechfound:
			# Mode could not be determined from input
			# ask for user input
			i = 0
			for mechname in Mechs:
				print(repr(i+1) + ": " + mechname)
				i+=1
			x = -1
			print("Check image for mech: " + filename)
			while x < 0 or x > len(Mechs):
				x = int(input("Enter mech number: "))
				log("Mech entered: " + repr(x))
			correctmech = Mechs[x-1]

	# remove brackets in mechname (e.g. (C), (I), (S) and so on)
	correctmech = re.sub(r"\(.\)", "", correctmech)
	
	cropstatus = crop.crop((CONFIG.resinfo.status.x, 0, CONFIG.resinfo.status.x + CONFIG.resinfo.status.w, h))
	rawstatus = pytesseract.image_to_string(cropstatus, lang="eng", config="-psm 6")
	dist = distance("alive", rawstatus.lower())
	status = 0
	if dist >= 4:
		# dead
		status = 1
	
	cropscore = crop.crop((CONFIG.resinfo.score.x, 0, CONFIG.resinfo.score.x + CONFIG.resinfo.score.w, h))
	rawscore = pytesseract.image_to_string(cropscore, lang="eng", config="-psm 6")
	try:
		score = int(rawscore)
	except ValueError:
		error("Could not determine match score from input: \"%s\"" % rawscore)
		print("Check image for match score: " + filename)
		score = int(input("Enter match score: "))

	cropkills = crop.crop((CONFIG.resinfo.kills.x, 0, CONFIG.resinfo.kills.x + CONFIG.resinfo.kills.w, h))
	rawkills = pytesseract.image_to_string(cropkills, lang="eng", config="-psm 6")
	try:
		kills = int(rawkills)
	except ValueError:
		error("Could not determine kills from input: \"%s\"" % rawkills)
		print("Check image for kills: " + filename)
		kills = int(input("Enter kills: "))

	cropassists = crop.crop((CONFIG.resinfo.assists.x, 0, CONFIG.resinfo.assists.x + CONFIG.resinfo.assists.w, h))
	rawassists = pytesseract.image_to_string(cropassists, lang="eng", config="-psm 6")
	try:
		assists = int(rawassists)
	except ValueError:
		error("Could not determine assists from input: \"%s\"" % rawassists)
		print("Check image for assists: " + filename)
		assists = int(input("Enter assists: "))

	cropdamage = crop.crop((CONFIG.resinfo.damage.x, 0, CONFIG.resinfo.damage.x + CONFIG.resinfo.damage.w, h))
	rawdamage = pytesseract.image_to_string(cropdamage, lang="eng", config="-psm 6")
	try:
		damage = int(rawdamage)
	except ValueError:
		error("Could not determine damage from input: \"%s\"" % rawdamage)
		print("Check image for damage: " + filename)
		damage = int(input("Enter damage: "))

	return (result, correctmech, status, score, kills, assists, damage)

def getcbills(img, id, filename):
	(x, y, w, h) =  (
		CONFIG.resinfo.cbills.offset.x,
		CONFIG.resinfo.cbills.offset.y,
		CONFIG.resinfo.cbills.size.w,
		CONFIG.resinfo.cbills.size.h,
	)
	crop = img.crop((x, y, x+w, y+h))
	#crop.save("./intermediate/%s_cbills.png" % id)
	rawcbills = pytesseract.image_to_string(crop, lang="eng", config="-psm 6")
	rawcbills = rawcbills.replace(",", "")
	rawcbills = rawcbills.replace(" ", "")

	try:
		cbills = int(rawcbills)
	except ValueError:
		error("Could not determine C-Bills from input: \"%s\"" % rawcbills)
		print("Check image for C-Bills: " + filename)
		cbills = int(input("Enter C-Bills: "))

	return cbills

def getxp(img, id, filename):
	(x, y, w, h) =  (
		CONFIG.resinfo.xp.offset.x,
		CONFIG.resinfo.xp.offset.y,
		CONFIG.resinfo.xp.size.w,
		CONFIG.resinfo.xp.size.h,
	)
	crop = img.crop((x, y, x+w, y+h))
	#crop.save("./intermediate/%s_xp.png" % id)
	rawxp = pytesseract.image_to_string(crop, lang="eng", config="-psm 6")
	rawxp = rawxp.replace(",", "")
	rawxp = rawxp.replace(" ", "")

	try:
		xp = int(rawxp)
	except ValueError:
		error("Could not determine XP from input: \"%s\"" % rawxp)
		print("Check image for XP: " + filename)
		xp = int(input("Enter XP: "))

	return xp

def checkpixelcolor((r1,g1,b1), (r2, g2, b2), factor):
	if r1 >= r2-255*factor and r1 <= r2+255*factor and \
		g1 >= g2-255*factor and g1 <= g2+255*factor and \
		b1 >= b2-255*factor and b1 <= b2+255*factor:
		return True
	else:
		return False

def getpsr(img, id, filename):
	row = 0
	y = 0
	(x, y) =  (
		CONFIG.resinfo.psr.x,
		CONFIG.resinfo.psr.y,
	)
	pixel = img.getpixel((x, y))
	debug(repr(pixel))
	if checkpixelcolor(CONFIG.resinfo.psrup, pixel, 0.1):
		return "Up"
	elif checkpixelcolor(CONFIG.resinfo.psrnone, pixel, 0.1):
		return "None"
	elif checkpixelcolor(CONFIG.resinfo.psrdown, pixel, 0.25):
		return "Down"
	else:
		error("Could not determine PSR")
		# PSR could not be determined from pixel
		# ask for user input
		i = 0
		for psr in PSR:
			print(repr(i+1) + ": " + psr)
			i+=1
		x = -1
		print("Check image for PSR: " + filename)
		while x < 0 or x > len(PSR):
			x = int(input("Enter PSR number: "))
			log("PSR entered: " + repr(x))
		return PSR[x-1]

def main():
	files = [f for f in listdir("./input") if isfile(join("./input", f))]
	files.sort()
	files.reverse()
	print(files)
	if len(files)%2 != 0:
		error("Odd number of files found: %d" % len(files))
		return
	
	count = len(files)/2
	
	while len(files) != 0:
		(result, mech, status, score, kills, assists, damage, cbills, xp, psr) = (None,)*10
		file1 = files.pop()
		file2 = files.pop()
		log(file1 + " " + file2)

		match = re.search(CONFIG.fnpattern, file1)
		if not match:
			error("Screenshot filename pattern: No match")
			continue
		datetime = time.strptime(match.group(), CONFIG.dtformat)

		file1 = "./input/" + file1
		file2 = "./input/" + file2
		id = time.strftime("%Y-%m-%d %H-%M-%S", datetime)
		filedate = time.strftime("%Y-%m-%d %H:%M:%S", datetime)
		with Image.open(file1) as img:
			img = preprocess(img, id, "team")
			(dist, map) = getmap(img, id, file1)
			debug("Found Map: \"%s\" with distance=%s" % (map, repr(dist)))
			(dist, mode) = getmode(img, id, file1)
			debug("Found Mode: \"%s\" with distance=%s" % (mode, repr(dist)))
			mytime = gettime(img, id, file1)
			(result, mech, status, score, kills, assists, damage) = getplayerdata(img, id, file1)
		with Image.open(file2) as img:
			psr = getpsr(img, id, file2)
			img = preprocess(img, id, "player")
			cbills = getcbills(img, id, file2)
			xp = getxp(img, id, file2)

		debug("%s,%s,%s,%s,%s,%d,%d,%d,%d,%d,%d,%d,%s,%s" % (filedate, result, mech, map, mode, status, score, kills, assists, damage, xp, cbills, psr, mytime))

		shutil.move(file1, "./processed")
		shutil.move(file2, "./processed")

		with open("./output/data.csv", "a") as myfile:
			myfile.write("%s,%s,%s,%s,%s,%d,%d,%d,%d,%d,%d,%d,%s,%s\n" % (filedate, result, mech, map, mode, status, score, kills, assists, damage, xp, cbills, psr, mytime))

		print

	success("Finished")
	return
	
if __name__ == "__main__":
	main()