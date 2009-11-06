"""
:mod:`pyffi.formats.egm` --- EGM (.egm)
=======================================

An .egm file contains facial shape modifiers, that is, morphs that modify
static properties of the face, such as nose size, chin shape, and so on.

Implementation
--------------

.. autoclass:: EgmFormat
   :show-inheritance:
   :members:

Regression tests
----------------

Read a EGM file
^^^^^^^^^^^^^^^

>>> # check and read egm file
>>> stream = open('tests/egm/mmouthxivilai.egm', 'rb')
>>> data = EgmFormat.Data()
>>> data.inspectQuick(stream)
>>> data.version
2
>>> data.inspect(stream)
>>> data.header.num_vertices
89
>>> data.header.num_sym_morphs
50
>>> data.header.num_asym_morphs
30
>>> data.header.time_date_stamp
2001060901
>>> data.read(stream)
>>> data.sym_morphs[0].vertices[0].x
17249

Parse all EGM files in a directory tree
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

>>> for stream, data in EgmFormat.walkData('tests/egm'):
...     print(stream.name)
tests/egm/mmouthxivilai.egm

Create an EGM file from scratch and write to file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

>>> data = EgmFormat.Data(num_vertices=10)
>>> data.header.num_vertices
10
>>> morph = data.add_sym_morph()
>>> len(morph.vertices)
10
>>> morph.scale = 0.4
>>> morph.vertices[0].z = 123
>>> morph.vertices[9].x = -30000
>>> morph = data.add_asym_morph()
>>> morph.scale = 2.3
>>> morph.vertices[3].z = -5
>>> morph.vertices[4].x = 99
>>> from tempfile import TemporaryFile
>>> stream = TemporaryFile()
>>> data.write(stream)
"""

# ***** BEGIN LICENSE BLOCK *****
#
# Copyright (c) 2007-2009, Python File Format Interface
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#    * Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials provided
#      with the distribution.
#
#    * Neither the name of the Python File Format Interface
#      project nor the names of its contributors may be used to endorse
#      or promote products derived from this software without specific
#      prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# ***** END LICENSE BLOCK *****

from itertools import izip
import struct
import os
import re

import pyffi.object_models.xml
from pyffi.object_models import Common
from pyffi.object_models.xml.Basic import BasicBase
import pyffi.object_models
from pyffi.utils.graph import EdgeFilter

class EgmFormat(pyffi.object_models.xml.FileFormat):
    """This class implements the EGM format."""
    xmlFileName = 'egm.xml'
    # where to look for egm.xml and in what order:
    # EGMXMLPATH env var, or EgmFormat module directory
    xmlFilePath = [os.getenv('EGMXMLPATH'), os.path.dirname(__file__)]
    # file name regular expression match
    RE_FILENAME = re.compile(r'^.*\.egm$', re.IGNORECASE)
    # used for comparing floats
    _EPSILON = 0.0001

    # basic types
    int = Common.Int
    uint = Common.UInt
    byte = Common.Byte
    ubyte = Common.UByte
    char = Common.Char
    short = Common.Short
    ushort = Common.UShort
    float = Common.Float

    # implementation of egm-specific basic types

    class FileSignature(BasicBase):
        """Basic type which implements the header of a EGM file."""
        def __init__(self, **kwargs):
            BasicBase.__init__(self, **kwargs)

        def __str__(self):
            return 'FREGM'

        def getDetailDisplay(self):
            return self.__str__()

        def getHash(self, **kwargs):
            """Return a hash value for this value.

            :return: An immutable object that can be used as a hash.
            """
            return None

        def read(self, stream, **kwargs):
            """Read header string from stream and check it.

            :param stream: The stream to read from.
            :type stream: file
            """
            hdrstr = stream.read(5)
            # check if the string is correct
            if hdrstr != "FREGM".encode("ascii"):
                raise ValueError(
                    "invalid EGM header: expected 'FREGM' but got '%s'"
                    % hdrstr)

        def write(self, stream, **kwargs):
            """Write the header string to stream.

            :param stream: The stream to write to.
            :type stream: file
            """
            stream.write("FREGM".encode("ascii"))

        def getSize(self, **kwargs):
            """Return number of bytes the header string occupies in a file.

            :return: Number of bytes.
            """
            return 5

    class FileVersion(BasicBase):
        def getValue(self):
            raise NotImplementedError

        def setValue(self, value):
            raise NotImplementedError

        def __str__(self):
            return 'XXX'

        def getSize(self, **kwargs):
            return 3

        def getHash(self, **kwargs):
            return None

        def read(self, stream, **kwargs):
            ver = stream.read(3)
            if ver != '%03i' % kwargs['data'].version:
                raise ValueError(
                    "Invalid version number: expected %03i but got %s."
                    % (kwargs['data'].version, ver))

        def write(self, stream, **kwargs):
            stream.write('%03i' % kwargs['data'].version)

        def getDetailDisplay(self):
            return 'XXX'

    @staticmethod
    def versionNumber(version_str):
        """Converts version string into an integer.

        :param version_str: The version string.
        :type version_str: str
        :return: A version integer.

        >>> EgmFormat.versionNumber('002')
        2
        >>> EgmFormat.versionNumber('XXX')
        -1
        """
        try:
            # note: always '002' in all files seen so far
            return int(version_str)
        except ValueError:
            # not supported
            return -1

    @staticmethod
    def name_attribute(name):
        """Converts an attribute name, as in the description file,
        into a name usable by python.

        :param name: The attribute name.
        :type name: ``str``
        :return: Reformatted attribute name, useable by python.

        >>> EgmFormat.name_attribute('tHis is A Silly naME')
        'this_is_a_silly_name'
        """

        # str(name) converts name to string in case name is a unicode string
        parts = str(name).split()
        attrname = parts[0].lower()
        for part in parts[1:]:
            attrname += "_" + part.lower()
        return attrname

    class Data(pyffi.object_models.FileFormat.Data):
        """A class to contain the actual egm data."""
        def __init__(self, version=2, num_vertices=0):
            self.header = EgmFormat.Header()
            self.header.num_vertices = num_vertices
            self.sym_morphs = []
            self.asym_morphs = []
            self.version = version
            self.user_version = None # not used

        def inspectQuick(self, stream):
            """Quickly checks if stream contains EGM data, and gets the
            version, by looking at the first 8 bytes.

            :param stream: The stream to inspect.
            :type stream: file
            """
            pos = stream.tell()
            try:
                hdrstr = stream.read(5)
                if hdrstr != "FREGM".encode("ascii"):
                    raise ValueError("Not an EGM file.")
                self.version = EgmFormat.versionNumber(stream.read(3))
            finally:
                stream.seek(pos)

        # overriding pyffi.object_models.FileFormat.Data methods

        def inspect(self, stream):
            """Quickly checks if stream contains EGM data, and reads the
            header.

            :param stream: The stream to inspect.
            :type stream: file
            """
            pos = stream.tell()
            try:
                self.inspectQuick(stream)
                self.header.read(stream, data=self)
            finally:
                stream.seek(pos)


        def read(self, stream):
            """Read a egm file.

            :param stream: The stream from which to read.
            :type stream: ``file``
            """
            # read the file
            self.inspectQuick(stream)
            self.header.read(stream, data=self)
            self.sym_morphs = [
                EgmFormat.MorphRecord(argument=self.header.num_vertices)
                for i in xrange(self.header.num_sym_morphs)]
            self.asym_morphs = [
                EgmFormat.MorphRecord(argument=self.header.num_vertices)
                for i in xrange(self.header.num_asym_morphs)]
            for morph in self.sym_morphs + self.asym_morphs:
                morph.read(stream, data=self, argument=morph.arg)

            # check if we are at the end of the file
            if stream.read(1):
                raise ValueError(
                    'end of file not reached: corrupt egm file?')
            
        def write(self, stream):
            """Write a egm file.

            :param stream: The stream to which to write.
            :type stream: ``file``
            """
            # write the file
            self.header.num_sym_morphs = len(self.sym_morphs)
            self.header.num_asym_morphs = len(self.asym_morphs)
            self.header.write(stream, data=self)
            for morph in self.sym_morphs + self.asym_morphs:
                if morph.arg != self.header.num_vertices:
                    raise ValueError("invalid morph length")
                morph.write(stream, data=self, argument=morph.arg)

        def add_sym_morph(self):
            """Add a symmetric morph, and return it."""
            morph = EgmFormat.MorphRecord(argument=self.header.num_vertices)
            self.sym_morphs.append(morph)
            self.header.num_sym_morphs = len(self.sym_morphs)
            return morph

        def add_asym_morph(self):
            """Add an asymmetric morph, and return it."""
            morph = EgmFormat.MorphRecord(argument=self.header.num_vertices)
            self.asym_morphs.append(morph)
            self.header.num_asym_morphs = len(self.asym_morphs)
            return morph

        # DetailNode

        def getDetailChildNodes(self, edge_filter=EdgeFilter()):
            return self.header.getDetailChildNodes(edge_filter=edge_filter)

        def getDetailChildNames(self, edge_filter=EdgeFilter()):
            return self.header.getDetailChildNames(edge_filter=edge_filter)

        # GlobalNode

        def getGlobalChildNodes(self, edge_filter=EdgeFilter()):
            for morph in self.sym_morphs:
                yield morph
            for morph in self.asym_morphs:
                yield morph

        def getGlobalChildNames(self, edge_filter=EdgeFilter()):
            for morph in self.sym_morphs:
                yield "Sym Morph"
            for morph in self.asym_morphs:
                yield "Asym Morph"

    class MorphRecord:
        """
        >>> # create morph with 3 vertices.
        >>> morph = EgmFormat.MorphRecord(argument=3)
        >>> morph.set_relative_vertices(
        ...     [(3, 5, 2), (1, 3, 2), (-9, 3, -1)])
        >>> # scale should be 9/32768.0 = 0.0002746...
        >>> morph.scale # doctest: +ELLIPSIS
        0.0002746...
        >>> for vert in morph.get_relative_vertices():
        ...     print [int(1000 * x + 0.5) for x in vert]
        [3000, 5000, 2000]
        [1000, 3000, 2000]
        [-8999, 3000, -999]
        """
        def get_relative_vertices(self):
            for vert in self.vertices:
                yield (vert.x * self.scale,
                       vert.y * self.scale,
                       vert.z * self.scale)

        def set_relative_vertices(self, vertices):
            # copy to list
            vertices = list(vertices)
            # check length
            if len(vertices) != self.arg:
                raise ValueError("expected %i vertices, but got %i"
                                 % (self.arg, len(vertices)))
            # get extreme values of morph
            max_value = max(max(abs(value) for value in vert)
                            for vert in vertices)
            # calculate scale
            self.scale = max_value / 32767.0
            inv_scale = 1 / self.scale
            # set vertices
            for vert, self_vert in izip(vertices, self.vertices):
                self_vert.x = int(vert[0] * inv_scale)
                self_vert.y = int(vert[1] * inv_scale)
                self_vert.z = int(vert[2] * inv_scale)
