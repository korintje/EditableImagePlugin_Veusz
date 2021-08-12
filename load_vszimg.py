# -*- coding: utf-8 -*-
from veusz.plugins import ToolsPlugin, toolspluginregistry
from array import array
import veusz.qtall as qt
import xml.etree.ElementTree as ET
import io, struct, warnings, zlib


class LoadVSZImagePlugin(ToolsPlugin):
    """Load re-editable images cotaining internal Veusz code."""
    menu = ('Load Veusz-image',)
    name = 'Load Veusz-image'
    description_short = 'Load Veusz-image.'
    description_full = 'Press "Apply" to select image (PNG or SVG).'
    
    def __init__(self):
        """Press Apply button to start Loading."""
        self.fields = []
                    
    def apply(self, interface, fields):
        """
        Select and load image file from a dialog.
        All widgets in the current window will be wiped.  
        """
        # Get file path and format
        get_filepath = qt.QFileDialog.getOpenFileName
        (filepath, fltr) = get_filepath(caption='Load', filter="Images (*.png *.svg)")
        if filepath[-4:] in (".png", ".PNG"):
            script = self.get_script_from_png(filepath)
        elif filepath[-4:] in (".svg", ".SVG"):
            script = self.get_script_from_svg(filepath)
        elif filepath == "":
            return
        else:
            raise Exception("The image file format must be .png or .svg")
        if script:
            for child in interface.Root.childnames_widgets:
                interface.Remove(child)
            cmds = [cmd for cmd in dir(interface) if cmd.startswith('__') is False]
            for cmd in cmds:
                exec(f"{cmd} = interface.{cmd}")
            exec(script)        
    
    def get_script_from_png(self, filepath):
        """
        Find "tEXt" chunk in the PNG image with text starting from "# Veusz" and load.
        """
        script = ''
        png = PNGReader(filename = filepath)
        for chunk in png.chunks():
            tag = chunk[0].decode(errors="ignore")
            content = chunk[1].decode(errors="ignore")
            if tag == "tEXt":
                if content[:7] == "# Veusz":
                    script = content
        return script

    def get_script_from_svg(self, filepath):
        """
        Find "metadata" element in the SVG image and load script in the Veusz namespace. 
        """
        namespace = r'{https://veusz.github.io/}'
        script = ''
        root = ET.parse(filepath).getroot()
        vszdata = root.find(f'./metadata/{namespace}veusz')
        script = vszdata.get('script')
        return script


class PNGReader:
    """
    This is a subclass extracted from the library pypng (https://github.com/drj11/pypng)
    with removal of some unused functions.
    """

    def __init__(self, _guess=None, filename=None, file=None, bytes=None):
        keywords_supplied = (
            (_guess is not None) +
            (filename is not None) +
            (file is not None) +
            (bytes is not None))
        if keywords_supplied != 1:
            raise TypeError("PNGReader() takes exactly 1 argument")
        self.signature = None
        self.transparent = None
        self.atchunk = None
        if _guess is not None:
            if isinstance(_guess, array):
                bytes = _guess
            elif isinstance(_guess, str):
                filename = _guess
            elif hasattr(_guess, 'read'):
                file = _guess
        if bytes is not None:
            self.file = io.BytesIO(bytes)
        elif filename is not None:
            self.file = open(filename, "rb")
        elif file is not None:
            self.file = file
        else:
            raise Exception("expecting filename, file or bytes array")

    def chunk(self, lenient=False):
        self.validate_signature()
        if not self.atchunk:
            self.atchunk = self._chunk_len_type()
        if not self.atchunk:
            raise Exception("No more chunks.")
        length, type = self.atchunk
        self.atchunk = None

        data = self.file.read(length)
        if len(data) != length:
            raise Exception(
                'Chunk %s too short for required %i octets.'
                % (type, length))
        checksum = self.file.read(4)
        if len(checksum) != 4:
            raise Exception('Chunk %s too short for checksum.' % type)
        verify = zlib.crc32(type)
        verify = zlib.crc32(data, verify)
        verify &= 2**32 - 1
        verify = struct.pack('!I', verify)
        if checksum != verify:
            (a, ) = struct.unpack('!I', checksum)
            (b, ) = struct.unpack('!I', verify)
            message = ("Checksum error in %s chunk: 0x%08X != 0x%08X."
                    % (type.decode('ascii'), a, b))
            if lenient:
                warnings.warn(message, RuntimeWarning)
            else:
                raise Exception(message)
        return type, data

    def chunks(self):
        while True:
            t, v = self.chunk()
            yield t, v
            if t == b'IEND':
                break

    def validate_signature(self):
        signature = struct.pack('8B', 137, 80, 78, 71, 13, 10, 26, 10)
        if self.signature:
            return
        self.signature = self.file.read(8)
        if self.signature != signature:
            raise Exception("PNG file has invalid signature.")

    def _chunk_len_type(self):
        x = self.file.read(8)
        if not x:
            return None
        if len(x) != 8:
            raise Exception(
                'End of file whilst reading chunk length and type.')
        length, type = struct.unpack('!I4s', x)
        if length > 2 ** 31 - 1:
            raise Exception('Chunk %s is too large: %d.' % (type, length))
        type_bytes = set(bytearray(type))
        if not(type_bytes <= set(range(65, 91)) | set(range(97, 123))):
            raise Exception(
                'Chunk %r has invalid Chunk Type.'
                % list(type))
        return length, type


toolspluginregistry.append(LoadVSZImagePlugin)