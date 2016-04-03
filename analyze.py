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
import re
import string
import shutil
from os import listdir
from os.path import isfile, join
import shutil
import time
import ConfigParser
import getopt

from Levenshtein import *
from PIL import Image, ImageFilter, ImageOps, ImageEnhance
import pytesseract

DEBUG = 2
LOG   = 1
loglevel = DEBUG

#RED    = "\033[91;1m"
#GREEN  = "\033[92;1m"
#YELLOW = "\033[93;1m"
#ENDC   = "\033[0m"
RED = ""
GREEN = ""
YELLOW = ""
ENDC = ""

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

PixelT = namedtuple("Pixel", "x y")
ColorT = namedtuple("Color", "r g b")
RectangleT = namedtuple("Rectangle", "x1 y1 x2 y2")
ImageNewT = namedtuple("ImageNew", "resolution psr psrup psrdown psrnone map mode time result entrysize entryposx entryposy player mech status score kills assists damage cbills xp")

Image1920x1200new = ImageNewT("1920x1200",    # resolution
		PixelT(1092, 677),		# psr pixel and corresponding color values for up/down/equal
		ColorT(168, 214, 96),			# psr up color (r,g,b)
		ColorT(255, 44, 44),			# psr down color (r,g,b)
		ColorT(255, 255, 0),			# psr none color (r,g,b)
        RectangleT(845, 80, 1097, 115),	# map
        RectangleT(1109, 80, 1345, 115),	# mode
        RectangleT(1560, 80, 1628, 115),	# time
        RectangleT(835, 165, 1070, 210),	# result
		[
        RectangleT(650, 240, 650+877, 240+23),		# entry row 1
        RectangleT(650, 266, 650+877, 266+23),		# entry row 2
        RectangleT(650, 292, 650+877, 292+23),		# entry row 3
        RectangleT(650, 318, 650+877, 318+23),		# entry row 4
        RectangleT(650, 350, 650+877, 350+23),		# entry row 5
        RectangleT(650, 376, 650+877, 376+23),		# entry row 6
        RectangleT(650, 402, 650+877, 402+23),		# entry row 7
        RectangleT(650, 428, 650+877, 428+23),		# entry row 8
        RectangleT(650, 461, 650+877, 461+23),		# entry row 9
        RectangleT(650, 487, 650+877, 487+23),		# entry row 10
        RectangleT(650, 512, 650+877, 512+23),		# entry row 11
        RectangleT(650, 537, 650+877, 537+23),		# entry row 12
        RectangleT(650, 576, 650+877, 576+23),		# entry row 13
        RectangleT(650, 603, 650+877, 603+23),		# entry row 14
        RectangleT(650, 629, 650+877, 629+23),		# entry row 15
        RectangleT(650, 655, 650+877, 655+23),		# entry row 16
        RectangleT(650, 687, 650+877, 687+23),		# entry row 17
        RectangleT(650, 712, 650+877, 712+23),		# entry row 18
        RectangleT(650, 738, 650+877, 738+23),		# entry row 19
        RectangleT(650, 764, 650+877, 764+23),		# entry row 20
        RectangleT(650, 798, 650+877, 798+23),		# entry row 21
        RectangleT(650, 823, 650+877, 823+23),		# entry row 22
        RectangleT(650, 849, 650+877, 849+23),		# entry row 23
        RectangleT(650, 874, 650+877, 874+23),		# entry row 24
		],
		EntryT(73, 240),		# player
		EntryT(315, 140),		# mech
		EntryT(457, 50),		# status (alive/dead)
		EntryT(595, 45),		# matchscore
		EntryT(692, 25),		# kills
		EntryT(757, 25),		# assists
		EntryT(827, 49),		# damage
		RectangleT(350, 295, 650, 395),		# cbills
		RectangleT(1270, 295, 1520, 395),	# xp
        )

Image1920x1200 = ImageT("1920x1200",    # resolution
		OffsetT(1092, 677),		# psr pixel and corresponding color values for up/down/equal
		(168, 214, 96),			# psr up color (r,g,b)
		(255, 44, 44),			# psr down color (r,g,b)
		(255, 255, 0),			# psr none color (r,g,b)
        AreaT(OffsetT(845, 80), SizeT(252, 35)),         # map
        AreaT(OffsetT(1109, 80), SizeT(236, 35)),        # mode
        AreaT(OffsetT(1560, 80), SizeT(68, 35)),         # time
        AreaT(OffsetT(835, 165), SizeT(235, 45)),        # result
        SizeT(877, 23),                  # entry size (the row of player data)
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

with open("basedata/maps.txt") as f:
	Maps = [line.rstrip("\n") for line in f]

with open("basedata/gamemodes.txt") as f:
	Modes = [line.rstrip("\n") for line in f]

with open("basedata/psr.txt") as f:
	PSR = [line.rstrip("\n") for line in f]

with open("basedata/mechs.txt") as f:
	Mechs = [line.rstrip("\n") for line in f]

def debug(txt):
	if loglevel >= DEBUG:
		print(YELLOW +	"[ DEBUG ] " + txt + ENDC)

def log(txt):
	if loglevel >= LOG:
		print(YELLOW +	"[  LOG  ] " + txt + ENDC)

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
	tmp = tmp.convert(mode="L")
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
			log("Found Map: \"%s\" with distance=0" % map)
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
		log("Found Map: \"%s\" with distance=%s" % (correctmap, repr(dist)))

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
	crop.save("./intermediate/%s_mode.png" % id)
	rawmode = pytesseract.image_to_string(crop, lang="eng", config="-psm 6")
	log("Raw Mode: \"%s\"" % rawmode)
	# if mode already matches an entry in the list, success
	for mode in Modes:
		if rawmode.lower() == mode.lower():
			mode.replace("Game Mode: ", "")		# workaround
			log("Found Mode: \"%s\" with distance=0" % mode)
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
		correctmode.replace("Game Mode: ", "")
		log("Found Mode: \"%s\" with distance=%s" % (correctmode, repr(dist)))
	
	if dist == None:
		# Mode could not be determined from input
		# ask for user input
		i = 0
		for modename in Modes:
			modename.replace("Game Mode: ", "")
			print(repr(i+1) + ": " + modename)
			i+=1
		x = -1
		print("Check image for mode: " + filename)
		while x < 0 or x > len(Modes):
			x = int(input("Enter mode number: "))
			log("Mode entered: " + repr(x))
		correctmode = Modes[x-1].replace("Game Mode: ", "")
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
		rawtime = input("Enter time: ")
	
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
	fjaro = 0.0
	fratio = 0.0
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
			fjaro = 1.0
			fratio = 1.0
			break

		#testlev(CONFIG.playername.lower(), rawplayer.lower())
		tmpdist = distance(CONFIG.playername.lower(), rawplayer.lower())
		tmpjaro = jaro(CONFIG.playername.lower(), rawplayer.lower())
		tmpratio = ratio(CONFIG.playername.lower(), rawplayer.lower())
		
		# check the quality of the found string
		if tmpdist <= dist and (tmpjaro >= 0.5 or tmpratio >= 0.5):
			playerfound = rawplayer
			selectedrow = row
			dist = tmpdist
			fjaro = tmpjaro
			fratio = tmpratio
		row += 1
	
	log("Found Player: \"%s\" (searched for \"%s\") with distance=%s" % (playerfound, CONFIG.playername, repr(dist)))
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

	if not mechfound:
		dist = 100
		fjaro = 0.0
		fratio = 0.0
		correctmech = None
		possiblemechs = []
		for mechname in Mechs:
			#testlev(modename.lower(), rawmode.lower())
			tmp_dist = distance(mechname.lower(), rawmech.lower())
			tmp_jaro = jaro(mechname.lower(), rawmech.lower())
			tmp_ratio = ratio(mechname.lower(), rawmech.lower())
			#debug("Check mech match: %s (dist %d, jaro %4.4f, ratio %4.4f)" % (mechname, tmp_dist, tmp_jaro, tmp_ratio))
			
			if tmp_jaro > fjaro:
				fjaro = tmp_jaro
				jaro_mech = mechname
				
			if tmp_ratio > fratio:
				fratio = tmp_ratio
				ratio_mech = mechname
				
			# found better match
			if tmp_dist < dist:
				# TODO: remember each better match in list
				dist = tmp_dist
				dist_mech = mechname
				correctmech = mechname
		
			# build list of possible matches
			if tmp_jaro >= 0.5 and tmp_ratio >= 0.5:
				possiblemechs.append(mechname)
				debug("Possible jaro/ratio match: %s (%4.4f, %4.4f)" % (mechname, tmp_jaro, tmp_ratio))

		debug("Best dist match: %s (%d)" % (dist_mech, dist))
		debug("Best jaro match: %s (%4.4f)" % (jaro_mech, fjaro))
		debug("Best ratio match: %s (%4.4f)" % (ratio_mech, fratio))
		
		# check the quality of the found string
		if dist > len(rawmech)*0.6 and fjaro < 0.5 and fratio < 0.5:
			debug("Quality of found mech not good enough.")
		else:
			if jaro_mech == ratio_mech and jaro_mech == dist_mech:
				mechfound = True
				correctmech = jaro_mech

	if not mechfound:
		error("Could not determine mech from input: \"%s\"" % rawmech)
		print("Check image for mech: " + filename)
		# Mech could not be determined from input
		# ask for user input
		i = 0
		print(repr(0) + ": manual")
		for mechname in possiblemechs:
			print(repr(i+1) + ": " + mechname)
			i+=1
		x = -1
		print("Check image for mech: " + filename)
		while x < 0 or x > len(possiblemechs):
			x = int(input("Enter mech number: "))
			log("Mech entered: " + repr(x))
		if x == 0:
			correctmech = input("Enter mech name: ")
		else:
			correctmech = possiblemechs[x-1]

	# remove brackets in mechname (e.g. (C), (I), (S) and so on)
	#correctmech = re.sub(r"\(.\)", "", correctmech)
	log("Found Mech: \"%s\" with distance=%s" % (correctmech, repr(dist)))
	
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

def checkpixelcolor(pixel1, pixel2, factor):
	r1, g1, b1 = pixel1
	r2, g2, b2 = pixel2
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

def usage():
	print("Usage: python analyze.py\n")
	print("    -p|--player=\"PLAYERNAME\"")
	print("    -r|--resolution=\"<1920x1200>\"")
	print("    [-h|--help]")
	print("    [-v|--verbose]")

def processArgs(argv):
	global CONFIG
	try:
		opts, args = getopt.getopt(argv, "p:r:t:vh", ["player=", "resolution=", "type=", "verbose", "help"])
	except getopt.GetoptError as err:
		usage()
		abort(repr(err))

	log("ARGS: " + repr(opts))
	
	for opt, arg in opts:
		if opt in ("-h", "--help"):
			usage()
			exit(0)
		elif opt in ("-p", "--player"):
			log("player=" + arg)
			target = arg
		elif opt in ("-p", "--parts"):
			log("parts=" + arg)
			if "all" in arg:
				arg = "bootstrap uboot env kernel rootfs"
			parts = string.split(arg)
		elif opt in ("-v", "--verbose"):
			log("verbose=True")
			verbose = True
	if not target:
		usage()
		abort("Architecture not given")
	if not parts:
		usage()
		abort("At least one part must be given")
	if target not in ("Matrix504", "Matrix505", "SEC2", "SEC3"):
		usage()
		abort("Invalid target given: " + repr(target))
	initArch()

def main(args):
	processArgs(args)
	# read config files
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

	log("Finished")
	return
	
if __name__ == "__main__":
	main()