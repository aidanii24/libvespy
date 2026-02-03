from concurrent.futures import ThreadPoolExecutor
from collections import namedtuple
import hashlib
import ctypes
import mmap
import sys
import os

from libvespy.utils import expand_and_write
from libvespy.structs import ScenarioHeader, ScenarioEntry


def extract(filename: str, out_dir: str = "", max_threads: int = 8):
    """
    Extract Scenario file.

    :param filename: Path to Scenario file.
    :param out_dir: Path to where the extracted files will be saved.
    :param max_threads: The maximum amount of threads that can be used for extraction.
    :return: None
    """
    if not out_dir:
        out_dir = f"{filename}.ext"
        os.makedirs(out_dir)

    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    File = namedtuple("File", ["filename", "data"])
    file_data: list[File] = []

    with open(filename, "rb") as f:
        mm = mmap.mmap(f.fileno(), 0, prot=mmap.PROT_READ)

        header = ScenarioHeader.from_buffer_copy(mm.read(ctypes.sizeof(ScenarioHeader)))
        _file_size_duplicate: int = int.from_bytes(mm.read(4), 'big')
        _padding: bytes = mm.read(4)

        for e in range(header.file_count):
            mm.seek(0x20 + e * 0x20)

            scenario_entry = ScenarioEntry.from_buffer_copy(mm.read(ctypes.sizeof(ScenarioEntry)))
            if not scenario_entry.file_size_compressed: continue

            mm.seek(scenario_entry.offset + header.file_offset)
            file_data.append(File(str(e), mm.read(scenario_entry.file_size_compressed)))

        mm.close()
        f.close()

    def _extract_file(fd: File):
        with open(os.path.join(out_dir, fd.filename), "w+b") as ef:
            ef.truncate(len(fd.data))
            em = mmap.mmap(ef.fileno(), 0, prot=mmap.PROT_WRITE)
            em.resize(len(fd.data))

            em.write(fd.data)

            em.flush()
            ef.close()

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        for file in file_data:
            executor.submit(_extract_file, file)

def pack(directory: str, output: str = ""):
    """
    Pack scenario files.

    :param directory: Path to directory of scenario files.
    :param output: Path to where the archived scenario file will be saved.
    :return: None
    """

    if not output:
        output = f"{directory}.pck"

    # Get number of files for the archive, including ones skipped from extraction
    # Add one to the max, as the files start count at index 0
    extracted: list[str] = os.listdir(directory)
    header = ScenarioHeader(file_count=max([int(c) for c in extracted]) + 1)

    with open(output, "w+b") as f:
        # Set initial size if needed
        if os.path.getsize(output) < header.file_offset: f.truncate(header.file_offset)

        mm = mmap.mmap(f.fileno(), 0, prot=mmap.PROT_WRITE)
        mm.seek(header.file_offset)

        # Write dummy entry as first entry
        expand_and_write(mm, bytes.fromhex('44554D4D59'))
        expand_and_write(mm, bytes(11))

        # Get Files metadata and write to archive
        previous_hash: str = ""
        entries: list[ScenarioEntry] = []
        for i in range(header.file_count):
            if not str(i) in extracted:
                entries.append(ScenarioEntry())
                previous_hash = ""
                continue

            with open(os.path.join(directory, str(i)), "rb") as cf:
                entry = ScenarioEntry()

                file_hash = hashlib.sha256(cf.read()).hexdigest()
                is_duplicate_from_previous: bool = file_hash == previous_hash
                previous_hash = file_hash

                # Check Validity
                # The file size check is for mocking an exception where a duplicate was still valid
                cm = mmap.mmap(cf.fileno(), 0, prot=mmap.PROT_READ)
                is_valid: bool = not is_duplicate_from_previous and cm.size() > 0x30

                entry.offset = mm.tell() - header.file_offset if is_valid else entries[-1].offset
                entry.file_size_compressed = cm.size()

                cm.seek(0x5)
                entry.file_size_uncompressed = int.from_bytes(cm.read(4), sys.byteorder)

                entries.append(entry)

                # No need to write contents if the file is an immediate duplicate of a previous file
                if is_valid:
                    cf.seek(0)
                    expand_and_write(mm, cf.read())

                    # Pad until aligned
                    if mm.size() % 0x10 != 0:
                        pad_length: int = 0x10 - mm.size() % 0x10
                        expand_and_write(mm, bytes(pad_length))

                cm.close()
                cf.close()

        # Write Header
        mm.seek(0)
        header.file_size = mm.size()
        mm.write(bytearray(header))
        mm.write(header.file_size.to_bytes(4, sys.byteorder))   # Don't forget the duplicate size entry
        mm.write(bytes(4))

        # Write File List/Metadata
        for i, e in enumerate(entries):
            mm.seek(0x20 + i * 0x20)
            mm.write(bytearray(e))

        mm.close()
        f.close()