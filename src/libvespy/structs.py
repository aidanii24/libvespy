from dataclasses import dataclass
from typing import Literal
import ctypes
import math
import mmap
import sys
import os

from libvespy.utils import read_null_terminated_string


class FPS4ContentData:
    has_start_pointers: bool = False
    has_sector_sizes: bool = False
    has_file_sizes: bool = False
    has_filenames: bool = False
    has_file_extensions: bool = False
    has_file_types: bool = False
    has_file_metadata: bool = False
    has_mask_0x080: bool = False
    has_mask_0x100: bool = False
    has_unknown_types: bool = False

    def __init__(self, value: int):
        self.has_start_pointers = value & 0x0001 == 0x0001
        self.has_sector_sizes = value & 0x0002 == 0x0002
        self.has_file_sizes = value & 0x0004 == 0x0004
        self.has_filenames = value & 0x0008 == 0x0008
        self.has_file_extensions = value & 0x0010 == 0x0010
        self.has_file_types = value & 0x0020 == 0x0020
        self.has_file_metadata = value & 0x0040 == 0x0040
        self.has_mask_080 = value & 0x0080 == 0x0080
        self.has_mask_0x100 = value & 0x0100 == 0x0100
        self.has_unknown_types = value & 0xFE00 != 0

    def get_entry_size(self) -> int:
        size: int = 0

        if self.has_start_pointers: size += 0x4
        if self.has_sector_sizes: size += 0x4
        if self.has_file_sizes: size += 0x4
        if self.has_filenames: size += 0x20
        if self.has_file_extensions: size += 0x8
        if self.has_file_types: size += 0x4
        if self.has_file_metadata: size += 0x4
        if self.has_mask_080: size += 0x4
        if self.has_mask_0x100: size += 0x4

        return size

    def get_metadata_offset(self) -> int:
        size: int = 0

        if not self.has_file_metadata: return size

        if self.has_start_pointers: size += 0x4
        if self.has_sector_sizes: size += 0x4
        if self.has_file_sizes: size += 0x4
        if self.has_filenames: size += 0x20
        if self.has_file_extensions: size += 0x8
        if self.has_file_types: size += 0x4

        return size

@dataclass
class FPS4FileData:
    index: int = None
    address: int = None
    sector_size: int = None
    file_size: int = None
    filename: str = None
    file_extension: str = None
    file_type: str = None
    metadata: list[tuple] = None
    unknown_0x080: int = None
    unknown_0x100: int = None

    skippable: bool = False

    def __init__(self, mm: mmap.mmap, index: int, data: FPS4ContentData,
                 byteorder: Literal['little', 'big'] = 'little', encoding: str = 'ascii'):
        self.index = index

        if data.has_start_pointers:
            self.address = int.from_bytes(mm.read(4), byteorder)

        if data.has_sector_sizes:
            self.sector_size = int.from_bytes(mm.read(4), byteorder)

        if data.has_file_sizes:
            self.file_size = int.from_bytes(mm.read(4), byteorder)

        if data.has_filenames:
            self.filename = mm.read(0x20).decode(encoding).rstrip('\x00')

        if data.has_file_extensions:
            self.file_extension = mm.read(0x8).decode(encoding)

        if data.has_file_types:
            self.file_type = mm.read(0x4).decode(encoding)

        if data.has_file_metadata:
            path_location: int = int.from_bytes(mm.read(4), byteorder)
            if path_location != 0:
                raw: str = read_null_terminated_string(mm, encoding, path_location)
                self.metadata: list[tuple] = []
                for md in [d for d in raw.split(' ') if d]:
                    if "=" in md:
                        pair: tuple = tuple(md.split('=', 1))
                        self.metadata.append(pair)
                    else:
                        self.metadata.append(tuple([None, md]))

        if data.has_mask_0x080:
            self.unknown_0x080 = int.from_bytes(mm.read(4), byteorder)

        if data.has_mask_0x100:
            self.unknown_0x100 = int.from_bytes(mm.read(4), byteorder)

        self.skippable = self.address == 0xFFFFFFFF or (self.unknown_0x080 and self.unknown_0x080 > 0)

    def estimate_file_size(self, files: list['FPS4FileData']) -> int | None:
        if self.file_size:
            return self.file_size

        if self.sector_size:
            return self.sector_size

        if self.address and files:
            for f in range(self.index + 1, len(files)):
                if not files[f].skippable:
                    return files[f].address - self.address

        return None

    def estimate_file_path(self, ignore_metadata: bool = False) -> tuple[str | None, str]:
        path: str | None = None
        if not ignore_metadata and self.metadata:
            for data in self.metadata:
                if data[0] is None:
                    path = data[1]
                    break

        if self.filename:
            return path, self.filename

        if not ignore_metadata and self.metadata:
            for data in self.metadata:
                if data[0] == "name" and data[1]:
                    return path, data[1]

        index: str = f"{self.index:04}"
        index_with_type: str = index if not self.file_type else index + "." + self.file_type
        if not path:
            return path, index_with_type

        if "/" not in path:
            return None, path + "." + index_with_type

        return os.path.dirname(path), os.path.basename(path) + "." + index_with_type

class FPS4LittleEndian(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("magic", ctypes.c_char * 4),
        ("file_entries", ctypes.c_uint32),
        ("header_size", ctypes.c_uint32),
        ("file_start", ctypes.c_uint32),
        ("entry_size", ctypes.c_uint16),
        ("content_bitmask", ctypes.c_uint16),
        ("unknown0", ctypes.c_uint32),
        ("archive_name_address", ctypes.c_uint32),
    ]

class FPS4BigEndian(ctypes.BigEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("magic", ctypes.c_char * 4),
        ("file_entries", ctypes.c_uint32),
        ("header_size", ctypes.c_uint32),
        ("file_start", ctypes.c_uint32),
        ("entry_size", ctypes.c_uint16),
        ("content_bitmask", ctypes.c_uint16),
        ("unknown0", ctypes.c_uint32),
        ("archive_name_address", ctypes.c_uint32),
    ]

class FPS4(ctypes.Union):
    _pack_ = 1
    _fields_ = [
        ("little", FPS4LittleEndian),
        ("big", FPS4BigEndian),
    ]

    file_size: int = -1
    byteorder: Literal['little', 'big']
    data: FPS4LittleEndian | FPS4BigEndian
    content_data: FPS4ContentData
    archive_name: str | None = None
    file_location_multiplier: int
    should_guess_file_size: bool = False

    files: list[FPS4FileData] = []

    def set_byteorder(self, byteorder: Literal['little', 'big']):
        self.byteorder = byteorder
        self.data = self.little if byteorder == 'little' else self.big

        self.content_data = FPS4ContentData(self.data.content_bitmask)

        self.files = []

    def finalize(self):
        self.file_location_multiplier = self.calculate_file_multiplier()
        self.should_guess_file_size = (self.content_data.has_file_sizes and not self.content_data.has_sector_sizes
                                       and self.is_linear())

    def is_linear(self) -> bool:
        if self.content_data.has_start_pointers:
            last_file_position: int = self.files[0].address
            for file in self.files:
                if file.skippable:
                    continue

                if file.address <= last_file_position:
                    return False

                last_file_position = file.address

            return True
        return False

    def calculate_file_multiplier(self) -> int:
        if self.content_data.has_start_pointers:
            smallest_file_position: int = sys.maxsize
            for file in self.files:
                if not file.skippable and file.address >= 0:
                    smallest_file_position = min(smallest_file_position, file.address)

            if smallest_file_position == sys.maxsize or smallest_file_position == self.data.file_start:
                return 1

            if self.data.file_start % smallest_file_position == 0:
                return math.ceil(self.data.file_start / smallest_file_position)

        return 1

    def generate_base_manifest(self) -> dict:
        manifest = {
            'content_bitmask': self.data.content_bitmask,
            'unknown0': self.data.unknown0,
            'file_location_multiplier': self.file_location_multiplier,
            'byteorder': self.byteorder,
            'file_terminator_address': (self.files[-1].address
                                        if len(self.files) > 0 and self.files[-1].address != self.file_size
                                        else -1),
            'files': []
        }

        if self.archive_name is not None:
            manifest["comment"] = self.archive_name

        return manifest

    @staticmethod
    def from_manifest(manifest_data: dict) -> 'FPS4':
        fps4: FPS4 = FPS4()

        fps4.set_byteorder(manifest_data['byteorder'])
        fps4.data.content_bitmask = manifest_data['content_bitmask']
        fps4.content_data = FPS4ContentData(manifest_data['content_bitmask'])

        fps4.data.magic = "FPS4".encode("ascii")
        fps4.data.file_entries = len(manifest_data['files'])
        fps4.data.header_size = ctypes.sizeof(fps4.data)
        fps4.data.unknown0 = manifest_data['unknown0']

        fps4.archive_name = manifest_data.get('archive_name', None)
        fps4.file_location_multiplier = manifest_data['file_location_multiplier']

        fps4.data.entry_size = fps4.content_data.get_entry_size()

        return fps4


    def validate(self):
        assert self.magic == b"FPS4", "Loaded file is not a valid FPS4 File!"
