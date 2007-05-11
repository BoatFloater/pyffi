# --------------------------------------------------------------------------
# FileFormat.XmlFileFormat
# Metaclass for parses file format description in XML format.
# Actual implementation of the parser is delegated to FileFormat.XmlHandler.
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

from XmlHandler import XmlHandler

import xml.sax
import os.path

class MetaXmlFileFormat(type):
    """The MetaXmlFileFormat metaclass transforms the XML description of a
    file format into a bunch of classes which can be directly used to
    manipulate files in this format.

    In particular, a file format corresponds to a particular class with
    subclasses corresponding to different file block types, compound
    types, enum types, and basic types. See NifFormat.py for an example
    of how to use MetaXmlFileFormat.
    """
    
    def __init__(cls, name, bases, dct):
        """This function constitutes the core of the class generation
        process. For instance, we declare NifFormat to have metaclass
        MetaXmlFileFormat, so upon creation of the NifFormat class,
        the __init__ function is called, with
    
        cls   : NifFormat
        name  : 'NifFormat'
        bases : a tuple (object,) since NifFormat is derived from object
        dct   : dictionary of NifFormat attributes, such as 'xmlFileName'
        """

        # consistency checks
        if not dct.has_key('xmlFileName'):
            raise TypeError("class " + str(cls) + " : missing xmlFileName attribute")
        if not dct.has_key('versionNumber'):
            raise TypeError("class " + str(cls) + " : missing versionNumber attribute")

        # set up XML parser
        parser = xml.sax.make_parser()
        parser.setContentHandler(XmlHandler(cls, name, bases, dct))

        # open XML file
        if not dct.has_key('xmlFilePath'):
            f = open(dct['xmlFileName'])
        else:
            f = open(os.path.join(dct['xmlFilePath'], dct['xmlFileName']))

        # parse the XML file: control is now passed on to XmlHandler
        # which takes care of the class creation
        try:
            parser.parse(f)
        finally:
            f.close()

