#!/usr/bin/env python3

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
    tags = flatten(("--comment", "{0}={1}".format(tag, value)) for tag, value in get_flac_tags(input_file))
    p = subprocess.Popen(
        ["flac", "--decode", "--stdout", input_file], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return subprocess.call(["opusenc"] + tags + ["-", output_file], stdin=p.stdout)

def flac2opus(args):
    if len(args) != 2:
        sys.stderr.write("usage: flac2opus INPUT.flac OUTPUT.opus\n")
        sys.exit(1)
    else:
        opusenc(args[0], args[1])

if __name__ == "__main__":
    try:
        flac2opus(sys.argv[1:])
    except KeyboardInterrupt:
        pass
