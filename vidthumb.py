#!/usr/bin/python
"""Program to create 3x3 thumbnail image for a video."""

import sys
import shlex
import subprocess
import os
import tempfile
import shutil
import Image
import ImageDraw
import threading
import Queue

def get_output(cmd):
  """Capture the output of a shell command.

  Args:
    cmd: the command to execute.

  Returns:
    a str, the stdout the command generated."""
  args = shlex.split(cmd)
  proc = subprocess.Popen(args, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
  stdout, stderr = proc.communicate()
  if proc.returncode != 0:
    print "returncode : %s" % proc.returncode
    print stdout
    print stderr
  return stdout
  
def get_video_data(filename):
  """Extracts identification data of a video specified by filename.

  Args:
    filename: the filename of the video to get the length for.

  Returns:
    A dictionary, keyed by property name, value is property value.
  """
  res = {}
  cmd = "mplayer -vo null -ao null -frames 0 -identify \"%s\"" % filename
  for line in get_output(cmd).split("\n"):
    if line.startswith("ID_"):
      [ key, value ] = line.split('=')
      res[key[3:]] = value
  return res

def get_thumbnail(filename, idx):
  """Extract a thumbnail from a video at a specific position by using mplayer.

  Args:
    filename: the filename of the video.
    idx: the index where to take the snapshot.
  """
  outdir = tempfile.mkdtemp()
  try:
    cmd = "mplayer -vo png:outdir=%(dir)s -frames 1 -ss %(idx)s \"%(fn)s\"" % {
        "idx": idx, "fn": filename, "dir": outdir }
    get_output(cmd)
    return Image.open(outdir + '/00000001.png')
  finally:
    shutil.rmtree(outdir)

def get_thumbnails_parallel(filename, idx):
  """Collect snapshot of a video in parallel to speed things up.

  Args:
    filename: the filename of the video.
    idx: a list with the indices to take snapshots at.
  """
  res = []
  def get_single_thumbnail(queue, filename, idx):
    try:
      queue.put(get_thumbnail(filename, idx))
    except:
      print "get_single_thumbnail %s %s failed !" % (filename, idx)
      queue.put(None) # don't block
  for time in idx:
    queue = Queue.Queue()
    res.append(queue)
    threading.Thread(target=get_single_thumbnail, 
                     args=(queue, filename, time)).start()
  return res

def make_thumbnail(filename):
  """Create an image for a video containing a 3x3 grid with thumbnails
  equally spaced within that video.

  Args:
    filename: the filename of the video to make the 3x3 thumbnails for.
  """
  video_data = get_video_data(filename)
  if not 'LENGTH' in video_data:
    print "mplayer cannot identify video length"
    positions = xrange(0, 90, 10)
  else:
    length = float(video_data['LENGTH'])

    # find 9 indices to capture at
    skip = length/10
    positions = map(lambda x: skip * x, xrange(1, 10))

    # First thumbnail closer to start to capture title.
    positions[0] = min(positions[0], 3.5)

  # get all the thumbnails in parallel
  thumbs = get_thumbnails_parallel(filename, positions)

  # Assemble the thumbnail image
  image = Image.new("RGB", (3*128, 3*128), (0, 0, 0))
  for i in xrange(9):
    ypos = i / 3
    xpos = i % 3
    
    # progress information.
    sys.stdout.write(".")
    sys.stdout.flush()

    to_thumbnail = thumbs[i].get()
    to_thumbnail.thumbnail( (128, 128), Image.ANTIALIAS )

    ofx = (128 - to_thumbnail.size[0]) / 2
    ofy = (128 - to_thumbnail.size[1]) / 2
    image.paste(to_thumbnail, (xpos * 128 + ofx, ypos * 128 + ofy))

  print
  return image

def paint_top_left(img, text):
  text = str(text)
  draw = ImageDraw.Draw(img)
  
  draw.text((1, 1), text, fill=(0, 0, 0))
  draw.text((0, 0), text, fill=(255, 255, 255))

def paint_top_right(img, text):
  text = str(text)
  draw = ImageDraw.Draw(img)

  img_size = img.size
  text_size = draw.textsize(text)

  xpos = img_size[0] - text_size[0] - 2
  ypos = 0 # img_size[1] - text_size[1] - 2

  draw.text((xpos+1, ypos+1), text, fill=(0, 0, 0))
  draw.text((xpos, ypos), text, fill=(255, 255, 255))

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
  filename = argv[1]
  img = make_thumbnail(filename)
  # paint the filename on the thumbnail
  paint_top_left(img, filename)

  # stat the filename to get size
  paint_top_right(img, nice_print_size(os.stat(filename).st_size))
  print "saving %s_thumb.png" % filename
  img.save(filename + "_thumb.png")

if __name__ == "__main__":
  main(sys.argv)
