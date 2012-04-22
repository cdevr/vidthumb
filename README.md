Vidthumb
========

Use mplayer and python imaging library to create 3x3 thumbnail images of videos. It is parallellized for maximum speed. 

This python library can be useful for a few other things, for example it contains a method get_thumbnail(video, timeindex), which gets you back a PIL image of a frame of the video as close as possible to timeindex.

Another use for this I use it for is duplicate video detection. If the videos match enough, their thumbnails will match very closely. It won't work for videos that have nontrivial offsets or anything like that.

I should probably make it more customizable, but it does what I want it to do at this point. 
