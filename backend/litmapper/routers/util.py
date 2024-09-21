from typing import Optional, TypeVar

from fastapi import HTTPException

T = TypeVar("T")


def raise_404_if_none(obj: Optional[T], msg="Object not found") -> T:
    if obj is None:
        raise HTTPException(status_code=404, detail=msg)
    return obj
