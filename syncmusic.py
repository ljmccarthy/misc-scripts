# sync music from source to destination directory
# copy opus, ogg, mp3, as-is
# encode flac as opus

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
            tags.append((tag[0].upper(), tag[1]))
    return tags

def flatten(xxs):
    return [x for xs in xxs for x in xs]

def opusenc(input_file, output_file):
    print("Encoding: {0}" .format(output_file))
    tags = flatten(("--comment", "{0}={1}".format(tag, value)) for tag, value in get_flac_tags(input_file))
    p = subprocess.Popen(
        ["flac", "--decode", "--stdout", input_file],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return subprocess.call(["opusenc"] + tags + ["-", output_file], stdin=p.stdout)

def aacenc(input_file, output_file):
    print("Encoding: {0}" .format(output_file))
    tags = dict(get_flac_tags(input_file))
    p = subprocess.Popen(
        ["flac", "--decode", "--stdout", input_file],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return subprocess.call([
        "fdkaac",
        "--title", tags.get("TITLE", ""),
        "--artist", tags.get("ARTIST", ""),
        "--album", tags.get("ALBUM", ""),
        "--track", tags.get("TRACKNUMBER", ""),
        "--disk", tags.get("DISCNUMBER", ""),
        "--genre", tags.get("GENRE", ""),
        "--date", tags.get("DATE", ""),
        "--bitrate", "128",
        "-o", output_file, "-"],
        stdin=p.stdout)

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

def find_files(path):
    for dirpath, dirnames, filenames in os.walk(path):
        dirnames.sort()
        filenames.sort()
        for filename in filenames:
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

def replace_extension(filename, ext_from, ext_to):
    name, ext = split_ext(filename)
    return name + os.path.extsep + ext_to if ext == ext_from else filename

invalid_chars_re = re.compile(r'["*:<>?\[\]|]')

def replace_invalid_chars(filename):
    return os.path.sep.join(invalid_chars_re.sub("_", part.rstrip(".")) for part in filename.split(os.path.sep))

music_extensions = ("flac", "m4a", "aac", "opus", "ogg", "mp3")

def sync_music(srcpath, dstpath, encoder, extension):
    srcfiles = list(find_files_by_extension(srcpath, music_extensions))
    srcfiles = find_preferred_files(srcfiles, music_extensions)
    dstfiles = frozenset(find_files(dstpath))

    files_to_delete = sorted(dstfiles - frozenset(replace_invalid_chars(replace_extension(x, "flac", extension)) for x in srcfiles))
    for filename in files_to_delete:
        filename = os.path.join(dstpath, filename)
        print("Removing:", filename)
        remove(filename)

    for filename in srcfiles:
        srcfile = os.path.join(srcpath, filename)
        dstfile = os.path.join(dstpath, replace_invalid_chars(filename))
        make_path(os.path.dirname(dstfile))
        try:
            if split_ext(filename)[1] == "flac":
                dstfile = os.path.splitext(dstfile)[0] + os.path.extsep + extension
                if not os.path.exists(dstfile) or file_newer(srcfile, dstfile):
                    rc = encoder(srcfile, dstfile)
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

def sync_music_opus(srcpath, dstpath):
    sync_music(srcpath, dstpath, encoder=opusenc, extension="opus")

def sync_music_vorbis(srcpath, dstpath):
    sync_music(srcpath, dstpath, encoder=oggenc, extension="ogg")

def sync_music_aac(srcpath, dstpath):
    sync_music(srcpath, dstpath, encoder=aacenc, extension="aac")

__all__ = [
    "sync_music_opus",
    "sync_music_vorbis",
    "sync_music_aac",
]
