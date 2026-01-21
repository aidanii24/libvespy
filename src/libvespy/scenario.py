import ctypes
import mmap
import sys
import os

from libvespy.structs import ScenarioHeader, ScenarioEntry


def extract(filename: str, out_dir: str):
    if not os.path.isfile(filename):
        print(f"{filename} was not found.")

    if not os.path.isdir(out_dir):
        try:
            os.makedirs(out_dir)
        except OSError as e:
            print(f"Failed to create {out_dir}: {e}")
            sys.exit(1)

    with open(filename, "rb") as f:
        mm = mmap.mmap(f.fileno(), 0, prot=mmap.PROT_READ)

        header = ScenarioHeader.from_buffer_copy(mm.read(ctypes.sizeof(ScenarioHeader)))
        file_size_duplicate: int = int.from_bytes(mm.read(4), 'big')
        padding: bytes = mm.read(4)

        for e in range(header.file_count):
            mm.seek(0x20 + e * 0x20)

            scenario_entry = ScenarioEntry.from_buffer_copy(mm.read(ctypes.sizeof(ScenarioEntry)))
            if not scenario_entry.file_size_compressed: continue

            mm.seek(scenario_entry.offset + header.file_offset)
            data: bytes = mm.read(scenario_entry.file_size_compressed)

            with open(os.path.join(out_dir, str(e)), "w+b") as ef:
                ef.truncate(len(data))
                em = mmap.mmap(ef.fileno(), 0, prot=mmap.PROT_WRITE)
                em.resize(len(data))

                em.write(data)

                em.flush()
                ef.close()

        mm.close()
        f.close()