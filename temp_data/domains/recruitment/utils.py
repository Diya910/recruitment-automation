from typing import Any, Optional, TypeVar

T = TypeVar('T')

def get_attribute(obj: Any, attr_name: str, default: Optional[T] = None) -> T:
    if hasattr(obj, attr_name):
        return getattr(obj, attr_name)
    elif isinstance(obj, dict) and attr_name in obj:
        return obj[attr_name]
    return default