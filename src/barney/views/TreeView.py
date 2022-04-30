from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from qtpy.QtCore import QEvent, QModelIndex, QPoint, QRect, Qt, Signal, Slot
from qtpy.QtGui import QHelpEvent, QKeyEvent, QKeySequence, QMouseEvent
from qtpy.QtWidgets import (
    QAbstractItemView,
    QFileSystemModel,
    QMenu,
    QToolTip,
    QTreeView,
)

from .StyleDelegate import EntryDelegate

if TYPE_CHECKING:
    from barney.models.FileSystemModel import FileSystemModel

    from .HorizontalSplitter import HorizontalSplitter
    from .MainWindow import MainWindow

logger = logging.getLogger(__name__)


class TreeView(QTreeView):
    sigCopyPath = Signal()
    sigSelectIndex = Signal(QModelIndex)
    sigCopyPath = Signal()

    def __init__(self, parent: HorizontalSplitter) -> None:
        super().__init__(parent)
        self.mainWindow: MainWindow = self.parent().parent()
        self.setModel(self.mainWindow._model.fileProxyModel)
        self.setSortingEnabled(True)
        self.sortByColumn(0, Qt.AscendingOrder)
        self.fileSystemModel.rootPathChanged.connect(self.updateRootPath)
        self.fileSystemModel.directoryLoaded.connect(self.refresh)

        # row selection
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setItemDelegate(EntryDelegate())

        # used for right click menu
        self.setMouseTracking(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.onContext)

    @property
    def fileSystemModel(self) -> FileSystemModel:
        return self.mainWindow._model.fileSystemModel

    @Slot(str)
    def refresh(self, directory: str) -> None:
        if self.model().sourceModel() is not self.fileSystemModel:
            return None
        fileSystemIndex = self.model().sourceModel().index(directory)
        fileProxyIndex = self.model().mapFromSource(fileSystemIndex)
        self.update(fileProxyIndex)

    @Slot(str)
    def updateRootPath(self, rootPath: str) -> None:
        logger.debug(f"Tree view setting rootIndex to {rootPath}")
        self.model().setSourceModel(self.model().parent().fileSystemModel)
        self.model().setSortRole(QFileSystemModel.FilePathRole)

        self.setColumnHidden(1, True)
        self.setColumnHidden(2, True)
        self.setColumnHidden(3, True)
        self.setHeaderHidden(True)
        index = self.model().mapFromSource(self.fileSystemModel.index(rootPath))
        self.setRootIndex(index)

    def currentChanged(self, current: QModelIndex, previous: QModelIndex) -> None:
        if current.isValid():
            self.scrollTo(current, hint=QAbstractItemView.EnsureVisible)
            self.sigSelectIndex.emit(current)

    def viewportEvent(self, event: QEvent) -> bool:
        if event.type() == QEvent.ToolTip:
            self._isActive = True
            helpEvent = QHelpEvent(event.type(), event.pos(), event.globalPos())
            self.showOrUpdateToolTip(helpEvent.globalPos())
            return False
        return super().viewportEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._isActive = False
        QToolTip.hideText()
        super().mouseMoveEvent(event)

    def keyPressEvent(self, event: QEvent) -> bool:
        if event.type() == QKeyEvent.KeyPress and event.matches(QKeySequence.Copy):
            self.sigCopyPath.emit()
            event.setAccepted(True)
            return False
        return super().keyPressEvent(event)

    def showOrUpdateToolTip(self, position: QPoint) -> None:
        if self.underMouse() and self._isActive:
            index = self.indexAt(self.mapFromGlobal(position))
            if index.isValid():
                toolTip = index.data(Qt.ToolTipRole)
                QToolTip.showText(position, toolTip, self, QRect())

    @Slot(QPoint)
    def onContext(self, position: QPoint) -> None:
        """shows right click menu"""
        index = self.mainWindow.selectedIndexes()[0]
        row = self.model().currentSelection(index)
        if row is None or row.empty:
            row = defaultdict(bool)
        isSkipped = row["skip"]
        isFlagged = row["flag"]
        isCacheable = not self.mainWindow._controller.cacheController.isBlacklisted(
            index
        )
        self.mainWindow.allowCachingAction.setChecked(isCacheable)

        menu = QMenu(self)
        if isSkipped:
            menu.addAction(self.mainWindow.removeSkipAction)
        else:
            menu.addAction(self.mainWindow.skipAction)
        if isFlagged:
            menu.addAction(self.mainWindow.removeFlagAction)
        else:
            menu.addAction(self.mainWindow.flagAction)
        menu.addAction(self.mainWindow.refreshAction)
        menu.addAction(self.mainWindow.allowCachingAction)
        menu.exec_(self.mapToGlobal(position))
