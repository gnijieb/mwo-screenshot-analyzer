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

from collections import namedtuple
from subprocess import call
import sys
import re
import string
from os import listdir
from os.path import isfile, join
import shutil
import ConfigParser
import getopt

from PIL import Image, ImageFilter, ImageOps, ImageEnhance, ImageDraw

EntryT = namedtuple("Entry", "x1 x2")	# the x1 offset (from) and x2 offset (to) of e.g. playername in cropped entry
PixelT = namedtuple("Pixel", "x y")
ColorT = namedtuple("Color", "r g b")
RectangleT = namedtuple("Rectangle", "x1 y1 x2 y2")
ImageT = namedtuple("Image", "resolution psr psrup psrdown psrnone map mode time result rowx1 rowx2 rowheight rows player mech status score kills assists damage cbills xp")

resinfo = None

def loadResolutionInfo(res):
	global resinfo
	width, height = res
	resolution = repr(width) + "x" + repr(height)

	p = ConfigParser.SafeConfigParser()
	p.read("basedata/resolution_" + resolution + ".ini")
	
	print p.get("Info", "Resolution")
	psrup = [int(val.strip()) for val in p.get("PSR", "up").split(" ")]
	psrdown = [int(val.strip()) for val in p.get("PSR", "down").split(" ")]
	psrnone = [int(val.strip()) for val in p.get("PSR", "none").split(" ")]

	resinfo = ImageT(
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

def dopreprocess(img):
	tmp = ImageOps.invert(img)
	# ENHANCE
	enhancer = ImageEnhance.Sharpness(tmp)
	tmp = enhancer.enhance(2.0)
	# convert to grayscale
	tmp = tmp.convert(mode="L")
	# threshold greys to white
	tmp = tmp.point(lambda p: p > 60 and 255)
	return tmp

def main(args):
	preprocess = False
	if preprocess:
		col = (0)
	else:
		col = (255,0,0)
	
	files = [f for f in listdir("./input") if isfile(join("./input", f))]
	files.sort()
	files.reverse()
	print(files)
	if len(files)%2 != 0:
		print("Odd number of files found: %d" % len(files))
		return
	
	count = len(files)/2
	
	if count >= 1:
		filename1 = files.pop()
		filename2 = files.pop()
		print(filename1 + " " + filename2)

		file1 = "./input/" + filename1
		file2 = "./input/" + filename2
	
		with Image.open(file1) as img:
			# load resolution information
			loadResolutionInfo(img.size)

			if preprocess:
				img = preprocess(img)
			
			draw = ImageDraw.Draw(img)
			
			# map
			rect = (
				resinfo.map.x1,
				resinfo.map.y1,
				resinfo.map.x2,
				resinfo.map.y2
			)
			draw.rectangle(rect, outline=col)
			
			# mode
			rect = (
				resinfo.mode.x1,
				resinfo.mode.y1,
				resinfo.mode.x2,
				resinfo.mode.y2
			)
			draw.rectangle(rect, outline=col)

			# time
			rect = (
				resinfo.time.x1,
				resinfo.time.y1,
				resinfo.time.x2,
				resinfo.time.y2
			)
			draw.rectangle(rect, outline=col)

			# result
			rect = (
				resinfo.result.x1,
				resinfo.result.y1,
				resinfo.result.x2,
				resinfo.result.y2
			)
			draw.rectangle(rect, outline=col)

			row = 0
			y1 = 0
			y2 = 0
			(x1, x2, h) =  (
				resinfo.rowx1,
				resinfo.rowx2,
				resinfo.rowheight
			)

			while row < 24:
				y1 = resinfo.rows[row]
				y2 = y1 + h
				
				# row
				#draw.rectangle((x1, y1, x2, y2), outline=col)
				
				# player
				draw.rectangle((resinfo.player.x1, y1, resinfo.player.x2, y2), outline=col)
				
				# mech
				draw.rectangle((resinfo.mech.x1, y1, resinfo.mech.x2, y2), outline=col)
				
				# status
				draw.rectangle((resinfo.status.x1, y1, resinfo.status.x2, y2), outline=col)
				
				# match score
				draw.rectangle((resinfo.score.x1, y1, resinfo.score.x2, y2), outline=col)
				
				# kills
				draw.rectangle((resinfo.kills.x1, y1, resinfo.kills.x2, y2), outline=col)
				
				# assists
				draw.rectangle((resinfo.assists.x1, y1, resinfo.assists.x2, y2), outline=col)

				# damage
				draw.rectangle((resinfo.damage.x1, y1, resinfo.damage.x2, y2), outline=col)

				row += 1

			del draw
			img.save("./output/%s" % filename1)
			
			
		with Image.open(file2) as img:
			if preprocess:
				img = preprocess(img)

			draw = ImageDraw.Draw(img)
			
			# cbills
			rect = (
				resinfo.cbills.x1,
				resinfo.cbills.y1,
				resinfo.cbills.x2,
				resinfo.cbills.y2
			)
			draw.rectangle(rect, outline=col)
			
			# xp
			rect = (
				resinfo.xp.x1,
				resinfo.xp.y1,
				resinfo.xp.x2,
				resinfo.xp.y2
			)
			draw.rectangle(rect, outline=col)
		
			del draw
			img.save("./output/%s" % filename2)

	print("Done")
	return
	
if __name__ == "__main__":
	main(sys.argv[1:])