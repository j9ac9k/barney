from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from qtpy.QtCore import QAbstractListModel, QModelIndex, Qt

if TYPE_CHECKING:
    from .SortFilterProxyModel import SortFilterProxyModel


class CompletionModel(QAbstractListModel):
    def __init__(self, parent: SortFilterProxyModel) -> None:
        super().__init__(parent)

    def rowCount(self, parent: Optional[QModelIndex] = None) -> int:
        if parent is None:
            parent = QModelIndex()
        return len(self.parent().sourceModel().keys)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Optional[str]:
        row = index.row()
        if role == Qt.EditRole:
            return self.parent().sourceModel().keys[row]
        return None
