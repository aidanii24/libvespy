from typing import Literal
import ctypes
import json
import mmap
import sys
import os

from libvespy import utils
from libvespy.structs import FPS4FileData, FPS4


def extract(filename: str, out_dir: str = "", manifest_dir: str = "", ignore_metadata: bool = False):
    """
    Extract contents of FPS4 file.

    :param filename: Path to FPS4 file.
    :param out_dir: Path to where the extracted files will be saved.
    :param manifest_dir: If specified, path to where the general data of the FPS4 file will be saved.
    :param ignore_metadata: If FPS4 metadata should be ignored
    :return: Manifest data
    """

    if not out_dir:
        out_dir = f"{filename}.ext"
        if not os.path.isdir(out_dir):
            os.makedirs(out_dir)

    byteorder: Literal['little', 'big'] = sys.byteorder

    manifest: dict = {}

    with open(filename, "rb") as f:
        mm = mmap.mmap(f.fileno(), 0, prot=mmap.PROT_READ)

        mm.seek(0)
        # Check Magic Number
        if mm.read(4) != 'FPS4'.encode('ascii'):
            raise FPS4Error(f"[ERROR]\t{filename} is not a valid FPS4 file.")

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
        fps4.archive_name = utils.read_null_terminated_string(mm, 'shift-jis', reset_position=False)
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
        file_data: list[dict] = []
        for file in fps4.files:
            file_size: int | None = file.estimate_file_size(fps4.files)

            has_valid_file = True
            file_manifest: dict = file.generate_manifest()
            #{k: v for k, v in file.__dict__.items() if v is not None}

            if not file.skippable:
                if not file.address:
                    raise FPS4Error("[ERROR]\tFPS4 file may be malformed. "
                                    "File does not contain file entry start pointer.")
                if file_size is None:
                    raise FPS4Error("[ERROR]\tFPS4 file may be malformed. "
                                    "File does not contain file size data.")

                file_address: int = file.address * fps4.file_location_multiplier
                first_file_position = min(first_file_position, file_address)
                estimated_alignment = estimated_alignment & ~file_address
                path, archived_filename = file.estimate_file_path(ignore_metadata)

                base_out_dir: str = out_dir

                if path is not None:
                    base_out_dir = os.path.join(base_out_dir, path)
                    if not os.path.isdir(base_out_dir):
                        os.makedirs(base_out_dir)
                else:
                    base_out_dir = archived_filename

                full_out_dir: str = os.path.join(out_dir, base_out_dir)
                file_manifest['path'] = os.path.abspath(full_out_dir)

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
                    af.close()

            file_data.append(file_manifest)

        mm.close()
        f.close()

    # More Metadata
    alignment: int = utils.get_alignment_from_lowest_unset_bit(estimated_alignment)
    manifest['alignment'] = alignment

    if first_file_position != 0xffffffffffffffff:
        first_file_alignment: int = utils.get_alignment_from_lowest_unset_bit(~first_file_position)
        if first_file_alignment > alignment:
            manifest['first_file_alignment'] = first_file_alignment


    manifest['set_sector_size_as_file_size'] = has_valid_file and is_sector_and_file_size_same
    manifest['files'] = file_data

    # Generate Manifest
    if manifest_dir:
        if not os.path.isdir(os.path.dirname(manifest_dir)):
            os.makedirs(os.path.dirname(manifest_dir))
        with open(manifest_dir, "w") as f:
            json.dump(manifest, f, indent=4)

            f.flush()
            f.close()

    return manifest

def pack_from_manifest(output: str, manifest_file: str = "", manifest_data: dict = ""):
    """
    Pack files into FPS4 format using data from a manifest.

    :param output: Path to where the packed archive will be saved.
    :param manifest_file: Path to file where archive manifest data is stored.
    :param manifest_data: Manifest Data.
    :return: None
    """

    if not manifest_file and not manifest_data:
        raise FPS4Error(f"[ERROR]\tManifest data must be provided.")

    if manifest_file:
        with open(manifest_file) as f:
            mf_data = json.load(f)
            f.close()
    else:
        mf_data = manifest_data

    # Re-check file sizes of extracted files in case they are changed
    for file in mf_data['files']:
        if os.path.isfile(file.get('path', '')):
            file['file_size'] = os.path.getsize(file['path'])

    fps4 = FPS4.from_manifest(mf_data)

    metadata_offset: int = fps4.content_data.get_metadata_offset()
    alignment = 1 if not mf_data['alignment'] else mf_data['alignment']
    is_sector_and_file_size_same: bool = mf_data['set_sector_size_as_file_size']
    file_terminator_address: int = mf_data['file_terminator_address']

    first_file_alignment: int = alignment if mf_data.get('first_file_alignment') is None \
        else mf_data['first_file_alignment']

    if not os.path.isdir(os.path.dirname(output)):
        os.makedirs(os.path.dirname(output))

    with open(output, "w+b") as f:
        # Set initial size
        if os.path.getsize(output) < 1: f.truncate(0x1C)

        mm = mmap.mmap(f.fileno(), 0, prot=mmap.PROT_WRITE)

        # Skip Header for now
        mm.seek(ctypes.sizeof(fps4))

        for file_data in mf_data['files']:

            # Place filler for Start Pointer/Sector Size data for now
            if fps4.content_data.has_start_pointers: utils.expand_and_write(mm, bytes(4))
            if fps4.content_data.has_sector_sizes: utils.expand_and_write(mm, bytes(4))

            if fps4.content_data.has_file_sizes:
                utils.expand_and_write(mm, int.to_bytes(file_data.get('file_size', 0),
                                                        length=4, byteorder=fps4.byteorder))
            if fps4.content_data.has_filenames:
                filename: str = file_data.get('filename', '')
                if len(filename) > 0x1F:
                    filename = filename[:0x1F]

                as_bytes: bytes = filename.encode('shift-jis')

                utils.expand_and_write(mm, as_bytes)
                utils.expand_and_write(mm, bytes(0x20 - len(as_bytes)))     # Padding
            if fps4.content_data.has_file_extensions:
                extension: str = file_data.get('file_extension', "")
                if not extension:
                    extension = file_data.get('filename', "")
                    if "." in extension:
                        extension = file_data['filename'].split('.')[-1]
                    if len(extension) > 0x8:
                        extension = extension[:0x8]

                as_bytes: bytes = extension.encode('shift-jis')

                utils.expand_and_write(mm, as_bytes)
                utils.expand_and_write(mm, bytes(0x8 - len(as_bytes)))      # Padding
            if fps4.content_data.has_file_types:
                extension: str = file_data.get('file_type', '')
                if not extension:
                    extension = file_data.get('filename', "")
                    if "." in extension:
                        extension = file_data['filename'].split('.')[-1]
                    if len(extension) > 0x4:
                        extension = extension[:0x4]

                as_bytes: bytes = extension.encode('shift-jis')

                utils.expand_and_write(mm, as_bytes)
                utils.expand_and_write(mm, bytes(0x4 - len(as_bytes)))     # Padding

            # Place filler for Metadata for now
            if fps4.content_data.has_file_metadata: utils.expand_and_write(mm, bytes(4))

            if fps4.content_data.has_mask_0x080: utils.expand_and_write(mm, bytes(4))
            if fps4.content_data.has_mask_0x100: utils.expand_and_write(mm, bytes(4))

        # Reserve space for final entry pointing to end of container
        utils.expand_and_write(mm, bytes(fps4.data.entry_size))

        # Handle Metadata
        if fps4.content_data.has_file_metadata:
            for i, file in enumerate(mf_data['files']):
                metadata = file.get('metadata', None)
                if metadata is None or len(metadata) == 0: continue

                pointer: int = ctypes.sizeof(fps4.data) + (i * fps4.data.entry_size) + metadata_offset

                # Write Pointer
                cur_pos: int = mm.tell()
                utils.expand_and_seek(mm, pointer)
                utils.expand_and_write(mm, cur_pos.to_bytes(4, byteorder=fps4.byteorder))
                mm.seek(cur_pos)

                # Write Metadata
                for kv in file['metadata']:
                    if kv[0] is None:
                        utils.expand_and_write(mm, kv[1].encode('shift-jis'))
                    else:
                        utils.expand_and_write(mm, f"{kv[0]}={kv[1]}".encode('shift-jis'))

                    utils.expand_and_write(mm, 0x20.to_bytes(1, byteorder=fps4.byteorder))

                mm.seek(-1, 1)
                mm.write(bytes(1))

        # Handle Archive Name
        if fps4.archive_name is not None:
            fps4.data.archive_name_address = mm.tell()

            as_bytes = fps4.archive_name.encode('shift-jis')
            utils.expand_and_write(mm, as_bytes)
            utils.expand_and_write(mm, bytes(1))

        # Resolve File Pointers
        last_pos: int = mm.tell()

        ## Handle File Start
        fps4.data.file_start = utils.align_number(mm.tell(), first_file_alignment)

        ## Handle Starting Addresses of Files
        start_pointer: int = fps4.data.file_start
        start_addresses: list[int] = []
        for file_data in mf_data['files']:
            start_addresses.append(start_pointer)
            start_pointer += utils.align_number(file_data.get('file_size', 0), alignment)

        ## Handle Start Pointers and Sector Sizes
        for i, file_data in enumerate(mf_data['files']):
            mm.seek(ctypes.sizeof(fps4.data) + (i * fps4.data.entry_size))

            does_file_exist: bool = os.path.isfile(file_data.get('path', ''))
            if fps4.content_data.has_start_pointers:
                if does_file_exist:
                    data = int(start_addresses[i] / fps4.file_location_multiplier)
                    utils.expand_and_write(mm, int(data).to_bytes(4, byteorder=fps4.byteorder))
                else:
                    utils.expand_and_write(mm, 0xffffffff.to_bytes(4, byteorder=fps4.byteorder))
            if fps4.content_data.has_sector_sizes:
                if does_file_exist:
                    if is_sector_and_file_size_same:
                        data: int = file_data['file_size']
                    else:
                        data: int = utils.align_number(file_data['file_size'], alignment)
                    utils.expand_and_write(mm, int(data).to_bytes(4, byteorder=fps4.byteorder))
                else:
                    utils.expand_and_write(mm, bytes(4))

        # Handle Final Entry
        mm.seek(ctypes.sizeof(fps4.data) + ((len(mf_data['files']) - 1 ) * fps4.data.entry_size))
        if file_terminator_address is None:
            utils.expand_and_write(mm, int(start_pointer / fps4.file_location_multiplier)
                                   .to_bytes(4, byteorder=fps4.byteorder))
        else:
            utils.expand_and_write(mm, file_terminator_address.to_bytes(4, byteorder=fps4.byteorder))

        # Pad until Files address
        mm.seek(last_pos)
        utils.expand_and_write(mm, bytes(fps4.data.file_start - mm.size()))

        # Write Files into archive
        for file_data in mf_data['files']:
            if file_data.get('skippable', False): continue
            if not os.path.isfile(file_data.get('path', '')): continue
            with open(file_data['path'], 'rb') as af:
                utils.expand_and_write(mm, af.read())
                f.close()

            if alignment > 1:
                utils.expand_and_write(mm, bytes(utils.align_number(mm.size(), alignment) - mm.size()))

        # Write Header
        mm.seek(0)
        mm.write(bytearray(fps4.data))

        mm.flush()
        mm.close()
        f.close()

class FPS4Error(Exception):
    """"""