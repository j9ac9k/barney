from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest  # noqa: F401
from qtpy.QtCore import QUrl

from ..helpers import openFile, rowSelector

if TYPE_CHECKING:
    from pytestqt import qtbot

    from barney.views.MainWindow import MainWindow

logger = logging.getLogger(__name__)


def test_QUrl_db_relative_paths(
    viewer: MainWindow, dbPath_relativeEntries: QUrl, qtbot: qtbot
):
    fileProxyModel = viewer._model.fileProxyModel
    assert fileProxyModel.sourceModel() is None

    # open the relative filepath database file
    openFile(viewer, dbPath_relativeEntries, qtbot)

    assert fileProxyModel.sourceModel() is not None

    assert viewer._controller._model.currentWaveform is None
    row = len(fileProxyModel.df.index)
    assert row > 0

    # check for legit item
    index = rowSelector(viewer, 0, qtbot)[0]
    assert viewer._model.currentWaveform is not None
    assert index.data() == "speech-mwm.flac"

    # filter for bogus item and checking on ¯\_(ツ)_/¯"
    assert not viewer.plotView.mainPlot.shrugItem.isVisible()
    viewer.lineEdit.setText("filename:bogus.wav")
    viewer.lineEdit.editingFinished.emit()

    index = rowSelector(viewer, 0, qtbot)[0]
    assert index.data() == "bogus.wav"
    assert viewer._model.currentWaveform is None
    assert viewer.plotView.mainPlot.shrugItem.isVisible()
