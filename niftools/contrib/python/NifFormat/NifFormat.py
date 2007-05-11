# --------------------------------------------------------------------------
# NifFormat.NifFormat
# Implementation of the NIF file format; uses FileFormat.XmlFileFormat.
# --------------------------------------------------------------------------
# ***** BEGIN LICENSE BLOCK *****
#
# Copyright (c) 2007, NIF File Format Library and Tools.
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
#    * Neither the name of the NIF File Format Library and Tools
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
# ***** END LICENCE BLOCK *****
# --------------------------------------------------------------------------

import struct
import os.path
from FileFormat.XmlFileFormat import MetaXmlFileFormat
import BasicTypes

class NifError(StandardError):
    pass

class NifFormat(object):
    """Stores all information about the nif file format.
    
    >>> for vnum in sorted(NifFormat.versions.values()): print '0x%08X'%vnum
    0x03000000
    0x03010000
    0x0303000D
    0x04000000
    0x04000002
    0x0401000C
    0x04020002
    0x04020100
    0x04020200
    0x0A000100
    0x0A000102
    0x0A010000
    0x0A01006A
    0x0A020000
    0x14000004
    0x14000005
    >>> print NifFormat.HeaderString
    <class 'NifFormat.BasicTypes.HeaderString'>
    """
    __metaclass__ = MetaXmlFileFormat
    xmlFileName = 'nif.xml'
    xmlFilePath = os.path.dirname(__file__) # path of nif.xml
    clsFilePath = os.path.dirname(__file__) # path of class customizers
    
    # basic types
    int = BasicTypes.Int
    uint = BasicTypes.UInt
    byte = BasicTypes.Byte
    bool = BasicTypes.Bool
    char = BasicTypes.Char
    short = BasicTypes.Short
    ushort = BasicTypes.UShort
    float = BasicTypes.Float
    Ptr = BasicTypes.Ptr
    Ref = BasicTypes.Ref
    BlockTypeIndex = BasicTypes.UShort
    StringOffset = BasicTypes.UInt
    FileVersion = BasicTypes.FileVersion
    Flags = BasicTypes.Flags
    HeaderString = BasicTypes.HeaderString
    LineString = BasicTypes.LineString
    # other types with internal implementation
    string = BasicTypes.String
    ShortString = BasicTypes.ShortString

    @staticmethod
    def versionNumber(version_str):
        """Converts version string into an integer.

        >>> hex(NifFormat.versionNumber('3.14.15.29'))
        '0x30e0f1d'
        >>> hex(NifFormat.versionNumber('1.2'))
        '0x1020000'
        """
        
        v = version_str.split('.')
        num = 0
        shift = 24
        for x in v:
            num += int(x) << shift
            shift -= 8
        return num

    @staticmethod
    def nameAttribute(name):
        """Converts an attribute name, as in the xml file, into a name usable by python.

        >>> NifFormat.nameAttribute('tHis is A Silly naME')
        'thisIsASillyName'
        """
        
        parts = str(name).split() # str(name) converts name to string in case name is a unicode string
        attrname = parts[0].lower()
        for part in parts[1:]:
            attrname += part.capitalize()
        return attrname

    @classmethod
    def getVersion(cls, f):
        """Returns version and user version number, if version is supported.
        Returns -1, 0 if version is not supported.
        Returns -2, 0 if <f> is not a nif file.
        """
        pos = f.tell()
        try:
            s = f.readline(64).rstrip()
        finally:
            f.seek(pos)
        if s.startswith("NetImmerse File Format, Version " ):
            ver_str = s[32:]
        elif s.startswith("Gamebryo File Format, Version "):
            ver_str = s[30:]
        else:
            return -2, 0 # not a nif file
        try:
            ver_list = [int(x) for x in ver_str.split('.')]
        except ValueError:
            return -1, 0 # version not supported (i.e. ver_str '10.0.1.3a' would trigger this)
        if len(ver_list) > 4 or len(ver_list) < 1:
            return -1, 0 # version not supported
        for ver_digit in ver_list:
            if (ver_digit | 0xff) > 0xff:
                return -1, 0 # version not supported
        while len(ver_list) < 4: ver_list.append(0)
        ver = (ver_list[0] << 24) + (ver_list[1] << 16) + (ver_list[2] << 8) + ver_list[3]
        if not ver in cls.versions.values():
            return -1, 0 # unsupported version
        # check version integer and user version
        userver = 0
        if ver >= 0x0303000D:
            ver_int = None
            try:
                f.readline(64)
                ver_int, = struct.unpack('<I', f.read(4))
                if ver_int != ver:
                    return -2, 0 # not a nif file
                if ver >= 0x14000004: f.read(1)
                if ver >= 0x0A010000: userver, = struct.unpack('<I', f.read(4))
            finally:
                f.seek(pos)
        return ver, userver

    @classmethod
    def read(cls, version, user_version, f, verbose = 0):
        # read header
        if verbose >= 1:
            print "reading block at 0x%08X..."%f.tell()
        hdr = cls.Header()
        link_stack = [] # list of indices, as they are added to the stack
        hdr.read(version, user_version, f, link_stack, None)
        assert(link_stack == []) # there should not be any links in the header
        if verbose >= 2:
            print hdr

        # read the blocks
        block_dct = {} # maps block index to actual block
        block_list = [] # records all blocks as read from the nif file in the proper order
        block_num = 0 # the current block numner

        if version < 0x0303000D:
            # skip 'Top Level Object' block type
            top_level_str = cls.string()
            top_level_str.read(version, user_version, f, link_stack, None)
            top_level_str = str(top_level_str)
            if not top_level_str == "Top Level Object":
                raise NifError("expected 'Top Level Object' but got '%s' instead"%top_level_str)

        while True:
            # get block name
            if version >= 0x05000001:
                if version <= 0x0A01006A:
                    dummy, = struct.unpack('<I', f.read(4))
                    if dummy != 0:
                        raise NifError('non-zero block tag 0x%08X at 0x%08X)'%(dummy, f.tell()))
                block_type = hdr.blockTypes[hdr.blockTypeIndex[block_num]]
            else:
                block_type = cls.string()
                block_type.read(version, user_version, f, link_stack, None)
                block_type = str(block_type)
            # get the block index
            if version >= 0x0303000D:
                # for these versions the block index is simply the block number
                block_index = block_num
            else:
                # earlier versions
                # the number of blocks is not in the header
                # and a special block type string marks the end of the file
                if block_type == "End Of File": break
                # read the block index, which is probably the memory
                # location of the object when it was written to
                # memory
                else:
                    block_index, = struct.unpack('<I', f.read(4))
                    if block_dct.has_key(block_index):
                        raise NifError('duplicate block index (0x%08X at 0x%08X)'%(block_index, f.tell()))
            # create and read block
            try:
                block = getattr(cls, block_type)()
            except AttributeError:
                raise NifError("unknown block type '" + block_type + "'")
            if verbose >= 1:
                print "reading block at 0x%08X..."%f.tell()
            try:
                block.read(version, user_version, f, link_stack, None)
            except:
                if verbose >= 1:
                    print "reading failed"
                if verbose >= 2:
                    print block
                elif verbose >= 1:
                    print block.__class__
                raise
            block_dct[block_index] = block
            block_list.append(block)
            if verbose >= 2:
                print block
            elif verbose >= 1:
                print block.__class__
            # check if we are done
            block_num += 1
            if version >= 0x0303000D:
                if block_num >= hdr.numBlocks: break

        # read footer
        ftr = cls.Footer()
        ftr.read(version, user_version, f, link_stack, None)

        # check if we are at the end of the file
        if f.read(1) != '':
            raise NifError('end of file not reached: corrupt nif file?')

        # fix links
        for block in block_list:
            block.fixLinks(version, user_version, block_dct, link_stack)
        ftr.fixLinks(version, user_version, block_dct, link_stack)
        if link_stack != []:
            raise NifError('not all links have been popped from the stack (bug?)')
        # return root objects
        roots = []
        if version >= 0x0303000D:
            for root in ftr.roots:
                roots.append(root)
        else:
            if block_num > 0:
                roots.append(block_list[0])
        return roots

    @classmethod
    def write(cls, version, user_version, f, roots, verbose = 0):
        # set up index and type dictionary
        block_list = [] # list of all blocks to be written
        block_index_dct = {} # maps block to block index
        block_type_list = [] # list of all block type strings
        block_type_dct = {} # maps block to block type string index
        for root in roots:
            cls.makeBlockList(version, user_version, root, block_list, block_index_dct, block_type_list, block_type_dct)

        # set up header
        hdr = cls.Header()
        hdr.userVersion = user_version # TODO dedicated type for userVersion similar to FileVersion
        hdr.numBlocks = len(block_list)
        hdr.numBlockTypes = len(block_type_list)
        hdr.blockTypes.updateSize()
        for i, block_type in enumerate(block_type_list):
            hdr.blockTypes[i] = block_type
        hdr.blockTypeIndex.updateSize()
        for i, block in enumerate(block_list):
            hdr.blockTypeIndex[i] = block_type_dct[block]
        if verbose >= 2:
            print hdr

        # set up footer
        ftr = cls.Footer()
        ftr.numRoots = len(roots)
        ftr.roots.updateSize()
        for i, root in enumerate(roots):
            ftr.roots[i] = root

        # write the file
        hdr.write(version, user_version, f, block_index_dct, None)
        if version < 0x0303000D:
            s = cls.string()
            s.setValue("Top Level Object")
            s.write(version, user_version, f, block_index_dct, None)
        for block in block_list:
            if version >= 0x05000001:
                if version <= 0x0A01006A:
                    f.write('\x00\x00\x00\x00') # write zero dummy separator
            else:
                # write block type string
                s = cls.string()
                assert(block_type_list[block_type_dct[block]] == block.__class__.__name__) # debug
                s.setValue(block.__class__.__name__)
                s.write(version, user_version, f, block_index_dct, None)
            # write block index
            if verbose >= 1:
                print "writing block %i..."%block_index_dct[block]
            if version < 0x0303000D:
                f.write(struct.pack('<i', block_index_dct[block])[0])
            # write block
            block.write(version, user_version, f, block_index_dct, None)
        if version < 0x0303000D:
            s = cls.string()
            s.setValue("End Of File")
            s.write(version, user_version, f, block_index_dct, None)
        ftr.write(version, user_version, f, block_index_dct, None)

    @classmethod
    def makeBlockList(cls, version, user_version, root, block_list, block_index_dct, block_type_list, block_type_dct, reverse = False):
        # block already listed? if so, return
        if root in block_list: return
        # add block type to block type dictionary
        block_type = root.__class__.__name__
        try:
            block_type_dct[root] = block_type_list.index(block_type)
        except ValueError:
            block_type_dct[root] = len(block_type_list)
            block_type_list.append(block_type)
        # check if we need to add children first (required for oblivion)
        if isinstance(root, cls.bhkRigidBody) or isinstance(root, cls.bhkCollisionObject):
            reverse = True
        # add block if not reverse
        if not reverse:
            if version >= 0x0303000D:
                block_index_dct[root] = len(block_list)
            else:
                block_index_dct[root] = id(root)
            block_list.append(root)
        # add children
        for child in root.getLinks(version, user_version):
            cls.makeBlockList(version, user_version, child, block_list, block_index_dct, block_type_list, block_type_dct, reverse)
        # add block if reverse
        if reverse:
            block_index_dct[root] = len(block_list)
            block_list.append(root)
