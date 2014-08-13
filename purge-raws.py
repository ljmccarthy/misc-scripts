#!/usr/bin/env python3

import os

PHOTOS_ROOT = '/data/photos'

RAW_EXTENSIONS = ['.RW2']

for dirpath, dirnamess, filenames in os.walk(PHOTOS_ROOT):
    for filename in filenames:
        if filename.lower().endswith('.jpg'):
            for ext in RAW_EXTENSIONS:
                raw_filename = os.path.splitext(filename)[0] + ext
                raw_path = os.path.join(dirpath, raw_filename)
                if os.path.exists(raw_path):
                    print('Deleting {0}'.format(raw_path))
