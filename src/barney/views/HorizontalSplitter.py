from __future__ import annotations

import logging
from enum import IntEnum
from typing import TYPE_CHECKING

from qtpy.QtCore import Qt, Slot
from qtpy.QtWidgets import QSplitter

from .FileViewPanel import Pane
from .PlotArea import PlotView
from .TreeView import TreeView

if TYPE_CHECKING:
    from qtpy.QtWidgets import QLineEdit

    from barney.views.ListView import ListView
    from barney.views.MainWindow import MainWindow

logger = logging.getLogger(__name__)


class Columns(IntEnum):

    list_ = 0
    tree = 1
    plot = 2


class HorizontalSplitter(QSplitter):
    def __init__(self, parent: MainWindow) -> None:
        super().__init__(parent)
        self.setOrientation(Qt.Horizontal)

        self.pane = Pane(self)
        self.pane.hide()
        self.tree = TreeView(self)
        self.tree.hide()
        self.plot = PlotView(self)

        self.setCollapsible(Columns.list_, True)
        self.setCollapsible(Columns.tree, True)
        self.setCollapsible(Columns.plot, False)

        sizePolicy = self.plot.sizePolicy()
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        self.plot.setSizePolicy(sizePolicy)

        self.setSizes([0, 0, -1])
        self.parent()._controller.sigShowTreeView.connect(self.showTree)
        self.parent()._controller.sigShowListView.connect(self.showPane)

    @Slot()
    def showPane(self) -> None:
        self.pane.show()
        self.tree.hide()
        self.setSizes([self.pane.sizeHint().width(), 0])

    @Slot()
    def showTree(self) -> None:
        self.tree.show()
        self.tree.resizeColumnToContents(0)
        self.setSizes([0, self.tree.sizeHint().width()])
        self.pane.hide()

    @property
    def listView(self) -> ListView:
        return self.pane.listView

    @property
    def textInput(self) -> QLineEdit:
        return self.pane.textInput
