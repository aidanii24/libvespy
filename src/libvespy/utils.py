import mmap


def expand_and_write(mm: mmap.mmap, buffer: bytes):
    if mm.tell() == mm.size() or mm.tell() + len(buffer) > mm.size():
        diff: int = len(buffer) + (mm.tell() - mm.size())
        mm.resize(mm.size() + diff)

    mm.write(buffer)

def expand_and_seek(mm: mmap.mmap, pos: int, whence: int = 0):
    absolute_pos: int = pos if not whence else mm.tell() + pos
    if absolute_pos >= mm.size():
        diff: int = absolute_pos - mm.size()
        mm.resize(mm.size() + diff)

    mm.seek(pos, whence)

def read_null_terminated_string(mm: mmap.mmap, encoding: str = 'utf-8', start: int = -1,
                                reset_position: bool = True) -> str:
    cur: int = mm.tell()
    content: bytearray = bytearray()
    if start >= 0:
        mm.seek(start)

    while mm.tell() < mm.size():
        c: bytes = mm.read(1)
        if c == '\x00'.encode():
            break

        content.extend(c)

    if reset_position:
        mm.seek(cur)

    return content.decode(encoding)

def get_alignment_from_lowest_unset_bit(alignment: int) -> int:
    bits: int = 0
    for b in range(64):
        if alignment & (1 << b) == 0:
            break

        bits += 1

    return 1 << bits

def align_number(base: int, alignment: int, offset: int = 0) -> int:
    diff: int = (base - offset) % alignment

    return base if diff == 0 else base + (alignment - diff)