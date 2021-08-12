# -*- coding: utf-8 -*-
from veusz.plugins import ToolsPlugin, toolspluginregistry

class SaveVSZPNGPlugin(ToolsPlugin):
    """Save as a re-editable PNG image with internal Veusz code."""
    menu = ('Save as Veusz-PNG',)
    name = 'Save as Veusz-PNG'
    description_short = 'Save as Veusz-PNG image.'
    description_full = 'Save as re-editable Veusz-PNG image.'
    
    def __init__(self):
        """Make list of fields."""
        from veusz.plugins import FieldInt
        self.fields = [ 
            FieldInt("pagenumber", default=1, descr="Page number of shown image"),
            ]
                    
    def apply(self, interface, fields):
        """
        pagenum: The pagenumber of Veusz document to be exported as PNG image
        The script data will be saved in tEXt chunk in the PNG file
        """
        import veusz.qtall as qt
        import os, tempfile
        import io
        import struct
        import warnings
        import zlib
        from array import array
        
        ##########################################################################
        # copied from "png.py" in the module pypng(https://github.com/drj11/pypng)
        # with deletion some unnecessary functions, classes, and modules,
        # in order to provide plugin as a one-file python file.
        # For main function, skip to "pypng module end".
        ##########################################################################

        signature = struct.pack('8B', 137, 80, 78, 71, 13, 10, 26, 10)

        class Error(Exception):
            def __str__(self):
                return self.__class__.__name__ + ': ' + ' '.join(self.args)

        class Reader:

            def __init__(self, _guess=None, filename=None, file=None, bytes=None):
                keywords_supplied = (
                    (_guess is not None) +
                    (filename is not None) +
                    (file is not None) +
                    (bytes is not None))
                if keywords_supplied != 1:
                    raise TypeError("Reader() takes exactly 1 argument")
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
                    raise Error("expecting filename, file or bytes array")

            def chunk(self, lenient=False):
                self.validate_signature()
                if not self.atchunk:
                    self.atchunk = self._chunk_len_type()
                if not self.atchunk:
                    raise Error("No more chunks.")
                length, type = self.atchunk
                self.atchunk = None

                data = self.file.read(length)
                if len(data) != length:
                    raise Error(
                        'Chunk %s too short for required %i octets.'
                        % (type, length))
                checksum = self.file.read(4)
                if len(checksum) != 4:
                    raise Error('Chunk %s too short for checksum.' % type)
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
                        raise Error(message)
                return type, data

            def chunks(self):
                while True:
                    t, v = self.chunk()
                    yield t, v
                    if t == b'IEND':
                        break

            def validate_signature(self):
                if self.signature:
                    return
                self.signature = self.file.read(8)
                if self.signature != signature:
                    raise Error("PNG file has invalid signature.")

            def _chunk_len_type(self):
                x = self.file.read(8)
                if not x:
                    return None
                if len(x) != 8:
                    raise Error(
                        'End of file whilst reading chunk length and type.')
                length, type = struct.unpack('!I4s', x)
                if length > 2 ** 31 - 1:
                    raise Error('Chunk %s is too large: %d.' % (type, length))
                type_bytes = set(bytearray(type))
                if not(type_bytes <= set(range(65, 91)) | set(range(97, 123))):
                    raise Error(
                        'Chunk %r has invalid Chunk Type.'
                        % list(type))
                return length, type

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
            out.write(signature)
            for chunk in chunks:
                write_chunk(out, *chunk)

        # get the Node corresponding to the widget path given
        pagenum = fields['pagenumber'] - 1
        
        # Save temporary .vsz document
        tmpdir = tempfile.TemporaryDirectory()
        tmpvsz = os.path.join(tmpdir.name, 'tmp.vsz')
        try:
            interface.Save(tmpvsz)
            with open(tmpvsz, 'r') as f:
                selfscript = f.read()
        except:
            pass
        os.remove(tmpvsz)
        tmpdir.cleanup()
        
        # Export normal PNG image
        getSaveFileName = qt.QFileDialog.getSaveFileName
        (filepath, fltr) = getSaveFileName(caption='Save', filter="Images (*.png)")
        if filepath[-4:] != ".png":
            filepath += ".png" 
        interface.Export(filepath, page=pagenum)

        # Add chunk to the PNG image
        # https://stackoverflow.com/questions/9036152/insert-a-text-chunk-into-a-png-image/23180764
        def generate_chunk_tuple(type_flag, content):
            return tuple([type_flag, content])

        def generate_text_chunk_tuple(str_info):
            type_flag = b'tEXt'
            return generate_chunk_tuple(type_flag, bytes(str_info, 'utf-8'))
        
        def insert_text_chunk(target, text, index=1):
            if index < 0:
                raise Exception('The index value {} less than 0!'.format(index))
            reader = Reader(filename=target)
            chunks = reader.chunks()
            chunk_list = list(chunks)
            chunk_item = generate_text_chunk_tuple(text)
            chunk_list.insert(index, chunk_item)
            with open(target, 'wb') as dst_file:
                write_chunks(dst_file, chunk_list)

        insert_text_chunk(filepath, selfscript)

toolspluginregistry.append(SaveVSZPNGPlugin)