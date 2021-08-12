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
        
        ##########################################################################
        # copied from "png.py" in the module pypng(https://github.com/drj11/pypng)
        # with deletion some unnecessary functions, classes, and modules,
        # in order to provide plugin as a one-file python file.
        # For main function, skip to "pypng module end".
        ##########################################################################
        import collections
        import io
        import itertools
        import math
        import operator
        import re
        import struct
        import warnings
        import zlib
        from array import array

        __all__ = ['Image', 'Reader', 'Writer', 'write_chunks', 'from_array']

        # The PNG signature.
        # http://www.w3.org/TR/PNG/#5PNG-file-signature
        signature = struct.pack('8B', 137, 80, 78, 71, 13, 10, 26, 10)

        # The xstart, ystart, xstep, ystep for the Adam7 interlace passes.
        adam7 = ((0, 0, 8, 8),
                (4, 0, 8, 8),
                (0, 4, 4, 8),
                (2, 0, 4, 4),
                (0, 2, 2, 4),
                (1, 0, 2, 2),
                (0, 1, 1, 2))

        def adam7_generate(width, height):
            for xstart, ystart, xstep, ystep in adam7:
                if xstart >= width:
                    continue
                yield ((xstart, y, xstep) for y in range(ystart, height, ystep))

        Resolution = collections.namedtuple('_Resolution', 'x y unit_is_meter')

        def group(s, n):
            return list(zip(* [iter(s)] * n))

        def isarray(x):
            return isinstance(x, array)

        def check_palette(palette):
            # None is the default and is allowed.
            if palette is None:
                return None

            p = list(palette)
            if not (0 < len(p) <= 256):
                raise ProtocolError(
                    "a palette must have between 1 and 256 entries,"
                    " see https://www.w3.org/TR/PNG/#11PLTE")
            seen_triple = False
            for i, t in enumerate(p):
                if len(t) not in (3, 4):
                    raise ProtocolError(
                        "palette entry %d: entries must be 3- or 4-tuples." % i)
                if len(t) == 3:
                    seen_triple = True
                if seen_triple and len(t) == 4:
                    raise ProtocolError(
                        "palette entry %d: all 4-tuples must precede all 3-tuples" % i)
                for x in t:
                    if int(x) != x or not(0 <= x <= 255):
                        raise ProtocolError(
                            "palette entry %d: "
                            "values must be integer: 0 <= x <= 255" % i)
            return p

        def check_sizes(size, width, height):
            if not size:
                return width, height

            if len(size) != 2:
                raise ProtocolError(
                    "size argument should be a pair (width, height)")
            if width is not None and width != size[0]:
                raise ProtocolError(
                    "size[0] (%r) and width (%r) should match when both are used."
                    % (size[0], width))
            if height is not None and height != size[1]:
                raise ProtocolError(
                    "size[1] (%r) and height (%r) should match when both are used."
                    % (size[1], height))
            return size

        def check_color(c, greyscale, which):
            if c is None:
                return c
            if greyscale:
                try:
                    len(c)
                except TypeError:
                    c = (c,)
                if len(c) != 1:
                    raise ProtocolError("%s for greyscale must be 1-tuple" % which)
                if not is_natural(c[0]):
                    raise ProtocolError(
                        "%s colour for greyscale must be integer" % which)
            else:
                if not (len(c) == 3 and
                        is_natural(c[0]) and
                        is_natural(c[1]) and
                        is_natural(c[2])):
                    raise ProtocolError(
                        "%s colour must be a triple of integers" % which)
            return c


        class Error(Exception):
            def __str__(self):
                return self.__class__.__name__ + ': ' + ' '.join(self.args)


        class FormatError(Error):
            """
            Problem with input file format.
            In other words, PNG file does not conform to
            the specification in some way and is invalid.
            """


        class ProtocolError(Error):
            """
            Problem with the way the programming interface has been used,
            or the data presented to it.
            """


        class ChunkError(FormatError):
            pass


        class Default:
            """The default for the greyscale paramter."""


        def write_chunk(outfile, tag, data=b''):
            """
            Write a PNG chunk to the output file, including length and
            checksum.
            """

            data = bytes(data)
            # http://www.w3.org/TR/PNG/#5Chunk-layout
            outfile.write(struct.pack("!I", len(data)))
            outfile.write(tag)
            outfile.write(data)
            checksum = zlib.crc32(tag)
            checksum = zlib.crc32(data, checksum)
            checksum &= 2 ** 32 - 1
            outfile.write(struct.pack("!I", checksum))


        def write_chunks(out, chunks):
            """Create a PNG file by writing out the chunks."""

            out.write(signature)
            for chunk in chunks:
                write_chunk(out, *chunk)

        # Regex for decoding mode string
        RegexModeDecode = re.compile("(LA?|RGBA?);?([0-9]*)", flags=re.IGNORECASE)

        class Reader:
            """
            Pure Python PNG decoder in pure Python.
            """

            def __init__(self, _guess=None, filename=None, file=None, bytes=None):
                """
                The constructor expects exactly one keyword argument.
                If you supply a positional argument instead,
                it will guess the input type.
                Choose from the following keyword arguments:

                filename
                Name of input file (a PNG file).
                file
                A file-like object (object with a read() method).
                bytes
                ``bytes`` or ``bytearray`` with PNG data.

                """
                keywords_supplied = (
                    (_guess is not None) +
                    (filename is not None) +
                    (file is not None) +
                    (bytes is not None))
                if keywords_supplied != 1:
                    raise TypeError("Reader() takes exactly 1 argument")

                # Will be the first 8 bytes, later on.  See validate_signature.
                self.signature = None
                self.transparent = None
                # A pair of (len,type) if a chunk has been read but its data and
                # checksum have not (in other words the file position is just
                # past the 4 bytes that specify the chunk type).
                # See preamble method for how this is used.
                self.atchunk = None

                if _guess is not None:
                    if isarray(_guess):
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
                    raise ProtocolError("expecting filename, file or bytes array")

            def chunk(self, lenient=False):
                self.validate_signature()
                if not self.atchunk:
                    self.atchunk = self._chunk_len_type()
                if not self.atchunk:
                    raise ChunkError("No more chunks.")
                length, type = self.atchunk
                self.atchunk = None

                data = self.file.read(length)
                if len(data) != length:
                    raise ChunkError(
                        'Chunk %s too short for required %i octets.'
                        % (type, length))
                checksum = self.file.read(4)
                if len(checksum) != 4:
                    raise ChunkError('Chunk %s too short for checksum.' % type)
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
                        raise ChunkError(message)
                return type, data

            def chunks(self):
                while True:
                    t, v = self.chunk()
                    yield t, v
                    if t == b'IEND':
                        break

            def undo_filter(self, filter_type, scanline, previous):
                result = scanline
                if filter_type == 0:
                    return result

                if filter_type not in (1, 2, 3, 4):
                    raise FormatError(
                        'Invalid PNG Filter Type.  '
                        'See http://www.w3.org/TR/2003/REC-PNG-20031110/#9Filters .')
                fu = max(1, self.psize)
                if not previous:
                    previous = bytearray([0] * len(scanline))
                fn = (None,
                    undo_filter_sub,
                    undo_filter_up,
                    undo_filter_average,
                    undo_filter_paeth)[filter_type]
                fn(fu, scanline, previous, result)
                return result

            def _deinterlace(self, raw):
                vpr = self.width * self.planes
                vpi = vpr * self.height
                if self.bitdepth > 8:
                    a = array('H', [0] * vpi)
                else:
                    a = bytearray([0] * vpi)
                source_offset = 0
                for lines in adam7_generate(self.width, self.height):
                    recon = None
                    for x, y, xstep in lines:
                        # Pixels per row (reduced pass image)
                        ppr = int(math.ceil((self.width - x) / float(xstep)))
                        # Row size in bytes for this pass.
                        row_size = int(math.ceil(self.psize * ppr))

                        filter_type = raw[source_offset]
                        source_offset += 1
                        scanline = raw[source_offset: source_offset + row_size]
                        source_offset += row_size
                        recon = self.undo_filter(filter_type, scanline, recon)
                        # Convert so that there is one element per pixel value
                        flat = self._bytes_to_values(recon, width=ppr)
                        if xstep == 1:
                            assert x == 0
                            offset = y * vpr
                            a[offset: offset + vpr] = flat
                        else:
                            offset = y * vpr + x * self.planes
                            end_offset = (y + 1) * vpr
                            skip = self.planes * xstep
                            for i in range(self.planes):
                                a[offset + i: end_offset: skip] = \
                                    flat[i:: self.planes]
                return a

            def _iter_bytes_to_values(self, byte_rows):
                for row in byte_rows:
                    yield self._bytes_to_values(row)

            def _bytes_to_values(self, bs, width=None):
                if self.bitdepth == 8:
                    return bytearray(bs)
                if self.bitdepth == 16:
                    return array('H',
                                struct.unpack('!%dH' % (len(bs) // 2), bs))
                assert self.bitdepth < 8
                if width is None:
                    width = self.width
                spb = 8 // self.bitdepth
                out = bytearray()
                mask = 2**self.bitdepth - 1
                shifts = [self.bitdepth * i
                        for i in reversed(list(range(spb)))]
                for o in bs:
                    out.extend([mask & (o >> i) for i in shifts])
                return out[:width]

            def _iter_straight_packed(self, byte_blocks):
                rb = self.row_bytes
                a = bytearray()
                recon = None
                for some_bytes in byte_blocks:
                    a.extend(some_bytes)
                    while len(a) >= rb + 1:
                        filter_type = a[0]
                        scanline = a[1: rb + 1]
                        del a[: rb + 1]
                        recon = self.undo_filter(filter_type, scanline, recon)
                        yield recon
                if len(a) != 0:
                    raise FormatError('Wrong size for decompressed IDAT chunk.')
                assert len(a) == 0

            def validate_signature(self):
                """
                If signature (header) has not been read then read and
                validate it; otherwise do nothing.
                """

                if self.signature:
                    return
                self.signature = self.file.read(8)
                if self.signature != signature:
                    raise FormatError("PNG file has invalid signature.")

            def preamble(self, lenient=False):
                """
                Extract the image metadata by reading
                the initial part of the PNG file up to
                the start of the ``IDAT`` chunk.
                All the chunks that precede the ``IDAT`` chunk are
                read and either processed for metadata or discarded.

                If the optional `lenient` argument evaluates to `True`,
                checksum failures will raise warnings rather than exceptions.
                """

                self.validate_signature()

                while True:
                    if not self.atchunk:
                        self.atchunk = self._chunk_len_type()
                        if self.atchunk is None:
                            raise FormatError('This PNG file has no IDAT chunks.')
                    if self.atchunk[1] == b'IDAT':
                        return
                    self.process_chunk(lenient=lenient)

            def _chunk_len_type(self):
                """
                Reads just enough of the input to
                determine the next chunk's length and type;
                return a (*length*, *type*) pair where *type* is a byte sequence.
                If there are no more chunks, ``None`` is returned.
                """

                x = self.file.read(8)
                if not x:
                    return None
                if len(x) != 8:
                    raise FormatError(
                        'End of file whilst reading chunk length and type.')
                length, type = struct.unpack('!I4s', x)
                if length > 2 ** 31 - 1:
                    raise FormatError('Chunk %s is too large: %d.' % (type, length))
                # Check that all bytes are in valid ASCII range.
                # https://www.w3.org/TR/2003/REC-PNG-20031110/#5Chunk-layout
                type_bytes = set(bytearray(type))
                if not(type_bytes <= set(range(65, 91)) | set(range(97, 123))):
                    raise FormatError(
                        'Chunk %r has invalid Chunk Type.'
                        % list(type))
                return length, type

            def process_chunk(self, lenient=False):
                type, data = self.chunk(lenient=lenient)
                method = '_process_' + type.decode('ascii')
                m = getattr(self, method, None)
                if m:
                    m(data)

            def read(self, lenient=False):
                """
                Read the PNG file and decode it.
                Returns (`width`, `height`, `rows`, `info`).

                May use excessive memory.

                `rows` is a sequence of rows;
                each row is a sequence of values.

                If the optional `lenient` argument evaluates to True,
                checksum failures will raise warnings rather than exceptions.
                """

                def iteridat():
                    """Iterator that yields all the ``IDAT`` chunks as strings."""
                    while True:
                        type, data = self.chunk(lenient=lenient)
                        if type == b'IEND':
                            # http://www.w3.org/TR/PNG/#11IEND
                            break
                        if type != b'IDAT':
                            continue
                        # type == b'IDAT'
                        # http://www.w3.org/TR/PNG/#11IDAT
                        if self.colormap and not self.plte:
                            warnings.warn("PLTE chunk is required before IDAT chunk")
                        yield data

                self.preamble(lenient=lenient)
                raw = decompress(iteridat())
                if self.interlace:
                    def rows_from_interlace():
                        """Yield each row from an interlaced PNG."""
                        # It's important that this iterator doesn't read
                        # IDAT chunks until it yields the first row.
                        bs = bytearray(itertools.chain(*raw))
                        arraycode = 'BH'[self.bitdepth > 8]
                        # Like :meth:`group` but
                        # producing an array.array object for each row.
                        values = self._deinterlace(bs)
                        vpr = self.width * self.planes
                        for i in range(0, len(values), vpr):
                            row = array(arraycode, values[i:i+vpr])
                            yield row
                    rows = rows_from_interlace()
                else:
                    rows = self._iter_bytes_to_values(self._iter_straight_packed(raw))
                info = dict()
                for attr in 'greyscale alpha planes bitdepth interlace'.split():
                    info[attr] = getattr(self, attr)
                info['size'] = (self.width, self.height)
                for attr in 'gamma transparent background'.split():
                    a = getattr(self, attr, None)
                    if a is not None:
                        info[attr] = a
                if getattr(self, 'x_pixels_per_unit', None):
                    info['physical'] = Resolution(self.x_pixels_per_unit,
                                                self.y_pixels_per_unit,
                                                self.unit_is_meter)
                if self.plte:
                    info['palette'] = self.palette()
                return self.width, self.height, rows, info

            def read_flat(self):
                x, y, pixel, info = self.read()
                arraycode = 'BH'[info['bitdepth'] > 8]
                pixel = array(arraycode, itertools.chain(*pixel))
                return x, y, pixel, info

            def palette(self, alpha='natural'):
                if not self.plte:
                    raise FormatError(
                        "Required PLTE chunk is missing in colour type 3 image.")
                plte = group(array('B', self.plte), 3)
                if self.trns or alpha == 'force':
                    trns = array('B', self.trns or [])
                    trns.extend([255] * (len(plte) - len(trns)))
                    plte = list(map(operator.add, plte, group(trns, 1)))
                return plte

        def decompress(data_blocks):
            d = zlib.decompressobj()
            for data in data_blocks:
                yield bytearray(d.decompress(data))
            yield bytearray(d.flush())

        def check_bitdepth_colortype(bitdepth, colortype):
            if bitdepth not in (1, 2, 4, 8, 16):
                raise FormatError("invalid bit depth %d" % bitdepth)
            if colortype not in (0, 2, 3, 4, 6):
                raise FormatError("invalid colour type %d" % colortype)
            if colortype & 1 and bitdepth > 8:
                raise FormatError(
                    "Indexed images (colour type %d) cannot"
                    " have bitdepth > 8 (bit depth %d)."
                    " See http://www.w3.org/TR/2003/REC-PNG-20031110/#table111 ."
                    % (bitdepth, colortype))
            if bitdepth < 8 and colortype not in (0, 3):
                raise FormatError(
                    "Illegal combination of bit depth (%d)"
                    " and colour type (%d)."
                    " See http://www.w3.org/TR/2003/REC-PNG-20031110/#table111 ."
                    % (bitdepth, colortype))

        def is_natural(x):
            """A non-negative integer."""
            try:
                is_integer = int(x) == x
            except (TypeError, ValueError):
                return False
            return is_integer and x >= 0

        def undo_filter_sub(filter_unit, scanline, previous, result):
            """Undo sub filter."""
            ai = 0
            for i in range(filter_unit, len(result)):
                x = scanline[i]
                a = result[ai]
                result[i] = (x + a) & 0xff
                ai += 1

        def undo_filter_up(filter_unit, scanline, previous, result):
            """Undo up filter."""

            for i in range(len(result)):
                x = scanline[i]
                b = previous[i]
                result[i] = (x + b) & 0xff

        def undo_filter_average(filter_unit, scanline, previous, result):
            """Undo up filter."""

            ai = -filter_unit
            for i in range(len(result)):
                x = scanline[i]
                if ai < 0:
                    a = 0
                else:
                    a = result[ai]
                b = previous[i]
                result[i] = (x + ((a + b) >> 1)) & 0xff
                ai += 1

        def undo_filter_paeth(filter_unit, scanline, previous, result):
            """Undo Paeth filter."""

            # Also used for ci.
            ai = -filter_unit
            for i in range(len(result)):
                x = scanline[i]
                if ai < 0:
                    a = c = 0
                else:
                    a = result[ai]
                    c = previous[ai]
                b = previous[i]
                p = a + b - c
                pa = abs(p - a)
                pb = abs(p - b)
                pc = abs(p - c)
                if pa <= pb and pa <= pc:
                    pr = a
                elif pb <= pc:
                    pr = b
                else:
                    pr = c
                result[i] = (x + pr) & 0xff
                ai += 1

        ##########################################################################
        # pypng module end
        ##########################################################################
        
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
        # The three functions below were originally written by cfh008
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