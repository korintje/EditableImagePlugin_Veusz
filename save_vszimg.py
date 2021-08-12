# -*- coding: utf-8 -*-
from veusz.plugins import ToolsPlugin, toolspluginregistry, FieldInt, FieldCombo
from array import array
import veusz.qtall as qt
import xml.etree.ElementTree as ET
import io, os, tempfile, struct, warnings, zlib


class SaveVSZImagePlugin(ToolsPlugin):
    """Save re-editable images cotaining internal Veusz code."""
    menu = ('Save Veusz-image',)
    name = 'Save Veusz-image'
    description_short = 'Save Veusz-image.'
    description_full = 'Press "Apply" to select image (PNG or SVG).'
    
    def __init__(self):
        """
        file_format: .png or .svg
        page_number: page-number to be exported as image
        """
        self.fields = [
            FieldCombo(
                name="format",
                descr="Image file format",
                items=("PNG", "SVG"), 
                default="PNG"
                ),
            FieldInt(
                name="pagenum",
                descr="Page number for image",
                default=1
                ),
            ]
                    
    def apply(self, interface, fields):
        """
        Set file name and save image.
        """
        # Save temporary .vsz document
        script = ''
        tmpdir = tempfile.TemporaryDirectory()
        tmpvsz = os.path.join(tmpdir.name, 'tmp.vsz')
        try:
            interface.Save(tmpvsz)
            with open(tmpvsz, 'r') as f:
                script = f.read()
        except:
            pass
        os.remove(tmpvsz)
        tmpdir.cleanup()
        # Export image and embed script
        page = fields['pagenum'] - 1
        imgtype = fields['format']
        get_filepath = qt.QFileDialog.getSaveFileName
        if imgtype == "SVG":
            type_filter = "Images (*.svg *.SVG)"
            (filepath, fltr) = get_filepath(caption='Save', filter=type_filter)
            if filepath:
                if filepath[-4:] not in (".svg", ".SVG"):
                    filepath += ".svg"
                interface.Export(filepath, page=page)
                self.embed_script_to_svg(filepath, script)
        else:
            type_filter = "Images (*.png *.PNG)"
            (filepath, fltr) = get_filepath(caption='Save', filter=type_filter)
            if filepath: 
                if filepath[-4:] not in (".png", ".PNG"):
                    filepath += ".png" 
                interface.Export(filepath, page=page)
                self.embed_script_to_png(filepath, script)
    
    def embed_script_to_png(self, filepath, script):
        """
        The script data will be saved in tEXt chunk in the PNG file
        """
        def write_chunk(outfile, tag, data=b''):
            data = bytes(data)
            outfile.write(struct.pack("!I", len(data)))
            outfile.write(tag)
            outfile.write(data)
            checksum = zlib.crc32(tag)
            checksum = zlib.crc32(data, checksum)
            checksum &= 2 ** 32 - 1
            outfile.write(struct.pack("!I", checksum))

        def write_chunks(out, chunks):
            signature = struct.pack('8B', 137, 80, 78, 71, 13, 10, 26, 10)
            out.write(signature)
            for chunk in chunks:
                write_chunk(out, *chunk)
        
        reader = PNGReader(filename=filepath)
        chunks = reader.chunks()
        chunk_list = list(chunks)
        chunk_item = tuple([b'tEXt', bytes(script, 'utf-8')])
        chunk_list.insert(1, chunk_item)
        with open(filepath, 'wb') as f:
            write_chunks(f, chunk_list)

    def embed_script_to_svg(self, filepath, script):
        """
        The script data will be saved in <metadata> element in the SVG file
        """
        namespace = r'{https://veusz.github.io/}'
        tree = ET.parse(filepath)
        root = tree.getroot()
        metadata = ET.SubElement(root, 'metadata')
        vszdata = ET.SubElement(metadata, f'{namespace}veusz')
        vszdata.set("script", script)
        tree.write(filepath, encoding="UTF-8")


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


toolspluginregistry.append(SaveVSZImagePlugin)