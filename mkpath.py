import sys, os, os.path, errno

def mkpath(path):
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
