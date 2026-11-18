"""Load ChainScope's released pandas pickles without running arbitrary code.

The released `df-wm*.pkl.gz` files are pandas DataFrames. Unpickling can call any importable
function, so this loader allows only the eight pandas/numpy constructors that a scan of the
pickle opcodes (pickletools.genops, no execution) found in every file we use. Anything else
raises.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import pickle
from pathlib import Path

ALLOWED = {
    ("pandas.core.frame", "DataFrame"),
    ("pandas.core.internals.managers", "BlockManager"),
    ("pandas._libs.internals", "_unpickle_block"),
    ("numpy.core.numeric", "_frombuffer"),
    ("numpy._core.numeric", "_frombuffer"),
    ("numpy", "dtype"),
    ("numpy.core.multiarray", "_reconstruct"),
    ("numpy._core.multiarray", "_reconstruct"),
    ("numpy", "ndarray"),
    ("pandas.core.indexes.base", "_new_Index"),
    ("pandas.core.indexes.base", "Index"),
    ("pandas.core.indexes.range", "RangeIndex"),
}


class _Restricted(pickle.Unpickler):
    def find_class(self, module, name):
        if (module, name) not in ALLOWED:
            raise pickle.UnpicklingError(f"refused global {module}.{name}")
        if module.startswith("numpy.core."):
            module = module.replace("numpy.core.", "numpy._core.")
        return super().find_class(module, name)


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_df(path):
    raw = gzip.open(path).read()
    return _Restricted(io.BytesIO(raw)).load()
