from typing import Literal
import ctypes
import json
import mmap
import sys
import os

from libvespy.utils import read_null_terminated_string, get_alignment_from_lowest_unset_bit
from libvespy.structs import FPS4FileData, FPS4


def extract(filename: str, out_dir: str, manifest_dir: str = "",
            absolute_paths: bool = False, ignore_metadata: bool = False):
    if not os.path.isfile(filename):
        print(f"{filename} was not found.")
        sys.exit(1)

    byteorder: Literal['little', 'big'] = sys.byteorder

    fps4: FPS4
    manifest: dict = {}

    with open(filename, "rb") as f:
        mm = mmap.mmap(f.fileno(), 0, prot=mmap.PROT_READ)

        mm.seek(0)
        # Check Magic Number
        if mm.read(4) != 'FPS4'.encode('ascii'):
            raise AssertionError("Provided file is not in FPS4 format.")

        # Use the correct byteorder version of the Header structure
        mm.seek(0)
        fps4 = FPS4.from_buffer_copy(mm.read(ctypes.sizeof(FPS4)))
        if byteorder == 'little' and fps4.little.header_size > 0xFFFF:
            fps4.set_byteorder('big')
        elif byteorder == 'big' and fps4.big.header_size > 0xFFFF:
            fps4.set_byteorder('little')
        else:
            fps4.set_byteorder(byteorder)

        # Get other data
        mm.seek(fps4.data.archive_name_address)
        fps4.archive_name = read_null_terminated_string(mm, 'shift-jis', reset_position=False)
        fps4.file_size = mm.size()

        # Get Files in Archive
        for e in range(fps4.data.file_entries):
            mm.seek(fps4.data.header_size + (e * fps4.data.entry_size))
            fps4.files.append(FPS4FileData(mm, e, fps4.content_data, fps4.byteorder))

        # Finalize remaining data
        fps4.finalize()

        # Prepare Extraction
        manifest = fps4.generate_base_manifest()

        first_file_position: int = 0xffffffffffffffff
        estimated_alignment: int = 0xffffffffffffffff
        is_sector_and_file_size_same: bool = fps4.content_data.has_file_sizes and fps4.content_data.has_sector_sizes
        has_valid_file: bool = False

        # Extract
        for file in fps4.files:
            if file.skippable: continue

            file_size: int | None = file.estimate_file_size(fps4.files)
            assert file.address, "FPS4 Extraction Error: File does not contain file entry start pointer."
            assert file_size is not None, "FPS4 Extraction Error: File does not contain file size data."

            has_valid_file = True
            file_manifest: dict = {k: v for k, v in file.__dict__.items() if v is not None}

            file_address: int = file.address * fps4.file_location_multiplier
            first_file_position = min(first_file_position, file_address)
            estimated_alignment = estimated_alignment & ~file_address
            path, filename = file.estimate_file_path(ignore_metadata)

            base_out_dir: str = out_dir

            if path is not None:
                base_out_dir = os.path.join(base_out_dir, path)
                if not os.path.isdir(base_out_dir):
                    os.makedirs(base_out_dir)
            else:
                base_out_dir = filename

            full_out_dir: str = os.path.join(out_dir, base_out_dir)
            file_manifest['path_on_disk'] = os.path.abspath(full_out_dir) if absolute_paths else full_out_dir

            mm.seek(file_address)
            contents: bytes = mm.read(file_size)

            if not os.path.isdir(os.path.dirname(full_out_dir)):
                os.makedirs(os.path.dirname(full_out_dir))

            with open(full_out_dir, "w+b") as af:
                af.truncate(len(contents))
                mf = mmap.mmap(af.fileno(), 0, prot=mmap.PROT_WRITE)

                mf.resize(len(contents))
                mf.write(contents)

                mf.flush()
                mf.close()

            manifest.setdefault('files', []).append(file_manifest)

        mm.close()

    # More Metadata
    alignment: int = get_alignment_from_lowest_unset_bit(estimated_alignment)
    manifest['alignment'] = alignment

    if first_file_position != 0xffffffffffffffff:
        first_file_alignment: int = get_alignment_from_lowest_unset_bit(~first_file_position)
        if first_file_alignment > alignment:
            manifest['first_file_alignment'] = first_file_alignment

    manifest['set_sector_size_as_file_size'] = has_valid_file and is_sector_and_file_size_same

    # Generate Manifest
    if manifest_dir:
        if not os.path.isdir(os.path.dirname(manifest_dir)):
            os.makedirs(os.path.dirname(manifest_dir))
        with open(manifest_dir, "w") as f:
            json.dump(manifest, f, indent=4)

            f.flush()
            f.close()


def pack(archive_dir: str = "", manifest: str = ""):
    if not archive_dir and not manifest:
        print("Provide either an archive directory to pack, or a manifest file!")
        sys.exit(1)

    if not os.path.isdir(archive_dir) and not os.path.isdir(manifest):
        print("The provided path is not valid!")
        sys.exit(1)
