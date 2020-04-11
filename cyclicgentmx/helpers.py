from typing import List
import sys
import math
from collections import defaultdict


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


def four_bytes(source_bytes: List[int]) -> int:
    return source_bytes[0] + source_bytes[1] * P28 + source_bytes[2] * P216 + source_bytes[3] * P224


def get_four_bytes(tile: int) -> str:
    return tile % P28, tile // P28, tile // P216, tile // P224


def count_types(elements: list):
    if not isinstance(elements, list):
        raise TypeError('elements must be list')
    result = defaultdict(int)
    for element in elements:
        result[type(element)] += 1
    return result


def clear_dict_from_none(original: dict) -> dict:
    return {k: str(v) for k, v in original.items() if v is not None}


def indent(elem, level=0):
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


def lcm(a: List[int]) -> int:
    _lcm = a[0]
    for i in a[1:]:
        _lcm = _lcm * i // math.gcd(_lcm, i)
    return _lcm


def gcd(a: List[int]) -> int:
    _gcd = a[0]
    for i in a[1:]:
        _gcd = math.gcd(_gcd, i)
    return _gcd