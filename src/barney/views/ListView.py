from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from qtpy.QtCore import QEvent, QModelIndex, QPoint, QRect, Qt, Signal
from qtpy.QtGui import QHelpEvent, QKeyEvent, QKeySequence, QMouseEvent
from qtpy.QtWidgets import QAbstractItemView, QListView, QMenu, QSizePolicy, QToolTip

from .StyleDelegate import EntryDelegate

if TYPE_CHECKING:
    from .HorizontalSplitter import HorizontalSplitter
    from .MainWindow import MainWindow

logger = logging.getLogger(__name__)


class ListView(QListView):
    sigCopyPath = Signal()
    sigSelectIndex = Signal(QModelIndex)

    def __init__(self, parent: HorizontalSplitter) -> None:
        super().__init__(parent)
        self.setItemDelegate(EntryDelegate())
        self.mainWindow: MainWindow = self.parent().parent().parent()

        self._isActive = False

        # Disabling tab-key navigation
        self.setTabKeyNavigation(False)
        self.setBatchSize(100)
        self.setLayoutMode(QListView.Batched)
        self.setUniformItemSizes(True)
        # used for right click menu
        self.setMouseTracking(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.onContext)

        # sizing
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setSelectionMode(QListView.ExtendedSelection)
        self.setWordWrap(False)
        self.setMinimumWidth(200)

    def viewportEvent(self, event: QEvent) -> bool:
        if event.type() == QEvent.ToolTip:
            self._isActive = True
            helpEvent = QHelpEvent(event.type(), event.pos(), event.globalPos())
            self.showOrUpdateToolTip(helpEvent.globalPos())
            return False
        return super().viewportEvent(event)

    def keyPressEvent(self, event: QEvent) -> bool:
        if event.type() == QKeyEvent.KeyPress:
            if event.key() == Qt.Key_Home:
                self.scrollToTop()
                event.setAccepted(True)
                return False
            elif event.key() == Qt.Key_End:
                self.scrollToBottom()
                event.setAccepted(True)
                return False
            elif event.matches(QKeySequence.Copy):
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

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._isActive = False
        QToolTip.hideText()
        super().mouseMoveEvent(event)

    def onContext(self, position: QPoint) -> None:
        """shows right click menu"""
        index = self.mainWindow.selectedIndexes()[0]

        isSkipped = self.model().df.iloc[index.row()]["skip"]
        isFlagged = self.model().df.iloc[index.row()]["flag"]
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

    def currentChanged(self, current: QModelIndex, previous: QModelIndex) -> None:
        if current.isValid():
            self.scrollTo(current, hint=QAbstractItemView.EnsureVisible)
            self.sigSelectIndex.emit(current)
