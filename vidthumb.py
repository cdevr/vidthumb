#!/usr/bin/python

import sys
import shlex
import subprocess
import os
import tempfile
import shutil
import Image
import ImageFont
import ImageDraw
import threading
import Queue

def getOutput(cmd):
	args = shlex.split(cmd)
	p = subprocess.Popen(args, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
	stdout, stderr = p.communicate()
	if p.returncode != 0:
		print "returncode : %s" % p.returncode
		print stdout
		print stderr
	return stdout
	
def getVideoData(fn):
	res = {}
	cmd = "mplayer -vo null -ao null -frames 0 -identify \"%s\"" % fn
	for l in getOutput(cmd).split("\n"):
		if l.startswith("ID_"):
			[ key, value ] = l.split('=')
			res[key[3:]] = value
	return res

def getThumbnail(fn, idx):
	outdir = tempfile.mkdtemp()
	try:
		cmd = "mplayer -vo png:outdir=%(outdir)s -frames 1 -ss %(idx)s \"%(fn)s\"" % { "idx": idx, "fn": fn, "outdir": outdir }
		getOutput(cmd)
		return Image.open(outdir + '/00000001.png')
	finally:
		shutil.rmtree(outdir)

def getThumbnailsParallel(fn, idx):
	res = []
	def getSingleThumbnail(q, fn, idx):
		try:
			q.put(getThumbnail(fn, idx))
		except:
			print "getSingleThumbnail %s %s failed !" % (fn,idx)
			q.put(None) # don't block
	for time in idx:
		q = Queue.Queue()
		res.append(q)
		threading.Thread(target=getSingleThumbnail, args=(q, fn, time)).start()
	return res

def make_thumbnail(video_filename):
	video_data = getVideoData(video_filename)
	if not 'LENGTH' in video_data:
		print "mplayer cannot identify video length"
		positions = xrange(0,90,10)
	else:
		length = float(video_data['LENGTH'])

		# find 9 indices to capture at
		skip = length/10
		positions = map(lambda x: skip * x, xrange(1,10))

		# First thumbnail closer to start to capture title.
		positions[0] = min(positions[0],3.5)

	# get all the thumbnails in parallel
	thumbs = getThumbnailsParallel(video_filename, positions)

	# Assemble the thumbnail image
	im = Image.new("RGB", (3*128, 3*128), (0,0,0))
	for i in xrange(9):
		y = i / 3
		x = i % 3
		
		# progress information.
		sys.stdout.write(".")
		sys.stdout.flush()

		to_thumbnail = thumbs[i].get()
		to_thumbnail.thumbnail( (128, 128), Image.ANTIALIAS )

		ofX = (128 - to_thumbnail.size[0]) / 2
		ofY = (128 - to_thumbnail.size[1]) / 2
		im.paste(to_thumbnail, (x * 128 + ofX, y * 128 + ofY))

	print
	return im

def paintTopLeft(img, text):
	text = str(text)
	draw = ImageDraw.Draw(img)
	
	draw.text((1,1), text, fill=(0,0,0))
	draw.text((0,0), text, fill=(255,255,255))

def paintTopRight(img, text):
	text = str(text)
	draw = ImageDraw.Draw(img)

	img_size = img.size
	text_size = draw.textsize(text)

	x = img_size[0] - text_size[0] - 2
	y = 0 # img_size[1] - text_size[1] - 2

	draw.text((x+1, y+1), text, fill=(0,0,0))
	draw.text((x, y), text, fill=(255,255,255))

def nice_print_size(size):
	if size < 2**10:
		return "%sb" % size
	elif size < 2**20:
		return "%.2dk" % ( (float(size)/float(2**10)) )
	elif size < 2**30:
		return "%.2dm" % ( (float(size)/float(2**20)) )
	elif size < 2**40:
		return "%.2dg" % ( (float(size)/float(2**30)) )
	elif size < 2**50:
		return "%.2dt" % ( (float(size)/float(2**40)) )
	else:
		return "Larger than 1000 terrabyte ?"

def main(argv):
	video_filename = argv[1]
	img = make_thumbnail(video_filename)
	# paint the filename on the thumbnail
	paintTopLeft(img, video_filename)

	# stat the filename to get size
	paintTopRight(img, nice_print_size(os.stat(video_filename).st_size))
	print "saving %s_thumb.png" % video_filename
	img.save(video_filename + "_thumb.png")

if __name__ == "__main__":
	main(sys.argv)
