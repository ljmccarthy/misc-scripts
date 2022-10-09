# Recursively rename JPEG files using the EXIF datetime to the format: IMG_%Y%m%d_%H%M%S
# and also sets the file timestamp on the filesystem to the same datetime.
#
# Luke McCarthy 2022-10-09

TIME_ZONE = 'Europe/London'

from datetime import datetime, timezone
import exifread
import os
import pytz
import sys

tzinfo = pytz.timezone(TIME_ZONE)

def read_exif(filename):
    with open(filename, 'rb') as f:
        return exifread.process_file(f)

def parse_exif_datetime(dt_str, subsec=None):
    dt = datetime.strptime(str(dt_str), '%Y:%m:%d %H:%M:%S')
    if subsec:
        subsec = str(subsec)[:6]
        usec = int(subsec) * 10 ** (6 - len(subsec))
        dt = dt.replace(microsecond=usec)
    return dt

def read_exif_datetime(filename):
    tags = read_exif(filename)
    try:
        exif_dt = str(tags['EXIF DateTimeOriginal'])
        # Fix weird use of 24 for hour 00
        if exif_dt[11:13] == '24':
            exif_dt = exif_dt[:11] + '00' + exif_dt[13:]
        return parse_exif_datetime(exif_dt, tags.get('EXIF SubSecTimeOriginal'))
    except (KeyError, ValueError) as e:
        print('error parsing exif datetime:', e)

def set_file_timestamp(filename, dt):
    dt = tzinfo.localize(dt)
    file_timestamp = os.stat(filename).st_mtime
    exif_timestamp = dt.timestamp()
    if exif_timestamp != file_timestamp:
        print('setting modified time {} for {}'.format(dt.isoformat(), filename))
        os.utime(filename, (exif_timestamp, exif_timestamp))

def rename_jpg_from_exif(old_filepath):
    dt = read_exif_datetime(old_filepath)
    if dt is not None:
        dirpath, old_filename = os.path.split(old_filepath)
        new_filename = dt.strftime('IMG_%Y%m%d_%H%M%S') + '.jpg'
        new_filepath = os.path.join(dirpath, new_filename)
        if new_filename != old_filename:
            if os.path.exists(new_filepath):
                print('filename already exists, skipping:', new_filepath)
            else:
                print('rename:', old_filepath, '->', new_filepath)
                os.rename(old_filepath, new_filepath)
                set_file_timestamp(new_filepath, dt)
        else:
            set_file_timestamp(old_filepath, dt)
    else:
        print('no valid exif datetime, skipping:', old_filepath)

def fix_file_names_exif(rootdir):
    for dirpath, dirnames, filenames in os.walk(rootdir):
        for filename in filenames:
            if os.path.splitext(filename)[1].lower() in ('.jpg', '.jpeg'):
                rename_jpg_from_exif(os.path.join(dirpath, filename))

def main():
    if len(sys.argv) == 1:
        fix_file_names_exif('.')
    elif len(sys.argv) == 2:
        fix_file_names_exif(sys.argv[1])
    else:
        print('usage: fix_file_names_exif.py [dir]', file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
