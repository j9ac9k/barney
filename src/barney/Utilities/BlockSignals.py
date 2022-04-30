from __future__ import annotations

from typing import TYPE_CHECKING

from qtpy.QtCore import QObject

if TYPE_CHECKING:
    from types import TracebackType
    from typing import Iterable, List, Type, Union


class BlockSignals:
    def __init__(self, qObjects: Union[QObject, Iterable[QObject]]) -> None:
        if isinstance(qObjects, QObject):
            qObjects = (qObjects,)
        self.qObjects = qObjects
        self.orig_values: List[bool] = []

    def __enter__(self) -> BlockSignals:
        for obj in self.qObjects:
            self.orig_values.append(obj.blockSignals(True))
        return self

    def __exit__(self, type_: Type, value: BaseException, tb: TracebackType) -> None:
        for obj, val in zip(self.qObjects, self.orig_values):
            obj.blockSignals(val)
