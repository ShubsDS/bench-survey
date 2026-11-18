"""Validator's own allow-list unpickler for the released ChainScope count tables (no code run)."""
import gzip, io, pickle
OK = {("pandas.core.frame","DataFrame"),("pandas.core.internals.managers","BlockManager"),
      ("pandas._libs.internals","_unpickle_block"),("numpy.core.numeric","_frombuffer"),
      ("numpy._core.numeric","_frombuffer"),("numpy","dtype"),("numpy.core.multiarray","_reconstruct"),
      ("numpy._core.multiarray","_reconstruct"),("numpy","ndarray"),("pandas.core.indexes.base","_new_Index"),
      ("pandas.core.indexes.base","Index"),("pandas.core.indexes.range","RangeIndex")}
class U(pickle.Unpickler):
    def find_class(self, m, n):
        if (m, n) not in OK: raise pickle.UnpicklingError(f"refused {m}.{n}")
        return super().find_class(m.replace("numpy.core.", "numpy._core."), n)
def load(path):
    return U(io.BytesIO(gzip.open(path).read())).load()
