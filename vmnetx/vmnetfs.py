#
# vmnetx.vmnetfs - Wrapper for vmnetfs FUSE driver
#
# Copyright (C) 2011-2012 Carnegie Mellon University
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of version 2 of the GNU General Public License as published
# by the Free Software Foundation.  A copy of the GNU General Public License
# should have been distributed along with this program in the file
# COPYING.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#

from lxml import etree
import os
import subprocess

from vmnetx.util import DetailException

# system.py is built at install time, so pylint may fail to import it.
# Also avoid warning on variable name.
# pylint: disable=F0401,C0103
vmnetfs_path = ''
from .system import vmnetfs_path
# pylint: enable=F0401,C0103

NS = 'http://olivearchive.org/xmlns/vmnetx/vmnetfs'
NSP = '{' + NS + '}'
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'schema', 'vmnetfs.xsd')

# We want this to be a public attribute
# pylint: disable=C0103
schema = etree.XMLSchema(etree.parse(SCHEMA_PATH))
# pylint: enable=C0103


class VMNetFSError(DetailException):
    pass


class VMNetFS(object):
    def __init__(self, tree):
        try:
            schema.assertValid(tree)
        except etree.DocumentInvalid, e:
            raise VMNetFSError('Argument XML does not validate', str(e))

        self._args = etree.tostring(tree, pretty_print=True, encoding='UTF-8',
                xml_declaration=True)
        self._pipe = None
        self.mountpoint = None

    # pylint is confused by Popen.returncode and the values returned from
    # Popen.communicate()
    # pylint: disable=E1101,E1103
    def start(self):
        read, write = os.pipe()
        try:
            proc = subprocess.Popen([vmnetfs_path], stdin=read,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    close_fds=True)
            self._pipe = os.fdopen(write, 'w')
            self._pipe.write(str(len(self._args)) + '\n')
            self._pipe.write(self._args)
            self._pipe.flush()
            out, err = proc.communicate()
            if len(err) > 0:
                raise VMNetFSError(err.strip())
            elif proc.returncode > 0:
                raise VMNetFSError('vmnetfs returned status %d' %
                        proc.returncode)
            self.mountpoint = out.strip()
        except:
            if self._pipe is not None:
                self._pipe.close()
            else:
                os.close(write)
            raise
        finally:
            os.close(read)
    # pylint: enable=E1101,E1103

    def terminate(self):
        if self._pipe is not None:
            self._pipe.close()
            self._pipe = None
