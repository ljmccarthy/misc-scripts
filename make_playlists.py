#!/usr/bin/env python3

import os

music_dir = "/data/music"

music_exts = [".flac"]

def make_playlist(path):
    music_files = [
        x for x in sorted(os.listdir(path))
        if os.path.splitext(x)[1].lower() in music_exts
    ]
    if music_files:
        playlist_path = os.path.join(path, "playlist.m3u")
        if not os.path.exists(playlist_path):
            print("writing playlist to {0}".format(playlist_path))
            with open(playlist_path, "w") as f:
                f.write("\n".join(music_files) + "\n")

for path, _, _ in os.walk(music_dir):
    make_playlist(path)
