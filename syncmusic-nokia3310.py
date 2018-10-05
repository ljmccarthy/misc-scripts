#!/usr/bin/env python

from syncmusic import sync_music_aac

srcpath = "/data/Music"
dstpath = "/run/media/shaurz/NOKIA3310/Music"

try:
    sync_music_aac(srcpath, dstpath)
except KeyboardInterrupt:
    pass
