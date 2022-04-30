from __future__ import annotations

import logging
from os.path import sep as osPathSep
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

import numpy as np
import pyqtgraph as pg
import pyqtgraph.console
from qtpy.QtCore import (
    QEvent,
    QItemSelection,
    QItemSelectionModel,
    QModelIndex,
    Qt,
    QUrl,
    Signal,
    Slot,
)
from qtpy.QtGui import QDesktopServices, QKeySequence
from qtpy.QtWidgets import QAction, QApplication, QLabel, QLineEdit, QMainWindow

from .AboutDialog import AboutDialog
from .HorizontalSplitter import HorizontalSplitter
from .MenuBar import MenuBar
from .TagDialog import TagDialog

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    import pandas as pd

    from ..controllers.controller import MainController
    from ..models.model import MainModel
    from .ListView import ListView
    from .PlotArea import PlotView
    from .TreeView import TreeView


class MainWindow(QMainWindow):

    sigPlayRequested = Signal(int, int)
    sigStopRequested = Signal()

    def __init__(self, model: MainModel, controller: MainController) -> None:
        super().__init__()

        self._model = model

        self._controller = controller

        controller.mainWindow = self

        self.setWindowTitle("Barney")

        # taking initial guess on window size
        self.resize(1366, 768)
        self.horizontalSplitter = HorizontalSplitter(self)
        self.setCentralWidget(self.horizontalSplitter)

        # Configuring the listView
        self.listView.setModel(self._model.fileProxyModel)

        self.flagAction = QAction("Flag", self)
        self.flagAction.triggered.connect(self.markFlag)
        self.flagAction.setShortcut(QKeySequence(Qt.Key_F))
        self.flagAction.setStatusTip("Mark Selected Files as Needing Review")
        self.flagAction.setEnabled(False)

        self.skipAction = QAction("Skip", self)
        self.skipAction.triggered.connect(self.markSkip)
        self.skipAction.setShortcut(QKeySequence(Qt.Key_S))
        self.skipAction.setStatusTip("Mark Selected Files to be Skipped")
        self.skipAction.setEnabled(False)

        self.removeFlagAction = QAction("Remove Flag", self)
        self.removeFlagAction.triggered.connect(self.removeFlag)
        self.removeFlagAction.setShortcut(QKeySequence(Qt.ALT + Qt.Key_F))
        self.removeFlagAction.setStatusTip("Remove Flag tag from selected files")
        self.removeFlagAction.setEnabled(False)

        self.removeSkipAction = QAction("Remove Skip", self)
        self.removeSkipAction.triggered.connect(self.removeSkip)
        self.removeSkipAction.setShortcut(QKeySequence(Qt.ALT + Qt.Key_S))
        self.removeSkipAction.setStatusTip("Remove Skip tag from selected files")
        self.removeSkipAction.setEnabled(False)

        self.refreshAction = QAction("Refresh", self)
        self.refreshAction.triggered.connect(self.refreshTracks)
        self.refreshAction.setShortcut(QKeySequence("Ctrl+r"))
        self.refreshAction.setStatusTip("Refresh selected files (and clear cache)")
        self.refreshAction.setEnabled(False)

        self.allowCachingAction = QAction("Allow Caching", self)
        self.allowCachingAction.setCheckable(True)
        self.allowCachingAction.triggered.connect(self.allowCaching)
        self.allowCachingAction.setStatusTip(
            "Allow or prohibit caching for selected files"
        )
        self.allowCachingAction.setEnabled(False)

        # TODO: Incorporate custom QCompleter
        # self.lineEdit.setCompleter(self._controller.textCompleter)

        self.setMenuBar(MenuBar(self))

        # status bar
        self.numberSelected = QLabel("", parent=self)
        self.numberSelected.setFixedWidth(50)
        self.numberSelected.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.numberTotal = QLabel("", parent=self)
        self.numberTotal.setFixedWidth(50)
        self.numberTotal.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.currentFilename = QLabel(parent=self)
        self.statusBar().addWidget(self.numberSelected)
        self.statusBar().addWidget(QLabel("/", parent=self))
        self.statusBar().addWidget(self.numberTotal)
        self.statusBar().addWidget(QLabel(" " * 5, parent=self))
        self.statusBar().addWidget(self.currentFilename)
        self._connect()

    def _connect(self) -> None:
        self._connectMenuBar()
        # When we want updating as the user is typing...
        self.lineEdit.editingFinished.connect(self.relayTextInput)

        self.sigPlayRequested.connect(self._controller.sigPlayRequested)
        self.sigStopRequested.connect(self._controller.sigStopRequested)

        self.listView.selectionModel().selectionChanged.connect(self.enableFileActions)
        self.treeView.selectionModel().selectionChanged.connect(self.enableFileActions)
        self.listView.selectionModel().selectionChanged.connect(
            self.updateSelectedFileCount
        )

        self.treeView.sigSelectIndex.connect(self._controller.selectIndex)
        self.listView.sigSelectIndex.connect(self._controller.selectIndex)

        self._controller.sigSetFileName.connect(self.currentFilename.setText)
        self.listView.sigCopyPath.connect(self.copyPaths)
        self.treeView.sigCopyPath.connect(self.copyPaths)

        self._controller.fileParser.thread.success.connect(self.updateTitle)
        self._controller.fileParser.thread.finished.connect(self.updateTotalFileCount)

    @Slot(QItemSelection, QItemSelection)
    def enableFileActions(self, selected: QItemSelection, _: QItemSelection) -> None:
        enabled = selected.count() > 0
        self.skipAction.setEnabled(enabled)
        self.flagAction.setEnabled(enabled)
        self.removeFlagAction.setEnabled(enabled)
        self.removeSkipAction.setEnabled(enabled)
        self.refreshAction.setEnabled(enabled)
        self.allowCachingAction.setEnabled(enabled)

    @Slot(QItemSelection, QItemSelection)
    def updateSelectedFileCount(self, _: QItemSelection, __: QItemSelection) -> None:
        selectionModel = self.listView.selectionModel()
        self.numberSelected.setText(str(len(selectionModel.selectedRows())))

    @Slot()
    def copyPaths(self) -> None:
        # rows = [index.row() for index in self.selectedIndexes()]
        paths = [
            self._model.fileProxyModel.currentSelection(index)["filepath"]
            for index in self.selectedIndexes()
        ]
        networkPaths = [
            self._model.pathMapper.getNetworkFilepath(Path(path)) for path in paths
        ]
        clipboardContents = [
            networkPath.as_posix() if networkPath is not None else localPath
            for networkPath, localPath in zip(networkPaths, paths)
        ]
        logger.debug("Putting {} in clipboard".format("\n".join(clipboardContents)))
        clipboard = QApplication.instance().clipboard()  # noqa: F821
        clipboard.setText("\n".join(clipboardContents))

    @Slot()
    def updateTotalFileCount(self) -> None:
        if self._model.fileProxyModel.sourceModel() is not None:
            totalFiles = self._model.fileProxyModel.df.shape[0]
        else:
            totalFiles = 0
        logger.debug(f"Setting total file label to {totalFiles}")
        self.numberTotal.setText(str(totalFiles))

    def _connectMenuBar(self) -> None:
        self.menuBar().relayURLs.connect(self._controller.fileParser.receiveQUrl)
        self.menuBar().relayForcedUrl.connect(
            self._controller.fileParser.receiveQUrlForced
        )
        self.menuBar().editMenu.sigSelectFilesInDirectory.connect(
            self.selectFilesInSameDirectory
        )

    @Slot()
    def relayTextInput(self) -> None:
        txt = self.lineEdit.text()
        if txt:
            self._controller.lineParser.parse(txt)
        else:
            self._controller.lineParser.reset()

    @Slot()
    def updateTitle(self) -> None:
        path = self._controller.fileParser.thread.path
        t = f"Barney  |  {path.as_posix()}" + (osPathSep if path.is_dir() else "")
        self.setWindowTitle(t)

    @property
    def lineEdit(self) -> QLineEdit:
        return self.horizontalSplitter.textInput

    @property
    def listView(self) -> ListView:
        return self.horizontalSplitter.listView

    @property
    def treeView(self) -> TreeView:
        return self.horizontalSplitter.tree

    @property
    def plotView(self) -> PlotView:
        return self.horizontalSplitter.plot

    @Slot()
    def refreshTracks(self) -> None:
        self._controller.cacheController.refreshTracks(self.selectedIndexes())

    @Slot(bool)
    def allowCaching(self, allow: bool) -> None:
        if allow:
            self._controller.cacheController.allowCaching(self.selectedIndexes())
        else:
            self._controller.cacheController.prohibitCaching(self.selectedIndexes())

    @Slot()
    def removeSkip(self) -> None:
        self._controller.audioTagController.removeFromDatabase(
            self.selectedIndexes(), "skip"
        )

    @Slot()
    def removeFlag(self) -> None:
        self._controller.audioTagController.removeFromDatabase(
            self.selectedIndexes(), "flag"
        )

    @Slot()
    def markSkip(self) -> None:
        index = self.currentIndex()
        fileSystemModel = self._model.fileSystemModel
        if (
            index.model() is fileSystemModel
            and fileSystemModel.fileInfo(index).isDir()
            and fileSystemModel.rowCount(index) == 0
        ):
            return None
        tagDialog = TagDialog(self, "skip")
        tagDialog.open()

    @Slot()
    def markFlag(self) -> None:
        index = self.currentIndex()
        if index.model() is self._model.fileSystemModel:
            if self._model.fileSystemModel.fileInfo(index).isDir():
                return None
        tagDialog = TagDialog(self, "flag")
        tagDialog.open()

    @Slot()
    def playGlobalRegion(self) -> None:
        self.sigPlayRequested.emit(*tuple(map(int, self.plotView.region.getRegion())))

    def playAlignment(self, minX: int, maxX: int) -> None:
        self.sigPlayRequested.emit(minX, maxX)

    @Slot()
    def changeSize(self) -> None:
        x = self.sender().text()
        self.plotView.updateTranscription(x)

    @Slot()
    def selectFilesInSameDirectory(self) -> None:
        currentSeries = self.currentDataframeEntry()
        if currentSeries is None:
            return None
        index = self.currentIndex()
        df = index.model().df
        selectionFlags = QItemSelectionModel.Rows | QItemSelectionModel.Select

        if index.model() is self._model.fileSystemModel:
            selectionModel = self.treeView.selectionModel()
            for row in range(index.model().rowCount(index.parent())):
                selectionModel.select(index.parent().child(row, 0), selectionFlags)
        else:
            regexMatch = currentSeries["original"].rpartition("/")[0] + "/" + "[^/]*$"
            model = index.model()
            if model is self._model.fileProxyModel:
                model = model.sourceModel()
            selectionModel = self.listView.selectionModel()
            for row in df[df["original"].str.match(regexMatch)].index.to_numpy(
                dtype=int
            ):
                logger.debug(f"Trying to select row {row}")
                modelIndex = model.createIndex(row, 0)
                selectionModel.select(modelIndex, selectionFlags)

    @Slot()
    def launchConsole(self) -> None:
        namespace = {"pg": pg, "np": np}
        ## initial text to display in the console
        text = """
        Go, play. pyqtgraph as pg, numpy as np
        """
        c = pg.console.ConsoleWidget(namespace=namespace, text=text)
        c.show()
        c.setWindowTitle("Barney Python Console")

    def closeEvent(self, event: QEvent) -> None:
        self.clear()
        self._controller.playbackController.stream = None
        super().closeEvent(event)

    def clear(self) -> None:
        self.sigStopRequested.emit()
        self.menuBar().sigUnloadAcousticModel.emit()
        self.plotView.clearTiers()
        self._model.currentWaveform = None
        self._controller.clearDatabase()

    def about(self) -> None:
        aboutDialog = AboutDialog(self, "about")
        aboutDialog.open()

    def currentIndex(self) -> QModelIndex:
        if self.listView.isVisible():
            index = self.listView.selectionModel().currentIndex()
        elif self.treeView.isVisible():
            index = self.treeView.selectionModel().currentIndex()
        else:
            raise RuntimeError
        return index

    def selectedIndexes(self, relativeToSource: bool = True) -> List[QModelIndex]:
        """Method Returning indexes.  If relativeToSource it returns QModelIndex's whose model
        is the source model, otherwise returns indexes relative to the FilerProxyModel

        Returns:
            List[QModelIndex]: List of currently selected indexes relative to the source models
        """
        selection = (
            self.listView.selectionModel()
            if self.listView.isVisible()
            else self.treeView.selectionModel()
        )
        if relativeToSource:
            return [
                self._model.fileProxyModel.mapToSource(index)
                for index in selection.selectedRows()
            ]
        else:
            return selection.selectedRows()

    def currentDataframeEntry(self) -> Optional[pd.Series]:
        index = self.currentIndex()
        if not index.isValid() or index.model() is None:
            return None
        df = index.model().df
        fileProxyModel = self._model.fileProxyModel
        if index.model().sourceModel() is not self._model.fileSystemModel:
            return self._model.fileProxyModel.currentSelection(index)

        fileInfo = (
            index.model().sourceModel().fileInfo(fileProxyModel.mapToSource(index))
        )
        filepath = fileInfo.absoluteFilePath()
        rows = df[df["filepath"] == filepath].drop_duplicates()
        if rows.empty:
            return None
        return rows.iloc[0]

    def currentDatabaseEntry(self) -> Dict[str, str]:
        row = self.currentDataframeEntry()
        if row is not None:
            key = row["key"]
            return self._model.fileProxyModel.sourceModel().sourceData[key]
        else:
            return {}

    @Slot()
    def createHelpWindow(self) -> None:
        wikiUrl = QUrl("https://github.com/j9ac9k/barney/-/wikis/")
        QDesktopServices.openUrl(wikiUrl)
