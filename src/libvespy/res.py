from typing import Any, Sequence
import lzma

class Defaults:
    LZMA_FILTERS: Sequence[dict[str, Any]] = [{
        'id': lzma.FILTER_LZMA2,
        'dict_size': 0x10000,
        'lc': 3,
        'lp': 0,
        'pb': 2,
        'nice_len': 64,     # Equivalent to NumFastBytes
        'mf': lzma.MF_BT4
    }]