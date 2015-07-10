#!/usr/bin/env python3
#
# sync music from source to destination directory
# copy opus, ogg, mp3, as-is
# encode flac as opus

srcpath = "/nas/music"
dstpath = "/run/media/shaurz/SANSA_SD"

import sys
import os
import errno
import shutil
import subprocess
import re

def oggenc(input_file, output_file):
    return subprocess.call(["oggenc", "-o", output_file, input_file])

def get_flac_tags(filename):
    output = subprocess.check_output(["metaflac", "--export-tags-to=-", filename])
    tags = []
    for line in output.decode("utf-8").split("\n"):
        tag = line.split("=", 1)
        if len(tag) == 2:
            tags.append(tag)
    return tags

def flatten(xxs):
    return [x for xs in xxs for x in xs]

def opusenc(input_file, output_file):
    print("Encoding: {0}\n" .format(os.path.basename(output_file)))
    tags = flatten(("--comment", "{0}={1}".format(tag, value)) for tag, value in get_flac_tags(input_file))
    p = subprocess.Popen(
        ["flac", "--decode", "--stdout", input_file], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return subprocess.call(["opusenc"] + tags + ["-", output_file], stdin=p.stdout)

def file_newer(src, dst):
    return (os.stat(src).st_mtime - os.stat(dst).st_mtime) > 1.0

def split_ext(filename):
    basename, ext = os.path.splitext(filename)
    return basename, ext[1:].lower()

def make_path(path):
    dirpath = path
    parts = []
    while dirpath != os.path.dirname(dirpath):
        try:
            os.mkdir(dirpath)
            break
        except OSError as e:
            if e.errno == errno.EEXIST:
                break
            elif e.errno == errno.ENOENT or (sys.platform == "win32" and e.winerror == 3):
                parts.append(os.path.basename(dirpath))
                dirpath = os.path.dirname(dirpath)
            else:
                raise
    for part in reversed(parts):
        dirpath = os.path.join(dirpath, part)
        os.mkdir(dirpath)

def remove(path):
    try:
        os.remove(path)
    except Exception:
        pass

def find_files_by_extension(path, extensions):
    for dirpath, dirnames, filenames in os.walk(path):
        dirnames.sort()
        filenames.sort()
        for filename in filenames:
            ext = split_ext(filename)[1]
            if ext in extensions:
                filepath = os.path.join(dirpath, filename)
                relpath = os.path.relpath(filepath, path)
                yield relpath

def find_preferred_files(filenames, extensions):
    ext_priority = {ext: i for i, ext in enumerate(extensions)}
    preferred = {}
    for filename in filenames:
        basename, ext = split_ext(filename)
        existing = preferred.get(basename)
        if existing is None or ext_priority[split_ext(existing)[1]] > ext_priority[ext]:
            preferred[basename] = filename
    return sorted(preferred.values())

music_extensions = ("flac", "opus", "ogg", "mp3")

invalid_chars_re = re.compile(r'["*:<>?\[\]|]')

def sync_music(srcpath, dstpath, encoder, extension):
    srcfiles = list(find_files_by_extension(srcpath, music_extensions))
    srcfiles = find_preferred_files(srcfiles, music_extensions)
    for filename in srcfiles:
        srcfile = os.path.join(srcpath, filename)
        dstfile = os.path.sep.join(invalid_chars_re.sub("_", part.rstrip(".")) for part in filename.split(os.path.sep))
        dstfile = os.path.join(dstpath, dstfile)
        make_path(os.path.dirname(dstfile))
        try:
            if split_ext(filename)[1] == "flac":
                dstfile = os.path.splitext(dstfile)[0] + extension
                if not os.path.exists(dstfile) or file_newer(srcfile, dstfile):
                    rc = encoder(srcfile, dstfile)
                    if rc != 0:
                        print("Error: encoder return error code {0}".format(rc))
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

def sync_music_opus(srcpath, dstpath):
    sync_music(srcpath, dstpath, encoder=opusenc, extension=".opus")

def sync_music_vorbis(srcpath, dstpath):
    sync_music(srcpath, dstpath, encoder=oggenc, extension=".ogg")

if __name__ == "__main__":
    try:
        sync_music_opus(srcpath, dstpath)
    except KeyboardInterrupt:
        pass
