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
# Copyright 2015-2016 gnijieb@gmail.com

from collections import namedtuple
from subprocess import call
import sys
import re
import string
from os import listdir
from os.path import isfile, join
import shutil
from datetime import datetime, date, time
import ConfigParser
import getopt
from importlib import import_module

from Levenshtein import *
from PIL import Image, ImageFilter, ImageOps, ImageEnhance
import pytesseract

DEBUG = 2
LOG   = 1

MODE_MATCHONLY = 1
MODE_MATCHPLAYER = 2
MODE_PLAYERMATCH = 3

class Configuration:
	player = None
	type = None
	mode = None
	ext = None
	resinfo = None
	fnpattern = None
	dtformat = None
	loglevel = LOG
	
EntryT = namedtuple("Entry", "x1 x2")	# the x1 offset (from) and x2 offset (to) of e.g. playername in cropped entry
PixelT = namedtuple("Pixel", "x y")
ColorT = namedtuple("Color", "r g b")
RectangleT = namedtuple("Rectangle", "x1 y1 x2 y2")
ImageT = namedtuple("Image", "resolution psr psrup psrdown psrnone map mode time result rowx1 rowx2 rowheight rows player mech status score kills assists damage cbills xp")

CONFIG = Configuration()

def abort(message, code = 1):
	error("Aborting: " + message)
	exit(code)

def debug(txt):
	if CONFIG.loglevel >= DEBUG:
		print("[ DEBUG ] " + txt)

def log(txt):
	if CONFIG.loglevel >= LOG:
		print("[  LOG  ] " + txt)

def error(message):
	print("[ ERROR ] " + message)

def isTimeFormat(input):
    try:
        datetime.strptime(input, "%M:%S")
        return True
    except ValueError:
        return False

def correctTimeFormat(input):
	mytime = datetime.strptime(input, "%M:%S")
	seconds = mytime.minute*60 + mytime.second
	return seconds

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
	if CONFIG.type == "fraps":
		threshold = 60
	elif CONFIG.type == "mwo":
		threshold = 80
	elif CONFIG.type == "steam":
		threshold = 90
	tmp = tmp.point(lambda p: p > threshold and 255)

	if CONFIG.loglevel >= DEBUG:
		tmp.save("./intermediate/%s_part_%s.png" % (id, part))
	return tmp

def getmap(img, id, filename):
	(x1, y1, x2, y2) = (
		CONFIG.resinfo.map.x1,
		CONFIG.resinfo.map.y1,
		CONFIG.resinfo.map.x2,
		CONFIG.resinfo.map.y2
	)
	crop = img.crop((x1, y1, x2, y2))
	if CONFIG.loglevel >= DEBUG:
		crop.save("./intermediate/%s_map.png" % id)
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
	(x1, y1, x2, y2) = (
		CONFIG.resinfo.mode.x1,
		CONFIG.resinfo.mode.y1,
		CONFIG.resinfo.mode.x2,
		CONFIG.resinfo.mode.y2
	)
	crop = img.crop((x1, y1, x2, y2))
	if CONFIG.loglevel >= DEBUG:
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
	(x1, y1, x2, y2) = (
		CONFIG.resinfo.time.x1,
		CONFIG.resinfo.time.y1,
		CONFIG.resinfo.time.x2,
		CONFIG.resinfo.time.y2
	)
	crop = img.crop((x1, y1, x2, y2))
	if CONFIG.loglevel >= DEBUG:
		crop.save("./intermediate/%s_time.png" % id)
	rawtime = pytesseract.image_to_string(crop, lang="eng", config="-psm 6")
	log("Raw Time: \"%s\"" % rawtime)

	while not isTimeFormat(rawtime):
		error("Could not determine time from input: \"%s\"" % rawtime)
		print("Check image for time: " + filename)
		rawtime = raw_input("Enter time: ")
	
	return correctTimeFormat(rawtime)

def getplayerdata(img, id, filename):
	row = 0
	y1 = 0
	y2 = 0
	(x1, x2, h) =  (
		CONFIG.resinfo.rowx1,
		CONFIG.resinfo.rowx2,
		CONFIG.resinfo.rowheight
	)
	crop = None
	playerfound = None
	selectedrow = None
	dist = 100
	fjaro = 0.0
	fratio = 0.0
	while row < 24:
		y1 = CONFIG.resinfo.rows[row]
		y2 = y1 + h
		crop = img.crop((x1, y1, x2, y2))
		#debug("crop: " + repr(crop.size))
		#crop.load()
		#crop.save("./intermediate/%s_entry_%s.png" % (id, repr(row)))
		
		#cropplayer = crop.crop((CONFIG.resinfo.player.x1, 0, CONFIG.resinfo.player.x2, h))
		cropplayer = img.crop((CONFIG.resinfo.player.x1, y1, CONFIG.resinfo.player.x2, y2))
		#cropplayer.load()
		rawplayer = pytesseract.image_to_string(cropplayer, lang="eng", config="-psm 6")
		debug("Raw Player: \"%s\"" % rawplayer)

		# if playername already matches, success
		if rawplayer.lower() == CONFIG.player.lower():
			playerfound = rawplayer
			selectedrow = row
			dist = 0
			fjaro = 1.0
			fratio = 1.0
			break

		#testlev(CONFIG.player.lower(), rawplayer.lower())
		tmpdist = distance(CONFIG.player.lower(), rawplayer.lower())
		tmpjaro = jaro(CONFIG.player.lower(), rawplayer.lower())
		tmpratio = ratio(CONFIG.player.lower(), rawplayer.lower())
		
		# check the quality of the found string
		if tmpdist <= dist and (tmpjaro >= 0.5 or tmpratio >= 0.5):
			playerfound = rawplayer
			selectedrow = row
			dist = tmpdist
			fjaro = tmpjaro
			fratio = tmpratio
		row += 1
	
	y1 = CONFIG.resinfo.rows[selectedrow]
	y2 = y1 + h
	
	log("Found Player: \"%s\" (searched for \"%s\") with distance=%s" % (playerfound, CONFIG.player, repr(dist)))
	if CONFIG.loglevel >= DEBUG:
		crop.save("./intermediate/%s_player.png" % id)

	result = None
	if selectedrow < 12:
		result = "Victory"
	else:
		result = "Defeat"

	# get the data from selected entry row
	#cropmech = crop.crop((CONFIG.resinfo.mech.x1, y, CONFIG.resinfo.mech.x2, y+h))
	cropmech = img.crop((CONFIG.resinfo.mech.x1, y1, CONFIG.resinfo.mech.x2, y2))
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
			if tmp_jaro >= 0.55 and tmp_ratio >= 0.55:
				possiblemechs.append(mechname)
				debug("Possible jaro/ratio match: %s (%4.4f, %4.4f)" % (mechname, tmp_jaro, tmp_ratio))

		debug("Best dist match: %s (%d)" % (dist_mech, dist))
		debug("Best jaro match: %s (%4.4f)" % (jaro_mech, fjaro))
		debug("Best ratio match: %s (%4.4f)" % (ratio_mech, fratio))
		
		# check the quality of the found string
		if dist > len(rawmech)*0.6 and fjaro < 0.5 and fratio < 0.5:
			debug("Quality of found mech not good enough.")
		else:
			if dist_mech == jaro_mech and jaro_mech == ratio_mech and fjaro >= 0.9 and fratio >= 0.9:
				mechfound = True
				correctmech = dist_mech
			elif jaro_mech == ratio_mech and fjaro >= 0.8 and fratio >= 0.8:
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
	
	#cropstatus = crop.crop((CONFIG.resinfo.status.x, 0, CONFIG.resinfo.status.x + CONFIG.resinfo.status.w, h))
	cropstatus = img.crop((CONFIG.resinfo.status.x1, y1, CONFIG.resinfo.status.x2, y2))
	rawstatus = pytesseract.image_to_string(cropstatus, lang="eng", config="-psm 6")
	dist = distance("alive", rawstatus.lower())
	status = 0
	if dist >= 4:
		# dead
		status = 1
	
	#cropscore = crop.crop((CONFIG.resinfo.score.x, 0, CONFIG.resinfo.score.x + CONFIG.resinfo.score.w, h))
	cropscore = img.crop((CONFIG.resinfo.score.x1, y1, CONFIG.resinfo.score.x2, y2))
	rawscore = pytesseract.image_to_string(cropscore, lang="eng", config="-psm 6")
	try:
		score = int(rawscore)
	except ValueError:
		error("Could not determine match score from input: \"%s\"" % rawscore)
		print("Check image for match score: " + filename)
		score = int(input("Enter match score: "))

	#cropkills = crop.crop((CONFIG.resinfo.kills.x, 0, CONFIG.resinfo.kills.x + CONFIG.resinfo.kills.w, h))
	cropkills = img.crop((CONFIG.resinfo.kills.x1, y1, CONFIG.resinfo.kills.x2, y2))
	rawkills = pytesseract.image_to_string(cropkills, lang="eng", config="-psm 6")
	try:
		kills = int(rawkills)
	except ValueError:
		error("Could not determine kills from input: \"%s\"" % rawkills)
		print("Check image for kills: " + filename)
		kills = int(input("Enter kills: "))

	#cropassists = crop.crop((CONFIG.resinfo.assists.x, 0, CONFIG.resinfo.assists.x + CONFIG.resinfo.assists.w, h))
	cropassists = img.crop((CONFIG.resinfo.assists.x1, y1, CONFIG.resinfo.assists.x2, y2))
	rawassists = pytesseract.image_to_string(cropassists, lang="eng", config="-psm 6")
	try:
		assists = int(rawassists)
	except ValueError:
		error("Could not determine assists from input: \"%s\"" % rawassists)
		print("Check image for assists: " + filename)
		assists = int(input("Enter assists: "))

	#cropdamage = crop.crop((CONFIG.resinfo.damage.x, 0, CONFIG.resinfo.damage.x + CONFIG.resinfo.damage.w, h))
	cropdamage = img.crop((CONFIG.resinfo.damage.x1, y1, CONFIG.resinfo.damage.x2, y2))
	rawdamage = pytesseract.image_to_string(cropdamage, lang="eng", config="-psm 6")
	try:
		damage = int(rawdamage)
	except ValueError:
		error("Could not determine damage from input: \"%s\"" % rawdamage)
		print("Check image for damage: " + filename)
		damage = int(input("Enter damage: "))

	return (result, correctmech, status, score, kills, assists, damage)

def getcbills(img, id, filename):
	(x1, y1, x2, y2) =  (
		CONFIG.resinfo.cbills.x1,
		CONFIG.resinfo.cbills.y1,
		CONFIG.resinfo.cbills.x2,
		CONFIG.resinfo.cbills.y2,
	)
	crop = img.crop((x1, y1, x2, y2))
	if CONFIG.loglevel >= DEBUG:
		crop.save("./intermediate/%s_cbills.png" % id)
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
	(x1, y1, x2, y2) =  (
		CONFIG.resinfo.xp.x1,
		CONFIG.resinfo.xp.y1,
		CONFIG.resinfo.xp.x2,
		CONFIG.resinfo.xp.y2,
	)
	crop = img.crop((x1, y1, x2, y2))
	if CONFIG.loglevel >= DEBUG:
		crop.save("./intermediate/%s_xp.png" % id)
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
	if checkpixelcolor(CONFIG.resinfo.psrup, pixel, 0.2):
		debug("PSR Up")
		return "Up"
	elif checkpixelcolor(CONFIG.resinfo.psrnone, pixel, 0.2):
		debug("PSR None")
		return "None"
	elif checkpixelcolor(CONFIG.resinfo.psrdown, pixel, 0.25):
		debug("PSR Down")
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

def loadGameKnowledge():
	global Maps, Modes, PSR, Mechs
	
	with open("basedata/maps.txt") as f:
		Maps = [line.rstrip("\n") for line in f]

	with open("basedata/gamemodes.txt") as f:
		Modes = [line.rstrip("\n") for line in f]

	with open("basedata/psr.txt") as f:
		PSR = [line.rstrip("\n") for line in f]

	with open("basedata/mechs.txt") as f:
		Mechs = [line.rstrip("\n") for line in f]

def loadResolutionInfo(res):
	global CONFIG
	width, height = res
	resolution = repr(width) + "x" + repr(height)

	p = ConfigParser.SafeConfigParser()
	p.read("basedata/resolution_" + resolution + ".ini")
	
	print p.get("Info", "Resolution")
	psrup = [int(val.strip()) for val in p.get("PSR", "up").split(" ")]
	psrdown = [int(val.strip()) for val in p.get("PSR", "down").split(" ")]
	psrnone = [int(val.strip()) for val in p.get("PSR", "none").split(" ")]

	CONFIG.resinfo = ImageT(
		resolution,
		PixelT(int(p.get("PSR", "x")), int(p.get("PSR", "y"))),		# psr pixel and corresponding color values for up/down/equal
		ColorT(psrup[0], psrup[1], psrup[2]),			# psr up color (r,g,b)
		ColorT(psrdown[0], psrdown[1], psrdown[2]),		# psr down color (r,g,b)
		ColorT(psrnone[0], psrnone[1], psrnone[2]),		# psr none color (r,g,b)
		RectangleT(int(p.get("Map", "x1")), int(p.get("Map", "y1")), int(p.get("Map", "x2")), int(p.get("Map", "y2"))),
		RectangleT(int(p.get("Mode", "x1")), int(p.get("Mode", "y1")), int(p.get("Mode", "x2")), int(p.get("Mode", "y2"))),
		RectangleT(int(p.get("Time", "x1")), int(p.get("Time", "y1")), int(p.get("Time", "x2")), int(p.get("Time", "y2"))),
		RectangleT(int(p.get("Result", "x1")), int(p.get("Result", "y1")), int(p.get("Result", "x2")), int(p.get("Result", "y2"))),
		int(p.get("RowGeneral", "x1")),
		int(p.get("RowGeneral", "x2")),
		int(p.get("RowGeneral", "height")),
		[
			int(p.get("Row1", "y")), # entry row 1
			int(p.get("Row2", "y")), # entry row 1
			int(p.get("Row3", "y")), # entry row 1
			int(p.get("Row4", "y")), # entry row 1
			int(p.get("Row5", "y")), # entry row 1
			int(p.get("Row6", "y")), # entry row 1
			int(p.get("Row7", "y")), # entry row 1
			int(p.get("Row8", "y")), # entry row 1
			int(p.get("Row9", "y")), # entry row 1
			int(p.get("Row10", "y")), # entry row 1
			int(p.get("Row11", "y")), # entry row 1
			int(p.get("Row12", "y")), # entry row 1
			int(p.get("Row13", "y")), # entry row 1
			int(p.get("Row14", "y")), # entry row 1
			int(p.get("Row15", "y")), # entry row 1
			int(p.get("Row16", "y")), # entry row 1
			int(p.get("Row17", "y")), # entry row 1
			int(p.get("Row18", "y")), # entry row 1
			int(p.get("Row19", "y")), # entry row 1
			int(p.get("Row20", "y")), # entry row 1
			int(p.get("Row21", "y")), # entry row 1
			int(p.get("Row22", "y")), # entry row 1
			int(p.get("Row23", "y")), # entry row 1
			int(p.get("Row24", "y"))# entry row 1
		],
		EntryT(int(p.get("Player", "x1")), int(p.get("Player", "x2"))),
		EntryT(int(p.get("Mech", "x1")), int(p.get("Mech", "x2"))),
		EntryT(int(p.get("Status", "x1")), int(p.get("Status", "x2"))),
		EntryT(int(p.get("Matchscore", "x1")), int(p.get("Matchscore", "x2"))),
		EntryT(int(p.get("Kills", "x1")), int(p.get("Kills", "x2"))),
		EntryT(int(p.get("Assists", "x1")), int(p.get("Assists", "x2"))),
		EntryT(int(p.get("Damage", "x1")), int(p.get("Damage", "x2"))),
		RectangleT(int(p.get("CBills", "x1")), int(p.get("CBills", "y1")), int(p.get("CBills", "x2")), int(p.get("CBills", "y2"))),
		RectangleT(int(p.get("XP", "x1")), int(p.get("XP", "y1")), int(p.get("XP", "x2")), int(p.get("XP", "y2")))
	)

def writeCSV(dtnow, matchdate, player, result, mech, map, mode, status, score, kills, assists, damage, xp, cbills, psr, gametime):
	defaultformat = "matchdate,playername,matchresult,mech,map,gamemode,survivalstatus,matchscore,kills,assists,damage,xp,cbills,psr,gametime"
	
	buf = defaultformat
	buf = buf.replace("matchdate", matchdate)
	buf = buf.replace("playername", player)
	buf = buf.replace("matchresult", result)
	buf = buf.replace("mech", mech)
	buf = buf.replace("map", map)
	buf = buf.replace("gamemode", mode)
	buf = buf.replace("survivalstatus", repr(status))
	buf = buf.replace("matchscore", repr(score))
	buf = buf.replace("kills", repr(kills))
	buf = buf.replace("assists", repr(assists))
	buf = buf.replace("damage", repr(damage))
	buf = buf.replace("gametime", repr(gametime))
	if xp:
		buf = buf.replace("xp", repr(xp))
	if cbills:
		buf = buf.replace("cbills", repr(cbills))
	if psr:
		buf = buf.replace("psr", psr)
	
	with open("./output/%s_data.csv" % (dtnow), "a") as myfile:
		myfile.write(buf+"\n")

def usage():
	print("Usage: python analyze.py\n")
	print("    -p|--player=\"PLAYERNAME\"")
	print("    -t|--type=\"<mwo|fraps|steam>\"")
	print("    -m|--mode=<1|2|3>")
	print("        1: matchstats only")
	print("        2: matchstats and playerstats (screenshots in this order)")
	print("        3: playerstats and matchstats (screenshots in this order)")
	print("    -x|--ext=\"NAME\"")
	print("        Name of external processing module")
	print("    [-h|--help]")
	print("    [-v|--verbose]")

def processArgs(argv):
	global CONFIG
	try:
		opts, args = getopt.getopt(argv, "p:t:m:x:vh", ["player=", "type=", "mode=", "ext=", "verbose", "help"])
	except getopt.GetoptError as err:
		usage()
		abort(repr(err))

	log("ARGS: " + repr(opts))
	
	for opt, arg in opts:
		if opt in ("-h", "--help"):
			usage()
			exit(1)
		elif opt in ("-p", "--player"):
			CONFIG.player = arg
			log("player=" + arg)
		elif opt in ("-t", "--type"):
			CONFIG.type = arg
			if arg == "fraps":
				CONFIG.fnpattern = r"\d{4}-\d{2}-\d{2} \d{2}-\d{2}-\d{2}" # FRAPS Screenshot filename datetime pattern
				CONFIG.dtformat = "%Y-%m-%d %H-%M-%S" # FRAPS Screenshot filename datetime format
			elif arg == "mwo":
				CONFIG.fnpattern = r"\d{2}\.\d{2}\.\d{4}-\d{2}\.\d{2}\.\d{2}" # MWO Screenshot filename datetime pattern
				CONFIG.dtformat = "%m.%d.%Y-%H.%M.%S" # MWO Screenshot filename datetime format
			elif arg == "steam":
				CONFIG.fnpattern = r"\d{4}\d{2}\d{2}\d{2}\d{2}\d{2}" # Steam Screenshot filename datetime pattern
				CONFIG.dtformat = "%Y%m%d%H%M%S" # Steam Screenshot filename datetime format
			else:
				usage()
				exit(1)
			log("type=" + arg)
		elif opt in ("-m", "--mode"):
			CONFIG.mode = int(arg)
			log("mode=" + arg)
		elif opt in ("-x", "--ext"):
			CONFIG.ext = arg
			log("ext=" + arg)
		elif opt in ("-v", "--verbose"):
			CONFIG.loglevel = DEBUG
			log("verbose=True")
	if not CONFIG.player:
		usage()
		abort("Playername not given")
	if not CONFIG.type:
		usage()
		abort("Screenshot type not given")
	if not CONFIG.mode:
		usage()
		abort("Mode not given")

def main(args):
	global CONFIG
	dtnow = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
	log("Script started at " + dtnow)

	# process commandline args
	processArgs(args)
	
	# read config files
	loadGameKnowledge()
	
	files = [f for f in listdir("./input") if isfile(join("./input", f))]
	files.sort()
	files.reverse()
	print(files)
	if CONFIG.mode == MODE_MATCHPLAYER or CONFIG.mode == MODE_PLAYERMATCH:
		if len(files)%2 != 0:
			error("Odd number of files found: %d" % len(files))
			return
	
	while len(files) != 0:
		(map, mode, gametime, result, mech, status, score, kills, assists, damage, cbills, xp, psr) = (None,)*13
		file1 = None
		file2 = None
		
		if CONFIG.mode == MODE_MATCHONLY:
			file1 = files.pop()
			log(file1)
		if CONFIG.mode == MODE_MATCHPLAYER:
			file1 = files.pop()
			file2 = files.pop()
			log(file1 + " " + file2)
		if CONFIG.mode == MODE_PLAYERMATCH:
			file2 = files.pop()
			file1 = files.pop()
			log(file1 + " " + file2)

		match = re.search(CONFIG.fnpattern, file1)
		if not match:
			error("Screenshot filename pattern: No match")
			continue
		dtfile = datetime.strptime(match.group(), CONFIG.dtformat)

		if CONFIG.mode == MODE_MATCHONLY:
			file1 = "./input/" + file1
		else:
			file1 = "./input/" + file1
			file2 = "./input/" + file2
		id = dtfile.strftime("%Y-%m-%d %H-%M-%S")
		matchdate = dtfile.strftime("%Y-%m-%d %H:%M:%S")

		# file1 is always matchstats
		with Image.open(file1) as img:
			# load resolution information
			debug(repr(img.size))
			loadResolutionInfo(img.size)
			img = preprocess(img, id, "team")
			(dist, map) = getmap(img, id, file1)
			debug("Found Map: \"%s\" with distance=%s" % (map, repr(dist)))
			(dist, mode) = getmode(img, id, file1)
			debug("Found Mode: \"%s\" with distance=%s" % (mode, repr(dist)))
			gametime = gettime(img, id, file1)
			(result, mech, status, score, kills, assists, damage) = getplayerdata(img, id, file1)
		if CONFIG.mode == MODE_MATCHPLAYER or CONFIG.mode == MODE_PLAYERMATCH:
			with Image.open(file2) as img:
				psr = getpsr(img, id, file2)
				img = preprocess(img, id, "player")
				cbills = getcbills(img, id, file2)
				xp = getxp(img, id, file2)

		if CONFIG.mode == MODE_MATCHONLY:
			debug("%s,%s,%s,%s,%s,%s,%d,%d,%d,%d,%d,%d" % (matchdate, CONFIG.player, result, mech, map, mode, status, score, kills, assists, damage, gametime))
		else:
			debug("%s,%s,%s,%s,%s,%s,%d,%d,%d,%d,%d,%d,%d,%s,%d" % (matchdate, CONFIG.player, result, mech, map, mode, status, score, kills, assists, damage, xp, cbills, psr, gametime))

		shutil.move(file1, "./processed")
		shutil.move(file2, "./processed")
		
		writeCSV(dtnow, matchdate, CONFIG.player, result, mech, map, mode, status, score, kills, assists, damage, xp, cbills, psr, gametime)

		if CONFIG.ext:
			extmod = import_module(CONFIG.ext)
			ext = getattr(extmod, "ext")
			ext(matchdate, CONFIG.player, result, mech, map, mode, status, score, kills, assists, damage, xp, cbills, psr, gametime)
		
		print

	log("Finished")
	return
	
if __name__ == "__main__":
	main(sys.argv[1:])