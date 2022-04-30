from __future__ import annotations

from typing import TYPE_CHECKING

import pytest  # noqa: F401
from qtpy.QtCore import QUrl
from qtpy.QtWidgets import QApplication

from ..helpers import openFile, rowSelector

if TYPE_CHECKING:
    from pytestqt import qtbot

    from barney.views.MainWindow import MainWindow


def test_trackSelection(viewer: MainWindow, wavPath: QUrl, qtbot: qtbot):
    fileProxyModel = viewer._model.fileProxyModel
    assert fileProxyModel.sourceModel() is None
    openFile(viewer, wavPath, qtbot)
    assert fileProxyModel.sourceModel() is not None
    assert viewer._model.currentWaveform is None
    row = len(fileProxyModel.df.index)
    _ = rowSelector(viewer, row - 1, qtbot)
    assert viewer._model.currentWaveform is not None
    assert viewer._model.currentWaveform.fs == 22050


def test_modelFilter(
    viewer: MainWindow, dbPath_relativeEntries: QUrl, qtbot: qtbot
) -> None:
    fileProxyModel = viewer._model.fileProxyModel
    assert fileProxyModel.sourceModel() is None
    openFile(viewer, dbPath_relativeEntries, qtbot)
    assert not fileProxyModel.df.empty
    qApp = QApplication.instance()
    qApp.processEvents()

    # making sure we imported properly
    indexes = rowSelector(viewer, [0, 1, 2, 3, 4], qtbot)
    assert fileProxyModel.data(indexes[0]) == "speech-mwm.flac"
    assert fileProxyModel.data(indexes[1]) == "metronome.wav"
    assert fileProxyModel.data(indexes[2]) == "speech-mwm.wav"
    assert fileProxyModel.data(indexes[3]) == "bogus.wav"
    assert fileProxyModel.data(indexes[4]) == "synthetic.wav"

    # now we reverse the order
    viewer.lineEdit.setText("order:DESC")
    viewer.lineEdit.editingFinished.emit()
    qApp.processEvents()
    indexes = rowSelector(viewer, [0, 1, 2, 3, 4], qtbot)
    assert fileProxyModel.data(indexes[0]) == "synthetic.wav"
    assert fileProxyModel.data(indexes[1]) == "bogus.wav"
    assert fileProxyModel.data(indexes[2]) == "speech-mwm.wav"
    assert fileProxyModel.data(indexes[3]) == "metronome.wav"
    assert fileProxyModel.data(indexes[4]) == "speech-mwm.flac"

    # filtering and sorting
    viewer.lineEdit.setText("filename:speech order:DESC")
    viewer.lineEdit.editingFinished.emit()
    qApp.processEvents()

    indexes = rowSelector(viewer, [0, 1], qtbot)
    assert fileProxyModel.data(indexes[0]) == "speech-mwm.wav"
    assert fileProxyModel.data(indexes[1]) == "speech-mwm.flac"

    # change the order of the arguments
    viewer.lineEdit.setText("order:DESC filename:speech")
    viewer.lineEdit.editingFinished.emit()
    qApp.processEvents()
    indexes = rowSelector(viewer, [0, 1], qtbot)
    assert fileProxyModel.data(indexes[0]) == "speech-mwm.wav"
    assert fileProxyModel.data(indexes[1]) == "speech-mwm.flac"

    viewer.lineEdit.setText("filename:speech")
    viewer.lineEdit.editingFinished.emit()
    qApp.processEvents()
    indexes = rowSelector(viewer, [0, 1], qtbot)
    assert fileProxyModel.data(indexes[0]) == "speech-mwm.flac"
    assert fileProxyModel.data(indexes[1]) == "speech-mwm.wav"
