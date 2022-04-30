from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, List, Union

import pytest  # noqa: F401
from qtpy.QtCore import QModelIndex, QUrl
from qtpy.QtWidgets import QListView

from .conftest import pathToQUrl

if TYPE_CHECKING:
    from pytestqt import qtbot

    from barney.views.MainWindow import MainWindow

__all__ = ["openFile", "rowSelector"]


def openFile(viewer: MainWindow, file_: Union[QUrl, Path], qtbot: qtbot) -> None:
    if isinstance(file_, Path):
        file_ = pathToQUrl(file_)

    with qtbot.waitSignal(viewer._controller.fileParser.thread.success, timeout=1000):
        viewer.menuBar().relayURLs.emit(file_)

    return None


def rowSelector(
    viewer: MainWindow, rows: Union[List[int], int], qtbot: qtbot
) -> List[QModelIndex]:
    viewer.listView.clearSelection()
    model = viewer.listView.model()
    if isinstance(rows, list):
        viewer.listView.setSelectionMode(QListView.MultiSelection)
        for i in rows:
            index = model.index(i, 0)
            while not index.isValid():
                model.sourceModel().fetchMore(QModelIndex())
                index = model.index(i, 0)
            viewer.listView.setCurrentIndex(index)
        viewer.listView.setSelectionMode(QListView.ExtendedSelection)

    elif isinstance(rows, int):
        index = model.index(rows, 0)
        while not index.isValid():
            model.sourceModel().fetchMore(QModelIndex())
            index = model.index(rows, 0)
        viewer.listView.setCurrentIndex(index)
    else:
        raise TypeError
    qrows = viewer.listView.selectionModel().selectedRows()

    def no_spectrogram_thread():
        assert viewer._controller.plotController.specController.currentThread is None

    qtbot.waitUntil(no_spectrogram_thread)
    return qrows
