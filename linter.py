#
# linter.py
# Linter for SublimeLinter3, a code checking framework for Sublime Text 3
#
# Written by Alec Thomas
# Copyright (c) 2014 Alec Thomas
#
# License: MIT
#

"""This module exports the Gometalinter plugin class."""

import os, subprocess, tempfile, re, fnmatch, time
from os import path


from SublimeLinter.lint import Linter, highlight, util


class Gometalinter(Linter):
    """Provides an interface to gometalinter."""

    syntax = ('go', 'gosublime-go', 'gotools')
    cmd = 'gometalinter * '
    regex = r'(?:[^:]+):(?P<line>\d+):(?P<col>\d+)?:(?:(?P<warning>warning)|(?P<error>error)):\s*(?P<message>.*)'
    error_stream = util.STREAM_BOTH
    default_type = highlight.ERROR

    def __init__(self, view, syntax):
        """Initialize and load GOPATH from settings if present."""
        Linter.__init__(self, view, syntax)

        gopath = self.get_view_settings().get('gopath')
        if gopath:
            if self.env:
                self.env['GOPATH'] = gopath
            else:
                self.env = {'GOPATH': gopath}
            print('sublimelinter: GOPATH={}'.format(self.env['GOPATH']))
        else:
            print('sublimelinter: using system GOPATH={}'.format(os.environ.get('GOPATH', '')))

    def run(self, cmd, code):
        # return
        print('--------')
        files = [f for f in os.listdir(path.dirname(self.filename)) if f.endswith('.go')]

        return self.tmpdir(cmd, files, code)

    # creates tmp directory whith clone structure of gopath direcory by symlinks, write linting file. Change GOPATH env to new tmp dir, execute gometalinter and clear all this.
    def tmpdir(self, cmd, files, code):
        filename = path.basename(self.filename)
        dirname = path.dirname(self.filename)

        gopath = path.expanduser(self.get_view_settings().get('gopath'))

        fakegopath = path.join(tempfile.tempdir,'gometalinter',)

        if not path.exists(fakegopath):
            os.makedirs(fakegopath)

        fakegopath = tempfile.mkdtemp(dir=fakegopath)

        os.environ['GOPATH']=fakegopath
        fakepathwd = dirname.replace(gopath, fakegopath)

        if not path.exists(fakepathwd):
            os.makedirs(fakepathwd)

        if not path.exists(path.join(fakegopath,'pkg')):
            os.symlink(path.join(gopath,'pkg'),path.join(fakegopath,'pkg'))

        lintfile = path.join(fakepathwd,filename)

        # if path.exists(lintfile):
        #     os.remove(lintfile)

        f = open(lintfile, 'w+')
        f.write(code)
        f.read()

        # recursive creates symlinks from the path of lint file
        p = dirname
        while p != gopath:
            self.linker(p, gopath, fakegopath)
            p = path.dirname(p)

        os.chdir(fakepathwd)
        cmd = ' '.join(cmd)+' -I ^%s'%filename
        out = self.execute(cmd)

        os.environ['GOPATH']=gopath
        self.removetmpdir(fakegopath)

        return out

    # create symlinks for all files and dirs in directory
    def linker(self, dirname, gopath, fakegopath):
        for f in os.listdir(dirname):
            fakedir = dirname.replace(gopath, fakegopath)
            target = path.join(fakedir,f)
            # if path.isfile(target):
                # os.remove(target)
            if path.exists(target):
                continue
            os.symlink(path.join(dirname,f),target)

        return

    def execute(self, cmd):
        # time.sleep(3)
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,shell=True)
        (output, err) = p.communicate()

        if err is not None:
            print('ERROR occurred while executing gometalinter:')
            print(output)
            print(err)

        if len(output)>0:
            return output.decode('utf-8')

    # clear and remove tmp directory
    def removetmpdir(self, tmpdir):
        for root, dirs, files in os.walk(tmpdir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                if path.islink(os.path.join(root, name)):
                    os.remove(os.path.join(root, name))
                else:
                    os.rmdir(os.path.join(root, name))

        os.rmdir(tmpdir)
                # os.rmdir(os.path.join(root, name))
