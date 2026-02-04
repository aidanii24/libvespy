from typing import Any, Literal, Sequence
import warnings
import ctypes
import struct
import mmap
import lzma
import zlib
import os

from libvespy.structs import TLZCHeader
from libvespy.utils import format_lzma_filters
from libvespy.res import Defaults

def decompress(filename: str, output: str = "",
               comp_type: Literal['deflate', 'zlib', 'lzma', 'auto'] = 'auto'):
    """
    Decompress a TLZC file.

    :param filename: Path to TLZC file to decompress.
    :param output: Path to where the decompressed file will be written.
    :param comp_type: Compression type.
    :return: None
    """

    if not output:
        output = f"{filename}.dec"

    if not os.path.isdir(os.path.dirname(output)):
        os.makedirs(os.path.dirname(output))

    with open(filename, "rb") as f:
        mm = mmap.mmap(f.fileno(), 0, prot=mmap.PROT_READ)

        header = TLZCHeader.from_buffer_copy(mm.read(ctypes.sizeof(TLZCHeader)))
        header.validate(mm.size())

        mm.close()

        decompressed: bytes = bytes()
        compression_type: int = 2
        compression_subtype = comp_type
        if comp_type == 'auto':
            compression_type = (header.type >> 8) & 0xff
            if compression_type == 2:
                compression_subtype = 'zlib'
        elif comp_type == 'lzma':
            compression_type = 4

        # <!> lib is only tested with zlib for now
        if comp_type == 'deflate' or compression_type == 4:
            warnings.warn("[WARNING]\tSupport for Type 2 deflate and Type 4 lzma are only experimental."
                          "Uncompressed output may get corrupted.")

        if compression_type == 2:
            data: bytes = f.read()[0x18:]
            if compression_subtype == 'deflate':
                zd = zlib.decompressobj(wbits=-zlib.MAX_WBITS)
                try:
                    decompressed = zd.decompress(data)
                    decompressed += zd.flush()
                except zlib.error:
                    raise TLZCError("[ERROR]\tdeflate Decompression failed.")
            else:
                try:
                    decompressed = zlib.decompress(data)
                except zlib.error:
                    raise TLZCError("[ERROR]\tzlib Decompression failed.")
        elif compression_type == 4:
            # Get LZMA Filters Data
            f.seek(0x14)
            mask, size = struct.unpack("<BI", f.read(5))
            filters = [{
                "id": lzma.FILTER_LZMA1,
                "dict_size": size,
                "lc": mask % 9,
                "lp": (mask // 9) % 5,
                "pb": (mask // 9) // 5,
                "mode": lzma.MODE_NORMAL
            }]

            # Get Stream Data
            stream_count: int = (header.file_size_compressed + 0xffff) >> 0x10
            stream_sizes = list(struct.unpack(f"<{stream_count}H", f.read(2 * stream_count)))

            # Decompress
            decompressed: bytes = bytes()
            for s in stream_sizes:
                stream_len: int = min(header.file_size_compressed - len(decompressed), 0x10000)
                if s:
                    lz = lzma.LZMADecompressor(lzma.FORMAT_RAW, filters=filters)
                    try:
                        decompressed += lz.decompress(f.read(s), max_length=stream_len)
                    except lzma.LZMAError:
                        raise TLZCError("[ERROR]\tLZMA decompression failed")
                else:
                    decompressed += f.read(stream_len)

        else:
            raise TLZCError(f"[ERROR]\tUnsupported compression type: Type {compression_type}")

        f.close()

    with open(output, "wb") as f:
        f.write(decompressed)
        f.flush()
        f.close()

def compress(filename: str, output: str = "",
             comp_type: Literal['deflate', 'zlib', 'lzma'] = 'zlib', nice_len: int = 64):
    """
    Compress a file into TLZC format.

    :param filename: Path to file to compress.
    :param output: Path to where the compressed file will be written.
    :param comp_type: Compression type.
    :param nice_len: (LZMA Only) What should be considered a “nice length” for a match. This should be 273 or less.
    :return: None
    """

    if not output:
        base_file, extension = os.path.splitext(filename)
        if extension == '.dec':
            output = f"{base_file}.cmp"
        else:
            output = f"{filename}.cmp"

    if not os.path.isdir(os.path.dirname(output)):
        os.makedirs(os.path.dirname(output))

    # <!> lib is only tested with zlib for now
    if comp_type in ('deflate', 'lzma'):
        warnings.warn("[WARNING]\tSupport for Type 2 deflate and Type 4 lzma are only experimental."
                      "Compression may fail or the compressed output may get corrupted.")

    file_size: int = os.path.getsize(filename)
    if file_size > 0xFFFFFFFF:
        raise TLZCError(f"[ERROR]\tCompression of files over 4GB is not supported.")

    compressed: bytes = bytes()
    with open(filename, "rb") as f:
        if comp_type in ('deflate', 'zlib'):
            # Type 2 (deflate/zlib)
            type_code: int = 0x0201
            if comp_type == 'deflate':
                header = TLZCHeader(type_code, file_size_compressed=file_size)

                zd = zlib.compressobj(wbits=-zlib.MAX_WBITS)
                try:
                    content = zd.compress(f.read())
                    content += zd.flush()
                except zlib.error:
                    raise TLZCError("[ERROR]\tdeflate Compression failed.")

                header.file_size_compressed = len(content)
            else:
                try:
                    content = zlib.compress(f.read(), zlib.Z_BEST_COMPRESSION)
                except zlib.error:
                    raise TLZCError("[ERROR]\tzlib Compression failed.")

                header = TLZCHeader(type_code, ctypes.sizeof(TLZCHeader) + len(content), file_size)

            compressed = bytearray(header) + content
        elif comp_type == 'lzma':
            compressed = compress_as_lzma(f.read(), nice_len)
            pass
        else:
            raise TLZCError(f"[ERROR]\tUnsupported compression type: Type {comp_type}")

        f.close()

    with open(output, "wb") as f:
        f.write(compressed)
        f.flush()
        f.close()

def compress_as_lzma(data: bytes, nice_len: int = 64) -> bytes:
    filters: Sequence[dict[str, Any]] = Defaults.LZMA_FILTERS
    filters[0]['nice_len'] = nice_len

    header = TLZCHeader(0x0401, file_size_uncompressed=len(data))
    filter_props: bytes = format_lzma_filters(filters)
    stream_count: int = (len(data) + 0xffff) >> 16

    last_chunk_size: int = len(data)
    data_sizes: list[int] = []
    content: bytes = bytes()
    for i in range(stream_count):
        pre_size: int = len(content)

        chunk_size: int = min(last_chunk_size, 0x10000)
        content += compress_lzma(data[:chunk_size], Defaults.LZMA_FILTERS)

        data_size: int = len(content) - pre_size
        if data_size >= 0x10000:
            data_size = 0

        last_chunk_size -= 0x10000
        data_sizes.append(data_size)

    # Remove lzma header
    content = content[0x1E:]

    sizes_as_bytes: bytes = bytes().join([s.to_bytes(2) for s in data_sizes])
    header.file_size_compressed = ctypes.sizeof(header) + len(filter_props) + len(sizes_as_bytes) + len(content)

    header_as_bytes = bytearray(header)
    header_as_bytes += filter_props
    header_as_bytes += sizes_as_bytes

    return header_as_bytes + content

def compress_lzma(data: bytes, filters: Sequence[dict[str, Any]]) -> bytes:
    try:
        lz = lzma.LZMACompressor(filters=filters)
        compressed = lz.compress(data)
        compressed += lz.flush()
        return compressed
    except lzma.LZMAError:
        raise TLZCError("[ERROR]\tlzma Compression failed.")

class TLZCError(Exception):
    """"""