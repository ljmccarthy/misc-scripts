#!/usr/bin/env python3
#
# sync music from source to destination directory
# copy opus, ogg, mp3, as-is
# encode flac, wav as opus

import argparse
import errno
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Callable

default_bitrate = "128k"

def encode_ffmpeg(input_file, output_file, codec, bitrate=default_bitrate, extra_args=[]):
    cmd = [
        "ffmpeg", "-y", "-i", input_file,
        "-map", "0:a",                      # map all audio streams
        "-map", "0:v?",                     # map video stream if exists
        "-c:a", codec, "-b:a", bitrate,     # set audio codec and bitrate
        "-c:v", "copy",                     # copy video stream as-is
        "-map_metadata", "0",               # copy metadata
    ] + extra_args + [
        output_file
    ]
    return subprocess.call(cmd)

def encode_ogg(input_file, output_file, bitrate=default_bitrate):
    return encode_ffmpeg(input_file, output_file, codec="libvorbis", bitrate=bitrate)

def encode_opus(input_file, output_file, bitrate=default_bitrate):
    return encode_ffmpeg(input_file, output_file, codec="libopus", bitrate=bitrate, extra_args=["-vbr", "on"])

def encode_aac(input_file, output_file, bitrate=default_bitrate):
    return encode_ffmpeg(input_file, output_file, codec="libfdk_aac", bitrate=bitrate)

@dataclass
class Encoder:
    extension: str
    encode: Callable[[str, str], int]

encoders = {
    "opus": Encoder(extension="opus", encode=encode_opus),
    "ogg": Encoder(extension="ogg", encode=encode_ogg),
    "aac": Encoder(extension="aac", encode=encode_aac),
}

def file_newer(src, dst):
    return (os.stat(src).st_mtime - os.stat(dst).st_mtime) > 1.0

def split_ext(filename):
    basename, ext = os.path.splitext(filename)
    return basename, ext[1:].lower()

def remove(path):
    try:
        os.remove(path)
    except Exception:
        pass

def find_files(path):
    for dirpath, dirnames, filenames in os.walk(path):
        dirnames[:] = [d for d in dirnames if not d.startswith('.')]
        dirnames.sort()
        filenames.sort()
        for filename in filenames:
            if not filename.startswith('.'):
                filepath = os.path.join(dirpath, filename)
                relpath = os.path.relpath(filepath, path)
                yield relpath

def find_files_by_extension(path, extensions):
    for filename in find_files(path):
        ext = split_ext(filename)[1]
        if ext in extensions:
            yield filename

def find_preferred_files(filenames, extensions):
    ext_priority = {ext: i for i, ext in enumerate(extensions)}
    preferred = {}
    for filename in filenames:
        basename, ext = split_ext(filename)
        existing = preferred.get(basename)
        if existing is None or ext_priority[split_ext(existing)[1]] > ext_priority[ext]:
            preferred[basename] = filename
    return sorted(preferred.values())

def replace_extension(filename, exts_from, ext_to):
    name, ext = split_ext(filename)
    return name + os.path.extsep + ext_to if ext in exts_from else filename

invalid_chars_re = re.compile(r'["*:<>?\[\]|]')

def replace_invalid_chars(filename):
    return os.path.sep.join(invalid_chars_re.sub("_", part.rstrip(".")) for part in filename.split(os.path.sep))

default_dst_extensions = ("flac", "wav", "m4a", "aac", "opus", "ogg", "mp3")
lossless_extensions = ("flac", "wav")

def sync_music(srcpath, dstpath, encoder, bitrate=default_bitrate, dst_extensions=default_dst_extensions):
    srcfiles = list(find_files_by_extension(srcpath, dst_extensions))
    srcfiles = find_preferred_files(srcfiles, dst_extensions)
    dstfiles = frozenset(find_files(dstpath))

    files_to_delete = sorted(dstfiles - frozenset(replace_invalid_chars(replace_extension(x, lossless_extensions, encoder.extension)) for x in srcfiles))
    for filename in files_to_delete:
        filename = os.path.join(dstpath, filename)
        print("Removing:", filename)
        remove(filename)

    for filename in srcfiles:
        srcfile = os.path.join(srcpath, filename)
        dstfile = os.path.join(dstpath, replace_invalid_chars(filename))
        os.makedirs(os.path.dirname(dstfile), exist_ok=True)
        try:
            if split_ext(filename)[1] in lossless_extensions:
                dstfile = os.path.splitext(dstfile)[0] + os.path.extsep + encoder.extension
                if not os.path.exists(dstfile) or file_newer(srcfile, dstfile):
                    rc = encoder.encode(srcfile, dstfile, bitrate=bitrate)
                    if rc != 0:
                        print("Error: encoder return error code {0} for file: {1}".format(rc, srcfile))
                        remove(dstfile)
            else:
                if not os.path.exists(dstfile) or file_newer(srcfile, dstfile):
                    print("Copying:", srcfile)
                    try:
                        shutil.copy2(srcfile, dstfile)
                    except Exception as e:
                        print("Error: Failed to copy file: {0}".format(e))
                        remove(dstfile)
        except:
            remove(dstfile)
            raise

def sync_music_opus(srcpath, dstpath, bitrate=default_bitrate):
    sync_music(srcpath, dstpath, encoder=encoders["opus"], bitrate=bitrate)

def sync_music_vorbis(srcpath, dstpath, bitrate=default_bitrate):
    sync_music(srcpath, dstpath, encoder=encoders["ogg"], bitrate=bitrate)

def sync_music_aac(srcpath, dstpath, bitrate=default_bitrate):
    sync_music(srcpath, dstpath, encoder=encoders["aac"], bitrate=bitrate)

def main():
    valid_formats = sorted(encoders.keys())
    argparser = argparse.ArgumentParser(description="Sync audio files from source to destination directory.")
    argparser.add_argument("srcpath", help="Source directory containing music files.")
    argparser.add_argument("dstpath", help="Destination directory to sync music files to.")
    argparser.add_argument("--format", choices=valid_formats, default="opus",
                        help="Format to encode audio files into (default: opus).")
    argparser.add_argument("--bitrate", default=default_bitrate,
                        help=f"Bitrate for encoding (default: {default_bitrate}).")
    args = argparser.parse_args()
    if args.format not in encoders:
        print("Error: Invalid format specified. Choose from: {}".format(", ".join(valid_formats)))
        sys.exit(1)
    sync_music(args.srcpath, args.dstpath, encoder=encoders[args.format], bitrate=args.bitrate)

if __name__ == "__main__":
    main()

__all__ = [
    "sync_music"
    "sync_music_opus",
    "sync_music_vorbis",
    "sync_music_aac",
]
