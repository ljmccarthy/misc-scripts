#!/usr/bin/python

import sys, os, time, shutil, getopt, errno, traceback

class DirSyncFS(object):
    def __init__(self, dryrun=True):
        self.dryrun = dryrun

    def copy(self, src, dst):
        if not self.dryrun:
            try:
                shutil.copy2(src, dst)
            except OSError as e:
                if e.errno != errno.EOPNOTSUPP:
                    raise

    def copystat(self, src, dst):
        if not self.dryrun:
            try:
                shutil.copystat(src, dst)
            except OSError as e:
                if e.errno != errno.EOPNOTSUPP:
                    raise

    def mkdir(self, path):
        if not self.dryrun:
            try:
                os.makedirs(path)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise

    def rmdir(self, path):
        if not self.dryrun:
            os.rmdir(path)

    def remove(self, path):
        if not self.dryrun:
            os.remove(path)

def stat_changed(src, dst):
    # Allow 2 second error for rubbish filesystems
    # and 1 hour difference for unadjusted DST
    time_diff = abs(src.st_mtime - dst.st_mtime)
    return ((2.0 < time_diff < 3599.0)
        or (time_diff > 3601.0)
        or src.st_size != dst.st_size)

def relpath(path, root):
    rpath = os.path.relpath(path, root)
    return "" if rpath == "." else rpath

class DirSyncer(object):
    def __init__(self, srcroot, dstroot, dryrun=True, logfile=None):
        self.srcroot = srcroot
        self.dstroot = dstroot
        self.fs = DirSyncFS(dryrun=dryrun)
        self.logfile = logfile
        self.loglines = []

    def log_write(self, s):
        if self.logfile:
            self.loglines.append(s)

    def log(self, *args):
        s = " ".join(str(arg) for arg in args) + "\n"
        self.log_write(s)
        encoding = sys.stdout.encoding
        sys.stdout.write(s.encode(encoding, "replace").decode(encoding))

    def log_marker(self, s):
        self.log_write("==== [{0}] {1}\n".format(get_timestamp(), s))

    def visit_cleanup(self, dstdir, filenames):
        dir = relpath(dstdir, self.dstroot)
        srcdir = os.path.join(self.srcroot, dir)
        for filename in filenames:
            srcfile = os.path.join(srcdir, filename)
            dstfile = os.path.join(dstdir, filename)
            if os.path.isfile(dstfile) and not os.path.isfile(srcfile):
                self.log("REMOVE", os.path.join(dir, filename))
                self.fs.remove(dstfile)
        if not os.path.isdir(srcdir):
            self.log("RMDIR", dir)
            self.fs.rmdir(dstdir)

    def visit_copy(self, srcdir, filenames):
        dir = relpath(srcdir, self.srcroot)
        dstdir = os.path.join(self.dstroot, dir) 
        if os.path.exists(dstdir):
            if not os.path.isdir(dstdir):
                self.log("REMOVE", dir)
                self.fs.remove(dstdir)
                self.log("MKDIR", dir)
                self.fs.mkdir(dstdir)
        else:
            self.log("MKDIR", dir)
            self.fs.mkdir(dstdir)
        self.fs.copystat(srcdir, dstdir)
        for filename in filenames:
            srcfile = os.path.join(srcdir, filename)
            dstfile = os.path.join(dstdir, filename)
            if os.path.isfile(srcfile):
                will_copy = not os.path.exists(dstfile)
                if not will_copy:
                    srcstat = os.stat(srcfile)
                    dststat = os.stat(dstfile)
                    will_copy = stat_changed(srcstat, dststat)
                if will_copy:
                    self.log("COPY", os.path.join(dir, filename))
                    self.fs.copy(srcfile, dstfile)

    def run(self):
        self.log_marker("START src={0} dst={1!r}{2}".format(
            self.srcroot, self.dstroot, " dryrun" if self.fs.dryrun else ""))

        try:
            for dirpath, dirnames, filenames in os.walk(self.dstroot, topdown=False):
                dirnames.sort()
                filenames.sort()
                self.visit_cleanup(dirpath, dirnames + filenames)

            for dirpath, dirnames, filenames in os.walk(self.srcroot, topdown=False):
                dirnames.sort()
                filenames.sort()
                self.visit_copy(dirpath, dirnames + filenames)
        except:
            print(traceback.format_exc())
            self.log_write(traceback.format_exc())
            self.log_marker("ABORT\n")
            raise
        else:
            self.log_marker("FINISH\n")

        if self.logfile:
            with open(self.logfile, "a") as f:
                f.write("".join(self.loglines))
                self.loglines = []

def get_timestamp():
    return time.strftime("%Y-%m-%d %H:%M:%S")

def syncdirs(srcroot, dstroot, dryrun=True, logfile=None):
    dirsync = DirSyncer(srcroot, dstroot, dryrun=dryrun, logfile=logfile)
    dirsync.run()

usage = "usage: %s [--commit] [--logfile=LOGFILE] SRCDIR DSTDIR" % sys.argv[0]

def main(args):
    try:
        opts, args = getopt.gnu_getopt(args, "", ["commit", "logfile="])
    except getopt.GetoptError as e:
        print(str(e) + "\n\n" + usage)
        sys.exit(2)
    if len(args) != 2:
        print(usage)
        sys.exit(2)
    src, dst = args
    dryrun = True
    logfile = None
    for o, a in opts:
        if o == "--commit":
            dryrun = False
        elif o == "--logfile":
            logfile = a
        else:
            print("Unknown option:", o)
            print(usage)
            sys.exit(2)
    try:
        syncdirs(src, dst, dryrun=dryrun, logfile=logfile)
    except SystemExit:
        raise
    except:
        print(sys.exc_info()[1])
        sys.exit(1)

if __name__ == "__main__":
    main(sys.argv[1:])
