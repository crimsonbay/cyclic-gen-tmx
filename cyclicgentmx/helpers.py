from typing import List
import sys


P28 = 2**8
P216 = P28**2
P224 = P28**3


def int_or_none(value):
    if value is not None:
        return int(value)
    else:
        return None


def float_or_none(value):
    if value is not None:
        return float(value)
    else:
        return None


def get_size(obj, seen=None):
    """Recursively finds size of objects"""
    size = sys.getsizeof(obj)
    if seen is None:
        seen = set()
    obj_id = id(obj)
    if obj_id in seen:
        return 0
    # Important mark as seen *before* entering recursion to gracefully handle
    # self-referential objects
    seen.add(obj_id)
    if isinstance(obj, dict):
        size += sum([get_size(v, seen) for v in obj.values()])
        size += sum([get_size(k, seen) for k in obj.keys()])
    elif hasattr(obj, '__dict__'):
        size += get_size(obj.__dict__, seen)
    elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes, bytearray)):
        size += sum([get_size(i, seen) for i in obj])
    return size


def four_bytes(bytes: List[int]) -> int:
    return bytes[0] + bytes[1] * P28 + bytes[2] * P216 + bytes[3] * P224
