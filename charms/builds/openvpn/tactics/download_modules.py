#!/usr/bin/python2
# Copyright (C) 2017  Ghent University
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import os
import errno
import shutil
import tarfile
from subprocess import check_call
from distutils.dir_util import copy_tree

import charmtools
from charmtools.build.tactics import Tactic


def make_tarfile(output_filename, source_dir):
    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))


class DownloadModulesTactic(Tactic):
    """ This tactic is used by charm-tools to download the modules from the
    Puppetfile at `charm build` time. """

    @classmethod
    def trigger(cls, entity, target, layer, next_config):
        """ Determines which files the tactic should apply to.
        """
        return str(entity).endswith("/files/puppet")

    @property
    def dest(self):
        """ The destination folder we are writing to."""
        return self.target / "files" / "puppet"

    def __call__(self):
        """ When the tactic is called, download puppet dependencies and remove
        useless folders."""
        try:
            os.makedirs(self.dest)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise
        copy_tree(self.entity, self.dest)
        check_call(['librarian-puppet', 'install', '--verbose'], cwd=self.dest)
        make_tarfile(self.dest / "modules.tgz", self.dest / "modules")
        shutil.rmtree(self.dest / 'modules')
        shutil.rmtree(self.dest / '.tmp')
        shutil.rmtree(self.dest / '.librarian')

    def sign(self):
        """ Return signatures for the charm build manifest. We need to do this
        because the addon template files were added dynamically """
        sigs = {}
        for filee in os.listdir(self.dest):
            path = self.dest / filee
            relpath = path.relpath(self.target.directory)
            sigs[relpath] = (
                self.current.url,
                "dynamic",
                charmtools.utils.sign(path)
            )
        return sigs
