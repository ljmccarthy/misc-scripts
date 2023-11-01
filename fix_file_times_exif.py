# Script to fix file modified datetimes of JPEG images using EXIF data.
# Requires pytz and exifread (pip install pytz exifread).
#
# Luke McCarthy 2017-01-09

TIME_ZONE = 'Europe/London'

import sys
import exifread
import os
import pytz
from datetime import datetime, timezone

def read_exif(filename):
    with open(filename, 'rb') as f:
        return exifread.process_file(f)

def parse_exif_datetime(dt, subsec=None):
    dt = datetime.strptime(str(dt), '%Y:%m:%d %H:%M:%S')
    if subsec:
        subsec = str(subsec)[:6]
        usec = int(subsec) * 10 ** (6 - len(subsec))
        dt = dt.replace(microsecond=usec)
    return dt

def read_exif_datetime(filename):
    tags = read_exif(filename)
    try:
        return parse_exif_datetime(tags['EXIF DateTimeOriginal'], tags.get('EXIF SubSecTimeOriginal'))
    except (KeyError, ValueError):
        pass

def set_file_time_from_exif(filename, tzinfo=timezone.utc):
    dt = read_exif_datetime(filename)
    if dt:
        dt = tzinfo.localize(dt)
        file_timestamp = os.stat(filename).st_mtime
        exif_timestamp = dt.timestamp()
        if exif_timestamp != file_timestamp:
            print('setting modified time {} -> {} for {}'.format(datetime.fromtimestamp(file_timestamp).isoformat(), dt.isoformat(), filename))
            os.utime(filename, (exif_timestamp, exif_timestamp))

def fix_file_times_exif(rootdir, timezone=TIME_ZONE):
    tzinfo = pytz.timezone(timezone)
    for dirpath, dirnames, filenames in os.walk(rootdir):
        for filename in filenames:
            if os.path.splitext(filename)[1].lower() in ('.jpg', '.jpeg'):
                set_file_time_from_exif(os.path.join(dirpath, filename), tzinfo)

if __name__ == '__main__':
    fix_file_times_exif(sys.argv[1])
