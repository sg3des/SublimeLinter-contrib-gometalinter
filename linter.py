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

import os, subprocess, tempfile, re, codecs, shutil
from os import path
from SublimeLinter.lint import Linter, highlight, util
from SublimeLinter.lint.persist import settings



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
        lint_mode = settings.get('lint_mode')

        if self.view.is_dirty() is False:
            return self.linthere(cmd)

        if lint_mode == 'load/save' or lint_mode == 'save only':
            return self.linthere(cmd)

        files = os.listdir(os.path.dirname(self.filename))
        # need be supplemented by other similar situations
        if 'vendor' in self.filename or 'vendor' in files:
            return self.linttmp(cmd, code)

        return self.shorttmp(cmd, code)

    def linthere(self, cmd):
        cmd = ''.join(cmd)+' . -I ^%s'%path.basename(self.filename)
        return self.execute(cmd)

    def shorttmp(self, cmd, code):
        cmd = cmd + ['.','-I','^%s'%os.path.basename(self.filename)]
        files = [f for f in os.listdir(os.path.dirname(self.filename)) if f.endswith('.go')]
        return self.tmpdir(cmd, files, code)

    # creates tmp directory whith clone structure of gopath direcory by symlinks, write linting file. Change GOPATH env to new tmp dir, execute gometalinter and clear all this.
    def linttmp(self, cmd, code):
        filename = path.basename(self.filename)
        dirname = path.dirname(self.filename)

        gopath = self.determineGopath()

        fakegopath = path.join(tempfile.tempdir,'gometalinter',)

        if not path.exists(fakegopath):
            os.makedirs(fakegopath)

        fakegopath = tempfile.mkdtemp(dir=fakegopath)

        fakepathwd = dirname.replace(gopath, fakegopath)

        if not path.exists(fakepathwd):
            os.makedirs(fakepathwd)

        if not path.exists(path.join(fakegopath,'pkg')):
            os.symlink(path.join(gopath,'pkg'),path.join(fakegopath,'pkg'))

        lintfile = path.join(fakepathwd,filename)

        # if path.exists(lintfile):
        #     os.remove(lintfile)

        with codecs.open(lintfile, 'w', encoding='utf8') as f:
            f.write(code)

        # recursive creates symlinks from the path of lint file
        p = dirname
        while p != gopath:
            self.linker(p, gopath, fakegopath)
            p = path.dirname(p)

        os.chdir(fakepathwd)
        cmd = 'GOPATH=%s '%fakegopath+' '.join(cmd)+' -I ^%s'%filename

        out = self.execute(cmd)

        shutil.rmtree(fakegopath)

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

    def determineGopath(self):
        gopath = self.get_view_settings().get('gopath')
        if gopath:
            return path.expanduser(gopath)
        
        if self.env and self.env['GOPATH']:
            return path.expanduser(self.env['GOPATH'])

        gopath = os.environ.get('GOPATH')
        if gopath:
            if ":" in gopath:
                gopath = gopath.split(':')
                return gopath[0]

            return gopath

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
