from typing import Any, Literal, Sequence
import warnings
import ctypes
import mmap
import lzma
import zlib
import sys
import os

from libvespy.structs import TLZCHeader
from libvespy.utils import format_lzma_filters
from libvespy.res import Defaults

def decompress(filename: str, output: str, comp_type: Literal['deflate', 'zlib', 'lzma', 'auto'] = 'auto'):
    if not os.path.isfile(filename):
        print(f"{filename} was not found.")
        sys.exit(1)

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
                decompressed = decompress_deflate(data)
            else:
                decompressed = decompress_zlib(data)
        elif compression_type == 4:
            decompressed = lzma.decompress(f.read())
        else:
            raise AssertionError(f"[Error]\tUnsupported compression type: Type {compression_type}")

        f.close()

    with open(output, "wb") as f:
        f.write(decompressed)
        f.flush()
        f.close()

def compress(filename: str, output: str, comp_type: Literal['deflate', 'zlib', 'lzma'] = 'zlib', nice_len: int = 64):
    if not os.path.isfile(filename):
        print(f"{filename} was not found.")
        sys.exit(1)

    if not os.path.isdir(os.path.dirname(output)):
        os.makedirs(os.path.dirname(output))

    # <!> lib is only tested with zlib for now
    if comp_type in ('deflate', 'lzma'):
        warnings.warn("[WARNING]\tSupport for Type 2 deflate and Type 4 lzma are only experimental."
                      "Compression may fail or the compressed output may get corrupted.")

    file_size: int = os.path.getsize(filename)
    if file_size > 0xFFFFFFFF:
        raise AssertionError(f"[Error]\tCompression of files over 4GB is not supported.")

    compressed: bytes = bytes()
    with open(filename, "rb") as f:
        if comp_type in ('deflate', 'zlib'):
            # Type 2 (deflate/zlib)
            type_code: int = 0x0201
            if comp_type == 'deflate':
                header = TLZCHeader(type_code, file_size_compressed=file_size)
                content = compress_deflate(f.read())

                header.file_size_compressed = len(content)
                header_as_bytes = bytearray(header)
            else:
                content = compress_zlib(f.read())
                header_as_bytes = bytearray(TLZCHeader(type_code, ctypes.sizeof(TLZCHeader) + len(content), file_size))

            compressed = header_as_bytes + content
        elif comp_type == 'lzma':
            compressed = compress_as_lzma(f.read(), nice_len)
            pass
        else:
            raise AssertionError(f"Unsupported compression type: Type {comp_type}")

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

def decompress_zlib(data: bytes) -> bytes:
    try:
        zl: bytes = zlib.decompress(data)
        return zl
    except zlib.error:
        raise AssertionError("zlib Decompression failed.")

def decompress_deflate(data: bytes) -> bytes:
    zd = zlib.decompressobj(wbits=-zlib.MAX_WBITS)
    try:
        inflated = zd.decompress(data)
        inflated += zd.flush()
        return inflated
    except zlib.error:
        raise AssertionError("deflate Decompression failed.")

def compress_zlib(data: bytes) -> bytes:
    try:
        zl: bytes = zlib.compress(data, zlib.Z_BEST_COMPRESSION)
        return zl
    except zlib.error:
        raise AssertionError("zlib Compression failed.")

def compress_deflate(data: bytes) -> bytes:
    zd = zlib.compressobj(wbits=-zlib.MAX_WBITS)
    try:
        deflated = zd.compress(data)
        deflated += zd.flush()
        return deflated
    except zlib.error:
        raise AssertionError("deflate Compression failed.")

def compress_lzma(data: bytes, filters: Sequence[dict[str, Any]]) -> bytes:
    try:
        lz = lzma.LZMACompressor(filters=filters)
        compressed = lz.compress(data)
        compressed += lz.flush()
        return compressed
    except lzma.LZMAError:
        print(filters)
        raise AssertionError("lzma Compression failed.")
