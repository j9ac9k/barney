from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

import pytest  # noqa: F401
from qtpy.QtCore import QItemSelectionModel, QUrl
from qtpy.QtWidgets import QApplication, QDialogButtonBox

from barney.views.TagDialog import TagDialog
from tests.conftest import qUrlToPath

from ..helpers import openFile

if TYPE_CHECKING:
    from pytestqt import qtbot

    from barney.views.MainWindow import MainWindow

logger = logging.getLogger(__name__)


def test_DirLoad(viewer: MainWindow, dirPath: QUrl, qtbot: qtbot) -> None:
    fileSystemModel = viewer._model.fileSystemModel
    fileProxyModel = viewer._model.fileProxyModel
    treeView = viewer.treeView
    selectionModel = treeView.selectionModel()
    with qtbot.waitSignal(fileSystemModel.directoryLoadFinished):
        openFile(viewer, dirPath, qtbot)
    # make sure the source model in file System model is updated
    assert fileProxyModel.sourceModel() is fileSystemModel

    # make sure the tree view is visible and list view is not
    assert viewer.treeView.isVisible()
    assert not viewer.listView.isVisible()

    # ensure that root path was set correctly
    assert fileSystemModel.rootPath() == dirPath.toDisplayString(
        QUrl.FormattingOptions(QUrl.PreferLocalFile)
    )

    # click on a directory
    dataDirectoryName = "data"
    dataPath = fileSystemModel.rootPath() + os.path.sep + dataDirectoryName
    dataDirectoryIndex = fileSystemModel.index(dataPath)
    assert dataDirectoryIndex.isValid()
    assert dataDirectoryIndex.data() == dataDirectoryName
    assert fileSystemModel.hasChildren(dataDirectoryIndex)

    # with qtbot.waitSignal(treeView.expanded):
    treeViewIndex = treeView.model().mapFromSource(dataDirectoryIndex)
    treeView.setExpanded(treeViewIndex, True)
    qtbot.waitUntil(lambda: treeView.isExpanded(treeViewIndex))
    qApp = QApplication.instance()
    qApp.processEvents()
    qApp.processEvents()
    # select file
    speechFile = "speech-mwm.wav"
    fileIndex = fileSystemModel.index(dataPath + os.path.sep + speechFile)
    assert fileIndex.isValid()
    assert fileIndex.model() is fileSystemModel
    assert fileIndex.data() == speechFile
    assert not fileSystemModel.hasChildren(fileIndex)

    treViewIndex = treeView.model().mapFromSource(fileIndex)

    with qtbot.waitSignal(viewer.plotView.sigPlotWaveformFinished):
        treeView.sigSelectIndex.emit(treViewIndex)

    selectionFlags = QItemSelectionModel.Rows | QItemSelectionModel.Select
    selectionModel.select(treViewIndex, selectionFlags)
    assert viewer._model.currentWaveform is not None

    # skip file
    qApp.processEvents()
    qApp.processEvents()
    with qtbot.waitSignal(qApp.focusWindowChanged):
        viewer.skipAction.triggered.emit()

    if qApp.focusWidget() is None:
        for widget in qApp.topLevelWindows():
            if isinstance(widget, TagDialog):
                tagDialog = widget
                break
        else:
            logger.error("Unable to find tagdialog")
            raise RuntimeError
    else:
        tagDialog = qApp.focusWidget().parent()
        assert isinstance(tagDialog, TagDialog)

    qApp.focusWidget().setText("PyTest Test")
    okButton = tagDialog.buttonBox.button(QDialogButtonBox.Ok)
    with qtbot.waitSignal(
        viewer._controller.audioTagController.sigDatabaseInteractionFinished
    ):
        okButton.clicked.emit()
    qApp.processEvents()

    df = fileIndex.model().df
    logger.debug(f"Index data: {fileIndex.data()}")
    filepath = fileSystemModel.fileInfo(fileIndex).absoluteFilePath()
    logger.debug(f"File Path: {filepath}")

    logger.debug("dataframe contents:")
    logger.debug(f'{df[["filepath", "original", "skip"]]}')
    logger.debug("dataframe partial contents")
    logger.debug(f'{df.loc[df["filepath"] == filepath][["filepath", "skip"]]}')

    # assert df.loc[df["filepath"] == fileSystemModel.filePath(fileIndex)]["skip"].all()
    assert df.loc[
        df["filepath"] == fileSystemModel.fileInfo(fileIndex).absoluteFilePath()
    ]["skip"].all()
    assert (qUrlToPath(dirPath) / "audiotagdb3").exists()
